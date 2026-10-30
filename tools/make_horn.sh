#!/usr/bin/env bash
# Convert any audio file into the WAV format the goal light plays.
#   ./tools/make_horn.sh my-goal-horn.mp3          -> horn.wav
#   ./tools/make_horn.sh my-goal-horn.mp3 out.wav 20   (trim to 20 s)
# Mono, 22.05 kHz, 16-bit PCM: ~44 KB per second, so up to ~45 s fits.
set -euo pipefail
in="${1:?usage: $0 input [output.wav] [max_seconds]}"
out="${2:-horn.wav}"
secs="${3:-30}"
ffmpeg -y -i "$in" -t "$secs" -ac 1 -ar 22050 -c:a pcm_s16le \
  -af "loudnorm=I=-12:TP=-1.0" -map_metadata -1 -fflags +bitexact "$out"
ls -lh "$out"
