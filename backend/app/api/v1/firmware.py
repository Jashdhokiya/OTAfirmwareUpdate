"""
Firmware release management endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.core.database import get_db
from app.models.user import User
from app.schemas.firmware import FirmwareReleaseResponse, FirmwareListResponse
from app.services.firmware_service import FirmwareService
from app.security.auth import get_current_user

router = APIRouter(prefix="/firmware", tags=["Firmware"])


@router.get("", response_model=FirmwareListResponse)
async def list_firmware(
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """List all firmware releases."""
    releases = await FirmwareService.list_releases(db, status_filter=status)
    return FirmwareListResponse(
        releases=[FirmwareReleaseResponse.model_validate(r) for r in releases],
        total=len(releases),
    )


@router.post("", response_model=FirmwareReleaseResponse)
async def upload_firmware(
    file: UploadFile = File(...),
    version: str = Form(...),
    release_name: str = Form(...),
    description: Optional[str] = Form(None),
    hardware_model: str = Form("ESP32"),
    min_compatible_version: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Upload a new firmware binary."""
    try:
        release = await FirmwareService.upload_firmware(
            db, file=file, version=version, release_name=release_name,
            description=description, hardware_model=hardware_model,
            min_compatible_version=min_compatible_version,
        )
        return FirmwareReleaseResponse.model_validate(release)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{release_id}", response_model=FirmwareReleaseResponse)
async def get_firmware(
    release_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    release = await FirmwareService.get_release(db, release_id)
    if not release:
        raise HTTPException(status_code=404, detail="Firmware release not found")
    return FirmwareReleaseResponse.model_validate(release)


@router.post("/{release_id}/publish", response_model=FirmwareReleaseResponse)
async def publish_firmware(
    release_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Publish a draft firmware release."""
    try:
        release = await FirmwareService.publish_release(db, release_id)
        if not release:
            raise HTTPException(status_code=404, detail="Firmware release not found")
        return FirmwareReleaseResponse.model_validate(release)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{release_id}/deprecate", response_model=FirmwareReleaseResponse)
async def deprecate_firmware(
    release_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    release = await FirmwareService.deprecate_release(db, release_id)
    if not release:
        raise HTTPException(status_code=404, detail="Firmware release not found")
    return FirmwareReleaseResponse.model_validate(release)


@router.get("/{release_id}/download")
async def download_firmware(
    release_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Download the firmware binary. Used by ESP32 devices."""
    release = await FirmwareService.get_release(db, release_id)
    if not release:
        raise HTTPException(status_code=404, detail="Firmware release not found")

    file_path = FirmwareService.get_firmware_path(release)
    return FileResponse(
        file_path,
        media_type="application/octet-stream",
        filename=f"firmware-{release.version}.bin",
    )
