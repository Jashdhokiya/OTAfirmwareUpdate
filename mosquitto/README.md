# Mosquitto MQTT Broker Configuration

## Password Setup

The MQTT broker requires password authentication. Before starting:

### Generate the password file:

```bash
# Install mosquitto clients
# Windows: choco install mosquitto
# Or download from https://mosquitto.org/download/

# Create password file (run from this directory)
mosquitto_passwd -c config/passwd fleet_backend
# Enter password: fleet_mqtt_pass (or match your .env)

# For development without mosquitto_passwd installed,
# set allow_anonymous to true temporarily in mosquitto.conf
```

### Quick dev setup (no password):
Edit `config/mosquitto.conf` and change:
```
allow_anonymous true
# password_file /mosquitto/config/passwd
```

## Topic Structure

```
fleet/devices/{device_uid}/commands   — Backend → Device (QoS 1)
fleet/devices/{device_uid}/status     — Device → Backend (QoS 0)
fleet/devices/{device_uid}/telemetry  — Device → Backend (QoS 0)
fleet/devices/{device_uid}/ack        — Device → Backend (QoS 1)
fleet/devices/{device_uid}/events     — Device → Backend (QoS 0)
```
