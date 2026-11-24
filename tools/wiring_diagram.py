"""Draw the whole-device wiring diagram.

    python3 tools/wiring_diagram.py      # writes docs/wiring_diagram.svg

Blocks are laid out roughly where the parts sit in the housing (tower on top,
main board under it, battery insert at the bottom); it is a wiring diagram,
not a scale drawing.
"""
from html import escape
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "docs" / "wiring_diagram.svg"

INK, MUTED = "#1c2321", "#5f6b66"
RED, BLACK, ORANGE, BLUE, GREY = "#d2362b", "#1b1f23", "#e08a1e", "#2f6fb5", "#7d8791"
W, H = 1500, 1010
o = []


def rect(x, y, w, h, fill, stroke=INK, sw=1.6, rx=8, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    o.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" '
             f'stroke-width="{sw}"{d}/>')


def text(x, y, msg, size=15, fill=INK, weight=400, anchor="start"):
    o.append(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{fill}" '
             f'text-anchor="{anchor}">{escape(msg)}</text>')


def block(x, y, w, h, title, lines=(), fill="#ffffff"):
    rect(x, y, w, h, fill)
    cy = y + h / 2 - (len(lines) * 18) / 2 + 5
    text(x + w / 2, cy, title, 16, INK, 700, "middle")
    for i, ln in enumerate(lines):
        text(x + w / 2, cy + 19 * (i + 1), ln, 13, MUTED, 400, "middle")


def zone(x, y, w, h, label):
    rect(x, y, w, h, "#f6f8f4", "#9aa59f", 1.4, 14, "7 6")
    text(x + 14, y + 22, label, 14, MUTED, 700)


def wire(pts, color, width=4, dash=None):
    d = " ".join(f"{x},{y}" for x, y in pts)
    e = f' stroke-dasharray="{dash}"' if dash else ""
    o.append(f'<polyline points="{d}" fill="none" stroke="#ffffff" stroke-width="{width + 4}" '
             f'stroke-linejoin="round" stroke-linecap="round"/>')
    o.append(f'<polyline points="{d}" fill="none" stroke="{color}" stroke-width="{width}" '
             f'stroke-linejoin="round" stroke-linecap="round"{e}/>')


def dot(x, y, color):
    o.append(f'<circle cx="{x}" cy="{y}" r="6" fill="{color}" stroke="#ffffff" stroke-width="2"/>')


def pin(x, y, label, color, above=True):
    o.append(f'<circle cx="{x}" cy="{y}" r="8" fill="#ffffff" stroke="{color}" stroke-width="3"/>')
    text(x, y - 14 if above else y + 26, label, 13, INK, 700, "middle")


def tag(x, y, msg, color, anchor="start"):
    o.append(f'<text x="{x}" y="{y}" font-size="13" font-weight="700" fill="{color}" text-anchor="{anchor}" '
             f'paint-order="stroke" stroke="#ffffff" stroke-width="4" stroke-linejoin="round">{escape(msg)}</text>')


o.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
         f'font-family="Inter, \'DejaVu Sans\', Arial, sans-serif">')
o.append(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')
text(30, 44, "Redlight: whole-device wiring", 28, INK, 700)
text(30, 70, "Laid out roughly as the parts sit in the housing. Not to scale.", 15, MUTED)

# --- Zones ---------------------------------------------------------------------
zone(540, 95, 920, 205, "Under the red dome")
zone(540, 318, 920, 340, "Main board (under the tower)")
zone(1150, 676, 310, 130, "Below the board")
zone(30, 676, 1090, 314, "Battery insert and housing (bottom of the light)")

# --- Tower and board ------------------------------------------------------------
block(820, 135, 300, 130, "Light tower", ["six LED strips, D1 to D6", "soldered into the board"], "#fde9e7")
block(580, 372, 220, 80, "XIAO ESP32-C6", ["WiFi, USB-C for flashing"], "#e3f1ea")
block(860, 372, 200, 80, "Driver chip (U2)", ["switches the six strips"], "#e9ecef")
block(1120, 372, 220, 80, "Amp (MAX98357A)", ["on the board"], "#eee6f8")
block(1120, 500, 300, 62, "Buttons SW1 to SW3", ["TEST, VOL+, VOL−"], "#fbe6df")

wire([(960, 372), (960, 265)], GREY, 5)
tag(972, 326, "6 strips", GREY)
wire([(800, 412), (860, 412)], GREY, 3)
tag(830, 398, "lights", GREY, "middle")
wire([(760, 452), (760, 476), (1230, 476), (1230, 452)], GREY, 3)
tag(995, 492, "audio", GREY, "middle")
wire([(1120, 531), (640, 531), (640, 452)], GREY, 3)
tag(880, 547, "buttons", GREY, "middle")

# J1 pads on the board's lower edge.
text(735, 598, "J1 solder pads (speaker side of the board)", 13, MUTED, 700, "middle")
for x, name, col in ((600, "VBAT", ORANGE), (700, "GND", BLACK), (870, "5V", RED)):
    pin(x, 640, name, col, above=True)

# --- Speaker ----------------------------------------------------------------------
block(1190, 712, 230, 76, "Speaker", ["4 Ω, 3 W (original)"], "#e7eef8")
wire([(1340, 404), (1440, 404), (1440, 750), (1420, 750)], BLUE, 3)
wire([(1340, 420), (1428, 420), (1428, 736), (1420, 736)], BLUE, 3)
tag(1416, 620, "speaker + and −", BLUE, "end")

# --- Battery side -------------------------------------------------------------------
block(60, 770, 270, 92, "4 × 18650 cells", ["all in parallel", "two 2-cell holders"], "#fff3d9")
block(380, 782, 90, 36, "3 A fuse", [], "#ffffff")
block(60, 896, 190, 72, "5 V, 2 A adapter", ["centre positive"], "#ffffff")
block(300, 896, 170, 72, "Barrel jack", ["5.5 × 2.1 mm"], "#ffffff")
block(560, 770, 300, 198, "Charge / boost module", ["DFRobot DFR0446"], "#e3f1ea")
block(790, 690, 160, 42, "Slide switch", [], "#ffffff")

# Battery + through the fuse to BAT+, with the gauge tap up to VBAT.
wire([(330, 800), (380, 800)], ORANGE)
wire([(470, 800), (560, 800)], ORANGE)
wire([(510, 800), (510, 668), (600, 668), (600, 648)], ORANGE, 2.5)
dot(510, 800, ORANGE)
tag(520, 690, "battery gauge (thin wire)", ORANGE)
wire([(330, 840), (560, 840)], BLACK)
# Adapter -> jack -> VIN.
wire([(250, 918), (300, 918)], RED)
wire([(250, 946), (300, 946)], BLACK)
wire([(470, 918), (560, 918)], RED)
wire([(470, 946), (560, 946)], BLACK)
# Module output: ground straight up to J1 GND, + through the switch to J1 5V.
wire([(700, 770), (700, 648)], BLACK)
wire([(830, 770), (830, 732)], RED)
wire([(870, 690), (870, 648)], RED)

for x, y, name, anchor in ((574, 805, "BAT+", "start"), (574, 845, "BAT−", "start"),
                           (574, 923, "VIN +", "start"), (574, 951, "VIN −", "start")):
    text(x, y, name, 13, INK, 700, anchor)
text(700, 790, "OUT −", 13, INK, 700, "middle")
text(830, 790, "OUT +", 13, INK, 700, "middle")

# --- Legend and notes -----------------------------------------------------------------
x0, y = 30, 118
text(x0, y, "Wires", 17, INK, 700)
for i, (col, name) in enumerate(((RED, "5 V"), (BLACK, "ground"), (ORANGE, "battery +"),
                                 (BLUE, "speaker"), (GREY, "signals on the board (no wiring needed)"))):
    yy = y + 26 + i * 24
    o.append(f'<line x1="{x0}" y1="{yy - 5}" x2="{x0 + 44}" y2="{yy - 5}" stroke="{col}" stroke-width="5" '
             f'stroke-linecap="round"/>')
    text(x0 + 58, yy, name, 14)
y += 26 + 5 * 24 + 22
text(x0, y, "Notes", 17, INK, 700)
notes = [
    ("Power wires", ["22 AWG or thicker for the red and black wires.",
                     "The battery-gauge wire carries almost nothing."]),
    ("Fuse", ["In the battery + lead, close to the cells."]),
    ("Slide switch", ["Cuts 5 V to the board only. The module stays on the",
                      "cells, so it charges with the light switched off."]),
    ("Module connections", ["BAT+ / BAT− pads; OUT on the big USB socket's two",
                            "outer pins; VIN at the capacitor beside the VIN label.",
                            "Confirm each with a meter before soldering."]),
    ("Speaker", ["Both wires go to the amp. Neither goes to ground."]),
    ("Reworked v2 board", ["Wires W1 and W2 already sit on J1's GND and 5V",
                           "pads. The amp also needs a wire from J1 5V to VIN."]),
]
y += 24
for head, lines in notes:
    text(x0, y, head, 14, INK, 700)
    y += 19
    for ln in lines:
        text(x0, y, ln, 13, MUTED)
        y += 17
    y += 8

o.append("</svg>")
OUT.write_text("\n".join(o))
print(f"wrote {OUT}")
