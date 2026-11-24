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
* **Board:** Seeed XIAO ESP32-C6.
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
* Tab slots 5.7 × 1.25 mm for the 5.15 mm tabs (extra length covers the
  fab's ~0.5 mm router corner radius), centered at r = 7.3 mm
  (strip inside faces 13.6 mm across, MEASURED); screw hole 4.2 mm.
* TEST / VOL+ / VOL- at the measured positions, on one ADC pin (resistor ladder).
* No support tab: tried one into the housing recess, it didn't fit as hoped.
* Red glass necks to ~82 mm ID 13 mm above the board: tower-side parts kept
  ≤ 9.5 mm (XIAO on low-profile headers, amp module soldered flat without its
  terminal block, 6.3 × 7 mm cap). Checked by `fit_stl.py`.
* Strips: 10 red LEDs in parallel behind an on-strip 20 Ω resistor ("200"),
  so R1–R6 are 0 Ω jumpers. MEASURED: 3.0 V across the resistor at 5 V, so
  150 mA per strip (≈ 135 mA through the driver). Strobe (all six) ≈ 0.8 A,
  peak with audio ≈ 1.5 A: within the 2.5 A module and 500 mA/channel.
  * The on-strip resistor dissipates ~0.36 W while lit; patterns are duty
    cycled. Firmware "Light brightness" defaults to 80 % for extra margin.
* Board is ready to order (the strip current only affects firmware tuning).

## First build findings (v2 board)

* Firmware runs on the XIAO C6: WiFi setup, web page and buttons work.
* **Tab pads are swapped** relative to the strips' printed "+", so no strip
  lights. Fix options and a second fault in the 5 V feed are written up under
  "Known issues" in `cad/pcb/README.md`.
* The DIP socket went in with its notch at the C2 end. Harmless; the chip goes
  in by the board's marking (notch toward the XIAO).
* **Board rework done** (source-driver route): cuts 1–3, W1 (tower pads to
  ground) and W2 (XIAO 5V to J1 5V) are in. Strips D1, D2 and D5 did not reach
  the ring through their own pads, so their "−" halves are linked by wire to a
  neighbour (D1 and D5 to D6, D2 to D3). All six strips light when 5 V is
  jumpered from socket hole 10 to holes 18–13.
* **Still to do:** fit a TBD62783APG with pins 9 and 10 crossed over
  (`cad/pcb/out/rework_chip.png`); fit the amp plus a wire from J1 5V to its VIN
  hole; wire the battery side.

## Button adapter (to design)

The board's three right-angle switches (TEST, VOL+, VOL−) do not line up with
the housing's original buttons, so a 3D-printed part is needed to carry each
button press to its switch. Not designed yet. The housing's buttons push in
line with the switch plungers (toward the board's edge); only the alignment is
off, so the part is an offset pusher, not a lever. Still needed: for each
button the offset from its push point to the switch plunger (sideways, height,
and gap), plus the button's travel.

## PCB v3

`cad/pcb/` now holds v3: strip polarity corrected, 5 V routed by hand so it
never passes through a tab pad, sturdier tab pads. DRC clean; not yet
fabricated. The built board is a reworked v2 (see above and `cad/pcb/README.md`).

## Battery insert — `cad/insert/`

* `RedLight_Insert_rev04.step`: the user's SolidWorks insert (reference, unchanged).
  Its battery tube is sized for two 2-cell 18650 holders side by side, so the
  door screws on with no play.
* `insert.py` → `out/RedLight_Insert_rev07.*`: rev04 cleaned up. Kept exactly:
  flange, door recess + screw boss, collar, ears and half-round bumps, the
  battery tube (no lip, identical to rev04 inside), side bay walls, the on/off
  switch hole and its wire channel. Removed: the old BMS/ESP holders. Added:
  slotted rails + stop in the side bay for the DFR0446 module.
* Cells: 4 × 18650 in the user's two 2-cell holders. Decided: all four in
  parallel (1S4P) with the DFR0446 charge/boost module, a plain 5 V adapter, and
  the board and firmware unchanged (R7/R8 = 100k/100k).
* **The carrier is currently wired 2S2P (about 8 V), not 1S4P.** It must be
  rewired all-parallel before it goes anywhere near the module or the VBAT pad:
  the module is for a single-cell pack (4.2 V maximum), and 8 V on VBAT would put
  over 4 V on the XIAO's battery-sense pin. Measure the pack first; it must read
  no more than 4.2 V.
* Still to do: rewire the carrier, then wire the module to the barrel jack,
  slide switch and J1.

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

## Full-scale replicas (×4) — using the four spare v2 boards

Four more lights built from scratch around the spare **v2** boards: new LED
strips, a printed tower core, a printed housing base and a dome printed in
translucent red PETG. No original branding.

* **LED strips:** done, ready to order: `cad/strip/` (see its README). They're
  made as a 6-up JLCPCB panel, one panel per light; order 5 panels (30 strips). "+"
  is placed to match the v2 board, so the fresh boards need only the W2 wire,
  not the polarity rework, and take the stock TBD62083APG.
* **Tower core:** done, ready to print: `cad/tower/`. Flange diameter and
  screw size still assumed.
* **Dome:** to design. Translucent red PETG. Needs measurements (below).
* **Housing base:** to design. Board grooves, speaker mount, button pushers
  lined up with the board's switches (this also solves the button adapter),
  the barrel jack and slide switch, and a socket for the battery insert (rev07).
  Needs measurements (below).
* **Per light, also buy:** XIAO ESP32-C6, TBD62083APG + DIP-18 socket,
  MAX98357A, 4 Ω 3 W speaker, DFR0446, 4 × 18650 + two 2-cell holders, 3 A
  fuse, passives per `docs/WIRING.md`, 5 V 2 A adapter, barrel jack, slide
  switch, M3 × 10 screw for the core.

Measurements still needed for the dome and base:

- [ ] Dome: overall height, outside diameter at the base, how it attaches to
      the base (thread, bayonet, clips, screws), wall thickness, and a
      side-on profile photo against a ruler (the neck is already known: 82 mm
      ID, 13 mm above the board)
- [ ] Base: outside diameter and height, groove height and depth for the
      board, speaker diameter, depth and mounting, button cap positions and
      travel, barrel jack and slide switch hole sizes and positions, and how the
      insert attaches
- [ ] Core: flange diameter, original screw size
