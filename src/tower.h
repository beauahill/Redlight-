#pragma once
#include <Arduino.h>

// The light tower: a ring of individually driven lights animated in their
// own task so network polling never stalls the spin.
enum LightPattern : uint8_t {
  PATTERN_SPIN = 0,    // smooth rotating beacon with a fading tail
  PATTERN_CHASE,       // one light at a time, hard steps
  PATTERN_STROBE,      // all lights flash together
  PATTERN_ALTERNATE,   // odd/even lights swap
  PATTERN_COUNT
};

extern const char *const PATTERN_NAMES[PATTERN_COUNT];

void towerBegin();
void towerRun(uint32_t durationMs);   // start (or extend) the animation
void towerStop();
bool towerActive();
uint8_t towerLightCount();
