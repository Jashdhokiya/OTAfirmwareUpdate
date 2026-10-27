# Architecture

## System Components

```
┌───────────────────────────────────────────────────────────────┐
│                     Windows Host Machine                       │
│                                                                │
│  ┌──────────┐  ┌───────────────────────────────────────────┐  │
│  │ Arduino  │  │           Docker Compose                   │  │
│  │   IDE    │  │                                            │  │
│  │          │  │  ┌──────────┐  ┌──────────┐  ┌─────────┐ │  │
│  └──────────┘  │  │ Frontend │  │ Backend  │  │ Postgres│ │  │
│                │  │  :5173   │  │  :8000   │  │  :5432  │ │  │
│                │  └──────────┘  └────┬─────┘  └─────────┘ │  │
│                │                     │                      │  │
│                │               ┌─────┴──────┐              │  │
│                │               │ Mosquitto  │              │  │
│                │               │   :1883    │              │  │
│                │               └─────┬──────┘              │  │
│                └─────────────────────┼──────────────────────┘  │
│                                      │                         │
│                        WiFi Network  │                         │
└──────────────────────────────────────┼─────────────────────────┘
                                       │
                          ┌────────────┼────────────┐
                          │            │            │
                     ┌────┴────┐ ┌────┴────┐ ┌────┴────┐
                     │  ESP32  │ │  ESP32  │ │  SIM    │
                     │ Board A │ │ Board B │ │ Devices │
                     └─────────┘ └─────────┘ └─────────┘
```

## Data Flow

### 1. Device Registration
Admin → Dashboard → POST /api/v1/devices → PostgreSQL → Returns API Key

### 2. Device Heartbeat
ESP32 → POST /api/v1/device/check-in → Backend updates device status

### 3. Firmware Upload
Admin → Dashboard → POST /api/v1/firmware (multipart) → SHA-256 computed → Stored on disk

### 4. Deployment Flow
1. Admin creates deployment → selects firmware + devices
2. Admin starts deployment → backend publishes MQTT commands
3. ESP32 receives command → fetches manifest → downloads firmware
4. ESP32 verifies SHA-256 → writes to OTA partition → reports ACK
5. Dashboard shows live progress

### 5. Cross-Network Access (ngrok)
```
Faculty Browser → ngrok HTTP tunnel → localhost:8000 (Backend)
ESP32 Device   → ngrok HTTP tunnel → localhost:8000 (Firmware download)
ESP32 Device   → ngrok TCP tunnel  → localhost:1883 (MQTT commands)
```

## Database Design

- **users** — Admin accounts with bcrypt password hashes
- **devices** — ESP32 registry with MAC-based UID, API key hash, health metrics
- **firmware_releases** — Firmware binaries with SHA-256, lifecycle status
- **deployments** — Rollout tracking with staged strategy support
- **device_deployment_attempts** — Per-device update status within a deployment
- **device_telemetry** — Historical RSSI, heap, uptime measurements
- **device_events** — Audit trail of device lifecycle events
- **audit_logs** — Admin action history

## Technology Rationale

| Decision | Why |
|----------|-----|
| FastAPI + async | High concurrency for many device connections |
| PostgreSQL | ACID transactions for deployment state integrity |
| MQTT (Mosquitto) | Lightweight pub/sub ideal for IoT command delivery |
| HTTP for firmware download | MQTT unsuitable for large binary transfer |
| SHA-256 on ESP32 | mbedtls built into ESP32 Arduino core |
| JWT for admin auth | Stateless, works with SPA frontend |
| API keys for devices | Simpler than client certificates for student project |
| ngrok for cross-network | Zero-config tunneling, no router access needed |
