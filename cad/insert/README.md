# Battery insert (rev07)

`out/RedLight_Insert_rev07.stl` is the part to print; `insert.py` builds it
from the original SolidWorks insert (`RedLight_Insert_rev04.step`). It is
91 mm across and 78 mm tall, about 80 cm³ of plastic if printed solid.

## Printing

| Setting | Recommendation |
|---|---|
| Material | **PETG**. ASA or ABS also work. Avoid PLA: it softens around 55–60 °C, and the cells and charge module run warm. Avoid carbon-fibre or other conductive filaments next to the battery contacts |
| Orientation | **Flange down** on the bed, battery tube pointing up |
| Layer height | 0.2 mm |
| Walls | 4 perimeters, so the tube and bay walls print solid |
| Top / bottom | 5 layers |
| Infill | 20–25 % gyroid (only the flange and thick sections have any) |
| Supports | **Needed.** Tree/organic supports at a 50° threshold, or paint them on (see below) |
| Bed adhesion | None needed; the flange is a 91 mm disc. Turn on elephant-foot compensation (about 0.15 mm), because the flange face is a fit surface |
| PETG temperatures | Nozzle 235–245 °C, bed 75–85 °C, part fan 30–50 % |

Faces that overhang when printed flange-down, measured from the model:

* the **door recess** in the flange face, a 1.9 mm deep pocket that prints as a
  ceiling just above the bed;
* the flange-facing sides of the **ears and half-round bumps**, at about 7 mm,
  13 mm and 57 mm above the bed. These are fit surfaces and must come out flat,
  so support them properly;
* small ledges near the deep end, at about 77 mm.

The charge-module rails have 45° tapers and print without support.

## Fitting the charge module

The rails in the side bay were drawn for a bare 30 × 35 mm board held by its
two long edges. The real DFR0446 has its battery socket overhanging one long
edge and its USB sockets close to both, so it probably will not slide into the
slots. Test-fit it after printing. If it does not go in, stick the module to
the faces of the rails with double-sided foam tape, parts facing the battery
tube; there is about 15 mm of depth there and the module is about 10 mm thick.
