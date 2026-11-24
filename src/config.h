#pragma once

// ---------------------------------------------------------------------------
// Pin map. Override any of these with -D PIN_xxx=N in platformio.ini.
// Chosen to avoid strapping, USB and flash pins on each chip.
// ---------------------------------------------------------------------------
#if defined(CONFIG_IDF_TARGET_ESP32C6)
  #ifndef LIGHT_PINS
  #define LIGHT_PINS     17, 1, 16, 18, 22, 23 // tower lights, in order around the ring
  #endif
  #ifndef PIN_VBAT
  #define PIN_VBAT       2    // battery sense via 100k/100k divider (ADC1)
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
  #ifndef PIN_BUTTONS_ADC
  #define PIN_BUTTONS_ADC 0   // TEST / VOL+ / VOL- resistor ladder (ADC1)
  #endif
#elif defined(CONFIG_IDF_TARGET_ESP32C3) && defined(ARDUINO_XIAO_ESP32C3)
  // Seeed XIAO ESP32-C3 on the tower PCB. The PCB is wired by XIAO "D" pin, so
  // this is the XIAO C6 map translated to the C3's GPIO numbers:
  // lights D7, D1, D6, D10, D4, D5; I2S D8, D9, D3; buttons D0; battery D2.
  // D0 (GPIO 2), D8 (GPIO 8) and D9 (GPIO 9) are strapping pins: the button
  // ladder's 10k pull-up holds GPIO 2 high, and the amp's inputs don't load
  // GPIO 8/9. Light 3 (GPIO 21, UART0 TX) blinks once at power-up.
  #ifndef LIGHT_PINS
  #define LIGHT_PINS     20, 3, 21, 10, 6, 7
  #endif
  #ifndef PIN_VBAT
  #define PIN_VBAT       4    // D2, ADC1
  #endif
  #ifndef PIN_I2S_BCLK
  #define PIN_I2S_BCLK   8    // D8
  #endif
  #ifndef PIN_I2S_LRC
  #define PIN_I2S_LRC    9    // D9
  #endif
  #ifndef PIN_I2S_DOUT
  #define PIN_I2S_DOUT   5    // D3
  #endif
  #ifndef PIN_BUTTONS_ADC
  #define PIN_BUTTONS_ADC 2   // D0, ADC1
  #endif
#elif defined(CONFIG_IDF_TARGET_ESP32C3)
  #ifndef LIGHT_PINS
  #define LIGHT_PINS     0, 1, 3, 7, 10, 20
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
  #define PIN_BUTTON     21
  #endif
  #ifndef PIN_VBAT
  #define PIN_VBAT       -1   // no spare ADC pin in this map
  #endif
#else
  #error "Unsupported target: build for esp32c3 or esp32c6"
#endif

// Each light pin drives one channel of a TBD62083A/ULN2803A driver. Up to 6
// lights get smooth PWM fading (both chips have 6 LEDC channels); any extra
// lights fall back to plain on/off. Reorder LIGHT_PINS to match the physical
// order around the tower so the spin goes the right way.
//
// Set to 0 if your driver turns a light on with a LOW signal.
#ifndef LIGHT_ACTIVE_HIGH
#define LIGHT_ACTIVE_HIGH 1
#endif

// Button ladder on PIN_BUTTONS_ADC: 10k pull-up to 3V3, TEST shorts to GND,
// VOL+ through 2.2k (~0.6 V), VOL- through 6.8k (~1.3 V). Thresholds in mV.
#define BTN_TEST_MAX_MV   300
#define BTN_VOLUP_MAX_MV  950
#define BTN_VOLDN_MAX_MV  2000
#define VOLUME_STEP       10

// Battery sense: VBAT -> 100k -> PIN_VBAT -> 100k -> GND (1S Li-ion, max 4.2 V).
#ifndef VBAT_DIVIDER
#define VBAT_DIVIDER 2.0f
#endif
#define VBAT_LOW_MV  3400   // web page warns below this

// ---------------------------------------------------------------------------
// Defaults (all editable later from the web page, stored in flash)
// ---------------------------------------------------------------------------
#define DEFAULT_TEAMS          "COL"   // comma-separated NHL abbreviations
#define DEFAULT_DELAY_S        0       // TV/stream delay before celebrating
#define DEFAULT_DURATION_S     20      // how long the light spins
#define DEFAULT_VOLUME         70      // 0-100
#define DEFAULT_LIVE_POLL_S    5       // poll rate while a favorite is playing
#define DEFAULT_PATTERN        0       // see LightPattern in tower.h
#define DEFAULT_RPM            90      // revolutions per minute of the spin
#define DEFAULT_BRIGHTNESS     80      // max PWM %, keeps the strips' 20 ohm resistors cool

#define HOSTNAME               "goallight"   // http://goallight.local
#define AP_NAME                "GoalLight-Setup"
#define HORN_PATH              "/horn.wav"

#define NHL_SCORE_URL          "https://api-web.nhle.com/v1/score/now"
