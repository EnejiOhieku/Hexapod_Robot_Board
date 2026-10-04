#!/usr/bin/env python3
"""
solve_complete_placement.py
Validates and optimizes the complete 140-component collision-free placement
for Hexapod Robot Board Rev 3.0.
"""
import pcbnew
import math

def get_complete_placement():
    return {
        # 1. Edge Mounting Holes
        'H1': (5.0, 5.0, 0.0),
        'H2': (105.0, 5.0, 0.0),
        'H3': (5.0, 85.0, 0.0),
        'H4': (105.0, 85.0, 0.0),

        # 2. Servos (Left & Right)
        'J_L4_C': (10.0, 15.0, 90.0),
        'J_L4_F': (10.0, 19.5, 90.0),
        'J_L4_T': (10.0, 24.0, 90.0),
        'J_L5_C': (10.0, 34.0, 90.0),
        'J_L5_F': (10.0, 38.5, 90.0),
        'J_L5_T': (10.0, 43.0, 90.0),
        'J_L6_C': (10.0, 53.0, 90.0),
        'J_L6_F': (10.0, 57.5, 90.0),
        'J_L6_T': (10.0, 62.0, 90.0),

        'J_L1_C': (100.0, 15.0, -90.0),
        'J_L1_F': (100.0, 19.5, -90.0),
        'J_L1_T': (100.0, 24.0, -90.0),
        'J_L2_C': (100.0, 34.0, -90.0),
        'J_L2_F': (100.0, 38.5, -90.0),
        'J_L2_T': (100.0, 43.0, -90.0),
        'J_L3_C': (100.0, 53.0, -90.0),
        'J_L3_F': (100.0, 57.5, -90.0),
        'J_L3_T': (100.0, 62.0, -90.0),

        # 3. Dual 5A Buck Converters
        'U3_L': (27.5, 39.0, 0.0),
        'L_SERVO_L': (42.5, 39.0, 0.0),
        'D_CATCH_L': (31.0, 50.5, 90.0),
        'C_IN1_L': (23.0, 26.0, 0.0),
        'C_IN2_L': (29.5, 28.0, 0.0),
        'C_OUT1_L': (43.0, 51.5, 0.0),
        'C_OUT2_L': (43.0, 59.0, 0.0),
        'C_OUT3_L': (37.0, 59.0, 0.0),
        'R_FB1_L': (20.5, 47.0, 90.0),
        'R_FB2_L': (20.5, 50.5, 90.0),
        'LED_L': (20.5, 54.0, 90.0),
        'R_LED_L': (20.5, 57.5, 90.0),

        'U3_R': (82.5, 39.0, 180.0),
        'L_SERVO_R': (67.5, 39.0, 180.0),
        'D_CATCH_R': (79.0, 50.5, 90.0),
        'C_IN1_R': (87.0, 26.0, 0.0),
        'C_IN2_R': (80.5, 28.0, 0.0),
        'C_OUT1_R': (67.0, 51.5, 0.0),
        'C_OUT2_R': (67.0, 59.0, 0.0),
        'C_OUT3_R': (73.0, 59.0, 0.0),
        'R_FB1_R': (89.5, 47.0, 90.0),
        'R_FB2_R': (89.5, 50.5, 90.0),
        'LED_R': (89.5, 54.0, 90.0),
        'R_LED_R': (89.5, 57.5, 90.0),

        # 4. PCA9685 Left (U5, 0x40) & Right (U6, 0x41)
        'U5': (26.0, 67.0, 0.0),
        'C_PCA1': (18.0, 65.0, 90.0),
        'C_PCA2': (18.0, 69.0, 90.0),
        'J_AUX4': (12.0, 82.0, 0.0),
        'J_AUX5': (16.5, 82.0, 0.0),
        'J_AUX6': (21.0, 82.0, 0.0),

        'U6': (84.0, 65.0, 0.0),
        'C_PCA3': (92.0, 63.0, 90.0),
        'C_PCA4': (92.0, 67.0, 90.0),
        'J_AUX1': (90.5, 73.0, 0.0),
        'J_AUX2': (95.0, 73.0, 0.0),
        'J_AUX3': (99.5, 73.0, 0.0),

        # 5. IMU & Center Sensors
        'U7': (55.0, 45.0, 0.0),
        'C_MPU1': (52.5, 39.5, 0.0),
        'C_MPU2': (52.5, 50.5, 0.0),
        'C_MPU3': (57.5, 39.5, 0.0),
        'C_MPU5': (57.5, 50.5, 0.0),
        'R_SDA': (49.0, 55.0, 0.0),
        'R_SCL': (53.0, 55.0, 0.0),
        'R_OE': (57.0, 55.0, 0.0),
        'R_BZ': (61.0, 55.0, 0.0),

        # 6. Battery Charger (TP5100)
        'J1': (37.0, 86.10, 0.0),
        'U2': (36.0, 73.0, 0.0),
        'L_CHG': (44.5, 73.0, 0.0),
        'C_VBUS1': (44.5, 83.5, 90.0),
        'C_VBUS2': (44.5, 87.0, 90.0),
        'R_CC1': (29.5, 81.5, 0.0),
        'R_CC2': (29.5, 84.5, 0.0),
        'LED_CHG': (26.0, 81.5, 0.0),
        'R_CHG': (26.0, 84.5, 0.0),
        'LED_FULL': (26.0, 87.5, 0.0),
        'R_FULL': (29.5, 87.5, 0.0),
        'C_BAT1': (51.0, 71.5, 90.0),
        'C_BAT2': (51.0, 75.5, 90.0),

        # 7. South Edge Power Switch & Battery & Expansion Headers
        'SW_PWR': (54.0, 82.0, 0.0),
        'J_SW_EXT': (57.0, 74.0, 0.0),
        'J_BAT': (14.0, 70.0, 90.0),
        'J_UART': (55.0, 31.0, 90.0),
        'J_I2C': (55.0, 35.0, 90.0),

        # 8. South Edge Type-C Ports (Vision & Main)
        'J3': (84.0, 86.10, 0.0),
        'R_VIS_CC1': (76.5, 85.0, 0.0),
        'R_VIS_CC2': (76.5, 87.5, 0.0),
        'J2': (95.5, 86.10, 0.0),
        'R_CC3': (105.0, 73.0, 0.0),
        'R_CC4': (105.0, 75.5, 0.0),
        'C_VBUS_MAIN': (105.0, 78.0, 0.0),

        # 9. North Edge - Top Center Camera
        'J_CAM': (55.0, -7.0, 180.0),
        'R_CAM_SDA': (66.5, -12.0, 0.0),
        'R_CAM_SCL': (66.5, -9.0, 0.0),
        'C_CAM1': (70.0, -12.0, 0.0),
        'C_CAM2': (70.0, -9.0, 0.0),

        # 10. North-Left Edge - Vision MCU (U8) & Support
        'U8': (22.0, 2.5, 0.0),
        'J_TOF': (5.0, -11.0, 90.0),
        'C_U8_1': (9.5, -5.5, 0.0),
        'C_U8_2': (9.5, -2.5, 0.0),
        'R_VIS_EN': (9.5, 0.5, 0.0),
        'C_VIS_EN': (11.0, 3.5, 0.0),
        'SW_VIS_BOOT': (36.0, 1.0, 0.0),
        'R_VIS_BOOT': (36.0, 5.0, 0.0),

        # High-Power Camera LED Driver
        'J_CAM_LED': (44.0, -11.0, 0.0),
        'Q_CAM_LED': (36.0, -11.0, 0.0),
        'R_CAM_LED': (36.0, -7.0, 0.0),
        'R_PD_CAM_LED': (36.0, -4.5, 0.0),
        'D_CAM_LED': (42.0, -4.0, 0.0),

        # Regulators
        'U_LDO_VIS': (42.0, 12.0, 0.0),
        'C_VIS_IN': (35.0, 12.0, 0.0),
        'C_VIS_OUT': (49.0, 12.0, 0.0),

        'U_REG_5V_TOF': (55.0, 20.0, 0.0),
        'C_TOF_IN': (48.0, 20.0, 0.0),
        'C_TOF_OUT': (62.0, 20.0, 0.0),

        # 11. North-Right Edge - Main MCU (U1) & Support
        'U1': (88.0, 2.5, 0.0),
        'C1': (74.0, -5.5, 0.0),
        'C2': (74.0, -2.5, 0.0),
        'R1': (74.0, 0.5, 0.0),
        'C3': (74.0, 3.5, 0.0),
        'SW1': (68.0, 0.0, 0.0),
        'SW2': (68.0, 5.0, 0.0),
        'R2': (68.0, 9.0, 0.0),
        'LED_RGB_MAIN': (73.0, -11.0, 0.0),
        'R_NEO': (76.5, -11.0, 0.0),
        'C_NEO': (76.5, -8.0, 0.0),

        'U4': (72.0, 16.0, 0.0),
        'C_3V3_1': (65.0, 16.0, 0.0),
        'C_3V3_2': (79.0, 16.0, 0.0),
        'LED_3V3': (65.0, 12.0, 0.0),
        'R_3V3_LED': (65.0, 9.5, 0.0),

        # Power path / status passives (Rev 2 verified positions)
        'D_ISO': (76.0, 12.0, 180.0),
        'C_ISO1': (74.0, 22.0, 0.0),
        'C_ISO2': (74.0, 28.0, 0.0),
        'D_STAT': (68.0, 24.5, 90.0),
        'R_STAT': (68.0, 28.0, 90.0),
        'R_DIV1': (68.0, 14.0, 90.0),
        'R_DIV2': (68.0, 17.5, 90.0),
        'C_DIV': (68.0, 21.0, 90.0),
        'C_IN1_L': (20.0, 28.0, 0.0),
        'C_IN2_L': (29.5, 28.0, 0.0),
        'C_IN1_R': (87.0, 26.0, 0.0),
        'C_IN2_R': (80.5, 28.0, 0.0),
    }

def get_courtyard_box(board, fp):
    f_crt = board.GetLayerID('F.Courtyard')
    box = None
    for item in fp.GraphicalItems():
        if item.GetLayer() == f_crt:
            b = item.GetBoundingBox()
            if box is None: box = pcbnew.BOX2I(b.GetOrigin(), b.GetSize())
            else: box.Merge(b)
    if box is None:
        for pad in fp.Pads():
            b = pad.GetBoundingBox()
            if box is None: box = pcbnew.BOX2I(b.GetOrigin(), b.GetSize())
            else: box.Merge(b)
    return box

def main():
    board_path = '/home/peacemaker/Desktop/Hexapod_Robot_Board/Hexapod_Robot_Board.kicad_pcb'
    board = pcbnew.LoadBoard(board_path)
    
    placements = get_complete_placement()
    print(f"Applying {len(placements)} placements...")
    
    for ref, (x, y, rot) in placements.items():
        fp = board.FindFootprintByReference(ref)
        if fp:
            fp.SetPosition(pcbnew.VECTOR2I(int(x * 1e6), int(y * 1e6)))
            fp.SetOrientationDegrees(rot)
        else:
            print(f"Footprint {ref} NOT found!")
            
    # Check courtyard overlaps
    fps = list(board.GetFootprints())
    overlaps = []
    for i in range(len(fps)):
        r1 = fps[i].GetReference()
        cb1 = get_courtyard_box(board, fps[i])
        if cb1 is None: continue
        for j in range(i+1, len(fps)):
            r2 = fps[j].GetReference()
            cb2 = get_courtyard_box(board, fps[j])
            if cb2 is None: continue
            if cb1.Intersects(cb2):
                overlaps.append((r1, r2))
                
    print(f"\nCourtyard Overlap Analysis: {len(overlaps)} overlaps found.")
    for o in overlaps:
        print("  Overlap:", o)
        
    if len(overlaps) == 0:
        print("\nPERFECT ZERO-COLLISION PLACEMENT ACHIEVED!")
        pcbnew.SaveBoard(board_path, board)
        print("Board saved successfully.")

if __name__ == '__main__':
    main()
