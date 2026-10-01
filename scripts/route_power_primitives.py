#!/usr/bin/env python3
"""
route_power_primitives.py
Pre-routes high-current switching loops, 5A buck power paths, battery rails,
and ground plane fanout vias on Hexapod_Robot_Board.kicad_pcb.
"""
import sys
import pcbnew

def add_track(board, net, layer, x1_mm, y1_mm, x2_mm, y2_mm, width_mm):
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(pcbnew.VECTOR2I(int(x1_mm * 1e6), int(y1_mm * 1e6)))
    t.SetEnd(pcbnew.VECTOR2I(int(x2_mm * 1e6), int(y2_mm * 1e6)))
    t.SetWidth(int(width_mm * 1e6))
    t.SetLayer(layer)
    t.SetNet(net)
    board.Add(t)
    return t

def add_via(board, net, x_mm, y_mm, drill_mm=0.3, size_mm=0.6):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(pcbnew.VECTOR2I(int(x_mm * 1e6), int(y_mm * 1e6)))
    v.SetDrill(int(drill_mm * 1e6))
    v.SetWidth(int(size_mm * 1e6))
    v.SetNet(net)
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    board.Add(v)
    return v

def main():
    board_path = '/home/peacemaker/Desktop/Hexapod_Robot_Board/Hexapod_Robot_Board.kicad_pcb'
    print(f'Loading board from {board_path}...')
    board = pcbnew.LoadBoard(board_path)
    
    f_cu = board.GetLayerID('F.Cu')
    b_cu = board.GetLayerID('B.Cu')
    in1_cu = board.GetLayerID('In1.Cu')
    in2_cu = board.GetLayerID('In2.Cu')
    
    # 1. Update Board Constraints and Rules
    print('Updating board design settings and constraints...')
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
    
    # Update Zone Settings (Thermal relief spoke & gap)
    for z in board.Zones():
        z.SetThermalReliefGap(int(0.30 * 1e6))
        z.SetThermalReliefSpokeWidth(int(0.40 * 1e6))
        
    # 2. Silkscreen Text Cleanup
    print('Cleaning up silkscreen texts and labels...')
    f_silk = board.GetLayerID('F.Silkscreen')
    for d in list(board.GetDrawings()):
        if d.GetLayer() == f_silk and isinstance(d, pcbnew.PCB_TEXT):
            board.RemoveNative(d)
            
    # Add new clean silkscreen labels
    labels = [
        # Title Banner
        ('HEXAPOD ROBOT CONTROLLER', 55.0, 62.0, 1.4, 0.2),
        ('ESP32-S3-WROOM-1U  *  MPU-6050  *  DUAL 5A BUCK', 55.0, 64.2, 1.0, 0.15),
        
        # Leg Groupings (Left side)
        ('LEG 4 [LF]', 11.5, 9.5, 1.1, 0.15),
        ('LEG 5 [LM]', 11.5, 28.5, 1.1, 0.15),
        ('LEG 6 [LR]', 11.5, 47.5, 1.1, 0.15),
        
        # Leg Groupings (Right side)
        ('LEG 1 [RF]', 98.5, 9.5, 1.1, 0.15),
        ('LEG 2 [RM]', 98.5, 28.5, 1.1, 0.15),
        ('LEG 3 [RR]', 98.5, 47.5, 1.1, 0.15),
        
        # Peripheral Labels
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
        
    # Adjust footprint reference texts to avoid overlaps
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        ref_text = fp.Reference()
        ref_text.SetTextSize(pcbnew.VECTOR2I(int(0.8 * 1e6), int(0.8 * 1e6)))
        ref_text.SetTextThickness(int(0.15 * 1e6))
        val_text = fp.Value()
        val_text.SetVisible(False)  # Hide value to keep board clean
        
    # 3. Pre-Route High-Current Power Paths
    print('Pre-routing high-current power paths...')
    
    # Left Buck Switching Node: BUCK_SW_L (1.5mm)
    sw_l_net = board.FindNet('BUCK_SW_L')
    add_track(board, sw_l_net, f_cu, 19.85, 39.00, 29.00, 39.00, 1.5)  # Lead to Tab
    add_track(board, sw_l_net, f_cu, 29.00, 39.00, 37.55, 39.00, 1.5)  # Tab to L_SERVO_L pin 1
    add_track(board, sw_l_net, f_cu, 31.00, 39.00, 31.00, 47.10, 1.5)  # Tab to D_CATCH_L pin 2
    
    # Right Buck Switching Node: BUCK_SW_R (1.5mm)
    sw_r_net = board.FindNet('BUCK_SW_R')
    add_track(board, sw_r_net, f_cu, 90.15, 39.00, 81.00, 39.00, 1.5)  # Lead to Tab
    add_track(board, sw_r_net, f_cu, 81.00, 39.00, 72.45, 39.00, 1.5)  # Tab to L_SERVO_R pin 1
    add_track(board, sw_r_net, f_cu, 79.00, 39.00, 79.00, 47.10, 1.5)  # Tab to D_CATCH_R pin 2
    
    # Left Servo Output: V_SERVO_L (1.5mm)
    v_l_net = board.FindNet('V_SERVO_L')
    # L_SERVO_L pin 2 (47.45, 39.0) to C_OUT1_L pin 1 (43.0, 51.5)
    add_track(board, v_l_net, f_cu, 47.45, 39.00, 47.45, 47.05, 1.5)
    add_track(board, v_l_net, f_cu, 47.45, 47.05, 43.00, 51.50, 1.5)
    # C_OUT1_L (43.0, 51.5) to C_OUT2_L (41.52, 59.0) to C_OUT3_L (36.23, 59.0)
    add_track(board, v_l_net, f_cu, 43.00, 51.50, 41.52, 59.00, 1.0)
    add_track(board, v_l_net, f_cu, 41.52, 59.00, 36.23, 59.00, 1.0)
    # Tap to R_FB1_L (20.5, 47.83) and LED_L (20.5, 54.94)
    add_track(board, v_l_net, f_cu, 43.00, 51.50, 20.50, 47.83, 0.4)
    add_track(board, v_l_net, f_cu, 20.50, 47.83, 20.50, 54.94, 0.4)
    # Power stitching vias for V_SERVO_L down to In2.Cu plane
    for vx, vy in [(46.0, 41.0), (47.5, 41.0), (46.0, 43.0), (47.5, 43.0)]:
        add_via(board, v_l_net, vx, vy, drill_mm=0.4, size_mm=0.8)
        
    # Right Servo Output: V_SERVO_R (1.5mm)
    v_r_net = board.FindNet('V_SERVO_R')
    # L_SERVO_R pin 2 (62.55, 39.0) to C_OUT1_R pin 1 (67.0, 51.5)
    add_track(board, v_r_net, f_cu, 62.55, 39.00, 62.55, 47.05, 1.5)
    add_track(board, v_r_net, f_cu, 62.55, 47.05, 67.00, 51.50, 1.5)
    # C_OUT1_R (67.0, 51.5) to C_OUT2_R (65.53, 59.0) to C_OUT3_R (72.22, 59.0)
    add_track(board, v_r_net, f_cu, 67.00, 51.50, 65.53, 59.00, 1.0)
    add_track(board, v_r_net, f_cu, 65.53, 59.00, 72.22, 59.00, 1.0)
    # Tap to R_FB1_R (89.5, 47.83) and LED_R (89.5, 54.94)
    add_track(board, v_r_net, f_cu, 67.00, 51.50, 89.50, 47.83, 0.4)
    add_track(board, v_r_net, f_cu, 89.50, 47.83, 89.50, 54.94, 0.4)
    # Power stitching vias for V_SERVO_R down to In2.Cu plane
    for vx, vy in [(64.0, 41.0), (62.5, 41.0), (64.0, 43.0), (62.5, 43.0)]:
        add_via(board, v_r_net, vx, vy, drill_mm=0.4, size_mm=0.8)
        
    # Feedback dividers
    fb_l_net = board.FindNet('BUCK_FB_L')
    add_track(board, fb_l_net, f_cu, 19.85, 37.30, 20.50, 37.95, 0.25)
    add_track(board, fb_l_net, f_cu, 20.50, 37.95, 20.50, 46.17, 0.25)
    add_track(board, fb_l_net, f_cu, 20.50, 46.17, 20.50, 51.33, 0.25)
    
    fb_r_net = board.FindNet('BUCK_FB_R')
    add_track(board, fb_r_net, f_cu, 90.15, 40.70, 89.50, 41.35, 0.25)
    add_track(board, fb_r_net, f_cu, 89.50, 41.35, 89.50, 46.17, 0.25)
    add_track(board, fb_r_net, f_cu, 89.50, 46.17, 89.50, 51.33, 0.25)
    
    # Raw Battery: VBAT (1.2mm)
    vbat_net = board.FindNet('VBAT')
    # J_BAT pin 1 (73.0, 80.0) to SW_PWR pin 1 (56.0, 82.0)
    add_track(board, vbat_net, f_cu, 73.00, 80.00, 71.00, 82.00, 1.2)
    add_track(board, vbat_net, f_cu, 71.00, 82.00, 56.00, 82.00, 1.2)
    # J_BAT pin 1 to U2 pins 13/14 (37.96, 74.0) via C_BAT1/2 (51.0, 71.5)
    add_track(board, vbat_net, f_cu, 73.00, 80.00, 51.00, 71.50, 1.0)
    add_track(board, vbat_net, f_cu, 51.00, 71.50, 51.00, 75.50, 1.0)
    add_track(board, vbat_net, f_cu, 51.00, 74.00, 37.96, 74.00, 1.0)
    
    # Switched Battery: VBAT_SW (1.0mm)
    vbat_sw_net = board.FindNet('VBAT_SW')
    # SW_PWR pin 2 & 3 (58.0, 82.0) - (60.0, 82.0)
    add_track(board, vbat_sw_net, f_cu, 58.00, 82.00, 60.00, 82.00, 1.0)
    # To Left Buck U3_L pin 5 (19.85, 42.40) & C_IN1_L (20.0, 28.0), C_IN2_L (28.0, 28.0)
    add_track(board, vbat_sw_net, f_cu, 58.00, 82.00, 35.00, 82.00, 1.0)
    add_track(board, vbat_sw_net, f_cu, 35.00, 82.00, 19.85, 66.85, 1.0)
    add_track(board, vbat_sw_net, f_cu, 19.85, 66.85, 19.85, 42.40, 1.0)
    add_track(board, vbat_sw_net, f_cu, 19.85, 42.40, 19.85, 28.00, 1.0)
    add_track(board, vbat_sw_net, f_cu, 19.85, 28.00, 20.00, 28.00, 1.0)
    add_track(board, vbat_sw_net, f_cu, 20.00, 28.00, 28.02, 28.00, 1.0)
    # To Right Buck U3_R pin 5 (90.15, 35.60) & C_IN1_R (87.0, 26.0), C_IN2_R (82.0, 28.0)
    add_track(board, vbat_sw_net, f_cu, 60.00, 82.00, 75.00, 82.00, 1.0)
    add_track(board, vbat_sw_net, f_cu, 75.00, 82.00, 90.15, 66.85, 1.0)
    add_track(board, vbat_sw_net, f_cu, 90.15, 66.85, 90.15, 35.60, 1.0)
    add_track(board, vbat_sw_net, f_cu, 90.15, 35.60, 90.15, 28.00, 1.0)
    add_track(board, vbat_sw_net, f_cu, 90.15, 28.00, 81.98, 28.00, 1.0)
    add_track(board, vbat_sw_net, f_cu, 87.00, 26.00, 87.00, 28.00, 1.0)
    # To D_ISO (77.65, 12.0) and R_DIV1 (68.0, 13.175)
    add_track(board, vbat_sw_net, f_cu, 90.15, 28.00, 90.15, 24.50, 0.5)
    add_track(board, vbat_sw_net, f_cu, 90.15, 24.50, 77.65, 12.00, 0.5)
    add_track(board, vbat_sw_net, f_cu, 77.65, 12.00, 68.00, 13.18, 0.5)
    
    # USB-C VBUS (1.0mm)
    vbus_net = board.FindNet('VBUS')
    add_track(board, vbus_net, f_cu, 34.60, 82.36, 39.40, 82.36, 0.8)
    add_track(board, vbus_net, f_cu, 39.40, 82.36, 44.50, 82.36, 0.8)
    add_track(board, vbus_net, f_cu, 44.50, 82.36, 44.50, 83.50, 0.8)
    add_track(board, vbus_net, f_cu, 44.50, 83.50, 44.50, 87.00, 0.8)
    add_track(board, vbus_net, f_cu, 34.60, 82.36, 34.60, 75.00, 0.8)
    add_track(board, vbus_net, f_cu, 34.60, 75.00, 36.25, 73.35, 0.8)
    add_track(board, vbus_net, f_cu, 36.25, 73.35, 36.25, 71.04, 0.8)
    add_track(board, vbus_net, f_cu, 36.25, 71.04, 35.25, 71.04, 0.8)
    add_track(board, vbus_net, f_cu, 36.25, 71.04, 41.30, 71.04, 0.8)
    add_track(board, vbus_net, f_cu, 41.30, 71.04, 41.30, 73.00, 0.8)  # L_CHG pin 1
    
    # Charger Switch Node: CHG_SW (1.0mm)
    chg_sw_net = board.FindNet('CHG_SW')
    add_track(board, chg_sw_net, f_cu, 37.96, 72.00, 47.70, 72.00, 1.0)
    add_track(board, chg_sw_net, f_cu, 47.70, 72.00, 47.70, 73.00, 1.0)
    
    # 4. Ground Fanout Vias for SMD Components
    print('Adding dedicated ground stitching vias to In1.Cu GND plane...')
    gnd_net = board.FindNet('GND')
    
    gnd_via_coords = [
        # Catch Diodes
        (31.00, 56.00),  # D_CATCH_L GND
        (79.00, 56.00),  # D_CATCH_R GND
        
        # Buck IC GND pins
        (18.00, 35.60),  # U3_L pin 1
        (18.00, 40.70),  # U3_L pin 4
        (92.00, 42.40),  # U3_R pin 1
        (92.00, 37.30),  # U3_R pin 4
        
        # Buck Feedback GND resistors & LEDs
        (22.00, 49.68),  # R_FB2_L GND
        (22.00, 56.68),  # R_LED_L GND
        (88.00, 49.68),  # R_FB2_R GND
        (88.00, 56.68),  # R_LED_R GND
        
        # MPU-6050 Ground pads
        (51.50, 43.75),  # U7 Pin 1 GND
        (54.75, 48.50),  # U7 Pin 9 GND
        (55.75, 48.50),  # U7 Pin 11 GND
        (58.45, 43.75),  # U7 Pin 18 GND
        (51.20, 39.50),  # C_MPU1 GND
        (51.20, 50.50),  # C_MPU2 GND
        (58.80, 39.50),  # C_MPU3 GND
        (58.80, 50.50),  # C_MPU5 GND
        
        # PCA9685 Left (U5)
        (21.50, 64.08),  # U5 Pins 1-5 address bank GND
        (21.50, 71.22),  # U5 Pin 14 GND
        (30.36, 65.05),  # U5 Pins 24-25 GND
        (16.50, 64.22),  # C_PCA1 GND
        (16.50, 68.05),  # C_PCA2 GND
        
        # PCA9685 Right (U6)
        (79.50, 64.08),  # U6 Pins 2-5 address bank GND
        (79.50, 71.22),  # U6 Pin 14 GND
        (88.36, 65.05),  # U6 Pins 24-25 GND
        (93.50, 64.22),  # C_PCA3 GND
        (93.50, 68.05),  # C_PCA4 GND
        
        # South Edge Components
        (28.00, 81.50),  # R_CC1 GND
        (31.82, 84.50),  # R_CC2 GND
        (24.50, 84.50),  # R_CHG GND
        (31.00, 87.50),  # R_FULL GND
        (70.00, 82.00),  # J_BAT pin 2 GND
        (80.50, 80.50),  # J_UART pin 2 GND
        (85.50, 80.50),  # J_I2C pin 2 GND
        
        # Northeast Telemetry & LDO
        (84.00, 10.50),  # U4 GND
        (89.00, 6.20),   # C_3V3_1 GND
        (89.00, 19.80),  # C_3V3_2 GND
        (95.50, 11.00),  # R_3V3_LED GND
        (66.50, 17.50),  # R_DIV2 GND
        (66.50, 28.00),  # R_STAT GND
    ]
    
    for vx, vy in gnd_via_coords:
        add_via(board, gnd_net, vx, vy, drill_mm=0.3, size_mm=0.6)
        
    # Short connecting tracks from pads to their GND vias
    # Catch diodes
    add_track(board, gnd_net, f_cu, 31.00, 53.90, 31.00, 56.00, 0.8)
    add_track(board, gnd_net, f_cu, 79.00, 53.90, 79.00, 56.00, 0.8)
    # Buck IC pins
    add_track(board, gnd_net, f_cu, 19.85, 35.60, 18.00, 35.60, 0.5)
    add_track(board, gnd_net, f_cu, 19.85, 40.70, 18.00, 40.70, 0.5)
    add_track(board, gnd_net, f_cu, 90.15, 42.40, 92.00, 42.40, 0.5)
    add_track(board, gnd_net, f_cu, 90.15, 37.30, 92.00, 37.30, 0.5)
    # Feedback resistors & LEDs
    add_track(board, gnd_net, f_cu, 20.50, 49.68, 22.00, 49.68, 0.3)
    add_track(board, gnd_net, f_cu, 20.50, 56.68, 22.00, 56.68, 0.3)
    add_track(board, gnd_net, f_cu, 89.50, 49.68, 88.00, 49.68, 0.3)
    add_track(board, gnd_net, f_cu, 89.50, 56.68, 88.00, 56.68, 0.3)
    # MPU-6050
    add_track(board, gnd_net, f_cu, 53.05, 43.75, 51.50, 43.75, 0.25)
    add_track(board, gnd_net, f_cu, 54.75, 46.95, 54.75, 48.50, 0.25)
    add_track(board, gnd_net, f_cu, 55.75, 46.95, 55.75, 48.50, 0.25)
    add_track(board, gnd_net, f_cu, 56.95, 43.75, 58.45, 43.75, 0.25)
    add_track(board, gnd_net, f_cu, 52.50, 39.50, 51.20, 39.50, 0.25)
    add_track(board, gnd_net, f_cu, 52.50, 50.50, 51.20, 50.50, 0.25)
    add_track(board, gnd_net, f_cu, 57.50, 39.50, 58.80, 39.50, 0.25)
    add_track(board, gnd_net, f_cu, 57.50, 50.50, 58.80, 50.50, 0.25)
    # PCA9685 Left (U5)
    add_track(board, gnd_net, f_cu, 23.14, 62.77, 23.14, 65.38, 0.3) # Tie pins 1-5
    add_track(board, gnd_net, f_cu, 23.14, 64.08, 21.50, 64.08, 0.3)
    add_track(board, gnd_net, f_cu, 23.14, 71.22, 21.50, 71.22, 0.3)
    add_track(board, gnd_net, f_cu, 28.86, 64.72, 28.86, 65.38, 0.3) # Tie pins 24-25
    add_track(board, gnd_net, f_cu, 28.86, 65.05, 30.36, 65.05, 0.3)
    # PCA9685 Right (U6)
    add_track(board, gnd_net, f_cu, 81.14, 63.42, 81.14, 65.38, 0.3) # Tie pins 2-5
    add_track(board, gnd_net, f_cu, 81.14, 64.08, 79.50, 64.08, 0.3)
    add_track(board, gnd_net, f_cu, 81.14, 71.22, 79.50, 71.22, 0.3)
    add_track(board, gnd_net, f_cu, 86.86, 64.72, 86.86, 65.38, 0.3) # Tie pins 24-25
    add_track(board, gnd_net, f_cu, 86.86, 65.05, 88.36, 65.05, 0.3)
    # J_UART & J_I2C
    add_track(board, gnd_net, f_cu, 80.50, 78.54, 80.50, 80.50, 0.4)
    add_track(board, gnd_net, f_cu, 85.50, 78.54, 85.50, 80.50, 0.4)
    
    # 5. Refill Zones and Save
    print('Refilling all zones...')
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    
    print('Saving board...')
    pcbnew.SaveBoard(board_path, board)
    print('Pre-routing complete!')

if __name__ == '__main__':
    main()
