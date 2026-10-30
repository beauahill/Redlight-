#include "tower.h"
#include <math.h>
#include "config.h"
#include "settings.h"

const char *const PATTERN_NAMES[PATTERN_COUNT] = {"Spin", "Chase", "Strobe", "Alternate"};

static const uint8_t PINS[] = {LIGHT_PINS};
static const uint8_t COUNT = sizeof(PINS) / sizeof(PINS[0]);
static bool pwm[COUNT];
static volatile uint32_t offAt = 0;
static volatile bool running = false;
static TaskHandle_t task = nullptr;

// level: 0.0 (off) .. 1.0 (full)
static void setLevel(uint8_t i, float level) {
  if (pwm[i]) {
    // Square the level so the fade looks linear to the eye.
    uint32_t duty = (uint32_t)(level * level * 255.0f + 0.5f);
    ledcWrite(PINS[i], LIGHT_ACTIVE_HIGH ? duty : 255 - duty);
  } else {
    bool on = level >= 0.5f;
    digitalWrite(PINS[i], on == LIGHT_ACTIVE_HIGH ? HIGH : LOW);
  }
}

static void allOff() {
  for (uint8_t i = 0; i < COUNT; i++) setLevel(i, 0);
}

static void frame(uint32_t t) {
  uint8_t rpm = settings.rpm ? settings.rpm : 1;
  uint32_t revMs = 60000UL / rpm;
  float phase = (float)(t % revMs) / revMs;   // 0..1 around the ring

  switch (settings.pattern) {
    case PATTERN_SPIN:
    default: {
      // Bright head with a tail about 1.5 lights long behind it.
      float head = phase * COUNT;
      for (uint8_t i = 0; i < COUNT; i++) {
        float behind = fmodf(head - i + COUNT, COUNT);
        float level = behind < 1.0f ? 1.0f : fmaxf(0.0f, 1.0f - (behind - 1.0f) / 1.5f);
        setLevel(i, level);
      }
      break;
    }
    case PATTERN_CHASE: {
      uint8_t on = (uint8_t)(phase * COUNT) % COUNT;
      for (uint8_t i = 0; i < COUNT; i++) setLevel(i, i == on ? 1 : 0);
      break;
    }
    case PATTERN_STROBE: {
      // Short bursts: on for the first 25% of each flash period.
      uint32_t periodMs = revMs / 2;
      bool on = (t % periodMs) < periodMs / 4;
      for (uint8_t i = 0; i < COUNT; i++) setLevel(i, on);
      break;
    }
    case PATTERN_ALTERNATE: {
      bool odd = phase >= 0.5f;
      for (uint8_t i = 0; i < COUNT; i++) setLevel(i, (i & 1) == odd);
      break;
    }
  }
}

static void towerTask(void *) {
  for (;;) {
    ulTaskNotifyTake(pdTRUE, portMAX_DELAY);
    uint32_t start = millis();
    while (running && (int32_t)(millis() - offAt) < 0) {
      frame(millis() - start);
      vTaskDelay(pdMS_TO_TICKS(5));
    }
    running = false;
    allOff();
  }
}

void towerBegin() {
  for (uint8_t i = 0; i < COUNT; i++) {
    pinMode(PINS[i], OUTPUT);
    pwm[i] = ledcAttach(PINS[i], 1000, 8);
    if (!pwm[i]) Serial.printf("[tower] no PWM channel for GPIO %u, using on/off\n", PINS[i]);
  }
  allOff();
  xTaskCreate(towerTask, "tower", 3072, nullptr, 4, &task);
  Serial.printf("[tower] %u lights\n", COUNT);
}

void towerRun(uint32_t durationMs) {
  offAt = millis() + durationMs;
  if (!running) {
    running = true;
    xTaskNotifyGive(task);
  }
}

void towerStop() { running = false; }
bool towerActive() { return running; }
uint8_t towerLightCount() { return COUNT; }
