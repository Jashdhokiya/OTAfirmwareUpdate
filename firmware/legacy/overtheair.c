#include <WiFi.h>
#include <WiFiClient.h>
#include <HTTPClient.h>
#include <HTTPUpdate.h>

// ========================================
// 1. Wi-Fi Configuration
// ========================================
const char* WIFI_SSID = "Jash's OnePlus Nord 5";
const char* WIFI_PASSWORD = "jash1234";

// ========================================
// 2. Firmware Server Configuration
// ========================================
// Replace with your laptop's actual IPv4 address.
// Find it using: ipconfig
const char* SERVER_IP = "172.22.143.14";
const int SERVER_PORT = 8000;

// ========================================
// 3. Current Firmware Version
// ========================================
#define VER 3

// Check for updates every 30 seconds
const unsigned long CHECK_INTERVAL = 30000;

unsigned long lastCheck = 0;
String deviceID;

// ========================================
// Get the server base URL
// ========================================
String getServerBase() {
  return String("http://") + SERVER_IP + ":" +
         String(SERVER_PORT);
}

// ========================================
// Connect to Wi-Fi
// ========================================
bool connectWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  Serial.print("Connecting to Wi-Fi");

  unsigned long startTime = millis();

  while (WiFi.status() != WL_CONNECTED &&
         millis() - startTime < 20000) {
    delay(500);
    Serial.print(".");
  }

  Serial.println();

  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("Wi-Fi connection failed!");
    return false;
  }

  Serial.println("Wi-Fi connected");
  Serial.print("ESP32 IP address: ");
  Serial.println(WiFi.localIP());

  // Read MAC only after Wi-Fi initialization.
  deviceID = WiFi.macAddress();
  deviceID.replace(":", "");
  deviceID.toUpperCase();

  Serial.print("Device ID: ");
  Serial.println(deviceID);

  return true;
}

// ========================================
// Check and install firmware update
// ========================================
void checkForUpdate() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("Wi-Fi disconnected. Reconnecting...");

    if (!connectWiFi()) {
      return;
    }
  }

  String folderURL =
      getServerBase() + "/" + deviceID;

  String versionURL =
      folderURL + "/version.txt";

  String firmwareURL =
      folderURL + "/firmware.bin";

  Serial.println();
  Serial.println("Checking for firmware update...");
  Serial.println("Version URL: " + versionURL);

  // --------------------------------------
  // Request the version file
  // --------------------------------------
  WiFiClient client;
  HTTPClient http;

  http.setConnectTimeout(5000);
  http.setTimeout(5000);

  if (!http.begin(client, versionURL)) {
    Serial.println("Could not initialize HTTP request.");
    return;
  }

  int httpCode = http.GET();

  if (httpCode != HTTP_CODE_OK) {
    Serial.printf(
        "Version request failed. HTTP result: %d\n",
        httpCode
    );

    http.end();
    return;
  }

  String versionText = http.getString();
  versionText.trim();

  http.end();

  // Reject an invalid version file.
  if (versionText.length() == 0) {
    Serial.println("version.txt is empty.");
    return;
  }

  for (unsigned int i = 0;
       i < versionText.length(); i++) {
    if (!isDigit(versionText[i])) {
      Serial.println("Invalid version.txt contents.");
      return;
    }
  }

  int availableVersion = versionText.toInt();

  Serial.printf("Installed version: %d\n", VER);
  Serial.printf("Server version: %d\n", availableVersion);

  // --------------------------------------
  // Compare versions
  // --------------------------------------
  if (availableVersion <= VER) {
    Serial.println("No update needed.");
    return;
  }

  Serial.println("New firmware available!");
  Serial.println("Downloading firmware...");
  Serial.println(firmwareURL);

  // --------------------------------------
  // Download and install firmware
  // --------------------------------------
  WiFiClient updateClient;

  httpUpdate.rebootOnUpdate(false);
  httpUpdate.setFollowRedirects(
      HTTPC_FORCE_FOLLOW_REDIRECTS
  );

  t_httpUpdate_return result =
      httpUpdate.update(updateClient, firmwareURL);

  if (result == HTTP_UPDATE_OK) {
    Serial.println("Firmware installed successfully.");
    Serial.println("Restarting ESP32...");

    delay(1000);
    ESP.restart();
  }
  else if (result == HTTP_UPDATE_NO_UPDATES) {
    Serial.println("No update was installed.");
  }
  else {
    Serial.printf(
        "Firmware update failed: %s\n",
        httpUpdate.getLastErrorString().c_str()
    );
  }
}

// ========================================
// Setup
// ========================================
void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println();
  Serial.println("================================");
  Serial.println("       ESP32 OTA SYSTEM");
  Serial.println("================================");

  Serial.printf("Firmware version: %d\n", VER);

  if (connectWiFi()) {
    checkForUpdate();
    lastCheck = millis();
  }
}

// ========================================
// Main loop
// ========================================
void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    if (!connectWiFi()) {
      delay(2000);
      return;
    }

    // Check for updates immediately after reconnecting.
    checkForUpdate();
    lastCheck = millis();
    return;
  }

  if (millis() - lastCheck >= CHECK_INTERVAL) {
    lastCheck = millis();
    checkForUpdate();
  }

  delay(10);
}