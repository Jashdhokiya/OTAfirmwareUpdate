"""
Device model representing an ESP32 in the fleet.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime, JSON, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    # Unique device identifier (derived from MAC address)
    device_uid: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hardware_model: Mapped[str] = mapped_column(String(100), nullable=False, default="ESP32")

    # Authentication - hashed device API key
    api_key_hash: Mapped[str] = mapped_column(String(255), nullable=True)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False)

    # Firmware state
    firmware_version: Mapped[str] = mapped_column(String(50), nullable=True)
    desired_firmware_version: Mapped[str] = mapped_column(String(50), nullable=True)

    # Connectivity
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="offline"
    )  # online, offline, updating
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    last_ip_address: Mapped[str] = mapped_column(String(45), nullable=True)
    wifi_rssi: Mapped[int] = mapped_column(Integer, nullable=True)

    # Health
    uptime_seconds: Mapped[int] = mapped_column(Integer, nullable=True)
    free_heap_bytes: Mapped[int] = mapped_column(Integer, nullable=True)

    # Metadata
    tags: Mapped[dict] = mapped_column(JSON, default=dict)
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    group_name: Mapped[str] = mapped_column(String(100), nullable=True, index=True)

    # Timestamps
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    telemetry = relationship("DeviceTelemetry", back_populates="device", lazy="dynamic")
    events = relationship("DeviceEvent", back_populates="device", lazy="dynamic")
    deployment_attempts = relationship(
        "DeviceDeploymentAttempt", back_populates="device", lazy="dynamic"
    )
