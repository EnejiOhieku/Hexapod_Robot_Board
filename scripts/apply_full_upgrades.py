#!/usr/bin/env python3
import os
import re
import sys
import pcbnew

def main():
    board_path = '/home/peacemaker/Desktop/Hexapod_Robot_Board/Hexapod_Robot_Board.kicad_pcb'
    net_path = '/home/peacemaker/Desktop/Hexapod_Robot_Board/Hexapod_Robot_Board.net'
    
    print('Loading board...')
    board = pcbnew.LoadBoard(board_path)
    
    # 1. Update Board Outline on Edge.Cuts
    print('Updating board outline to 110.0 x 90.0 mm (R=3.0 mm)...')
    edge_cuts = board.GetLayerID('Edge.Cuts')
    for d in list(board.GetDrawings()):
        if d.GetLayer() == edge_cuts:
            board.RemoveNative(d)
            
    outline = pcbnew.PCB_SHAPE(board)
    outline.SetShape(pcbnew.SHAPE_T_RECT)
    outline.SetStart(pcbnew.VECTOR2I(0, 0))
    outline.SetEnd(pcbnew.VECTOR2I(int(110 * 1e6), int(90 * 1e6)))
    outline.SetCornerRadius(int(3 * 1e6))
    outline.SetLayer(edge_cuts)
    outline.SetWidth(int(0.1 * 1e6))
    board.Add(outline)
    
    # 2. Remove obsolete footprints and rule areas
    print('Removing obsolete footprints and keepout areas...')
    obsolete = {'C_IN1', 'C_IN2', 'C_OUT1', 'C_OUT2', 'C_OUT3', 'D_CATCH', 'LED_SERVO', 'L_SERVO', 'R_FB1', 'R_FB2', 'R_SERVO_LED', 'U3'}
    for fp in list(board.GetFootprints()):
        if fp.GetReference() in obsolete:
            board.RemoveNative(fp)
            
    for z in list(board.Zones()):
        if z.GetIsRuleArea():
            board.RemoveNative(z)
            
    # 3. Replace U1 with ESP32-S3-WROOM-1U
    print('Updating U1 to ESP32-S3-WROOM-1U...')
    u1_old = board.FindFootprintByReference('U1')
    if u1_old:
        board.RemoveNative(u1_old)
    u1_new = pcbnew.FootprintLoad('/home/peacemaker/.local/share/kicad-appimage/share/kicad/footprints/RF_Module.pretty', 'ESP32-S3-WROOM-1U')
    u1_new.SetReference('U1')
    u1_new.SetValue('ESP32-S3-WROOM-1U')
    board.Add(u1_new)
    
    # 4. Position all 105 footprints (USB-C opposite ESP32)
    print('Positioning all footprints according to collision-free floorplan...')
    full_layout = {
        # Mounting holes (4 corners of 110x90)
        'H1': (5.0, 5.0, 0),
        'H2': (105.0, 5.0, 0),
        'H3': (5.0, 85.0, 0),
        'H4': (105.0, 85.0, 0),
        
        # MCU & Decoupling (North Center)
        'U1': (55.0, 11.5, 0),
        'C1': (42.0, 14.0, 0),
        'C2': (42.0, 17.5, 0),
        
        # MPU-6050 & IMU Passives (Exact Center)
        'U7': (55.0, 45.0, 0),
        'C_MPU1': (52.5, 39.5, 0),
        'C_MPU2': (52.5, 50.5, 0),
        'C_MPU3': (57.5, 39.5, 0),
        'C_MPU5': (57.5, 50.5, 0),
        'R_SDA': (51.0, 55.0, 0),
        'R_SCL': (54.0, 55.0, 0),
        'R_OE': (57.0, 55.0, 0),
        'R_BZ': (60.0, 55.0, 0),
        
        # North Controls (Reset & Boot)
        'SW1': (38.0, 5.5, 0),
        'C3': (43.0, 5.5, 0),
        'R1': (43.0, 8.5, 0),
        'SW2': (72.0, 5.5, 0),
        'R2': (67.0, 5.5, 0),
        
        # LDO & Telemetry (Northeast)
        'U4': (84.0, 13.0, 0),
        'C_3V3_1': (89.0, 7.5, 0),
        'C_3V3_2': (89.0, 18.5, 0),
        'LED_3V3': (94.0, 7.5, 0),
        'R_3V3_LED': (94.0, 11.0, 0),
        'D_ISO': (76.0, 12.0, 180),
        'C_ISO1': (74.0, 22.0, 0),
        'C_ISO2': (74.0, 28.0, 0),
        'R_DIV1': (68.0, 14.0, 90),
        'R_DIV2': (68.0, 17.5, 90),
        'C_DIV': (68.0, 21.0, 90),
        'D_STAT': (68.0, 24.5, 90),
        'R_STAT': (68.0, 28.0, 90),
        
        # Left Buck
        'U3_L': (27.5, 39.0, 0),
        'D_CATCH_L': (31.0, 50.5, 90),
        'L_SERVO_L': (42.5, 39.0, 0),
        'C_IN1_L': (20.0, 28.0, 0),
        'C_IN2_L': (29.5, 28.0, 0),
        'C_OUT1_L': (43.0, 51.5, 0),
        'C_OUT2_L': (43.0, 59.0, 0),
        'C_OUT3_L': (37.0, 59.0, 0),
        'R_FB1_L': (20.5, 47.0, 90),
        'R_FB2_L': (20.5, 50.5, 90),
        'LED_L': (20.5, 54.0, 90),
        'R_LED_L': (20.5, 57.5, 90),
        
        # Right Buck
        'U3_R': (82.5, 39.0, 180),
        'D_CATCH_R': (79.0, 50.5, 90),
        'L_SERVO_R': (67.5, 39.0, 180),
        'C_IN1_R': (87.0, 26.0, 0),
        'C_IN2_R': (80.5, 28.0, 0),
        'C_OUT1_R': (67.0, 51.5, 0),
        'C_OUT2_R': (67.0, 59.0, 0),
        'C_OUT3_R': (73.0, 59.0, 0),
        'R_FB1_R': (89.5, 47.0, 90),
        'R_FB2_R': (89.5, 50.5, 90),
        'LED_R': (89.5, 54.0, 90),
        'R_LED_R': (89.5, 57.5, 90),
        
        # Left Leg Servos (West Edge X=10)
        'J_L4_C': (10.0, 15.0, 90),
        'J_L4_F': (10.0, 19.5, 90),
        'J_L4_T': (10.0, 24.0, 90),
        'J_L5_C': (10.0, 34.0, 90),
        'J_L5_F': (10.0, 38.5, 90),
        'J_L5_T': (10.0, 43.0, 90),
        'J_L6_C': (10.0, 53.0, 90),
        'J_L6_F': (10.0, 57.5, 90),
        'J_L6_T': (10.0, 62.0, 90),
        
        # Right Leg Servos (East Edge X=100)
        'J_L1_C': (100.0, 15.0, 270),
        'J_L1_F': (100.0, 19.5, 270),
        'J_L1_T': (100.0, 24.0, 270),
        'J_L2_C': (100.0, 34.0, 270),
        'J_L2_F': (100.0, 38.5, 270),
        'J_L2_T': (100.0, 43.0, 270),
        'J_L3_C': (100.0, 53.0, 270),
        'J_L3_F': (100.0, 57.5, 270),
        'J_L3_T': (100.0, 62.0, 270),
        
        # PWM Controllers
        'U5': (26.0, 67.0, 0),
        'C_PCA1': (18.0, 65.0, 90),
        'C_PCA2': (18.0, 69.0, 90),
        'U6': (84.0, 67.0, 0),
        'C_PCA3': (92.0, 65.0, 90),
        'C_PCA4': (92.0, 69.0, 90),
        
        # South Edge: Left AUX Headers
        'J_AUX4': (11.5, 76.0, 0),
        'J_AUX5': (16.5, 76.0, 0),
        'J_AUX6': (21.5, 76.0, 0),
        
        # South Edge: USB-C (J1) opposite ESP32
        'J1': (37.0, 86.1, 0),
        'R_CC1': (29.5, 81.5, 0),
        'R_CC2': (29.5, 84.5, 0),
        'C_VBUS1': (44.5, 83.5, 90),
        'C_VBUS2': (44.5, 87.0, 90),
        'LED_CHG': (26.0, 81.5, 0),
        'R_CHG': (26.0, 84.5, 0),
        'LED_FULL': (26.0, 87.5, 0),
        'R_FULL': (29.5, 87.5, 0),
        
        # South Edge: 2S Charger (U2 & L_CHG)
        'U2': (36.0, 73.0, 0),
        'L_CHG': (44.5, 73.0, 0),
        'C_BAT1': (51.0, 71.5, 90),
        'C_BAT2': (51.0, 75.5, 90),
        
        # South Edge: Power Switch & Battery
        'SW_PWR': (56.0, 82.0, 0),
        'J_BAT': (73.0, 80.0, 0),
        
        # South Edge: Debug Headers
        'J_UART': (80.5, 76.0, 0),
        'J_I2C': (85.5, 76.0, 0),
        
        # South Edge: Right AUX Headers
        'J_AUX1': (90.5, 76.0, 0),
        'J_AUX2': (95.0, 76.0, 0),
        'J_AUX3': (99.5, 76.0, 0)
    }
    
    for ref, (x, y, rot) in full_layout.items():
        fp = board.FindFootprintByReference(ref)
        if fp:
            fp.SetPosition(pcbnew.VECTOR2I(int(x * 1e6), int(y * 1e6)))
            fp.SetOrientationDegrees(rot)
            
    # 5. Parse netlist and assign nets to pads
    print('Parsing netlist and assigning nets...')
    with open(net_path) as f:
        net_text = f.read()
        
    net_matches = re.finditer(r'\(net\s+\(code\s+\"\d+\"\)\s+\(name\s+\"([^\"]+)\"\)', net_text)
    positions = [m.start() for m in net_matches]
    positions.append(len(net_text))

    pad_to_net = {}
    net_names = []
    for i in range(len(positions) - 1):
        chunk = net_text[positions[i]:positions[i+1]]
        net_name = re.match(r'\(net\s+\(code\s+\"\d+\"\)\s+\(name\s+\"([^\"]+)\"\)', chunk).group(1)
        net_names.append(net_name)
        nodes = re.findall(r'\(node\s+\(ref\s+\"([^\"]+)\"\)\s+\(pin\s+\"([^\"]+)\"\)', chunk)
        for ref, pin in nodes:
            pad_to_net[(ref, pin)] = net_name

    for net_name in net_names:
        if not board.FindNet(net_name):
            net_item = pcbnew.NETINFO_ITEM(board, net_name)
            board.Add(net_item)

    assigned_count = 0
    for (ref, pin), net_name in pad_to_net.items():
        fp = board.FindFootprintByReference(ref)
        if fp:
            net_item = board.FindNet(net_name)
            if net_item:
                for pad in fp.Pads():
                    if pad.GetNumber() == pin:
                        pad.SetNet(net_item)
                        assigned_count += 1
                        
    # Assign GND to all thermal/exposed pads of U1, U2, U7
    gnd_net = board.FindNet('GND')
    for ref, pad_nums in [('U1', ('41', '', 'EP')), ('U2', ('25', '', 'EP')), ('U7', ('25', '', 'EP'))]:
        fp = board.FindFootprintByReference(ref)
        if fp:
            for pad in fp.Pads():
                if pad.GetNumber() in pad_nums:
                    pad.SetNet(gnd_net)
                    
    print(f'Assigned {assigned_count} pads to exact nets.')
    
    # 6. Remove old tracks and vias
    print('Clearing old tracks and vias...')
    for t in list(board.GetTracks()):
        board.RemoveNative(t)
        
    # 7. Copper Zones Setup
    print('Setting up copper zones on In1.Cu (GND) and In2.Cu (V_SERVO_L / V_SERVO_R)...')
    for z in list(board.Zones()):
        board.RemoveNative(z)
        
    # In1.Cu: Solid GND Plane
    in1_id = board.GetLayerID('In1.Cu')
    z_gnd = pcbnew.ZONE(board)
    z_gnd.SetLayer(in1_id)
    z_gnd.SetNet(gnd_net)
    poly_gnd = pcbnew.SHAPE_POLY_SET()
    poly_gnd.NewOutline()
    poly_gnd.Append(int(1.0 * 1e6), int(1.0 * 1e6))
    poly_gnd.Append(int(109.0 * 1e6), int(1.0 * 1e6))
    poly_gnd.Append(int(109.0 * 1e6), int(89.0 * 1e6))
    poly_gnd.Append(int(1.0 * 1e6), int(89.0 * 1e6))
    z_gnd.SetOutline(poly_gnd)
    board.Add(z_gnd)
    
    # In2.Cu: Split Power Planes
    in2_id = board.GetLayerID('In2.Cu')
    
    # Left Plane: V_SERVO_L
    v_servo_l_net = board.FindNet('V_SERVO_L')
    z_l = pcbnew.ZONE(board)
    z_l.SetLayer(in2_id)
    z_l.SetNet(v_servo_l_net)
    poly_l = pcbnew.SHAPE_POLY_SET()
    poly_l.NewOutline()
    poly_l.Append(int(1.0 * 1e6), int(1.0 * 1e6))
    poly_l.Append(int(54.0 * 1e6), int(1.0 * 1e6))
    poly_l.Append(int(54.0 * 1e6), int(89.0 * 1e6))
    poly_l.Append(int(1.0 * 1e6), int(89.0 * 1e6))
    z_l.SetOutline(poly_l)
    board.Add(z_l)
    
    # Right Plane: V_SERVO_R
    v_servo_r_net = board.FindNet('V_SERVO_R')
    z_r = pcbnew.ZONE(board)
    z_r.SetLayer(in2_id)
    z_r.SetNet(v_servo_r_net)
    poly_r = pcbnew.SHAPE_POLY_SET()
    poly_r.NewOutline()
    poly_r.Append(int(56.0 * 1e6), int(1.0 * 1e6))
    poly_r.Append(int(109.0 * 1e6), int(1.0 * 1e6))
    poly_r.Append(int(109.0 * 1e6), int(89.0 * 1e6))
    poly_r.Append(int(56.0 * 1e6), int(89.0 * 1e6))
    z_r.SetOutline(poly_r)
    board.Add(z_r)
    
    # Refill all zones
    print('Refilling all zones...')
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    
    # Save the updated board
    print('Saving board...')
    pcbnew.SaveBoard(board_path, board)
    print('Successfully applied full upgrades to PCB!')

if __name__ == '__main__':
    main()
