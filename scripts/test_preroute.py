import pcbnew
board = pcbnew.LoadBoard('Hexapod_Robot_Board.kicad_pcb')
f_cu = board.GetLayerID('F.Cu')
b_cu = board.GetLayerID('B.Cu')
in1_cu = board.GetLayerID('In1.Cu')
gnd_net = board.FindNet('GND')

def add_via(net, x, y, drill=0.3, size=0.6):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(pcbnew.VECTOR2I(int(round(x * 1e6)), int(round(y * 1e6))))
    v.SetDrill(int(round(drill * 1e6)))
    v.SetWidth(int(round(size * 1e6)))
    v.SetNet(net)
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    board.Add(v)
    return v

def add_track(net, layer, x1, y1, x2, y2, w=0.25):
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(pcbnew.VECTOR2I(int(round(x1 * 1e6)), int(round(y1 * 1e6))))
    t.SetEnd(pcbnew.VECTOR2I(int(round(x2 * 1e6)), int(round(y2 * 1e6))))
    t.SetWidth(int(round(w * 1e6)))
    t.SetLayer(layer)
    t.SetNet(net)
    board.Add(t)
    return t

# 1. Add GND vias right next to all key GND pads
gnd_via_coords = [
    # J2 (South USB)
    (88.0, 86.1), (98.0, 86.1), (100.1, 80.5), (100.1, 89.0),
    # J3 (North USB)
    (80.0, -11.1), (90.0, -11.1), (76.0, -13.0),
    # J_CAM
    (30.25, -7.5), (16.0, -7.5), (15.0, -11.0),
    # J_TOF
    (6.5, -9.0),
    # U8 GND pads
    (15.0, -7.0), (35.0, -7.0), (25.0, 11.5), (15.0, 11.5), (35.0, 11.5),
    # Decoupling caps
    (11.0, -6.5), (11.0, -1.0), (11.0, 4.0),
    # Boot & Reset
    (46.0, -5.0),
    # Regulators
    (50.0, 23.5), (43.0, 25.0), (57.0, 25.0),
    (62.0, -11.5), (55.0, -9.5), (69.0, -9.5),
    # IMU U7
    (53.05, 42.0), (57.0, 42.0), (55.0, 48.0),
    # R_FB2_R
    (89.5, 51.5)
]
for x, y in gnd_via_coords:
    add_via(gnd_net, x, y)

filler = pcbnew.ZONE_FILLER(board)
filler.Fill(board.Zones())
board.Save('/tmp/test_preroute.kicad_pcb')
print('GND vias added successfully.')
