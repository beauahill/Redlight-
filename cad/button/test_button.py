"""Replacement TEST button, with the contact bump where the v2 board's switch is.

    pip install manifold3d
    python3 cad/button/test_button.py
        -> cad/button/out/test_button.stl  (and a dimensioned .svg)

A copy of the housing's original TEST button from its measurements, except
that the bump on the back of the flange is longer and reaches further out, so
it lands on the switch plunger (see test_button_extender.py for the same fix
as a cap glued onto the original button).

It prints bump-face down with the shaft pointing up. The flange then overhangs
the bed by the height of the bump, so it needs supports under the flange
("build plate only" is enough); they are on the hidden back face.

All dimensions in mm. x runs along the flange from the centre toward the bump;
z is the push direction: 0 at the flange's back face, positive toward the
switch, negative along the shaft toward the tip you press.
"""
from pathlib import Path
import struct

import manifold3d as m3

HERE = Path(__file__).parent

# --- Measured on the original button ----------------------------------------------
SHAFT_DIA = 5.8
SHAFT_LEN = 19.92         # flange front face to the tip
FLANGE_W = 5.5
FLANGE_LEN = 17.9         # centred on the shaft
FLANGE_T = 2.5
COLLAR_DIA = 9.0          # round middle of the flange (ASSUMED the same thickness as the rest)
BUMP_DIA = 4.2
BUMP_H = 1.8
BUMP_X = 6.9              # shaft centre to bump centre
RIB_LEN = 7.5             # alignment rib, on the side opposite the bump, from the flange up the shaft
RIB_W = 2.0
RIB_OUT = 1.4
SMALL_RIB_H = 1.5         # three small ribs at 90 degrees, rising this far up the shaft
GUSSET_RUN = 3.75         # the one on the bump side slopes out this far along the flange
SMALL_RIB_W = 1.0         # ASSUMED (not measured)
SMALL_RIB_OUT = 1.0       # ASSUMED (not measured), for the two side ribs

# --- What the new contact point needs ------------------------------------------------
OFFSET_OUT = 3.5          # plunger lands this far past the old bump, along the flange
EXTRA_REACH = 1.5         # and needs the surface this much closer than the old bump's top
PAD_PAST = 2.5            # the bump extends this far past the plunger's landing point

# --- Print allowances ------------------------------------------------------------------
SHAFT_FIT = 0.05          # printed round shafts come out slightly fat; take this off the diameter
TIP_CHAMFER = 0.5

PAD_Z = BUMP_H + EXTRA_REACH
TARGET_X = BUMP_X + OFFSET_OUT
X_END = TARGET_X + PAD_PAST          # end of the bump and of the flange on that side
R = (SHAFT_DIA - SHAFT_FIT) / 2
N = 64


def stadium(x0, x1, w):
    r = w / 2
    return m3.CrossSection.batch_hull([m3.CrossSection.circle(r, N).translate((x, 0.0))
                                       for x in (x0 + r, x1 - r)])


def box(x0, x1, y0, y1, z0, z1):
    return m3.Manifold.cube([x1 - x0, y1 - y0, z1 - z0]).translate((x0, y0, z0))


def build():
    """The button in its own coordinates (z = 0 at the flange's back face)."""
    front = -FLANGE_T                                      # flange front face
    tip = front - SHAFT_LEN
    flange = (stadium(-FLANGE_LEN / 2, X_END, FLANGE_W) + m3.CrossSection.circle(COLLAR_DIA / 2, N)
              ).extrude(FLANGE_T).translate((0, 0, front))
    shaft = (m3.Manifold.cylinder(SHAFT_LEN - TIP_CHAMFER + 0.01, R, R, N).translate((0, 0, tip + TIP_CHAMFER))
             + m3.Manifold.cylinder(TIP_CHAMFER, R - TIP_CHAMFER, R, N).translate((0, 0, tip)))
    rib = box(-(R + RIB_OUT), -(R - 0.6), -RIB_W / 2, RIB_W / 2, front - RIB_LEN, front + 0.01)
    side = box(-SMALL_RIB_W / 2, SMALL_RIB_W / 2, R - 0.6, R + SMALL_RIB_OUT, front - SMALL_RIB_H, front + 0.01)
    h = SMALL_RIB_W / 2
    gusset = m3.Manifold.hull_points([(x, y, z) for y in (-h, h) for x, z in
                                      ((R - 0.6, front + 0.01), (R + GUSSET_RUN, front + 0.01),
                                       (R - 0.6, front - SMALL_RIB_H))])
    bump = stadium(BUMP_X - BUMP_DIA / 2, X_END, BUMP_DIA).extrude(PAD_Z + 0.01).translate((0, 0, -0.01))
    return flange + shaft + rib + side + side.mirror((0.0, 1.0, 0.0)) + gusset + bump


def for_printing(part):
    """Bump face on the bed, shaft pointing up."""
    return part.mirror((0.0, 0.0, 1.0)).translate((0.0, 0.0, PAD_Z))


def write_stl(part, path):
    mesh = part.to_mesh()
    verts, tris = mesh.vert_properties, mesh.tri_verts
    with open(path, "wb") as f:
        f.write(b"Redlight TEST button".ljust(80, b" "))
        f.write(struct.pack("<I", len(tris)))
        for t in tris:
            a, b, c = (verts[i][:3] for i in t)
            u, v = b - a, c - a
            n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
            k = sum(x * x for x in n) ** 0.5 or 1.0
            f.write(struct.pack("<12fH", *[x / k for x in n], *a, *b, *c, 0))
    return len(tris)


def write_svg(path):
    s = 15.0                                               # px per mm
    ox, oy = 360.0, 230.0

    def P(x, z):
        return ox + x * s, oy - z * s

    def poly(pts, fill, extra=""):
        d = " ".join("%.1f,%.1f" % P(*p) for p in pts)
        return f'<polygon points="{d}" fill="{fill}" stroke="#1c2321" stroke-width="1.6" {extra}/>'

    def text(x, z, msg, size=14, fill="#1c2321", weight=400, anchor="middle", dy=0):
        px, py = P(x, z)
        return (f'<text x="{px:.1f}" y="{py + dy:.1f}" font-size="{size}" font-weight="{weight}" '
                f'fill="{fill}" text-anchor="{anchor}">{msg}</text>')

    def arrow(x0, z0, x1, z1, color="#c2185b"):
        (a, b), (c, d) = P(x0, z0), P(x1, z1)
        return (f'<line x1="{a:.1f}" y1="{b:.1f}" x2="{c:.1f}" y2="{d:.1f}" stroke="{color}" '
                f'stroke-width="2" marker-start="url(#h)" marker-end="url(#h)"/>')

    front, half = -FLANGE_T, FLANGE_LEN / 2
    tip = front - SHAFT_LEN
    red = "#e9685a"
    o = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 740" width="900" height="740" '
         'font-family="Inter, \'DejaVu Sans\', Arial, sans-serif">',
         '<defs><marker id="h" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" '
         'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#c2185b"/></marker></defs>',
         '<rect width="900" height="740" fill="#ffffff"/>',
         '<text x="24" y="40" font-size="26" font-weight="700" fill="#1c2321">Replacement TEST button</text>',
         '<text x="24" y="66" font-size="15" fill="#5f6b66">Side view. The switch is above; you press the tip '
         'at the bottom. Dashed: the original bump and flange end.</text>']
    o.append(poly([(-R, front), (-R, tip + TIP_CHAMFER), (-R + TIP_CHAMFER, tip), (R - TIP_CHAMFER, tip),
                   (R, tip + TIP_CHAMFER), (R, front)], red))
    o.append(poly([(-R - RIB_OUT, front), (-R - RIB_OUT, front - RIB_LEN), (-R, front - RIB_LEN), (-R, front)], red))
    o.append(poly([(R, front), (R + GUSSET_RUN, front), (R, front - SMALL_RIB_H)], red))
    o.append(poly([(-half, 0), (X_END, 0), (X_END, front), (-half, front)], red))
    o.append(poly([(BUMP_X - BUMP_DIA / 2, 0), (BUMP_X - BUMP_DIA / 2, PAD_Z), (X_END, PAD_Z), (X_END, 0)], red))
    o.append(poly([(BUMP_X - BUMP_DIA / 2, 0), (BUMP_X - BUMP_DIA / 2, BUMP_H), (BUMP_X + BUMP_DIA / 2, BUMP_H),
                   (BUMP_X + BUMP_DIA / 2, 0)], "none", 'stroke-dasharray="5 4"'))
    (a, b), (c, d) = P(half, 0.6), P(half, front - 0.6)
    o.append(f'<line x1="{a:.1f}" y1="{b:.1f}" x2="{c:.1f}" y2="{d:.1f}" stroke="#1c2321" stroke-width="1.4" '
             f'stroke-dasharray="5 4"/>')
    px, py = P(TARGET_X, PAD_Z)
    o.append(f'<path d="M{px - 22:.1f},{py - 58:.1f} h44 v36 h-14 v22 h-16 v-22 h-14 z" fill="#3a4046" '
             f'stroke="#1c2321" stroke-width="1.4"/>')
    o.append(text(TARGET_X, PAD_Z, "switch plunger", 13, "#1c2321", 700, dy=-66))
    o.append(arrow(BUMP_X, PAD_Z + 1.0, TARGET_X, PAD_Z + 1.0))
    o.append(text((BUMP_X + TARGET_X) / 2 - 1.4, PAD_Z + 1.0, f"{OFFSET_OUT:g}", 13, "#c2185b", 700, dy=-7))
    o.append(arrow(X_END + 1.0, BUMP_H, X_END + 1.0, PAD_Z))
    o.append(text(X_END + 1.5, (BUMP_H + PAD_Z) / 2, f"{EXTRA_REACH:g}", 13, "#c2185b", 700, "start", 5))
    o.append(arrow(R + 2.2, front, R + 2.2, tip, "#5f6b66"))
    o.append(text(R + 2.8, (front + tip) / 2, f"shaft {SHAFT_LEN:g} long, {SHAFT_DIA:g} dia", 13, "#5f6b66", 400, "start", 5))
    o.append(text(-R - RIB_OUT - 0.6, front - RIB_LEN / 2, "alignment rib", 13, "#1c2321", 700, "end", 5))
    o.append(text(-half - 0.6, front / 2, f"flange {FLANGE_T:g} thick", 13, "#1c2321", 700, "end", 5))
    notes = [f"Bump: {PAD_Z:g} mm high (the original {BUMP_H:g} plus {EXTRA_REACH:g}), running from the original position "
             f"to {X_END - FLANGE_LEN / 2:.2f} mm past the original flange end.",
             "Assumed, not measured: the 9 mm round part is the same thickness as the flange; the small ribs are 1 mm wide.",
             "Print bump-face down, shaft up, with supports under the flange (build plate only).",
             f"Printed size: {X_END + FLANGE_LEN / 2:.2f} x {COLLAR_DIA:g} x {PAD_Z + FLANGE_T + SHAFT_LEN:.1f} mm tall."]
    for i, n in enumerate(notes):
        o.append(f'<text x="24" y="{640 + i * 24}" font-size="15" fill="#1c2321">{n}</text>')
    o.append("</svg>")
    path.write_text("\n".join(o))


if __name__ == "__main__":
    out = HERE / "out"
    out.mkdir(exist_ok=True)
    part = for_printing(build())
    n = write_stl(part, out / "test_button.stl")
    write_svg(out / "test_button.svg")
    lo_x, lo_y, lo_z, hi_x, hi_y, hi_z = part.bounding_box()
    print(f"{n} triangles, status {part.status()}, volume {part.volume():.0f} mm3, "
          f"{hi_x - lo_x:.1f} x {hi_y - lo_y:.1f} x {hi_z - lo_z:.1f} mm as printed")
