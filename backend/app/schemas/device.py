"""
Pydantic schemas for device endpoints.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class DeviceCreate(BaseModel):
    device_uid: str
    display_name: str
    hardware_model: str = "ESP32"
    group_name: Optional[str] = None
    tags: dict = {}


class DeviceUpdate(BaseModel):
    display_name: Optional[str] = None
    group_name: Optional[str] = None
    tags: Optional[dict] = None
    metadata_: Optional[dict] = None


class DeviceResponse(BaseModel):
    id: str
    device_uid: str
    display_name: str
    hardware_model: str
    firmware_version: Optional[str]
    desired_firmware_version: Optional[str]
    status: str
    last_seen_at: Optional[datetime]
    last_ip_address: Optional[str]
    wifi_rssi: Optional[int]
    uptime_seconds: Optional[int]
    free_heap_bytes: Optional[int]
    tags: dict
    group_name: Optional[str]
    is_revoked: bool
    registered_at: datetime

    class Config:
        from_attributes = True


class DeviceCheckIn(BaseModel):
    """Sent by the ESP32 on heartbeat."""
    device_uid: str
    api_key: str
    firmware_version: str
    ip_address: Optional[str] = None
    wifi_rssi: Optional[int] = None
    uptime_seconds: Optional[int] = None
    free_heap_bytes: Optional[int] = None


class DeviceTelemetryReport(BaseModel):
    """Telemetry data sent by the ESP32."""
    device_uid: str
    api_key: str
    firmware_version: Optional[str] = None
    uptime_seconds: Optional[int] = None
    free_heap_bytes: Optional[int] = None
    wifi_rssi: Optional[int] = None
    temperature: Optional[float] = None


class DeploymentAck(BaseModel):
    """Sent by the ESP32 to acknowledge a deployment command."""
    device_uid: str
    api_key: str
    command_id: str
    status: str  # downloading, installing, success, failed
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    firmware_version: Optional[str] = None


class DeviceListResponse(BaseModel):
    devices: list[DeviceResponse]
    total: int
    page: int
    per_page: int
