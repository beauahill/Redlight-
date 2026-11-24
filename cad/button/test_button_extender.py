"""TEST-button extender: a cap that moves the button's contact point.

    pip install manifold3d
    python3 cad/button/test_button_extender.py
        -> cad/button/out/test_button_extender.stl  (and a dimensioned .svg)

The housing's TEST button has a small bump on the back of its flange that
presses the switch. On the v2 board the switch plunger sits 3.5 mm further out
along the flange than that bump, and 1.5 mm further away. This part is glued
onto the back of the flange, located by a peg in the button's centre hole and
a slot over the old bump, and gives the plunger a flat pad in the right place.

It prints pad-face down with the peg pointing up: no overhangs, no supports.

All dimensions in mm. x runs along the flange from the centre hole toward the
bump; z is the push direction, 0 at the flange's back face, positive toward
the switch.
"""
from pathlib import Path
import struct

import manifold3d as m3

HERE = Path(__file__).parent

# --- Measured on the button ------------------------------------------------------
BUMP_DIA = 4.2            # existing bump on the back of the flange
BUMP_H = 1.8
HOLE_DIA = 3.15           # hole in the centre of the button's back (17.2 deep)
BUMP_X = 6.9              # centre hole to bump, centre to centre
FLANGE_W = 5.5
FLANGE_LEN = 17.9

# --- What the new contact point needs ----------------------------------------------
OFFSET_OUT = 3.5          # plunger lands this far past the old bump, along the flange
EXTRA_REACH = 1.5         # and needs the surface this much closer than the old bump's top

# --- Part ---------------------------------------------------------------------------
WIDTH = FLANGE_W          # flush with the flange's sides
CLEAR = 0.2               # around the old bump
PEG_DIA = HOLE_DIA - 0.3  # printed pegs come out slightly fat
PEG_LEN = 4.0
PAD_PAST = 3.0            # pad extends this far past the plunger's landing point
BASE_BACK = 3.5           # how far the body runs back past the hole centre

PAD_Z = BUMP_H + EXTRA_REACH                 # new contact surface
SLOT_X0 = BUMP_X - BUMP_DIA / 2 - CLEAR
SLOT_X1 = max(BUMP_X + BUMP_DIA / 2, FLANGE_LEN / 2) + CLEAR
SLOT_Z = BUMP_H + 0.05                       # the bridge rests on top of the old bump
TARGET_X = BUMP_X + OFFSET_OUT
END_X = TARGET_X + PAD_PAST
assert PAD_Z - SLOT_Z >= 1.2, "bridge over the old bump is too thin"


def build():
    """The part in button coordinates (z = 0 at the flange's back face)."""
    r = WIDTH / 2
    ends = [m3.CrossSection.circle(r, 48).translate((x, 0.0)) for x in (-BASE_BACK + r, END_X - r)]
    body = m3.CrossSection.batch_hull(ends).extrude(PAD_Z)
    slot = m3.Manifold.cube([SLOT_X1 - SLOT_X0, WIDTH + 2.0, SLOT_Z + 1.0]).translate(
        (SLOT_X0, -WIDTH / 2 - 1.0, -1.0))
    tip = 0.4
    peg = (m3.Manifold.cylinder(PEG_LEN - tip + 0.01, PEG_DIA / 2, PEG_DIA / 2, 48).translate((0, 0, -PEG_LEN + tip))
           + m3.Manifold.cylinder(tip, PEG_DIA / 2 - tip, PEG_DIA / 2, 48).translate((0, 0, -PEG_LEN)))
    return body - slot + peg


def for_printing(part):
    """Flip it pad-face down: the pad sits on the bed and the peg points up."""
    return part.mirror((0.0, 0.0, 1.0)).translate((0.0, 0.0, PAD_Z))


def write_stl(part, path):
    mesh = part.to_mesh()
    verts, tris = mesh.vert_properties, mesh.tri_verts
    with open(path, "wb") as f:
        f.write(b"Redlight TEST button extender".ljust(80, b" "))
        f.write(struct.pack("<I", len(tris)))
        for t in tris:
            a, b, c = (verts[i][:3] for i in t)
            u, v = b - a, c - a
            n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
            k = sum(x * x for x in n) ** 0.5 or 1.0
            f.write(struct.pack("<12fH", *[x / k for x in n], *a, *b, *c, 0))
    return len(tris)


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

    half, pr = FLANGE_LEN / 2, PEG_DIA / 2
    profile = [(-BASE_BACK, 0), (-pr, 0), (-pr, -PEG_LEN + 0.4), (-pr + 0.4, -PEG_LEN), (pr - 0.4, -PEG_LEN),
               (pr, -PEG_LEN + 0.4), (pr, 0), (SLOT_X0, 0), (SLOT_X0, SLOT_Z), (SLOT_X1, SLOT_Z), (SLOT_X1, 0),
               (END_X, 0), (END_X, PAD_Z), (-BASE_BACK, PAD_Z)]
    o = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 600" width="900" height="600" '
         'font-family="Inter, \'DejaVu Sans\', Arial, sans-serif">',
         '<defs><marker id="h" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" '
         'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#c2185b"/></marker></defs>',
         '<rect width="900" height="600" fill="#ffffff"/>',
         '<text x="24" y="40" font-size="26" font-weight="700" fill="#1c2321">TEST button extender</text>',
         '<text x="24" y="66" font-size="15" fill="#5f6b66">Side view, cut through the middle of the button. '
         'The switch is above; the button is pressed from below.</text>']
    # Button: flange, old bump, shaft with its centre hole (schematic below the flange).
    o.append(poly([(-half, 0), (half, 0), (half, -1.6), (-half, -1.6)], "#f2b8b0"))
    o.append(poly([(-4.5, -1.6), (4.5, -1.6), (4.5, -6.5), (-4.5, -6.5)], "#f2b8b0"))
    o.append(poly([(-HOLE_DIA / 2, 0), (HOLE_DIA / 2, 0), (HOLE_DIA / 2, -6.5), (-HOLE_DIA / 2, -6.5)],
                  "#ffffff", "#1c2321", 'stroke-dasharray="5 4"'))
    o.append(poly([(BUMP_X - BUMP_DIA / 2, 0), (BUMP_X + BUMP_DIA / 2, 0),
                   (BUMP_X + BUMP_DIA / 2, BUMP_H), (BUMP_X - BUMP_DIA / 2, BUMP_H)], "#e58a7d"))
    o.append(poly(profile, "#f2a23c", "#1c2321", 'fill-opacity="0.92"'))
    px, py = P(TARGET_X, PAD_Z)
    o.append(f'<path d="M{px - 26:.1f},{py - 70:.1f} h52 v44 h-17 v24 h-18 v-24 h-17 z" fill="#3a4046" '
             f'stroke="#1c2321" stroke-width="1.4"/>')
    o.append(text(TARGET_X, PAD_Z, "switch plunger", 14, "#1c2321", 700, dy=-80))
    o.append(arrow(BUMP_X, PAD_Z + 0.9, TARGET_X, PAD_Z + 0.9))
    o.append(text((BUMP_X + TARGET_X) / 2, PAD_Z + 0.9, f"{OFFSET_OUT:g}", 14, "#c2185b", 700, dy=-8))
    o.append(arrow(END_X + 0.9, BUMP_H, END_X + 0.9, PAD_Z))
    o.append(text(END_X + 1.2, (BUMP_H + PAD_Z) / 2, f"{EXTRA_REACH:g}", 14, "#c2185b", 700, "start", 5))
    o.append(text(BUMP_X, BUMP_H / 2, "old bump", 12, "#1c2321", 700, dy=4))
    o.append(text(-4.9, -3.4, "peg in the", 12, "#1c2321", 700, "end"))
    o.append(text(-4.9, -4.1, "centre hole", 12, "#1c2321", 700, "end"))
    o.append(text(-6.9, -0.8, "flange", 12, "#1c2321", 700, dy=4))
    notes = [f"The part is {END_X + BASE_BACK:g} mm long, {WIDTH:g} mm wide (into the page) and {PAD_Z:g} mm thick, "
             f"plus a {PEG_DIA:g} mm peg.",
             f"New contact surface is {PAD_Z:g} mm above the flange: the old bump's {BUMP_H:g} mm plus {EXTRA_REACH:g} mm.",
             f"The plunger lands {OFFSET_OUT:g} mm past the old bump, {TARGET_X - FLANGE_LEN / 2:.1f} mm beyond the end of the flange.",
             "It prints upside down from this view: pad face on the bed, peg pointing up, no supports.",
             "Glue it to the back of the flange once the fit is confirmed."]
    for i, n in enumerate(notes):
        o.append(f'<text x="24" y="{486 + i * 24}" font-size="15" fill="#1c2321">{n}</text>')
    o.append("</svg>")
    path.write_text("\n".join(o))


if __name__ == "__main__":
    out = HERE / "out"
    out.mkdir(exist_ok=True)
    part = for_printing(build())
    n = write_stl(part, out / "test_button_extender.stl")
    write_svg(out / "test_button_extender.svg")
    lo_x, lo_y, lo_z, hi_x, hi_y, hi_z = part.bounding_box()
    print(f"{n} triangles, status {part.status()}, volume {part.volume():.0f} mm3, "
          f"{hi_x - lo_x:.1f} x {hi_y - lo_y:.1f} x {hi_z - lo_z:.1f} mm as printed; "
          f"pad {PAD_Z:g} thick, peg {PEG_DIA:g} dia, plunger target x = {TARGET_X:g}")
