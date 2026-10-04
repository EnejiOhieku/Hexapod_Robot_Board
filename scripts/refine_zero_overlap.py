#!/usr/bin/env python3
import pcbnew

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

def test(board, p):
    for ref, (x, y, rot) in p.items():
        fp = board.FindFootprintByReference(ref)
        if fp:
            fp.SetPosition(pcbnew.VECTOR2I(int(x * 1e6), int(y * 1e6)))
            fp.SetOrientationDegrees(rot)
            
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
    return overlaps

def main():
    board_path = '/home/peacemaker/Desktop/Hexapod_Robot_Board/Hexapod_Robot_Board.kicad_pcb'
    board = pcbnew.LoadBoard(board_path)
    
    import sys
    sys.path.insert(0, '/home/peacemaker/Desktop/Hexapod_Robot_Board')
    import scripts.solve_complete_placement as scp
    p = scp.get_complete_placement()
    
    # Apply targeted adjustments
    p['J_UART'] = (55.0, 28.0, 0.0)
    p['J_I2C'] = (55.0, 34.0, 0.0)
    
    p['J_CAM'] = (55.0, -11.0, 180.0)
    p['R_CAM_SDA'] = (66.5, -12.0, 0.0)
    p['R_CAM_SCL'] = (66.5, -8.5, 0.0)
    p['C_CAM1'] = (66.5, -14.0, 0.0)
    p['C_CAM2'] = (66.5, -6.0, 0.0)
    
    p['LED_RGB_MAIN'] = (73.0, -11.0, 0.0)
    p['R_NEO'] = (75.0, -8.0, 0.0)
    p['C_NEO'] = (75.0, -5.5, 0.0)
    
    p['C_U8_1'] = (9.5, -6.5, 0.0)
    p['C_U8_2'] = (9.5, -4.0, 0.0)
    p['C_VIS_EN'] = (9.5, -1.5, 0.0)
    p['R_VIS_EN'] = (9.5, 1.0, 0.0)
    p['D_CAM_LED'] = (44.0, -4.0, 0.0)
    
    p['R_SDA'] = (51.0, 55.0, 0.0)
    p['R_SCL'] = (54.5, 55.0, 0.0)
    p['R_OE'] = (58.0, 55.0, 0.0)
    p['R_BZ'] = (61.5, 55.0, 0.0)
    
    # Clear U4 vs divider/isolation passives
    p['U4'] = (71.0, 15.0, 0.0)
    p['C_3V3_1'] = (79.0, 14.0, 0.0)
    p['C_3V3_2'] = (79.0, 17.0, 0.0)
    p['LED_3V3'] = (79.0, 20.0, 0.0)
    p['R_3V3_LED'] = (79.0, 22.5, 0.0)
    
    p['C1'] = (74.0, -3.0, 0.0)
    p['C2'] = (74.0, -0.5, 0.0)
    p['R1'] = (74.0, 2.0, 0.0)
    p['C3'] = (74.0, 4.5, 0.0)
    
    p['D_ISO'] = (65.0, 8.0, 180.0)
    p['R_DIV1'] = (65.0, 11.5, 0.0)
    p['R_DIV2'] = (65.0, 14.0, 0.0)
    p['C_DIV'] = (65.0, 16.5, 0.0)
    p['C_ISO1'] = (65.0, 23.5, 0.0)
    p['C_ISO2'] = (65.0, 27.0, 0.0)
    p['D_STAT'] = (71.0, 25.0, 90.0)
    p['R_STAT'] = (71.0, 28.5, 90.0)
    
    p['SW1'] = (66.0, -1.0, 0.0)
    p['SW2'] = (66.0, 3.5, 0.0)
    p['R2'] = (62.0, 3.5, 0.0)
    
    overlaps = test(board, p)
    print(f"Resulting overlaps: {len(overlaps)}")
    for o in overlaps:
        print("  Overlap:", o)
        
    if len(overlaps) == 0:
        print("\n*** ZERO OVERLAPS REACHED! ***")
        pcbnew.SaveBoard(board_path, board)
        print("Saved to", board_path)

if __name__ == '__main__':
    main()
