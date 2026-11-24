# Tower core

`out/tower_core.stl` (and `.step`) is the hex column the six strips stand
around. `core.py` builds it.

* Hollow hex: 13.6 mm across the outside flats (where the strips lie), 10.8 mm
  inside, 143.1 mm tall overall (MEASURED on the original: about 143).
* Round flange on top, 1.4 mm thick, with six slots for the strips' top tabs,
  on the same pattern as the PCB. Slots are 5.65 × 1.4 mm for the
  5.15 × 1.0 mm tabs.
* A solid boss at the bottom with a 2.5 mm pilot hole for one screw up through
  the board's center hole. That suits an M3 thread-forming or #4 self-tapping
  screw about 10 mm long. If the original screw is a #6, set `PILOT = 2.9`.

**Not measured yet:** the flange diameter (22 mm assumed) and the original
screw size.

## Printing

PETG, **flange down** on the bed, 3 walls, 0.2 mm layers. A 45° cone inside
roofs over the screw boss, so no supports are needed. It's tall and thin
(143 mm on a 22 mm flange): slow the outer wall down, and use a brim if it
wobbles. The color doesn't matter much since the strips cover it, but white or
grey reflects some light out between the strips.

## Assembly

Put all six strips' top tabs through the flange (LEDs facing out, "+" pads at
the bottom), lower the whole tower onto the PCB with the bottom tabs in their
slots, screw it down from the speaker side, then solder the tabs.
