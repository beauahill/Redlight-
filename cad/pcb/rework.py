"""Draw the rework for v2 boards, whose strip-tab pads have + and - swapped.

    python3 cad/pcb/rework.py     # writes out/rework_tower_side.svg, out/rework_speaker_side.svg

The strips' printed "+" is the clockwise half of each tab (seen from the tower
side); the v2 board put +5V on the counter-clockwise half. The rework turns
the tower's common pads into ground and drives each strip's + from a source
driver (TBD62783APG) instead of sinking its - with the TBD62083APG.
"""
import math
from html import escape

import assembly as A

CUT = "#c2185b"
WIRE_GND = "#1b1f23"
WIRE_5V = "#d2362b"
OLD_5V = "#f08a24"

# Board coordinates here are top-view mm with Y up (as in make_pcb.py).
TRACK_XIAO = [(7.62, 43.62), (4.39, 40.39), (4.39, 10.43), (3.39, 8.70)]        # top layer
TRACK_VIN = [(-3.39, -8.70), (-4.39, -10.43), (-4.39, -30.08), (-8.76, -34.45), (-8.76, -36.0)]  # top
TRACK_C2 = [(9.0, -6.3), (16.7, -14.0), (27.0, -14.0)]                           # bottom layer
RING_R = 11.03
CUT1, CUT2, CUT3 = (4.39, 20.0), (-4.39, -22.0), (12.6, -9.9)


def up(p):
    """Y-up board mm -> the Y-down coordinates assembly.View expects."""
    return p[0], -p[1]


def polyline(v, pts, color, width, dash=None, opacity=1.0):
    d = " ".join("%.1f,%.1f" % v.pt(up(p)) for p in pts)
    extra = f' stroke-dasharray="{dash}"' if dash else ""
    v.add(f'<polyline points="{d}" fill="none" stroke="{color}" stroke-width="{width}" '
          f'stroke-linecap="round" stroke-linejoin="round" opacity="{opacity}"{extra}/>')


def label(v, p, msg, color, size=16, anchor="middle"):
    x, y = v.pt(up(p))
    v.add(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-weight="700" fill="{color}" '
          f'text-anchor="{anchor}" dominant-baseline="central" paint-order="stroke" stroke="#ffffff" '
          f'stroke-width="5" stroke-linejoin="round">{escape(msg)}</text>')


def cut_mark(v, p, direction, name, label_at):
    """A bar across the track at p; `direction` is the track's direction there."""
    d = math.hypot(*direction)
    nx, ny = -direction[1] / d, direction[0] / d
    a = (p[0] + nx * 2.2, p[1] + ny * 2.2)
    b = (p[0] - nx * 2.2, p[1] - ny * 2.2)
    polyline(v, [a, b], "#ffffff", 9)
    polyline(v, [a, b], CUT, 5)
    label(v, label_at, name, CUT, 17)


def wire(v, pts, color, name, label_at):
    polyline(v, pts, "#ffffff", 9)
    polyline(v, pts, color, 5)
    for p in (pts[0], pts[-1]):
        x, y = v.pt(up(p))
        v.add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" fill="{color}" stroke="#ffffff" stroke-width="2"/>')
    label(v, label_at, name, color, 17)


def base(fps, edges, arcs, speaker_side):
    """Board and parts, faded, with the tab pads recoloured by what the strip needs."""
    v = A.View(mirror=speaker_side)
    keep = dict(A.COL)
    # Board "+" pads carry the strips' minus side: dark. Board "-" pads carry strip plus: red.
    A.COL["plus"], A.COL["minus"] = "#30363d", "#d2362b"
    v.add('<g opacity="0.5">')
    A.draw_board(v, edges, arcs, fps)
    order = sorted(fps.values(), key=lambda f: (not f.ref.startswith("LED"), f.ref))
    for fp in order:
        if fp.ref == "H1" or fp.ref.startswith("LED"):
            continue
        if fp.bottom == speaker_side:
            (A.draw_speaker_part if speaker_side else A.draw_tower_part)(v, fp)
        else:
            A.draw_ghost(v, fp)
    v.add("</g>")
    for fp in order:
        if fp.ref.startswith("LED"):
            A.draw_pads(v, fp)
            k = math.hypot(fp.x, fp.y)
            v.text((fp.x / k * 4.4, fp.y / k * 4.4), "D" + fp.ref[3:], 12, A.COL["ink"], 700)
    A.COL.update(keep)
    return v


def ring(v, color, width):
    pts = [(RING_R * math.cos(math.radians(a)), RING_R * math.sin(math.radians(a))) for a in range(0, 361, 6)]
    polyline(v, pts, color, width, opacity=0.9)


def tower_side(fps, edges, arcs):
    v = base(fps, edges, arcs, False)
    polyline(v, TRACK_XIAO, OLD_5V, 6, opacity=0.9)
    polyline(v, TRACK_VIN, OLD_5V, 6, opacity=0.9)
    cut_mark(v, CUT1, (0, 1), "CUT 1", (CUT1[0] + 6.5, CUT1[1]))
    cut_mark(v, CUT2, (0, 1), "CUT 2", (CUT2[0] + 7.0, CUT2[1]))
    label(v, (5.6, 23.6), "old 5 V feed from the XIAO", OLD_5V, 13, anchor="start")
    label(v, (-3.2, -27.0), "old 5 V to VIN", OLD_5V, 13, anchor="start")
    rows = [
        (WIRE_5V, "Why", [
            "The strips' printed + is the left half of each tab",
            "(seen from outside); this board put 5 V on the right",
            "half. Red pads = strip +, dark pads = strip −."]),
        ("#ffffff", "0. First, prove a strip with two AA cells", [
            "USB unplugged, chip out. Battery + on the joint under",
            "a printed +, battery − on the other half. It should",
            "light. Only then cut anything."]),
        (CUT, "1. CUT 1: 5 V feed from the XIAO", [
            "The wide trace running from under the XIAO straight",
            "to the tower, between R2 and R3. Cut it about halfway",
            "between the XIAO and the tower."]),
        (CUT, "2. CUT 2: 5 V to the amp", [
            "The wide trace running from the tower toward VIN,",
            "between R5 and R6. Cut it where it is in the open."]),
        ("#ffffff", "How to cut a trace", [
            "Two knife cuts about 1 mm apart across the trace,",
            "then pick out the sliver between them. Check with",
            "the meter (Ohms) that the two sides read OL."]),
        ("#ffffff", "Jumpers R1–R6 stay as they are", [
            "The socket stays too. The chip changes: see the",
            "speaker-side drawing."]),
    ]
    return page(v, "tower side", "Top view. Orange = existing copper that carries 5 V through the tower pads.",
                rows, "Rework, tower side")


def speaker_side(fps, edges, arcs):
    v = base(fps, edges, arcs, True)
    ring(v, OLD_5V, 5)
    polyline(v, TRACK_C2, OLD_5V, 6, opacity=0.9)
    cut_mark(v, CUT3, (1, -1), "CUT 3", (CUT3[0] + 5.0, CUT3[1] + 3.6))
    led6 = next(p["xy"] for p in fps["LED6"].pads if p["num"] == "+")
    j1 = {p["net"]: p["xy"] for p in fps["J1"].pads}
    xiao5 = fps["U1"].pad("5V")
    d6 = (led6[0], -led6[1])
    gnd = (j1["GND"][0], -j1["GND"][1])
    v5 = (j1["+5V"][0], -j1["+5V"][1])
    x5 = (xiao5[0], -xiao5[1])
    wire(v, [d6, (3.5, -19.0), (7.0, -30.5), gnd], WIRE_GND, "W1 ground", (1.0, -24.5))
    wire(v, [x5, (20.0, 34.0), (34.5, 16.0), (34.5, -24.0), v5], WIRE_5V, "W2 5 V", (30.0, 30.0))
    rows = [
        (CUT, "3. CUT 3: tower ring to the rest of 5 V", [
            "The trace leaving the tower's ring diagonally toward",
            "the socket. Cut it on the diagonal, in the open."]),
        ("#ffffff", "4. Check the tower is now separate", [
            "Ohms, USB unplugged: from the unmarked half of a",
            "strip tab to the 5V pad at J1 should read OL."]),
        (WIRE_GND, "5. W1: tower pads to ground", [
            "Insulated wire from the solder on strip D6's dark pad",
            "(the half without the printed +) to the GND pad at J1."]),
        (WIRE_5V, "6. W2: 5 V straight from the XIAO", [
            "Insulated wire, 22–24 AWG, from the XIAO's 5V pin tip",
            "to the 5V pad at J1. This replaces the old feed that",
            "ran through strip D2's pad."]),
        ("#ffffff", "7. Check every strip's ground", [
            "From the unmarked half of each tab to the GND pad at",
            "J1 should read about 0 Ω. Any that doesn't gets a",
            "short wire to a neighbour's unmarked half."]),
        ("#ffffff", "8. New driver chip: TBD62783APG", [
            "Same socket, notch toward the XIAO, but its pins 9",
            "and 10 are the other way round. See the chip drawing.",
            "Never plug it in unmodified: it would be powered",
            "backwards."]),
        ("#ffffff", "9. Later, with the amp", [
            "One more wire from the 5V pad at J1 to the amp's VIN",
            "hole, since CUT 2 removed its supply."]),
    ]
    return page(v, "speaker side", "Mirrored view: the board turned over sideways, XIAO end still at the top.",
                rows, "Rework, speaker side")


def page(v, side, sub, rows, title):
    w, h = A.BOARD_W + A.PANEL_W, A.HEAD_H + A.BOARD_H + 20
    head = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
        f'font-family="Inter, \'DejaVu Sans\', Arial, sans-serif">',
        f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
        f'<text x="24" y="40" font-size="26" font-weight="700" fill="{A.COL["ink"]}">'
        f'Redlight PCB v2 rework: {side}</text>',
        f'<text x="24" y="66" font-size="15" fill="{A.COL["muted"]}">{escape(sub)}</text>',
    ]
    out = [f'<text x="{A.BOARD_W + 16}" y="{A.HEAD_H + 26}" font-size="19" font-weight="700" '
           f'fill="{A.COL["ink"]}">{escape(title)}</text>']
    x0, y = A.BOARD_W + 16, A.HEAD_H + 62
    for swatch, head_text, lines in rows:
        out.append(f'<rect x="{x0}" y="{y - 14}" width="26" height="18" rx="3" fill="{swatch}" '
                   f'stroke="{A.COL["ink"]}" stroke-width="1.2"/>')
        out.append(f'<text x="{x0 + 38}" y="{y}" font-size="16" font-weight="700" fill="{A.COL["ink"]}">'
                   f'{escape(head_text)}</text>')
        y += 22
        for ln in lines:
            out.append(f'<text x="{x0 + 38}" y="{y}" font-size="14" fill="{A.COL["muted"]}">{escape(ln)}</text>')
            y += 19
        y += 16
    return "\n".join(head + v.out + out + ["</svg>"])


def chip_figure():
    """Top view of the TBD62783APG in the socket with pins 9 and 10 crossed over."""
    w, h = 1080, 760
    ink, muted = A.COL["ink"], A.COL["muted"]
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
         f'font-family="Inter, \'DejaVu Sans\', Arial, sans-serif">',
         f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
         f'<text x="24" y="40" font-size="26" font-weight="700" fill="{ink}">'
         f'Redlight PCB v2 rework: the new driver chip</text>',
         f'<text x="24" y="66" font-size="15" fill="{muted}">TBD62783APG seen from above, in the U2 socket. '
         f'Notch toward the XIAO, as before.</text>']
    cx, top, pitch, half = 330, 150, 52, 78        # column centre, first pin row, row pitch, half row spacing

    def t(x, y, msg, size=15, fill=ink, weight=600, anchor="middle"):
        o.append(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{fill}" '
                 f'text-anchor="{anchor}" dominant-baseline="central">{escape(msg)}</text>')

    # Socket frame and chip body.
    o.append(f'<rect x="{cx - half - 34}" y="{top - 40}" width="{2 * half + 68}" height="{8 * pitch + 80}" rx="6" '
             f'fill="{A.COL["socket"]}" stroke="{ink}" stroke-width="1.5"/>')
    o.append(f'<rect x="{cx - half + 22}" y="{top - 26}" width="{2 * half - 44}" height="{8 * pitch + 52}" rx="4" '
             f'fill="{A.COL["ic"]}" stroke="{ink}" stroke-width="1.5"/>')
    o.append(f'<path d="M{cx - 16},{top - 26} A16,16 0 0 0 {cx + 16},{top - 26}" fill="{A.COL["socket"]}" '
             f'stroke="{ink}" stroke-width="1.5"/>')
    t(cx, top - 62, "XIAO end (notch)", 15, muted)
    t(cx, top + 4 * pitch, "TBD62783APG", 16, "#ffffff", 700)
    o[-1] = o[-1].replace("<text ", f'<text transform="rotate(-90 {cx} {top + 4 * pitch})" ')
    for k in range(9):
        y = top + k * pitch
        for side, num in ((-1, k + 1), (1, 18 - k)):
            x = cx + side * half
            crossed = num in (9, 10)
            o.append(f'<circle cx="{x}" cy="{y}" r="9" fill="#ffffff" stroke="{ink}" stroke-width="1.5"/>')
            if crossed:                           # pin bent out sideways, clear of its socket hole
                o.append(f'<path d="M{x - side * 56},{y - 16} L{x - side * 30},{y - 16} L{x + side * 62},{y - 46}" '
                         f'fill="none" stroke="{A.COL["pad"]}" stroke-width="7" stroke-linecap="round" '
                         f'stroke-linejoin="round"/>')
            else:                                 # pin sitting in its hole
                o.append(f'<line x1="{x - side * 56}" y1="{y}" x2="{x}" y2="{y}" stroke="{A.COL["pad"]}" '
                         f'stroke-width="7" stroke-linecap="round"/>')
                o.append(f'<circle cx="{x}" cy="{y}" r="4.5" fill="{A.COL["pad"]}"/>')
            if not crossed:
                t(x + side * 30, y, str(num), 15)
    y9 = top + 8 * pitch
    lx, rx = cx - half, cx + half
    # Wires: chip pin 9 (left, VCC) -> socket hole 10 (right, 5 V); chip pin 10 (right, GND) -> hole 9 (left).
    for x0, x1, color, dy in ((lx - 62, rx, WIRE_5V, 74), (rx + 62, lx, WIRE_GND, 118)):
        d = f"M{x0},{y9 - 46} L{x0},{y9 + dy} L{x1},{y9 + dy} L{x1},{y9}"
        o.append(f'<path d="{d}" fill="none" stroke="#ffffff" stroke-width="10" stroke-linejoin="round"/>')
        o.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="5.5" stroke-linejoin="round" '
                 f'stroke-linecap="round"/>')
        o.append(f'<circle cx="{x0}" cy="{y9 - 46}" r="7" fill="{color}" stroke="#ffffff" stroke-width="2"/>')
        o.append(f'<circle cx="{x1}" cy="{y9}" r="6" fill="{color}" stroke="#ffffff" stroke-width="2"/>')
    t(lx - 76, y9 - 46, "chip pin 9 (VCC)", 14, WIRE_5V, 700, "end")
    t(rx + 76, y9 - 46, "chip pin 10 (GND)", 14, WIRE_GND, 700, "start")
    t(lx + 30, y9, "hole 9", 12, "#ffffff", 700, "start")
    t(lx + 30, y9 + 15, "GND", 12, "#ffffff", 700, "start")
    t(rx - 30, y9, "hole 10", 12, "#ffffff", 700, "end")
    t(rx - 30, y9 + 15, "5 V", 12, "#ffffff", 700, "end")
    notes = [
        ("Why", ["On this board socket hole 9 is ground and hole 10 is 5 V.",
                 "On the new chip pin 9 is its supply and pin 10 is its ground."]),
        ("1. Bend two pins", ["Bend pins 9 and 10 straight out sideways so they",
                              "cannot enter the socket. They are the two pins at",
                              "the end away from the notch."]),
        ("2. Add two insulated wires", ["Chip pin 9 to socket hole 10 (red, 5 V).",
                                        "Chip pin 10 to socket hole 9 (black, ground).",
                                        "Solid-core wire or a clipped lead plugs into the",
                                        "socket hole; insulate them where they cross."]),
        ("3. Check before power", ["Ohms: chip pin 9 to the 5V pad at J1 reads about 0;",
                                   "chip pin 10 to the GND pad at J1 reads about 0."]),
        ("Never plug it in unmodified", ["Straight in, it is powered backwards and will be",
                                         "destroyed. The old TBD62083APG is not used."]),
    ]
    x0, y = 640, 128
    for head_text, lines in notes:
        o.append(f'<text x="{x0}" y="{y}" font-size="16" font-weight="700" fill="{ink}">{escape(head_text)}</text>')
        y += 22
        for ln in lines:
            o.append(f'<text x="{x0}" y="{y}" font-size="14" fill="{muted}">{escape(ln)}</text>')
            y += 19
        y += 16
    return "\n".join(o + ["</svg>"])


def main():
    A.BOARD = A.HERE / "v2" / "redlight_v2.kicad_pcb"     # the rework applies to v2 boards only
    fps, edges, arcs = A.load()
    A.OUT.mkdir(exist_ok=True)
    for name, fn in (("rework_tower_side", tower_side), ("rework_speaker_side", speaker_side)):
        path = A.OUT / f"{name}.svg"
        path.write_text(fn(fps, edges, arcs))
        print(f"wrote {path}")
    path = A.OUT / "rework_chip.svg"
    path.write_text(chip_figure())
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
