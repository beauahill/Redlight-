"""Battery sled for three 18650 cells (1S3P, in parallel).

    python3 cad/insert/battery_sled.py   -> cad/insert/out/battery_sled.stl / .step

The sled holds the cells in a triangle and slides into the insert's square
battery tube (41.5 x 42.5 mm inside) through the door opening, and rests on
the lip at the tube's deep end (see insert.py). The salvaged door closes the
other end; put a 3-5 mm foam pad between the door and the sled.

Cells sit fully inside the sled. Nickel strip goes in the shallow recesses on
both end faces; the corner channels carry the leads to the deep end.
"""
import math
from pathlib import Path

import cadquery as cq

HERE = Path(__file__).parent

TUBE_INNER = (41.5, 42.5)   # MEASURED from the insert STEP (x, y)
FIT_CLEARANCE = 0.3         # per side, so it slides in and out
CELL_DIA = 18.4             # 18650 (unprotected). Protected cells are ~18.6
CELL_BORE = 19.0
CELL_PITCH = 20.0           # center to center; leaves ~1 mm wall between cells
CELL_LEN = 65.2             # 18650 (unprotected); protected cells are ~67-69
SLED_HEIGHT = CELL_LEN + 1.8  # cell plus nickel strip at each end
STRIP_RECESS = (8.0, 0.4)   # nickel strip channel on each end face: width, depth
LIP_THICK = 2.5             # insert's stop lip (insert.py)
TUBE_BOTTOM = -73.0
WIRE_CHANNEL = 4.0          # corner channels for the pack leads
FINGER_SLOT = (14.0, 8.0)   # pull tab cutout at the top of one face

w = TUBE_INNER[0] - 2 * FIT_CLEARANCE
d = TUBE_INNER[1] - 2 * FIT_CLEARANCE

# Triangle of cells, centered on the sled.
h = CELL_PITCH * math.sqrt(3) / 2
shift = (h / 3 - 2 * h / 3) / 2      # center the triangle's extent, not its centroid
centers = [(-CELL_PITCH / 2, -h / 3 + shift), (CELL_PITCH / 2, -h / 3 + shift), (0, 2 * h / 3 + shift)]

sled = cq.Workplane("XY").rect(w, d).extrude(SLED_HEIGHT)
sled = sled.edges("|Z").fillet(1.5)
for cx, cy in centers:
    sled = sled.cut(cq.Workplane("XY").center(cx, cy).circle(CELL_BORE / 2).extrude(SLED_HEIGHT))

# Wire channels in the two corners beside the top cell.
for sx in (-1, 1):
    x = sx * (w / 2 - WIRE_CHANNEL / 2 - 1.0)
    y = d / 2 - WIRE_CHANNEL / 2 - 1.0
    sled = sled.cut(cq.Workplane("XY").center(x, y).rect(WIRE_CHANNEL, WIRE_CHANNEL).extrude(SLED_HEIGHT))

# Finger slot on the -Y face at the top, to pull the sled out.
fw, fh = FINGER_SLOT
sled = sled.cut(cq.Workplane("XZ", origin=(0, -d / 2, SLED_HEIGHT - fh / 2))
                .rect(fw, fh).extrude(-3.0))

# Nickel strip recesses joining the three cells on both end faces.
sw, sd = STRIP_RECESS
for z0 in (0.0, SLED_HEIGHT - sd):
    for (x0, y0), (x1, y1) in zip(centers, centers[1:] + centers[:1]):
        length = math.hypot(x1 - x0, y1 - y0)
        ang = math.degrees(math.atan2(y1 - y0, x1 - x0))
        strip = (cq.Workplane("XY").workplane(offset=z0).center((x0 + x1) / 2, (y0 + y1) / 2)
                 .rect(length, sw).extrude(sd)
                 .rotate(((x0 + x1) / 2, (y0 + y1) / 2, 0), ((x0 + x1) / 2, (y0 + y1) / 2, 1), ang))
        sled = sled.cut(strip)



if __name__ == "__main__":
    out = HERE / "out"
    out.mkdir(exist_ok=True)
    cq.exporters.export(sled, str(out / "battery_sled.stl"), tolerance=0.02, angularTolerance=0.1)
    cq.exporters.export(sled, str(out / "battery_sled.step"))
    room = 2.5 - (TUBE_BOTTOM + LIP_THICK)       # door recess floor is at z = 2.5
    print(f"tube length above the lip {room:.1f} mm: sled {SLED_HEIGHT:.1f} mm + "
          f"{room - SLED_HEIGHT:.1f} mm for the foam pad")
    bb = sled.val().BoundingBox()
    print(f"sled {bb.xlen:.1f} x {bb.ylen:.1f} x {bb.zlen:.1f} mm, "
          f"cells span {CELL_PITCH + CELL_BORE:.1f} x {h + CELL_BORE:.1f} mm")
