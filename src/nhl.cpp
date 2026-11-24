#include "nhl.h"
#include <ArduinoJson.h>
#include <HTTPClient.h>
#include <NetworkClientSecure.h>
#include <WiFi.h>
#include <map>
#include "celebrate.h"
#include "config.h"
#include "settings.h"

// Last seen score for each favorite team, keyed by game id + home/away side.
static std::map<uint64_t, int> knownScores;
static std::vector<GameView> favGames;
static std::vector<uint32_t> pendingAt;   // millis() when a delayed goal fires
static std::vector<String> pendingWho;
static String lastError = "not polled yet";
static uint32_t lastPoll = 0, nextPoll = 0;

// "score/now" answers with a redirect to the current date's feed. Remember
// where it pointed for a few minutes so most polls need a single request.
static String datedUrl;
static uint32_t datedUrlAt = 0;
static const uint32_t DATED_URL_TTL_MS = 10UL * 60 * 1000;

static bool isLive(const String &state) { return state == "LIVE" || state == "CRIT"; }

static void scoreSeen(uint32_t gameId, bool home, const String &team, int score, bool live) {
  uint64_t key = ((uint64_t)gameId << 1) | home;
  auto it = knownScores.find(key);
  if (it == knownScores.end()) {
    // First time we see this game: record a baseline, don't celebrate
    // goals that happened before boot.
    knownScores[key] = score;
    return;
  }
  if (score > it->second && live) {
    for (int g = it->second; g < score; g++) {
      pendingAt.push_back(millis() + settings.delayS * 1000UL);
      pendingWho.push_back(team + " goal! (" + String(score) + ")");
    }
  }
  // Also follows score decreases (goal overturned on review).
  it->second = score;
}

static bool poll() {
  NetworkClientSecure client;
  client.setInsecure();  // public read-only data; avoids shipping a CA bundle
  HTTPClient http;
  http.useHTTP10(true);  // no chunked encoding so we can stream-parse
  http.setTimeout(8000);
  bool cached = datedUrl.length() && millis() - datedUrlAt < DATED_URL_TTL_MS;
  String url = cached ? datedUrl : String(NHL_SCORE_URL);
  int code = 0;
  for (int hop = 0; hop < 2; hop++) {
    if (!http.begin(client, url)) {
      lastError = "http begin failed";
      return false;
    }
    code = http.GET();
    if (code != 301 && code != 302 && code != 307 && code != 308) break;
    String loc = http.getLocation();
    http.end();
    if (!loc.length()) break;
    if (loc.startsWith("/")) {  // relative redirect: keep scheme and host
      String base = NHL_SCORE_URL;
      loc = base.substring(0, base.indexOf('/', 8)) + loc;
    }
    url = datedUrl = loc;
    datedUrlAt = millis();
  }
  if (code != 200) {
    lastError = "HTTP " + String(code);
    datedUrl = "";  // ask "now" again next time
    http.end();
    return false;
  }

  // The feed is large (goal details, TV info, ...). Keep only what we need.
  JsonDocument filter;
  JsonObject g = filter["games"][0].to<JsonObject>();
  g["id"] = true;
  g["gameState"] = true;
  g["awayTeam"]["abbrev"] = true;
  g["awayTeam"]["score"] = true;
  g["homeTeam"]["abbrev"] = true;
  g["homeTeam"]["score"] = true;

  JsonDocument doc;
  DeserializationError err =
      deserializeJson(doc, http.getStream(), DeserializationOption::Filter(filter));
  http.end();
  if (err) {
    lastError = String("JSON: ") + err.c_str();
    return false;
  }

  favGames.clear();
  for (JsonObject game : doc["games"].as<JsonArray>()) {
    GameView v;
    v.id = game["id"] | 0;
    v.state = game["gameState"] | "";
    v.away = game["awayTeam"]["abbrev"] | "";
    v.home = game["homeTeam"]["abbrev"] | "";
    v.awayScore = game["awayTeam"]["score"] | 0;
    v.homeScore = game["homeTeam"]["score"] | 0;
    bool favAway = settings.isFavorite(v.away), favHome = settings.isFavorite(v.home);
    if (!favAway && !favHome) continue;
    bool live = isLive(v.state);
    if (favAway) scoreSeen(v.id, false, v.away, v.awayScore, live);
    if (favHome) scoreSeen(v.id, true, v.home, v.homeScore, live);
    favGames.push_back(v);
  }
  lastError = "";
  return true;
}

static uint32_t pollIntervalMs(bool ok) {
  if (!ok) return 30000;
  for (auto &g : favGames) {
    if (isLive(g.state)) return settings.livePollS * 1000UL;
    if (g.state == "PRE") return 30000;
  }
  return favGames.empty() ? 300000 : 60000;  // FUT: check each minute for puck drop
}

void nhlLoop() {
  // Fire delayed celebrations.
  for (size_t i = 0; i < pendingAt.size();) {
    if ((int32_t)(millis() - pendingAt[i]) >= 0 && !celebrateActive()) {
      celebrateStart(pendingWho[i]);
      pendingAt.erase(pendingAt.begin() + i);
      pendingWho.erase(pendingWho.begin() + i);
    } else {
      i++;
    }
  }

  if (WiFi.status() != WL_CONNECTED || (int32_t)(millis() - nextPoll) < 0) return;
  bool ok = poll();
  lastPoll = millis();
  nextPoll = lastPoll + pollIntervalMs(ok);
  if (!ok) Serial.printf("[nhl] poll failed: %s\n", lastError.c_str());
}

void nhlResetBaselines() {
  knownScores.clear();
  pendingAt.clear();
  pendingWho.clear();
  nextPoll = millis();
}

const std::vector<GameView> &nhlFavoriteGames() { return favGames; }
String nhlLastError() { return lastError; }
uint32_t nhlLastPollMs() { return lastPoll; }
uint32_t nhlPendingGoals() { return pendingAt.size(); }
