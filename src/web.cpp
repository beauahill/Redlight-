#include "web.h"
#include <LittleFS.h>
#include <WebServer.h>
#include <WiFi.h>
#include <WiFiManager.h>
#include "celebrate.h"
#include "config.h"
#include "nhl.h"
#include "settings.h"
#include "tower.h"

static WebServer server(80);
static File uploadFile;

static const char *TEAMS[] = {
    "ANA", "BOS", "BUF", "CGY", "CAR", "CHI", "COL", "CBJ", "DAL", "DET", "EDM",
    "FLA", "LAK", "MIN", "MTL", "NSH", "NJD", "NYI", "NYR", "OTT", "PHI", "PIT",
    "SJS", "SEA", "STL", "TBL", "TOR", "UTA", "VAN", "VGK", "WSH", "WPG"};

static const char PAGE_HEAD[] PROGMEM = R"HTML(<!doctype html><html><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Goal Light</title><style>
body{font-family:system-ui,sans-serif;max-width:640px;margin:0 auto;padding:16px;background:#111;color:#eee}
h1{color:#e33;margin:.2em 0}fieldset{border:1px solid #444;border-radius:8px;margin:12px 0}
.teams{display:grid;grid-template-columns:repeat(auto-fill,minmax(70px,1fr));gap:4px}
label{display:block;margin:6px 0}input[type=number]{width:80px}
button,input[type=submit]{background:#c22;color:#fff;border:0;border-radius:6px;padding:10px 16px;font-size:1em;margin:4px 4px 4px 0}
.sec{background:#444}code{color:#fc6}#st{white-space:pre-wrap;font-family:monospace;font-size:.9em}
</style></head><body><h1>&#128680; Goal Light</h1>)HTML";

static void handleRoot() {
  String h;
  h.reserve(6000);
  h += FPSTR(PAGE_HEAD);
  h += F("<button onclick=\"fetch('/test',{method:'POST'})\">Test goal</button>"
         "<button class=sec onclick=\"fetch('/test-lights',{method:'POST'})\">Test lights only</button>"
         "<button class=sec onclick=\"fetch('/stop',{method:'POST'})\">Stop</button>"
         "<fieldset><legend>Status</legend><div id=st>loading…</div></fieldset>"
         "<form method=POST action=/save><fieldset><legend>Favorite teams</legend><div class=teams>");
  for (const char *t : TEAMS) {
    h += "<label><input type=checkbox name=t value=" + String(t);
    if (settings.isFavorite(t)) h += " checked";
    h += ">" + String(t) + "</label>";
  }
  h += F("</div></fieldset><fieldset><legend>Celebration</legend>");
  h += "<label>TV / stream delay <input type=number name=delay min=0 max=600 value=" +
       String(settings.delayS) + "> s</label>";
  h += "<label>Light duration <input type=number name=duration min=1 max=300 value=" +
       String(settings.durationS) + "> s</label>";
  h += "<label>Volume <input type=range name=volume min=0 max=100 value=" + String(settings.volume) +
       "></label>";
  h += F("<label>Light pattern <select name=pattern>");
  for (uint8_t i = 0; i < PATTERN_COUNT; i++) {
    h += "<option value=" + String(i) + (settings.pattern == i ? " selected>" : ">") +
         PATTERN_NAMES[i] + "</option>";
  }
  h += "</select></label>";
  h += "<label>Spin speed <input type=number name=rpm min=10 max=250 value=" +
       String(settings.rpm) + "> RPM (" + String(towerLightCount()) + " lights)</label>";
  h += String("<label><input type=checkbox name=sound value=1") + (settings.sound ? " checked" : "") +
       "> Play horn</label>";
  h += "<label>Poll every <input type=number name=poll min=3 max=60 value=" +
       String(settings.livePollS) + "> s during games</label>";
  h += F("<input type=submit value=Save></fieldset></form>"
         "<form method=POST action=/upload enctype=multipart/form-data><fieldset><legend>Horn sound</legend>");
  h += hornFilePresent() ? F("Custom <code>horn.wav</code> installed. ")
                         : F("No WAV uploaded &mdash; using built-in synth siren. ");
  h += F("Upload a 16-bit PCM WAV (see README for the ffmpeg command):<br>"
         "<input type=file name=f accept=.wav> <input type=submit value=Upload></fieldset></form>"
         "<form method=POST action=/delete-horn><button class=sec>Remove custom horn</button></form>"
         "<form method=POST action=/reset-wifi onsubmit=\"return confirm('Forget WiFi and reboot into setup mode?')\">"
         "<button class=sec>Reset WiFi</button></form>"
         "<script>async function u(){try{let s=await (await fetch('/status')).json();"
         "let t=s.games.map(g=>`${g.away} ${g.as} @ ${g.home} ${g.hs}  [${g.state}]`).join('\\n')||'No games today for your teams';"
         "document.getElementById('st').textContent=t+`\\n\\nLast poll: ${s.ago}s ago ${s.err?'('+s.err+')':'OK'}`"
         "+(s.pending?`\\nGoals queued (TV delay): ${s.pending}`:'')+(s.active?'\\n*** CELEBRATING ***':'');}catch(e){}}"
         "u();setInterval(u,3000)</script></body></html>");
  server.send(200, "text/html", h);
}

static void handleStatus() {
  String j = "{\"games\":[";
  bool first = true;
  for (auto &g : nhlFavoriteGames()) {
    if (!first) j += ',';
    first = false;
    j += "{\"away\":\"" + g.away + "\",\"home\":\"" + g.home + "\",\"as\":" + g.awayScore +
         ",\"hs\":" + g.homeScore + ",\"state\":\"" + g.state + "\"}";
  }
  j += "],\"ago\":" + String((millis() - nhlLastPollMs()) / 1000);
  j += ",\"err\":\"" + nhlLastError() + "\"";
  j += ",\"pending\":" + String(nhlPendingGoals());
  j += ",\"active\":" + String(celebrateActive() ? "true" : "false") + "}";
  server.send(200, "application/json", j);
}

static void redirectHome() {
  server.sendHeader("Location", "/");
  server.send(303);
}

static void handleSave() {
  String teams;
  for (int i = 0; i < server.args(); i++) {
    if (server.argName(i) == "t") {
      if (teams.length()) teams += ',';
      teams += server.arg(i);
    }
  }
  settings.teams = teams;
  settings.delayS = constrain(server.arg("delay").toInt(), 0, 600);
  settings.durationS = constrain(server.arg("duration").toInt(), 1, 300);
  settings.volume = constrain(server.arg("volume").toInt(), 0, 100);
  settings.livePollS = constrain(server.arg("poll").toInt(), 3, 60);
  settings.sound = server.hasArg("sound");
  settings.pattern = constrain(server.arg("pattern").toInt(), 0, PATTERN_COUNT - 1);
  settings.rpm = constrain(server.arg("rpm").toInt(), 10, 250);
  settingsSave();
  nhlResetBaselines();
  redirectHome();
}

static void handleUploadData() {
  HTTPUpload &up = server.upload();
  if (up.status == UPLOAD_FILE_START) {
    uploadFile = LittleFS.open(HORN_PATH, "w");
  } else if (up.status == UPLOAD_FILE_WRITE && uploadFile) {
    uploadFile.write(up.buf, up.currentSize);
  } else if (up.status == UPLOAD_FILE_END && uploadFile) {
    uploadFile.close();
    Serial.printf("[web] horn uploaded, %u bytes\n", up.totalSize);
  }
}

void webBegin() {
  server.on("/", HTTP_GET, handleRoot);
  server.on("/status", HTTP_GET, handleStatus);
  server.on("/save", HTTP_POST, handleSave);
  server.on("/test", HTTP_POST, [] {
    celebrateStart("test from web");
    server.send(204);
  });
  server.on("/test-lights", HTTP_POST, [] {
    towerRun(10000);
    server.send(204);
  });
  server.on("/stop", HTTP_POST, [] {
    celebrateStop();
    server.send(204);
  });
  server.on("/upload", HTTP_POST, redirectHome, handleUploadData);
  server.on("/delete-horn", HTTP_POST, [] {
    LittleFS.remove(HORN_PATH);
    redirectHome();
  });
  server.on("/reset-wifi", HTTP_POST, [] {
    server.send(200, "text/plain", "WiFi cleared, rebooting into setup mode...");
    delay(500);
    WiFiManager wm;
    wm.resetSettings();
    ESP.restart();
  });
  server.begin();
}

void webLoop() { server.handleClient(); }
