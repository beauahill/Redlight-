"""Draw assembly (parts placement) drawings for the tower PCB.

    python3 cad/pcb/assembly.py            # writes out/assembly_tower_side.svg
                                           #    and out/assembly_speaker_side.svg

Reads redlight.kicad_pcb directly (no KiCad needed), so the drawings always
match the board that was ordered. The speaker-side view is mirrored
left-to-right, the way the board looks after turning it over sideways.
"""
import math
import re
from html import escape
from pathlib import Path

HERE = Path(__file__).parent
BOARD = HERE / "redlight.kicad_pcb"
OUT = HERE / "out"

S = 10.0                    # px per mm
ORIGIN = (100.0, 100.0)     # tower screw on the KiCad sheet (see make_pcb.py)
BOARD_W, BOARD_H = 760, 1130
PANEL_W = 600
HEAD_H = 92

# MAX98357A breakout pin order at J3 (same as make_pcb.py).
AMP_PINS = ("LRC", "BCLK", "DIN", "GAIN", "SD", "GND", "VIN")

COL = {
    "board": "#e7efe2", "edge": "#3d4a3f", "ink": "#1c2321", "muted": "#5f6b66",
    "pad": "#c9972c", "pad_hole": "#ffffff",
    "res": "#e8c98f", "jumper": "#7d8791", "cap": "#9fc3e8", "ecap": "#6e9fd6",
    "ic": "#3a4046", "socket": "#9aa3ab", "module": "#bfe0cf", "amp": "#d9c9ee",
    "switch": "#f3b7a4", "wire": "#f2a23c", "plus": "#d2362b", "minus": "#2b4c7e",
    "ghost": "#9aa59f", "usb": "#aeb6bd",
}


# --- .kicad_pcb reader ---------------------------------------------------------
def parse_sexpr(text):
    stack, cur = [], []
    for tok in re.findall(r'\(|\)|"(?:\\.|[^"\\])*"|[^\s()]+', text):
        if tok == "(":
            stack.append(cur)
            cur = []
        elif tok == ")":
            done, cur = cur, stack.pop()
            cur.append(done)
        else:
            cur.append(tok[1:-1] if tok.startswith('"') else tok)
    return cur[0]


def find(node, key):
    return next((c for c in node if isinstance(c, list) and c and c[0] == key), None)


def findall(node, key):
    return [c for c in node if isinstance(c, list) and c and c[0] == key]


def rot(x, y, deg):
    """KiCad rotation (positive = counter-clockwise on screen, Y down)."""
    a = math.radians(deg)
    return x * math.cos(a) + y * math.sin(a), -x * math.sin(a) + y * math.cos(a)


class Footprint:
    def __init__(self, node):
        self.name = node[1]
        self.bottom = find(node, "layer")[1].startswith("B.")
        at = find(node, "at")
        self.x, self.y = float(at[1]) - ORIGIN[0], float(at[2]) - ORIGIN[1]
        self.rot = float(at[3]) if len(at) > 3 else 0.0
        self.ref = self.value = ""
        for t in findall(node, "fp_text"):
            if t[1] == "reference":
                self.ref = t[2]
            elif t[1] == "value":
                self.value = t[2]
        self.pads = []
        for p in findall(node, "pad"):
            pat = find(p, "at")
            size = find(p, "size")
            net = find(p, "net")
            self.pads.append({
                "num": p[1], "shape": p[3], "xy": self.to_board(float(pat[1]), float(pat[2])),
                "angle": float(pat[3]) if len(pat) > 3 else 0.0,
                "size": (float(size[1]), float(size[2])),
                "net": net[2] if net else "",
                "plated": p[2] == "thru_hole",
                "drill": float(find(p, "drill")[1]) if find(p, "drill") else 0.0,
            })

    def to_board(self, lx, ly):
        """Footprint-local mm -> board mm (origin at the screw, Y down)."""
        dx, dy = rot(lx, ly, self.rot)
        return self.x + dx, self.y + dy

    def pad(self, num):
        return next(p for p in self.pads if p["num"] == num)["xy"]


def load():
    root = parse_sexpr(BOARD.read_text())
    fps = {}
    for node in findall(root, "footprint"):
        fp = Footprint(node)
        fps[fp.ref] = fp
    edges = []
    arcs = []
    for g in findall(root, "gr_line"):
        if find(g, "layer")[1] == "Edge.Cuts":
            a, b = find(g, "start"), find(g, "end")
            edges.append(((float(a[1]) - ORIGIN[0], float(a[2]) - ORIGIN[1]),
                          (float(b[1]) - ORIGIN[0], float(b[2]) - ORIGIN[1])))
    for g in findall(root, "gr_arc"):
        if find(g, "layer")[1] == "Edge.Cuts":
            arcs.append([(float(find(g, k)[1]) - ORIGIN[0], float(find(g, k)[2]) - ORIGIN[1])
                         for k in ("start", "mid", "end")])
    return fps, edges, arcs


def closed_loops(edges):
    """Group Edge.Cuts segments into closed polygons (the six tab slots)."""
    key = lambda p: (round(p[0], 2), round(p[1], 2))
    left = list(edges)
    loops = []
    while left:
        a, b = left.pop()
        loop = [a, b]
        while key(loop[-1]) != key(loop[0]):
            for i, (c, d) in enumerate(left):
                if key(c) == key(loop[-1]):
                    loop.append(d)
                elif key(d) == key(loop[-1]):
                    loop.append(c)
                else:
                    continue
                left.pop(i)
                break
            else:
                break
        if key(loop[-1]) == key(loop[0]) and len(loop) > 3:
            loops.append(loop[:-1])
    return loops


# --- SVG helpers -----------------------------------------------------------------
class View:
    """One side of the board. `mirror` flips X for the speaker side."""

    def __init__(self, mirror):
        self.mirror = mirror
        self.cx, self.cy = BOARD_W / 2, HEAD_H + BOARD_H / 2
        self.out = []

    def pt(self, p):
        x = -p[0] if self.mirror else p[0]
        return self.cx + x * S, self.cy + p[1] * S

    def add(self, s):
        self.out.append(s)

    def poly(self, pts, fill, stroke=None, width=1.5, extra=""):
        d = " ".join(f"{x:.1f},{y:.1f}" for x, y in map(self.pt, pts))
        self.add(f'<polygon points="{d}" fill="{fill}" stroke="{stroke or COL["ink"]}" '
                 f'stroke-width="{width}" stroke-linejoin="round" {extra}/>')

    def line(self, a, b, stroke, width, extra=""):
        (x1, y1), (x2, y2) = self.pt(a), self.pt(b)
        self.add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" '
                 f'stroke-width="{width}" stroke-linecap="round" {extra}/>')

    def circle(self, c, r_mm, fill, stroke=None, width=1.5, extra=""):
        x, y = self.pt(c)
        self.add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r_mm * S:.1f}" fill="{fill}" '
                 f'stroke="{stroke or "none"}" stroke-width="{width}" {extra}/>')

    def text(self, c, msg, size=14, fill=None, weight=600, angle=0, anchor="middle", halo=True):
        x, y = self.pt(c)
        tr = f' transform="rotate({angle:.1f} {x:.1f} {y:.1f})"' if angle else ""
        h = (f' paint-order="stroke" stroke="{COL["board"]}" stroke-width="4" stroke-linejoin="round"'
             if halo else "")
        self.add(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-weight="{weight}" '
                 f'fill="{fill or COL["ink"]}" text-anchor="{anchor}" dominant-baseline="central"{h}{tr}>'
                 f'{escape(msg)}</text>')

    def screen_angle(self, a, b):
        """Angle for text running along a->b, kept upright (never upside down)."""
        (x1, y1), (x2, y2) = self.pt(a), self.pt(b)
        deg = math.degrees(math.atan2(y2 - y1, x2 - x1))
        if deg > 89.99:
            deg -= 180
        elif deg < -90.01:
            deg += 180
        return deg


def mid(a, b):
    return (a[0] + b[0]) / 2, (a[1] + b[1]) / 2


def along(a, b, t):
    """Point at distance t mm past b on the line a->b."""
    d = math.hypot(b[0] - a[0], b[1] - a[1])
    return b[0] + (b[0] - a[0]) / d * t, b[1] + (b[1] - a[1]) / d * t


def box(a, b, half_w, extend=0.0):
    """Rectangle around segment a-b: half_w to each side, `extend` past each end."""
    d = math.hypot(b[0] - a[0], b[1] - a[1])
    ux, uy = (b[0] - a[0]) / d, (b[1] - a[1]) / d
    nx, ny = -uy, ux
    a2 = (a[0] - ux * extend, a[1] - uy * extend)
    b2 = (b[0] + ux * extend, b[1] + uy * extend)
    return [(a2[0] + nx * half_w, a2[1] + ny * half_w), (b2[0] + nx * half_w, b2[1] + ny * half_w),
            (b2[0] - nx * half_w, b2[1] - ny * half_w), (a2[0] - nx * half_w, a2[1] - ny * half_w)]


def pretty_value(v):
    m = re.fullmatch(r"(\d+)k(\d*)", v)          # 2k2 -> 2.2k, 100k -> 100k
    return f"{m.group(1)}.{m.group(2)}k" if m and m.group(2) else v


# --- Drawing ---------------------------------------------------------------------
def draw_board(v, edges, arcs, fps):
    # Outline: two arcs joined by the two flats.
    pts = [p for arc in arcs for p in (arc[0], arc[2])]
    r = max(math.hypot(*arc[1]) for arc in arcs)
    xf, yf = max(abs(p[0]) for p in pts), max(abs(p[1]) for p in pts)
    (ax, ay), (bx, by) = v.pt((-xf, -yf)), v.pt((xf, -yf))
    (cx_, cy_), (dx, dy) = v.pt((xf, yf)), v.pt((-xf, yf))
    lo, hi = min(ax, bx), max(ax, bx)
    v.add(f'<path d="M{lo:.1f},{ay:.1f} A{r * S:.1f},{r * S:.1f} 0 0 1 {hi:.1f},{by:.1f} '
          f'L{hi:.1f},{cy_:.1f} A{r * S:.1f},{r * S:.1f} 0 0 1 {lo:.1f},{dy:.1f} Z" '
          f'fill="{COL["board"]}" stroke="{COL["edge"]}" stroke-width="2.5"/>')
    for loop in closed_loops(edges):
        v.poly(loop, "#ffffff", COL["edge"], 1.5)
    h1 = fps["H1"]
    v.circle((h1.x, h1.y), h1.pads[0]["drill"] / 2 if h1.pads else 2.1, "#ffffff", COL["edge"], 1.5)


def draw_pads(v, fp, ghost=False):
    for p in fp.pads:
        if not p["plated"]:
            continue
        x, y = v.pt(p["xy"])
        w, h = p["size"][0] * S, p["size"][1] * S
        fill = COL["pad"]
        if fp.ref.startswith("LED"):
            fill = COL["plus"] if p["num"] == "+" else COL["minus"]
        op = ' opacity="0.55"' if ghost else ""
        if p["shape"] == "rect":
            ang = p["angle"] if v.mirror else -p["angle"]
            v.add(f'<rect x="{x - w / 2:.1f}" y="{y - h / 2:.1f}" width="{w:.1f}" height="{h:.1f}" '
                  f'fill="{fill}" stroke="{COL["ink"]}" stroke-width="1" '
                  f'transform="rotate({ang:.1f} {x:.1f} {y:.1f})"{op}/>')
        else:
            v.add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{w / 2:.1f}" fill="{fill}" '
                  f'stroke="{COL["ink"]}" stroke-width="1"{op}/>')
        v.add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{max(p["drill"], 0.5) * S / 2:.1f}" '
              f'fill="{COL["pad_hole"]}"{op}/>')


def draw_resistor(v, fp):
    a, b = fp.pad("1"), fp.pad("2")
    ang = v.screen_angle(a, b)
    horizontal = abs(ang) < 45
    # Reference label just past one end: the upper end if it stands, the right end if it lies.
    pa, pb = v.pt(a), v.pt(b)
    if horizontal:
        far, near = (a, b) if pa[0] < pb[0] else (b, a)
    else:
        far, near = (a, b) if pa[1] > pb[1] else (b, a)
    if fp.value == "0R":                                   # wire jumper
        v.line(a, b, COL["ink"], 7)
        v.line(a, b, COL["jumper"], 4.5)
        draw_pads(v, fp)
        d = math.hypot(b[0] - a[0], b[1] - a[1])
        nx, ny = -(b[1] - a[1]) / d, (b[0] - a[0]) / d
        m = mid(a, b)
        v.text((m[0] + nx * 1.9, m[1] + ny * 1.9), fp.ref, 14, COL["ink"], 700)
        return
    v.line(a, b, COL["ink"], 2.5)
    c = mid(a, b)
    d = math.hypot(b[0] - a[0], b[1] - a[1])
    u = ((b[0] - a[0]) / d, (b[1] - a[1]) / d)
    e1 = (c[0] - u[0] * 3.15, c[1] - u[1] * 3.15)
    e2 = (c[0] + u[0] * 3.15, c[1] + u[1] * 3.15)
    v.poly(box(e1, e2, 1.25), COL["res"])
    draw_pads(v, fp)
    v.text(c, pretty_value(fp.value), 14, COL["ink"], 700, angle=ang, halo=False)
    lab = along(far, near, 2.3 if not horizontal else 2.9)
    v.text(lab, fp.ref, 13, COL["ink"], 700)


def draw_tower_part(v, fp):
    ref = fp.ref
    if ref.startswith("R"):
        draw_resistor(v, fp)
    elif ref == "C1":
        plus, minus = fp.pad("1"), fp.pad("2")
        c = mid(plus, minus)
        v.circle(c, 3.15, COL["ecap"], COL["ink"], 1.5)
        # Shade the negative-stripe side of the can.
        x, y = v.pt(c)
        ang = math.degrees(math.atan2(v.pt(minus)[1] - y, v.pt(minus)[0] - x))
        rr = 3.15 * S
        v.add(f'<path d="M{x:.1f},{y - rr:.1f} A{rr:.1f},{rr:.1f} 0 0 1 {x:.1f},{y + rr:.1f} '
              f'A{rr * 2.2:.1f},{rr * 2.2:.1f} 0 0 0 {x:.1f},{y - rr:.1f} Z" fill="{COL["ink"]}" '
              f'opacity="0.55" transform="rotate({ang:.1f} {x:.1f} {y:.1f})"/>')
        draw_pads(v, fp)
        v.text((c[0] + 3.9, plus[1] + 0.35), "+ long lead", 13, COL["plus"], 700, anchor="start")
        v.text((c[0] + 3.9, minus[1] - 0.35), "− stripe", 13, COL["ink"], 700, anchor="start")
        v.text((c[0] - 3.9, c[1]), "C1  220 µF", 13, COL["ink"], 700, anchor="end")
    elif ref == "C2":
        a, b = fp.pad("1"), fp.pad("2")
        v.poly(box(a, b, 1.25, -0.9), COL["cap"])
        draw_pads(v, fp)
        v.text((min(a[0], b[0]) - 1.6, a[1]), "C2  100 nF", 13, COL["ink"], 700, anchor="end")
    elif ref == "U2":
        p1, p9, p18 = fp.pad("1"), fp.pad("9"), fp.pad("18")
        row = (p9[0] - p1[0], p9[1] - p1[1])
        d = math.hypot(*row)
        u = (row[0] / d, row[1] / d)
        across = (p18[0] - p1[0], p18[1] - p1[1])
        # Chip body sits between the two pin rows, inside the socket frame.
        a = (p1[0] + across[0] / 2, p1[1] + across[1] / 2)
        b = (a[0] + row[0], a[1] + row[1])
        v.poly(box(a, b, 5.08, 1.27), COL["socket"])
        v.poly(box(a, b, 3.2, 0.9), COL["ic"])
        # Notch at the pin-1 end.
        n = (a[0] - u[0] * 0.9, a[1] - u[1] * 0.9)
        v.circle(n, 1.0, COL["socket"], COL["ink"], 1)
        draw_pads(v, fp)
        ang = v.screen_angle(a, b)
        v.text(mid(a, b), "U2  TBD62083APG", 13, "#ffffff", 700, angle=ang, halo=False)
        v.text((n[0], n[1] - 3.1), "notch this end", 13, COL["ink"], 700)
        v.text((p1[0] - 2.2, p1[1]), "1", 13, COL["ink"], 700)
    elif ref == "U1":
        d0, d6, v5 = fp.pad("D0"), fp.pad("D6"), fp.pad("5V")
        col = (d6[0] - d0[0], d6[1] - d0[1])
        d = math.hypot(*col)
        u = (col[0] / d, col[1] / d)
        top = mid(d0, v5)
        a = (top[0] - u[0] * 3.63, top[1] - u[1] * 3.63)          # USB end of the module
        b = (top[0] + u[0] * (d + 2.13), top[1] + u[1] * (d + 2.13))
        v.poly(box(a, b, 8.75), COL["module"])
        usb_a = (a[0] - u[0] * 1.3, a[1] - u[1] * 1.3)
        usb_b = (a[0] + u[0] * 5.3, a[1] + u[1] * 5.3)
        v.poly(box(usb_a, usb_b, 4.2), COL["usb"])
        v.text(mid(usb_a, usb_b), "USB-C", 13, COL["ink"], 700, halo=False)
        draw_pads(v, fp)
        for p in fp.pads:
            inward = 1 if p["xy"][0] < top[0] else -1
            v.text((p["xy"][0] + inward * 1.25, p["xy"][1]), p["num"], 10.5, COL["ink"], 600,
                   anchor="start" if (inward > 0) != v.mirror else "end", halo=False)
        c = mid(a, b)
        v.text((c[0], c[1] + 3.0), "U1", 15, COL["ink"], 700, halo=False)
        v.text((c[0], c[1] + 5.0), "XIAO", 13, COL["ink"], 700, halo=False)
        v.text((c[0], c[1] + 6.8), "ESP32-C6", 12, COL["ink"], 600, halo=False)
        v.text((a[0], a[1] - 2.6), "USB end toward this edge", 13, COL["ink"], 700)
    elif ref == "J3":
        p1, p7 = fp.pad("1"), fp.pad("7")
        d = math.hypot(p7[0] - p1[0], p7[1] - p1[1])
        u = ((p7[0] - p1[0]) / d, (p7[1] - p1[1]) / d)
        n = (u[1], -u[0])                                         # toward the module body
        c0 = (p1[0] - u[0] * 1.27 - n[0] * 1.3, p1[1] - u[1] * 1.27 - n[1] * 1.3)
        body = [c0, (c0[0] + u[0] * 17.8, c0[1] + u[1] * 17.8),
                (c0[0] + u[0] * 17.8 + n[0] * 19.4, c0[1] + u[1] * 17.8 + n[1] * 19.4),
                (c0[0] + n[0] * 19.4, c0[1] + n[1] * 19.4)]
        v.poly(body, COL["amp"])
        draw_pads(v, fp)
        for k, name in enumerate(AMP_PINS):
            p = fp.pad(str(k + 1))
            v.text((p[0] + n[0] * 1.4, p[1] + n[1] * 1.4), name, 11, COL["ink"], 700, angle=-90,
                   anchor="start", halo=False)
        c = (c0[0] + u[0] * 8.9 + n[0] * 11.5, c0[1] + u[1] * 8.9 + n[1] * 11.5)
        v.text((c[0], c[1] - 1.9), "J3  MAX98357A", 14, COL["ink"], 700, halo=False)
        v.text((c[0], c[1]), "amp module", 13, COL["ink"], 600, halo=False)
        v.text((c[0], c[1] + 1.9), "parts facing up", 12, COL["ink"], 600, halo=False)
    elif ref.startswith("LED"):
        draw_pads(v, fp)
        k = math.hypot(fp.x, fp.y)
        v.text((fp.x / k * 4.4, fp.y / k * 4.4), "D" + ref[3:], 12, COL["ink"], 700)


def draw_speaker_part(v, fp):
    ref = fp.ref
    if ref.startswith("SW"):
        v.poly([fp.to_board(*p) for p in ((-1.5, -4.2), (6, -4.2), (6, 2.59), (-1.5, 2.59))], COL["switch"])
        v.poly([fp.to_board(*p) for p in ((0.5, 2.59), (4, 2.59), (4, 3.15), (0.5, 3.15))], COL["ink"])
        draw_pads(v, fp)
        v.text(fp.to_board(2.25, -6.1), f"{ref}  {fp.value}", 14, COL["ink"], 700)
    elif ref in ("J1", "J2"):
        names = {"+5V": "5V", "/VBAT": "VBAT", "/BUTTONS": "BTN"}
        for p in fp.pads:
            v.circle(p["xy"], 1.25, COL["wire"], COL["ink"], 1.5)
            v.circle(p["xy"], 0.45, "#ffffff")
        a, b = fp.pads[0]["xy"], fp.pads[-1]["xy"]
        vertical = abs(a[0] - b[0]) < abs(a[1] - b[1])
        for p in fp.pads:
            label = names.get(p["net"], p["net"])
            if vertical:
                side = 1 if p["xy"][0] > 0 else -1                # label toward the board center
                v.text((p["xy"][0] - side * 2.0, p["xy"][1]), label, 13, COL["ink"], 700,
                       anchor="start" if (side < 0) != v.mirror else "end")
            else:
                v.text((p["xy"][0], p["xy"][1] - 2.6), label, 13, COL["ink"], 700)
        title = "J1  power wires" if ref == "J1" else "J2  ext. button (optional)"
        if vertical:
            top = min(fp.pads, key=lambda p: p["xy"][1])["xy"]
            side = 1 if top[0] > 0 else -1
            v.text((top[0] + side * 0.9, top[1] - 3.0), title, 13, COL["ink"], 700,
                   anchor="end" if (side > 0) != v.mirror else "start")
        else:
            v.text((mid(a, b)[0], mid(a, b)[1] + 2.9), title, 13, COL["ink"], 700)
    elif ref.startswith("LED"):
        draw_pads(v, fp)
        k = math.hypot(fp.x, fp.y)
        v.text((fp.x / k * 4.4, fp.y / k * 4.4), "D" + ref[3:], 12, COL["ink"], 700)


def draw_ghost(v, fp):
    """Solder joints of a part that sits on the other side."""
    draw_pads(v, fp, ghost=True)
    if fp.ref.startswith(("R", "LED", "H")):
        return
    xs = [p["xy"][0] for p in fp.pads]
    ys = [p["xy"][1] for p in fp.pads]
    v.poly([(min(xs) - 1.6, min(ys) - 1.6), (max(xs) + 1.6, min(ys) - 1.6),
            (max(xs) + 1.6, max(ys) + 1.6), (min(xs) - 1.6, max(ys) + 1.6)],
           "none", COL["ghost"], 1.5, 'stroke-dasharray="6 5"')
    label = {"U1": "U1 pins", "U2": "U2 pins", "J3": "amp pins"}.get(fp.ref, fp.ref)
    if not v.mirror:
        label = f"{fp.ref} {fp.value} (other side)" if fp.ref.startswith("SW") else f"{fp.ref} (other side)"
    w, h = max(xs) - min(xs), max(ys) - min(ys)
    c = ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)
    if max(w, h) < 4:                                   # tiny group: label beside it, toward the middle
        side = -1 if c[0] > 0 else 1
        v.text((c[0] + side * (w / 2 + 2.4), c[1]), label, 13, COL["muted"], 600,
               anchor="start" if (side > 0) != v.mirror else "end")
    elif h < 4 and (len(fp.pads) > 2 or not v.mirror):   # single row: label above it
        v.text((c[0], min(ys) - 2.8), label, 13, COL["muted"], 600)
    elif w < 4:                                         # single column: label beside it
        side = -1 if c[0] > 0 else 1
        v.text((c[0] + side * 2.4, c[1]), label, 13, COL["muted"], 600,
               anchor="start" if (side > 0) != v.mirror else "end")
    else:
        v.text(c, label, 13, COL["muted"], 600)


# --- Side panel ------------------------------------------------------------------
def panel(x0, rows, title):
    out = [f'<text x="{x0}" y="{HEAD_H + 26}" font-size="19" font-weight="700" fill="{COL["ink"]}">'
           f'{escape(title)}</text>']
    y = HEAD_H + 62
    for n, (swatch, head, lines) in enumerate(rows, 1):
        out.append(f'<rect x="{x0}" y="{y - 14}" width="26" height="18" rx="3" fill="{swatch}" '
                   f'stroke="{COL["ink"]}" stroke-width="1.2"/>')
        out.append(f'<text x="{x0 + 38}" y="{y}" font-size="16" font-weight="700" fill="{COL["ink"]}">'
                   f'{n}. {escape(head)}</text>')
        y += 22
        for ln in lines:
            out.append(f'<text x="{x0 + 38}" y="{y}" font-size="14" fill="{COL["muted"]}">{escape(ln)}</text>')
            y += 19
        y += 16
    return out


TOWER_ROWS = [
    (COL["jumper"], "R1–R6: wire jumpers", [
        "A clipped component lead across each pair of pads.",
        "The strips carry their own 20 Ω resistor."]),
    (COL["res"], "R7, R8: 100 kΩ (battery gauge)", [
        "4 bands: brown, black, yellow, gold",
        "5 bands: brown, black, black, orange, brown"]),
    (COL["res"], "R10: 10 kΩ   R11: 2.2 kΩ   R12: 6.8 kΩ", [
        "Button ladder. Resistors fit either way round.",
        "10 kΩ: brown, black, orange  (5 band: brown, black, black, red)",
        "2.2 kΩ: red, red, red  (5 band: red, red, black, brown)",
        "6.8 kΩ: blue, grey, red  (5 band: blue, grey, black, brown)"]),
    (COL["cap"], "C2: 100 nF ceramic", ["Fits either way round."]),
    (COL["socket"], "U2: DIP-18 socket, then TBD62083APG", [
        "Notch on the socket and on the chip toward the XIAO end.",
        "Pin 1 is the square pad."]),
    (COL["ecap"], "C1: 220 µF electrolytic", [
        "Polarised. Long lead (+) in the square pad, the one",
        "nearer the buttons. The stripe on the can marks (−)."]),
    (COL["module"], "U1: XIAO ESP32-C6 on header pins", [
        "Chip side up, USB connector toward the board edge.",
        "D0 is the square pad; 5V is opposite it."]),
    (COL["amp"], "J3: MAX98357A amp module", [
        "Solder it on its 1×7 header, parts facing up, with no",
        "screw terminal. Match its pin labels to the board's",
        "before soldering. Speaker wires go on its + / − pads."]),
    (COL["plus"], "D1–D6: LED strip tabs", [
        "Red pad = strip +, blue pad = strip −.",
        "+ is the counter-clockwise half of each tab."]),
    (COL["pad"], "Dashed boxes: parts on the speaker side", [
        "SW1–SW3 and the J1 / J2 wire pads mount from the other",
        "face. See the speaker-side drawing."]),
]

SPEAKER_ROWS = [
    (COL["switch"], "SW1 TEST, SW2 VOL+, SW3 VOL−", [
        "PTS645 right-angle tact switches, plunger pointing",
        "off the bottom edge toward the housing's buttons."]),
    (COL["wire"], "J1: power wires", [
        "5V and GND from the charge module's 5 V output",
        "(through the slide switch). VBAT from the battery +,",
        "for the battery gauge only."]),
    (COL["wire"], "J2: external TEST button (optional)", [
        "BTN and GND. Leave empty if you don't use one."]),
    (COL["pad"], "Everything else on this side is solder joints", [
        "Dashed boxes show where the tower-side parts' pins",
        "come through. Trim them short: the speaker sits",
        "11 mm below this face."]),
]


def render(fps, edges, arcs, speaker_side):
    v = View(mirror=speaker_side)
    draw_board(v, edges, arcs, fps)
    order = sorted(fps.values(), key=lambda f: (not f.ref.startswith("LED"), f.ref))
    for fp in order:
        if fp.ref == "H1":
            continue
        if fp.ref.startswith("LED"):
            (draw_speaker_part if speaker_side else draw_tower_part)(v, fp)
        elif fp.bottom == speaker_side:
            (draw_speaker_part if speaker_side else draw_tower_part)(v, fp)
        else:
            draw_ghost(v, fp)
    side = "Speaker side" if speaker_side else "Tower side"
    sub = ("Mirrored view: the board turned over sideways, XIAO end still at the top"
           if speaker_side else "Top view: looking down at the side the light tower stands on")
    w, h = BOARD_W + PANEL_W, HEAD_H + BOARD_H + 20
    head = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
        f'font-family="Inter, \'DejaVu Sans\', Arial, sans-serif">',
        f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
        f'<text x="24" y="40" font-size="26" font-weight="700" fill="{COL["ink"]}">'
        f'Redlight PCB v2: {side.lower()} assembly</text>',
        f'<text x="24" y="66" font-size="15" fill="{COL["muted"]}">{escape(sub)}</text>',
    ]
    rows = SPEAKER_ROWS if speaker_side else TOWER_ROWS
    title = "Parts on this side" if speaker_side else "Parts, in soldering order (lowest first)"
    return "\n".join(head + v.out + panel(BOARD_W + 16, rows, title) + ["</svg>"])


def main():
    fps, edges, arcs = load()
    OUT.mkdir(exist_ok=True)
    for speaker_side, name in ((False, "assembly_tower_side"), (True, "assembly_speaker_side")):
        path = OUT / f"{name}.svg"
        path.write_text(render(fps, edges, arcs, speaker_side))
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
