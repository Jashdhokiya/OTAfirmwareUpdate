"""
MQTT client for backend ↔ device communication.

Handles:
- Publishing firmware update commands to devices
- Subscribing to device status, telemetry, and ACK topics
- Reconnection and message retry logic
"""
import json
import uuid
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Callable
import paho.mqtt.client as mqtt
from app.core.config import settings

logger = logging.getLogger("mqtt_client")


class FleetMQTTClient:
    """Manages MQTT connection for the fleet management backend."""

    # Topic patterns
    TOPIC_DEVICE_STATUS = "fleet/devices/{device_uid}/status"
    TOPIC_DEVICE_TELEMETRY = "fleet/devices/{device_uid}/telemetry"
    TOPIC_DEVICE_ACK = "fleet/devices/{device_uid}/ack"
    TOPIC_DEVICE_COMMANDS = "fleet/devices/{device_uid}/commands"
    TOPIC_DEVICE_EVENTS = "fleet/devices/{device_uid}/events"

    def __init__(self):
        self._client: Optional[mqtt.Client] = None
        self._connected = False
        self._message_handlers: dict[str, list[Callable]] = {}
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    @property
    def is_connected(self) -> bool:
        return self._connected

    def connect(self):
        """Initialize and connect the MQTT client."""
        client_id = f"fleet-backend-{uuid.uuid4().hex[:8]}"
        self._client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=client_id,
            protocol=mqtt.MQTTv311,
        )
        self._client.username_pw_set(settings.MQTT_USERNAME, settings.MQTT_PASSWORD)

        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message

        try:
            self._client.connect(settings.MQTT_BROKER_HOST, settings.MQTT_BROKER_PORT, keepalive=60)
            self._client.loop_start()
            logger.info(f"MQTT connecting to {settings.MQTT_BROKER_HOST}:{settings.MQTT_BROKER_PORT}")
        except Exception as e:
            logger.error(f"MQTT connection failed: {e}")

    def disconnect(self):
        """Disconnect the MQTT client."""
        if self._client:
            self._client.loop_stop()
            self._client.disconnect()
            self._connected = False
            logger.info("MQTT disconnected")

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        """Called when connected to broker."""
        if reason_code == 0:
            self._connected = True
            logger.info("MQTT connected to broker")
            # Subscribe to all device topics
            client.subscribe("fleet/devices/+/status", qos=1)
            client.subscribe("fleet/devices/+/telemetry", qos=1)
            client.subscribe("fleet/devices/+/ack", qos=1)
            client.subscribe("fleet/devices/+/events", qos=1)
        else:
            logger.error(f"MQTT connection failed: {reason_code}")

    def _on_disconnect(self, client, userdata, flags, reason_code, properties):
        """Called when disconnected from broker."""
        self._connected = False
        logger.warning(f"MQTT disconnected: {reason_code}")

    def _on_message(self, client, userdata, msg):
        """Route incoming messages to registered handlers."""
        topic = msg.topic
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.error(f"Invalid MQTT message on {topic}: {e}")
            return

        # Extract device_uid from topic: fleet/devices/{device_uid}/...
        parts = topic.split("/")
        if len(parts) >= 4:
            device_uid = parts[2]
            topic_type = parts[3]  # status, telemetry, ack, events

            # Call registered handlers
            for handler in self._message_handlers.get(topic_type, []):
                try:
                    if self._loop:
                        asyncio.run_coroutine_threadsafe(
                            handler(device_uid, payload), self._loop
                        )
                    else:
                        logger.warning("No event loop set for async handler")
                except Exception as e:
                    logger.error(f"Handler error for {topic_type}: {e}")

    def set_event_loop(self, loop: asyncio.AbstractEventLoop):
        """Set the asyncio event loop for dispatching async handlers."""
        self._loop = loop

    def register_handler(self, topic_type: str, handler: Callable):
        """Register an async handler for a topic type (status, telemetry, ack, events)."""
        if topic_type not in self._message_handlers:
            self._message_handlers[topic_type] = []
        self._message_handlers[topic_type].append(handler)

    def publish_update_command(
        self,
        device_uid: str,
        deployment_id: str,
        release_id: str,
        version: str,
        command_id: Optional[str] = None,
    ) -> str:
        """
        Publish a firmware update command to a device.
        Returns the command_id.
        """
        if not command_id:
            command_id = str(uuid.uuid4())

        topic = self.TOPIC_DEVICE_COMMANDS.format(device_uid=device_uid)

        manifest_url = f"{settings.PUBLIC_BASE_URL}/api/v1/device/firmware/{release_id}/manifest"

        payload = {
            "schema_version": 1,
            "command_id": command_id,
            "type": "firmware_update",
            "deployment_id": deployment_id,
            "release_id": release_id,
            "version": version,
            "manifest_url": manifest_url,
            "issued_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": (
                datetime.now(timezone.utc)
                + timedelta(seconds=settings.DEPLOYMENT_COMMAND_TIMEOUT_SECONDS)
            ).isoformat(),
        }

        if self._client and self._connected:
            result = self._client.publish(
                topic, json.dumps(payload), qos=1, retain=False
            )
            logger.info(f"Published update command {command_id} to {device_uid}")
            return command_id
        else:
            logger.error(f"Cannot publish: MQTT not connected")
            raise ConnectionError("MQTT broker not connected")

    def publish_cancel_command(self, device_uid: str, deployment_id: str):
        """Publish a cancel command to a device."""
        topic = self.TOPIC_DEVICE_COMMANDS.format(device_uid=device_uid)
        payload = {
            "schema_version": 1,
            "command_id": str(uuid.uuid4()),
            "type": "cancel_update",
            "deployment_id": deployment_id,
            "issued_at": datetime.now(timezone.utc).isoformat(),
        }
        if self._client and self._connected:
            self._client.publish(topic, json.dumps(payload), qos=1, retain=False)


# Singleton instance
mqtt_client = FleetMQTTClient()
