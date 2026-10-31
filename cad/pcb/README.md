# Replacement tower PCB (v2)

Drop-in replacement for the original "Red Light 2.0" board: same outline
(109.5 mm circle, 74.15 mm across the flats) plus a support tab that sits in
the housing recess opposite the buttons, a 4.2 mm tower screw hole, and six
slots for the 5.15 mm LED strip tabs.

The speaker sits only 11 mm below the board, so all tall parts go on the
**tower side**, which is hidden inside the housing. The speaker side carries
only the angled TEST switch (~4 mm) and solder pads for wires.

![preview](out/pcb_preview.png)

## Files

| File | What |
|---|---|
| `redlight-gerbers.zip` | upload this to JLCPCB / PCBWay / OSH Park |
| `redlight.kicad_pcb` | KiCad board (opens in KiCad 7, 8, 9) |
| `out/redlight_fit.stl` | printable fit model (tower-side parts as blocks of real size/height) |
| `make_pcb.py` | generates the board: outline, slots, placement, nets |
| `route.py` | autoroutes (Freerouting), pours ground, DRC, Gerbers |
| `fit_stl.py` | builds the fit model from the board |

There's no schematic sheet. The netlist is defined in `make_pcb.py`, and
`docs/WIRING.md` has the circuit.

## Ordering

2 layers, 1.6 mm, any color, HASL (lead-free is fine), 1 oz copper.
The six tab slots and the screw hole are cut from the Edge.Cuts outline
(non-plated), which every fab handles at no extra cost. Leave other options
at their defaults.

## Parts (BOM)

| Ref | Part | Notes |
|---|---|---|
| U1 | Seeed XIAO ESP32-C6 | on 2× 1x7 female headers (2.54 mm) so it's removable |
| U2 | TBD62083APG | DIP-18, in a DIP-18 socket. ULN2803A also fits (dimmer) |
| R1–R6 | LED resistors, 1/4 W axial | **value TBD** from strip current measurement (47 Ω placeholder) |
| R7, R8 | 100 kΩ 1/4 W axial | battery gauge divider |
| C1 | 470 µF 10 V electrolytic, 8 mm dia, 3.5 mm pitch | watch polarity |
| C2 | 100 nF ceramic, 5 mm pitch | |
| J1 | solder pads, 3-way (speaker side) | 5V / GND / VBAT wires from the UPS module + cells |
| J2 | solder pads, 2-way (speaker side) | optional external TEST button |
| J3 | 1x7 female header 2.54 mm | MAX98357A breakout plugs in here, components facing away |
| SW1–SW3 | PTS645 right-angle 6 mm tact switch (speaker side) | TEST, VOL+, VOL- at the housing's buttons |
| R10, R11, R12 | 10 kΩ, 2.2 kΩ, 6.8 kΩ 1/4 W axial | button resistor ladder |
| D1, R9 | 3 mm LED (right-angle) + 2.2 kΩ | optional power light, points into the old Wi-Fi light recess |
| — | MAX98357A breakout (Adafruit 3006 or clone) | speaker wires go to its screw terminal |

## Before ordering

- [x] Flat fit print: outline, tab slots, screw hole
- [ ] Support tab position: centered 15 mm off-axis (under the old sensor/LED) — confirm
- [ ] v2 fit print: tower-side parts clear the dome, tab sits in the recess
- [x] Tab thickness 1.0 mm, width 5.15 mm, 14.4 mm across strip faces
- [x] "+" is the left pad facing the LEDs (clockwise half from the tower side)
- [x] Button positions (TEST 39.6 mm, VOL± 48 mm and 20.15 mm apart)
- [ ] LED resistor value from the strip current

To regenerate after a change:

```bash
python3 cad/pcb/make_pcb.py
FREEROUTING_JAR=~/freerouting-1.9.0.jar python3 cad/pcb/route.py   # needs Java (+ xvfb-run on headless Linux)
python3 cad/pcb/fit_stl.py
```
