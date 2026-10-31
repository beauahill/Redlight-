#include "buttons.h"
#include <Arduino.h>
#include <WiFiManager.h>
#include "celebrate.h"
#include "config.h"
#include "settings.h"

enum Button { BTN_NONE, BTN_TEST, BTN_VOL_UP, BTN_VOL_DOWN };

static Button readRaw() {
#ifdef PIN_BUTTONS_ADC
  uint32_t mv = analogReadMilliVolts(PIN_BUTTONS_ADC);
  if (mv < BTN_TEST_MAX_MV) return BTN_TEST;
  if (mv < BTN_VOLUP_MAX_MV) return BTN_VOL_UP;
  if (mv < BTN_VOLDN_MAX_MV) return BTN_VOL_DOWN;
  return BTN_NONE;
#else
  return digitalRead(PIN_BUTTON) == LOW ? BTN_TEST : BTN_NONE;
#endif
}

static void changeVolume(int delta) {
  settings.volume = constrain((int)settings.volume + delta, 0, 100);
  settingsSave();
  Serial.printf("[btn] volume %u\n", settings.volume);
  celebrateBeep();
}

void buttonsBegin() {
#ifndef PIN_BUTTONS_ADC
  pinMode(PIN_BUTTON, INPUT_PULLUP);
#endif
}

void buttonsLoop() {
  static Button stable = BTN_NONE, last = BTN_NONE;
  static uint32_t changedAt = 0, pressedAt = 0;

  Button now = readRaw();
  if (now != last) {
    last = now;
    changedAt = millis();
    return;
  }
  if (now == stable || millis() - changedAt < 30) return;  // debounce

  Button released = stable;
  stable = now;
  if (stable != BTN_NONE) {
    pressedAt = millis();
    if (stable == BTN_VOL_UP) changeVolume(VOLUME_STEP);
    if (stable == BTN_VOL_DOWN) changeVolume(-VOLUME_STEP);
    return;
  }

  if (released == BTN_TEST) {
    if (millis() - pressedAt > 10000) {
      Serial.println("[btn] resetting WiFi");
      WiFiManager wm;
      wm.resetSettings();
      ESP.restart();
    } else if (celebrateActive()) {
      celebrateStop();
    } else {
      celebrateStart("button test");
    }
  }
}
