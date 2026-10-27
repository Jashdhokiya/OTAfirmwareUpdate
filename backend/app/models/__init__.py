# Models package - import all models so Alembic can discover them
from app.models.user import User
from app.models.device import Device
from app.models.firmware import FirmwareRelease
from app.models.deployment import Deployment, DeviceDeploymentAttempt
from app.models.telemetry import DeviceTelemetry
from app.models.event import DeviceEvent, AuditLog

__all__ = [
    "User",
    "Device",
    "FirmwareRelease",
    "Deployment",
    "DeviceDeploymentAttempt",
    "DeviceTelemetry",
    "DeviceEvent",
    "AuditLog",
]
