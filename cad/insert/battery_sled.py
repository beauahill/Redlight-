"""Battery sled: holds three 18650 cells (1S3P, in parallel) in a triangle and
slides into the main square tube of RedLight_Insert_rev04 (41.5 x 42.5 mm
inside). The insert itself is unchanged.

    python3 cad/insert/battery_sled.py   -> cad/insert/out/battery_sled.stl / .step

The cells stick out of both ends of the sled so nickel strip can be welded
across them (or use 3-cell parallel holders' contacts). Corner channels
carry the + / - leads up to the UPS module.
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
SLED_HEIGHT = 50.0          # cells (65 mm) protrude ~7.5 mm each end for strips
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

if __name__ == "__main__":
    out = HERE / "out"
    out.mkdir(exist_ok=True)
    cq.exporters.export(sled, str(out / "battery_sled.stl"), tolerance=0.02, angularTolerance=0.1)
    cq.exporters.export(sled, str(out / "battery_sled.step"))
    bb = sled.val().BoundingBox()
    print(f"sled {bb.xlen:.1f} x {bb.ylen:.1f} x {bb.zlen:.1f} mm, "
          f"cells span {CELL_PITCH + CELL_BORE:.1f} x {h + CELL_BORE:.1f} mm")
