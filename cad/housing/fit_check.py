"""Check the whole light for parts that run into each other.

    python3 cad/housing/fit_check.py

Puts every part where it goes (housing halves, globe, speaker cup and a
stand-in speaker, button plungers, the tower PCB fit model with stand-ins for
its underside switches, tower core, strips, battery insert) and reports any
pair that overlaps, then the closest approaches that matter. Exits non-zero on
an overlap.
"""
from pathlib import Path
import sys, math, itertools
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "cad/housing")); sys.path.insert(0, str(ROOT / "cad/tower"))
import housing as H, core as C, cadquery as cq
parts = H.build()
board_z = H.PCB_Z - H.PCB_T/2 - 0.15
P = {}
P["front"] = parts["housing_front"]; P["back"] = parts["housing_back"]
P["globe"] = parts["globe"].translate(H.PLACE["globe"])
P["cup"] = parts["speaker_cup"].translate(H.PLACE["speaker_cup"])
for b in ("button_test","button_vol_plus","button_vol_minus"): P[b]=parts[b]
P["pcb"] = cq.importers.importStep(str(ROOT / "cad/pcb/out/redlight_fit.step")).translate((0,0,board_z))
top = board_z + 1.6
P["core"] = C.build().translate((0,0,top))
strips=None
for k in range(6):
    s=(cq.Workplane("XY").workplane(offset=-3.4).center(C.AF_OUT/2+0.5,0).rect(1.0,5.15).extrude(3.4)
       .union(cq.Workplane("XY").center(C.AF_OUT/2+0.5,0).rect(1.0,6.15).extrude(C.BODY))
       .union(cq.Workplane("XY").workplane(offset=C.BODY).center(C.AF_OUT/2+0.5,0).rect(1.0,5.15).extrude(2.9))
       .rotate((0,0,0),(0,0,1),60*k).translate((0,0,top)))
    strips = s if strips is None else strips.union(s)
P["strips"]=strips
P["insert"] = H.insert_in_place()
# speaker body: 64 mm frame on the cup top, magnet 40 dia hanging 20 down
cup_top = H.PLACE["speaker_cup"][2] + H.SPK_CUP_H
P["speaker"] = (cq.Workplane("XY").workplane(offset=cup_top-1.5).circle(32).extrude(4)
                .union(cq.Workplane("XY").workplane(offset=cup_top-20).circle(20).extrude(18.5)))
# switches under the board: 6x6 bodies with actuators
sw=None
for n,(x,y) in H.SWITCHES.items():
    b = H.box(x-3.5, x+3.5, y+0.0, y+6.5+3.15, board_z-7.0, board_z)
    sw = b if sw is None else sw.union(b)
P["switches"]=sw
names=list(P)
bad = 0
for a,b in itertools.combinations(names,2):
    try:
        v = P[a].intersect(P[b]).val().Volume()
    except Exception: v=0
    if v>0.01:
        print(f"OVERLAP {a} x {b}: {v:.2f} mm3"); bad += 1
print("checked", len(names), "parts")
print("closest approaches (0 = resting on each other, as intended):")
for a,b in (("insert","cup"),("insert","front"),("speaker","switches"),("globe","strips"),("globe","pcb"),("globe","front"),("cup","front"),("button_test","switches"),("pcb","front")):
    print(f"  {a} to {b}: {P[a].val().distance(P[b].val()):.2f} mm")

sys.exit(1 if bad else 0)
