#!/usr/bin/env python3
"""
run_pipeline_test.py
Full automated routing and DRC pipeline test.
"""
import os
import re
import subprocess
import pcbnew

def main():
    board_path = '/home/peacemaker/Desktop/Hexapod_Robot_Board/Hexapod_Robot_Board.kicad_pcb'
    test_board_path = '/home/peacemaker/Desktop/Hexapod_Robot_Board/test_pipeline.kicad_pcb'
    dsn_path = '/home/peacemaker/Desktop/Hexapod_Robot_Board/test_pipeline.dsn'
    ses_path = '/home/peacemaker/Desktop/Hexapod_Robot_Board/test_pipeline.ses'
    clean_ses_path = '/home/peacemaker/Desktop/Hexapod_Robot_Board/test_pipeline_clean.ses'
    rpt_path = '/home/peacemaker/Desktop/Hexapod_Robot_Board/test_pipeline-drc.rpt'

    print('1. Loading base board...')
    board = pcbnew.LoadBoard(board_path)
    f_cu = board.GetLayerID('F.Cu')
    
    # 2. Board setup & constraints
    print('2. Setting constraints and netclasses...')
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
    
    if not ns.HasNetclass('Power'):
        pnc = pcbnew.NETCLASS('Power')
        pnc.SetClearance(int(0.15 * 1e6))
        pnc.SetTrackWidth(int(0.80 * 1e6))
        pnc.SetViaDrill(int(0.40 * 1e6))
        pnc.SetViaDiameter(int(0.80 * 1e6))
        ns.SetNetclass(pnc)
    else:
        pnc = ns.GetNetClassByName('Power')
        
    for name in ['V_SERVO_L', 'V_SERVO_R', 'VBAT', 'VBAT_SW', 'VBUS', 'BUCK_SW_L', 'BUCK_SW_R', 'CHG_SW']:
        net = board.FindNet(name)
        if net:
            net.SetNetClass(pnc)

    # Zone settings
    for z in board.Zones():
        z.SetThermalReliefGap(int(0.30 * 1e6))
        z.SetThermalReliefSpokeWidth(int(0.40 * 1e6))

    # 3. Clean Silkscreen Text
    print('3. Cleaning silkscreen labels...')
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
        ('TYPE-C CHG', 37.0, 89.8, 1.0, 0.15),
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

    # 4. Pre-route high-current switching nodes & inductor outputs
    print('4. Pre-routing high-current primitives...')
    def add_track(net, x1, y1, x2, y2, w):
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(pcbnew.VECTOR2I(int(x1*1e6), int(y1*1e6)))
        t.SetEnd(pcbnew.VECTOR2I(int(x2*1e6), int(y2*1e6)))
        t.SetWidth(int(w*1e6))
        t.SetLayer(f_cu)
        t.SetNet(net)
        board.Add(t)

    def add_via(net, x, y, drill=0.4, size=0.8):
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(pcbnew.VECTOR2I(int(x*1e6), int(y*1e6)))
        v.SetDrill(int(drill*1e6))
        v.SetWidth(int(size*1e6))
        v.SetNet(net)
        v.SetViaType(pcbnew.VIATYPE_THROUGH)
        board.Add(v)

    # BUCK_SW_L
    net_sw_l = board.FindNet('BUCK_SW_L')
    add_track(net_sw_l, 19.85, 39.00, 29.00, 39.00, 1.5)
    add_track(net_sw_l, 29.00, 39.00, 37.55, 39.00, 1.5)
    add_track(net_sw_l, 31.00, 39.00, 31.00, 47.10, 1.5)

    # BUCK_SW_R
    net_sw_r = board.FindNet('BUCK_SW_R')
    add_track(net_sw_r, 90.15, 39.00, 81.00, 39.00, 1.5)
    add_track(net_sw_r, 81.00, 39.00, 72.45, 39.00, 1.5)
    add_track(net_sw_r, 79.00, 39.00, 79.00, 47.10, 1.5)

    # V_SERVO_L (Inductor to C_OUT1_L + 4 vias)
    net_vl = board.FindNet('V_SERVO_L')
    add_track(net_vl, 47.45, 39.00, 47.45, 47.05, 1.5)
    add_track(net_vl, 47.45, 47.05, 43.00, 51.50, 1.5)
    for vx, vy in [(47.45, 41.0), (48.80, 41.0), (47.45, 42.5), (48.80, 42.5)]:
        add_via(net_vl, vx, vy)

    # V_SERVO_R (Inductor to C_OUT1_R + 4 vias)
    net_vr = board.FindNet('V_SERVO_R')
    add_track(net_vr, 62.55, 39.00, 62.55, 47.05, 1.5)
    add_track(net_vr, 62.55, 47.05, 67.00, 51.50, 1.5)
    for vx, vy in [(62.55, 41.0), (61.20, 41.0), (62.55, 42.5), (61.20, 42.5)]:
        add_via(net_vr, vx, vy)

    # Refill zones and save
    print('5. Refilling zones and exporting DSN...')
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    pcbnew.SaveBoard(test_board_path, board)
    pcbnew.ExportSpecctraDSN(board, dsn_path)
    print('DSN exported successfully.')

    # 6. Run Freerouting
    print('6. Running Freerouting (-mp 15)...')
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
    print('Freerouting stdout tail:')
    for line in res.stdout.strip().splitlines()[-6:]:
        print(' ', line)

    # 7. Import SES
    print('7. Cleaning SES placement and importing into PCB...')
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
    pcbnew.SaveBoard(test_board_path, board)
    print('Saved updated board.')

    # 8. Run DRC
    print('8. Running KiCad DRC check...')
    drc_cmd = [
        '/home/peacemaker/.local/bin/kicad-cli',
        'pcb', 'drc',
        '--severity-all',
        '--units', 'mm',
        test_board_path
    ]
    drc_res = subprocess.run(drc_cmd, capture_output=True, text=True)
    print(drc_res.stdout)

if __name__ == '__main__':
    main()
