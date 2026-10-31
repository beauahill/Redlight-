// Redlight: ESP32-C3/C6 goal light for a repurposed light-tower housing.
// Spins the light and plays a horn when a favorite NHL team scores.

#include <Arduino.h>
#include <ESPmDNS.h>
#include <WiFi.h>
#include <WiFiManager.h>
#include "battery.h"
#include "buttons.h"
#include "celebrate.h"
#include "config.h"
#include "nhl.h"
#include "settings.h"
#include "web.h"

void setup() {
  Serial.begin(115200);
  delay(200);
  Serial.println("\n[boot] Redlight goal light");

  buttonsBegin();
  settingsLoad();
  celebrateBegin();

  // First boot (or after reset): join the "GoalLight-Setup" WiFi from a phone
  // and pick your network. Afterwards it reconnects automatically.
  WiFi.setHostname(HOSTNAME);
  WiFiManager wm;
  wm.setConfigPortalTimeout(300);
  if (!wm.autoConnect(AP_NAME)) {
    Serial.println("[wifi] setup timed out, rebooting");
    ESP.restart();
  }
  WiFi.setAutoReconnect(true);
  Serial.printf("[wifi] connected, IP %s\n", WiFi.localIP().toString().c_str());

  if (MDNS.begin(HOSTNAME)) MDNS.addService("http", "tcp", 80);
  webBegin();
  Serial.printf("[web] open http://%s.local or http://%s\n", HOSTNAME,
                WiFi.localIP().toString().c_str());
}

void loop() {
  webLoop();
  buttonsLoop();
  nhlLoop();
  batteryLoop();
  delay(5);
}
