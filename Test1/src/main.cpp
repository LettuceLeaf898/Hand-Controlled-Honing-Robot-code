#include <Arduino.h>
#include <Wire.h>
#include "SparkFun_BNO080_Arduino_Library.h"
#include <WiFi.h>
#include <WiFiClient.h>
#include <WebServer.h>
#include <ElegantOTA.h>

// --- WiFi Credentials ---
const char* ssid = "piHotspot";
const char* eap_password = "empanada";

// --- Pi Socket ---
const char* PI_IP   = "10.42.0.1";
const uint16_t PI_PORT = 5001;

// --- Global Objects ---
BNO080 bno;
WebServer server(80);
WiFiClient piClient;

// --- Cached Sensor Data ---
float roll = 0, pitch = 0, yaw = 0;
float yawRef = 0;
bool yawInitialized = false;
int mode = 0;
String lastCmd = "";

unsigned long ota_progress_millis = 0;
unsigned long lastSendMillis = 0;
const unsigned long SEND_INTERVAL = 100;
unsigned long lastWifiReconnectAttempt = 0;
const unsigned long WIFI_RECONNECT_INTERVAL = 5000;
unsigned long lastPiReconnectAttempt = 0;
const unsigned long PI_RECONNECT_INTERVAL = 2000;

String wifiStatusToString(wl_status_t status) {
  switch (status) {
    case WL_NO_SHIELD:       return "NO_SHIELD";
    case WL_IDLE_STATUS:     return "IDLE";
    case WL_NO_SSID_AVAIL:   return "NO_SSID";
    case WL_SCAN_COMPLETED:  return "SCAN_DONE";
    case WL_CONNECTED:       return "CONNECTED";
    case WL_CONNECT_FAILED:  return "CONNECT_FAILED";
    case WL_CONNECTION_LOST: return "CONNECTION_LOST";
    case WL_DISCONNECTED:    return "DISCONNECTED";
    default:                 return "UNKNOWN";
  }
}

bool connectToWiFi(unsigned long timeoutMs = 30000) {
  Serial.printf("Connecting to SSID: \"%s\"\n", ssid);
  WiFi.begin(ssid, eap_password);

  unsigned long startAttemptTime = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - startAttemptTime < timeoutMs) {
    delay(500);
    wl_status_t s = WiFi.status();
    if (s == WL_NO_SSID_AVAIL) {
      Serial.printf("  Status: NO_SSID (target \"%s\" disappeared after scan)\n", ssid);
    } else if (s == WL_CONNECT_FAILED) {
      Serial.printf("  Status: CONNECT_FAILED (bad password for \"%s\"?)\n", ssid);
    } else {
      Serial.printf("  Status: %s\n", wifiStatusToString(s).c_str());
    }
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("WiFi connected! IP: %s\n", WiFi.localIP().toString().c_str());
    return true;
  }

  Serial.printf("WiFi connect failed. Final status: %s\n", wifiStatusToString(WiFi.status()).c_str());
  return false;
}

// --- OTA Callbacks ---
void onOTAStart() {
  Serial.println("OTA update started!");
}

void onOTAProgress(size_t current, size_t final) {
  if (millis() - ota_progress_millis > 1000) {
    ota_progress_millis = millis();
    Serial.printf("OTA Progress Current: %u bytes, Final: %u bytes\n", current, final);
  }
}

void onOTAEnd(bool success) {
  if (success) {
    Serial.println("OTA update finished successfully!");
  } else {
    Serial.println("There was an error during OTA update!");
  }
}

void setup() {
  Serial.begin(115200);
  Wire.begin();

  // 1. Initialize Sensor
  if (!bno.begin()) {
    Serial.println("BNO080 not detected. Check wiring!");
    while (1);
  }
  Serial.println("BNO08x connected!");
  bno.enableRotationVector(50);

  // 2. Initialize WiFi
  // Note: avoid WIFI_OFF -> WIFI_STA transition, it causes Error 263
  // (ESP_ERR_WIFI_NOT_STARTED) on some Arduino core versions
  WiFi.mode(WIFI_STA);
  WiFi.persistent(false);
  WiFi.setAutoReconnect(true);
  WiFi.disconnect(false);
  delay(1000);
  WiFi.setSleep(false);

  Serial.printf("ESP32 MAC: %s\n", WiFi.macAddress().c_str());

  // Static IP to bypass DHCP timing issues
  IPAddress local_IP(10, 42, 0, 200);
  IPAddress gateway(10, 42, 0, 1);
  IPAddress subnet(255, 255, 255, 0);
  IPAddress dns(10, 42, 0, 1);
  if (!WiFi.config(local_IP, gateway, subnet, dns)) {
    Serial.println("Static IP config failed!");
  }

  connectToWiFi();

  // 3. Initialize Web Server and OTA
  server.on("/", []() {
    server.send(200, "text/plain", "ESP32 Sensor Node & OTA Ready.");
  });

  server.on("/data", []() {
    String json = "{\"roll\":" + String(roll) + ",\"pitch\":" + String(pitch) + ",\"yaw\":" + String(yaw) + "}";
    server.send(200, "application/json", json);
  });

  ElegantOTA.begin(&server);
  server.begin();
}

String getCommand() {
  if (pitch > 20)       return "F";
  else if (pitch < -20) return "B";
  else if (roll > 20)   return "R";
  else if (roll < -20)  return "L";
  else {
    float delta = yaw - yawRef;
    if (delta > 20 || delta < -20) return "C";
    return "S";
  }
}

void loop() {
  // 1. Keep the OTA web server running and listening
  server.handleClient();
  ElegantOTA.loop();

  // Reconnect to WiFi automatically if hotspot drops
  if (WiFi.status() != WL_CONNECTED) {
    if (piClient.connected()) {
      piClient.stop();
    }
    if (millis() - lastWifiReconnectAttempt >= WIFI_RECONNECT_INTERVAL) {
      lastWifiReconnectAttempt = millis();
      Serial.printf("WiFi lost (%s). Reconnecting...\n", wifiStatusToString(WiFi.status()).c_str());
      connectToWiFi(10000);
    }
    delay(50);
    return;
  }

  // 2. Update cached sensor data
  if (bno.dataAvailable()) {
    roll  = bno.getRoll()  * 180.0 / PI;
    pitch = bno.getPitch() * 180.0 / PI;
    yaw   = bno.getYaw()   * 180.0 / PI;
    if (!yawInitialized) {
      yawRef = yaw;
      yawInitialized = true;
    }
    Serial.printf("Roll: %.1f  Pitch: %.1f  Yaw: %.1f  YawRef: %.1f\n", roll, pitch, yaw, yawRef);
  }

  // Keep trying Pi socket connection even when command doesn't change
  if (!piClient.connected() && millis() - lastPiReconnectAttempt >= PI_RECONNECT_INTERVAL) {
    lastPiReconnectAttempt = millis();
    Serial.printf("Connecting to Pi %s:%u ...\n", PI_IP, PI_PORT);
    if (piClient.connect(PI_IP, PI_PORT)) {
      Serial.println("Pi socket connected.");
    } else {
      Serial.println("Pi socket connect failed.");
    }
  }

  // 3. Send command to Pi
  String cmd = getCommand();

  // In mode 1, ignore all commands except C
  if (mode == 1 && cmd != "C") cmd = "S";

  // Toggle mode when C is detected
  if (cmd == "C" && cmd != lastCmd) {
    mode = (mode == 0) ? 1 : 0;
    Serial.printf("Mode switched to %d\n", mode);
  }

  bool directionChanged = (cmd != lastCmd);
  bool shouldSend = directionChanged || (cmd != "S" && cmd != "C" && millis() - lastSendMillis >= SEND_INTERVAL);

  if (shouldSend && piClient.connected()) {
    piClient.println(cmd);
    lastCmd = cmd;
    lastSendMillis = millis();
    Serial.println("Sent: " + cmd);
  }
}