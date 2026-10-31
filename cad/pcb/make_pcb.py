"""Generate the Redlight replacement tower PCB (KiCad 7+).

    python3 cad/pcb/make_pcb.py            # place parts, write redlight.kicad_pcb
    python3 cad/pcb/route.py               # autoroute, pour, DRC, gerbers

The board replaces the original "Red Light 2.0" PCB: same outline, the LED
strip tabs pass through six slots around the tower screw. The tower stands on
the top (F) side; every component is on the bottom (B) side, like the original.

Coordinates below are millimetres in a top view (looking at the tower side),
origin at the tower screw, +Y toward the end the old Imp module was on.
"""
import math
from pathlib import Path

import pcbnew

HERE = Path(__file__).parent
OUT = HERE / "redlight.kicad_pcb"
LIB = Path("/usr/share/kicad/footprints")

# --- Measured board geometry -------------------------------------------------
DIAMETER = 109.5
FLAT_WIDTH = 74.15
SCREW_HOLE = 4.0

# --- LED strip tabs ------------------------------------------------------------
TAB_RADIUS = 6.7          # screw center to tab center
TAB_WIDTH = 6.0
TAB_THICK = 1.0           # ESTIMATE until measured
SLOT_CLEAR = 0.25         # slot = tab + this, each direction
PLUS_ON_CCW_SIDE = True   # which half of each tab is "+" (looking from the top)

# --- Estimated housing features (check with the fit print) -------------------
TEST_BUTTON = (1.0, -42.0)  # angled tact switch, actuator toward the edge

ORIGIN = (100.0, 100.0)     # where (0, 0) sits on the KiCad sheet


def P(x, y):
    """Top-view mm -> KiCad internal units (KiCad's Y axis points down)."""
    return pcbnew.VECTOR2I(pcbnew.FromMM(ORIGIN[0] + x), pcbnew.FromMM(ORIGIN[1] - y))


board = pcbnew.NewBoard(str(OUT))
board.GetDesignSettings().SetCopperLayerCount(2)
nets = {}


def net(name):
    if name not in nets:
        n = pcbnew.NETINFO_ITEM(board, name)
        board.Add(n)
        nets[name] = n
    return nets[name]


def place(lib, name, ref, value, x, y, rot=0.0, bottom=True):
    """Bottom parts are flipped left-right, as if you turned the board over
    sideways: a footprint vector at angle a ends up at 180 - a - rot."""
    fp = pcbnew.FootprintLoad(str(LIB / f"{lib}.pretty"), name)
    fp.SetReference(ref)
    fp.SetValue(value)
    fp.SetPosition(P(x, y))
    fp.SetOrientationDegrees(rot)
    board.Add(fp)
    if bottom:
        fp.Flip(fp.GetPosition(), True)
    return fp


def connect(fp, pad_nets):
    for pad in fp.Pads():
        if pad.GetNumber() in pad_nets:
            pad.SetNet(net(pad_nets[pad.GetNumber()]))


def edge_line(a, b, layer=pcbnew.Edge_Cuts, width=0.1):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(P(*a))
    s.SetEnd(P(*b))
    s.SetLayer(layer)
    s.SetWidth(pcbnew.FromMM(width))
    board.Add(s)


def edge_arc(a, mid, b):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_ARC)
    s.SetArcGeometry(P(*a), P(*mid), P(*b))
    s.SetLayer(pcbnew.Edge_Cuts)
    s.SetWidth(pcbnew.FromMM(0.1))
    board.Add(s)


def text(msg, x, y, size=1.5, layer=pcbnew.F_SilkS, rot=0.0):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(msg)
    t.SetPosition(P(x, y))
    t.SetLayer(layer)
    t.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(size), pcbnew.FromMM(size)))
    t.SetTextThickness(pcbnew.FromMM(size * 0.15))
    t.SetTextAngleDegrees(rot)
    if layer in (pcbnew.B_SilkS, pcbnew.B_Cu):
        t.SetMirrored(True)
    board.Add(t)


# --- Outline: circle with two flats --------------------------------------------
r = DIAMETER / 2
xf = FLAT_WIDTH / 2
yf = math.sqrt(r * r - xf * xf)
edge_arc((-xf, yf), (0, r), (xf, yf))
edge_line((xf, yf), (xf, -yf))
edge_arc((xf, -yf), (0, -r), (-xf, -yf))
edge_line((-xf, -yf), (-xf, yf))

# Tower screw: plain NPTH hole.
hole = pcbnew.FootprintLoad(str(LIB / "MountingHole.pretty"), "MountingHole_3.2mm_M3")
hole.SetReference("H1")
hole.SetValue("tower screw")
hole.Value().SetVisible(False)
hole.SetPosition(P(0, 0))
for pad in hole.Pads():
    pad.SetDrillSize(pcbnew.VECTOR2I(pcbnew.FromMM(SCREW_HOLE), pcbnew.FromMM(SCREW_HOLE)))
    pad.SetSize(pcbnew.VECTOR2I(pcbnew.FromMM(SCREW_HOLE), pcbnew.FromMM(SCREW_HOLE)))
board.Add(hole)


# --- LED strip tabs: slot + two pads per strip on both copper layers -----------
def tab(i):
    deg = 60 * i
    a = math.radians(deg)
    ux, uy = math.cos(a), math.sin(a)     # radial
    tx, ty = -uy, ux                      # tangential (counter-clockwise)

    def at(rad, tan):
        return (rad * ux + tan * tx, rad * uy + tan * ty)

    # Slot outline on Edge.Cuts.
    hw = (TAB_THICK + SLOT_CLEAR) / 2
    hl = (TAB_WIDTH + SLOT_CLEAR) / 2
    corners = [at(TAB_RADIUS + dr, dt) for dr, dt in ((-hw, -hl), (hw, -hl), (hw, hl), (-hw, hl))]
    for k in range(4):
        edge_line(corners[k], corners[(k + 1) % 4])

    # Pads along the outside edge of the slot, split into + and - halves.
    fp = pcbnew.FOOTPRINT(board)
    fp.SetReference(f"LED{i + 1}")
    fp.SetValue("strip tab")
    fp.Reference().SetVisible(False)
    fp.Value().SetVisible(False)
    fp.SetPosition(P(*at(TAB_RADIUS, 0)))
    board.Add(fp)
    pad_depth, gap = 1.6, 0.5
    pad_len = (TAB_WIDTH - gap) / 2
    rad = TAB_RADIUS + hw + 0.25 + pad_depth / 2
    plus_side = 1 if PLUS_ON_CCW_SIDE else -1
    for name, side in (("+", plus_side), ("-", -plus_side)):
        for layer_set in (pcbnew.LSET(pcbnew.F_Cu), pcbnew.LSET(pcbnew.B_Cu)):
            pad = pcbnew.PAD(fp)
            pad.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
            pad.SetShape(pcbnew.PAD_SHAPE_RECT)
            pad.SetSize(pcbnew.VECTOR2I(pcbnew.FromMM(pad_depth), pcbnew.FromMM(pad_len)))
            pad.SetNumber(name)
            layers = layer_set
            layers.AddLayer(pcbnew.F_Mask if layer_set.Contains(pcbnew.F_Cu) else pcbnew.B_Mask)
            pad.SetLayerSet(layers)
            fp.Add(pad)
            pad.SetPosition(P(*at(rad, side * (gap + pad_len) / 2)))
            pad.SetOrientationDegrees(deg)
            pad.SetLocalCoord()  # KiCad 7 saves footprint-relative positions
            pad.SetNet(net("+5V") if name == "+" else net(f"/STRIP{i + 1}-"))
    # Tie the top and bottom pads of each half together.
    for name, side in (("+", plus_side), ("-", -plus_side)):
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(P(*at(rad + pad_depth / 2 + 0.6, side * (gap + pad_len) / 2)))
        v.SetDrill(pcbnew.FromMM(0.4))
        v.SetWidth(pcbnew.FromMM(0.8))
        v.SetNet(net("+5V") if name == "+" else net(f"/STRIP{i + 1}-"))
        board.Add(v)
        for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(P(*at(rad, side * (gap + pad_len) / 2)))
            t.SetEnd(v.GetPosition())
            t.SetWidth(pcbnew.FromMM(0.6))
            t.SetLayer(layer)
            t.SetNet(v.GetNet())
            board.Add(t)
    text(f"D{i + 1}", *at(TAB_RADIUS + 5.6, 0), size=1.2)
    text(f"D{i + 1}", *at(TAB_RADIUS + 5.6, 0), size=1.2, layer=pcbnew.B_SilkS)
    px, py = at(rad + 2.6, plus_side * (gap + pad_len) / 2)
    text("+", px, py, size=1.0)
    return at


for i in range(6):
    tab(i)


# --- XIAO ESP32-C6, socketed, on the bottom side -----------------------------------
# Built as a footprint in the XIAO's own top view (USB up): left column
# D0..D6, right column 5V, GND, 3V3, D10, D9, D8, D7. Flipping it to the
# bottom side mirrors it correctly.
XIAO_PINS_LEFT = ["D0", "D1", "D2", "D3", "D4", "D5", "D6"]
XIAO_PINS_RIGHT = ["5V", "GND", "3V3", "D10", "D9", "D8", "D7"]
XIAO_NETS = {
    "D0": "/LIGHT1", "D1": "/LIGHT2", "D6": "/LIGHT3",
    "D10": "/LIGHT4", "D4": "/LIGHT5", "D5": "/LIGHT6",
    "D8": "/I2S_BCLK", "D9": "/I2S_LRC", "D3": "/I2S_DIN",
    "D7": "/BUTTON", "D2": "/VSENSE", "5V": "+5V", "GND": "GND",
}


def xiao(x, y):
    fp = pcbnew.FOOTPRINT(board)
    fp.SetReference("U1")
    fp.SetValue("XIAO ESP32-C6")
    fp.SetPosition(P(x, y))
    board.Add(fp)
    org = fp.GetPosition()

    def rel(dx, dy):
        return pcbnew.VECTOR2I(org.x + pcbnew.FromMM(dx), org.y + pcbnew.FromMM(dy))

    for col, names in ((-7.62, XIAO_PINS_LEFT), (7.62, XIAO_PINS_RIGHT)):
        for k, name in enumerate(names):
            pad = pcbnew.PAD(fp)
            pad.SetAttribute(pcbnew.PAD_ATTRIB_PTH)
            pad.SetShape(pcbnew.PAD_SHAPE_RECT if name == "D0" else pcbnew.PAD_SHAPE_CIRCLE)
            pad.SetSize(pcbnew.VECTOR2I(pcbnew.FromMM(1.7), pcbnew.FromMM(1.7)))
            pad.SetDrillSize(pcbnew.VECTOR2I(pcbnew.FromMM(1.0), pcbnew.FromMM(1.0)))
            pad.SetLayerSet(pad.PTHMask())
            pad.SetNumber(name)
            fp.Add(pad)
            pad.SetPosition(rel(col, -7.62 + 2.54 * k))
            pad.SetLocalCoord()
            if name in XIAO_NETS:
                pad.SetNet(net(XIAO_NETS[name]))
    # Body outline (21 x 17.5 mm, USB end up) on silkscreen + courtyard.
    for layer, (w, h) in ((pcbnew.F_SilkS, (17.5, 21.0)), (pcbnew.F_CrtYd, (18.0, 22.5))):
        pts = [(-w / 2, -h / 2 - 0.75), (w / 2, -h / 2 - 0.75), (w / 2, h / 2 - 0.75), (-w / 2, h / 2 - 0.75)]
        for k in range(4):
            s = pcbnew.FP_SHAPE(fp)
            s.SetShape(pcbnew.SHAPE_T_SEGMENT)
            s.SetStart(rel(*pts[k]))
            s.SetEnd(rel(*pts[(k + 1) % 4]))
            s.SetLocalCoord()
            s.SetLayer(layer)
            s.SetWidth(pcbnew.FromMM(0.12 if layer == pcbnew.F_SilkS else 0.05))
            fp.Add(s)
    t = pcbnew.FP_TEXT(fp)
    t.SetText("USB")
    t.SetLayer(pcbnew.F_SilkS)
    t.SetPosition(rel(0, -9.5))
    t.SetLocalCoord()
    fp.Add(t)
    fp.Flip(fp.GetPosition(), True)
    return fp


xiao(0, 36)

# --- LED driver: TBD62083APG (ULN2803A pinout) in a DIP-18 socket ----------------
u2 = place("Package_DIP", "DIP-18_W7.62mm_Socket", "U2", "TBD62083APG", 31.0, 10.16, rot=0)
drv = {"9": "GND", "10": "+5V", "7": "GND", "8": "GND"}
for k in range(6):
    drv[str(k + 1)] = f"/LIGHT{k + 1}"
    drv[str(18 - k)] = f"/OUT{k + 1}"
connect(u2, drv)

# --- LED series resistors, one per strip, radiating from the tower ---------------
for k in range(6):
    deg = 60 * k
    a = math.radians(deg)
    x, y = 12.2 * math.cos(a), 12.2 * math.sin(a)
    # Footprint pad 1 at origin, pad 2 at +7.62 along its X axis.
    rr = place("Resistor_THT", "R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal",
               f"R{k + 1}", "47R*", x, y, rot=180 - deg)
    connect(rr, {"1": f"/STRIP{k + 1}-", "2": f"/OUT{k + 1}"})

# --- Audio amp: MAX98357A breakout plugged into a 1x7 socket --------------------------
# Adafruit pin order: LRC, BCLK, DIN, GAIN, SD, GND, VIN. The module body sits
# over the board on the +Y side of the header.
amp = place("Connector_PinSocket_2.54mm", "PinSocket_1x07_P2.54mm_Vertical", "J3",
            "MAX98357A", -24.0, -41.0, rot=-90)
connect(amp, {"1": "/I2S_LRC", "2": "/I2S_BCLK", "3": "/I2S_DIN", "6": "GND", "7": "+5V"})
# Module footprint (Adafruit 3006: 17.8 x 19.4 mm) for reference.
_ax, _ay = -24.0 - 1.27, -41.0 - 1.3
for a, b in (((0, 0), (17.8, 0)), ((17.8, 0), (17.8, 19.4)), ((17.8, 19.4), (0, 19.4)), ((0, 19.4), (0, 0))):
    edge_line((_ax + a[0], _ay + a[1]), (_ax + b[0], _ay + b[1]), layer=pcbnew.B_SilkS, width=0.12)
text("MAX98357A module", _ax + 8.9, _ay + 10, size=1.0, layer=pcbnew.B_SilkS)

# --- Power in: 5V, GND, VBAT from the UPS module and cell pack -----------------------
j1 = place("TerminalBlock_Phoenix", "TerminalBlock_Phoenix_MKDS-1,5-3-5.08_1x03_P5.08mm_Horizontal",
           "J1", "5V GND VBAT", 24.0, -36.0, rot=0)
connect(j1, {"1": "+5V", "2": "GND", "3": "/VBAT"})

c1 = place("Capacitor_THT", "CP_Radial_D8.0mm_P3.50mm", "C1", "470uF 10V", 24.0, -22.0, rot=90)
connect(c1, {"1": "+5V", "2": "GND"})
c2 = place("Capacitor_THT", "C_Disc_D5.0mm_W2.5mm_P5.00mm", "C2", "100nF", 32.0, -14.0, rot=0)
connect(c2, {"1": "+5V", "2": "GND"})

# --- Battery gauge divider: VBAT -> 100k -> VSENSE -> 100k -> GND -----------------
r7 = place("Resistor_THT", "R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal",
           "R7", "100k", 14.5, 27.0, rot=90)
connect(r7, {"1": "/VBAT", "2": "/VSENSE"})
r8 = place("Resistor_THT", "R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal",
           "R8", "100k", 18.5, 27.0, rot=90)
connect(r8, {"1": "/VSENSE", "2": "GND"})

# --- Button: angled tact switch at the housing's TEST button, plus a header ----------
sw = place("Button_Switch_THT", "SW_Tactile_SPST_Angled_PTS645Vx31-2LFS", "SW1", "TEST",
           TEST_BUTTON[0], TEST_BUTTON[1], rot=180)
connect(sw, {"1": "/BUTTON", "2": "GND"})
j2 = place("Connector_JST", "JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical", "J2", "BUTTON", -31.0, 10.0, rot=90)
connect(j2, {"1": "/BUTTON", "2": "GND"})

# --- Silkscreen --------------------------------------------------------------------
text("REDLIGHT v1", 0, -22, size=2.0)
text("tower side", 0, -25.5, size=1.2)
text("REDLIGHT v1", 0, 50.5, size=1.5, layer=pcbnew.B_SilkS)
text("5V  GND  VBAT", 19.0, -30.5, size=1.0, layer=pcbnew.B_SilkS)

board.Save(str(OUT))
print(f"wrote {OUT} with {len(list(board.GetFootprints()))} footprints, {len(nets)} nets")
