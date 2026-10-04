#!/usr/bin/env python3
"""
scripts/finalize_board.py

Integrates BZ1, SW_VIS_RST, and C_VBUS_VIS into Hexapod_Robot_Board.kicad_pcb.
Connects all nets, resolves the 1 unconnected item on U7 Pad 9,
refills copper zones, and verifies 0 DRC violations and 0 unconnected items.
"""

import os
import re
import sys
import subprocess
import pcbnew

def main():
    root_dir = '/home/peacemaker/Desktop/Hexapod_Robot_Board'
    board_path = os.path.join(root_dir, 'Hexapod_Robot_Board.kicad_pcb')
    net_path = os.path.join(root_dir, 'Hexapod_Robot_Board.net')

    print("1. Loading board with pcbnew...")
    board = pcbnew.LoadBoard(board_path)

    f_cu = board.GetLayerID('F.Cu')
    b_cu = board.GetLayerID('B.Cu')
    f_silk = board.GetLayerID('F.Silkscreen')

    # Get or create nets
    def get_or_create_net(name):
        n = board.FindNet(name)
        if not n:
            n = pcbnew.NETINFO_ITEM(board, name)
            board.Add(n)
        return n

    gnd_net = get_or_create_net('GND')
    buzzer_out_net = get_or_create_net('Net-(BZ1-+)')
    vis_rst_net = get_or_create_net('VISION_RESET')
    vbus_vis_net = get_or_create_net('VBUS_VIS')

    # Update R_BZ Pad 2 net to Net-(BZ1-+)
    r_bz = board.FindFootprintByReference('R_BZ')
    if r_bz:
        for p in r_bz.Pads():
            if p.GetNumber() == '2':
                p.SetNet(buzzer_out_net)
                print("Updated R_BZ Pad 2 net to Net-(BZ1-+)")

    # 1. Add BZ1 footprint if not present
    bz1 = board.FindFootprintByReference('BZ1')
    if not bz1:
        bz_lib = '/home/peacemaker/.local/share/kicad-appimage/share/kicad/footprints/Buzzer_Beeper.pretty'
        bz1 = pcbnew.FootprintLoad(bz_lib, 'MagneticBuzzer_Kingstate_KCG0601')
        bz1.SetReference('BZ1')
        bz1.SetValue('Buzzer_Magnetic_3V')
        bz1.Reference().SetVisible(False)
        bz1.Value().SetVisible(False)
        board.Add(bz1)
        print("Added BZ1 footprint to board")

    # Position BZ1 at (61.5, 66.0)
    bz1.SetPosition(pcbnew.VECTOR2I(int(61.5 * 1e6), int(66.0 * 1e6)))
    bz1.SetOrientationDegrees(0.0)

    # Set BZ1 pad nets: Pad 1 (+) to Net-(BZ1-+), Pad 2 (-) to GND
    for p in bz1.Pads():
        if p.GetNumber() == '1':
            p.SetNet(buzzer_out_net)
        elif p.GetNumber() == '2':
            p.SetNet(gnd_net)

    # 2. Add SW_VIS_RST footprint if not present
    sw_rst = board.FindFootprintByReference('SW_VIS_RST')
    if not sw_rst:
        sw_lib = '/home/peacemaker/.local/share/kicad-appimage/share/kicad/footprints/Button_Switch_SMD.pretty'
        sw_rst = pcbnew.FootprintLoad(sw_lib, 'SW_Push_SPST_NO_Alps_SKRK')
        sw_rst.SetReference('SW_VIS_RST')
        sw_rst.SetValue('SW_Push')
        sw_rst.Reference().SetVisible(False)
        sw_rst.Value().SetVisible(False)
        board.Add(sw_rst)
        print("Added SW_VIS_RST footprint to board")

    # Position SW_VIS_RST at (36.0, 8.5)
    sw_rst.SetPosition(pcbnew.VECTOR2I(int(36.0 * 1e6), int(8.5 * 1e6)))
    sw_rst.SetOrientationDegrees(0.0)

    # Set SW_VIS_RST pad nets: Pad 1 to GND, Pad 2 to VISION_RESET
    for p in sw_rst.Pads():
        if p.GetNumber() == '1':
            p.SetNet(gnd_net)
        elif p.GetNumber() == '2':
            p.SetNet(vis_rst_net)

    # 3. Add C_VBUS_VIS footprint if not present
    c_vis = board.FindFootprintByReference('C_VBUS_VIS')
    if not c_vis:
        c_lib = '/home/peacemaker/.local/share/kicad-appimage/share/kicad/footprints/Capacitor_SMD.pretty'
        c_vis = pcbnew.FootprintLoad(c_lib, 'C_0603_1608Metric')
        c_vis.SetReference('C_VBUS_VIS')
        c_vis.SetValue('100nF')
        c_vis.Reference().SetVisible(False)
        c_vis.Value().SetVisible(False)
        board.Add(c_vis)
        print("Added C_VBUS_VIS footprint to board")

    # Position C_VBUS_VIS at (78.0, 78.0)
    c_vis.SetPosition(pcbnew.VECTOR2I(int(78.0 * 1e6), int(78.0 * 1e6)))
    c_vis.SetOrientationDegrees(90.0)

    # Set C_VBUS_VIS pad nets: Pad 1 to GND, Pad 2 to VBUS_VIS
    for p in c_vis.Pads():
        if p.GetNumber() == '1':
            p.SetNet(gnd_net)
        elif p.GetNumber() == '2':
            p.SetNet(vbus_vis_net)

    # 4. Helper routing functions
    def add_track(net, layer, x1, y1, x2, y2, w=0.25):
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(pcbnew.VECTOR2I(int(round(x1 * 1e6)), int(round(y1 * 1e6))))
        t.SetEnd(pcbnew.VECTOR2I(int(round(x2 * 1e6)), int(round(y2 * 1e6))))
        t.SetWidth(int(round(w * 1e6)))
        t.SetLayer(layer)
        t.SetNet(net)
        board.Add(t)
        return t

    def add_via(net, x, y, drill=0.3, size=0.6):
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(pcbnew.VECTOR2I(int(round(x * 1e6)), int(round(y * 1e6))))
        v.SetDrill(int(round(drill * 1e6)))
        v.SetWidth(int(round(size * 1e6)))
        v.SetNet(net)
        v.SetViaType(pcbnew.VIATYPE_THROUGH)
        board.Add(v)
        return v

    # 5. Connect U7 Pad 9 to GND track (resolves the 1 unconnected DRC item)
    print("5. Connecting U7 Pad 9 to GND track...")
    add_track(gnd_net, f_cu, 54.75, 46.95, 55.75, 46.95, 0.20)

    # 6. Route BZ1:
    # R_BZ Pad 2 is at (61.5 + 0.825 = 62.325, 57.0)
    # BZ1 Pad 1 is at (61.5, 66.0)
    # BZ1 Pad 2 is at (61.5 + 3.2 = 64.7, 66.0)
    print("6. Routing BZ1...")
    add_track(buzzer_out_net, f_cu, 62.325, 57.0, 62.325, 61.0, 0.30)
    add_track(buzzer_out_net, f_cu, 62.325, 61.0, 61.50, 61.825, 0.30)
    add_track(buzzer_out_net, f_cu, 61.50, 61.825, 61.50, 66.0, 0.30)
    
    # BZ1 Pad 2 GND via
    add_track(gnd_net, f_cu, 64.7, 66.0, 66.0, 66.0, 0.35)
    add_via(gnd_net, 66.0, 66.0, 0.3, 0.6)

    # 7. Route SW_VIS_RST:
    # SW_VIS_RST is at (36.0, 8.5)
    # Pad 1 is at (36.0 - 2.1 = 33.9, 8.5) -> GND
    # Pad 2 is at (36.0 + 2.1 = 38.1, 8.5) -> VISION_RESET
    print("7. Routing SW_VIS_RST...")
    # Pad 1 GND via
    add_track(gnd_net, f_cu, 33.9, 8.5, 32.5, 8.5, 0.25)
    add_via(gnd_net, 32.5, 8.5, 0.3, 0.6)
    
    # Pad 2 connects to VISION_RESET net
    # R_VIS_EN is at (9.5, -0.5), U8 Pin 3 is at (17.5, 2.5)
    # Or connect Pad 2 to adjacent GND-isolated via / route
    # Let's route VISION_RESET on B.Cu to U8 Pin 3 / R_VIS_EN
    add_track(vis_rst_net, f_cu, 38.1, 8.5, 39.5, 8.5, 0.25)
    add_via(vis_rst_net, 39.5, 8.5, 0.3, 0.6)

    # Find U8 Pad 3 (EN) position or R_VIS_EN Pad 2
    r_vis_en = board.FindFootprintByReference('R_VIS_EN')
    if r_vis_en:
        for p in r_vis_en.Pads():
            if p.GetNumber() == '2': # VISION_RESET
                en_pos = p.GetPosition()
                en_x, en_y = en_pos.x / 1e6, en_pos.y / 1e6
                add_track(vis_rst_net, b_cu, 39.5, 8.5, 39.5, en_y + 2.0, 0.25)
                add_track(vis_rst_net, b_cu, 39.5, en_y + 2.0, en_x + 1.5, en_y + 2.0, 0.25)
                add_track(vis_rst_net, b_cu, en_x + 1.5, en_y + 2.0, en_x + 1.5, en_y, 0.25)
                add_via(vis_rst_net, en_x + 1.5, en_y, 0.3, 0.6)
                add_track(vis_rst_net, f_cu, en_x + 1.5, en_y, en_x, en_y, 0.25)

    # 8. Route C_VBUS_VIS:
    # C_VBUS_VIS is at (78.0, 78.0), rot=90
    # Pad 1 is at (78.0, 78.0 - 0.775 = 77.225) -> GND
    # Pad 2 is at (78.0, 78.0 + 0.775 = 78.775) -> VBUS_VIS
    print("8. Routing C_VBUS_VIS...")
    add_track(gnd_net, f_cu, 78.0, 77.225, 78.0, 76.0, 0.30)
    add_via(gnd_net, 78.0, 76.0, 0.3, 0.6)

    # Connect Pad 2 to J3 VBUS_VIS reversible bridge via at (81.60, 80.50)
    add_track(vbus_vis_net, f_cu, 78.0, 78.775, 78.0, 80.50, 0.40)
    add_track(vbus_vis_net, f_cu, 78.0, 80.50, 81.60, 80.50, 0.40)

    # 9. Relocate decorative silkscreen text away from BZ1
    print("9. Relocating silkscreen text...")
    for d in board.GetDrawings():
        if d.GetLayer() == f_silk and isinstance(d, pcbnew.PCB_TEXT):
            txt = d.GetText()
            if 'HEXAPOD ROBOT CONTROLLER' in txt:
                d.SetPosition(pcbnew.VECTOR2I(int(55.0 * 1e6), int(28.0 * 1e6)))
            elif 'DUAL ESP32-S3' in txt:
                d.SetPosition(pcbnew.VECTOR2I(int(55.0 * 1e6), int(31.0 * 1e6)))

    # Add button silkscreen labels
    lbl_rst = pcbnew.PCB_TEXT(board)
    lbl_rst.SetText("VIS_RST")
    lbl_rst.SetPosition(pcbnew.VECTOR2I(int(36.0 * 1e6), int(10.5 * 1e6)))
    lbl_rst.SetTextSize(pcbnew.VECTOR2I(int(0.8 * 1e6), int(0.8 * 1e6)))
    lbl_rst.SetTextThickness(int(0.12 * 1e6))
    lbl_rst.SetLayer(f_silk)
    board.Add(lbl_rst)

    lbl_bz = pcbnew.PCB_TEXT(board)
    lbl_bz.SetText("BUZZER")
    lbl_bz.SetPosition(pcbnew.VECTOR2I(int(63.0 * 1e6), int(71.0 * 1e6)))
    lbl_bz.SetTextSize(pcbnew.VECTOR2I(int(0.9 * 1e6), int(0.9 * 1e6)))
    lbl_bz.SetTextThickness(int(0.15 * 1e6))
    lbl_bz.SetLayer(f_silk)
    board.Add(lbl_bz)

    # 10. Refill copper zones and save
    print("10. Refilling copper zones and saving...")
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    pcbnew.SaveBoard(board_path, board)
    print(f"Board saved to {board_path}!")

    # 11. Run DRC
    print("11. Running DRC...")
    drc_rpt_path = os.path.join(root_dir, 'reports/Hexapod_Robot_Board-drc.rpt')
    cmd = [
        '/home/peacemaker/.local/bin/kicad-cli',
        'pcb', 'drc',
        '--severity-all',
        '--units', 'mm',
        '-o', drc_rpt_path,
        board_path
    ]
    subprocess.run(cmd, capture_output=True, text=True)
    with open(drc_rpt_path) as f:
        drc_text = f.read()

    v_count = len(re.findall(r'\[(?!unconnected_items)[^\]]+\]:', drc_text))
    u_count = len(re.findall(r'\[unconnected_items\]:', drc_text))
    print(f"\n=======================================================")
    print(f"DRC REPORT: {v_count} violations, {u_count} unconnected items.")
    print(f"=======================================================\n")
    if v_count > 0 or u_count > 0:
        for line in drc_text.splitlines()[:40]:
            print(" ", line)

if __name__ == '__main__':
    main()
