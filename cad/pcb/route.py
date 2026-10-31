"""Autoroute redlight.kicad_pcb with Freerouting, pour ground, run DRC and
export fabrication files.

    FREEROUTING_JAR=/path/to/freerouting-1.9.0.jar python3 cad/pcb/route.py

Outputs cad/pcb/fab/ (Gerbers + drill, zipped for JLCPCB / PCBWay / OSH Park).
"""
import os
import re
import shutil
import subprocess
import zipfile
from pathlib import Path

import pcbnew

HERE = Path(__file__).parent
PCB = HERE / "redlight.kicad_pcb"
WORK = HERE / "build"
FAB = HERE / "fab"
JAR = os.environ.get("FREEROUTING_JAR", str(HERE / "freerouting.jar"))

POWER = ["+5V", "GND"]
LED = [f"/OUT{i}" for i in range(1, 7)] + [f'"/STRIP{i}-"' for i in range(1, 7)]


def write_dsn(board, path):
    pcbnew.ExportSpecctraDSN(board, str(path))
    dsn = path.read_text()
    # Track widths per net class (units: um). KiCad exports a single class.
    m = re.search(r'\(class kicad_default "" (.*?)\(circuit', dsn, re.S)
    names = m.group(1).split()
    signal = [n for n in names if n not in POWER and n not in LED]
    classes = (
        f'(class kicad_default "" {" ".join(signal)}\n'
        '      (circuit (use_via Via[0-1]_600:300_um)) (rule (width 300) (clearance 250)))\n'
        f'    (class power "" {" ".join(POWER)}\n'
        '      (circuit (use_via Via[0-1]_600:300_um)) (rule (width 800) (clearance 300)))\n'
        f'    (class led "" {" ".join(LED)}\n'
        '      (circuit (use_via Via[0-1]_600:300_um)) (rule (width 600) (clearance 250)))\n'
    )
    dsn = re.sub(r'\(class kicad_default "".*?\(rule.*?\)\s*\)\s*\)', classes, dsn, count=1, flags=re.S)
    dsn = dsn.replace("(clearance 200.1)", "(clearance 250)")
    path.write_text(dsn)


def parse_sexpr(text):
    tokens = re.findall(r'\(|\)|"[^"]*"|[^\s()]+', text)
    stack = [[]]
    for t in tokens:
        if t == "(":
            stack.append([])
        elif t == ")":
            done = stack.pop()
            stack[-1].append(done)
        else:
            stack[-1].append(t.strip('"'))
    return stack[0][0]


def find(node, key):
    return [c for c in node if isinstance(c, list) and c and c[0] == key]


def import_ses(board, path):
    """Add Freerouting's tracks and vias to the board. (KiCad 7's
    ImportSpecctraSES only works inside the GUI.)"""
    ses = parse_sexpr(path.read_text())
    routes = find(ses, "routes")[0]
    res = float(find(find(ses, "placement")[0], "resolution")[0][2])   # units per um
    scale = 1000.0 * res                                                  # units per mm

    # Freerouting's coordinates can land a fraction of a micron off the pads
    # and tracks already on the board, which KiCad then treats as unconnected.
    # Snap anything within 5 um onto those existing anchor points.
    anchors = [p.GetPosition() for p in board.GetPads()]
    for t in board.GetTracks():
        anchors += [t.GetStart(), t.GetEnd()] if t.GetClass() == "PCB_TRACK" else [t.GetPosition()]
    snap = pcbnew.FromMM(0.005)

    def pt(x, y):
        v = pcbnew.VECTOR2I(pcbnew.FromMM(float(x) / scale), pcbnew.FromMM(-float(y) / scale))
        for a in anchors:
            if abs(a.x - v.x) <= snap and abs(a.y - v.y) <= snap:
                return pcbnew.VECTOR2I(a.x, a.y)
        anchors.append(v)
        return v

    layers = {"F.Cu": pcbnew.F_Cu, "B.Cu": pcbnew.B_Cu}
    joins = []   # (point, netcode, layers) where new copper meets existing tracks
    vias = {}
    for ps in find(find(routes, "library_out")[0], "padstack"):
        m = re.search(r"_(\d+):(\d+)_um", ps[1])
        vias[ps[1]] = (int(m.group(1)), int(m.group(2)))
    tracks = 0
    for n in find(find(routes, "network_out")[0], "net"):
        netinfo = board.FindNet(n[1])
        for w in find(n, "wire"):
            if find(w, "type") and find(w, "type")[0][1] == "protect":
                continue   # tracks that were already on the board
            path_ = find(w, "path")[0]
            layer, width, coords = path_[1], float(path_[2]) / scale, path_[3:]
            pts = [pt(coords[i], coords[i + 1]) for i in range(0, len(coords), 2)]
            for a, b in zip(pts, pts[1:]):
                if a.x == b.x and a.y == b.y:
                    continue
                t = pcbnew.PCB_TRACK(board)
                t.SetStart(a)
                t.SetEnd(b)
                t.SetWidth(pcbnew.FromMM(width))
                t.SetLayer(layers[layer])
                t.SetNet(netinfo)
                board.Add(t)
                tracks += 1
                joins += [(a, netinfo.GetNetCode(), [layers[layer]]), (b, netinfo.GetNetCode(), [layers[layer]])]
        for v in find(n, "via"):
            if find(v, "type") and find(v, "type")[0][1] == "protect":
                continue
            dia, drill = vias[v[1]]
            via = pcbnew.PCB_VIA(board)
            via.SetPosition(pt(v[2], v[3]))
            via.SetWidth(pcbnew.FromMM(dia / 1000))
            via.SetDrill(pcbnew.FromMM(drill / 1000))
            via.SetNet(netinfo)
            board.Add(via)
            joins.append((via.GetPosition(), netinfo.GetNetCode(), [pcbnew.F_Cu, pcbnew.B_Cu]))
    # Freerouting may end a wire on the middle of another wire (a T-junction);
    # KiCad only connects tracks at their ends, so split the track there.
    splits = sum(split_tracks_at(board, *j) for j in joins)
    print(f"imported {tracks} track segments, split {splits} at T-junctions")


def split_tracks_at(board, pos, netcode, layer_ids):
    for t in list(board.GetTracks()):
        if t.GetClass() != "PCB_TRACK" or t.GetNetCode() != netcode or t.GetLayer() not in layer_ids:
            continue
        a, b = t.GetStart(), t.GetEnd()
        if (pos.x, pos.y) in ((a.x, a.y), (b.x, b.y)):
            continue
        dx, dy = b.x - a.x, b.y - a.y
        length2 = dx * dx + dy * dy
        if not length2:
            continue
        u = ((pos.x - a.x) * dx + (pos.y - a.y) * dy) / length2
        if not 0 < u < 1:
            continue
        px, py = a.x + u * dx, a.y + u * dy
        if (px - pos.x) ** 2 + (py - pos.y) ** 2 > (t.GetWidth() / 2) ** 2:
            continue
        tail = pcbnew.PCB_TRACK(board)
        tail.SetStart(pcbnew.VECTOR2I(pos.x, pos.y))
        tail.SetEnd(b)
        tail.SetWidth(t.GetWidth())
        tail.SetLayer(t.GetLayer())
        tail.SetNet(t.GetNet())
        board.Add(tail)
        t.SetEnd(pcbnew.VECTOR2I(pos.x, pos.y))
        return 1
    return 0


def add_ground_pours(board):
    gnd = board.FindNet("GND")
    outline = board.GetBoardEdgesBoundingBox()
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        z = pcbnew.ZONE(board)
        z.SetLayer(layer)
        z.SetNet(gnd)
        z.SetLocalClearance(pcbnew.FromMM(0.4))
        z.SetMinThickness(pcbnew.FromMM(0.3))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        z.SetThermalReliefGap(pcbnew.FromMM(0.4))
        z.SetThermalReliefSpokeWidth(pcbnew.FromMM(0.6))
        poly = z.Outline()
        poly.NewOutline()
        for x, y in ((outline.GetLeft(), outline.GetTop()), (outline.GetRight(), outline.GetTop()),
                     (outline.GetRight(), outline.GetBottom()), (outline.GetLeft(), outline.GetBottom())):
            poly.Append(x, y)
        board.Add(z)

    # No ground fill under the XIAO's antenna (the end opposite its USB port).
    x0, x1, y0, y1 = 100 - 9.5, 100 + 9.5, 100 - 31.5, 100 - 24.0
    keep = pcbnew.ZONE(board)
    keep.SetIsRuleArea(True)
    keep.SetDoNotAllowCopperPour(True)
    keep.SetDoNotAllowTracks(False)
    keep.SetDoNotAllowVias(False)
    keep.SetDoNotAllowPads(False)
    keep.SetDoNotAllowFootprints(False)
    keep.SetLayerSet(pcbnew.LSET(pcbnew.F_Cu).AddLayer(pcbnew.B_Cu))
    poly = keep.Outline()
    poly.NewOutline()
    for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        poly.Append(pcbnew.FromMM(x), pcbnew.FromMM(y))
    board.Add(keep)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())


def route_once(unrouted, attempt):
    board = pcbnew.LoadBoard(str(unrouted))
    dsn, ses = WORK / "redlight.dsn", WORK / "redlight.ses"
    write_dsn(board, dsn)
    subprocess.run(["xvfb-run", "-a", "java", "-jar", JAR,
                    "-de", str(dsn), "-do", str(ses), "-mp", "40"], check=True)
    import_ses(board, ses)
    add_ground_pours(board)
    board.Save(str(PCB))

    report = WORK / "drc.rpt"
    pcbnew.WriteDRCReport(pcbnew.LoadBoard(str(PCB)), str(report), pcbnew.EDA_UNITS_MILLIMETRES, True)
    text = report.read_text()
    unconnected = int(re.search(r"Found (\d+) unconnected", text).group(1))
    errors = [l for l in text.splitlines()
              if l.startswith("[") and not l.startswith(("[silk_", "[lib_footprint_issues"))]
    print(f"attempt {attempt}: {unconnected} unconnected, {len(errors)} DRC errors")
    for l in sorted(set(errors)):
        print("  ", l)
    return unconnected == 0 and not errors


def main():
    WORK.mkdir(exist_ok=True)
    # Freerouting occasionally leaves a net unfinished, so keep the unrouted
    # board and retry until DRC is clean.
    unrouted = WORK / "unrouted.kicad_pcb"
    shutil.copy(PCB, unrouted)
    for attempt in range(1, 6):
        if route_once(unrouted, attempt):
            break
    else:
        raise SystemExit("routing still has errors after 5 attempts, see build/drc.rpt")

    FAB.mkdir(exist_ok=True)
    for f in FAB.glob("*"):
        f.unlink()
    layers = "F.Cu,B.Cu,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts"
    subprocess.run(["kicad-cli", "pcb", "export", "gerbers", "--layers", layers,
                    "--subtract-soldermask", "-o", str(FAB) + "/", str(PCB)], check=True)
    subprocess.run(["kicad-cli", "pcb", "export", "drill", "--format", "excellon",
                    "--excellon-separate-th", "-o", str(FAB) + "/", str(PCB)], check=True)
    with zipfile.ZipFile(HERE / "redlight-gerbers.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(FAB.iterdir()):
            z.write(f, f.name)
    print("fab files ->", HERE / "redlight-gerbers.zip")


if __name__ == "__main__":
    main()
