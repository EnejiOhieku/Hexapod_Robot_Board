#!/usr/bin/env python3
"""
run_final_perfect_route.py
The definitive autorouting pipeline for Hexapod Robot Board Rev 2.0:
1. Pure power plane on In2.Cu (type power in DSN).
2. Complete, non-colliding pre-routes for all high-current and power plane escape pins.
3. Freerouting 15-pass routing.
4. Clean SES import and zone refill.
5. KiCad DRC check and verification of 0 DRC violations and 0 unconnected items.
"""
import os
import re
import sys
import subprocess
import pcbnew

def main():
    board_path = '/home/peacemaker/Desktop/Hexapod_Robot_Board/Hexapod_Robot_Board.kicad_pcb'
    dsn_path = '/home/peacemaker/Desktop/Hexapod_Robot_Board/final_route.dsn'
    ses_path = '/home/peacemaker/Desktop/Hexapod_Robot_Board/final_route.ses'
    clean_ses_path = '/home/peacemaker/Desktop/Hexapod_Robot_Board/final_route_clean.ses'
    drc_rpt_path = '/home/peacemaker/Desktop/Hexapod_Robot_Board/final_route_drc.rpt'

    print('1. Loading board...')
    board = pcbnew.LoadBoard(board_path)
    f_cu = board.GetLayerID('F.Cu')
    b_cu = board.GetLayerID('B.Cu')
    in1_cu = board.GetLayerID('In1.Cu')
    in2_cu = board.GetLayerID('In2.Cu')
    f_silk = board.GetLayerID('F.Silkscreen')

    # 2. Constraints and Netclasses
    print('2. Setting design constraints...')
    ds = board.GetDesignSettings()
    ds.m_MinThroughDrill = int(0.20 * 1e6)
    ds.m_TrackMinWidth = int(0.15 * 1e6)
    ds.m_HoleToHoleMin = int(0.25 * 1e6)
    ds.m_HoleClearance = int(0.25 * 1e6)

    ns = ds.m_NetSettings
    dnc = ns.GetDefaultNetclass()
    dnc.SetClearance(int(0.15 * 1e6))
    dnc.SetTrackWidth(int(0.20 * 1e6))
    dnc.SetViaDrill(int(0.30 * 1e6))
    dnc.SetViaDiameter(int(0.60 * 1e6))

    for net in board.GetNetsByName().values():
        net.SetNetClass(dnc)

    # 3. Silkscreen Labels
    print('3. Setting silkscreen labels...')
    for d in list(board.GetDrawings()):
        if d.GetLayer() == f_silk and isinstance(d, pcbnew.PCB_TEXT):
            board.RemoveNative(d)

    labels = [
        ('HEXAPOD ROBOT CONTROLLER', 55.0, 62.0, 1.4, 0.2),
        ('ESP32-S3-WROOM-1U  *  MPU-6050  *  DUAL 5A BUCK', 55.0, 64.2, 1.0, 0.15),
        ('LEG 4 [LF]', 11.5, 9.5, 1.1, 0.15),
        ('LEG 5 [LM]', 11.5, 28.5, 1.1, 0.15),
        ('LEG 6 [LR]', 11.5, 47.5, 1.1, 0.15),
        ('LEG 1 [RF]', 98.5, 9.5, 1.1, 0.15),
        ('LEG 2 [RM]', 98.5, 28.5, 1.1, 0.15),
        ('LEG 3 [RR]', 98.5, 47.5, 1.1, 0.15),
        ('BUCK L (5A)', 27.5, 32.5, 1.1, 0.15),
        ('BUCK R (5A)', 82.5, 32.5, 1.1, 0.15),
        ('MPU-6050', 55.0, 36.5, 1.1, 0.15),
        ('TYPE-C CHG', 37.0, 88.5, 1.0, 0.15),
        ('2S LiPo 7.4V', 73.0, 85.5, 1.1, 0.15),
        ('PWR SWITCH', 56.0, 77.5, 1.0, 0.15),
        ('AUX 4-6', 16.5, 72.0, 1.0, 0.15),
        ('AUX 1-3', 95.0, 72.0, 1.0, 0.15),
        ('UART', 80.5, 72.0, 1.0, 0.15),
        ('I2C', 85.5, 72.0, 1.0, 0.15),
    ]
    for text, x, y, sz, th in labels:
        txt = pcbnew.PCB_TEXT(board)
        txt.SetText(text)
        txt.SetPosition(pcbnew.VECTOR2I(int(x * 1e6), int(y * 1e6)))
        txt.SetTextSize(pcbnew.VECTOR2I(int(sz * 1e6), int(sz * 1e6)))
        txt.SetTextThickness(int(th * 1e6))
        txt.SetLayer(f_silk)
        board.Add(txt)

    for fp in board.GetFootprints():
        ref_text = fp.Reference()
        ref_text.SetTextSize(pcbnew.VECTOR2I(int(0.8 * 1e6), int(0.8 * 1e6)))
        ref_text.SetTextThickness(int(0.15 * 1e6))
        val_text = fp.Value()
        val_text.SetVisible(False)

    # 4. Copper Zones
    print('4. Setting up copper zones...')
    gnd_net = board.FindNet('GND')
    vl_net = board.FindNet('V_SERVO_L')
    vr_net = board.FindNet('V_SERVO_R')

    for z in board.Zones():
        z.SetThermalReliefGap(int(0.30 * 1e6))
        z.SetThermalReliefSpokeWidth(int(0.40 * 1e6))
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)

    has_b_cu = any(z.GetLayer() == b_cu for z in board.Zones())
    if not has_b_cu:
        z = pcbnew.ZONE(board)
        z.SetLayer(b_cu)
        z.SetNet(gnd_net)
        z.SetThermalReliefGap(int(0.30 * 1e6))
        z.SetThermalReliefSpokeWidth(int(0.40 * 1e6))
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        poly = pcbnew.SHAPE_POLY_SET()
        poly.NewOutline()
        poly.Append(int(1.0 * 1e6), int(1.0 * 1e6))
        poly.Append(int(109.0 * 1e6), int(1.0 * 1e6))
        poly.Append(int(109.0 * 1e6), int(89.0 * 1e6))
        poly.Append(int(1.0 * 1e6), int(89.0 * 1e6))
        z.SetOutline(poly)
        board.Add(z)

    # 5. Clear all tracks and add verified pre-routes
    print('5. Adding verified clean pre-routes...')
    for t in list(board.GetTracks()):
        board.RemoveNative(t)

    def add_track(net, layer, x1, y1, x2, y2, w):
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

    # 5.1 BUCK_SW_L (1.2mm)
    sw_l = board.FindNet('BUCK_SW_L')
    add_track(sw_l, f_cu, 19.85, 39.00, 29.00, 39.00, 1.2)
    add_track(sw_l, f_cu, 29.00, 39.00, 37.55, 39.00, 1.2)
    add_track(sw_l, f_cu, 31.00, 39.00, 31.00, 47.10, 1.2)

    # 5.2 BUCK_SW_R (1.2mm)
    sw_r = board.FindNet('BUCK_SW_R')
    add_track(sw_r, f_cu, 90.15, 39.00, 81.00, 39.00, 1.2)
    add_track(sw_r, f_cu, 81.00, 39.00, 72.45, 39.00, 1.2)
    add_track(sw_r, f_cu, 79.00, 39.00, 79.00, 47.10, 1.2)

    # 5.3 V_SERVO_L Power Vias + C_OUT1_L Track
    add_track(vl_net, f_cu, 47.45, 39.00, 45.00, 41.45, 1.0)
    add_via(vl_net, 45.00, 41.45, 0.4, 0.8)
    add_via(vl_net, 45.00, 44.00, 0.4, 0.8)
    add_track(vl_net, f_cu, 45.00, 41.45, 45.00, 44.00, 1.0)
    add_track(vl_net, f_cu, 45.00, 44.00, 43.00, 46.00, 1.0)
    add_track(vl_net, f_cu, 43.00, 46.00, 43.00, 51.50, 1.0)

    # Daisy-chain servo power pins (Pad 2) on F.Cu
    add_track(vl_net, f_cu, 12.54, 15.00, 12.54, 24.00, 0.8) # Leg 4
    add_track(vl_net, f_cu, 12.54, 34.00, 12.54, 43.00, 0.8) # Leg 5
    add_track(vl_net, f_cu, 12.54, 53.00, 12.54, 62.00, 0.8) # Leg 6
    # LED_L via to In2.Cu
    add_track(vl_net, f_cu, 20.50, 54.9375, 22.50, 54.9375, 0.3)
    add_via(vl_net, 22.50, 54.9375, 0.3, 0.6)

    # 5.4 V_SERVO_R Power Vias + C_OUT1_R Track + In2.Cu bridge
    add_track(vr_net, f_cu, 62.55, 39.00, 65.00, 41.45, 1.0)
    add_via(vr_net, 65.00, 41.45, 0.4, 0.8)
    add_via(vr_net, 65.00, 44.00, 0.4, 0.8)
    add_track(vr_net, f_cu, 65.00, 41.45, 65.00, 44.00, 1.0)
    add_track(vr_net, f_cu, 65.00, 44.00, 67.00, 46.00, 1.0)
    add_track(vr_net, f_cu, 67.00, 46.00, 67.00, 51.50, 1.0)

    # Daisy-chain servo power pins (Pad 2) on F.Cu
    add_track(vr_net, f_cu, 97.46, 15.00, 97.46, 24.00, 0.8) # Leg 1
    add_track(vr_net, f_cu, 97.46, 34.00, 97.46, 43.00, 0.8) # Leg 2
    add_track(vr_net, f_cu, 97.46, 53.00, 97.46, 62.00, 0.8) # Leg 3
    # LED_R via to In2.Cu
    add_track(vr_net, f_cu, 89.50, 54.9375, 87.50, 54.9375, 0.3)
    add_via(vr_net, 87.50, 54.9375, 0.3, 0.6)
    # In2.Cu plane bridge
    add_track(vr_net, in2_cu, 67.00, 51.50, 67.00, 58.00, 1.0)

    # 5.5 VBUS Reversible Bridge across J1
    vbus = board.FindNet('VBUS')
    add_track(vbus, f_cu, 34.60, 82.355, 34.60, 80.50, 0.40)
    add_via(vbus, 34.60, 80.50, 0.3, 0.6)
    add_track(vbus, f_cu, 39.40, 82.355, 39.40, 80.50, 0.40)
    add_via(vbus, 39.40, 80.50, 0.3, 0.6)
    add_track(vbus, b_cu, 34.60, 80.50, 39.40, 80.50, 0.60)

    # 5.6 +3V3 connection: Pin 2 (46.25, 4.36) to C1/C2/R1 (41.05, 9.625) via B.Cu
    v33 = board.FindNet('+3V3')
    add_track(v33, f_cu, 46.250, 4.360, 48.500, 4.360, 0.30)
    add_via(v33, 48.500, 4.360, 0.30, 0.60)
    add_track(v33, b_cu, 48.500, 4.360, 43.235, 9.625, 0.30)
    add_track(v33, b_cu, 43.235, 9.625, 41.050, 9.625, 0.30)
    add_via(v33, 41.050, 9.625, 0.30, 0.60)
    add_track(v33, f_cu, 41.050, 9.625, 42.175, 8.500, 0.30)

    # 5.7 BUCK_FB_L perimeter bypass: Pin 2 (19.85, 37.30) to R_FB1_L (20.50, 46.175) via B.Cu
    fb_l = board.FindNet('BUCK_FB_L')
    add_track(fb_l, f_cu, 19.850, 37.300, 16.500, 37.300, 0.25)
    add_via(fb_l, 16.500, 37.300, 0.30, 0.60)
    add_track(fb_l, b_cu, 16.500, 37.300, 16.500, 46.175, 0.25)
    add_via(fb_l, 16.500, 46.175, 0.30, 0.60)
    add_track(fb_l, f_cu, 16.500, 46.175, 20.500, 46.175, 0.25)

    # 5.8 6 Dedicated SMD Power Vias to In2.Cu:
    # R_FB1_L Pad 1 (20.500, 47.825) -> via at (18.500, 47.825)
    add_track(vl_net, f_cu, 20.500, 47.825, 18.500, 47.825, 0.3)
    add_via(vl_net, 18.500, 47.825, 0.3, 0.6)
    # C_OUT2_L Pad 1 (41.525, 59.000) -> via at (39.500, 59.000)
    add_track(vl_net, f_cu, 41.525, 59.000, 39.500, 59.000, 0.5)
    add_via(vl_net, 39.500, 59.000, 0.3, 0.6)
    # C_OUT3_L Pad 1 (36.225, 59.000) -> via at (34.500, 59.000)
    add_track(vl_net, f_cu, 36.225, 59.000, 34.500, 59.000, 0.5)
    add_via(vl_net, 34.500, 59.000, 0.3, 0.6)
    # C_OUT2_R Pad 1 (65.525, 59.000) -> via at (63.500, 59.000)
    add_track(vr_net, f_cu, 65.525, 59.000, 63.500, 59.000, 0.5)
    add_via(vr_net, 63.500, 59.000, 0.3, 0.6)
    # C_OUT3_R Pad 1 (72.225, 59.000) -> via at (70.200, 59.000)
    add_track(vr_net, f_cu, 72.225, 59.000, 70.200, 59.000, 0.5)
    add_via(vr_net, 70.200, 59.000, 0.3, 0.6)
    # R_FB1_R Pad 1 (89.500, 47.825) -> via at (91.500, 47.825)
    add_track(vr_net, f_cu, 89.500, 47.825, 91.500, 47.825, 0.3)
    add_via(vr_net, 91.500, 47.825, 0.3, 0.6)

    # 5.9 U5 PCA9685 Ground Tie and Via to GND Plane
    add_track(gnd_net, f_cu, 23.1375, 62.775, 23.1375, 65.375, 0.25)
    add_track(gnd_net, f_cu, 23.1375, 64.075, 24.500, 64.075, 0.25)
    add_via(gnd_net, 24.500, 64.075, 0.30, 0.60)

    # 6. Refill and Export DSN
    print('6. Refilling zones and exporting DSN...')
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    pcbnew.SaveBoard(board_path, board)
    pcbnew.ExportSpecctraDSN(board, dsn_path)

    # Verify pre-routing DRC
    pre_rpt = '/tmp/final_pre_drc.rpt'
    subprocess.run(['/home/peacemaker/.local/bin/kicad-cli', 'pcb', 'drc', '--severity-all', '--units', 'mm', '-o', pre_rpt, board_path], capture_output=True, text=True)
    with open(pre_rpt) as f:
        pre_text = f.read()
    pre_v = len(re.findall(r'\[(?!unconnected_items)[^\]]+\]:', pre_text))
    print(f'Pre-routing check: {pre_v} DRC violations.')
    if pre_v > 0:
        print('Aborting due to pre-routing DRC violations!')
        for line in pre_text.splitlines()[:30]:
            print(' ', line)
        return

    # Multi-line regex replacement to set In2.Cu as pure power layer
    print('Configuring In2.Cu as POWER layer in DSN...')
    with open(dsn_path, 'r') as f:
        dsn_content = f.read()
    dsn_content = re.sub(r'\(layer\s+In2\.Cu\s*\(type\s+signal\)', '(layer In2.Cu\n      (type power)', dsn_content)
    with open(dsn_path, 'w') as f:
        f.write(dsn_content)

    # 7. Run Freerouting
    print('7. Running Freerouting (-mp 15)...')
    cmd = [
        '/home/peacemaker/.local/bin/java',
        '-jar',
        '/home/peacemaker/.kicad-mcp/freerouting.jar',
        '-de', dsn_path,
        '-do', ses_path,
        '--gui.enabled=false',
        '-mp', '15'
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    print('Freerouting output tail:')
    for line in res.stdout.strip().splitlines()[-8:]:
        print(' ', line)

    # 8. Clean placement from SES and import
    print('8. Importing SES...')
    with open(ses_path, 'r') as f:
        ses_text = f.read()

    placement_match = re.search(r'\(placement(?=[\s)])', ses_text)
    if placement_match:
        depth = 0
        in_string = False
        start = placement_match.start()
        end = -1
        for i in range(start, len(ses_text)):
            ch = ses_text[i]
            if ch == '"':
                in_string = not in_string
            elif in_string:
                continue
            elif ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        if end > 0:
            ses_text = ses_text[:start] + ses_text[end:]

    with open(clean_ses_path, 'w') as f:
        f.write(ses_text)

    ok = pcbnew.ImportSpecctraSES(board, clean_ses_path)
    print('Import status:', ok)

    filler.Fill(board.Zones())
    pcbnew.SaveBoard(board_path, board)
    print(f'Successfully updated and saved {board_path}.')

    # 9. Run KiCad DRC
    print('9. Running final KiCad DRC check...')
    drc_cmd = [
        '/home/peacemaker/.local/bin/kicad-cli',
        'pcb', 'drc',
        '--severity-all',
        '--units', 'mm',
        '-o', drc_rpt_path,
        board_path
    ]
    subprocess.run(drc_cmd, capture_output=True, text=True)
    with open(drc_rpt_path, 'r') as f:
        drc_text = f.read()

    violations = len(re.findall(r'\[(?!unconnected_items)[^\]]+\]:', drc_text))
    unconnected = len(re.findall(r'\[unconnected_items\]:', drc_text))
    print(f'\n======================================================')
    print(f'FINAL BOARD DRC RESULTS: {violations} violations, {unconnected} unconnected items.')
    print(f'======================================================\n')

if __name__ == '__main__':
    main()
