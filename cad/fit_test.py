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
HEX_APOTHEM = 7.8         # ESTIMATE, screw center to the outside of a strip
STRIP_WIDTH = 9.0         # ESTIMATE, width of one LED strip (hex side)
STRIP_THICK = 0.8         # ESTIMATE
HEX_ROTATION = 0.0        # faces centered at 0, 60, 120 ... deg from +X

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

    # Footprint of each LED strip where it stands on the board.
    for i in range(6):
        a = math.radians(HEX_ROTATION + 60 * i)
        cx = (HEX_APOTHEM - STRIP_THICK / 2) * math.cos(a)
        cy = (HEX_APOTHEM - STRIP_THICK / 2) * math.sin(a)
        slot = (
            top.center(cx, cy)
            .rect(STRIP_THICK, STRIP_WIDTH)
            .extrude(-MARK_DEPTH)
            .rotate((cx, cy, 0), (cx, cy, 1), HEX_ROTATION + 60 * i)
        )
        plate = plate.cut(slot)

    for label, (x, y) in BUTTONS.items():
        plate = plate.cut(cq.Workplane("XY").center(x, y).circle(BUTTON_HOLE / 2).extrude(THICKNESS))
        plate = plate.cut(top.center(x, y + 4).text(label, 3, -MARK_DEPTH))

    plate = plate.cut(top.center(0, 25).text("TOWER SIDE", 4, -MARK_DEPTH))
    plate = plate.cut(top.center(0, 18).text("FIT v2", 3.5, -MARK_DEPTH))
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
