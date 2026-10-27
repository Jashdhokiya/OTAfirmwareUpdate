# MQTT Protocol Reference

## Topic Structure

All topics follow the pattern: `fleet/devices/{device_uid}/{type}`

| Topic | Direction | QoS | Description |
|-------|-----------|-----|-------------|
| `fleet/devices/{uid}/commands` | Backend → Device | 1 | Firmware update commands |
| `fleet/devices/{uid}/status` | Device → Backend | 0 | Online/offline status |
| `fleet/devices/{uid}/telemetry` | Device → Backend | 0 | Health metrics |
| `fleet/devices/{uid}/ack` | Device → Backend | 1 | Deployment acknowledgements |
| `fleet/devices/{uid}/events` | Device → Backend | 0 | Device events |

## Message Schemas

### Firmware Update Command (Backend → Device)
```json
{
  "schema_version": 1,
  "command_id": "550e8400-e29b-41d4-a716-446655440000",
  "type": "firmware_update",
  "deployment_id": "deployment-uuid",
  "release_id": "release-uuid",
  "version": "2",
  "manifest_url": "http://server:8000/api/v1/device/firmware/release-id/manifest",
  "issued_at": "2024-01-01T12:00:00Z",
  "expires_at": "2024-01-01T12:05:00Z"
}
```

### Cancel Command (Backend → Device)
```json
{
  "schema_version": 1,
  "command_id": "uuid",
  "type": "cancel_update",
  "deployment_id": "deployment-uuid",
  "issued_at": "2024-01-01T12:00:00Z"
}
```

### Device Status (Device → Backend)
```json
{
  "status": "online",
  "firmware_version": "1",
  "ip_address": "192.168.1.105"
}
```

### Device Telemetry (Device → Backend)
```json
{
  "firmware_version": "1",
  "uptime_seconds": 3600,
  "free_heap_bytes": 245000,
  "wifi_rssi": -52
}
```

### Deployment ACK (Device → Backend)
```json
{
  "command_id": "uuid-from-command",
  "status": "success",
  "firmware_version": "2"
}
```

Status values: `downloading`, `installing`, `success`, `failed`

For failures:
```json
{
  "command_id": "uuid",
  "status": "failed",
  "error_code": "HASH_MISMATCH",
  "error_message": "SHA-256 verification failed"
}
```

## Error Codes

| Code | Description |
|------|-------------|
| `MANIFEST_ERROR` | Failed to fetch firmware manifest |
| `MANIFEST_PARSE_ERROR` | Invalid manifest JSON |
| `DOWNLOAD_ERROR` | HTTP error during firmware download |
| `INCOMPLETE_DOWNLOAD` | Not all bytes received |
| `HASH_MISMATCH` | SHA-256 doesn't match manifest |
| `MEMORY_ERROR` | Not enough heap for firmware buffer |
| `UPDATE_BEGIN_ERROR` | Failed to initialize OTA partition |
| `WRITE_ERROR` | Failed to write firmware to flash |
| `UPDATE_END_ERROR` | Failed to finalize OTA update |
| `SIMULATED_FAILURE` | Simulator-generated test failure |

## Duplicate Protection

- Each command has a unique `command_id`
- The ESP32 tracks the last processed `command_id`
- Duplicate commands are silently ignored
- MQTT QoS 1 may deliver duplicates on reconnect — this is handled
