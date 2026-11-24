"""Generate the tower LED strips as a 6-up JLCPCB assembly panel (KiCad 7).

    python3 cad/strip/make_strip.py

Writes cad/strip/redlight_strip_panel.kicad_pcb, then fills the pours, runs
DRC and exports the order files to cad/strip/fab/:

    redlight-strip-gerbers.zip   upload as the PCB
    strip_bom.csv                JLCPCB assembly BOM
    strip_cpl.csv                JLCPCB assembly placement (pick-and-place)

One panel is one light: six identical strips in a frame, joined by
mouse-bite tabs. Order 5 panels (the JLCPCB minimum), enough for four lights
plus six spare strips.

Each strip copies the original's outline: 148 mm long including its tabs,
6.15 mm wide, 1.0 mm thick, with a 5.15 mm wide tab at each end. The bottom tab
goes through the tower PCB, the top tab through the core's flange. Ten red
PLCC-2 (3528) LEDs, each with its own 200 ohm resistor, which comes to about
140 mA per strip at 5 V, the same as the original's 150 mA, so the firmware
and the driver chip need no change.

POLARITY: these strips are for the **v2** tower board, which has the 5 V
ring on the counter-clockwise pad of each slot (seen from the tower side).
Seen from outside the tower, LEDs facing you and the bottom tab down, "+" is
the RIGHT half of the bottom tab. That is the reverse of the original strips,
so a v2 board needs no polarity rework with these. (For a v3 board, set
PLUS_ON_RIGHT = False.)

Coordinates are millimetres on the KiCad sheet: X to the right, Y down, the
strips seen from their LED side, top tab at the top.
"""
import csv
import re
import subprocess
import zipfile
from pathlib import Path

import pcbnew
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

HERE = Path(__file__).parent
OUT = HERE / "redlight_strip_panel.kicad_pcb"
FAB = HERE / "fab"
LIB = Path("/usr/share/kicad/footprints")

# --- Strip, MEASURED from an original -----------------------------------------
LENGTH = 148.0            # tip to tip, tabs included
WIDTH = 6.15
TAB_WIDTH = 5.15          # same tab the v2/v3 board slots are sized for
THICKNESS = 1.0           # order the panel at 1.0 mm: the slots are 1.25 mm
BOARD_THICK = 1.6         # tower PCB
TAB_OUT_BOTTOM = 1.8      # tab sticks this far out under the tower PCB
FLANGE_THICK = 1.4        # core flange at the top
TAB_OUT_TOP = 1.5         # tab sticks this far out above the flange
BOTTOM_TAB = BOARD_THICK + TAB_OUT_BOTTOM     # 3.4 mm
TOP_TAB = FLANGE_THICK + TAB_OUT_TOP          # 2.9 mm
BODY = LENGTH - BOTTOM_TAB - TOP_TAB          # 141.7 mm: board top to flange underside
TIP_CHAMFER = 0.3         # eases the tabs into their slots

LED_FIRST = 7.0           # MEASURED: first LED center from the top tip
LED_PITCH = 11.6          # MEASURED
LED_COUNT = 10
R_VALUE = "200"           # ohms, one per LED: (5 - 0.2 - 2.0) / 200 = 14 mA each

PLUS_ON_RIGHT = True      # True for the v2 board (see the docstring)

# --- Panel ----------------------------------------------------------------------
STRIPS = 6
GAP = 2.0                 # milled gap between strips (JLCPCB's router is ~1-2 mm)
RAIL = 5.0                # frame width
END_GAP = 2.5             # tab tip to the end rails
BRIDGES = (24.0, 74.0, 124.0)   # mouse-bite tab centers, from the top tip
BRIDGE_LEN = 2.4
BITE_DRILL = 0.5
BITE_PITCH = 0.8
X0, Y0 = 100.0, 100.0     # panel's top-left corner on the sheet

PITCH = WIDTH + GAP
PANEL_W = 2 * (RAIL + GAP) + STRIPS * WIDTH + (STRIPS - 1) * GAP
PANEL_H = LENGTH + 2 * (RAIL + END_GAP)
TIP_Y = Y0 + RAIL + END_GAP                         # top tip of every strip


def strip_cx(n):
    return X0 + RAIL + GAP + WIDTH / 2 + n * PITCH


board = pcbnew.NewBoard(str(OUT))
ds = board.GetDesignSettings()
ds.SetCopperLayerCount(2)
ds.SetBoardThickness(pcbnew.FromMM(THICKNESS))
ds.m_CopperEdgeClearance = pcbnew.FromMM(0.3)
nets = {}


def V(x, y):
    return pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))


def net(name):
    if name not in nets:
        n = pcbnew.NETINFO_ITEM(board, name)
        board.Add(n)
        nets[name] = n
    return nets[name]


def seg(a, b, layer, width=0.1):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(V(*a))
    s.SetEnd(V(*b))
    s.SetLayer(layer)
    s.SetWidth(pcbnew.FromMM(width))
    board.Add(s)


def text(msg, x, y, size=1.0, layer=pcbnew.F_SilkS, rot=0.0):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(msg)
    t.SetPosition(V(x, y))
    t.SetLayer(layer)
    t.SetTextSize(V(size, size))
    t.SetTextThickness(pcbnew.FromMM(size * 0.15))
    t.SetTextAngleDegrees(rot)
    if layer == pcbnew.B_SilkS:
        t.SetMirrored(True)
    board.Add(t)


def track(a, b, netname, layer=pcbnew.F_Cu, width=0.4):
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(V(*a))
    t.SetEnd(V(*b))
    t.SetLayer(layer)
    t.SetWidth(pcbnew.FromMM(width))
    t.SetNet(net(netname))
    board.Add(t)


def via(pos, netname):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(V(*pos))
    v.SetWidth(pcbnew.FromMM(0.6))
    v.SetDrill(pcbnew.FromMM(0.3))
    v.SetNet(net(netname))
    board.Add(v)


def zone(x0, y0, x1, y1, netname, layer=pcbnew.B_Cu):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    z.SetNet(net(netname))
    z.SetLocalClearance(pcbnew.FromMM(0.3))
    z.SetMinThickness(pcbnew.FromMM(0.25))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    poly = z.Outline()
    poly.NewOutline()
    for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        poly.Append(pcbnew.FromMM(x), pcbnew.FromMM(y))
    board.Add(z)


def smd_pad(fp, number, x, y, w, h, netname=None, paste=True):
    pad = pcbnew.PAD(fp)
    pad.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
    pad.SetShape(pcbnew.PAD_SHAPE_ROUNDRECT)
    pad.SetRoundRectRadiusRatio(0.15)
    pad.SetSize(V(w, h))
    pad.SetNumber(number)
    layers = pcbnew.LSET(pcbnew.F_Cu).AddLayer(pcbnew.F_Mask)
    if paste:
        layers.AddLayer(pcbnew.F_Paste)
    pad.SetLayerSet(layers)
    fp.Add(pad)
    pad.SetPosition(V(x, y))
    pad.SetLocalCoord()
    if netname:
        pad.SetNet(net(netname))
    return pad


def npth(fp, x, y, drill):
    pad = pcbnew.PAD(fp)
    pad.SetAttribute(pcbnew.PAD_ATTRIB_NPTH)
    pad.SetShape(pcbnew.PAD_SHAPE_CIRCLE)
    pad.SetSize(V(drill, drill))
    pad.SetDrillSize(V(drill, drill))
    pad.SetLayerSet(pad.UnplatedHoleMask())
    fp.Add(pad)
    pad.SetPosition(V(x, y))
    pad.SetLocalCoord()


def fp_line(fp, a, b, layer, width):
    s = pcbnew.FP_SHAPE(fp)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(V(*a))
    s.SetEnd(V(*b))
    s.SetLayer(layer)
    s.SetWidth(pcbnew.FromMM(width))
    fp.Add(s)
    s.SetLocalCoord()


def mechanical(ref, x, y):
    """A footprint that is not a part: kept out of the BOM and placement files."""
    fp = pcbnew.FOOTPRINT(board)
    fp.SetReference(ref)
    fp.Reference().SetVisible(False)
    fp.Value().SetVisible(False)
    fp.SetPosition(V(x, y))
    fp.SetAttributes(pcbnew.FP_EXCLUDE_FROM_POS_FILES | pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_BOARD_ONLY)
    board.Add(fp)
    return fp


def led(ref, x, y, cathode_net, anode_net):
    """PLCC-2 3528 red LED, cathode toward the top of the strip.

    Lands for a 3.5 x 2.8 mm PLCC-2: two 2.4 x 1.4 mm pads 2.9 mm apart,
    the same for either polarity, so a part whose marking is the other way
    round is fixed by rotating it 180 degrees in JLCPCB's placement preview."""
    fp = pcbnew.FOOTPRINT(board)
    fp.SetFPID(pcbnew.LIB_ID("redlight", "LED_PLCC-2_3528"))
    fp.SetReference(ref)
    fp.SetValue("Red 3528 LED")
    fp.Reference().SetVisible(False)
    fp.Value().SetLayer(pcbnew.F_Fab)
    fp.Value().SetVisible(False)
    fp.SetPosition(V(x, y))
    fp.SetAttributes(pcbnew.FP_SMD)
    board.Add(fp)
    # Footprint drawn pin 1 (cathode) on the left, then turned so it points up.
    smd_pad(fp, "1", x - 1.45, y, 1.4, 2.4, cathode_net)
    smd_pad(fp, "2", x + 1.45, y, 1.4, 2.4, anode_net)
    # Cathode bar beside pad 1, then the body outline on the fab layer.
    fp_line(fp, (x - 2.5, y - 1.0), (x - 2.5, y + 1.0), pcbnew.F_SilkS, 0.15)
    for a, b in (((-1.75, -1.4), (1.75, -1.4)), ((1.75, -1.4), (1.75, 1.4)),
                 ((1.75, 1.4), (-1.75, 1.4)), ((-1.75, 1.4), (-1.75, -1.4))):
        fp_line(fp, (x + a[0], y + a[1]), (x + b[0], y + b[1]), pcbnew.F_Fab, 0.1)
    for a, b in (((-2.3, -1.6), (2.3, -1.6)), ((2.3, -1.6), (2.3, 1.6)),
                 ((2.3, 1.6), (-2.3, 1.6)), ((-2.3, 1.6), (-2.3, -1.6))):
        fp_line(fp, (x + a[0], y + a[1]), (x + b[0], y + b[1]), pcbnew.F_CrtYd, 0.05)
    fp.SetOrientationDegrees(-90)     # pin 1 (cathode) up
    return fp


def resistor(ref, x, y, nets_by_pad):
    fp = pcbnew.FootprintLoad(str(LIB / "Resistor_SMD.pretty"), "R_0603_1608Metric")
    fp.SetReference(ref)
    fp.SetValue(R_VALUE)
    fp.Reference().SetVisible(False)
    fp.SetPosition(V(x, y))
    board.Add(fp)
    for pad in fp.Pads():
        pad.SetNet(net(nets_by_pad[pad.GetNumber()]))
    return fp


# --- Outline ---------------------------------------------------------------------
def strip_shape(cx):
    t, c = TIP_Y, TIP_CHAMFER
    hw, ht = WIDTH / 2, TAB_WIDTH / 2
    top_tab = Polygon([(cx - ht, t + TOP_TAB), (cx - ht, t + c), (cx - ht + c, t),
                       (cx + ht - c, t), (cx + ht, t + c), (cx + ht, t + TOP_TAB)])
    body = box(cx - hw, t + TOP_TAB, cx + hw, t + TOP_TAB + BODY)
    b = t + LENGTH
    bottom_tab = Polygon([(cx - ht, b - BOTTOM_TAB), (cx + ht, b - BOTTOM_TAB),
                          (cx + ht, b - c), (cx + ht - c, b), (cx - ht + c, b), (cx - ht, b - c)])
    return unary_union([top_tab, body, bottom_tab])


frame = box(X0, Y0, X0 + PANEL_W, Y0 + PANEL_H).difference(
    box(X0 + RAIL, Y0 + RAIL, X0 + PANEL_W - RAIL, Y0 + PANEL_H - RAIL))
parts = [frame] + [strip_shape(strip_cx(n)) for n in range(STRIPS)]
bites = []          # (x of the strip edge, y center): mouse-bite hole rows
# A bridge across every gap: rail-strip, strip-strip, strip-rail.
edges_x = [X0 + RAIL] + [strip_cx(n) + s * WIDTH / 2 for n in range(STRIPS) for s in (-1, 1)] \
    + [X0 + PANEL_W - RAIL]
for k in range(0, len(edges_x), 2):
    left, right = edges_x[k], edges_x[k + 1]
    for by in BRIDGES:
        y = TIP_Y + by
        parts.append(box(left - 0.01, y - BRIDGE_LEN / 2, right + 0.01, y + BRIDGE_LEN / 2))
        # Holes only on the strip side(s), so the break line is the strip's own edge.
        if k > 0:
            bites.append((left, y))
        if k + 2 < len(edges_x):
            bites.append((right, y))
outline = unary_union(parts)
assert outline.geom_type == "Polygon", "panel outline should be one piece"
for ring in [outline.exterior] + list(outline.interiors):
    pts = list(ring.coords)
    for a, b in zip(pts, pts[1:]):
        seg(a, b, pcbnew.Edge_Cuts)

for i, (x, y) in enumerate(bites):
    fp = mechanical(f"MB{i + 1}", x, y)
    n = int(BRIDGE_LEN / BITE_PITCH)
    for k in range(n):
        npth(fp, x, y + (k - (n - 1) / 2) * BITE_PITCH, BITE_DRILL)

# --- Frame: fiducials, tooling holes, labels -------------------------------------
fid_lib = str(LIB / "Fiducial.pretty")
for i, (x, y) in enumerate(((X0 + RAIL / 2, Y0 + 12), (X0 + PANEL_W - RAIL / 2, Y0 + 12),
                            (X0 + RAIL / 2, Y0 + PANEL_H - 12))):
    fp = pcbnew.FootprintLoad(fid_lib, "Fiducial_1mm_Mask2mm")
    fp.SetReference(f"FID{i + 1}")
    fp.Reference().SetVisible(False)
    fp.Value().SetVisible(False)
    fp.SetPosition(V(x, y))
    fp.SetAttributes(pcbnew.FP_EXCLUDE_FROM_POS_FILES | pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_BOARD_ONLY)
    board.Add(fp)
for i, (x, y) in enumerate(((X0 + RAIL / 2, Y0 + RAIL / 2), (X0 + PANEL_W - RAIL / 2, Y0 + RAIL / 2),
                            (X0 + RAIL / 2, Y0 + PANEL_H - RAIL / 2),
                            (X0 + PANEL_W - RAIL / 2, Y0 + PANEL_H - RAIL / 2))):
    npth(mechanical(f"TH{i + 1}", x, y), x, y, 1.152)       # JLCPCB tooling hole size

text("REDLIGHT TOWER STRIPS  6-UP", X0 + PANEL_W / 2, Y0 + RAIL / 2, size=1.4)
text("JLCJLCJLCJLC", X0 + PANEL_W / 2, Y0 + PANEL_H - RAIL / 2, size=1.4)   # order number goes here
text("1.0 mm FR-4", X0 + PANEL_W - RAIL / 2, Y0 + PANEL_H / 2, size=1.4, rot=90)

# --- Strips ------------------------------------------------------------------------
ref = 1
for n in range(STRIPS):
    cx = strip_cx(n)
    s = n + 1
    plus, minus = f"/S{s}+", f"/S{s}-"
    side = 1 if PLUS_ON_RIGHT else -1
    hw = WIDTH / 2
    body_top, body_bot = TIP_Y + TOP_TAB, TIP_Y + TOP_TAB + BODY

    # Back layer: two rails the full length of the body, + and -.
    pour_in, pour_out = 0.2, hw - 0.55     # 0.55 mm from the edge clears the mouse bites
    y0, y1 = body_top + 0.5, body_bot - 0.5
    zone(cx + side * pour_in, y0, cx + side * pour_out, y1, plus)
    zone(cx - side * pour_out, y0, cx - side * pour_in, y1, minus)
    via_x = 2.05

    for k in range(LED_COUNT):
        yc = TIP_Y + LED_FIRST + k * LED_PITCH
        anode = f"/S{s}_A{k + 1}"
        led(f"D{ref}", cx, yc, minus, anode)
        # Cathode pad (top) -> via to the "-" rail.
        track((cx, yc - 1.45), (cx - side * via_x, yc - 1.45), minus)
        via((cx - side * via_x, yc - 1.45), minus)
        # Anode pad (bottom) -> resistor below the LED -> via to the "+" rail.
        ry = yc + 4.2
        resistor(f"R{ref}", cx, ry, {"1": anode, "2": plus} if side > 0 else {"1": plus, "2": anode})
        track((cx - side * 0.775, yc + 1.45), (cx - side * 0.775, ry), anode)
        track((cx + side * 0.775, ry), (cx + side * via_x, ry), plus)
        via((cx + side * via_x, ry), plus)
        ref += 1

    # Bottom tab: exposed pads on the LED face, soldered to the tower PCB's
    # pads on the outside of each slot. They start 1.8 mm up the body so the
    # solder fillet has copper to wet on the tower side of the board.
    fp = pcbnew.FOOTPRINT(board)
    fp.SetReference(f"J{s}")
    fp.SetValue("tab")
    fp.Reference().SetVisible(False)
    fp.Value().SetVisible(False)
    fp.SetPosition(V(cx, body_bot))
    fp.SetAttributes(pcbnew.FP_EXCLUDE_FROM_POS_FILES | pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_BOARD_ONLY)
    board.Add(fp)
    tip = TIP_Y + LENGTH
    py0, py1 = body_bot - 1.8, tip - 0.35
    pw = TAB_WIDTH / 2 - 0.25 - 0.35                    # 0.5 mm gap, 0.35 mm from the edge
    pcx = 0.25 + pw / 2
    smd_pad(fp, "+", cx + side * pcx, (py0 + py1) / 2, pw, py1 - py0, plus, paste=False)
    smd_pad(fp, "-", cx - side * pcx, (py0 + py1) / 2, pw, py1 - py0, minus, paste=False)
    for dy in (0.4, 1.2):
        via((cx + side * pcx, py0 + dy), plus)
        via((cx - side * pcx, py0 + dy), minus)

    # Markings: "+"/"-" above the tab pads; strip label on the back.
    text("+", cx + side * 1.5, py0 - 1.0, size=0.9)
    text("-", cx - side * 1.5, py0 - 1.0, size=0.9)
    text("TOP", cx, body_top + 2.2, size=0.9, layer=pcbnew.B_SilkS)
    text("REDLIGHT STRIP  FOR V2 BOARD" if PLUS_ON_RIGHT else "REDLIGHT STRIP  FOR V3 BOARD",
         cx, TIP_Y + 70, size=1.0, layer=pcbnew.B_SilkS, rot=90)

pcbnew.ZONE_FILLER(board).Fill(board.Zones())
board.Save(str(OUT))
print(f"panel {PANEL_W:.2f} x {PANEL_H:.2f} mm, {STRIPS} strips, body {BODY:.1f} mm "
      f"(tabs {TOP_TAB:.1f} top / {BOTTOM_TAB:.1f} bottom) -> {OUT.name}")

# --- DRC ---------------------------------------------------------------------------
FAB.mkdir(exist_ok=True)
report = FAB / "drc.rpt"
pcbnew.WriteDRCReport(pcbnew.LoadBoard(str(OUT)), str(report), pcbnew.EDA_UNITS_MILLIMETRES, True)
rpt = report.read_text()
unconnected = int(re.search(r"Found (\d+) unconnected", rpt).group(1))
errors = sorted({l for l in rpt.splitlines() if l.startswith("[") and not l.startswith(("[silk_", "[lib_footprint_issues"))})
print(f"DRC: {unconnected} unconnected, {len(errors)} kinds of error")
for l in errors:
    print("  ", l)

# --- Fabrication and assembly files -------------------------------------------------
for f in FAB.glob("*"):
    if f.name != "drc.rpt":
        f.unlink()
gerb = FAB / "gerbers"
gerb.mkdir()
layers = "F.Cu,B.Cu,F.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts"
subprocess.run(["kicad-cli", "pcb", "export", "gerbers", "--layers", layers,
                "--subtract-soldermask", "-o", str(gerb) + "/", str(OUT)], check=True,
               stdout=subprocess.DEVNULL)
subprocess.run(["kicad-cli", "pcb", "export", "drill", "--format", "excellon",
                "--excellon-separate-th", "-o", str(gerb) + "/", str(OUT)], check=True,
               stdout=subprocess.DEVNULL)
with zipfile.ZipFile(FAB / "redlight-strip-gerbers.zip", "w", zipfile.ZIP_DEFLATED) as z:
    for f in sorted(gerb.iterdir()):
        z.write(f, f.name)
for f in gerb.iterdir():
    f.unlink()
gerb.rmdir()

raw = FAB / "pos_raw.csv"
subprocess.run(["kicad-cli", "pcb", "export", "pos", "--format", "csv", "--units", "mm",
                "--side", "front", "-o", str(raw), str(OUT)], check=True, stdout=subprocess.DEVNULL)
rows = list(csv.DictReader(raw.open()))
raw.unlink()
with (FAB / "strip_cpl.csv").open("w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
    for r in rows:
        w.writerow([r["Ref"], r["PosX"], r["PosY"], "Top", f"{float(r['Rot']) % 360:g}"])

leds = [r["Ref"] for r in rows if r["Ref"].startswith("D")]
res = [r["Ref"] for r in rows if r["Ref"].startswith("R")]
with (FAB / "strip_bom.csv").open("w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
    w.writerow(["Red LED, PLCC-2 3528, 620-630 nm, 20 mA", ",".join(leds), "PLCC-2 3528", ""])
    w.writerow([f"{R_VALUE} ohm 1% 0603", ",".join(res), "0603", "C8218"])
print(f"{len(leds)} LEDs, {len(res)} resistors per panel -> {FAB.relative_to(HERE.parent.parent)}/")
