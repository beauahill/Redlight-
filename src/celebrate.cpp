#include "celebrate.h"
#include <ESP_I2S.h>
#include <LittleFS.h>
#include "config.h"
#include "settings.h"
#include "tower.h"

static I2SClass i2s;
static TaskHandle_t audioTask = nullptr;
static volatile bool stopAudio = false;
static volatile bool audioPlaying = false;
static volatile bool beepPending = false;
// Perceptual volume curve, returns a Q15 gain.
static int32_t gainQ15() {
  int32_t v = settings.volume;
  return (v * v * 32768) / 10000;
}

static bool i2sStart(uint32_t rate) {
  i2s.setPins(PIN_I2S_BCLK, PIN_I2S_LRC, PIN_I2S_DOUT);
  // Always stereo: the MAX98357A mixes (L+R)/2 by default, so duplicating
  // mono samples into both slots gives full volume regardless of its SD pin.
  return i2s.begin(I2S_MODE_STD, rate, I2S_DATA_BIT_WIDTH_16BIT, I2S_SLOT_MODE_STEREO);
}

// Write mono samples as stereo frames with volume applied.
static void writeMono(const int16_t *in, size_t n, int32_t gain) {
  int16_t out[256 * 2];
  while (n) {
    size_t chunk = n > 256 ? 256 : n;
    for (size_t i = 0; i < chunk; i++) {
      int16_t s = (int16_t)(((int32_t)in[i] * gain) >> 15);
      out[2 * i] = s;
      out[2 * i + 1] = s;
    }
    i2s.write((uint8_t *)out, chunk * 4);
    in += chunk;
    n -= chunk;
  }
}

// Plays a 16-bit PCM WAV (mono or stereo, any sample rate).
static bool playWav(const char *path) {
  File f = LittleFS.open(path, "r");
  if (!f) return false;

  uint8_t hdr[12];
  if (f.read(hdr, 12) != 12 || memcmp(hdr, "RIFF", 4) || memcmp(hdr + 8, "WAVE", 4)) {
    Serial.println("[audio] not a WAV file");
    return false;
  }

  uint16_t channels = 0, bits = 0;
  uint32_t rate = 0, dataLen = 0;
  while (f.available()) {
    uint8_t ch[8];
    if (f.read(ch, 8) != 8) break;
    uint32_t len = ch[4] | (ch[5] << 8) | (ch[6] << 16) | ((uint32_t)ch[7] << 24);
    if (!memcmp(ch, "fmt ", 4)) {
      uint8_t fmt[16];
      f.read(fmt, 16);
      uint16_t format = fmt[0] | (fmt[1] << 8);
      channels = fmt[2] | (fmt[3] << 8);
      rate = fmt[4] | (fmt[5] << 8) | (fmt[6] << 16) | ((uint32_t)fmt[7] << 24);
      bits = fmt[14] | (fmt[15] << 8);
      if (format != 1) {
        Serial.println("[audio] WAV must be uncompressed PCM");
        return false;
      }
      f.seek(len - 16 + (len & 1), SeekCur);
    } else if (!memcmp(ch, "data", 4)) {
      dataLen = len;
      break;
    } else {
      f.seek(len + (len & 1), SeekCur);
    }
  }

  if (bits != 16 || channels < 1 || channels > 2 || !rate || !dataLen) {
    Serial.printf("[audio] unsupported WAV (%u ch, %u bit, %lu Hz)\n", channels, bits, rate);
    return false;
  }
  if (!i2sStart(rate)) return false;

  Serial.printf("[audio] playing %s: %lu Hz, %u ch, %lu bytes\n", path, rate, channels, dataLen);
  int16_t buf[512];
  int32_t gain = gainQ15();
  while (dataLen && !stopAudio) {
    size_t want = dataLen > sizeof(buf) ? sizeof(buf) : dataLen;
    size_t got = f.read((uint8_t *)buf, want);
    if (!got) break;
    dataLen -= got;
    size_t samples = got / 2;
    if (channels == 2) {
      // Downmix to mono so volume scaling stays in one place.
      for (size_t i = 0; i < samples / 2; i++) buf[i] = ((int32_t)buf[2 * i] + buf[2 * i + 1]) / 2;
      samples /= 2;
    }
    writeMono(buf, samples, gain);
  }
  i2s.end();
  return true;
}

// Fallback when no horn.wav is uploaded: a two-tone goal horn blast followed
// by a rising/falling siren wail, until the celebration ends.
static void playSynth(uint32_t durationMs) {
  const uint32_t rate = 22050;
  if (!i2sStart(rate)) return;
  int32_t gain = gainQ15();
  int16_t buf[256];
  float p1 = 0, p2 = 0;
  uint32_t total = (uint64_t)durationMs * rate / 1000, n = 0;
  const uint32_t hornLen = rate * 3;

  while (n < total && !stopAudio) {
    for (int i = 0; i < 256; i++, n++) {
      float s;
      if (n < hornLen) {
        // Low brassy horn: two detuned sawtooths around 160 Hz.
        p1 += 160.0f / rate; if (p1 >= 1) p1 -= 1;
        p2 += 202.0f / rate; if (p2 >= 1) p2 -= 1;
        s = (p1 * 2 - 1) * 0.5f + (p2 * 2 - 1) * 0.5f;
      } else {
        // Siren: 2 s up/down sweep between 500 and 1300 Hz, square-ish.
        float t = (float)((n - hornLen) % (rate * 2)) / (rate * 2);
        float tri = t < 0.5f ? t * 2 : 2 - t * 2;
        p1 += (500.0f + 800.0f * tri) / rate; if (p1 >= 1) p1 -= 1;
        s = p1 < 0.5f ? 0.6f : -0.6f;
      }
      buf[i] = (int16_t)(s * 20000);
    }
    writeMono(buf, 256, gain);
  }
  i2s.end();
}

static void playBeep() {
  const uint32_t rate = 22050, len = rate / 8;  // 125 ms at 1 kHz
  if (!i2sStart(rate)) return;
  int32_t gain = gainQ15();
  int16_t buf[256];
  for (uint32_t n = 0; n < len;) {
    for (int i = 0; i < 256; i++, n++) buf[i] = ((n * 2000 / rate) & 1) ? 12000 : -12000;
    writeMono(buf, 256, gain);
  }
  i2s.end();
}

static void audioTaskFn(void *) {
  for (;;) {
    ulTaskNotifyTake(pdTRUE, portMAX_DELAY);
    if (beepPending) {
      beepPending = false;
      playBeep();
      continue;
    }
    stopAudio = false;
    audioPlaying = true;
    if (!playWav(HORN_PATH)) playSynth(settings.durationS * 1000UL);
    audioPlaying = false;
  }
}

void celebrateBegin() {
  towerBegin();
  if (!LittleFS.begin(true)) Serial.println("[fs] LittleFS mount failed");
  xTaskCreate(audioTaskFn, "audio", 6144, nullptr, 5, &audioTask);
}

void celebrateStart(const String &reason) {
  Serial.printf("[goal] %s\n", reason.c_str());
  towerRun(settings.durationS * 1000UL);
  if (settings.sound && settings.volume > 0 && !audioPlaying) xTaskNotifyGive(audioTask);
}

void celebrateBeep() {
  if (audioPlaying || settings.volume == 0) return;
  beepPending = true;
  xTaskNotifyGive(audioTask);
}

void celebrateStop() {
  towerStop();
  stopAudio = true;
}

bool celebrateActive() { return towerActive() || audioPlaying; }

bool hornFilePresent() { return LittleFS.exists(HORN_PATH); }
