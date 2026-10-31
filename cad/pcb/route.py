"""Autoroute redlight.kicad_pcb with Freerouting, pour ground, run DRC and
export fabrication files.

    FREEROUTING_JAR=/path/to/freerouting-1.9.0.jar python3 cad/pcb/route.py

Outputs cad/pcb/fab/ (Gerbers + drill, zipped for JLCPCB / PCBWay / OSH Park).
"""
import os
import re
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
        '      (circuit (use_via Via[0-1]_800:400_um)) (rule (width 800) (clearance 300)))\n'
        f'    (class led "" {" ".join(LED)}\n'
        '      (circuit (use_via Via[0-1]_800:400_um)) (rule (width 600) (clearance 250)))\n'
    )
    dsn = re.sub(r'\(class kicad_default "".*?\(rule.*?\)\s*\)\s*\)', classes, dsn, count=1, flags=re.S)
    dsn = dsn.replace("(clearance 200.1)", "(clearance 250)")
    path.write_text(dsn)


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
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())


def main():
    WORK.mkdir(exist_ok=True)
    board = pcbnew.LoadBoard(str(PCB))
    dsn, ses = WORK / "redlight.dsn", WORK / "redlight.ses"
    write_dsn(board, dsn)
    subprocess.run(["java", "-Djava.awt.headless=true", "-jar", JAR,
                    "-de", str(dsn), "-do", str(ses), "-mp", "40"], check=True)
    if not pcbnew.ImportSpecctraSES(board, str(ses)):
        raise SystemExit("SES import failed")
    add_ground_pours(board)
    board.Save(str(PCB))

    report = WORK / "drc.rpt"
    subprocess.run(["kicad-cli", "pcb", "drc", "--severity-error", "--schematic-parity" if False else "--units", "mm",
                    "-o", str(report), str(PCB)], check=False)
    print(report.read_text()[-1500:])

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
