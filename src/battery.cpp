#include "battery.h"
#include "config.h"

static uint16_t mv = 0;
static uint32_t nextRead = 0;

// Resting Li-ion voltage vs. charge, roughly.
static const uint16_t CURVE[][2] = {
    {4150, 100}, {4050, 90}, {3970, 80}, {3900, 70}, {3840, 60}, {3790, 50},
    {3750, 40}, {3710, 30}, {3670, 20}, {3600, 10}, {3400, 5}, {3200, 0}};

void batteryLoop() {
  if (PIN_VBAT < 0 || (int32_t)(millis() - nextRead) < 0) return;
  nextRead = millis() + 10000;
  uint32_t sum = 0;
  for (int i = 0; i < 16; i++) sum += analogReadMilliVolts(PIN_VBAT);
  uint16_t now = (uint16_t)(sum / 16 * VBAT_DIVIDER);
  mv = mv ? (mv * 3 + now) / 4 : now;  // smooth out speaker/LED load dips
}

uint16_t batteryMillivolts() { return mv; }

uint8_t batteryPercent() {
  if (!mv) return 0;
  const size_t n = sizeof(CURVE) / sizeof(CURVE[0]);
  if (mv >= CURVE[0][0]) return 100;
  for (size_t i = 1; i < n; i++) {
    if (mv >= CURVE[i][0]) {
      uint16_t v0 = CURVE[i][0], v1 = CURVE[i - 1][0], p0 = CURVE[i][1], p1 = CURVE[i - 1][1];
      return p0 + (uint32_t)(mv - v0) * (p1 - p0) / (v1 - v0);
    }
  }
  return 0;
}
