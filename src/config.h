#pragma once

// ---------------------------------------------------------------------------
// Pin map. Override any of these with -D PIN_xxx=N in platformio.ini.
// Chosen to avoid strapping, USB and flash pins on each chip.
// ---------------------------------------------------------------------------
#if defined(CONFIG_IDF_TARGET_ESP32C6)
  #ifndef PIN_LIGHT
  #define PIN_LIGHT      18   // gate of the MOSFET that switches the light tower
  #endif
  #ifndef PIN_I2S_BCLK
  #define PIN_I2S_BCLK   19   // MAX98357A BCLK
  #endif
  #ifndef PIN_I2S_LRC
  #define PIN_I2S_LRC    20   // MAX98357A LRC / WS
  #endif
  #ifndef PIN_I2S_DOUT
  #define PIN_I2S_DOUT   21   // MAX98357A DIN
  #endif
  #ifndef PIN_BUTTON
  #define PIN_BUTTON     22   // momentary button to GND (optional)
  #endif
#elif defined(CONFIG_IDF_TARGET_ESP32C3)
  #ifndef PIN_LIGHT
  #define PIN_LIGHT      3
  #endif
  #ifndef PIN_I2S_BCLK
  #define PIN_I2S_BCLK   4
  #endif
  #ifndef PIN_I2S_LRC
  #define PIN_I2S_LRC    5
  #endif
  #ifndef PIN_I2S_DOUT
  #define PIN_I2S_DOUT   6
  #endif
  #ifndef PIN_BUTTON
  #define PIN_BUTTON     7
  #endif
#else
  #error "Unsupported target: build for esp32c3 or esp32c6"
#endif

// Set to 0 if your driver turns the light on with a LOW signal.
#ifndef LIGHT_ACTIVE_HIGH
#define LIGHT_ACTIVE_HIGH 1
#endif

// ---------------------------------------------------------------------------
// Defaults (all editable later from the web page, stored in flash)
// ---------------------------------------------------------------------------
#define DEFAULT_TEAMS          "COL"   // comma-separated NHL abbreviations
#define DEFAULT_DELAY_S        0       // TV/stream delay before celebrating
#define DEFAULT_DURATION_S     20      // how long the light spins
#define DEFAULT_VOLUME         70      // 0-100
#define DEFAULT_LIVE_POLL_S    5       // poll rate while a favorite is playing

#define HOSTNAME               "goallight"   // http://goallight.local
#define AP_NAME                "GoalLight-Setup"
#define HORN_PATH              "/horn.wav"

#define NHL_SCORE_URL          "https://api-web.nhle.com/v1/score/now"
