# Windows Setup Guide

## Prerequisites

1. **Docker Desktop** — https://www.docker.com/products/docker-desktop/
   - Enable WSL 2 backend during installation
   - After install, open Docker Desktop and wait for it to start

2. **Node.js 18+** — https://nodejs.org/ (for frontend development)

3. **Python 3.12+** — https://python.org/ (for simulator and backend dev)

4. **Arduino IDE 2.x** — https://www.arduino.cc/en/software (for ESP32 firmware)

5. **ngrok** — https://ngrok.com/download (for cross-network demos)
   - Create a free account and get your auth token
   - Run `ngrok config add-authtoken YOUR_TOKEN`

## Quick Start

### Step 1: Setup environment
```powershell
cd "d:\College\sem 7\IoT\project\smart-ota-fleet-manager"
copy .env.example .env
# Edit .env if you want to change default passwords
```

### Step 2: Start all services
```powershell
docker compose up --build -d
```

Wait ~60 seconds for all services to initialize.

### Step 3: Verify services
```powershell
# Check all containers are running
docker compose ps

# Check backend health
curl http://localhost:8000/health

# Open dashboard
start http://localhost:5173
```

### Step 4: Login
- Email: `admin@fleet.local`
- Password: `admin123`

## Frontend Development (without Docker)

```powershell
cd frontend
npm install
npm run dev
# Opens at http://localhost:5173
```

## Backend Development (without Docker)

```powershell
cd backend
pip install -r requirements.txt

# Start PostgreSQL and Mosquitto via Docker
docker compose up postgres mosquitto -d

# Set environment for local dev
$env:DATABASE_URL="postgresql+asyncpg://fleet_admin:devpassword123@localhost:5432/fleet_manager"
$env:MQTT_BROKER_HOST="localhost"

# Run migrations
alembic upgrade head

# Start backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Cross-Network Setup (ngrok)

This allows your faculty to access the dashboard from a different network.

### Terminal 1: HTTP tunnel for backend
```powershell
ngrok http 8000
# Note the HTTPS URL, e.g.: https://abc123.ngrok-free.app
```

### Terminal 2: TCP tunnel for MQTT
```powershell
ngrok tcp 1883
# Note the TCP address, e.g.: 0.tcp.ngrok.io:12345
```

### Update configuration
1. Update `.env`: `PUBLIC_BASE_URL=https://abc123.ngrok-free.app`
2. Update ESP32 firmware with the ngrok URLs
3. Share the ngrok HTTPS URL with your faculty

## Connecting ESP32 Devices

### Find your ESP32 MAC address
1. Upload the firmware sketch
2. Open Serial Monitor (115200 baud)
3. Look for the MAC address in the boot log

### Register in dashboard
1. Go to Devices → Register Device
2. Enter the MAC address (e.g., `AABBCCDDEEFF`)
3. Give it a name (e.g., "Lab Sensor 1")
4. **SAVE THE API KEY** — shown only once

### Configure firmware
Edit `firmware/ota_fleet_client/ota_fleet_client.ino`:
```cpp
const char* WIFI_SSID     = "Your_WiFi";
const char* WIFI_PASSWORD  = "Your_Password";
const char* SERVER_URL     = "http://YOUR_LAPTOP_IP:8000";
const char* MQTT_HOST      = "YOUR_LAPTOP_IP";
const char* DEVICE_UID     = "AABBCCDDEEFF";
const char* DEVICE_API_KEY = "your-api-key-from-dashboard";
```

### Finding your laptop IP
```powershell
ipconfig
# Look for "IPv4 Address" under your WiFi adapter
```

## Firewall Rules

If ESP32 cannot connect, allow these ports through Windows Firewall:
- **8000** (Backend HTTP)
- **1883** (MQTT)

```powershell
# Run as Administrator
netsh advfirewall firewall add rule name="Fleet Manager Backend" dir=in action=allow protocol=TCP localport=8000
netsh advfirewall firewall add rule name="Fleet Manager MQTT" dir=in action=allow protocol=TCP localport=1883
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Docker won't start | Ensure WSL 2 is enabled, restart Docker Desktop |
| Cannot connect to DB | Wait for PostgreSQL health check to pass |
| MQTT connection refused | Check if Mosquitto container is running |
| ESP32 can't reach server | Verify IP address, check firewall rules |
| ngrok URL not working | Restart ngrok, update all URLs |
| Frontend blank page | Check VITE_API_URL in .env matches backend |
