# Notes for Claude

Standing facts about this project and workshop. Read before designing anything.

* **3D printer: Bambu H2S**, build volume 340 × 320 × 340 mm. Default
  material PETG (cells and the charge module run warm; avoid PLA). Translucent
  red PETG for the globe.
* Four spare **v2** tower PCBs exist and will be built as full-size replicas.
  New LED strips are designed to match v2's polarity (`cad/strip/`). Don't
  apply the v2 rework (`cad/pcb/rework.py`) to boards built with them; only
  the W2 5 V wire.
* The housing, globe and power can be our own design; only the PCB and the
  strips are fixed.
* Running build notes and decisions: `docs/PLAN.md`.
* CAD is Python: KiCad 7 `pcbnew` for boards, CadQuery for printed parts.
  `cad/housing/fit_check.py` checks the whole light for collisions; run it
  after changing any part.
