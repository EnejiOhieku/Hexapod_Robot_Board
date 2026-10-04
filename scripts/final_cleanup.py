import pcbnew
import math

BOARD_PATH = "/home/peacemaker/Desktop/Hexapod_Robot_Board/Hexapod_Robot_Board.kicad_pcb"

board = pcbnew.LoadBoard(BOARD_PATH)

# Helper to move a footprint by reference
def move_fp(ref, x_mm, y_mm):
    fp = board.FindFootprintByReference(ref)
    if not fp:
        print(f"⚠️ Footprint {ref} not found")
        return
    fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x_mm), pcbnew.FromMM(y_mm)))

# Helper to delete tracks intersecting a footprint's bbox
def delete_intersecting_tracks(fp):
    bbox = fp.GetBoundingBox()
    to_remove = []
    for item in board.GetTracks():
        if isinstance(item, pcbnew.PCB_TRACK) and bbox.Intersects(item.GetBoundingBox()):
            to_remove.append(item)
    for tr in to_remove:
        board.Remove(tr)

# Move components to collision‑free locations
move_fp("C_VBUS_VIS", 70, 30)   # far from USB/VBUS tracks
move_fp("SW_VIS_RST", 45, 3)    # clear spot verified earlier
move_fp("BZ1", 58, 64)          # safe area without GND zones

# Delete any tracks that now intersect the moved footprints
for ref in ["C_VBUS_VIS", "SW_VIS_RST", "BZ1"]:
    fp = board.FindFootprintByReference(ref)
    if fp:
        delete_intersecting_tracks(fp)

# ---- Re‑wire nets ----------------------------------------------------------
# BZ1 (+) -> R_BZ Pad2
bz1_plus = board.FindFootprintByReference("BZ1").FindPadByNumber("1")
r_bz_pad2 = board.FindFootprintByReference("R_BZ").FindPadByNumber("2")
track = pcbnew.PCB_TRACK(board)
track.SetStart(bz1_plus.GetPosition())
track.SetEnd(r_bz_pad2.GetPosition())
track.SetLayer(pcbnew.F_Cu)
track.SetWidth(pcbnew.FromMM(0.2))
board.Add(track)

# BZ1 (‑) -> GND via (creates a solid connection to the ground plane)
bz1_gnd = board.FindFootprintByReference("BZ1").FindPadByNumber("2")
via = pcbnew.VIA(board)
via.SetPosition(bz1_gnd.GetPosition())
via.SetWidth(pcbnew.FromMM(0.6))
via.SetDrill(pcbnew.FromMM(0.3))
via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
board.Add(via)

# SW_VIS_RST Pad2 (VISION_RESET) already belongs to the net – ensure it has a short track to the nearest VISION_RESET rail (if any). Here we simply create a short stub.
sw_vis_rst = board.FindFootprintByReference("SW_VIS_RST")
pad2 = sw_vis_rst.FindPadByNumber("2")
# Find an existing VISION_RESET track near the component (search first track on B_Cu of that net)
vision_reset_tracks = []
for tr in board.GetTracks():
    if isinstance(tr, pcbnew.PCB_TRACK) and tr.GetNet() and tr.GetNet().GetNetClassName() == "Vision" and tr.GetLayer() == pcbnew.B_Cu:
        vision_reset_tracks.append(tr)
if vision_reset_tracks:
    target = vision_reset_tracks[0].GetStart()
    track_rst = pcbnew.PCB_TRACK(board)
    track_rst.SetStart(pad2.GetPosition())
    track_rst.SetEnd(target)
    track_rst.SetLayer(pcbnew.B_Cu)
    track_rst.SetWidth(pcbnew.FromMM(0.2))
    board.Add(track_rst)

# SW_VIS_RST Pad1 (GND) – connect to ground plane (no explicit track needed, zone will cover)

# ---- Fix silkscreen text colour (white -> black) --------------------------
for draw in board.GetDrawings():
    if isinstance(draw, pcbnew.PCB_TEXT) and draw.GetLayer() == pcbnew.F_SilkS:
        # KiCad uses integer colour; 0xFFFFFF is white, 0x000000 is black
        if draw.GetTextColor() == pcbnew.WHITE:
            draw.SetTextColor(pcbnew.BLACK)

# Refresh copper zones
for zone in board.Zones():
    if zone.GetLayer() == pcbnew.F_Cu:
        zone.ClearFilledPolysList()
        zone.Fill(board.GetArea(board.GetPageSettings().GetPageSizeIU()))

# Save changes
pcbnew.Refresh()
board.Save(BOARD_PATH)
print("✅ final_cleanup script completed and board saved.")
