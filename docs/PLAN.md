# Build plan

Running notes on where the hardware build stands and what's decided.

## What we know (from teardown photos)

* Housing: original "Red Light 2.0_V4" (buzzproducts.com). The original brain
  was an Electric Imp IMP002 module, which no longer works because its cloud
  service was shut down.
* Tower: hexagonal column with **6 LED strips**, one per face. Each strip
  lands on a pad pair labelled D1–D6 around the center screw of the original
  board. The original board switched each strip low-side with its own SOT-23
  transistor (Q2–Q7, 100k gate resistors). The strips **share negative**,
  with a separate + pad per strip (confirmed by last winter's high-side test).
* The original board is also the tower's mechanical mount (center screw +
  soldered strip tabs).
* Last winter's build added six TO-220 MOSFETs (IRF540N) on the + pads. An
  N-channel MOSFET on the high side from a 3.3 V gate only passes about 1 V,
  and the IRF540N isn't logic-level anyway. Remove them.
* Already in the housing: barrel jack (panel-mounted), slide switch, DROK
  mini buck converter, lithium protection board, XIAO ESP32-C6 with screw
  terminals.

## Decisions

* **Board:** XIAO ESP32-C6 (XIAO C3 kept as a spare; PCB uses the XIAO footprint).
* **Power:** 3 salvaged 18650 Li-ion cells **in parallel (1S3P)** → 1S
  load-sharing charge/boost (UPS) module → 5 V rail. Barrel jack takes a
  plain 5 V 2 A adapter. The old 3S protection board and DROK buck are no
  longer needed. See WIRING.md → Power for module requirements and cell checks.
* **LED driver:** single TBD62783APG high-side driver instead of discrete
  MOSFETs (the tower's – side is shared, so the + side must be switched).
* **Direction:** custom replacement PCB in the original board's outline that
  carries the tower and all electronics (pending measurements).

## Open questions

- [ ] Choose the UPS module (needs tower current to size it).
- [ ] Current per strip, and whether the strips have built-in resistors.
- [ ] Speaker impedance.
- [ ] Where the cells sit (3D-printed insert?) vs. electronics on the new PCB.
- [ ] Insert design file (STL/3MF/STEP).

## Board geometry (fit-test v2: `cad/fit_test.py` → `cad/out/fit_test.stl`)

* MEASURED: 109.5 mm circle with two parallel flats 74.15 mm apart, 4 mm
  center hole for the tower's plastic core screw. No top flat needed.
* ESTIMATE (from photos, check with the print): hex strip faces 7.8 mm from
  center, strips 9 mm wide, button positions. No mounting holes; the board appears to slide into grooves in
  the housing.
* The barrel jack is a bare panel connector (5.5×2.1 mm); no charger yet.

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
