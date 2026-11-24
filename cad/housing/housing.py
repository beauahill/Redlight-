"""Printed housing for the full-size replicas: two shell halves with the guard
cage built in, the red globe, the speaker cup and the three button plungers.

    python3 cad/housing/housing.py         # -> cad/housing/out/*.stl, assembly.step

The shape follows the original (MEASURED on it, see docs/PLAN.md) but isn't a
copy: no emblem plate, a plain bow-tie button on the collar, printed seam lugs
for M3 screws with heat-set inserts, and a panel hole for the barrel jack.

Coordinates: millimetres, Z up from the table, the tower screw on the Z axis.
-Y is the FRONT (buttons). The halves split on the XZ plane (seam at +-X), so
the tower PCB's flats, which face +-X, sit at the seam. The PCB uses the same
top-view axes as cad/pcb/make_pcb.py, so its switches face the buttons.

Stack (from the table):
    0 - 4.9    battery insert flange, in a recess in the bottom
    4.9 - 7.1  bottom plate, 2.2 mm, that the insert's ears catch on
    80         speaker cup groove (the original's is at 75; moved up 5 mm so
               the insert's top end clears the cup)
    112        tower PCB groove (MEASURED)
    115        globe flange groove
    136        top of the collar band, where the cage starts
    300        top of the cage (MEASURED)
"""
import math
from pathlib import Path

import cadquery as cq

HERE = Path(__file__).parent
ROOT = HERE.parent
OUT = HERE / "out"

# --- Outside shape, MEASURED on the original (diameters halved) ------------------
FOOT_R = 134 / 2
FOOT_BAND = 8.0            # straight band at the bottom of the foot
FOOT_TOP = 30.0            # the foot flares in to the neck by here
NECK_R = 97 / 2
COLLAR_R = 114 / 2
COLLAR_BOTTOM = 96.5       # 45 deg chamfer from the neck below this
COLLAR_TOP = 136.0
CAGE_R = 111 / 2
HEIGHT = 300.0
WALL = 2.4                 # the original is 2.1 mm cast aluminium; 6 perimeters of PETG

# --- Inside ---------------------------------------------------------------------------
PCB_Z = 112.0              # groove centerline, MEASURED from the bottom face
PCB_T = 1.6
PCB_R = 109.5 / 2
PCB_FLAT_X = 74.15 / 2
SLOT_CLEAR = 0.3
COLLAR_IN_R = 52.5         # collar band is thick (4.5 mm) so the grooves have depth

GLOBE_FLANGE_R = 109 / 2   # MEASURED
GLOBE_FLANGE_T = 2.1       # MEASURED
RIB = 2.0                  # between the PCB groove and the globe groove

SPK_Z = 80.0               # speaker cup groove centerline (see the docstring)
SPK_FLANGE_R = 91.5 / 2    # MEASURED: the cup's rim that sits in the groove
SPK_FLANGE_T = 3.0
SPK_CUP_H = 22.8           # MEASURED
SPEAKER_D = 64.0           # MEASURED

INSERT_FLANGE_T = 4.9      # the rev07 insert: flange face to collar
PLATE_T = 2.2              # its ears catch 2.4 mm above the flange

# --- Cage -------------------------------------------------------------------------------
BAR_D = 3.65               # MEASURED
BAR_R = CAGE_R - BAR_D / 2
RING_STEP = 40.0           # MEASURED
RINGS = [COLLAR_TOP + RING_STEP * k for k in (1, 2, 3)]
ARC_START = 262.0          # vertical bars bend in over the globe from here
TOP_RING_R = 22.0
SEAM_BAR_W = 7.0           # bars on the seam are flat, so each half gets a solid share

# --- Globe (MEASURED unless noted) -------------------------------------------------------
GLOBE_H = 170.0
GLOBE_R = 86 / 2
SKIRT_IN_R = 100 / 2       # MEASURED: the wide part above the flange, inside
SKIRT_H = 17.4
GLOBE_WALL = 2.0           # assumed
DOME_H = 28.0              # assumed: height of the rounded top
RIBS = 120                 # fine vertical ribs on the cylinder

# --- Buttons: the PCB's angled switches (cad/pcb/make_pcb.py BUTTONS) --------------------
# Actuator fronts, top view, pointing -Y. The switches hang under the board;
# their actuators are about 3.5 mm below its bottom face (PTS645 angled).
SWITCHES = {"TEST": (0.0, -39.6), "VOL+": (-10.075, -48.0), "VOL-": (10.075, -48.0)}
BUTTON_Z = PCB_Z - PCB_T / 2 - 3.5
BTN_CLEAR = 0.25

# --- Seam screws (M3, heat-set insert in the back half) ------------------------------------
LUG_Z = [18.0, 60.0, 101.0, 196.0, 236.0]
SCREW_D = 3.4
INSERT_D = 4.2             # M3 heat-set insert hole
HEAD_D = 6.5

JACK_Z = 45.0              # panel-mount barrel jack, back of the neck
JACK_D = 8.2               # for the common M8-threaded 5.5 x 2.1 jack


def outer_r(z):
    """Outside radius of the shell at height z."""
    if z <= FOOT_BAND:
        return FOOT_R
    if z <= FOOT_TOP:
        # Concave flare: quarter ellipse centered at (FOOT_R, FOOT_TOP).
        c = (FOOT_TOP - z) / (FOOT_TOP - FOOT_BAND)
        return FOOT_R - (FOOT_R - NECK_R) * math.sqrt(max(0.0, 1 - c * c))
    if z <= COLLAR_BOTTOM - (COLLAR_R - NECK_R):
        return NECK_R
    if z <= COLLAR_BOTTOM:
        return COLLAR_R - (COLLAR_BOTTOM - z)
    return COLLAR_R


def revolve(points):
    """Solid of revolution about Z from (r, z) points."""
    return cq.Workplane("XZ").polyline(points).close().revolve(360, (0, 0, 0), (0, 1, 0))


def ring(r_in, r_out, z0, z1):
    return (cq.Workplane("XY").workplane(offset=z0).circle(r_out).circle(r_in).extrude(z1 - z0))


def box(x0, x1, y0, y1, z0, z1):
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))


# --- Shell -------------------------------------------------------------------------------
def shell():
    flare = [FOOT_BAND + (FOOT_TOP - FOOT_BAND) * k / 16 for k in range(17)]
    neck_top = COLLAR_BOTTOM - (COLLAR_R - NECK_R)
    outside = ([(0, 0), (FOOT_R, 0)] + [(outer_r(z), z) for z in flare]
               + [(NECK_R, neck_top), (COLLAR_R, COLLAR_BOTTOM), (COLLAR_R, COLLAR_TOP), (0, COLLAR_TOP)])
    body = revolve(outside)

    plate_top = INSERT_FLANGE_T + PLATE_T
    neck_in = NECK_R - WALL
    inside = ([(0, plate_top), (FOOT_R - WALL, plate_top)]
              + [(outer_r(z) - WALL, z) for z in flare if z > plate_top]
              + [(neck_in, neck_top + WALL), (neck_in, COLLAR_BOTTOM - 1.0),
                 (COLLAR_IN_R, COLLAR_BOTTOM - 1.0 + (COLLAR_IN_R - neck_in)),
                 (COLLAR_IN_R, COLLAR_TOP + 1), (0, COLLAR_TOP + 1)])
    body = body.cut(revolve(inside))

    # Battery insert: recess for its flange, and the opening its collar
    # passes through (its outline plus clearance; the ears snap over the plate).
    body = body.cut(cq.Workplane("XY").workplane(offset=-1).circle(45.5 + 0.4).extrude(INSERT_FLANGE_T + 1))
    body = body.cut(insert_opening(INSERT_FLANGE_T - 0.5, plate_top + 0.5))

    # PCB groove, with keys at the board's flats so it can only sit one way round.
    z0, z1 = PCB_Z - PCB_T / 2 - 0.15, PCB_Z + PCB_T / 2 + 0.15
    body = body.cut(ring(COLLAR_IN_R - 1, PCB_R + SLOT_CLEAR, z0, z1))
    for s in (-1, 1):
        key = box(min(s * (PCB_FLAT_X + 0.3), s * (PCB_R + 2)), max(s * (PCB_FLAT_X + 0.3), s * (PCB_R + 2)),
                  -15, 15, z0, z1).intersect(ring(0, PCB_R + SLOT_CLEAR + 0.1, z0, z1))
        body = body.union(key)
    # Globe flange groove just above it.
    g0 = z1 + RIB
    body = body.cut(ring(COLLAR_IN_R - 1, GLOBE_FLANGE_R + SLOT_CLEAR, g0, g0 + GLOBE_FLANGE_T + 0.3))

    # Speaker cup groove: two ribs on the neck wall, the lower one with a 45 deg
    # underside so the half prints standing up without support.
    h = SPK_FLANGE_T / 2 + 0.15
    r_in = SPK_FLANGE_R - 2.6
    body = body.union(revolve([(neck_in + 0.01, SPK_Z - h - 1.5 - 2.7), (r_in, SPK_Z - h - 1.5),
                               (r_in, SPK_Z - h), (neck_in + 0.01, SPK_Z - h)]))
    body = body.union(revolve([(neck_in + 0.01, SPK_Z + h), (r_in, SPK_Z + h),
                               (r_in, SPK_Z + h + 1.5), (neck_in + 0.01, SPK_Z + h + 4.2)]))

    # Barrel jack in the back of the neck.
    body = body.cut(cq.Workplane("XZ").workplane(offset=-(NECK_R - 8)).center(0, JACK_Z)
                    .circle(JACK_D / 2).extrude(-15))
    return body


def insert_opening(z0, z1):
    """The rev07 insert's collar outline, turned to housing coordinates, plus clearance."""
    from shapely.geometry import Polygon
    from shapely.ops import unary_union

    ins = cq.importers.importStep(str(ROOT / "insert" / "out" / "RedLight_Insert_rev07.step"))
    polys = []
    pts = []
    for z in (-0.3, -1.2, -2.1):                   # the collar, between the flange and the ears
        for e in ins.section(z).edges().vals():
            n = max(2, int(e.Length() / 0.5))
            pts += [(v.x, v.y) for v in (e.positionAt(k / n) for k in range(n + 1))]
    # Its outline is a rounded square; the hull is what the plate has to clear.
    # Turn it over (180 deg about X: y -> -y) so the flange face is on the table.
    outline = unary_union([Polygon(pts).convex_hull]).buffer(0.35, join_style=2)
    rings = [outline] if outline.geom_type == "Polygon" else list(outline.geoms)
    cut = None
    for g in rings:
        pts = [(x, -y) for x, y in list(g.exterior.coords)[:-1]]
        c = cq.Workplane("XY").workplane(offset=z0).polyline(pts).close().extrude(z1 - z0)
        cut = c if cut is None else cut.union(c)
    return cut


def insert_in_place():
    ins = cq.importers.importStep(str(ROOT / "insert" / "out" / "RedLight_Insert_rev07.step"))
    return ins.rotate((0, 0, 0), (1, 0, 0), 180).translate((0, 0, INSERT_FLANGE_T))


# --- Cage ---------------------------------------------------------------------------------
def arc_path(angle, steps=24):
    """Bar centerline bending in from the vertical bar to the top ring."""
    a = math.radians(angle)
    pts = []
    for k in range(steps + 1):
        t = math.pi / 2 * k / steps
        r = (TOP_RING_R - 1.0) + (BAR_R - TOP_RING_R + 1.0) * math.cos(t)   # ends inside the top ring
        z = ARC_START + (HEIGHT - BAR_D / 2 - ARC_START) * math.sin(t)
        pts.append(cq.Vector(r * math.cos(a), r * math.sin(a), z))
    return cq.Wire.assembleEdges([cq.Edge.makeSpline(pts)])


def cage():
    parts = []
    for angle in (0, 90, 180, 270):
        a = math.radians(angle)
        cx, cy = BAR_R * math.cos(a), BAR_R * math.sin(a)
        seam = angle in (0, 180)
        plane = cq.Plane(origin=(cx, cy, COLLAR_TOP - 0.5), xDir=(math.cos(a), math.sin(a), 0), normal=(0, 0, 1))
        wp = cq.Workplane(plane)
        prof = wp.rect(BAR_D, SEAM_BAR_W) if seam else wp.circle(BAR_D / 2)
        parts.append(prof.extrude(ARC_START - COLLAR_TOP + 0.5))
        plane2 = cq.Plane(origin=(cx, cy, ARC_START), xDir=(math.cos(a), math.sin(a), 0), normal=(0, 0, 1))
        wp2 = cq.Workplane(plane2)
        prof2 = wp2.rect(BAR_D, SEAM_BAR_W) if seam else wp2.circle(BAR_D / 2)
        parts.append(prof2.sweep(cq.Workplane().add(arc_path(angle)), transition="round"))
    for z in RINGS:
        parts.append(cq.Workplane().add(cq.Solid.makeTorus(BAR_R, BAR_D / 2, pnt=cq.Vector(0, 0, z))))
    parts.append(cq.Workplane().add(cq.Solid.makeTorus(TOP_RING_R, BAR_D / 2,
                                                         pnt=cq.Vector(0, 0, HEIGHT - BAR_D / 2))))
    out = parts[0]
    for p in parts[1:]:
        out = out.union(p)
    assert out.val().isValid(), "cage solid is invalid"
    return out


# --- Seam lugs ---------------------------------------------------------------------------------
def lug_r(z):
    return BAR_R if z > COLLAR_TOP else outer_r(z)


def lugs():
    solids, holes = [], []
    for z in LUG_Z:
        r = lug_r(z)
        inner = r - (BAR_D / 2 if z > COLLAR_TOP else WALL) - 0.5
        outer = r + 7.0
        drop = outer - inner              # 45 deg chamfer under the lug, so it prints standing up
        for s in (-1, 1):
            xi, xo = s * inner, s * outer
            pts = [(xi, z - 5 - drop), (xo, z - 5), (xo, z + 5), (xi, z + 5)]
            prof = cq.Workplane("XZ").workplane(offset=-6).polyline(pts).close().extrude(12)
            solids.append(prof)
            holes.append((s * (r + 3.2), z))
    return solids, holes


def split(body, holes):
    """Cut along the XZ plane. Front half (-Y) gets clearance holes with
    counterbores; back half (+Y) gets holes for M3 heat-set inserts."""
    front = body.intersect(box(-100, 100, -100, 0, -1, HEIGHT + 1))
    back = body.intersect(box(-100, 100, 0, 100, -1, HEIGHT + 1))
    for x, z in holes:
        front = front.cut(cq.Workplane("XZ").center(x, z).circle(SCREW_D / 2).extrude(10))
        front = front.cut(cq.Workplane("XZ").workplane(offset=3).center(x, z).circle(HEAD_D / 2).extrude(10))
        back = back.cut(cq.Workplane("XZ").center(x, z).circle(INSERT_D / 2).extrude(-5.5))
    return front, back


# --- Buttons --------------------------------------------------------------------------------
def button_outline(name, grow=0.0):
    """Outside face of each button, in the XZ plane (seen from the front)."""
    x, _ = SWITCHES[name]
    if name == "TEST":
        return cq.Workplane("XZ").center(0, BUTTON_Z).circle(3.2 + grow)
    s = 1 if x > 0 else -1
    # Bow-tie wings: narrow at the middle, wide at the outside.
    pts = [(s * (5.6 - grow), BUTTON_Z - 1.9 - grow), (s * (14.6 + grow), BUTTON_Z - 3.0 - grow),
           (s * (14.6 + grow), BUTTON_Z + 3.0 + grow), (s * (5.6 - grow), BUTTON_Z + 1.9 + grow)]
    return cq.Workplane("XZ").polyline(pts).close()


def wall_inside_y(xs):
    return -max(math.sqrt(COLLAR_IN_R ** 2 - x * x) for x in xs)


def button_holes():
    cut = None
    for name in SWITCHES:
        c = button_outline(name, BTN_CLEAR).extrude(-(COLLAR_R + 5)).translate((0, -COLLAR_R - 5, 0))
        cut = c if cut is None else cut.union(c)
    return cut.intersect(box(-30, 30, -COLLAR_R - 5, -COLLAR_IN_R + 4, 0, 200))


def plunger(name):
    """Button cap through the collar wall, a stop plate inside, and a pin to
    the switch actuator. Fit from inside before closing the halves."""
    x, y_act = SWITCHES[name]
    y_out = -COLLAR_R - 1.0             # 1 mm proud at the middle of the front
    # Stop plate inside the wall, kept under the PCB groove; it starts where
    # the curved wall's inside face is, at the plate's outer corner.
    stop_w = 9.0 if name == "TEST" else 11.0
    y_stop = wall_inside_y([abs(x) + stop_w / 2]) + 0.3
    cap = button_outline(name).extrude(-(y_stop - y_out)).translate((0, y_out, 0))
    stop = box(x - stop_w / 2, x + stop_w / 2, y_stop, y_stop + 1.6, BUTTON_Z - 3.0, BUTTON_Z + 2.8)
    pin = box(x - 1.2, x + 1.2, y_stop + 1.6, y_act - 0.2, BUTTON_Z - 1.2, BUTTON_Z + 1.2)
    return cap.union(stop).union(pin)


# --- Globe ---------------------------------------------------------------------------------------
def globe():
    """Translucent red PETG. Z = 0 is the flange's bottom face."""
    cyl_top = GLOBE_H - DOME_H
    w = GLOBE_WALL
    skirt_r = SKIRT_IN_R + w
    taper = skirt_r - GLOBE_R

    def dome(r, h, steps=18):
        return [(r * math.cos(math.pi / 2 * k / steps), cyl_top + h * math.sin(math.pi / 2 * k / steps))
                for k in range(steps + 1)]

    outside = ([(0, 0), (GLOBE_FLANGE_R, 0), (GLOBE_FLANGE_R, GLOBE_FLANGE_T), (skirt_r, GLOBE_FLANGE_T),
                (skirt_r, SKIRT_H), (GLOBE_R, SKIRT_H + taper)] + dome(GLOBE_R, DOME_H))
    inside = ([(0, -1), (SKIRT_IN_R, -1), (SKIRT_IN_R, SKIRT_H), (GLOBE_R - w, SKIRT_H + taper)]
              + dome(GLOBE_R - w, DOME_H - w))
    g = revolve(outside).cut(revolve(inside))
    # Fine vertical ribs on the cylinder: a star cross-section, 0.5 mm deep.
    pts = []
    for k in range(2 * RIBS):
        r = GLOBE_R + (0.5 if k % 2 == 0 else 0.0)
        a = math.pi * k / RIBS
        pts.append((r * math.cos(a), r * math.sin(a)))
    z0, z1 = SKIRT_H + taper, cyl_top
    ribs = (cq.Workplane("XY").workplane(offset=z0).polyline(pts).close().extrude(z1 - z0)
            .cut(cq.Workplane("XY").workplane(offset=z0 - 1).circle(GLOBE_R - 0.2).extrude(z1 - z0 + 2)))
    return g.union(ribs)


# --- Speaker cup -------------------------------------------------------------------------------------
def speaker_cup():
    """Z = 0 is the rim's bottom face. The speaker sits face up in a recess in
    the top plate (glue it, or hold it with three dabs of hot glue), its magnet
    hanging down inside the cup. Print rim down."""
    r_body = SPEAKER_D / 2 + 5.5
    t = 2.0
    top = SPK_CUP_H
    hole_r = SPEAKER_D / 2 - 4.0
    f = SPK_FLANGE_R - 0.2
    step_r = SPK_FLANGE_R - 3.0          # clear of the groove's upper rib
    prof = [(r_body - t, 0), (f, 0), (f, SPK_FLANGE_T), (step_r, SPK_FLANGE_T),
            (r_body, SPK_FLANGE_T + (step_r - r_body)),
            (r_body, top), (hole_r, top), (hole_r, top - t),
            (r_body - t, top - t - (r_body - t - hole_r))]     # 45 deg underside, no support
    cup = revolve(prof)
    cup = cup.cut(cq.Workplane("XY").workplane(offset=top - 1.5).circle(SPEAKER_D / 2 + 0.4).extrude(2))
    # Notch for the speaker wires.
    cup = cup.cut(box(-3, 3, 0, SPK_FLANGE_R + 1, -1, 6))
    return cup


# --- Build --------------------------------------------------------------------------------------------
def build():
    body = shell().union(cage())
    solids, holes = lugs()
    for s in solids:
        body = body.union(s)
    body = body.cut(button_holes())
    assert body.val().isValid(), "housing solid is invalid"
    front, back = split(body, holes)
    parts = {
        "housing_front": front,
        "housing_back": back,
        "globe": globe(),
        "speaker_cup": speaker_cup(),
        "button_test": plunger("TEST"),
        "button_vol_plus": plunger("VOL+"),
        "button_vol_minus": plunger("VOL-"),
    }
    return parts


# Where each loose part sits in the assembly.
PLACE = {
    "globe": (0, 0, PCB_Z + PCB_T / 2 + 0.15 + RIB + 0.15),
    "speaker_cup": (0, 0, SPK_Z - SPK_FLANGE_T / 2),
}


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    parts = build()
    asm = cq.Assembly()
    for name, p in parts.items():
        cq.exporters.export(p, str(OUT / f"{name}.stl"), tolerance=0.03, angularTolerance=0.1)
        bb = p.val().BoundingBox()
        print(f"{name:18s} {bb.xlen:6.1f} x {bb.ylen:6.1f} x {bb.zlen:6.1f} mm  {p.val().Volume() / 1000:6.1f} cm3")
        asm.add(p.translate(PLACE.get(name, (0, 0, 0))), name=name)
    asm.save(str(OUT / "assembly.step"))
