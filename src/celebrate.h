#pragma once
#include <Arduino.h>

// Light tower + horn. Call celebrateBegin() once.
void celebrateBegin();
void celebrateStart(const String &reason);
void celebrateStop();
void celebrateBeep();   // short tone at the current volume
bool celebrateActive();
bool hornFilePresent();
