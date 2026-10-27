"""
Pydantic schemas for firmware release endpoints.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class FirmwareReleaseResponse(BaseModel):
    id: str
    version: str
    release_name: str
    description: Optional[str]
    hardware_model: str
    file_size: int
    sha256_hash: str
    min_compatible_version: Optional[str]
    status: str
    created_at: datetime
    published_at: Optional[datetime]

    class Config:
        from_attributes = True


class FirmwareListResponse(BaseModel):
    releases: list[FirmwareReleaseResponse]
    total: int


class FirmwareManifest(BaseModel):
    """Manifest sent to ESP32 before firmware download."""
    release_id: str
    version: str
    file_size: int
    sha256_hash: str
    download_url: str
