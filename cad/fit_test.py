"""Fit-test plate for the replacement tower PCB.

Print this at 1.6 mm (real PCB thickness), slide it into the housing grooves
and lay the original board on top to compare. All positions are in mm with
the origin at the tower screw (board center), +Y toward the old Imp module side
and -Y toward the TEST/VOL buttons, looking at the tower side of the board.

    python3 cad/fit_test.py        -> cad/out/fit_test.stl + .step

Values marked MEASURED come from calipers; ESTIMATE values were scaled from
photos and are what the test print is meant to check.
"""
import math
from pathlib import Path

import cadquery as cq

# --- Board outline -----------------------------------------------------------
DIAMETER = 109.5          # MEASURED
FLAT_WIDTH = 74.15        # MEASURED, distance between the two straight sides
THICKNESS = 1.6           # standard PCB

# --- Tower -------------------------------------------------------------------
SCREW_HOLE = 4.0          # MEASURED
TAB_RADIUS = 6.7          # MEASURED (approx), screw center to each strip tab
TAB_WIDTH = 6.0           # MEASURED
TAB_THICK = 1.0           # ESTIMATE, strip board thickness at the tab
SLOT_CLEARANCE = 0.4      # extra slot size so the tab fits a 3D print
HEX_ROTATION = 0.0        # tabs centered at 0, 60, 120 ... deg from +X

# --- Housing buttons (original S3 VOL+, S2 TEST, S4 VOL-) --------------------
BUTTONS = {               # ESTIMATE, (x, y) of the switch body center
    "V+": (-9.2, -42.7),
    "T": (1.0, -39.5),
    "V-": (11.4, -42.7),
}
BUTTON_HOLE = 3.0

MARK_DEPTH = 0.6          # engraved guide lines


def outline():
    """Circle with two parallel flats cut off its sides."""
    disc = cq.Workplane("XY").circle(DIAMETER / 2).extrude(THICKNESS)
    keep = cq.Workplane("XY").rect(FLAT_WIDTH, DIAMETER + 2).extrude(THICKNESS)
    return disc.intersect(keep)


def build():
    plate = outline()
    top = cq.Workplane("XY").workplane(offset=THICKNESS)

    plate = plate.cut(cq.Workplane("XY").circle(SCREW_HOLE / 2).extrude(THICKNESS))

    # Through-slots for the strip tabs, one per hex face.
    for i in range(6):
        deg = HEX_ROTATION + 60 * i
        a = math.radians(deg)
        cx, cy = TAB_RADIUS * math.cos(a), TAB_RADIUS * math.sin(a)
        slot = (
            cq.Workplane("XY")
            .center(cx, cy)
            .rect(TAB_THICK + SLOT_CLEARANCE, TAB_WIDTH + SLOT_CLEARANCE)
            .extrude(THICKNESS)
            .rotate((cx, cy, 0), (cx, cy, 1), deg)
        )
        plate = plate.cut(slot)
        plate = plate.cut(top.center(1.75 * cx, 1.75 * cy).text(f"D{i + 1}", 2.5, -MARK_DEPTH))

    for label, (x, y) in BUTTONS.items():
        plate = plate.cut(cq.Workplane("XY").center(x, y).circle(BUTTON_HOLE / 2).extrude(THICKNESS))
        plate = plate.cut(top.center(x, y + 4).text(label, 3, -MARK_DEPTH))

    plate = plate.cut(top.center(0, 25).text("TOWER SIDE", 4, -MARK_DEPTH))
    plate = plate.cut(top.center(0, 18).text("FIT v3", 3.5, -MARK_DEPTH))
    plate = plate.cut(top.center(0, 45).text("TOP", 3.5, -MARK_DEPTH))
    return plate


if __name__ == "__main__":
    out = Path(__file__).parent / "out"
    out.mkdir(exist_ok=True)
    part = build()
    cq.exporters.export(part, str(out / "fit_test.stl"), tolerance=0.02, angularTolerance=0.1)
    cq.exporters.export(part, str(out / "fit_test.step"))
    bb = part.val().BoundingBox()
    print(f"bbox {bb.xlen:.2f} x {bb.ylen:.2f} x {bb.zlen:.2f} mm -> {out}")
