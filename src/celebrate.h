#pragma once
#include <Arduino.h>

// Light tower + horn. Call celebrateBegin() once, celebrateLoop() every loop.
void celebrateBegin();
void celebrateLoop();
void celebrateStart(const String &reason);
void celebrateStop();
bool celebrateActive();
bool hornFilePresent();
