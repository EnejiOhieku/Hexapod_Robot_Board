#!/usr/bin/env python3
"""
scripts/run_clean_rev3_route.py
End-to-end placement, 3D model configuration, zone setup, pre-routing, Freerouting,
and DRC validation for Hexapod Robot Board Rev 3.0.
"""
import os
import re
import sys
import subprocess
import pcbnew

def main():
    root_dir = '/home/peacemaker/Desktop/Hexapod_Robot_Board'
    board_path = os.path.join(root_dir, 'Hexapod_Robot_Board.kicad_pcb')
    dsn_path = os.path.join(root_dir, 'vision_route.dsn')
    ses_path = os.path.join(root_dir, 'vision_route.ses')
    clean_ses_path = os.path.join(root_dir, 'vision_route_clean.ses')
    drc_rpt_path = os.path.join(root_dir, 'reports/Hexapod_Robot_Board-drc.rpt')

    os.makedirs(os.path.join(root_dir, 'reports'), exist_ok=True)

    print("1. Updating 3D model definitions and zone polygons in PCB text...")
    with open(board_path, 'r') as f:
        board_text = f.read()

    # Zone polygons
    board_text = re.sub(r'\(pts\s*\(xy 1 (?:1|-15|-15\.5)\)\s*\(xy 109 (?:1|-15|-15\.5)\)', '(pts (xy 1 -15.5) (xy 109 -15.5)', board_text)
    board_text = re.sub(r'\(pts\s*\(xy 1 (?:1|-15|-15\.5)\)\s*\(xy 5[34] (?:1|-15|-15\.5)\)', '(pts (xy 1 -15.5) (xy 54 -15.5)', board_text)
    board_text = re.sub(r'\(pts\s*\(xy 56 (?:1|-15|-15\.5)\)\s*\(xy 109 (?:1|-15|-15\.5)\)', '(pts (xy 56 -15.5) (xy 109 -15.5)', board_text)

    # Replace U8 3D model
    board_text = re.sub(
        r'(\(property "Reference" "U8".*?)\(model "\$\{KICAD10_3DMODEL_DIR\}/RF_Module\.3dshapes/ESP32-S3-WROOM-1U\.step".*?\n\t\t\)',
        r'\1(model "${KIPRJMOD}/3dmodels/ESP32-S3-WROOM-1U.step"\n\t\t\t(offset\n\t\t\t\t(xyz -9 -9.6 0)\n\t\t\t)\n\t\t\t(scale\n\t\t\t\t(xyz 1 1 1)\n\t\t\t)\n\t\t\t(rotate\n\t\t\t\t(xyz 0 0 0)\n\t\t\t)\n\t\t)',
        board_text, flags=re.DOTALL
    )

    # Replace J_CAM 3D model
    board_text = re.sub(
        r'(\(property "Reference" "J_CAM".*?)\(model "\$\{KICAD10_3DMODEL_DIR\}/Connector_FFC-FPC\.3dshapes/Hirose_FH12-24S-0\.5SH_1x24-1MP_P0\.50mm_Horizontal\.step".*?\n\t\t\)',
        r'\1(model "${KIPRJMOD}/3dmodels/Hirose_FH12-24S-0.5SH_1x24-1MP_P0.50mm_Horizontal.step"\n\t\t\t(offset\n\t\t\t\t(xyz 0 0 0)\n\t\t\t)\n\t\t\t(scale\n\t\t\t\t(xyz 1 1 1)\n\t\t\t)\n\t\t\t(rotate\n\t\t\t\t(xyz 0 0 -90)\n\t\t\t)\n\t\t)',
        board_text, flags=re.DOTALL
    )

    # Replace LED_RGB_MAIN 3D model
    board_text = re.sub(
        r'(\(property "Reference" "LED_RGB_MAIN".*?)\(model "\$\{KICAD10_3DMODEL_DIR\}/LED_SMD\.3dshapes/LED_WS2812B-2020_PLCC4_2\.0x2\.0mm\.step".*?\n\t\t\)',
        r'\1(model "${KIPRJMOD}/3dmodels/LED_WS2812B-2020.step"\n\t\t\t(offset\n\t\t\t\t(xyz 0 0 0)\n\t\t\t)\n\t\t\t(scale\n\t\t\t\t(xyz 0.5714 0.5714 0.5714)\n\t\t\t)\n\t\t\t(rotate\n\t\t\t\t(xyz 0 0 0)\n\t\t\t)\n\t\t)',
        board_text, flags=re.DOTALL
    )

    with open(board_path, 'w') as f:
        f.write(board_text)

    print("2. Loading board...")
    board = pcbnew.LoadBoard(board_path)
    f_cu = board.GetLayerID('F.Cu')
    b_cu = board.GetLayerID('B.Cu')
    in1_cu = board.GetLayerID('In1.Cu')
    in2_cu = board.GetLayerID('In2.Cu')
    f_silk = board.GetLayerID('F.Silkscreen')

    # Edge.Cuts
    print("3. Updating Edge.Cuts outline to 110 x 106.5 mm (Y: -16.5 to 90 mm)...")
    for d in board.GetDrawings():
        if d.GetLayerName() == 'Edge.Cuts':
            d.SetStart(pcbnew.VECTOR2I(int(0 * 1e6), int(-16.5 * 1e6)))
            d.SetEnd(pcbnew.VECTOR2I(int(110 * 1e6), int(90 * 1e6)))

    # Master placement dictionary
    print("4. Applying verified zero-collision placements for all 140 components...")
    sys.path.insert(0, root_dir)
    import scripts.solve_complete_placement as scp
    placements = scp.get_complete_placement()

    # Exact verified adjustments
    placements['R_VIS_EN'] = (9.5, -0.5, 0.0)
    placements['C_VIS_EN'] = (9.5, -2.5, 0.0)
    placements['C_U8_2'] = (9.5, -4.5, 0.0)
    placements['C_U8_1'] = (9.5, -7.0, 0.0)

    # Shifted J_CAM downward to Y = -7.0
    placements['J_CAM'] = (55.0, -7.0, 180.0)
    placements['R_CAM_SDA'] = (66.5, -12.0, 0.0)
    placements['R_CAM_SCL'] = (66.5, -8.5, 0.0)
    placements['C_CAM1'] = (66.5, -14.0, 0.0)
    placements['C_CAM2'] = (66.5, -6.0, 0.0)

    placements['LED_RGB_MAIN'] = (73.0, -11.0, 0.0)
    placements['R_NEO'] = (75.0, -8.0, 0.0)
    placements['C_NEO'] = (75.0, -5.5, 0.0)

    # Adjusted D_CAM_LED to maintain generous clearance
    placements['D_CAM_LED'] = (42.0, -4.0, 0.0)

    # Shifted isolation components
    placements['D_ISO'] = (50.0, -2.0, 0.0)
    placements['C_ISO2'] = (55.0, -2.0, 0.0)
    placements['C_ISO1'] = (53.0, 3.5, 0.0)
    placements['R_DIV1'] = (53.0, 9.5, 0.0)
    placements['R_DIV2'] = (53.0, 12.0, 0.0)
    placements['C_DIV'] = (53.0, 14.5, 0.0)
    placements['D_STAT'] = (61.0, 10.5, 90.0)
    placements['R_STAT'] = (61.0, 14.0, 90.0)

    placements['C_VIS_OUT'] = (48.5, 12.0, 0.0)

    placements['U4'] = (71.0, 15.0, 0.0)
    placements['C_3V3_1'] = (79.0, 14.0, 0.0)
    placements['C_3V3_2'] = (79.0, 17.0, 0.0)
    placements['LED_3V3'] = (79.0, 20.0, 0.0)
    placements['R_3V3_LED'] = (79.0, 22.5, 0.0)

    placements['C1'] = (74.0, -3.0, 0.0)
    placements['C2'] = (74.0, -0.5, 0.0)
    placements['R1'] = (74.0, 2.0, 0.0)
    placements['C3'] = (74.0, 4.5, 0.0)
    placements['SW1'] = (67.0, -1.0, 0.0)
    placements['SW2'] = (67.0, 4.0, 0.0)
    placements['R2'] = (62.5, 4.0, 0.0)

    placements['R_SDA'] = (51.0, 57.0, 0.0)
    placements['R_SCL'] = (54.5, 57.0, 0.0)
    placements['R_OE'] = (58.0, 57.0, 0.0)
    placements['R_BZ'] = (61.5, 57.0, 0.0)

    placements['U6'] = (84.0, 62.0, 0.0)
    placements['C_PCA3'] = (92.0, 61.0, 90.0)
    placements['C_PCA4'] = (92.0, 65.0, 90.0)
    placements['J_UART'] = (80.5, 70.5, 0.0)
    placements['J_I2C'] = (85.5, 70.5, 0.0)
    placements['J3'] = (84.0, 86.10, 0.0)

    # Re-oriented J_BAT along West edge (mouth facing West)
    placements['J_BAT'] = (14.0, 70.0, 90.0)
    placements['J_AUX4'] = (12.0, 82.0, 0.0)
    placements['J_AUX5'] = (16.5, 82.0, 0.0)
    placements['J_AUX6'] = (21.0, 82.0, 0.0)

    for ref, (x, y, rot) in placements.items():
        fp = board.FindFootprintByReference(ref)
        if fp:
            fp.SetPosition(pcbnew.VECTOR2I(int(x * 1e6), int(y * 1e6)))
            fp.SetOrientationDegrees(rot)
        else:
            print(f"Warning: footprint {ref} not found on board!")

    # 5. Constraints and Netclasses
    print("5. Setting design constraints and netclasses...")
    ds = board.GetDesignSettings()
    ds.m_MinThroughDrill = int(0.20 * 1e6)
    ds.m_TrackMinWidth = int(0.15 * 1e6)
    ds.m_HoleToHoleMin = int(0.25 * 1e6)
    ds.m_HoleClearance = int(0.25 * 1e6)
    ds.m_CopperEdgeClearance = int(0.75 * 1e6)  # Generous perimeter margin

    ns = ds.m_NetSettings
    dnc = ns.GetDefaultNetclass()
    dnc.SetClearance(int(0.15 * 1e6))
    dnc.SetTrackWidth(int(0.20 * 1e6))
    dnc.SetViaDrill(int(0.30 * 1e6))
    dnc.SetViaDiameter(int(0.60 * 1e6))

    for net in board.GetNetsByName().values():
        net.SetNetClass(dnc)

    # 6. Silkscreen Labels
    print("6. Adding silkscreen labels...")
    for d in list(board.GetDrawings()):
        if d.GetLayer() == f_silk and isinstance(d, pcbnew.PCB_TEXT):
            board.RemoveNative(d)

    labels = [
        ('HEXAPOD ROBOT CONTROLLER REV 3.0', 55.0, 62.0, 1.4, 0.2),
        ('DUAL ESP32-S3  *  VISION COPROCESSOR  *  3x TYPE-C', 55.0, 64.5, 1.0, 0.15),
        ('CAMERA DVP', 55.0, -14.5, 1.1, 0.15),
        ('TOF DEPTH', 5.0, -14.5, 1.0, 0.15),
        ('CAM LED', 42.0, -14.0, 1.0, 0.15),
        ('RGB STAT', 73.0, -14.0, 1.0, 0.15),
        ('ESP32-S3 VIS', 22.0, -9.0, 1.1, 0.15),
        ('ESP32-S3 MAIN', 88.0, -9.0, 1.1, 0.15),
        ('LEG 4 [LF]', 11.5, 9.5, 1.1, 0.15),
        ('LEG 5 [LM]', 11.5, 28.5, 1.1, 0.15),
        ('LEG 6 [LR]', 11.5, 47.5, 1.1, 0.15),
        ('LEG 1 [RF]', 98.5, 9.5, 1.1, 0.15),
        ('LEG 2 [RM]', 98.5, 28.5, 1.1, 0.15),
        ('LEG 3 [RR]', 98.5, 47.5, 1.1, 0.15),
        ('BUCK L (5A)', 27.5, 32.5, 1.1, 0.15),
        ('BUCK R (5A)', 82.5, 32.5, 1.1, 0.15),
        ('MPU-6050', 55.0, 48.0, 1.0, 0.15),
        ('USB CHG', 37.0, 89.0, 1.0, 0.15),
        ('USB VISION', 84.0, 89.0, 1.0, 0.15),
        ('USB MAIN', 95.5, 89.0, 1.0, 0.15),
        ('5V TOF REG', 55.0, 17.5, 0.9, 0.15),
        ('3.3V VIS', 42.0, 8.5, 0.9, 0.15),
        ('3.3V MAIN', 71.0, 11.5, 0.9, 0.15),
        ('2S LiPo 7.4V', 14.0, 65.0, 1.0, 0.15),
        ('PWR SW', 54.0, 78.5, 1.0, 0.15),
        ('EXT SW', 60.5, 74.0, 0.9, 0.15),
        ('AUX 4-6', 16.5, 79.5, 0.9, 0.15),
        ('AUX 1-3', 95.0, 69.0, 1.0, 0.15),
        ('UART', 80.5, 68.0, 0.9, 0.15),
        ('I2C', 85.5, 68.0, 0.9, 0.15),
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
        fp.Reference().SetVisible(False)
        fp.Value().SetVisible(False)

    # 7. Copper Zones Properties
    print("7. Setting copper zone thermal reliefs and island removal...")
    for z in board.Zones():
        z.SetThermalReliefGap(int(0.30 * 1e6))
        z.SetThermalReliefSpokeWidth(int(0.40 * 1e6))
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)

    # 8. Clear tracks and add verified pre-routes
    print("8. Adding verified clean pre-routes...")
    for t in list(board.GetTracks()):
        board.RemoveNative(t)

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

    vl_net = board.FindNet('V_SERVO_L')
    vr_net = board.FindNet('V_SERVO_R')
    gnd_net = board.FindNet('GND')

    # BUCK_SW_L (1.2mm)
    sw_l = board.FindNet('BUCK_SW_L')
    add_track(sw_l, f_cu, 19.85, 39.00, 29.00, 39.00, 1.2)
    add_track(sw_l, f_cu, 29.00, 39.00, 37.55, 39.00, 1.2)
    add_track(sw_l, f_cu, 31.00, 39.00, 31.00, 47.10, 1.2)

    # BUCK_SW_R (1.2mm)
    sw_r = board.FindNet('BUCK_SW_R')
    add_track(sw_r, f_cu, 90.15, 39.00, 81.00, 39.00, 1.2)
    add_track(sw_r, f_cu, 81.00, 39.00, 72.45, 39.00, 1.2)
    add_track(sw_r, f_cu, 79.00, 39.00, 79.00, 47.10, 1.2)

    # V_SERVO_L Power Vias + C_OUT1_L Track
    add_track(vl_net, f_cu, 47.45, 39.00, 45.00, 41.45, 1.0)
    add_via(vl_net, 45.00, 41.45, 0.4, 0.8)
    add_via(vl_net, 45.00, 44.00, 0.4, 0.8)
    add_track(vl_net, f_cu, 45.00, 41.45, 45.00, 44.00, 1.0)
    add_track(vl_net, f_cu, 45.00, 44.00, 43.00, 46.00, 1.0)
    add_track(vl_net, f_cu, 43.00, 46.00, 43.00, 51.50, 1.0)

    add_track(vl_net, f_cu, 12.54, 15.00, 12.54, 24.00, 0.8)
    add_track(vl_net, f_cu, 12.54, 34.00, 12.54, 43.00, 0.8)
    add_track(vl_net, f_cu, 12.54, 53.00, 12.54, 62.00, 0.8)
    add_track(vl_net, f_cu, 20.50, 54.9375, 22.50, 54.9375, 0.3)
    add_via(vl_net, 22.50, 54.9375, 0.3, 0.6)

    # V_SERVO_R Power Vias + C_OUT1_R Track
    add_track(vr_net, f_cu, 62.55, 39.00, 65.00, 41.45, 1.0)
    add_via(vr_net, 65.00, 41.45, 0.4, 0.8)
    add_via(vr_net, 65.00, 44.00, 0.4, 0.8)
    add_track(vr_net, f_cu, 65.00, 41.45, 65.00, 44.00, 1.0)
    add_track(vr_net, f_cu, 65.00, 44.00, 67.00, 46.00, 1.0)
    add_track(vr_net, f_cu, 67.00, 46.00, 67.00, 51.50, 1.0)

    add_track(vr_net, f_cu, 97.46, 15.00, 97.46, 24.00, 0.8)
    add_track(vr_net, f_cu, 97.46, 34.00, 97.46, 43.00, 0.8)
    add_track(vr_net, f_cu, 97.46, 53.00, 97.46, 62.00, 0.8)
    add_track(vr_net, f_cu, 89.50, 54.9375, 87.50, 54.9375, 0.3)
    add_via(vr_net, 87.50, 54.9375, 0.3, 0.6)
    add_track(vr_net, in2_cu, 67.00, 51.50, 67.00, 58.00, 1.0)

    # VBUS Reversible Bridges for J1
    vbus = board.FindNet('VBUS')
    add_track(vbus, f_cu, 34.60, 82.355, 34.60, 80.50, 0.40)
    add_via(vbus, 34.60, 80.50, 0.3, 0.6)
    add_track(vbus, f_cu, 39.40, 82.355, 39.40, 80.50, 0.40)
    add_via(vbus, 39.40, 80.50, 0.3, 0.6)
    add_track(vbus, b_cu, 34.60, 80.50, 39.40, 80.50, 0.60)

    # BUCK_FB_L perimeter bypass
    fb_l = board.FindNet('BUCK_FB_L')
    add_track(fb_l, f_cu, 19.850, 37.300, 16.500, 37.300, 0.25)
    add_via(fb_l, 16.500, 37.300, 0.30, 0.60)
    add_track(fb_l, b_cu, 16.500, 37.300, 16.500, 46.175, 0.25)
    add_via(fb_l, 16.500, 46.175, 0.30, 0.60)
    add_track(fb_l, f_cu, 16.500, 46.175, 20.500, 46.175, 0.25)

    # Power vias to In2.Cu
    add_track(vl_net, f_cu, 20.500, 47.825, 18.500, 47.825, 0.3)
    add_via(vl_net, 18.500, 47.825, 0.3, 0.6)
    add_track(vl_net, f_cu, 41.525, 59.000, 39.500, 59.000, 0.5)
    add_via(vl_net, 39.500, 59.000, 0.3, 0.6)
    add_track(vl_net, f_cu, 36.225, 59.000, 34.500, 59.000, 0.5)
    add_via(vl_net, 34.500, 59.000, 0.3, 0.6)
    add_track(vr_net, f_cu, 65.525, 59.000, 63.500, 59.000, 0.5)
    add_via(vr_net, 63.500, 59.000, 0.3, 0.6)
    add_track(vr_net, f_cu, 72.225, 59.000, 70.200, 59.000, 0.5)
    add_via(vr_net, 70.200, 59.000, 0.3, 0.6)
    add_track(vr_net, f_cu, 89.500, 47.825, 91.500, 47.825, 0.3)
    add_via(vr_net, 91.500, 47.825, 0.3, 0.6)

    # PCA9685 Left (U5) Ground Ties
    add_track(gnd_net, f_cu, 23.1375, 62.775, 23.1375, 65.375, 0.25)
    add_track(gnd_net, f_cu, 23.1375, 64.075, 24.500, 64.075, 0.25)
    add_via(gnd_net, 24.500, 64.075, 0.30, 0.60)

    # PCA9685 Right (U6) Ground Ties (Pads 24 & 25)
    add_track(gnd_net, f_cu, 86.8625, 59.725, 86.8625, 60.375, 0.25)
    add_track(gnd_net, f_cu, 86.8625, 60.050, 85.500, 60.050, 0.25)
    add_via(gnd_net, 85.500, 60.050, 0.30, 0.60)

    # J_CAM_LED & D_CAM_LED complete circuit
    add_track(vl_net, f_cu, 44.00, -11.00, 41.50, -11.00, 0.40)
    add_via(vl_net, 41.50, -11.00, 0.30, 0.60)
    add_track(vl_net, f_cu, 40.35, -4.00, 38.50, -4.00, 0.40)
    add_via(vl_net, 38.50, -4.00, 0.30, 0.60)
    drain_net = board.FindNet('CAM_LED_DRAIN')
    add_track(drain_net, f_cu, 43.65, -4.00, 44.00, -5.00, 0.40)
    add_track(drain_net, f_cu, 44.00, -5.00, 44.00, -8.46, 0.40)

    # J3 VBUS_VIS Reversible Bridges
    vbus_vis = board.FindNet('VBUS_VIS')
    add_track(vbus_vis, f_cu, 81.60, 82.355, 81.60, 80.50, 0.40)
    add_via(vbus_vis, 81.60, 80.50, 0.30, 0.60)
    add_track(vbus_vis, f_cu, 86.40, 82.355, 86.40, 80.50, 0.40)
    add_via(vbus_vis, 86.40, 80.50, 0.30, 0.60)
    add_track(vbus_vis, b_cu, 81.60, 80.50, 86.40, 80.50, 0.60)

    # U7 Pin 8 (+3V3) B.Cu bridge to Pin 13
    v33_net = board.FindNet('+3V3')
    add_track(v33_net, f_cu, 54.25, 46.95, 54.25, 48.20, 0.20)
    add_via(v33_net, 54.25, 48.20, 0.30, 0.60)
    add_track(v33_net, b_cu, 54.25, 48.20, 57.50, 48.20, 0.25)
    add_via(v33_net, 57.50, 48.20, 0.30, 0.60)
    add_track(v33_net, f_cu, 57.50, 48.20, 56.95, 46.25, 0.20)

    # U7 Pin 11 (GND) direct via connection
    add_track(gnd_net, f_cu, 55.75, 46.95, 55.75, 49.30, 0.20)
    add_via(gnd_net, 55.75, 49.30, 0.30, 0.60)

    # D_ISO / C_ISO2 / C_ISO1 LDO_IN Power Filter Pre-routes
    ldo_in = board.FindNet('LDO_IN')
    add_track(ldo_in, f_cu, 51.65, -2.00, 54.05, -2.00, 0.50)
    add_track(ldo_in, f_cu, 53.00, -2.00, 53.00, 3.50, 0.50)
    # C_ISO2 GND via
    add_track(gnd_net, f_cu, 55.95, -2.00, 57.50, -2.00, 0.35)
    add_via(gnd_net, 57.50, -2.00, 0.30, 0.60)

    # R_PD_CAM_LED Pad 2 GND via
    add_track(gnd_net, f_cu, 36.825, -4.500, 36.825, -3.000, 0.25)
    add_via(gnd_net, 36.825, -3.000, 0.30, 0.60)

    # J_BAT Pad 2 GND via
    add_track(gnd_net, f_cu, 14.00, 75.00, 14.00, 77.00, 0.50)
    add_via(gnd_net, 14.00, 77.00, 0.30, 0.60)

    # 9. Refill zones and save
    print("9. Refilling copper zones and saving board...")
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    pcbnew.SaveBoard(board_path, board)

    # Pre-routing DRC check
    print("10. Checking pre-routing DRC...")
    pre_rpt = '/tmp/rev3_pre_drc.rpt'
    subprocess.run(['/home/peacemaker/.local/bin/kicad-cli', 'pcb', 'drc', '--severity-all', '--units', 'mm', '-o', pre_rpt, board_path], capture_output=True, text=True)
    with open(pre_rpt) as f:
        pre_text = f.read()
    pre_v = len(re.findall(r'\[(?!unconnected_items)[^\]]+\]:', pre_text))
    print(f"Pre-routing check: {pre_v} DRC violations.")
    if pre_v > 0:
        print("Pre-routing check failed with DRC violations! Details:")
        for line in pre_text.splitlines()[:30]:
            print(" ", line)
        return

    # Export DSN
    print("11. Exporting Specctra DSN...")
    pcbnew.ExportSpecctraDSN(board, dsn_path)

    # Configure In2.Cu as POWER layer in DSN
    with open(dsn_path, 'r') as f:
        dsn_content = f.read()
    dsn_content = re.sub(r'\(layer\s+In2\.Cu\s*\(type\s+signal\)', '(layer In2.Cu\n      (type power)', dsn_content)
    with open(dsn_path, 'w') as f:
        f.write(dsn_content)

    # Run Freerouting (-mp 15)
    print("12. Running Freerouting (-mp 15)...")
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
    print("Freerouting output tail:")
    for line in res.stdout.strip().splitlines()[-10:]:
        print(" ", line)

    # Clean placement from SES and import
    print("13. Importing SES...")
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
    print("Import status:", ok)

    filler.Fill(board.Zones())
    pcbnew.SaveBoard(board_path, board)
    print(f"Successfully updated and saved {board_path}.")

    # Run KiCad DRC
    print("14. Running final KiCad DRC check...")
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
    print(f"\n======================================================")
    print(f"FINAL BOARD DRC RESULTS: {violations} violations, {unconnected} unconnected items.")
    print(f"======================================================\n")

if __name__ == '__main__':
    main()
