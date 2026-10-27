# ESP32 OTA Fleet Client — Firmware

## Overview
This Arduino sketch connects an ESP32 to the Smart OTA Fleet Manager platform.

## Features
- WiFi connection with automatic reconnection
- MQTT command subscription for firmware update notifications  
- HTTP-based device check-in and telemetry reporting
- OTA firmware download via HTTP with SHA-256 verification
- Deployment acknowledgement (downloading → installing → success/failed)
- Duplicate command protection
- ESP-IDF OTA partition support with rollback marking

## Required Libraries

Install via Arduino Library Manager:

| Library | Version | Purpose |
|---------|---------|---------|
| PubSubClient | ≥ 2.8 | MQTT client |
| ArduinoJson | ≥ 7.0 | JSON parsing |
| WiFi | Built-in | WiFi connectivity |
| HTTPClient | Built-in | HTTP requests |
| Update | Built-in | OTA firmware installation |
| mbedtls | Built-in | SHA-256 hash computation |

## Board Configuration

1. **Board**: ESP32 Dev Module
2. **Partition Scheme**: "Minimal SPIFFS (1.9MB APP with OTA)" or "Default 4MB with OTA"
3. **Flash Size**: 4MB (default)
4. **Upload Speed**: 921600

## Setup Steps

### 1. Register the device in the dashboard

1. Open the Fleet Manager dashboard
2. Go to Devices → Register Device
3. Enter the MAC address of your ESP32 (found via Serial Monitor)
4. Copy the generated API key — save it securely

### 2. Configure the firmware

Edit `ota_fleet_client.ino` and set:

```cpp
const char* WIFI_SSID     = "Your_WiFi_SSID";
const char* WIFI_PASSWORD  = "Your_WiFi_Password";
const char* SERVER_URL     = "http://your-server:8000";  // or ngrok URL
const char* MQTT_HOST      = "your-server-ip";            // or ngrok TCP host
const int   MQTT_PORT      = 1883;                        // or ngrok TCP port
const char* DEVICE_UID     = "AABBCCDDEEFF";              // from registration
const char* DEVICE_API_KEY = "your-api-key-here";         // from registration
```

### 3. Flash the firmware

1. Connect ESP32 via USB
2. Select correct COM port in Arduino IDE
3. Upload the sketch

### 4. Cross-network setup (ngrok)

If your faculty is on a different network:

```bash
# Terminal 1: Expose the backend
ngrok http 8000

# Terminal 2: Expose MQTT
ngrok tcp 1883
```

Then update `SERVER_URL` and `MQTT_HOST`/`MQTT_PORT` to the ngrok URLs.

## How It Works

```
┌──────────┐    MQTT commands    ┌──────────┐    HTTP     ┌──────────┐
│  Backend │ ───────────────────→│  ESP32   │ ──────────→│  Backend │
│          │ ←───────────────────│          │            │  (API)   │
│          │    MQTT ack/status  │          │            │          │
│          │                     │          │ ←──────────│(firmware)│
└──────────┘                     └──────────┘  download  └──────────┘
```

1. ESP32 sends periodic check-ins via HTTP POST
2. Backend publishes update command via MQTT
3. ESP32 receives command, fetches manifest via HTTP
4. ESP32 downloads firmware binary via HTTP
5. ESP32 verifies SHA-256 hash before installation
6. ESP32 writes firmware to OTA partition
7. ESP32 reports success/failure via HTTP + MQTT
8. ESP32 reboots to new firmware

## Serial Monitor Output (Example)

```
╔══════════════════════════════════════════╗
║   Smart OTA Fleet Manager — ESP32       ║
╚══════════════════════════════════════════╝
Firmware Version: 1
Chip Model: ESP32-D0WDQ6
Flash Size: 4096 KB
Free Heap: 285432 bytes

[WiFi] Connected — IP: 192.168.1.105, RSSI: -45 dBm
[MQTT] Connected ✓
[MQTT] Subscribed to: fleet/devices/AABBCCDDEEFF/commands
[Check-in] OK — RSSI: -45, Heap: 283256
[MQTT] Received command: type=firmware_update, id=abc123
[OTA] Target version: 2
[OTA] Downloading 145632 bytes...
[OTA] Download complete: 145632 bytes in 3240 ms
[OTA] Computing SHA-256...
[OTA] SHA-256 verified ✓
[OTA] Firmware installed successfully!
[OTA] Rebooting...
```

## Security Notes

- **SHA-256 verification**: Firmware integrity is verified before installation
- **API key authentication**: Each device has a unique API key (hashed on server)
- **Duplicate protection**: Repeated MQTT commands are ignored
- **Rollback**: `esp_ota_mark_app_valid_cancel_rollback()` is called on successful boot
- **Limitation**: Digital signature verification is not implemented in this version (documented as future work)
