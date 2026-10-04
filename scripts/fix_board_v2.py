#!/usr/bin/env python3
"""
fix_board_v2.py - Robust PCB fix using proper S-expression tokenizer.
Fixes all DRC violations in Hexapod_Robot_Board.kicad_pcb.
"""

import re
import uuid
import os

BOARD = "/home/peacemaker/Desktop/Hexapod_Robot_Board/Hexapod_Robot_Board.kicad_pcb"


def read_board():
    with open(BOARD, 'r', encoding='utf-8') as f:
        return f.read()


def write_board(content):
    with open(BOARD, 'w', encoding='utf-8') as f:
        f.write(content)


def find_all_segments(content):
    """Return list of (start_pos, end_pos, attrs_dict) for all segments."""
    results = []
    for m in re.finditer(r'\(segment\b', content):
        depth = 0
        i = m.start()
        while i < len(content):
            if content[i] == '(':
                depth += 1
            elif content[i] == ')':
                depth -= 1
                if depth == 0:
                    block = content[m.start():i+1]
                    # Parse attrs
                    start_m = re.search(r'\(start ([0-9.-]+) ([0-9.-]+)\)', block)
                    end_m = re.search(r'\(end ([0-9.-]+) ([0-9.-]+)\)', block)
                    net_m = re.search(r'\(net "([^"]+)"\)', block)
                    layer_m = re.search(r'\(layer "([^"]+)"\)', block)
                    width_m = re.search(r'\(width ([0-9.]+)\)', block)
                    if start_m and end_m and net_m and layer_m:
                        results.append({
                            'start': m.start(), 'end': i+1,
                            'x1': float(start_m.group(1)), 'y1': float(start_m.group(2)),
                            'x2': float(end_m.group(1)), 'y2': float(end_m.group(2)),
                            'net': net_m.group(1),
                            'layer': layer_m.group(1),
                            'width': float(width_m.group(1)) if width_m else 0.25,
                            'text': block,
                        })
                    break
            i += 1
    return results


def find_all_vias(content):
    """Return list of (start_pos, end_pos, attrs_dict) for all vias."""
    results = []
    for m in re.finditer(r'\(via\b', content):
        depth = 0
        i = m.start()
        while i < len(content):
            if content[i] == '(':
            	depth += 1
            elif content[i] == ')':
                depth -= 1
                if depth == 0:
                    block = content[m.start():i+1]
                    at_m = re.search(r'\(at ([0-9.-]+) ([0-9.-]+)\)', block)
                    net_m = re.search(r'\(net "([^"]+)"\)', block)
                    if at_m and net_m:
                        results.append({
                            'start': m.start(), 'end': i+1,
                            'x': float(at_m.group(1)), 'y': float(at_m.group(2)),
                            'net': net_m.group(1),
                            'text': block,
                        })
                    break
            i += 1
    return results


def find_footprint_by_ref(content, ref):
    """Find footprint block start/end positions by reference."""
    for m in re.finditer(r'\(footprint\b', content):
        depth = 0
        i = m.start()
        while i < len(content):
            if content[i] == '(':
                depth += 1
            elif content[i] == ')':
                depth -= 1
                if depth == 0:
                    block = content[m.start():i+1]
                    if f'"Reference" "{ref}"' in block or f'"{ref}"' in block.split('(property')[0][:200]:
                        # More precise ref check
                        if re.search(r'\(property "Reference" "' + re.escape(ref) + r'"', block):
                            return m.start(), i+1, block
                    break
            i += 1
    return None, None, None


def near(v, target, tol=0.2):
    return abs(v - target) < tol


def make_seg(net, layer, x1, y1, x2, y2, width=0.25):
    uid = str(uuid.uuid4())
    return (f'\n\t(segment\n\t\t(start {x1:.4f} {y1:.4f})\n\t\t(end {x2:.4f} {y2:.4f})\n'
            f'\t\t(width {width:.4f})\n\t\t(layer "{layer}")\n\t\t(net "{net}")\n'
            f'\t\t(uuid "{uid}")\n\t)')


def make_via(net, x, y, drill=0.3, size=0.6):
    uid = str(uuid.uuid4())
    return (f'\n\t(via\n\t\t(at {x:.4f} {y:.4f})\n\t\t(size {size:.4f})\n\t\t(drill {drill:.4f})\n'
            f'\t\t(layers "F.Cu" "B.Cu")\n\t\t(net "{net}")\n\t\t(uuid "{uid}")\n\t)')


print("=" * 60)
print("Hexapod Robot Board - DRC Violation Fix Script v2")
print("=" * 60)

content = read_board()
orig_len = len(content)
print(f"Board loaded: {orig_len} bytes")

# Collect all segments and vias
segments = find_all_segments(content)
vias = find_all_vias(content)
print(f"Found {len(segments)} segments, {len(vias)} vias")

# Build set of positions to delete (by start char position)
to_delete = set()

# ============================================================
# VIOLATIONS TO FIX:
# 1. GND via at (54.75, 48.2) -- too close to +3V3 via and shorting GND+3V3
# 2. GND track stub at (54.75, 46.95) -- shorting U7 pad10 (Net-(C_MPU2-Pad1))
# 3. GND track stub at (54.75, 46.95)-(54.75, 48.2) -- clearance violation
# 4. Net-(BZ1-+) track at (58, 61.325) -- crosses BZ1 GND pad at (58, 62.8)
# 5. VISION_RESET track at (18.1, -7.5) -- crosses +3V3_VIS
# 6. VISION_RESET track at (14.59, -3.99) -- dangling
# 7. GND track at (61.2, 66.0) -- dangling
# 8. GND track at (58.0, 69.2) -- dangling  
# 9. CAM_D0 track at (42.9, 3.0) -- dangling
# 10. SW_VIS_RST at (16, -9) -- courtyard overlap with J_TOF and U8
# ============================================================

print("\n--- Marking segments/vias for deletion ---")

for seg in segments:
    x1, y1, x2, y2, net, layer = seg['x1'], seg['y1'], seg['x2'], seg['y2'], seg['net'], seg['layer']
    
    # Fix 2+3: GND track stubs near (54.75, 46.95) and (54.75, 48.2)
    if net == 'GND' and layer == 'F.Cu':
        if (near(x1, 54.75) or near(x2, 54.75)):
            if (near(y1, 46.95) or near(y2, 46.95) or near(y1, 48.2) or near(y2, 48.2)):
                to_delete.add(seg['start'])
                print(f"  ✅ Mark GND stub ({x1},{y1})->({x2},{y2}) for deletion")
    
    # Fix 4: Net-(BZ1-+) track from (58, 61.325) that crosses BZ1 GND pad
    if net == 'Net-(BZ1-+)' and layer == 'F.Cu':
        if near(x1, 58.0) and near(y1, 61.325) or near(x2, 58.0) and near(y2, 61.325):
            to_delete.add(seg['start'])
            print(f"  ✅ Mark BZ1+ bad track ({x1},{y1})->({x2},{y2}) for deletion")
    
    # Fix 5: VISION_RESET tracks causing problems
    if net == 'VISION_RESET' and layer == 'F.Cu':
        # Track crossing +3V3_VIS at (13.25, -4.64) region
        if (near(x1, 18.1, 0.3) or near(x2, 18.1, 0.3)) and (near(y1, -7.5, 0.5) or near(y2, -7.5, 0.5)):
            to_delete.add(seg['start'])
            print(f"  ✅ Mark VISION_RESET crossing track ({x1},{y1})->({x2},{y2}) for deletion")
        if (near(x1, 18.1, 0.3) or near(x2, 18.1, 0.3)) and (near(y1, -9.0, 0.5) or near(y2, -9.0, 0.5)):
            to_delete.add(seg['start'])
            print(f"  ✅ Mark VISION_RESET track at y=-9 ({x1},{y1})->({x2},{y2}) for deletion")
    
    # Fix 6: VISION_RESET dangling track at (14.59, -3.99)
    if net == 'VISION_RESET' and layer == 'F.Cu':
        if near(x1, 14.59, 0.2) and near(y1, -3.99, 0.2) or near(x2, 14.59, 0.2) and near(y2, -3.99, 0.2):
            to_delete.add(seg['start'])
            print(f"  ✅ Mark VISION_RESET dangling track ({x1},{y1})->({x2},{y2}) for deletion")
    
    # Fix 7: GND dangling track at (61.2, 66.0) -- from bad BZ1 routing
    if net == 'GND' and layer == 'F.Cu':
        if near(x1, 61.2, 0.2) and near(y1, 66.0, 0.2) or near(x2, 61.2, 0.2) and near(y2, 66.0, 0.2):
            to_delete.add(seg['start'])
            print(f"  ✅ Mark GND dangling track at 61.2,66 ({x1},{y1})->({x2},{y2}) for deletion")
    
    # Fix 8: GND dangling track at (58.0, 69.2)
    if net == 'GND' and layer == 'F.Cu':
        if near(x1, 58.0, 0.2) and near(y1, 69.2, 0.2) or near(x2, 58.0, 0.2) and near(y2, 69.2, 0.2):
            to_delete.add(seg['start'])
            print(f"  ✅ Mark GND dangling track at 58,69.2 ({x1},{y1})->({x2},{y2}) for deletion")
    
    # Fix 9: CAM_D0 dangling track at (42.9, 3.0) -- from bad SW_VIS_RST routing
    if net == 'CAM_D0' and layer == 'F.Cu':
        if near(x1, 42.9, 0.2) and near(y1, 3.0, 0.2) or near(x2, 42.9, 0.2) and near(y2, 3.0, 0.2):
            to_delete.add(seg['start'])
            print(f"  ✅ Mark CAM_D0 dangling track ({x1},{y1})->({x2},{y2}) for deletion")
    
    # Also remove SW_VIS_RST-related routing from bad position (near 33.9, 38.1, 32.5 at y=8.5)
    if net in ('GND', 'VISION_RESET') and layer == 'F.Cu':
        y_near_85 = near(y1, 8.5, 0.3) or near(y2, 8.5, 0.3)
        x_near_sw = any(near(x1, x, 0.5) or near(x2, x, 0.5) for x in [32.5, 33.9, 38.1, 39.5])
        if y_near_85 and x_near_sw:
            to_delete.add(seg['start'])
            print(f"  ✅ Mark SW_VIS_RST routing ({x1},{y1})->({x2},{y2}) net={net} for deletion")

# Mark vias for deletion
for via in vias:
    x, y, net = via['x'], via['y'], via['net']
    
    # Fix 1: GND via at (54.75, 48.2) -- too close to +3V3 via
    if net == 'GND' and near(x, 54.75) and near(y, 48.2):
        to_delete.add(via['start'])
        print(f"  ✅ Mark GND via at ({x},{y}) for deletion [shorts +3V3]")
    
    # Remove VISION_RESET via from bad routing at (39.5, 8.5)
    if net == 'VISION_RESET' and near(x, 39.5) and near(y, 8.5, 0.3):
        to_delete.add(via['start'])
        print(f"  ✅ Mark VISION_RESET via at ({x},{y}) for deletion")
    
    # Remove GND via at (66.0, 66.0) - dangling BZ1 via
    if net == 'GND' and near(x, 66.0) and near(y, 66.0):
        to_delete.add(via['start'])
        print(f"  ✅ Mark GND via at ({x},{y}) for deletion [dangling]")
    
    # Remove GND via at (32.5, 8.5) - bad SW_VIS_RST routing
    if net == 'GND' and near(x, 32.5) and near(y, 8.5, 0.3):
        to_delete.add(via['start'])
        print(f"  ✅ Mark GND via at ({x},{y}) for deletion [bad SW_VIS_RST]")

print(f"\n  Total items to delete: {len(to_delete)}")

# Now delete them from back to front (to preserve positions)
all_items = [(s['start'], s['end']) for s in segments if s['start'] in to_delete]
all_items += [(v['start'], v['end']) for v in vias if v['start'] in to_delete]
all_items.sort(key=lambda x: x[0], reverse=True)

for start, end in all_items:
    content = content[:start] + content[end:]

print(f"  Board after deletions: {len(content)} bytes")

# ============================================================
# Fix 10: Move SW_VIS_RST footprint from (16, -9) to (45, -8)
# ============================================================
print("\n--- Fix 10: Moving SW_VIS_RST footprint ---")
fp_start, fp_end, fp_block = find_footprint_by_ref(content, 'SW_VIS_RST')
if fp_start is not None:
    # Replace the (at 16 -9) in the footprint
    old_at = re.search(r'\(at 16(?:\.0+)? -9(?:\.0+)?\)', fp_block)
    if old_at:
        new_fp = fp_block[:old_at.start()] + '(at 45 -8)' + fp_block[old_at.end():]
        content = content[:fp_start] + new_fp + content[fp_end:]
        # Refresh positions since we modified content
        fp_start, fp_end, fp_block = find_footprint_by_ref(content, 'SW_VIS_RST')
        print(f"  ✅ Moved SW_VIS_RST to (45, -8)")
    else:
        print(f"  ⚠️  Could not find (at 16 -9) pattern in SW_VIS_RST block")
        print(f"  Block start: {fp_block[:100]}")
else:
    print("  ⚠️  SW_VIS_RST footprint not found!")

# ============================================================
# Fix BZ1 net assignment: BZ1 Pad 1 should be Net-(BZ1-+), Pad 2 should be GND
# Check the BZ1 footprint orientation - at (58, 66, 90°)
# For MagneticBuzzer_Kingstate_KCG0601 at 90°:
#   Pad 1 is at y - 3.2 = 62.8 (the + pad)  
#   Pad 2 is at y + 3.2 = 69.2 (the - GND pad)
# The Net-(BZ1-+) track connecting to R_BZ Pad2 at (62.325, 57.0):
#   Route: (58, 62.8) -> path -> (62.325, 57.0)
# ============================================================
print("\n--- Adding clean BZ1 routing ---")
new_routing = ""
# BZ1 Pad1 at (58, 62.8) -> route right to clear BZ1 courtyard, then to R_BZ Pad2
new_routing += make_seg("Net-(BZ1-+)", "F.Cu", 58.0, 62.8, 62.0, 62.8, 0.3)
new_routing += make_seg("Net-(BZ1-+)", "F.Cu", 62.0, 62.8, 62.0, 57.0, 0.3)
new_routing += make_seg("Net-(BZ1-+)", "F.Cu", 62.0, 57.0, 62.325, 57.0, 0.3)
print("  Added: BZ1 Pad1(58,62.8) -> (62,62.8) -> (62,57) -> R_BZ Pad2(62.325,57)")

# ============================================================
# Add VISION_RESET routing
# Key pads:
#  C_VIS_EN Pad1 at (8.725, -2.5)
#  R_VIS_EN Pad2 at (10.325, -0.5)
#  U8 Pad3 at (13.25, -3.37)
#  U1 Pad22 at (89.905, 11.85)
#  SW_VIS_RST Pad2 (new pos: approx 47.1, -8) VISION_RESET
# Connect: C_VIS_EN.1 <-> R_VIS_EN.2 via short hop
# Connect: U8.3 -> R_VIS_EN.2  (direct F.Cu track)
# Connect: SW_VIS_RST -> existing net via B.Cu route
# Connect: U1.22 -> other VISION_RESET nodes via B.Cu
# ============================================================
print("\n--- Adding VISION_RESET routing ---")

# C_VIS_EN Pad1 (8.725, -2.5) -> R_VIS_EN Pad2 (10.325, -0.5)
new_routing += make_seg("VISION_RESET", "F.Cu", 8.725, -2.5, 8.725, -0.5, 0.25)
new_routing += make_seg("VISION_RESET", "F.Cu", 8.725, -0.5, 10.325, -0.5, 0.25)
print("  Added: C_VIS_EN.Pad1 -> R_VIS_EN.Pad2")

# U8 Pad3 (13.25, -3.37) -> R_VIS_EN Pad2 (10.325, -0.5)
new_routing += make_seg("VISION_RESET", "F.Cu", 13.25, -3.37, 13.25, -0.5, 0.25)
new_routing += make_seg("VISION_RESET", "F.Cu", 13.25, -0.5, 10.325, -0.5, 0.25)
print("  Added: U8.Pad3 -> R_VIS_EN.Pad2")

# U1 Pad22 (89.905, 11.85) -> existing net via B.Cu long route
new_routing += make_via("VISION_RESET", 10.325, -0.5, 0.3, 0.6)
new_routing += make_seg("VISION_RESET", "B.Cu", 10.325, -0.5, 10.325, 11.85, 0.25)
new_routing += make_seg("VISION_RESET", "B.Cu", 10.325, 11.85, 89.905, 11.85, 0.25)
new_routing += make_via("VISION_RESET", 89.905, 11.85, 0.3, 0.6)
print("  Added: R_VIS_EN -> (B.Cu) -> U1.Pad22")

# SW_VIS_RST Pad2 at new pos (45, -8): Pad2 = +2.1mm in x = (47.1, -8)
new_routing += make_via("VISION_RESET", 47.1, -8, 0.3, 0.6)
new_routing += make_seg("VISION_RESET", "B.Cu", 47.1, -8, 10.325, -8, 0.25)
new_routing += make_seg("VISION_RESET", "B.Cu", 10.325, -8, 10.325, -0.5, 0.25)
print("  Added: SW_VIS_RST.Pad2 -> (B.Cu) -> VISION_RESET node")

# Insert all new routing before the closing paren of the board
insert_pos = content.rfind('\n)')
content = content[:insert_pos] + new_routing + content[insert_pos:]

print(f"\n  Board after additions: {len(content)} bytes")

write_board(content)
print("\n✅ Board saved successfully!")
print("\nNow run: kicad-cli pcb drc ... to verify")
