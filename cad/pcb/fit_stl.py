"""Build a 3D-printable fit model of the PCB as laid out in redlight.kicad_pcb.

    python3 cad/pcb/fit_stl.py   -> cad/pcb/out/redlight_fit.stl / .step

The board is 1.6 mm thick with the real outline, screw hole and tab slots.
Each bottom-side part is a solid block of its footprint's courtyard area and
its approximate installed height, so you can check clearance inside the
housing. The model is oriented for printing: tower side on the bed, parts up.
"""
from pathlib import Path

import cadquery as cq
import pcbnew

HERE = Path(__file__).parent
PCB = HERE / "redlight.kicad_pcb"
OUT = HERE / "out"
ORIGIN = 100.0
THICKNESS = 1.6
PRINT_SLOT_EXTRA = 0.3      # extra slot width/length so tabs fit a 3D print

# Installed height below the board, mm (sockets included).
HEIGHTS = {
    "U1": 13.0,   # XIAO on 8.5 mm female headers
    "U2": 8.0,    # DIP socket + chip
    "J1": 10.0,   # screw terminal
    "J2": 7.0,    # JST XH
    "J3": 8.5,    # socket for the amp module (module modelled separately)
    "C1": 12.5,   # 470 uF 8 x 11.5 mm
    "C2": 5.0,
    "SW1": 4.0,
}
DEFAULT_HEIGHT = 3.0        # axial resistors lying flat
AMP_MODULE = (-25.27, -42.3, 17.8, 19.4, 8.5 + 1.6 + 8.5)   # x, y, w, h, top of terminal


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
                    .rect(1.25 + PRINT_SLOT_EXTRA, 6.25 + PRINT_SLOT_EXTRA).extrude(THICKNESS)
                    .rotate((x, y, 0), (x, y, 1), 60 * n))
            plate = plate.cut(slot)

    plate = plate.cut(cq.Workplane("XY").circle(2.0).extrude(THICKNESS))

    # Bottom-side parts as blocks hanging below the board (z < 0).
    for fp in board.GetFootprints():
        if not fp.IsFlipped():
            continue
        fp.BuildCourtyardCaches()
        c = fp.GetCourtyard(pcbnew.B_CrtYd)
        if not c.OutlineCount():
            continue
        bb = c.BBox()
        x0, y0 = to_top_view(bb.GetOrigin())
        w, h = mm(bb.GetWidth()), mm(bb.GetHeight())
        height = HEIGHTS.get(fp.GetReference(), DEFAULT_HEIGHT)
        block = cq.Workplane("XY").center(x0 + w / 2, y0 - h / 2).rect(w, h).extrude(-height)
        plate = plate.union(block)

    ax, ay, aw, ah, az = AMP_MODULE
    plate = plate.union(cq.Workplane("XY").center(ax + aw / 2, ay + ah / 2).rect(aw, ah).extrude(-az))

    # Print orientation: tower side down.
    return plate.rotate((0, 0, 0), (1, 0, 0), 180).translate((0, 0, THICKNESS))


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    part = build()
    cq.exporters.export(part, str(OUT / "redlight_fit.stl"), tolerance=0.02, angularTolerance=0.1)
    cq.exporters.export(part, str(OUT / "redlight_fit.step"))
    bb = part.val().BoundingBox()
    print(f"bbox {bb.xlen:.1f} x {bb.ylen:.1f} x {bb.zlen:.1f} mm -> {OUT}")
