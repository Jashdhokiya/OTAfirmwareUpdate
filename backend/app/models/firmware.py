"""
Firmware release model for managing uploaded firmware binaries.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Integer, BigInteger, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class FirmwareRelease(Base):
    __tablename__ = "firmware_releases"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    version: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    release_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    hardware_model: Mapped[str] = mapped_column(String(100), nullable=False, default="ESP32")

    # File metadata
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    # Compatibility
    min_compatible_version: Mapped[str] = mapped_column(String(50), nullable=True)

    # Status lifecycle: draft → published → deprecated
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="draft"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
