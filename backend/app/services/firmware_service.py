"""
Firmware service — upload, publish, deprecate, and download firmware releases.
"""
import os
import uuid
import hashlib
import logging
import aiofiles
from datetime import datetime, timezone
from typing import Optional
from fastapi import UploadFile
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.firmware import FirmwareRelease
from app.core.config import settings

logger = logging.getLogger("firmware_service")

MAX_FILE_SIZE = settings.MAX_FIRMWARE_SIZE_MB * 1024 * 1024  # Convert to bytes


class FirmwareService:

    @staticmethod
    async def list_releases(
        db: AsyncSession, status_filter: Optional[str] = None
    ) -> list[FirmwareRelease]:
        query = select(FirmwareRelease).order_by(FirmwareRelease.created_at.desc())
        if status_filter:
            query = query.where(FirmwareRelease.status == status_filter)
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_release(db: AsyncSession, release_id: str) -> Optional[FirmwareRelease]:
        result = await db.execute(
            select(FirmwareRelease).where(FirmwareRelease.id == release_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def upload_firmware(
        db: AsyncSession,
        file: UploadFile,
        version: str,
        release_name: str,
        description: Optional[str] = None,
        hardware_model: str = "ESP32",
        min_compatible_version: Optional[str] = None,
    ) -> FirmwareRelease:
        """Upload a firmware binary, compute SHA-256, and create a release record."""

        # Validate file extension
        if not file.filename or not file.filename.endswith(".bin"):
            raise ValueError("Firmware file must be a .bin file")

        # Read file content with size limit
        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise ValueError(
                f"File size {len(content)} bytes exceeds maximum {MAX_FILE_SIZE} bytes"
            )
        if len(content) == 0:
            raise ValueError("Firmware file is empty")

        # Compute SHA-256
        sha256_hash = hashlib.sha256(content).hexdigest()

        # Check for duplicate version
        existing = await db.execute(
            select(FirmwareRelease).where(
                FirmwareRelease.version == version,
                FirmwareRelease.hardware_model == hardware_model,
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Firmware version {version} already exists for {hardware_model}")

        # Generate safe filename and save
        release_id = str(uuid.uuid4())
        safe_filename = f"{release_id}.bin"
        file_path = os.path.join(settings.FIRMWARE_STORAGE_PATH, safe_filename)

        os.makedirs(settings.FIRMWARE_STORAGE_PATH, exist_ok=True)
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)

        release = FirmwareRelease(
            id=release_id,
            version=version,
            release_name=release_name,
            description=description,
            hardware_model=hardware_model,
            file_path=safe_filename,
            file_size=len(content),
            sha256_hash=sha256_hash,
            min_compatible_version=min_compatible_version,
        )
        db.add(release)
        await db.flush()

        logger.info(f"Firmware {version} uploaded: {safe_filename} ({len(content)} bytes)")
        return release

    @staticmethod
    async def publish_release(db: AsyncSession, release_id: str) -> Optional[FirmwareRelease]:
        release = await FirmwareService.get_release(db, release_id)
        if not release:
            return None
        if release.status != "draft":
            raise ValueError(f"Cannot publish release in '{release.status}' status")

        release.status = "published"
        release.published_at = datetime.now(timezone.utc)
        await db.flush()
        return release

    @staticmethod
    async def deprecate_release(db: AsyncSession, release_id: str) -> Optional[FirmwareRelease]:
        release = await FirmwareService.get_release(db, release_id)
        if not release:
            return None
        release.status = "deprecated"
        await db.flush()
        return release

    @staticmethod
    def get_firmware_path(release: FirmwareRelease) -> str:
        """Get the absolute file path for a firmware release."""
        return os.path.join(settings.FIRMWARE_STORAGE_PATH, release.file_path)

    @staticmethod
    async def get_firmware_distribution(db: AsyncSession) -> dict[str, int]:
        """Get count of devices running each firmware version."""
        from app.models.device import Device
        result = await db.execute(
            select(Device.firmware_version, func.count(Device.id))
            .where(Device.firmware_version.isnot(None))
            .group_by(Device.firmware_version)
        )
        return {row[0]: row[1] for row in result.all()}
