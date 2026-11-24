"""Draw cad/strip/out/strip_preview.png from the panel board file:
the whole 6-up panel, and close-ups of one strip's top end and bottom tab
(LED side, then the back).

    python3 cad/strip/preview.py
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Polygon as MPoly

import pcbnew

HERE = Path(__file__).parent
PCB = HERE / "redlight_strip_panel.kicad_pcb"
OUT = HERE / "out" / "strip_preview.png"

board = pcbnew.LoadBoard(str(PCB))
mm = pcbnew.ToMM
COL = {"board": "#1f5f3a", "F": "#c9a227", "B": "#4f7fbf", "pad": "#e8e8e8", "silk": "#ffffff",
       "led": "#d22", "res": "#333"}


def poly_pts(shape_poly):
    out = []
    for i in range(shape_poly.OutlineCount()):
        o = shape_poly.Outline(i)
        out.append([(mm(o.CPoint(k).x), mm(o.CPoint(k).y)) for k in range(o.PointCount())])
    return out


def draw(ax, side):
    ax.set_facecolor("#0d1b12")
    edges = [d for d in board.GetDrawings() if d.GetLayer() == pcbnew.Edge_Cuts]
    for e in edges:
        ax.plot([mm(e.GetStart().x), mm(e.GetEnd().x)], [mm(e.GetStart().y), mm(e.GetEnd().y)],
                color="#9fd4a8", lw=0.6)
    layer = pcbnew.F_Cu if side == "F" else pcbnew.B_Cu
    for z in board.Zones():
        if z.GetLayer() == layer and not z.GetIsRuleArea():
            for pts in poly_pts(z.GetFilledPolysList(layer)):
                ax.add_patch(MPoly(pts, closed=True, fc=COL[side], ec="none", alpha=0.85))
    for t in board.GetTracks():
        if t.GetClass() == "PCB_VIA":
            ax.add_patch(Circle((mm(t.GetPosition().x), mm(t.GetPosition().y)), 0.3, fc="#bbb", ec="none"))
            ax.add_patch(Circle((mm(t.GetPosition().x), mm(t.GetPosition().y)), 0.15, fc="#000", ec="none"))
        elif t.GetLayer() == layer:
            ax.plot([mm(t.GetStart().x), mm(t.GetEnd().x)], [mm(t.GetStart().y), mm(t.GetEnd().y)],
                    color=COL[side], lw=2.2, solid_capstyle="round")
    for fp in board.GetFootprints():
        for p in fp.Pads():
            on = p.IsOnLayer(layer) or p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH
            if not on:
                continue
            if p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
                ax.add_patch(Circle((mm(p.GetPosition().x), mm(p.GetPosition().y)),
                                    mm(p.GetDrillSize().x) / 2, fc="#000", ec="#9fd4a8", lw=0.3))
                continue
            bb = p.GetBoundingBox()
            ax.add_patch(plt.Rectangle((mm(bb.GetX()), mm(bb.GetY())), mm(bb.GetWidth()), mm(bb.GetHeight()),
                                       fc=COL["pad"], ec="none"))
        if side == "F":
            ref = fp.GetReference()
            c = (mm(fp.GetPosition().x), mm(fp.GetPosition().y))
            if ref.startswith("D"):
                ax.add_patch(plt.Rectangle((c[0] - 1.4, c[1] - 1.75), 2.8, 3.5, fc=COL["led"], ec="#fff",
                                           lw=0.3, alpha=0.75))
                ax.plot([c[0] - 1.4, c[0] + 1.4], [c[1] - 1.75, c[1] - 1.75], color="#fff", lw=1.2)  # cathode
            elif ref.startswith("R"):
                ax.add_patch(plt.Rectangle((c[0] - 0.8, c[1] - 0.4), 1.6, 0.8, fc=COL["res"], ec="#aaa", lw=0.3))
    for d in board.GetDrawings():
        silk = pcbnew.F_SilkS if side == "F" else pcbnew.B_SilkS
        if d.GetClass() == "PCB_TEXT" and d.GetLayer() == silk:
            ax.text(mm(d.GetPosition().x), mm(d.GetPosition().y), d.GetText(), color=COL["silk"],
                    fontsize=6, ha="center", va="center", rotation=d.GetTextAngleDegrees())
    ax.set_aspect("equal")
    ax.invert_yaxis()
    ax.set_xticks([])
    ax.set_yticks([])


bb = board.GetBoardEdgesBoundingBox()
x0, y0, x1, y1 = mm(bb.GetX()), mm(bb.GetY()), mm(bb.GetRight()), mm(bb.GetBottom())
cx = x0 + 5 + 2 + 6.15 / 2           # first strip
tip = y0 + 7.5

fig = plt.figure(figsize=(15, 9), facecolor="white")
gs = fig.add_gridspec(2, 4, width_ratios=[1.3, 1, 1, 1.6])
ax = fig.add_subplot(gs[:, 0])
draw(ax, "F")
ax.set_xlim(x0 - 1, x1 + 1)
ax.set_ylim(y1 + 1, y0 - 1)
ax.set_title("6-up panel, LED side", fontsize=10)

views = [("F", tip - 1, tip + 30, "top end, LED side"),
         ("F", tip + 124, tip + 149, "bottom tab, LED side\n+ is RIGHT (v2 board)"),
         ("B", tip - 1, tip + 30, "top end, back\n(seen through the board)"),
         ("B", tip + 124, tip + 149, "bottom tab, back\n(seen through the board)")]
spots = [gs[0, 1], gs[1, 1], gs[0, 2], gs[1, 2]]
for (side, ya, yb, title), spot in zip(views, spots):
    a = fig.add_subplot(spot)
    draw(a, side)
    a.set_xlim(cx - 6, cx + 6)
    a.set_ylim(yb, ya)
    a.set_title(title, fontsize=9)

note = fig.add_subplot(gs[:, 3])
note.axis("off")
note.text(0, 1, (
    "Strip (one of six per light)\n"
    "  148 mm tip to tip, 6.15 mm wide, 1.0 mm FR-4\n"
    "  tabs 5.15 mm: top 2.9 mm, bottom 3.4 mm\n"
    "  body 141.7 mm (board top to flange)\n\n"
    "LEDs\n"
    "  10 x red PLCC-2 3528, first 7 mm from\n"
    "  the top tip, 11.6 mm apart\n"
    "  each with its own 200 ohm 0603\n"
    "  ~14 mA each, ~140 mA per strip\n\n"
    "Back copper\n"
    "  two rails the full length: + and -\n\n"
    "Bottom tab\n"
    "  exposed pads on the LED face, solder\n"
    "  to the board's pads outside each slot\n"
    "  (both sides of the board)\n\n"
    "White bar on each LED = cathode (top)"),
    va="top", fontsize=9, family="monospace")
fig.tight_layout()
OUT.parent.mkdir(exist_ok=True)
fig.savefig(OUT, dpi=150)
print("->", OUT)
