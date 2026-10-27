# Smart OTA Fleet Manager

A full-stack IoT fleet management platform for ESP32 OTA firmware deployments. Built as a college project demonstrating embedded systems, backend development, MQTT communication, database design, and reliable firmware deployment.

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌──────────────┐
│   React     │────→│   FastAPI   │────→│  PostgreSQL  │
│  Dashboard  │←────│   Backend   │←────│   Database   │
│  (Vite+TS)  │     │  (Python)   │     │              │
└─────────────┘     └──────┬──────┘     └──────────────┘
                           │
                    ┌──────┴──────┐
                    │  Mosquitto  │
                    │   (MQTT)    │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
         ┌────┴────┐ ┌────┴────┐ ┌────┴────┐
         │  ESP32  │ │  ESP32  │ │  ESP32  │
         │ Board A │ │ Board B │ │  (Sim)  │
         └─────────┘ └─────────┘ └─────────┘
```

## Features

- **Device Management**: Register, monitor, and manage ESP32 devices
- **Firmware Lifecycle**: Upload, publish, deprecate firmware with SHA-256 verification
- **OTA Deployments**: Push firmware to individual or groups of devices via MQTT
- **Staged Rollouts**: Canary → percentage → full rollout with failure thresholds
- **Real-time Monitoring**: Live device status, telemetry charts, deployment progress
- **Cross-network Access**: Works via ngrok for faculty demos from different networks
- **Device Simulator**: Test fleet operations without physical hardware

## Quick Start

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) for Windows
- [Node.js](https://nodejs.org/) ≥ 18 (for frontend dev)
- [Python](https://python.org/) ≥ 3.12 (for backend dev or simulator)
- [Arduino IDE](https://www.arduino.cc/en/software) (for ESP32 firmware)
- [ngrok](https://ngrok.com/) (for cross-network demos)

### 1. Clone and configure

```bash
cd smart-ota-fleet-manager
cp .env.example .env
# Edit .env with your passwords
```

### 2. Start with Docker

```bash
# For development, first allow anonymous MQTT:
# Edit mosquitto/config/mosquitto.conf → set allow_anonymous true

docker compose up --build -d
```

Services:
- **Dashboard**: http://localhost:5173
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **MQTT**: localhost:1883

### 3. Login

Default admin: `admin@fleet.local` / `admin123`  
⚠️ Change these in your `.env` before any real deployment.

### 4. Register your ESP32

1. Dashboard → Devices → Register Device
2. Enter the MAC address (found via Serial Monitor)
3. Save the API key
4. Flash firmware with your credentials

### 5. Cross-network setup (ngrok)

```bash
# Terminal 1: Expose backend for dashboard + firmware download
ngrok http 8000

# Terminal 2: Expose MQTT for device commands
ngrok tcp 1883
```

Update `.env`:
```
PUBLIC_BASE_URL=https://your-subdomain.ngrok-free.app
VITE_API_URL=https://your-subdomain.ngrok-free.app
```

Update ESP32 firmware:
```cpp
const char* SERVER_URL = "https://your-subdomain.ngrok-free.app";
const char* MQTT_HOST  = "0.tcp.ngrok.io";
const int   MQTT_PORT  = 12345;  // your ngrok TCP port
```

### 6. Run the device simulator

```bash
cd backend
pip install requests paho-mqtt
python simulator.py --count 5 --server http://localhost:8000
```

## Project Structure

```
smart-ota-fleet-manager/
├── docker-compose.yml       # All services orchestration
├── .env.example             # Environment template
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI entry point
│   │   ├── core/            # Config, database
│   │   ├── api/v1/          # REST endpoints
│   │   ├── models/          # SQLAlchemy models (8 tables)
│   │   ├── schemas/         # Pydantic validation
│   │   ├── services/        # Business logic
│   │   ├── mqtt/            # MQTT client + handlers
│   │   └── security/        # JWT, bcrypt, API keys
│   ├── migrations/          # Alembic database migrations
│   ├── simulator.py         # Multi-device simulator
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── pages/           # Login, Overview, Devices, Firmware, Deployments, Settings
│   │   ├── components/      # StatCard, StatusBadge, ConfirmDialog, States
│   │   ├── hooks/           # useAuth
│   │   ├── services/        # API client (axios)
│   │   └── types/           # TypeScript interfaces
│   └── Dockerfile
├── firmware/
│   ├── ota_fleet_client/    # Arduino sketch for ESP32
│   └── legacy/              # Original prototype
├── mosquitto/
│   └── config/              # MQTT broker configuration
└── storage/                 # Firmware binary storage
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/login` | Admin login |
| GET | `/api/v1/auth/me` | Current user |
| GET/POST | `/api/v1/devices` | List/register devices |
| GET/PATCH | `/api/v1/devices/{id}` | Get/update device |
| POST | `/api/v1/devices/{id}/revoke` | Revoke device credentials |
| GET/POST | `/api/v1/firmware` | List/upload firmware |
| POST | `/api/v1/firmware/{id}/publish` | Publish release |
| GET | `/api/v1/firmware/{id}/download` | Download binary |
| GET/POST | `/api/v1/deployments` | List/create deployments |
| POST | `/api/v1/deployments/{id}/start` | Start deployment |
| POST | `/api/v1/deployments/{id}/cancel` | Cancel deployment |
| POST | `/api/v1/device/check-in` | Device heartbeat |
| POST | `/api/v1/device/telemetry` | Device telemetry |
| POST | `/api/v1/device/deployment-ack` | Deployment ACK |
| WS | `/api/v1/ws` | Real-time updates |

Full OpenAPI docs at `/docs` when backend is running.

## MQTT Protocol

### Topic Structure
```
fleet/devices/{device_uid}/commands   — Backend → Device
fleet/devices/{device_uid}/status     — Device → Backend
fleet/devices/{device_uid}/telemetry  — Device → Backend
fleet/devices/{device_uid}/ack        — Device → Backend
```

### Update Command (Backend → Device)
```json
{
  "schema_version": 1,
  "command_id": "uuid",
  "type": "firmware_update",
  "deployment_id": "uuid",
  "release_id": "uuid",
  "version": "2",
  "manifest_url": "http://server/api/v1/device/firmware/{release_id}/manifest",
  "issued_at": "2024-01-01T00:00:00Z",
  "expires_at": "2024-01-01T00:05:00Z"
}
```

## Security

| Feature | Implementation |
|---------|---------------|
| Admin auth | JWT (HS256) + bcrypt password hashing |
| Device auth | Unique API keys, hashed with bcrypt |
| Firmware integrity | SHA-256 hash verification on ESP32 |
| MQTT auth | Username/password (configurable TLS) |
| Upload validation | .bin extension, size limit (4MB), safe filenames |
| Duplicate protection | Command ID deduplication on device |
| Credential storage | Hashed — never stored in plaintext |

### Known Limitations
- Firmware digital signature verification not yet implemented
- TLS not enabled by default in development mode
- CORS is permissive (`*`) in development

## Database Schema

8 tables: `users`, `devices`, `firmware_releases`, `deployments`, `device_deployment_attempts`, `device_telemetry`, `device_events`, `audit_logs`

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, TanStack Query, Recharts, Lucide |
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.x, Pydantic, Alembic |
| Database | PostgreSQL 16 |
| MQTT | Eclipse Mosquitto 2, Paho MQTT |
| Firmware | Arduino framework, ESP32, PubSubClient, ArduinoJson |
| Deployment | Docker Compose |

## License

MIT — Academic project for IoT coursework.
