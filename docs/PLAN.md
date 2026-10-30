# Build plan

Running notes on where the hardware build stands and what's decided.

## What we know (from teardown photos)

* Housing: original "Red Light 2.0_V4" (buzzproducts.com). The original brain
  was an Electric Imp IMP002 module, which no longer works because its cloud
  service was shut down.
* Tower: hexagonal column with **6 LED strips**, one per face. Each strip
  lands on a pad pair labelled D1–D6 around the center screw of the original
  board. The original board switched each strip low-side with its own SOT-23
  transistor (Q2–Q7, 100k gate resistors), so the strips probably share a
  common + (to be confirmed with a meter).
* The original board is also the tower's mechanical mount (center screw +
  soldered strip tabs).
* Last winter's build added six TO-220 MOSFETs (IRF540N). Those are **not
  logic-level** (they need ~10 V on the gate) and won't switch properly from a
  3.3 V ESP32 pin. Remove them.
* Already in the housing: barrel jack (panel-mounted), slide switch, DROK
  mini buck converter, lithium protection board, XIAO ESP32-C6 with screw
  terminals.

## Decisions

* **Board:** XIAO ESP32-C6 (XIAO C3 kept as a spare; PCB uses the XIAO footprint).
* **Power:** keep batteries. 3 lithium cells in series → protection board →
  DROK buck at 5 V → electronics. Barrel jack charges the pack.
  * Must be fed by a proper CC/CV charger brick for the chemistry
    (12.6 V for Li-ion 3S, ~10.8–11 V for LiFePO4 3S), or have a charger
    module between the jack and the pack. The protection board is not a
    charger.
* **LED driver:** single TBD62083APG (or ULN2803A) instead of discrete MOSFETs.
* **Direction:** custom replacement PCB in the original board's outline that
  carries the tower and all electronics (pending measurements).

## Open questions

- [ ] Cell chemistry: Li-ion 3.6/3.7 V or LiFePO4 3.2 V? Capacity?
- [ ] What charger/adapter feeds the barrel jack (voltage, current, is it a Li charger)?
- [ ] Tower polarity: common + or common –? Current per strip?
- [ ] Speaker impedance.
- [ ] Where the cells sit (3D-printed insert?) vs. electronics on the new PCB.
- [ ] Insert design file (STL/3MF/STEP).

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

- [ ] Battery voltage sense (divider into an ADC pin, shown on the web page,
      low-battery warning). Needs a light moved from D2 to D6 on the XIAO C6.
- [ ] Optional quiet hours / sleep to stretch battery life.
- [ ] Verify the XIAO C3 pin map against its strapping pins before the PCB is final.
