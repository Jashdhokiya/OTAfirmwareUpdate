"""
Deployment and DeviceDeploymentAttempt models for tracking firmware rollouts.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Integer, Text, JSON, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Deployment(Base):
    """A firmware deployment targeting one or more devices."""
    __tablename__ = "deployments"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    firmware_release_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("firmware_releases.id"), nullable=False
    )

    # Target selection: {"type": "devices", "device_ids": [...]} or {"type": "group", "group_name": "..."}
    target_selection: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Rollout strategy: {"type": "immediate"} or {"type": "staged", "stages": [...]}
    rollout_strategy: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=lambda: {"type": "immediate"}
    )

    # Status: created, in_progress, paused, completed, cancelled, failed
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="created")
    current_stage: Mapped[int] = mapped_column(Integer, nullable=True, default=0)

    # Counters
    total_devices: Mapped[int] = mapped_column(Integer, default=0)
    successful_devices: Mapped[int] = mapped_column(Integer, default=0)
    failed_devices: Mapped[int] = mapped_column(Integer, default=0)

    # Thresholds
    max_failure_percentage: Mapped[int] = mapped_column(Integer, default=20)

    # Audit
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    firmware_release = relationship("FirmwareRelease", lazy="joined")
    attempts = relationship("DeviceDeploymentAttempt", back_populates="deployment", lazy="selectin")


class DeviceDeploymentAttempt(Base):
    """Tracks per-device status within a deployment."""
    __tablename__ = "device_deployment_attempts"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    deployment_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("deployments.id"), nullable=False, index=True
    )
    device_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("devices.id"), nullable=False, index=True
    )

    # Status: pending, command_sent, downloading, installing, success, failed, timeout, cancelled
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    attempt_number: Mapped[int] = mapped_column(Integer, default=1)
    stage_number: Mapped[int] = mapped_column(Integer, nullable=True)

    # MQTT command tracking
    command_id: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=True, default=lambda: str(uuid.uuid4())
    )

    # Error details
    error_code: Mapped[str] = mapped_column(String(50), nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)

    # Timestamps
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    # Prevent duplicate deployment-device pairs
    __table_args__ = (
        UniqueConstraint("deployment_id", "device_id", "attempt_number", name="uq_deployment_device_attempt"),
    )

    # Relationships
    deployment = relationship("Deployment", back_populates="attempts")
    device = relationship("Device", back_populates="deployment_attempts")
