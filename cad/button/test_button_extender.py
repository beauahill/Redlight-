"""TEST-button extender: a clip that moves the button's contact point.

    python3 cad/button/test_button_extender.py
        -> cad/button/out/test_button_extender.stl  (and a dimensioned .svg)

The housing's TEST button has a small bump on the back of its flange that
presses the switch. On the v2 board the switch plunger sits 3.5 mm further out
along the flange than that bump, and 1.5 mm further away. This part sits on
the back of the flange, located by a tab in the button's centre hole and a
slot over the old bump, and gives the plunger a flat pad in the right place.

It is one flat profile extruded sideways, so it prints lying on its side with
no supports. Pure Python: no CAD library needed.

All dimensions in mm. x runs along the flange from the centre hole toward the
bump; z is the push direction, 0 at the flange's back face, positive toward
the switch.
"""
from pathlib import Path
import struct

HERE = Path(__file__).parent

# --- Measured on the button ------------------------------------------------------
BUMP_DIA = 4.2            # existing bump on the back of the flange
BUMP_H = 1.8
HOLE_DIA = 5.9            # hole in the centre of the button's back
BUMP_X = 6.9              # centre hole to bump, centre to centre
FLANGE_W = 5.5
FLANGE_LEN = 17.9

# --- What the new contact point needs ----------------------------------------------
OFFSET_OUT = 3.5          # plunger lands this far past the old bump, along the flange
EXTRA_REACH = 1.5         # and needs the surface this much closer than the old bump's top

# --- Part ---------------------------------------------------------------------------
WIDTH = 5.0               # across the flange (the extrusion); a little under FLANGE_W
CLEAR = 0.2               # around the old bump
BASE_T = 2.0              # thickness where it rests on the flange
TAB_W = 2.2               # tab in the centre hole: TAB_W x WIDTH must fit inside HOLE_DIA
TAB_LEN = 5.0
PAD_PAST = 3.0            # pad extends this far past the plunger's landing point
BASE_BACK = 4.0           # how far the base runs back past the hole centre

PAD_Z = BUMP_H + EXTRA_REACH                 # new contact surface
SLOT_X0 = BUMP_X - BUMP_DIA / 2 - CLEAR
SLOT_X1 = max(BUMP_X + BUMP_DIA / 2, FLANGE_LEN / 2) + CLEAR
SLOT_Z = BUMP_H + 0.05                       # the bridge rests on top of the old bump
TARGET_X = BUMP_X + OFFSET_OUT
END_X = TARGET_X + PAD_PAST
assert (TAB_W ** 2 + WIDTH ** 2) ** 0.5 < HOLE_DIA - 0.3, "tab will not fit the centre hole"
assert PAD_Z - SLOT_Z >= 1.2, "bridge over the old bump is too thin"

# Profile in (x, z), counter-clockwise.
PROFILE = [
    (-BASE_BACK, 0.0),
    (-TAB_W / 2, 0.0), (-TAB_W / 2, -TAB_LEN + 0.5), (-TAB_W / 2 + 0.5, -TAB_LEN),
    (TAB_W / 2 - 0.5, -TAB_LEN), (TAB_W / 2, -TAB_LEN + 0.5), (TAB_W / 2, 0.0),
    (SLOT_X0, 0.0), (SLOT_X0, SLOT_Z), (SLOT_X1, SLOT_Z), (SLOT_X1, 0.0),
    (END_X, 0.0), (END_X, PAD_Z),
    (SLOT_X0 - 1.0, PAD_Z), (SLOT_X0 - 1.0, BASE_T), (-BASE_BACK, BASE_T),
]


def triangulate(poly):
    """Ear clipping for a simple counter-clockwise polygon."""
    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    def inside(p, a, b, c):
        return cross(a, b, p) >= -1e-9 and cross(b, c, p) >= -1e-9 and cross(c, a, p) >= -1e-9

    idx = list(range(len(poly)))
    tris = []
    while len(idx) > 3:
        for k in range(len(idx)):
            i, j, l = idx[k - 1], idx[k], idx[(k + 1) % len(idx)]
            a, b, c = poly[i], poly[j], poly[l]
            if cross(a, b, c) <= 1e-9:
                continue                                   # reflex or flat corner
            if any(inside(poly[m], a, b, c) for m in idx if m not in (i, j, l)):
                continue
            tris.append((i, j, l))
            idx.pop(k)
            break
        else:
            raise ValueError("polygon could not be triangulated")
    tris.append(tuple(idx))
    return tris


def build():
    """Triangles of the extruded profile. Output axes: X = x, Y = z, Z = across
    the flange, so the part lies on its side on the print bed."""
    n = len(PROFILE)
    lo = [(x, z, 0.0) for x, z in PROFILE]
    hi = [(x, z, WIDTH) for x, z in PROFILE]
    out = []
    for i, j, l in triangulate(PROFILE):
        out.append((lo[i], lo[l], lo[j]))                  # bottom face looks down
        out.append((hi[i], hi[j], hi[l]))                  # top face looks up
    for i in range(n):
        j = (i + 1) % n
        out.append((lo[i], lo[j], hi[j]))
        out.append((lo[i], hi[j], hi[i]))
    return out


def check(tris):
    """Every edge must be shared by exactly two triangles, in opposite directions."""
    edges = {}
    for t in tris:
        for a, b in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
            edges[(a, b)] = edges.get((a, b), 0) + 1
    bad = [e for e in edges if edges[e] != 1 or edges.get((e[1], e[0]), 0) != 1]
    vol = sum((a[0] * (b[1] * c[2] - b[2] * c[1]) - a[1] * (b[0] * c[2] - b[2] * c[0])
               + a[2] * (b[0] * c[1] - b[1] * c[0])) / 6 for a, b, c in tris)
    return len(bad), vol


def write_stl(tris, path):
    with open(path, "wb") as f:
        f.write(b"Redlight TEST button extender".ljust(80, b" "))
        f.write(struct.pack("<I", len(tris)))
        for a, b, c in tris:
            u = [b[k] - a[k] for k in range(3)]
            v = [c[k] - a[k] for k in range(3)]
            nrm = [u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]]
            m = sum(x * x for x in nrm) ** 0.5 or 1.0
            f.write(struct.pack("<12fH", *[x / m for x in nrm], *a, *b, *c, 0))


def write_svg(path):
    s = 26.0                                               # px per mm
    ox, oy = 330.0, 270.0

    def P(x, z):
        return ox + x * s, oy - z * s

    def poly(pts, fill, stroke="#1c2321", extra=""):
        d = " ".join("%.1f,%.1f" % P(*p) for p in pts)
        return f'<polygon points="{d}" fill="{fill}" stroke="{stroke}" stroke-width="1.6" {extra}/>'

    def text(x, z, msg, size=15, fill="#1c2321", weight=400, anchor="middle", dy=0):
        px, py = P(x, z)
        return (f'<text x="{px:.1f}" y="{py + dy:.1f}" font-size="{size}" font-weight="{weight}" '
                f'fill="{fill}" text-anchor="{anchor}">{msg}</text>')

    def arrow(x0, z0, x1, z1, color="#c2185b"):
        (a, b), (c, d) = P(x0, z0), P(x1, z1)
        return (f'<line x1="{a:.1f}" y1="{b:.1f}" x2="{c:.1f}" y2="{d:.1f}" stroke="{color}" '
                f'stroke-width="2" marker-start="url(#h)" marker-end="url(#h)"/>')

    half = FLANGE_LEN / 2
    o = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 600" width="900" height="600" '
         'font-family="Inter, \'DejaVu Sans\', Arial, sans-serif">',
         '<defs><marker id="h" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" '
         'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#c2185b"/></marker></defs>',
         '<rect width="900" height="600" fill="#ffffff"/>',
         '<text x="24" y="40" font-size="26" font-weight="700" fill="#1c2321">TEST button extender</text>',
         '<text x="24" y="66" font-size="15" fill="#5f6b66">Side view, cut through the middle of the button. '
         'The switch is above; the button is pressed from below.</text>']
    # Button: flange, old bump, hollow shaft (schematic below the flange).
    o.append(poly([(-half, 0), (half, 0), (half, -1.6), (-half, -1.6)], "#f2b8b0"))
    o.append(poly([(-4.5, -1.6), (4.5, -1.6), (4.5, -6.5), (-4.5, -6.5)], "#f2b8b0"))
    o.append(poly([(-HOLE_DIA / 2, 0), (HOLE_DIA / 2, 0), (HOLE_DIA / 2, -6.5), (-HOLE_DIA / 2, -6.5)],
                  "#ffffff", "#1c2321", 'stroke-dasharray="5 4"'))
    o.append(poly([(BUMP_X - BUMP_DIA / 2, 0), (BUMP_X + BUMP_DIA / 2, 0),
                   (BUMP_X + BUMP_DIA / 2, BUMP_H), (BUMP_X - BUMP_DIA / 2, BUMP_H)], "#e58a7d"))
    o.append(poly(PROFILE, "#f2a23c", "#1c2321", 'fill-opacity="0.92"'))
    # Plunger landing point and dimensions.
    px, py = P(TARGET_X, PAD_Z)
    o.append(f'<path d="M{px - 26:.1f},{py - 70:.1f} h52 v44 h-17 v24 h-18 v-24 h-17 z" fill="#3a4046" '
             f'stroke="#1c2321" stroke-width="1.4"/>')
    o.append(text(TARGET_X, PAD_Z, "switch plunger", 14, "#1c2321", 700, dy=-80))
    o.append(arrow(BUMP_X, PAD_Z + 0.9, TARGET_X, PAD_Z + 0.9))
    o.append(text((BUMP_X + TARGET_X) / 2, PAD_Z + 0.9, f"{OFFSET_OUT:g}", 14, "#c2185b", 700, dy=-8))
    o.append(arrow(END_X + 0.9, BUMP_H, END_X + 0.9, PAD_Z))
    o.append(text(END_X + 1.2, (BUMP_H + PAD_Z) / 2, f"{EXTRA_REACH:g}", 14, "#c2185b", 700, "start", 5))
    o.append(text(BUMP_X, BUMP_H / 2, "old bump", 12, "#1c2321", 700, dy=4))
    o.append(text(0, -3.6, "tab in the", 12, "#1c2321", 700))
    o.append(text(0, -4.3, "centre hole", 12, "#1c2321", 700))
    o.append(text(-6.2, -0.8, "flange", 12, "#1c2321", 700, dy=4))
    notes = [f"The part is {END_X + BASE_BACK:g} mm long and {WIDTH:g} mm wide (into the page).",
             f"New contact surface is {PAD_Z:g} mm above the flange: the old bump's {BUMP_H:g} mm plus {EXTRA_REACH:g} mm.",
             f"The plunger lands {OFFSET_OUT:g} mm past the old bump, {TARGET_X - FLANGE_LEN / 2:.1f} mm beyond the end of the flange.",
             "It prints lying on this side, with no supports.",
             "Fix it with a drop of glue once the fit is confirmed."]
    for i, n in enumerate(notes):
        o.append(f'<text x="24" y="{486 + i * 24}" font-size="15" fill="#1c2321">{n}</text>')
    o.append("</svg>")
    path.write_text("\n".join(o))


if __name__ == "__main__":
    out = HERE / "out"
    out.mkdir(exist_ok=True)
    tris = build()
    bad, vol = check(tris)
    write_stl(tris, out / "test_button_extender.stl")
    write_svg(out / "test_button_extender.svg")
    xs = [p[0] for p in PROFILE]
    zs = [p[1] for p in PROFILE]
    print(f"{len(tris)} triangles, {bad} bad edges, volume {vol:.0f} mm3, "
          f"{max(xs) - min(xs):.1f} x {max(zs) - min(zs):.1f} x {WIDTH:.1f} mm; "
          f"pad at z = {PAD_Z:g}, plunger target x = {TARGET_X:g}")
