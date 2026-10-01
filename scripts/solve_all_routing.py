#!/usr/bin/env python3
"""
solve_all_routing.py
Comprehensive routing script to produce a fully routed, 0 DRC violation,
0 ERC error, 0 unconnected item Hexapod Robot Board.
"""
import os
import re
import subprocess
import pcbnew

def main():
    board_path = '/home/peacemaker/Desktop/Hexapod_Robot_Board/Hexapod_Robot_Board.kicad_pcb'
    dsn_path = '/home/peacemaker/Desktop/Hexapod_Robot_Board/Hexapod_Robot_Board.dsn'
    ses_path = '/home/peacemaker/Desktop/Hexapod_Robot_Board/Hexapod_Robot_Board.ses'
    clean_ses_path = '/home/peacemaker/Desktop/Hexapod_Robot_Board/Hexapod_Robot_Board_clean.ses'
    rpt_path = '/home/peacemaker/Desktop/Hexapod_Robot_Board/Hexapod_Robot_Board-drc.rpt'

    print('1. Loading board...')
    board = pcbnew.LoadBoard(board_path)
    f_cu = board.GetLayerID('F.Cu')
    b_cu = board.GetLayerID('B.Cu')
    in1_cu = board.GetLayerID('In1.Cu')
    in2_cu = board.GetLayerID('In2.Cu')
    
    # 2. Design Rules & Constraints
    print('2. Configuring board design constraints...')
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

    # 3. Clean Silkscreen Text & Footprint Labels
    print('3. Cleaning silkscreen...')
    f_silk = board.GetLayerID('F.Silkscreen')
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

    # 4. Copper Zones Setup
    print('4. Setting up copper zones (In1=GND, In2=V_SERVO_L/R, B.Cu=GND)...')
    for z in list(board.Zones()):
        board.RemoveNative(z)
        
    gnd_net = board.FindNet('GND')
    v_l_net = board.FindNet('V_SERVO_L')
    v_r_net = board.FindNet('V_SERVO_R')

    def create_zone(layer, net, x1, y1, x2, y2):
        z = pcbnew.ZONE(board)
        z.SetLayer(layer)
        z.SetNet(net)
        z.SetThermalReliefGap(int(0.30 * 1e6))
        z.SetThermalReliefSpokeWidth(int(0.40 * 1e6))
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        poly = pcbnew.SHAPE_POLY_SET()
        poly.NewOutline()
        poly.Append(int(x1 * 1e6), int(y1 * 1e6))
        poly.Append(int(x2 * 1e6), int(y1 * 1e6))
        poly.Append(int(x2 * 1e6), int(y2 * 1e6))
        poly.Append(int(x1 * 1e6), int(y2 * 1e6))
        z.SetOutline(poly)
        board.Add(z)
        return z

    create_zone(in1_cu, gnd_net, 1.0, 1.0, 109.0, 89.0)
    create_zone(b_cu, gnd_net, 1.0, 1.0, 109.0, 89.0)
    create_zone(in2_cu, v_l_net, 1.0, 1.0, 54.0, 89.0)
    create_zone(in2_cu, v_r_net, 56.0, 1.0, 109.0, 89.0)

    # 5. Pre-route high-current switching paths and USB-C break-out
    print('5. Pre-routing primitives...')
    for t in list(board.GetTracks()):
        board.RemoveNative(t)
        
    def add_track(net, layer, x1, y1, x2, y2, w):
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(pcbnew.VECTOR2I(int(x1*1e6), int(y1*1e6)))
        t.SetEnd(pcbnew.VECTOR2I(int(x2*1e6), int(y2*1e6)))
        t.SetWidth(int(w*1e6))
        t.SetLayer(layer)
        t.SetNet(net)
        board.Add(t)

    def add_via(net, x, y, drill=0.3, size=0.6):
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(pcbnew.VECTOR2I(int(x*1e6), int(y*1e6)))
        v.SetDrill(int(drill*1e6))
        v.SetWidth(int(size*1e6))
        v.SetNet(net)
        v.SetViaType(pcbnew.VIATYPE_THROUGH)
        board.Add(v)
        return v

    # BUCK_SW_L (1.5mm)
    net_sw_l = board.FindNet('BUCK_SW_L')
    add_track(net_sw_l, f_cu, 19.85, 39.00, 29.00, 39.00, 1.5)
    add_track(net_sw_l, f_cu, 29.00, 39.00, 37.55, 39.00, 1.5)
    add_track(net_sw_l, f_cu, 31.00, 39.00, 31.00, 47.10, 1.5)

    # BUCK_SW_R (1.5mm)
    net_sw_r = board.FindNet('BUCK_SW_R')
    add_track(net_sw_r, f_cu, 90.15, 39.00, 81.00, 39.00, 1.5)
    add_track(net_sw_r, f_cu, 81.00, 39.00, 72.45, 39.00, 1.5)
    add_track(net_sw_r, f_cu, 79.00, 39.00, 79.00, 47.10, 1.5)

    # V_SERVO_L (Inductor to C_OUT1_L, C_OUT2_L, C_OUT3_L)
    add_track(v_l_net, f_cu, 47.45, 39.00, 47.45, 47.05, 1.5)
    add_track(v_l_net, f_cu, 47.45, 47.05, 43.00, 51.50, 1.5)
    add_track(v_l_net, f_cu, 43.00, 51.50, 41.52, 53.50, 0.5)
    add_track(v_l_net, f_cu, 41.52, 53.50, 41.52, 59.00, 0.5)
    add_track(v_l_net, f_cu, 41.52, 59.00, 41.52, 60.50, 0.5)
    add_track(v_l_net, f_cu, 41.52, 60.50, 36.225, 60.50, 0.5)
    add_track(v_l_net, f_cu, 36.225, 60.50, 36.225, 59.00, 0.5)
    add_via(v_l_net, 47.45, 41.0, 0.3, 0.6)
    add_via(v_l_net, 47.45, 43.0, 0.3, 0.6)

    # V_SERVO_R (Inductor to C_OUT1_R + In2.Cu plane bridge)
    add_track(v_r_net, f_cu, 62.55, 39.00, 62.55, 47.05, 1.5)
    add_track(v_r_net, f_cu, 62.55, 47.05, 67.00, 51.50, 1.5)
    add_track(v_r_net, in2_cu, 67.00, 51.50, 67.00, 55.00, 0.8)
    add_via(v_r_net, 62.55, 41.0, 0.3, 0.6)
    add_via(v_r_net, 62.55, 43.0, 0.3, 0.6)

    # USB-C (J1) Pre-routed crossover break-out:
    # 1. D- (A7 at 37.25, B7 at 36.25) joins cleanly at (37.00, 78.50) on F.Cu
    net_dm = board.FindNet('USB_D-')
    add_track(net_dm, f_cu, 36.25, 82.355, 36.25, 80.00, 0.25)
    add_track(net_dm, f_cu, 36.25, 80.00, 37.00, 78.50, 0.25)
    add_track(net_dm, f_cu, 37.25, 82.355, 37.25, 80.00, 0.25)
    add_track(net_dm, f_cu, 37.25, 80.00, 37.00, 78.50, 0.25)

    # 2. D+ (A6 at 36.75, B6 at 37.75) joins via B.Cu underpass at (37.50, 78.50)
    net_dp = board.FindNet('USB_D+')
    add_track(net_dp, f_cu, 36.75, 82.355, 36.75, 81.00, 0.25)
    add_via(net_dp, 36.75, 81.00, 0.3, 0.6)
    add_track(net_dp, f_cu, 37.75, 82.355, 37.75, 81.00, 0.25)
    add_via(net_dp, 37.75, 81.00, 0.3, 0.6)
    add_track(net_dp, b_cu, 36.75, 81.00, 37.50, 78.50, 0.25)
    add_track(net_dp, b_cu, 37.75, 81.00, 37.50, 78.50, 0.25)
    add_via(net_dp, 37.50, 78.50, 0.3, 0.6)

    # 3. VBUS Bridge across connector
    net_vbus = board.FindNet('VBUS')
    add_track(net_vbus, f_cu, 34.60, 82.355, 34.60, 81.50, 0.4)
    add_via(net_vbus, 34.60, 81.50, 0.3, 0.6)
    add_track(net_vbus, f_cu, 39.40, 82.355, 39.40, 81.50, 0.4)
    add_via(net_vbus, 39.40, 81.50, 0.3, 0.6)
    add_track(net_vbus, b_cu, 34.60, 81.50, 39.40, 81.50, 0.5)

    # 4. CC1 and CC2 traces to pull-down resistors
    net_cc1 = board.FindNet('CC1')
    add_track(net_cc1, f_cu, 35.75, 82.355, 35.75, 81.50, 0.25)
    add_track(net_cc1, f_cu, 35.75, 81.50, 29.50, 81.50, 0.25)

    net_cc2 = board.FindNet('CC2')
    add_track(net_cc2, f_cu, 38.75, 82.355, 38.75, 84.50, 0.25)
    add_via(net_cc2, 38.75, 84.50, 0.3, 0.6)
    add_via(net_cc2, 31.00, 84.50, 0.3, 0.6)
    add_track(net_cc2, b_cu, 38.75, 84.50, 31.00, 84.50, 0.25)
    add_track(net_cc2, f_cu, 31.00, 84.50, 29.50, 84.50, 0.25)

    # 6. Refill Zones and Export DSN
    print('6. Refilling zones and exporting DSN...')
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    pcbnew.SaveBoard(board_path, board)
    pcbnew.ExportSpecctraDSN(board, dsn_path)
    print('DSN exported successfully.')

    # 7. Run Freerouting
    print('7. Running Freerouting (-mp 20)...')
    cmd = [
        '/home/peacemaker/.local/bin/java',
        '-jar',
        '/home/peacemaker/.kicad-mcp/freerouting.jar',
        '-de', dsn_path,
        '-do', ses_path,
        '--gui.enabled=false',
        '-mp', '20'
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    print('Freerouting stdout tail:')
    for line in res.stdout.strip().splitlines()[-6:]:
        print(' ', line)

    # 8. Import SES
    print('8. Cleaning SES placement and importing into PCB...')
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
    print('ImportSpecctraSES result:', ok)

    filler.Fill(board.Zones())
    pcbnew.SaveBoard(board_path, board)
    print('Saved updated board.')

    # 9. Run DRC
    print('9. Running KiCad DRC check...')
    drc_cmd = [
        '/home/peacemaker/.local/bin/kicad-cli',
        'pcb', 'drc',
        '--severity-all',
        '--units', 'mm',
        board_path
    ]
    drc_res = subprocess.run(drc_cmd, capture_output=True, text=True)
    print(drc_res.stdout)

if __name__ == '__main__':
    main()
