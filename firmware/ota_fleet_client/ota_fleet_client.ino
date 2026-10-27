/**
 * ============================================================
 *  Smart OTA Fleet Manager — ESP32 Client Firmware
 * ============================================================
 *
 * This firmware connects an ESP32 to the Fleet Manager platform.
 * It handles:
 *   - WiFi connection and reconnection
 *   - MQTT command subscription and processing
 *   - HTTP check-in and telemetry reporting
 *   - Firmware OTA updates via HTTPS with SHA-256 verification
 *   - Update status acknowledgement
 *
 * Required Libraries (install via Arduino Library Manager):
 *   - PubSubClient (by Nick O'Leary) v2.8+
 *   - ArduinoJson v7.x
 *   - WiFi (built-in ESP32)
 *   - HTTPClient (built-in ESP32)
 *   - Update (built-in ESP32)
 *
 * Board: ESP32 Dev Module
 * Partition Scheme: "Minimal SPIFFS (1.9MB APP with OTA)"
 *
 * ============================================================
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <Update.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <mbedtls/sha256.h>
#include <esp_ota_ops.h>

// ============================================================
// CONFIGURATION — Edit these values for your setup
// ============================================================

// WiFi credentials
const char* WIFI_SSID     = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD  = "YOUR_WIFI_PASSWORD";

// Fleet Manager backend URL (set to ngrok URL for cross-network)
// Example: "http://192.168.1.100:8000" or "https://abc123.ngrok-free.app"
const char* SERVER_URL     = "http://192.168.1.100:8000";

// MQTT Broker (set to ngrok TCP URL for cross-network)
// Example: "192.168.1.100" or "0.tcp.ngrok.io"
const char* MQTT_HOST      = "192.168.1.100";
const int   MQTT_PORT      = 1883;
const char* MQTT_USER      = "fleet_backend";
const char* MQTT_PASS      = "fleet_mqtt_pass";

// Device identity — set after registering in the dashboard
const char* DEVICE_UID     = "";   // Your MAC-based UID, e.g., "AABBCCDDEEFF"
const char* DEVICE_API_KEY = "";   // API key from device registration

// Current firmware version — increment with each new build
const char* FIRMWARE_VERSION = "1";

// ============================================================
// TIMING CONSTANTS
// ============================================================
const unsigned long CHECKIN_INTERVAL      = 30000;   // 30s heartbeat
const unsigned long TELEMETRY_INTERVAL    = 60000;   // 60s telemetry
const unsigned long WIFI_RECONNECT_DELAY  = 5000;    // 5s between WiFi retries
const unsigned long MQTT_RECONNECT_DELAY  = 5000;    // 5s between MQTT retries
const unsigned long COMMAND_EXPIRY_SEC    = 300;     // 5 min command expiry

// ============================================================
// GLOBALS
// ============================================================
WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient);

String deviceMac;              // Derived from WiFi MAC
unsigned long lastCheckin = 0;
unsigned long lastTelemetry = 0;
unsigned long lastMqttReconnect = 0;

// Duplicate command protection
String lastCommandId = "";

// ============================================================
// WiFi Connection
// ============================================================
bool connectWiFi() {
  if (WiFi.status() == WL_CONNECTED) return true;

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("[WiFi] Connecting");

  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < 20000) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("[WiFi] Connected — IP: %s, RSSI: %d dBm\n",
      WiFi.localIP().toString().c_str(), WiFi.RSSI());

    // Derive device MAC
    deviceMac = WiFi.macAddress();
    deviceMac.replace(":", "");
    deviceMac.toUpperCase();

    return true;
  }

  Serial.println("[WiFi] Connection failed");
  return false;
}

// ============================================================
// MQTT Callback — Handle incoming commands
// ============================================================
void mqttCallback(char* topic, byte* payload, unsigned int length) {
  // Parse JSON payload
  JsonDocument doc;
  DeserializationError err = deserializeJson(doc, payload, length);
  if (err) {
    Serial.printf("[MQTT] JSON parse error: %s\n", err.c_str());
    return;
  }

  const char* type = doc["type"];
  const char* commandId = doc["command_id"];

  Serial.printf("[MQTT] Received command: type=%s, id=%s\n", type, commandId);

  // Duplicate protection
  if (commandId && String(commandId) == lastCommandId) {
    Serial.println("[MQTT] Duplicate command — ignoring");
    return;
  }

  // Check command expiry
  const char* expiresAt = doc["expires_at"];
  // (Basic check: we trust the server's timestamp for now)

  if (strcmp(type, "firmware_update") == 0) {
    lastCommandId = String(commandId);
    handleFirmwareUpdate(doc);
  } else if (strcmp(type, "cancel_update") == 0) {
    Serial.println("[MQTT] Received cancel command");
    // If we're not currently downloading, nothing to cancel
  } else {
    Serial.printf("[MQTT] Unknown command type: %s\n", type);
  }
}

// ============================================================
// Firmware Update Handler
// ============================================================
void handleFirmwareUpdate(JsonDocument& cmd) {
  const char* commandId    = cmd["command_id"];
  const char* deploymentId = cmd["deployment_id"];
  const char* releaseId    = cmd["release_id"];
  const char* version      = cmd["version"];
  const char* manifestUrl  = cmd["manifest_url"];

  Serial.println("============================================");
  Serial.printf("[OTA] Update command received\n");
  Serial.printf("[OTA] Target version: %s\n", version);
  Serial.printf("[OTA] Manifest URL: %s\n", manifestUrl);
  Serial.println("============================================");

  // Acknowledge receipt
  sendDeploymentAck(commandId, "downloading", NULL, NULL);

  // Step 1: Fetch firmware manifest
  HTTPClient http;
  http.begin(String(manifestUrl));
  http.setTimeout(10000);
  int httpCode = http.GET();

  if (httpCode != 200) {
    Serial.printf("[OTA] Manifest fetch failed: HTTP %d\n", httpCode);
    sendDeploymentAck(commandId, "failed", "MANIFEST_ERROR",
      ("HTTP " + String(httpCode)).c_str());
    http.end();
    return;
  }

  // Parse manifest
  JsonDocument manifest;
  DeserializationError err = deserializeJson(manifest, http.getString());
  http.end();

  if (err) {
    Serial.printf("[OTA] Manifest parse error: %s\n", err.c_str());
    sendDeploymentAck(commandId, "failed", "MANIFEST_PARSE_ERROR", err.c_str());
    return;
  }

  const char* downloadUrl  = manifest["download_url"];
  const char* expectedHash = manifest["sha256_hash"];
  int expectedSize         = manifest["file_size"];

  Serial.printf("[OTA] Download URL: %s\n", downloadUrl);
  Serial.printf("[OTA] Expected SHA256: %s\n", expectedHash);
  Serial.printf("[OTA] Expected size: %d bytes\n", expectedSize);

  // Step 2: Download firmware and compute SHA-256
  sendDeploymentAck(commandId, "downloading", NULL, NULL);

  HTTPClient dlHttp;
  dlHttp.begin(String(downloadUrl));
  dlHttp.setTimeout(30000);
  httpCode = dlHttp.GET();

  if (httpCode != 200) {
    Serial.printf("[OTA] Download failed: HTTP %d\n", httpCode);
    sendDeploymentAck(commandId, "failed", "DOWNLOAD_ERROR",
      ("HTTP " + String(httpCode)).c_str());
    dlHttp.end();
    return;
  }

  int contentLength = dlHttp.getSize();
  if (contentLength <= 0) {
    Serial.println("[OTA] Invalid content length");
    sendDeploymentAck(commandId, "failed", "INVALID_SIZE", "Content length is 0");
    dlHttp.end();
    return;
  }

  Serial.printf("[OTA] Downloading %d bytes...\n", contentLength);

  // Get the stream
  WiFiClient* stream = dlHttp.getStreamPtr();

  // Allocate buffer for the entire firmware
  uint8_t* firmwareBuf = (uint8_t*)malloc(contentLength);
  if (!firmwareBuf) {
    Serial.println("[OTA] Failed to allocate memory for firmware");
    sendDeploymentAck(commandId, "failed", "MEMORY_ERROR", "Cannot allocate firmware buffer");
    dlHttp.end();
    return;
  }

  // Read all data
  int bytesRead = 0;
  unsigned long dlStart = millis();
  while (bytesRead < contentLength && (millis() - dlStart) < 60000) {
    if (stream->available()) {
      int toRead = min((int)stream->available(), contentLength - bytesRead);
      int read = stream->readBytes(firmwareBuf + bytesRead, toRead);
      bytesRead += read;

      // Progress every 10%
      if (bytesRead % (contentLength / 10 + 1) < 512) {
        Serial.printf("[OTA] Downloaded %d / %d bytes (%d%%)\n",
          bytesRead, contentLength, (bytesRead * 100) / contentLength);
      }
    }
    delay(1);
  }
  dlHttp.end();

  if (bytesRead != contentLength) {
    Serial.printf("[OTA] Incomplete download: %d / %d bytes\n", bytesRead, contentLength);
    sendDeploymentAck(commandId, "failed", "INCOMPLETE_DOWNLOAD",
      ("Got " + String(bytesRead) + " of " + String(contentLength)).c_str());
    free(firmwareBuf);
    return;
  }

  Serial.printf("[OTA] Download complete: %d bytes in %lu ms\n",
    bytesRead, millis() - dlStart);

  // Step 3: Verify SHA-256
  Serial.println("[OTA] Computing SHA-256...");
  uint8_t hash[32];
  mbedtls_sha256_context ctx;
  mbedtls_sha256_init(&ctx);
  mbedtls_sha256_starts(&ctx, 0);
  mbedtls_sha256_update(&ctx, firmwareBuf, contentLength);
  mbedtls_sha256_finish(&ctx, hash);
  mbedtls_sha256_free(&ctx);

  // Convert to hex string
  char computedHash[65];
  for (int i = 0; i < 32; i++) {
    sprintf(computedHash + (i * 2), "%02x", hash[i]);
  }
  computedHash[64] = '\0';

  Serial.printf("[OTA] Computed SHA256: %s\n", computedHash);
  Serial.printf("[OTA] Expected SHA256: %s\n", expectedHash);

  if (strcmp(computedHash, expectedHash) != 0) {
    Serial.println("[OTA] *** SHA-256 MISMATCH — REFUSING INSTALLATION ***");
    sendDeploymentAck(commandId, "failed", "HASH_MISMATCH",
      "SHA-256 verification failed");
    free(firmwareBuf);
    return;
  }

  Serial.println("[OTA] SHA-256 verified ✓");

  // Step 4: Install firmware to OTA partition
  sendDeploymentAck(commandId, "installing", NULL, NULL);

  if (!Update.begin(contentLength)) {
    Serial.printf("[OTA] Update.begin() failed: %s\n",
      Update.errorString());
    sendDeploymentAck(commandId, "failed", "UPDATE_BEGIN_ERROR",
      Update.errorString());
    free(firmwareBuf);
    return;
  }

  size_t written = Update.write(firmwareBuf, contentLength);
  free(firmwareBuf);  // Free memory immediately

  if (written != (size_t)contentLength) {
    Serial.printf("[OTA] Write failed: wrote %d / %d\n", written, contentLength);
    Update.abort();
    sendDeploymentAck(commandId, "failed", "WRITE_ERROR",
      ("Wrote " + String(written) + " of " + String(contentLength)).c_str());
    return;
  }

  if (!Update.end(true)) {
    Serial.printf("[OTA] Update.end() failed: %s\n", Update.errorString());
    sendDeploymentAck(commandId, "failed", "UPDATE_END_ERROR",
      Update.errorString());
    return;
  }

  Serial.println("[OTA] ============================================");
  Serial.println("[OTA] Firmware installed successfully!");
  Serial.println("[OTA] ============================================");

  // Report success
  sendDeploymentAck(commandId, "success", NULL, version);

  // Allow time for ACK to be sent
  delay(2000);

  Serial.println("[OTA] Rebooting...");
  ESP.restart();
}

// ============================================================
// Send deployment acknowledgement via HTTP
// ============================================================
void sendDeploymentAck(const char* commandId, const char* status,
                       const char* errorCode, const char* extra) {
  JsonDocument doc;
  doc["device_uid"] = strlen(DEVICE_UID) > 0 ? DEVICE_UID : deviceMac.c_str();
  doc["api_key"]    = DEVICE_API_KEY;
  doc["command_id"] = commandId;
  doc["status"]     = status;

  if (errorCode) doc["error_code"] = errorCode;
  if (extra) {
    if (strcmp(status, "success") == 0) {
      doc["firmware_version"] = extra;
    } else {
      doc["error_message"] = extra;
    }
  }

  String body;
  serializeJson(doc, body);

  HTTPClient http;
  String url = String(SERVER_URL) + "/api/v1/device/deployment-ack";
  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(5000);
  int code = http.POST(body);
  Serial.printf("[ACK] %s → HTTP %d\n", status, code);
  http.end();

  // Also publish via MQTT for redundancy
  String uid = strlen(DEVICE_UID) > 0 ? String(DEVICE_UID) : deviceMac;
  String topic = "fleet/devices/" + uid + "/ack";
  JsonDocument ackDoc;
  ackDoc["command_id"] = commandId;
  ackDoc["status"]     = status;
  if (errorCode) ackDoc["error_code"] = errorCode;
  if (extra && strcmp(status, "success") == 0) ackDoc["firmware_version"] = extra;
  if (extra && strcmp(status, "failed") == 0) ackDoc["error_message"] = extra;

  String ackBody;
  serializeJson(ackDoc, ackBody);
  mqttClient.publish(topic.c_str(), ackBody.c_str());
}

// ============================================================
// Device Check-in (heartbeat)
// ============================================================
void sendCheckin() {
  JsonDocument doc;
  doc["device_uid"]      = strlen(DEVICE_UID) > 0 ? DEVICE_UID : deviceMac.c_str();
  doc["api_key"]         = DEVICE_API_KEY;
  doc["firmware_version"] = FIRMWARE_VERSION;
  doc["ip_address"]      = WiFi.localIP().toString();
  doc["wifi_rssi"]       = WiFi.RSSI();
  doc["uptime_seconds"]  = (int)(millis() / 1000);
  doc["free_heap_bytes"] = (int)ESP.getFreeHeap();

  String body;
  serializeJson(doc, body);

  HTTPClient http;
  String url = String(SERVER_URL) + "/api/v1/device/check-in";
  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(5000);
  int code = http.POST(body);

  if (code == 200) {
    Serial.printf("[Check-in] OK — RSSI: %d, Heap: %d\n",
      WiFi.RSSI(), ESP.getFreeHeap());
  } else {
    Serial.printf("[Check-in] Failed: HTTP %d\n", code);
  }
  http.end();
}

// ============================================================
// Telemetry Report
// ============================================================
void sendTelemetry() {
  JsonDocument doc;
  doc["device_uid"]      = strlen(DEVICE_UID) > 0 ? DEVICE_UID : deviceMac.c_str();
  doc["api_key"]         = DEVICE_API_KEY;
  doc["firmware_version"] = FIRMWARE_VERSION;
  doc["uptime_seconds"]  = (int)(millis() / 1000);
  doc["free_heap_bytes"] = (int)ESP.getFreeHeap();
  doc["wifi_rssi"]       = WiFi.RSSI();

  String body;
  serializeJson(doc, body);

  HTTPClient http;
  String url = String(SERVER_URL) + "/api/v1/device/telemetry";
  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(5000);
  int code = http.POST(body);
  http.end();

  // Also publish via MQTT
  String uid = strlen(DEVICE_UID) > 0 ? String(DEVICE_UID) : deviceMac;
  String topic = "fleet/devices/" + uid + "/telemetry";
  mqttClient.publish(topic.c_str(), body.c_str());
}

// ============================================================
// MQTT Connection
// ============================================================
void connectMQTT() {
  if (mqttClient.connected()) return;
  if (millis() - lastMqttReconnect < MQTT_RECONNECT_DELAY) return;
  lastMqttReconnect = millis();

  String uid = strlen(DEVICE_UID) > 0 ? String(DEVICE_UID) : deviceMac;
  String clientId = "esp32-" + uid;

  Serial.printf("[MQTT] Connecting to %s:%d as %s...\n",
    MQTT_HOST, MQTT_PORT, clientId.c_str());

  mqttClient.setServer(MQTT_HOST, MQTT_PORT);
  mqttClient.setCallback(mqttCallback);
  mqttClient.setBufferSize(2048);  // Increase for JSON commands

  if (mqttClient.connect(clientId.c_str(), MQTT_USER, MQTT_PASS)) {
    Serial.println("[MQTT] Connected ✓");

    // Subscribe to commands topic
    String cmdTopic = "fleet/devices/" + uid + "/commands";
    mqttClient.subscribe(cmdTopic.c_str(), 1);  // QoS 1
    Serial.printf("[MQTT] Subscribed to: %s\n", cmdTopic.c_str());

    // Publish online status
    String statusTopic = "fleet/devices/" + uid + "/status";
    JsonDocument statusDoc;
    statusDoc["status"] = "online";
    statusDoc["firmware_version"] = FIRMWARE_VERSION;
    statusDoc["ip_address"] = WiFi.localIP().toString();
    String statusBody;
    serializeJson(statusDoc, statusBody);
    mqttClient.publish(statusTopic.c_str(), statusBody.c_str());
  } else {
    Serial.printf("[MQTT] Connection failed, rc=%d\n", mqttClient.state());
  }
}

// ============================================================
// Setup
// ============================================================
void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println();
  Serial.println("╔══════════════════════════════════════════╗");
  Serial.println("║   Smart OTA Fleet Manager — ESP32       ║");
  Serial.println("╚══════════════════════════════════════════╝");
  Serial.printf("Firmware Version: %s\n", FIRMWARE_VERSION);
  Serial.printf("Chip Model: %s\n", ESP.getChipModel());
  Serial.printf("Flash Size: %d KB\n", ESP.getFlashChipSize() / 1024);
  Serial.printf("Free Heap: %d bytes\n", ESP.getFreeHeap());
  Serial.println();

  // Mark current firmware as valid (for rollback support)
  const esp_partition_t* running = esp_ota_get_running_partition();
  if (running) {
    Serial.printf("Running partition: %s (offset 0x%X)\n",
      running->label, running->address);
    // Mark app as valid to prevent automatic rollback
    esp_ota_mark_app_valid_cancel_rollback();
  }

  // Connect WiFi
  if (connectWiFi()) {
    // Initial check-in
    sendCheckin();
    lastCheckin = millis();
  }
}

// ============================================================
// Main Loop
// ============================================================
void loop() {
  // Ensure WiFi is connected
  if (WiFi.status() != WL_CONNECTED) {
    if (!connectWiFi()) {
      delay(WIFI_RECONNECT_DELAY);
      return;
    }
  }

  // Ensure MQTT is connected
  connectMQTT();
  mqttClient.loop();

  unsigned long now = millis();

  // Periodic check-in
  if (now - lastCheckin >= CHECKIN_INTERVAL) {
    lastCheckin = now;
    sendCheckin();
  }

  // Periodic telemetry
  if (now - lastTelemetry >= TELEMETRY_INTERVAL) {
    lastTelemetry = now;
    sendTelemetry();
  }

  delay(10);
}
