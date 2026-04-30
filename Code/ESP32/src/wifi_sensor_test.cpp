#include <Arduino.h>
#include <Wire.h>
#include "SparkFun_BNO080_Arduino_Library.h"
#include <WiFi.h>

const char* ssid     = "Accolade"; // or "eduroam"
const char* password = "CrossPhloxIguana";         // Your university password

BNO080 bno;

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n--- WiFi + Sensor Test ---");

  // 1. Sensor
  Wire.begin();
  if (!bno.begin()) {
    Serial.println("BNO080 not detected. Check wiring!");
  } else {
    Serial.println("BNO080 connected!");
    bno.enableRotationVector(50);
  }

  // 2. WiFi
  WiFi.disconnect(true);
  delay(500);
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);

  Serial.print("Connecting to WiFi");
  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < 30000) {
    delay(500);
    Serial.print(".");
    Serial.print(" [");
    Serial.print(WiFi.status());
    Serial.print("]");
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi connected!");
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());
    Serial.print("Signal strength (RSSI): ");
    Serial.print(WiFi.RSSI());
    Serial.println(" dBm");
  } else {
    Serial.println("\nFailed to connect.");
    Serial.print("Final WiFi status code: ");
    Serial.println(WiFi.status());
    Serial.println("Status codes: 0=IDLE, 1=NO_SSID, 3=CONNECTED, 4=CONNECT_FAILED, 6=DISCONNECTED, 255=NO_SHIELD");
  }
}

void loop() {
  if (bno.dataAvailable()) {
    float roll  = bno.getRoll()  * 180.0 / PI;
    float pitch = bno.getPitch() * 180.0 / PI;
    float yaw   = bno.getYaw()   * 180.0 / PI;
    Serial.printf("Roll: %.1f  Pitch: %.1f  Yaw: %.1f\n", roll, pitch, yaw);
  }
  delay(200);
}
