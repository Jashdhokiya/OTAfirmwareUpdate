"""
ESP32 Device Simulator — simulates multiple ESP32 devices for testing.

Usage:
  python simulator.py --count 5 --server http://localhost:8000

Each simulated device:
  - Registers itself (if API key provided or uses pre-registered keys)
  - Sends periodic check-ins
  - Sends telemetry
  - Subscribes to MQTT commands
  - Responds to firmware update commands (simulated download + ACK)

NOTE: Simulated devices are clearly marked with "[SIM]" prefix.
"""
import argparse
import json
import time
import uuid
import random
import hashlib
import threading
import requests
import paho.mqtt.client as mqtt


class SimulatedDevice:
    """Simulates a single ESP32 device."""

    def __init__(self, device_num: int, server_url: str, mqtt_host: str,
                 mqtt_port: int, api_key: str = "", device_uid: str = ""):
        self.device_num = device_num
        self.server_url = server_url.rstrip("/")
        self.mqtt_host = mqtt_host
        self.mqtt_port = mqtt_port
        self.device_uid = device_uid or f"SIM{device_num:04d}AABB"
        self.api_key = api_key
        self.firmware_version = "1"
        self.running = True
        self.last_command_id = ""

    def start(self):
        """Start the simulated device in a background thread."""
        thread = threading.Thread(target=self._run, daemon=True)
        thread.start()
        return thread

    def _run(self):
        """Main loop for the simulated device."""
        print(f"[SIM-{self.device_num}] Starting device {self.device_uid}")

        # Connect MQTT
        mqtt_client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=f"sim-{self.device_uid}",
        )
        mqtt_client.username_pw_set("fleet_backend", "fleet_mqtt_pass")
        mqtt_client.on_message = lambda c, u, msg: self._on_mqtt_message(msg)

        try:
            mqtt_client.connect(self.mqtt_host, self.mqtt_port)
            mqtt_client.subscribe(f"fleet/devices/{self.device_uid}/commands", qos=1)
            mqtt_client.loop_start()
            print(f"[SIM-{self.device_num}] MQTT connected")
        except Exception as e:
            print(f"[SIM-{self.device_num}] MQTT failed: {e}")

        # Main loop
        while self.running:
            try:
                self._send_checkin()
                time.sleep(10 + random.uniform(0, 5))
                self._send_telemetry()
                time.sleep(20 + random.uniform(0, 10))
            except Exception as e:
                print(f"[SIM-{self.device_num}] Error: {e}")
                time.sleep(5)

    def _send_checkin(self):
        """Send heartbeat check-in."""
        payload = {
            "device_uid": self.device_uid,
            "api_key": self.api_key,
            "firmware_version": self.firmware_version,
            "ip_address": f"192.168.1.{100 + self.device_num}",
            "wifi_rssi": random.randint(-75, -40),
            "uptime_seconds": int(time.time()) % 86400,
            "free_heap_bytes": random.randint(180000, 280000),
        }
        try:
            r = requests.post(f"{self.server_url}/api/v1/device/check-in",
                              json=payload, timeout=5)
            if r.status_code == 200:
                print(f"[SIM-{self.device_num}] Check-in OK")
            else:
                print(f"[SIM-{self.device_num}] Check-in failed: {r.status_code}")
        except Exception as e:
            print(f"[SIM-{self.device_num}] Check-in error: {e}")

    def _send_telemetry(self):
        """Send telemetry data."""
        payload = {
            "device_uid": self.device_uid,
            "api_key": self.api_key,
            "firmware_version": self.firmware_version,
            "uptime_seconds": int(time.time()) % 86400,
            "free_heap_bytes": random.randint(180000, 280000),
            "wifi_rssi": random.randint(-75, -40),
        }
        try:
            requests.post(f"{self.server_url}/api/v1/device/telemetry",
                          json=payload, timeout=5)
        except Exception:
            pass

    def _on_mqtt_message(self, msg):
        """Handle MQTT command."""
        try:
            payload = json.loads(msg.payload.decode())
            cmd_type = payload.get("type")
            cmd_id = payload.get("command_id", "")

            print(f"[SIM-{self.device_num}] Received command: {cmd_type} ({cmd_id})")

            if cmd_id == self.last_command_id:
                print(f"[SIM-{self.device_num}] Duplicate — ignoring")
                return
            self.last_command_id = cmd_id

            if cmd_type == "firmware_update":
                self._simulate_update(payload)
        except Exception as e:
            print(f"[SIM-{self.device_num}] MQTT error: {e}")

    def _simulate_update(self, cmd):
        """Simulate a firmware update (downloading, verifying, installing)."""
        cmd_id = cmd["command_id"]
        version = cmd.get("version", "unknown")

        # Simulate download time
        self._send_ack(cmd_id, "downloading")
        time.sleep(random.uniform(2, 5))

        # Simulate occasional failures (10% chance for testing)
        if random.random() < 0.1:
            self._send_ack(cmd_id, "failed", "SIMULATED_FAILURE",
                           "Simulated download failure for testing")
            return

        # Simulate installation
        self._send_ack(cmd_id, "installing")
        time.sleep(random.uniform(1, 3))

        # Success
        self.firmware_version = version
        self._send_ack(cmd_id, "success", firmware_version=version)
        print(f"[SIM-{self.device_num}] Updated to v{version}")

    def _send_ack(self, command_id, status, error_code=None,
                  error_message=None, firmware_version=None):
        """Send deployment acknowledgement."""
        payload = {
            "device_uid": self.device_uid,
            "api_key": self.api_key,
            "command_id": command_id,
            "status": status,
        }
        if error_code:
            payload["error_code"] = error_code
        if error_message:
            payload["error_message"] = error_message
        if firmware_version:
            payload["firmware_version"] = firmware_version

        try:
            requests.post(f"{self.server_url}/api/v1/device/deployment-ack",
                          json=payload, timeout=5)
        except Exception as e:
            print(f"[SIM-{self.device_num}] ACK failed: {e}")


def main():
    parser = argparse.ArgumentParser(description="ESP32 Device Simulator")
    parser.add_argument("--count", type=int, default=5, help="Number of simulated devices")
    parser.add_argument("--server", default="http://localhost:8000", help="Backend URL")
    parser.add_argument("--mqtt-host", default="localhost", help="MQTT broker host")
    parser.add_argument("--mqtt-port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument("--register", action="store_true",
                        help="Register devices first (requires admin token)")
    parser.add_argument("--token", default="", help="Admin JWT token for registration")
    args = parser.parse_args()

    devices = []
    api_keys = {}

    # Register devices if requested
    if args.register and args.token:
        print(f"Registering {args.count} simulated devices...")
        headers = {"Authorization": f"Bearer {args.token}"}
        for i in range(1, args.count + 1):
            uid = f"SIM{i:04d}AABB"
            try:
                r = requests.post(
                    f"{args.server}/api/v1/devices",
                    json={
                        "device_uid": uid,
                        "display_name": f"[SIM] Device {i}",
                        "hardware_model": "ESP32",
                        "group_name": "simulators",
                    },
                    headers=headers,
                    timeout=5,
                )
                if r.status_code == 200:
                    data = r.json()
                    api_keys[uid] = data["api_key"]
                    print(f"  Registered {uid}: API key = {data['api_key'][:8]}...")
                else:
                    print(f"  Failed to register {uid}: {r.status_code} {r.text[:100]}")
            except Exception as e:
                print(f"  Error registering {uid}: {e}")

    # Start simulated devices
    print(f"\nStarting {args.count} simulated devices...")
    threads = []
    for i in range(1, args.count + 1):
        uid = f"SIM{i:04d}AABB"
        api_key = api_keys.get(uid, "")
        sim = SimulatedDevice(
            device_num=i,
            server_url=args.server,
            mqtt_host=args.mqtt_host,
            mqtt_port=args.mqtt_port,
            device_uid=uid,
            api_key=api_key,
        )
        threads.append(sim.start())
        time.sleep(0.5)

    print(f"\n{args.count} devices running. Press Ctrl+C to stop.\n")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping simulator...")


if __name__ == "__main__":
    main()
