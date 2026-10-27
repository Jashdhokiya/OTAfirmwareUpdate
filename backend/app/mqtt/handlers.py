"""
MQTT message handlers — process incoming device messages.
"""
import logging
from app.mqtt.client import mqtt_client
from app.core.database import async_session
from app.services.device_service import DeviceService
from app.services.deployment_service import DeploymentService

logger = logging.getLogger("mqtt_handlers")


def register_mqtt_handlers():
    """Register all MQTT topic handlers."""
    mqtt_client.register_handler("status", handle_device_status)
    mqtt_client.register_handler("telemetry", handle_device_telemetry)
    mqtt_client.register_handler("ack", handle_device_ack)
    mqtt_client.register_handler("events", handle_device_event)
    logger.info("MQTT handlers registered")


async def handle_device_status(device_uid: str, payload: dict):
    """Handle device status updates received via MQTT."""
    logger.info(f"Device status from {device_uid}: {payload.get('status', 'unknown')}")
    async with async_session() as session:
        device = await DeviceService.get_device_by_uid(session, device_uid)
        if device:
            device.status = payload.get("status", "online")
            if "firmware_version" in payload:
                device.firmware_version = payload["firmware_version"]
            if "ip_address" in payload:
                device.last_ip_address = payload["ip_address"]
            from datetime import datetime, timezone
            device.last_seen_at = datetime.now(timezone.utc)
            await session.commit()


async def handle_device_telemetry(device_uid: str, payload: dict):
    """Handle telemetry data received via MQTT."""
    logger.info(f"Telemetry from {device_uid}")
    async with async_session() as session:
        from app.models.telemetry import DeviceTelemetry
        device = await DeviceService.get_device_by_uid(session, device_uid)
        if device:
            telemetry = DeviceTelemetry(
                device_id=device.id,
                uptime_seconds=payload.get("uptime_seconds"),
                free_heap_bytes=payload.get("free_heap_bytes"),
                wifi_rssi=payload.get("wifi_rssi"),
                temperature=payload.get("temperature"),
                firmware_version=payload.get("firmware_version"),
            )
            session.add(telemetry)
            # Update device live fields
            if payload.get("wifi_rssi") is not None:
                device.wifi_rssi = payload["wifi_rssi"]
            if payload.get("free_heap_bytes") is not None:
                device.free_heap_bytes = payload["free_heap_bytes"]
            if payload.get("uptime_seconds") is not None:
                device.uptime_seconds = payload["uptime_seconds"]
            from datetime import datetime, timezone
            device.last_seen_at = datetime.now(timezone.utc)
            device.status = "online"
            await session.commit()


async def handle_device_ack(device_uid: str, payload: dict):
    """Handle deployment acknowledgements received via MQTT."""
    command_id = payload.get("command_id")
    status = payload.get("status")
    logger.info(f"ACK from {device_uid}: command={command_id}, status={status}")

    if not command_id or not status:
        logger.warning(f"Invalid ACK from {device_uid}")
        return

    async with async_session() as session:
        await DeploymentService.process_device_ack(
            session,
            device_uid=device_uid,
            command_id=command_id,
            status=status,
            error_code=payload.get("error_code"),
            error_message=payload.get("error_message"),
            firmware_version=payload.get("firmware_version"),
        )
        await session.commit()


async def handle_device_event(device_uid: str, payload: dict):
    """Handle generic device events received via MQTT."""
    logger.info(f"Event from {device_uid}: {payload.get('event_type', 'unknown')}")
    async with async_session() as session:
        device = await DeviceService.get_device_by_uid(session, device_uid)
        if device:
            from app.models.event import DeviceEvent
            event = DeviceEvent(
                device_id=device.id,
                event_type=payload.get("event_type", "unknown"),
                description=payload.get("description"),
                metadata_=payload.get("metadata", {}),
            )
            session.add(event)
            await session.commit()
