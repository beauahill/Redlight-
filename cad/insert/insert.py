"""RedLight insert rev06: the user's rev04 SolidWorks insert, cleaned up.

    python3 cad/insert/insert.py   -> cad/insert/out/RedLight_Insert_rev06.stl / .step

Kept exactly as drawn (fit features): flange, door recess and screw boss,
collar, ears and half-round bumps (their flange-facing sides must stay flat),
square battery tube, side bay walls, and the on/off switch hole in the flange
with its wire channel down the side bay wall.

Removed: the old BMS/ESP holders (hook clips on the far side, board frame on
the screw side, braces/ramp/rails and floor inside the side bay).

Added:
  * a lip at the deep end of the battery tube so the battery sled can't slide
    into the housing (45 degree underside, prints without supports);
  * two slotted rails in the side bay for the DFRobot DFR0446 charge/boost
    module (30 x 35 mm board), with a stop at the collar end. The bay's deep
    end is open: slide the board in from there, wires come out the same way.

Coordinates are rev04's: flange outer face at z = 4.9, deep end at z = -73,
door screw on the -Y ("screw") side, side bay on the -X side.
Print flange down.
"""
from pathlib import Path

import cadquery as cq

HERE = Path(__file__).parent

# --- Measured from rev04 -------------------------------------------------------
TUBE_X = (-8.75, 32.75)       # battery tube inside
TUBE_Y = (-21.25, 21.25)
DEEP_END = -73.0
BAY_X = (-32.0, -11.0)        # side bay inside
BAY_Y = (-15.41, 17.59)
BAY_TOP = -20.0               # bay meets the collar here

# --- Battery stop lip -------------------------------------------------------------
LIP = 2.5                     # how far it reaches in at the deep end (45 deg slope)

# --- DFR0446 module rails -----------------------------------------------------------
BOARD_W = 30.0                # MP2636 module, edge that spans the bay
BOARD_H = 35.0                # length along the bay
BOARD_T = 1.6
SLOT_CLEAR = 0.3              # each side of the board in the slot
SLOT_DEPTH = 2.0              # how far the board edge sits in the slot
BOARD_X = -29.0               # board plane; parts face the battery tube (+X)
RAIL_W = 6.0                  # rail size across the board plane
STOP = 2.0                    # stop at the collar end of each rail


def box(x0, x1, y0, y1, z0, z1):
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))


def build():
    part = cq.importers.importStep(str(HERE / "RedLight_Insert_rev04.step"))

    # Old holders. Each box stays clear of the tube, collar and bay walls.
    for b in (
        box(-12, 36, 23.5, 36, -58, -41),                 # hook clips, far side (tube face at +23.5)
        box(-12, 36, -32, -23.5, -62, -23),               # board frame, screw side (face at -23.5)
        box(BAY_X[0] + 0.1, BAY_X[1] - 0.1, BAY_Y[0] + 0.1, BAY_Y[1] - 0.1,
            DEEP_END - 1, BAY_TOP),                       # bay braces, rails, floor
    ):
        part = part.cut(b)

    # The solid ramp under the collar, above the bay. The walls running
    # through that zone (bay walls up to the flange, a rib on the far side)
    # carry the collar, so keep their footprint: take the wall cross-section
    # just below the ramp and protect it over the whole zone.
    zone = box(-35.0, BAY_X[1] - 0.1, -33.0, 33.0, BAY_TOP, -6.5)
    walls = part.intersect(box(-35.0, BAY_X[1] - 0.1, -33.0, 33.0, -13.05, -12.95))
    prism = cq.Workplane("XY")
    for f in walls.faces("<Z").vals():
        prism = prism.add(cq.Solid.extrudeLinear(f, cq.Vector(0, 0, 14.0)).translate((0, 0, BAY_TOP + 12.95)))
    part = part.cut(zone.cut(prism.combine()))

    # Battery stop lip: full inward reach at the deep end, tapering to nothing
    # LIP mm toward the flange, so its underside is a 45 degree slope.
    (x0, x1), (y0, y1) = TUBE_X, TUBE_Y
    cx, cy, w, d = (x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0
    ring = box(x0, x1, y0, y1, DEEP_END, DEEP_END + LIP)
    funnel = (cq.Workplane("XY").workplane(offset=DEEP_END).center(cx, cy).rect(w - 2 * LIP, d - 2 * LIP)
              .workplane(offset=LIP).rect(w, d).loft())
    part = part.union(ring.cut(funnel))

    # Module rails on both side walls of the bay. Each is a block with a slot
    # for the board edge, a stop at the collar end, and a 45 degree taper at
    # the top so it grows out of the wall without supports.
    board_edge_lo = (BAY_Y[0] + BAY_Y[1]) / 2 - BOARD_W / 2
    board_edge_hi = board_edge_lo + BOARD_W
    slot_w = BOARD_T + 2 * SLOT_CLEAR
    rail_top = BAY_TOP - 0.5
    for wall, edge, sign in ((BAY_Y[0], board_edge_lo, 1), (BAY_Y[1], board_edge_hi, -1)):
        depth = abs(edge - wall) + SLOT_DEPTH          # rail reaches past the board edge
        inner = wall + sign * depth
        slot_top = rail_top - depth - STOP             # taper, then the stop, then the slot
        rail_bot = slot_top - BOARD_H
        ya, yb = sorted((wall - sign * 0.2, inner))    # 0.2 mm into the wall to fuse
        rail = box(BOARD_X - RAIL_W / 2, BOARD_X + RAIL_W / 2, ya, yb, rail_bot, rail_top)
        slot_y = sorted((edge - sign * SLOT_CLEAR, inner + sign * 0.1))
        rail = rail.cut(box(BOARD_X - slot_w / 2, BOARD_X + slot_w / 2, *slot_y, rail_bot - 0.1, slot_top))
        # 45 degree taper on the flange-facing end so the rail grows out of the wall.
        tri = (cq.Workplane("YZ", origin=(BOARD_X - RAIL_W / 2 - 0.1, 0, 0))
               .polyline([(inner + sign * 0.1, rail_top + 0.1),
                          (inner + sign * 0.1, rail_top - depth - 0.1),
                          (wall - sign * 0.2, rail_top + 0.1)]).close().extrude(RAIL_W + 0.2))
        part = part.union(rail.cut(tri))
    return part


if __name__ == "__main__":
    out = HERE / "out"
    out.mkdir(exist_ok=True)
    part = build()
    cq.exporters.export(part, str(out / "RedLight_Insert_rev06.stl"), tolerance=0.02, angularTolerance=0.1)
    cq.exporters.export(part, str(out / "RedLight_Insert_rev06.step"))
    bb = part.val().BoundingBox()
    print(f"rev06 {bb.xlen:.1f} x {bb.ylen:.1f} x {bb.zlen:.1f} mm, {part.val().Volume() / 1000:.1f} cm3, "
          f"solids: {len(part.solids().vals())}")
