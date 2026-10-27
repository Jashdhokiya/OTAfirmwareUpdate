"""
Deployment service — create, start, cancel, and monitor deployments.
Handles staged rollouts, failure thresholds, and MQTT command dispatch.
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.deployment import Deployment, DeviceDeploymentAttempt
from app.models.device import Device
from app.models.firmware import FirmwareRelease
from app.models.event import DeviceEvent, AuditLog
from app.schemas.deployment import DeploymentCreate
from app.mqtt.client import mqtt_client
from app.core.config import settings

logger = logging.getLogger("deployment_service")


class DeploymentService:

    @staticmethod
    async def list_deployments(
        db: AsyncSession, status_filter: Optional[str] = None, limit: int = 50
    ) -> list[Deployment]:
        query = select(Deployment).order_by(Deployment.created_at.desc()).limit(limit)
        if status_filter:
            query = query.where(Deployment.status == status_filter)
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_deployment(db: AsyncSession, deployment_id: str) -> Optional[Deployment]:
        result = await db.execute(
            select(Deployment).where(Deployment.id == deployment_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create_deployment(
        db: AsyncSession, data: DeploymentCreate, user_id: str
    ) -> Deployment:
        """Create a deployment and resolve target devices."""

        # Validate firmware release exists and is published
        release = await db.execute(
            select(FirmwareRelease).where(FirmwareRelease.id == data.firmware_release_id)
        )
        release = release.scalar_one_or_none()
        if not release:
            raise ValueError("Firmware release not found")
        if release.status != "published":
            raise ValueError("Firmware release must be published before deployment")

        # Resolve target devices
        device_ids = await DeploymentService._resolve_targets(db, data.target_selection, release)

        if not device_ids:
            raise ValueError("No eligible devices found for this deployment")

        deployment = Deployment(
            name=data.name,
            firmware_release_id=data.firmware_release_id,
            target_selection=data.target_selection,
            rollout_strategy=data.rollout_strategy.model_dump(),
            total_devices=len(device_ids),
            max_failure_percentage=data.rollout_strategy.max_failure_percentage,
            created_by=user_id,
        )
        db.add(deployment)
        await db.flush()

        # Create deployment attempts for each device
        for device_id in device_ids:
            attempt = DeviceDeploymentAttempt(
                deployment_id=deployment.id,
                device_id=device_id,
                status="pending",
            )
            db.add(attempt)

        # Audit log
        audit = AuditLog(
            user_id=user_id,
            action="deployment_created",
            resource_type="deployment",
            resource_id=deployment.id,
            details={"name": data.name, "firmware": release.version, "devices": len(device_ids)},
        )
        db.add(audit)

        await db.flush()
        return deployment

    @staticmethod
    async def _resolve_targets(
        db: AsyncSession, target_selection: dict, release: FirmwareRelease
    ) -> list[str]:
        """Resolve target selection to a list of device IDs."""
        target_type = target_selection.get("type", "devices")

        if target_type == "devices":
            device_ids = target_selection.get("device_ids", [])
            result = await db.execute(
                select(Device.id).where(
                    Device.id.in_(device_ids),
                    Device.is_revoked == False,
                    Device.hardware_model == release.hardware_model,
                )
            )
            return [row[0] for row in result.all()]

        elif target_type == "group":
            group_name = target_selection.get("group_name")
            result = await db.execute(
                select(Device.id).where(
                    Device.group_name == group_name,
                    Device.is_revoked == False,
                    Device.hardware_model == release.hardware_model,
                )
            )
            return [row[0] for row in result.all()]

        elif target_type == "all":
            result = await db.execute(
                select(Device.id).where(
                    Device.is_revoked == False,
                    Device.hardware_model == release.hardware_model,
                )
            )
            return [row[0] for row in result.all()]

        return []

    @staticmethod
    async def start_deployment(db: AsyncSession, deployment_id: str) -> Deployment:
        """Start sending update commands to target devices."""
        deployment = await DeploymentService.get_deployment(db, deployment_id)
        if not deployment:
            raise ValueError("Deployment not found")
        if deployment.status not in ("created", "paused"):
            raise ValueError(f"Cannot start deployment in '{deployment.status}' status")

        deployment.status = "in_progress"
        deployment.started_at = datetime.now(timezone.utc)

        release = deployment.firmware_release

        # Get rollout strategy
        strategy = deployment.rollout_strategy or {"type": "immediate"}
        strategy_type = strategy.get("type", "immediate")

        # Get pending attempts
        result = await db.execute(
            select(DeviceDeploymentAttempt)
            .where(
                DeviceDeploymentAttempt.deployment_id == deployment_id,
                DeviceDeploymentAttempt.status == "pending",
            )
        )
        pending_attempts = list(result.scalars().all())

        if strategy_type == "staged":
            stages = strategy.get("stages", [])
            current_stage = deployment.current_stage or 0
            if current_stage < len(stages):
                stage = stages[current_stage]
                batch_size = stage.get("count", 1)
                batch = pending_attempts[:batch_size]
                for attempt in batch:
                    attempt.stage_number = current_stage
                    await DeploymentService._send_command(attempt, deployment, release)
            deployment.current_stage = current_stage
        else:
            # Immediate: send to all devices
            for attempt in pending_attempts:
                await DeploymentService._send_command(attempt, deployment, release)

        await db.flush()
        return deployment

    @staticmethod
    async def _send_command(
        attempt: DeviceDeploymentAttempt,
        deployment: Deployment,
        release: FirmwareRelease,
    ):
        """Send MQTT update command for a single device attempt."""
        from sqlalchemy import select as sa_select
        try:
            # We need the device_uid from the device
            # For now, use a simpler approach
            command_id = str(uuid.uuid4())
            attempt.command_id = command_id
            attempt.status = "command_sent"
            attempt.started_at = datetime.now(timezone.utc)

            # The MQTT publish uses device_uid, we store it in the attempt
            # We'll look it up via the relationship
            device = attempt.device
            if device:
                mqtt_client.publish_update_command(
                    device_uid=device.device_uid,
                    deployment_id=deployment.id,
                    release_id=release.id,
                    version=release.version,
                    command_id=command_id,
                )
                logger.info(f"Sent update command to {device.device_uid}")
        except Exception as e:
            attempt.status = "failed"
            attempt.error_message = str(e)
            logger.error(f"Failed to send command: {e}")

    @staticmethod
    async def cancel_deployment(db: AsyncSession, deployment_id: str) -> Deployment:
        """Cancel a deployment, stopping pending commands."""
        deployment = await DeploymentService.get_deployment(db, deployment_id)
        if not deployment:
            raise ValueError("Deployment not found")

        deployment.status = "cancelled"
        deployment.completed_at = datetime.now(timezone.utc)

        # Cancel pending attempts
        result = await db.execute(
            select(DeviceDeploymentAttempt).where(
                DeviceDeploymentAttempt.deployment_id == deployment_id,
                DeviceDeploymentAttempt.status.in_(["pending", "command_sent"]),
            )
        )
        for attempt in result.scalars().all():
            attempt.status = "cancelled"
            if attempt.device:
                mqtt_client.publish_cancel_command(
                    attempt.device.device_uid, deployment_id
                )

        await db.flush()
        return deployment

    @staticmethod
    async def process_device_ack(
        db: AsyncSession,
        device_uid: str,
        command_id: str,
        status: str,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
        firmware_version: Optional[str] = None,
    ):
        """Process a deployment acknowledgement from a device."""
        # Find the attempt by command_id
        result = await db.execute(
            select(DeviceDeploymentAttempt).where(
                DeviceDeploymentAttempt.command_id == command_id
            )
        )
        attempt = result.scalar_one_or_none()
        if not attempt:
            logger.warning(f"No attempt found for command_id {command_id}")
            return

        now = datetime.now(timezone.utc)
        attempt.status = status
        attempt.updated_at = now
        attempt.error_code = error_code
        attempt.error_message = error_message

        if status in ("success", "failed", "timeout"):
            attempt.completed_at = now

        # Update deployment counters
        deployment = await DeploymentService.get_deployment(db, attempt.deployment_id)
        if deployment:
            if status == "success":
                deployment.successful_devices += 1
                # Update device firmware version
                device = attempt.device
                if device and firmware_version:
                    device.firmware_version = firmware_version
                    device.status = "online"

                # Record event
                event = DeviceEvent(
                    device_id=attempt.device_id,
                    event_type="update_success",
                    description=f"Firmware updated to {firmware_version}",
                    metadata_={"deployment_id": deployment.id, "version": firmware_version},
                )
                db.add(event)

            elif status == "failed":
                deployment.failed_devices += 1

                event = DeviceEvent(
                    device_id=attempt.device_id,
                    event_type="update_failed",
                    description=error_message or "Firmware update failed",
                    metadata_={
                        "deployment_id": deployment.id,
                        "error_code": error_code,
                    },
                )
                db.add(event)

            # Check if deployment is complete or should pause
            await DeploymentService._check_deployment_progress(db, deployment)

        await db.flush()

    @staticmethod
    async def _check_deployment_progress(db: AsyncSession, deployment: Deployment):
        """Check if deployment should advance, pause, or complete."""
        total = deployment.total_devices
        completed = deployment.successful_devices + deployment.failed_devices

        # Check failure threshold
        if total > 0 and deployment.failed_devices > 0:
            failure_rate = (deployment.failed_devices / total) * 100
            if failure_rate >= deployment.max_failure_percentage:
                deployment.status = "paused"
                logger.warning(
                    f"Deployment {deployment.id} paused: failure rate {failure_rate:.1f}% "
                    f"exceeds threshold {deployment.max_failure_percentage}%"
                )
                return

        # Check if all devices are done
        if completed >= total:
            deployment.status = "completed" if deployment.failed_devices == 0 else "completed"
            deployment.completed_at = datetime.now(timezone.utc)
            return

        # For staged rollout, check if current stage is complete
        strategy = deployment.rollout_strategy or {}
        if strategy.get("type") == "staged":
            stages = strategy.get("stages", [])
            current_stage = deployment.current_stage or 0

            # Count completed in current stage
            result = await db.execute(
                select(func.count(DeviceDeploymentAttempt.id)).where(
                    DeviceDeploymentAttempt.deployment_id == deployment.id,
                    DeviceDeploymentAttempt.stage_number == current_stage,
                    DeviceDeploymentAttempt.status.in_(["success", "failed"]),
                )
            )
            stage_completed = result.scalar() or 0

            result = await db.execute(
                select(func.count(DeviceDeploymentAttempt.id)).where(
                    DeviceDeploymentAttempt.deployment_id == deployment.id,
                    DeviceDeploymentAttempt.stage_number == current_stage,
                )
            )
            stage_total = result.scalar() or 0

            if stage_completed >= stage_total and current_stage < len(stages) - 1:
                # Advance to next stage
                deployment.current_stage = current_stage + 1
                logger.info(f"Deployment {deployment.id} advancing to stage {deployment.current_stage}")

    @staticmethod
    async def get_deployment_attempts(
        db: AsyncSession, deployment_id: str
    ) -> list[DeviceDeploymentAttempt]:
        result = await db.execute(
            select(DeviceDeploymentAttempt)
            .where(DeviceDeploymentAttempt.deployment_id == deployment_id)
            .order_by(DeviceDeploymentAttempt.started_at)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_dashboard_stats(db: AsyncSession) -> dict:
        """Compute dashboard statistics from real data."""
        # Device counts
        total_devices = (await db.execute(select(func.count(Device.id)))).scalar() or 0
        online_devices = (
            await db.execute(
                select(func.count(Device.id)).where(Device.status == "online")
            )
        ).scalar() or 0
        offline_devices = total_devices - online_devices

        # Devices needing attention (revoked or with failed recent deployments)
        needing_attention = (
            await db.execute(
                select(func.count(Device.id)).where(Device.is_revoked == True)
            )
        ).scalar() or 0

        # Firmware
        total_releases = (
            await db.execute(select(func.count(FirmwareRelease.id)))
        ).scalar() or 0

        # Deployments
        active_deployments = (
            await db.execute(
                select(func.count(Deployment.id)).where(
                    Deployment.status.in_(["created", "in_progress"])
                )
            )
        ).scalar() or 0

        # Success rate
        completed = await db.execute(
            select(Deployment.successful_devices, Deployment.total_devices).where(
                Deployment.status == "completed"
            )
        )
        completed_rows = completed.all()
        total_attempted = sum(r[1] for r in completed_rows) if completed_rows else 0
        total_successful = sum(r[0] for r in completed_rows) if completed_rows else 0
        success_rate = (total_successful / total_attempted * 100) if total_attempted > 0 else 0

        # Recent deployments
        from app.schemas.deployment import DeploymentResponse
        recent = await DeploymentService.list_deployments(db, limit=5)

        # Firmware distribution
        from app.services.firmware_service import FirmwareService
        fw_dist = await FirmwareService.get_firmware_distribution(db)

        return {
            "total_devices": total_devices,
            "online_devices": online_devices,
            "offline_devices": offline_devices,
            "devices_needing_attention": needing_attention,
            "total_firmware_releases": total_releases,
            "active_deployments": active_deployments,
            "deployment_success_rate": round(success_rate, 1),
            "recent_deployments": recent,
            "firmware_distribution": fw_dist,
        }
