#pragma once
#include <Arduino.h>

// Single-cell (1S) Li-ion pack monitor. Reports 0 when PIN_VBAT is unused.
void batteryLoop();
uint16_t batteryMillivolts();
uint8_t batteryPercent();
