"""
Device service — business logic for device management.
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.device import Device
from app.models.event import DeviceEvent
from app.models.telemetry import DeviceTelemetry
from app.schemas.device import DeviceCreate, DeviceUpdate, DeviceCheckIn, DeviceTelemetryReport
from app.security.auth import hash_api_key, verify_api_key
from app.core.config import settings

logger = logging.getLogger("device_service")


class DeviceService:

    @staticmethod
    async def list_devices(
        db: AsyncSession,
        page: int = 1,
        per_page: int = 20,
        search: Optional[str] = None,
        status_filter: Optional[str] = None,
        group_filter: Optional[str] = None,
        model_filter: Optional[str] = None,
    ) -> tuple[list[Device], int]:
        """List devices with filtering and pagination."""
        query = select(Device)

        if search:
            query = query.where(
                or_(
                    Device.device_uid.ilike(f"%{search}%"),
                    Device.display_name.ilike(f"%{search}%"),
                )
            )
        if status_filter:
            query = query.where(Device.status == status_filter)
        if group_filter:
            query = query.where(Device.group_name == group_filter)
        if model_filter:
            query = query.where(Device.hardware_model == model_filter)

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_query)).scalar() or 0

        # Paginate
        query = query.order_by(Device.display_name).offset((page - 1) * per_page).limit(per_page)
        result = await db.execute(query)
        devices = list(result.scalars().all())

        return devices, total

    @staticmethod
    async def get_device(db: AsyncSession, device_id: str) -> Optional[Device]:
        result = await db.execute(select(Device).where(Device.id == device_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_device_by_uid(db: AsyncSession, device_uid: str) -> Optional[Device]:
        result = await db.execute(select(Device).where(Device.device_uid == device_uid))
        return result.scalar_one_or_none()

    @staticmethod
    async def create_device(db: AsyncSession, data: DeviceCreate) -> tuple[Device, str]:
        """Create a new device and return (device, plain_api_key)."""
        # Generate API key
        api_key = str(uuid.uuid4())

        device = Device(
            device_uid=data.device_uid,
            display_name=data.display_name,
            hardware_model=data.hardware_model,
            group_name=data.group_name,
            tags=data.tags,
            api_key_hash=hash_api_key(api_key),
        )
        db.add(device)

        # Record event
        event = DeviceEvent(
            device_id=device.id,
            event_type="registered",
            description=f"Device {data.display_name} registered",
        )
        db.add(event)

        await db.flush()
        return device, api_key

    @staticmethod
    async def update_device(db: AsyncSession, device_id: str, data: DeviceUpdate) -> Optional[Device]:
        device = await DeviceService.get_device(db, device_id)
        if not device:
            return None

        if data.display_name is not None:
            device.display_name = data.display_name
        if data.group_name is not None:
            device.group_name = data.group_name
        if data.tags is not None:
            device.tags = data.tags
        if data.metadata_ is not None:
            device.metadata_ = data.metadata_

        await db.flush()
        return device

    @staticmethod
    async def authenticate_device(db: AsyncSession, device_uid: str, api_key: str) -> Optional[Device]:
        """Authenticate a device using its UID and API key."""
        device = await DeviceService.get_device_by_uid(db, device_uid)
        if not device:
            return None
        if device.is_revoked:
            return None
        if not device.api_key_hash:
            return None
        if not verify_api_key(api_key, device.api_key_hash):
            return None
        return device

    @staticmethod
    async def device_check_in(db: AsyncSession, data: DeviceCheckIn) -> Optional[Device]:
        """Process a device heartbeat/check-in."""
        device = await DeviceService.authenticate_device(db, data.device_uid, data.api_key)
        if not device:
            return None

        now = datetime.now(timezone.utc)
        device.last_seen_at = now
        device.status = "online"
        device.firmware_version = data.firmware_version
        if data.ip_address:
            device.last_ip_address = data.ip_address
        if data.wifi_rssi is not None:
            device.wifi_rssi = data.wifi_rssi
        if data.uptime_seconds is not None:
            device.uptime_seconds = data.uptime_seconds
        if data.free_heap_bytes is not None:
            device.free_heap_bytes = data.free_heap_bytes

        await db.flush()
        return device

    @staticmethod
    async def ingest_telemetry(db: AsyncSession, data: DeviceTelemetryReport) -> bool:
        """Store telemetry data from a device."""
        device = await DeviceService.authenticate_device(db, data.device_uid, data.api_key)
        if not device:
            return False

        telemetry = DeviceTelemetry(
            device_id=device.id,
            uptime_seconds=data.uptime_seconds,
            free_heap_bytes=data.free_heap_bytes,
            wifi_rssi=data.wifi_rssi,
            temperature=data.temperature,
            firmware_version=data.firmware_version,
        )
        db.add(telemetry)

        # Also update device live fields
        device.last_seen_at = datetime.now(timezone.utc)
        device.status = "online"
        if data.wifi_rssi is not None:
            device.wifi_rssi = data.wifi_rssi
        if data.free_heap_bytes is not None:
            device.free_heap_bytes = data.free_heap_bytes
        if data.uptime_seconds is not None:
            device.uptime_seconds = data.uptime_seconds

        await db.flush()
        return True

    @staticmethod
    async def revoke_device(db: AsyncSession, device_id: str) -> Optional[Device]:
        device = await DeviceService.get_device(db, device_id)
        if not device:
            return None
        device.is_revoked = True
        device.api_key_hash = None

        event = DeviceEvent(
            device_id=device.id,
            event_type="revoked",
            description="Device credentials revoked",
        )
        db.add(event)
        await db.flush()
        return device

    @staticmethod
    async def get_device_events(
        db: AsyncSession, device_id: str, limit: int = 50
    ) -> list[DeviceEvent]:
        result = await db.execute(
            select(DeviceEvent)
            .where(DeviceEvent.device_id == device_id)
            .order_by(DeviceEvent.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_device_telemetry(
        db: AsyncSession, device_id: str, limit: int = 100
    ) -> list[DeviceTelemetry]:
        result = await db.execute(
            select(DeviceTelemetry)
            .where(DeviceTelemetry.device_id == device_id)
            .order_by(DeviceTelemetry.recorded_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    @staticmethod
    async def update_offline_devices(db: AsyncSession):
        """Mark devices as offline if they haven't sent a heartbeat recently."""
        threshold = datetime.now(timezone.utc) - __import__("datetime").timedelta(
            seconds=settings.DEVICE_OFFLINE_TIMEOUT_SECONDS
        )
        result = await db.execute(
            select(Device).where(
                Device.status == "online",
                Device.last_seen_at < threshold,
            )
        )
        for device in result.scalars().all():
            device.status = "offline"
        await db.flush()
