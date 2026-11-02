# Build plan

Running notes on where the hardware build stands and what's decided.

## What we know (from teardown photos)

* Housing: original "Red Light 2.0_V4" (buzzproducts.com). The original brain
  was an Electric Imp IMP002 module, which no longer works because its cloud
  service was shut down.
* Tower: hexagonal column with **6 LED strips**, one per face. Each strip
  lands on a pad pair labelled D1–D6 around the center screw of the original
  board. The original board switched each strip low-side with its own SOT-23
  transistor. The strips themselves are **independent** rigid LED strips with
  "+" marked next to their pads at both ends; any shared connection was only
  on the old board.
* The original board is also the tower's mechanical mount (center screw +
  soldered strip tabs).
* Last winter's build added six TO-220 MOSFETs (IRF540N) on the + pads. An
  N-channel MOSFET on the high side from a 3.3 V gate only passes about 1 V,
  and the IRF540N isn't logic-level anyway. Remove them.
* Already in the housing: barrel jack (panel-mounted), slide switch, DROK
  mini buck converter, lithium protection board, XIAO ESP32-C6 with screw
  terminals.

## Decisions

* **Speaker:** original 4 Ω 3 W, driven by a MAX98357A (≈3 W into 4 Ω at
  5 V). At full volume it can pull ~0.8 A from 5 V, so size the UPS module
  for 2 A.
* **Board:** XIAO ESP32-C6 (XIAO C3 kept as a spare; PCB uses the XIAO footprint).
* **Power:** 3 salvaged 18650 Li-ion cells **in parallel (1S3P)** → 1S
  load-sharing charge/boost (UPS) module → 5 V rail. Barrel jack takes a
  plain 5 V 2 A adapter. The old 3S protection board and DROK buck are no
  longer needed. See WIRING.md → Power for module requirements and cell checks.
* **LED driver:** single TBD62083APG low-side driver (ULN2803A as fallback).
  All strip + pads on the 5 V rail, each strip's – switched.
* **Direction:** custom replacement PCB in the original board's outline that
  carries the tower and all electronics (pending measurements).

## Open questions

- [ ] Choose the UPS module (needs tower current to size it).
- [ ] Current per strip, and whether the strips have built-in resistors.
- [ ] Where the cells sit (3D-printed insert?) vs. electronics on the new PCB.
- [ ] Insert design file (STL/3MF/STEP).

## Board geometry (fit-test v2: `cad/fit_test.py` → `cad/out/fit_test.stl`)

* MEASURED: 109.5 mm circle with two parallel flats 74.15 mm apart, 4 mm
  center hole for the tower's plastic core screw. No top flat needed.
* Strip tabs pass through slots in the board: tabs 6 mm wide, ~6.7 mm from
  the screw center (MEASURED). Tab thickness and button positions are still
  estimates. D1–D6 on the plate is our numbering, counter-clockwise from +X.
* Each tab has a + and a – pad. The new board puts + on 5 V and routes – to
  the driver. No mounting holes; the board appears to slide into grooves in
  the housing.
* The barrel jack is a bare panel connector (5.5×2.1 mm); no charger yet.

## PCB v2 — `cad/pcb/` (see its README)

* Routed, DRC clean (0 unconnected, no copper errors), Gerbers in
  `cad/pcb/redlight-gerbers.zip`. Don't order until the open items below are done.
* Speaker is 11 mm below the board, so tall parts are on the tower side; the
  speaker side has only the TEST switch and wire pads.
* Tab slots 5.4 × 1.25 mm for the 5.15 mm tabs; screw hole 4.2 mm.
* TEST / VOL+ / VOL- at the measured positions, on one ADC pin (resistor ladder).
* No support tab: tried one into the housing recess, it didn't fit as hoped.
* Red glass necks to ~82 mm ID 13 mm above the board: tower-side parts kept
  ≤ 9.5 mm (XIAO on low-profile headers, amp module soldered flat without its
  terminal block, 6.3 × 7 mm cap). Checked by `fit_stl.py`.
* Strips: 10 LEDs each with an on-strip 20 Ω resistor ("200"), so R1–R6 are
  0 Ω jumpers. MEASURED: very bright at 5 V, ~0.1 W (≈ 20 mA) on the bench
  supply, so the LEDs are likely series pairs. Strobe (all six on) ≈ 0.12 A.
  The driver drops only ~0.04 V at that current.
* Board is ready to order.

## Battery insert — `cad/insert/`

* `RedLight_Insert_rev04.step`: the user's SolidWorks insert (reference, unchanged).
* `insert.py` → `out/RedLight_Insert_rev06.*`: rev04 cleaned up. Kept exactly:
  flange, door recess + screw boss, collar, ears and half-round bumps (flange
  sides stay flat, so they still print with supports), battery tube, side bay
  walls, the on/off switch hole in the flange and its wire channel. Removed:
  the old BMS/ESP holders (hook clips, board frame, bay braces/ramp/rails/floor).
  Added: 45° battery stop lip at the deep end, slotted rails + stop in the side
  bay for the DFR0446 module (slides in from the open deep end).
* `battery_sled.py` → `out/battery_sled.*`: 3 × 18650 sled, rests on the lip;
  3-5 mm foam pad under the door.
* Charge/boost module: DFRobot DFR0446 (MP2636), 35 × 30 × 11 mm, 2.5 A boost.
  Verify pass-through and light-load behavior on arrival.
* Wiring: barrel jack → module VIN; cells → module BAT and → PCB VBAT;
  module 5 V out → flange slide switch → PCB 5V. The switch cuts the light,
  charging still works with it off.

## Measurements needed for the PCB

1. Outline: straight-down photo on paper with a ruler, plus overall width,
   height and the flat edges.
2. Center screw hole: diameter and position from two edges.
3. Tower pads: radius from center to each pair, pad size, gap within a pair,
   tower base width across flats.
4. Mounting holes to the housing: positions and diameters.
5. Board thickness (likely 1.6 mm).
6. Height clearance above and below the board inside the housing.
7. Position of the button cap, speaker and wire routes relative to the board.

## Firmware to-do

- [x] Battery voltage sense on XIAO C6 D2 (light 3 moved to D6), shown on the
      web page with a low-battery warning.
- [ ] Optional quiet hours / sleep to stretch battery life.
- [ ] Verify the XIAO C3 pin map against its strapping pins before the PCB is final.
