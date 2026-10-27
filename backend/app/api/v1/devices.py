"""
Device management endpoints (admin-facing).
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.core.database import get_db
from app.models.user import User
from app.schemas.device import (
    DeviceCreate, DeviceUpdate, DeviceResponse, DeviceListResponse,
    DeviceCheckIn, DeviceTelemetryReport, DeploymentAck,
)
from app.services.device_service import DeviceService
from app.services.deployment_service import DeploymentService
from app.security.auth import get_current_user

router = APIRouter(prefix="/devices", tags=["Devices"])


@router.get("", response_model=DeviceListResponse)
async def list_devices(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    status: Optional[str] = None,
    group: Optional[str] = None,
    model: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """List all registered devices with filtering."""
    devices, total = await DeviceService.list_devices(
        db, page=page, per_page=per_page,
        search=search, status_filter=status,
        group_filter=group, model_filter=model,
    )
    return DeviceListResponse(
        devices=[DeviceResponse.model_validate(d) for d in devices],
        total=total, page=page, per_page=per_page,
    )


@router.post("", response_model=dict)
async def register_device(
    data: DeviceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Register a new device. Returns the device info and a one-time API key."""
    try:
        device, api_key = await DeviceService.create_device(db, data)
        return {
            "device": DeviceResponse.model_validate(device),
            "api_key": api_key,
            "message": "Save this API key — it will not be shown again.",
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{device_id}", response_model=DeviceResponse)
async def get_device(
    device_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    device = await DeviceService.get_device(db, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return DeviceResponse.model_validate(device)


@router.patch("/{device_id}", response_model=DeviceResponse)
async def update_device(
    device_id: str,
    data: DeviceUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    device = await DeviceService.update_device(db, device_id, data)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return DeviceResponse.model_validate(device)


@router.post("/{device_id}/revoke")
async def revoke_device(
    device_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    device = await DeviceService.revoke_device(db, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return {"message": "Device credentials revoked"}


@router.get("/{device_id}/events")
async def get_device_events(
    device_id: str,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    events = await DeviceService.get_device_events(db, device_id, limit)
    return {"events": [
        {
            "id": e.id,
            "event_type": e.event_type,
            "description": e.description,
            "metadata": e.metadata_,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in events
    ]}


@router.get("/{device_id}/telemetry")
async def get_device_telemetry(
    device_id: str,
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    telemetry = await DeviceService.get_device_telemetry(db, device_id, limit)
    return {"telemetry": [
        {
            "id": t.id,
            "uptime_seconds": t.uptime_seconds,
            "free_heap_bytes": t.free_heap_bytes,
            "wifi_rssi": t.wifi_rssi,
            "temperature": t.temperature,
            "firmware_version": t.firmware_version,
            "recorded_at": t.recorded_at.isoformat() if t.recorded_at else None,
        }
        for t in telemetry
    ]}
