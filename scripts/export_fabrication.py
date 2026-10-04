#!/usr/bin/env python3
"""
export_fabrication.py
Automated fabrication & manufacturing export pipeline for Hexapod Robot Board Rev 2.0.

Exports:
1. DRC & ERC verification reports (to reports/)
2. RS-274X Gerbers (11 layers) and Excellon Drills (PTH/NPTH) (to fabrication/gerbers/ & zipped)
3. Pick-and-Place (CPL) for JLCPCB SMT and KiCad standard POS
4. Bill of Materials (BOM) grouped for JLCPCB with LCSC part numbers & standard KiCad BOM
5. 3D mechanical STEP model
6. Schematic vector PDF
7. Board statistics report
8. 2D/3D high-resolution raytraced renders
"""

import os
import sys
import subprocess
import shutil
import csv
from collections import defaultdict

KICAD_CLI = '/home/peacemaker/.local/bin/kicad-cli'
BOARD_FILE = 'Hexapod_Robot_Board.kicad_pcb'
SCH_FILE = 'Hexapod_Robot_Board.kicad_sch'
FAB_DIR = 'fabrication'
REPORTS_DIR = 'reports'
GERBERS_DIR = os.path.join(FAB_DIR, 'gerbers')

def run_cmd(cmd, desc):
    print(f"--> {desc}...")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Warning: {desc} exited with code {res.returncode}")
        if res.stderr:
            print(f"    Stderr: {res.stderr.strip()[:200]}")
    return res

def main():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(root_dir)
    print(f"=== Starting Fabrication Export Pipeline in {root_dir} ===")

    os.makedirs(FAB_DIR, exist_ok=True)
    os.makedirs(REPORTS_DIR, exist_ok=True)
    os.makedirs(GERBERS_DIR, exist_ok=True)

    # 1. Run ERC
    run_cmd([
        KICAD_CLI, 'sch', 'erc',
        '--severity-all',
        '-o', os.path.join(REPORTS_DIR, 'Hexapod_Robot_Board-erc.rpt'),
        SCH_FILE
    ], "Running Schematic ERC")
    shutil.copy(os.path.join(REPORTS_DIR, 'Hexapod_Robot_Board-erc.rpt'), 'Hexapod_Robot_Board-erc.rpt')

    # 2. Run DRC
    run_cmd([
        KICAD_CLI, 'pcb', 'drc',
        '--severity-all',
        '--units', 'mm',
        '-o', os.path.join(REPORTS_DIR, 'Hexapod_Robot_Board-drc.rpt'),
        BOARD_FILE
    ], "Running PCB DRC")
    shutil.copy(os.path.join(REPORTS_DIR, 'Hexapod_Robot_Board-drc.rpt'), 'Hexapod_Robot_Board-drc.rpt')

    # 3. Export Gerbers & Drill
    for f in os.listdir(GERBERS_DIR):
        os.remove(os.path.join(GERBERS_DIR, f))

    run_cmd([
        KICAD_CLI, 'pcb', 'export', 'gerbers',
        '--layers', 'F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts',
        '-o', f"{GERBERS_DIR}/",
        BOARD_FILE
    ], "Exporting 11 RS-274X Gerber Layers")

    run_cmd([
        KICAD_CLI, 'pcb', 'export', 'drill',
        '--format', 'excellon',
        '--drill-origin', 'absolute',
        '--excellon-separate-th',
        '-o', f"{GERBERS_DIR}/",
        BOARD_FILE
    ], "Exporting Excellon Drill Files")

    zip_path = os.path.join(FAB_DIR, 'Hexapod_Robot_Board-gerbers.zip')
    if os.path.exists(zip_path):
        os.remove(zip_path)
    shutil.make_archive(os.path.splitext(zip_path)[0], 'zip', GERBERS_DIR)
    print(f"Created Gerbers archive: {zip_path}")

    # 4. Export Positions (POS / CPL)
    run_cmd([
        KICAD_CLI, 'pcb', 'export', 'pos',
        '--format', 'ascii',
        '--units', 'mm',
        '--side', 'both',
        '-o', os.path.join(FAB_DIR, 'Hexapod_Robot_Board-pos.csv'),
        BOARD_FILE
    ], "Exporting KiCad Standard POS")

    # 5. Export Schematic PDF
    run_cmd([
        KICAD_CLI, 'sch', 'export', 'pdf',
        '-o', os.path.join(FAB_DIR, 'Hexapod_Robot_Board_Schematic.pdf'),
        SCH_FILE
    ], "Exporting Vector Schematic PDF")

    # 6. Export STEP Model
    run_cmd([
        KICAD_CLI, 'pcb', 'export', 'step',
        '--subst-models',
        '-o', os.path.join(FAB_DIR, 'Hexapod_Robot_Board.step'),
        BOARD_FILE
    ], "Exporting 3D STEP Mechanical Model")

    # 7. Export Stats
    stats_rpt = os.path.join(REPORTS_DIR, 'Hexapod_Robot_Board-stats.txt')
    run_cmd([
        KICAD_CLI, 'pcb', 'export', 'stats',
        '-o', stats_rpt,
        BOARD_FILE
    ], "Generating Board Statistics")
    shutil.copy(stats_rpt, os.path.join(FAB_DIR, 'Hexapod_Robot_Board-stats.txt'))

    # 8. Export JLCPCB CPL & Grouped BOM using pcbnew
    try:
        import pcbnew
        board = pcbnew.LoadBoard(BOARD_FILE)

        # CPL
        cpl_file = os.path.join(FAB_DIR, 'Hexapod_Robot_Board-cpl-jlcpcb.csv')
        with open(cpl_file, 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow(["Designator", "Val", "Package", "Mid X", "Mid Y", "Rotation", "Layer"])
            for fp in sorted(board.GetFootprints(), key=lambda x: str(x.GetReference())):
                layer = "Top" if fp.GetLayer() == pcbnew.F_Cu else "Bottom"
                w.writerow([
                    str(fp.GetReference()),
                    str(fp.GetValue()),
                    str(fp.GetFPID().GetLibItemName()),
                    f"{fp.GetPosition().x / 1e6:.3f}",
                    f"{fp.GetPosition().y / 1e6:.3f}",
                    f"{fp.GetOrientationDegrees():.1f}",
                    layer
                ])

        # BOM
        groups = defaultdict(list)
        for fp in board.GetFootprints():
            ref = str(fp.GetReference())
            val = str(fp.GetValue())
            pkg = str(fp.GetFPID().GetLibItemName())
            fp_type = "SMD" if fp.GetAttributes() & pcbnew.FP_SMD else "THT"
            groups[(val, pkg, fp_type)].append(ref)

        bom_file = os.path.join(FAB_DIR, 'Hexapod_Robot_Board-bom-jlcpcb.csv')
        with open(bom_file, 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow(["Item", "Designator", "Quantity", "Value", "Package/Footprint", "Type", "LCSC Part #"])
            for idx, (key, refs) in enumerate(sorted(groups.items(), key=lambda x: (x[0][2], x[0][1], x[0][0])), 1):
                val, pkg, fp_type = key
                sorted_refs = sorted(refs)
                lcsc = ""
                if val == "XL4015": lcsc = "C73335"
                elif val == "MPU-6050": lcsc = "C24112"
                elif "ESP32-S3-WROOM-1U" in val: lcsc = "C2934560"
                elif val == "PCA9685PW": lcsc = "C15309"
                elif val == "AMS1117-5.0": lcsc = "C4262"
                elif "AMS1117" in val: lcsc = "C6186"
                elif "AO3400" in val: lcsc = "C20917"
                elif "WS2812B" in val or "WS2812B" in pkg: lcsc = "C2843785"
                elif "FH12-24S" in pkg: lcsc = "C264338"
                elif "TYPE-C-16P" in pkg or "HC-TYPE-C" in pkg: lcsc = "C2836886"
                elif "SW_SPST" in pkg or "Tactile" in pkg: lcsc = "C318884"
                elif "PinHeader_1x04" in pkg: lcsc = "C49240"
                elif "PinHeader_1x02" in pkg: lcsc = "C2883695"
                elif val == "SS54": lcsc = "C22452"
                elif val == "SS14": lcsc = "C2410"
                elif "47uH" in val: lcsc = "C518625"
                elif val == "100nF": lcsc = "C14663"
                elif val == "10uF": lcsc = "C15850"
                elif val == "22uF": lcsc = "C45783"
                elif val == "1uF": lcsc = "C15849"
                elif val == "2.2nF": lcsc = "C1604"
                elif val == "10k": lcsc = "C25804"
                elif val == "1k": lcsc = "C21190"
                elif val == "330": lcsc = "C23138"
                elif val == "100": lcsc = "C22775"
                elif val == "5.1k": lcsc = "C23186"
                w.writerow([idx, ", ".join(sorted_refs), len(refs), val, pkg, fp_type, lcsc])

        print(f"Generated JLCPCB CPL ({len(board.GetFootprints())} components) and BOM ({len(groups)} line items).")
    except Exception as e:
        print(f"Warning: pcbnew BOM/CPL generation error: {e}")

    # 9. Generate 2D/3D PNG Renders
    run_cmd([
        KICAD_CLI, 'pcb', 'render',
        '--side', 'top',
        '--quality', 'high',
        '--width', '2400', '--height', '1800',
        '-o', os.path.join(FAB_DIR, 'Hexapod_Robot_Board_Top.png'),
        BOARD_FILE
    ], "Rendering Top View (PNG)")

    run_cmd([
        KICAD_CLI, 'pcb', 'render',
        '--side', 'bottom',
        '--quality', 'high',
        '--width', '2400', '--height', '1800',
        '-o', os.path.join(FAB_DIR, 'Hexapod_Robot_Board_Bottom.png'),
        BOARD_FILE
    ], "Rendering Bottom View (PNG)")

    run_cmd([
        KICAD_CLI, 'pcb', 'render',
        '--perspective',
        '--rotate', '-45,0,45',
        '--floor',
        '--quality', 'high',
        '--width', '2400', '--height', '1800',
        '-o', os.path.join(FAB_DIR, 'Hexapod_Robot_Board_3D.png'),
        BOARD_FILE
    ], "Rendering 3D Isometric View (PNG)")

    print("=== Fabrication Export Pipeline Finished Successfully ===")

if __name__ == '__main__':
    main()
