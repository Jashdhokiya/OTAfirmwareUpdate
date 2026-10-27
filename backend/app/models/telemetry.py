"""
Device telemetry model for storing health metrics.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Integer, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class DeviceTelemetry(Base):
    __tablename__ = "device_telemetry"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    device_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("devices.id"), nullable=False, index=True
    )
    uptime_seconds: Mapped[int] = mapped_column(Integer, nullable=True)
    free_heap_bytes: Mapped[int] = mapped_column(Integer, nullable=True)
    wifi_rssi: Mapped[int] = mapped_column(Integer, nullable=True)
    temperature: Mapped[float] = mapped_column(Float, nullable=True)
    firmware_version: Mapped[str] = mapped_column(String(50), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )

    device = relationship("Device", back_populates="telemetry")
