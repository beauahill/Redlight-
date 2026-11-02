"""Build a 3D-printable fit model of the PCB as laid out in redlight.kicad_pcb.

    python3 cad/pcb/fit_stl.py   -> cad/pcb/out/redlight_fit.stl / .step

The board is 1.6 mm thick with the real outline, screw hole and tab slots.
Each tower-side part is a solid block of its footprint's courtyard area and
its approximate installed height, so you can check clearance inside the
housing. Bottom-side parts are left off so it prints flat; the only one is
the angled TEST switch (~4 mm, well under the 11 mm speaker clearance).
"""
import math
from pathlib import Path

import cadquery as cq
import pcbnew

HERE = Path(__file__).parent
PCB = HERE / "redlight.kicad_pcb"
OUT = HERE / "out"
ORIGIN = 100.0
THICKNESS = 1.6
PRINT_SLOT_EXTRA = 0.15     # printed slots come out a little small
PRINT_HOLE_EXTRA = 0.3      # printed holes come out ~0.2-0.3 mm small

# Installed height above the board, mm.
HEIGHTS = {
    "U1": 9.5,    # XIAO on low-profile female headers (~7 soldered on male pins)
    "U2": 8.0,    # DIP socket + chip
    "J3": 2.5,    # header pins under the amp module (module modelled separately)
    "C1": 7.7,    # 220 uF 6.3 x 7 mm
    "C2": 5.0,
}
DEFAULT_HEIGHT = 3.0        # axial resistors lying flat
AMP_MODULE = (-25.27, -37.3, 17.8, 19.4, 2.5 + 1.6 + 2.0)   # x, y, w, h, height: on header, no terminal

# The red glass: full width for 13 mm above the board, then necks to ~82 mm ID.
GLASS_NECK_RADIUS = 41.0    # MEASURED (82 mm inside diameter)
GLASS_NECK_HEIGHT = 13.0    # MEASURED
GLASS_MARGIN = 1.0


def check_glass(name, x0, y0, w, h, height):
    """Parts reaching outside the neck must stay below it."""
    r = max(math.hypot(x, y) for x in (x0, x0 + w) for y in (y0, y0 - h))
    if r > GLASS_NECK_RADIUS - GLASS_MARGIN and height > GLASS_NECK_HEIGHT - GLASS_MARGIN:
        return f"{name}: {height:.1f} mm tall reaching r = {r:.1f} mm hits the glass neck"
    return None


def mm(v):
    return pcbnew.ToMM(v)


def to_top_view(pt):
    return (mm(pt.x) - ORIGIN, ORIGIN - mm(pt.y))


def build():
    board = pcbnew.LoadBoard(str(PCB))

    # Outline + slots straight from Edge.Cuts.
    poly = pcbnew.SHAPE_POLY_SET()
    board.GetBoardPolygonOutlines(poly)
    outline = poly.Outline(0)
    pts = [to_top_view(outline.CPoint(i)) for i in range(outline.PointCount())]
    plate = cq.Workplane("XY").polyline(pts).close().extrude(THICKNESS)
    for h in range(poly.HoleCount(0)):
        hole = poly.Hole(0, h)
        hp = [to_top_view(hole.CPoint(i)) for i in range(hole.PointCount())]
        cut = cq.Workplane("XY").polyline(hp).close().extrude(THICKNESS)
        plate = plate.cut(cut)

    # Widen the tab slots a little for printing tolerance.
    for fp in board.GetFootprints():
        if fp.GetReference().startswith("LED"):
            x, y = to_top_view(fp.GetPosition())
            n = int(fp.GetReference()[3:]) - 1
            slot = (cq.Workplane("XY").center(x, y)
                    .rect(1.25 + PRINT_SLOT_EXTRA, 5.4 + PRINT_SLOT_EXTRA).extrude(THICKNESS)
                    .rotate((x, y, 0), (x, y, 1), 60 * n))
            plate = plate.cut(slot)

    plate = plate.cut(cq.Workplane("XY").circle((4.2 + PRINT_HOLE_EXTRA) / 2).extrude(THICKNESS))

    # Tower-side parts as blocks standing on the board.
    problems = []
    for fp in board.GetFootprints():
        # Skip bottom-side parts, and the screw hole / strip tabs, which are
        # holes rather than parts (H1's keep-out circle would fill the hole).
        if fp.IsFlipped() or fp.GetReference().startswith(("H", "LED")):
            continue
        fp.BuildCourtyardCaches()
        c = fp.GetCourtyard(pcbnew.F_CrtYd)
        if not c.OutlineCount():
            continue
        bb = c.BBox()
        x0, y0 = to_top_view(bb.GetOrigin())
        w, h = mm(bb.GetWidth()), mm(bb.GetHeight())
        height = HEIGHTS.get(fp.GetReference(), DEFAULT_HEIGHT)
        problems.append(check_glass(fp.GetReference(), x0, y0, w, h, height))
        block = (cq.Workplane("XY").workplane(offset=THICKNESS)
                 .center(x0 + w / 2, y0 - h / 2).rect(w, h).extrude(height))
        plate = plate.union(block)

    ax, ay, aw, ah, az = AMP_MODULE
    plate = plate.union(cq.Workplane("XY").workplane(offset=THICKNESS)
                        .center(ax + aw / 2, ay + ah / 2).rect(aw, ah).extrude(az))
    problems.append(check_glass("amp module", ax, ay + ah, aw, ah, az))
    problems = [p for p in problems if p]
    if problems:
        raise SystemExit("glass clearance:\n  " + "\n  ".join(problems))
    return plate


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    part = build()
    cq.exporters.export(part, str(OUT / "redlight_fit.stl"), tolerance=0.02, angularTolerance=0.1)
    cq.exporters.export(part, str(OUT / "redlight_fit.step"))
    bb = part.val().BoundingBox()
    print(f"bbox {bb.xlen:.1f} x {bb.ylen:.1f} x {bb.zlen:.1f} mm -> {OUT}")
