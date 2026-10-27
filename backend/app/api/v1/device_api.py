"""
Device-facing endpoints — called by ESP32 devices, not the admin dashboard.
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.config import settings
from app.schemas.device import DeviceCheckIn, DeviceTelemetryReport, DeploymentAck
from app.schemas.firmware import FirmwareManifest
from app.services.device_service import DeviceService
from app.services.firmware_service import FirmwareService
from app.services.deployment_service import DeploymentService

router = APIRouter(prefix="/device", tags=["Device API"])


@router.post("/check-in")
async def device_check_in(
    data: DeviceCheckIn,
    db: AsyncSession = Depends(get_db),
):
    """Device heartbeat — updates status, firmware version, and connectivity info."""
    device = await DeviceService.device_check_in(db, data)
    if not device:
        raise HTTPException(status_code=401, detail="Invalid device credentials")

    return {
        "status": "ok",
        "desired_firmware_version": device.desired_firmware_version,
        "server_time": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ).isoformat(),
    }


@router.post("/telemetry")
async def device_telemetry(
    data: DeviceTelemetryReport,
    db: AsyncSession = Depends(get_db),
):
    """Ingest telemetry data from a device."""
    success = await DeviceService.ingest_telemetry(db, data)
    if not success:
        raise HTTPException(status_code=401, detail="Invalid device credentials")
    return {"status": "ok"}


@router.post("/deployment-ack")
async def deployment_ack(
    data: DeploymentAck,
    db: AsyncSession = Depends(get_db),
):
    """Process deployment status update from a device."""
    # Authenticate device
    device = await DeviceService.authenticate_device(db, data.device_uid, data.api_key)
    if not device:
        raise HTTPException(status_code=401, detail="Invalid device credentials")

    await DeploymentService.process_device_ack(
        db,
        device_uid=data.device_uid,
        command_id=data.command_id,
        status=data.status,
        error_code=data.error_code,
        error_message=data.error_message,
        firmware_version=data.firmware_version,
    )
    return {"status": "ok"}


@router.get("/firmware/{release_id}/manifest", response_model=FirmwareManifest)
async def get_firmware_manifest(
    release_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Return firmware metadata for the device to verify before downloading."""
    release = await FirmwareService.get_release(db, release_id)
    if not release:
        raise HTTPException(status_code=404, detail="Firmware release not found")

    download_url = f"{settings.PUBLIC_BASE_URL}/api/v1/firmware/{release_id}/download"

    return FirmwareManifest(
        release_id=release.id,
        version=release.version,
        file_size=release.file_size,
        sha256_hash=release.sha256_hash,
        download_url=download_url,
    )
