#include "settings.h"
#include <Preferences.h>
#include "config.h"

Settings settings;
static Preferences prefs;

bool Settings::isFavorite(const String &abbrev) const {
  if (abbrev.isEmpty()) return false;
  // Match whole entries of the comma-separated list.
  String padded = "," + teams + ",";
  return padded.indexOf("," + abbrev + ",") >= 0;
}

void settingsLoad() {
  prefs.begin("goallight", true);
  settings.teams = prefs.getString("teams", DEFAULT_TEAMS);
  settings.delayS = prefs.getUShort("delay", DEFAULT_DELAY_S);
  settings.durationS = prefs.getUShort("duration", DEFAULT_DURATION_S);
  settings.volume = prefs.getUChar("volume", DEFAULT_VOLUME);
  settings.livePollS = prefs.getUChar("poll", DEFAULT_LIVE_POLL_S);
  settings.sound = prefs.getBool("sound", true);
  settings.pattern = prefs.getUChar("pattern", DEFAULT_PATTERN);
  settings.rpm = prefs.getUChar("rpm", DEFAULT_RPM);
  prefs.end();
}

void settingsSave() {
  prefs.begin("goallight", false);
  prefs.putString("teams", settings.teams);
  prefs.putUShort("delay", settings.delayS);
  prefs.putUShort("duration", settings.durationS);
  prefs.putUChar("volume", settings.volume);
  prefs.putUChar("poll", settings.livePollS);
  prefs.putBool("sound", settings.sound);
  prefs.putUChar("pattern", settings.pattern);
  prefs.putUChar("rpm", settings.rpm);
  prefs.end();
}
