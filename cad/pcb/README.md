# Replacement tower PCB (v1)

Drop-in replacement for the original "Red Light 2.0" board: same outline
(109.5 mm circle, 74.15 mm across the flats), 4 mm tower screw hole, and six
slots for the LED strip tabs. The tower stands on the top side. All parts
are through-hole and mount on the bottom side, like the original.

![preview](out/pcb_preview.png)

## Files

| File | What |
|---|---|
| `redlight-gerbers.zip` | upload this to JLCPCB / PCBWay / OSH Park |
| `redlight.kicad_pcb` | KiCad board (opens in KiCad 7, 8, 9) |
| `out/redlight_fit.stl` | printable fit model (parts as blocks of real size/height) |
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
| J1 | 3-way 5.08 mm screw terminal | 5V / GND / VBAT from the UPS module + cells |
| J2 | JST XH 2-pin | optional external button |
| J3 | 1x7 female header 2.54 mm | MAX98357A breakout plugs in here, components facing away |
| SW1 | PTS645 right-angle 6 mm tact switch | at the housing's TEST button (position to verify) |
| — | MAX98357A breakout (Adafruit 3006 or clone) | speaker wires go to its screw terminal |

## Before ordering

- [ ] Fit print checked (outline, slots, tower stands straight, parts clear the housing)
- [ ] Tab thickness measured (slot is 1.0 mm + 0.25 mm clearance)
- [ ] Which half of each tab is "+" (`PLUS_ON_CCW_SIDE` in `make_pcb.py`)
- [ ] LED resistor value from the strip current
- [ ] TEST button position

To regenerate after a change:

```bash
python3 cad/pcb/make_pcb.py
FREEROUTING_JAR=~/freerouting-1.9.0.jar python3 cad/pcb/route.py   # needs Java (+ xvfb-run on headless Linux)
python3 cad/pcb/fit_stl.py
```
