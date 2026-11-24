"""Tower core: the hex column the six LED strips stand around.

    python3 cad/tower/core.py      # -> cad/tower/out/tower_core.step / .stl

A hollow hex tube that stands on the tower PCB, held by one screw up through
the board's 4.2 mm center hole, with a round flange on top. The strips' top
tabs go through the flange's six slots (the same pattern as the PCB), their
bottom tabs through the PCB.

Print it flange-down (the flange is a flat 1.4 mm disc on the bed) in PETG,
3 walls; the inside cone over the screw boss needs no support.

Dimensions MEASURED on the original core unless marked:
  * 13.6 mm across the outside flats (the strips' inside faces), 10.8 mm across
    the inside flats
  * 143 mm tall overall, flange 1.4 mm thick
  * strips: 141.7 mm of body between the PCB and the flange
"""
import math
from pathlib import Path

import cadquery as cq

HERE = Path(__file__).parent
OUT = HERE / "out"

AF_OUT = 13.6              # across the flats, outside: the strips lie on these faces
AF_IN = 10.8               # across the flats, inside
BODY = 141.7               # PCB top to flange underside (the strips' body length)
FLANGE_T = 1.4
FLANGE_D = 22.0            # ESTIMATE: the original flange's diameter wasn't measured

# Slots for the 5.15 x 1.0 mm tabs, with printing clearance. Same angles as the
# PCB (one per face, face normals at 0, 60, ... deg). The slot's inside edge
# lines up with the core face, so the strip's back stays flat on the core.
TAB_W, TAB_T = 5.15, 1.0
SLOT_W = TAB_W + 0.5
SLOT_T = TAB_T + 0.4
SLOT_INNER = AF_OUT / 2 - 0.1

# Screw boss at the PCB end. The original screw wasn't measured: 2.5 mm suits
# an M3 thread-forming / #4 self-tapping screw; use 2.9 mm for a #6.
BOSS_LEN = 8.0
PILOT = 2.5


def hexagon(af):
    """Hexagon with flats facing 0, 60, ... deg (a vertex at 30 deg)."""
    r = af / math.sqrt(3)       # circumradius
    return [(r * math.cos(math.radians(30 + 60 * k)), r * math.sin(math.radians(30 + 60 * k)))
            for k in range(6)]


def build():
    # Z = 0 is the PCB's top face; the flange is at the top.
    body = cq.Workplane("XY").polyline(hexagon(AF_OUT)).close().extrude(BODY)
    bore = (cq.Workplane("XY").workplane(offset=BOSS_LEN)
            .polyline(hexagon(AF_IN)).close().extrude(BODY - BOSS_LEN))
    # 45 deg cone from the bore down onto the boss, so it prints without support
    # when the part is upside down on the bed.
    cone_h = AF_IN / 2
    cone = cq.Solid.makeCone(0.01, AF_IN / 2, cone_h, pnt=cq.Vector(0, 0, BOSS_LEN - cone_h))
    core = body.cut(bore).cut(cq.Workplane().add(cone).intersect(
        cq.Workplane("XY").polyline(hexagon(AF_IN)).close().extrude(BOSS_LEN)))
    core = core.cut(cq.Workplane("XY").circle(PILOT / 2).extrude(BOSS_LEN + 1))

    flange = (cq.Workplane("XY").workplane(offset=BODY)
              .circle(FLANGE_D / 2).extrude(FLANGE_T))
    core = core.union(flange)
    # Keep the middle of the flange open, the same as the bore.
    core = core.cut(cq.Workplane("XY").workplane(offset=BODY - 0.01)
                    .polyline(hexagon(AF_IN)).close().extrude(FLANGE_T + 0.02))
    for k in range(6):
        a = 60 * k
        slot = (cq.Workplane("XY").workplane(offset=BODY - 0.5)
                .center(SLOT_INNER + SLOT_T / 2, 0).rect(SLOT_T, SLOT_W)
                .extrude(FLANGE_T + 1.0)
                .rotate((0, 0, 0), (0, 0, 1), a))
        core = core.cut(slot)
    return core


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    core = build()
    cq.exporters.export(core, str(OUT / "tower_core.step"))
    cq.exporters.export(core, str(OUT / "tower_core.stl"), tolerance=0.02, angularTolerance=0.1)
    bb = core.val().BoundingBox()
    print(f"core {bb.xlen:.1f} x {bb.ylen:.1f} x {bb.zlen:.1f} mm, "
          f"{core.val().Volume() / 1000:.1f} cm3 -> {OUT}")
