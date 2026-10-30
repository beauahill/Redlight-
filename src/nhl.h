#pragma once
#include <Arduino.h>

// Polls the public NHL score feed and reports goals by favorite teams.
struct GameView {
  uint32_t id;
  String away, home, state;
  int awayScore, homeScore;
};

void nhlLoop();                 // call every loop; polls when due
void nhlResetBaselines();       // forget known scores (after changing teams)
const std::vector<GameView> &nhlFavoriteGames();
String nhlLastError();
uint32_t nhlLastPollMs();
uint32_t nhlPendingGoals();
