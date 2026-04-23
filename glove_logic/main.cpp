#include <Arduino.h>
#include <Wire.h>
#include "SparkFun_BNO080_Arduino_Library.h"
#include <WiFi.h>
#include <WiFiClient.h>
#include <WebServer.h>
#include <ElegantOTA.h>

// --- WiFi Credentials ---
//const char* ssid = "JoshuaiPhone"; // or "eduroam"
//const char* eap_password = "123456789";         // Your university password
const char* ssid = "JoshuaiPhone"; // or "eduroam"
const char* eap_password = "123456789";         // Your university password

// --- Pi Socket ---
const char* PI_IP   = "100.70.33.84";
const uint16_t PI_PORT = 5000;

// --- Global Objects ---
BNO080 bno;
WebServer server(80);
WiFiClient piClient;

// --- Cached Sensor Data ---
float roll = 0, pitch = 0, yaw = 0;
String lastCmd = "";

unsigned long ota_progress_millis = 0;

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

  // 2. Initialize WiFi - Simplified for Hotspot
  WiFi.disconnect(true); // Clear any old saved university settings
  delay(1000);
  WiFi.mode(WIFI_STA);
  
  // Use the standard begin for a phone hotspot
  WiFi.begin(ssid, eap_password); 

  Serial.print("Connecting to Hotspot");
  
  // Timeout after 30 seconds so it doesn't loop forever
  unsigned long startAttemptTime = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - startAttemptTime < 30000) {
    delay(500);
    Serial.print(".");
  }
  
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("\nFailed to connect. Check 'Maximize Compatibility' on iPhone.");
  } else {
    Serial.println("\nConnected!");
    Serial.print("IP: ");
    Serial.println(WiFi.localIP());
  }

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
  else                  return "S";
}

void loop() {
  // 1. Keep the OTA web server running and listening
  server.handleClient();
  ElegantOTA.loop();

  // 2. Update cached sensor data
  if (bno.dataAvailable()) {
    roll  = bno.getRoll()  * 180.0 / PI;
    pitch = bno.getPitch() * 180.0 / PI;
    yaw   = bno.getYaw()   * 180.0 / PI;
  }

  // 3. Send command to Pi if it changed
  String cmd = getCommand();
  if (cmd != lastCmd) {
    lastCmd = cmd;
    if (!piClient.connected()) {
      piClient.connect(PI_IP, PI_PORT);
    }
    if (piClient.connected()) {
      piClient.println(cmd);
      Serial.println("Sent: " + cmd);
    }
  }
}
