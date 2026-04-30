#include <Arduino.h>

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("ESP32 booted successfully");
}

void loop() {
  Serial.println("Still running...");
  delay(1000);
}