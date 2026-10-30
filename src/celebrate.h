#pragma once
#include <Arduino.h>

// Light tower + horn. Call celebrateBegin() once.
void celebrateBegin();
void celebrateStart(const String &reason);
void celebrateStop();
bool celebrateActive();
bool hornFilePresent();
