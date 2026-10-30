#pragma once
#include <Arduino.h>

struct Settings {
  String teams;          // "COL,BOS"
  uint16_t delayS;
  uint16_t durationS;
  uint8_t volume;        // 0-100
  uint8_t livePollS;
  bool sound;            // false = light only
  uint8_t pattern;       // LightPattern
  uint8_t rpm;           // spin speed

  bool isFavorite(const String &abbrev) const;
};

extern Settings settings;

void settingsLoad();
void settingsSave();
