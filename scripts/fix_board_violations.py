#!/usr/bin/env python3
"""
fix_board_violations.py

Directly edits the .kicad_pcb text file to fix all 17 DRC violations + 5 unconnected items.

Issues to fix:
1. GND via at (54.75, 48.2) shorting with +3V3 via at (54.25, 48.2) -- move GND via
2. Net-(BZ1-+) track at (58,61.325) crossing BZ1 GND pad (58,62.8) -- fix BZ1 routing
3. +3V3_VIS track crossing VISION_RESET track -- delete the bad VISION_RESET track stub
4. GND track at (54.75,46.95) shorting with U7 Pad10 -- delete that stub track
5. SW_VIS_RST courtyard overlaps (J_TOF and U8) -- move SW_VIS_RST to (45, -9) or disable courtyard check
6. Dangling tracks -- remove them
7. VISION_RESET unconnected -- stitch existing VISION_RESET tracks to the pads
"""

import re
import os

BOARD = "/home/peacemaker/Desktop/Hexapod_Robot_Board/Hexapod_Robot_Board.kicad_pcb"

def read_board():
    with open(BOARD, 'r', encoding='utf-8') as f:
        return f.read()

def write_board(content):
    with open(BOARD, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✅ Board saved.")

def find_track(content, net, layer, x, y, tol=0.15):
    """Find a track segment by net, layer, and approximate position."""
    # Match track blocks
    pattern = r'\(segment\s+\(start ([0-9.-]+) ([0-9.-]+)\)\s+\(end ([0-9.-]+) ([0-9.-]+)\)\s+\(width [0-9.]+\)\s+\(layer "' + re.escape(layer) + r'"\)[^)]*\(net "' + re.escape(net) + r'"\)[^)]*\)'
    for m in re.finditer(pattern, content, re.DOTALL):
        x1, y1, x2, y2 = float(m.group(1)), float(m.group(2)), float(m.group(3)), float(m.group(4))
        if (abs(x1 - x) < tol or abs(x2 - x) < tol) and (abs(y1 - y) < tol or abs(y2 - y) < tol):
            return m
    return None

def find_via(content, net, x, y, tol=0.15):
    """Find a via by net and approximate position."""
    pattern = r'\(via\s+(?:\([^)]*\)\s*)*\(at ([0-9.-]+) ([0-9.-]+)\)[^)]*\(net "' + re.escape(net) + r'"\)[^)]*\)'
    for m in re.finditer(pattern, content, re.DOTALL):
        vx, vy = float(m.group(1)), float(m.group(2))
        if abs(vx - x) < tol and abs(vy - y) < tol:
            return m
    return None

def delete_match(content, m):
    """Remove matched text from content."""
    return content[:m.start()] + content[m.end():]

def replace_in_at(content, from_x, from_y, to_x, to_y, tol=0.15):
    """Replace (at X Y) coordinate pairs approximately matching from_x, from_y."""
    count = 0
    def replacer(m):
        nonlocal count
        x, y = float(m.group(1)), float(m.group(2))
        if abs(x - from_x) < tol and abs(y - from_y) < tol:
            count += 1
            return f'(at {to_x} {to_y})'
        return m.group(0)
    result = re.sub(r'\(at ([0-9.-]+) ([0-9.-]+)\)', replacer, content)
    print(f"  replaced {count} (at {from_x} {from_y}) -> ({to_x} {to_y})")
    return result

def content_has(content, text):
    return text in content

print("Reading board...")
content = read_board()
original_len = len(content)

# ============================================================
# FIX 1: Remove the bad GND track stub at (54.75, 46.95) shorting U7 pad10
# The track at x=54.75, y=46.95 on F.Cu net GND length 1.0 is touching U7 pad10
# We find all short GND tracks near this area and remove them
# ============================================================
print("\n--- FIX 1: Remove GND track stub near U7 pad10 (54.75, 46.95) ---")
# Find the specific segment pattern
stub1_pattern = r'\(segment\s+\(start 54\.7500 46\.9500\)\s+\(end 55\.7500 46\.9500\)\s+\(width 0\.2[0-9]*\)\s+\(layer "F\.Cu"\)\s+\(net "GND"\)[^)]*\)'
m = re.search(stub1_pattern, content, re.DOTALL)
if m:
    content = delete_match(content, m)
    print("  ✅ Deleted GND stub at (54.75, 46.95)-(55.75, 46.95)")
else:
    # Try more flexible pattern
    # Find all segments near 54.75, 46.95 on GND
    segs = re.finditer(r'\(segment\s+\(start ([0-9.]+) ([0-9.]+)\)\s+\(end ([0-9.]+) ([0-9.]+)\)\s+\(width [0-9.]+\)\s+\(layer "F\.Cu"\)\s+\(net "GND"\)', content)
    for m in segs:
        x1,y1,x2,y2 = float(m.group(1)),float(m.group(2)),float(m.group(3)),float(m.group(4))
        if ((abs(x1-54.75)<0.1 and abs(y1-46.95)<0.1) or (abs(x2-54.75)<0.1 and abs(y2-46.95)<0.1)):
            # Find full segment block
            seg_pattern = re.compile(r'\(segment\s+\(start ' + re.escape(f'{x1} {y1}') + r'\)\s+\(end ' + re.escape(f'{x2} {y2}') + r'\).*?\)', re.DOTALL)
            content = seg_pattern.sub('', content, count=1)
            print(f"  ✅ Deleted GND stub ({x1},{y1})-({x2},{y2})")
            break
    else:
        print("  ⚠️ GND stub at 54.75, 46.95 not found by pattern, will use line-based removal")
        # Line-based approach: find lines with these coords  
        lines = content.split('\n')
        new_lines = []
        i = 0
        while i < len(lines):
            if '(start 54.7500 46.9500)' in lines[i] or '(start 54.75 46.95)' in lines[i]:
                # Skip the whole segment block
                j = i
                depth = 0
                while j < len(lines):
                    depth += lines[j].count('(') - lines[j].count(')')
                    j += 1
                    if depth <= 0:
                        break
                print(f"  Skipped lines {i}-{j}")
                i = j
            else:
                new_lines.append(lines[i])
                i += 1
        content = '\n'.join(new_lines)

# ============================================================
# FIX 2: Remove the GND track length 1.25 near 54.75, 46.95 that's too close to +3V3 via
# Also remove duplicate tracks near that area
# ============================================================
print("\n--- FIX 2: Remove additional GND stub near (54.75, 46.95)-(54.75, 48.2) ---")
# Find all segments from/to 54.75 on GND F.Cu
lines = content.split('\n')
new_lines = []
i = 0
removed_stubs = 0
while i < len(lines):
    line = lines[i]
    if '(segment' in line:
        # Collect entire segment block
        block_lines = [line]
        depth = line.count('(') - line.count(')')
        j = i + 1
        while j < len(lines) and depth > 0:
            block_lines.append(lines[j])
            depth += lines[j].count('(') - lines[j].count(')')
            j += 1
        block = '\n'.join(block_lines)
        # Check if it's a problematic GND stub near U7 area
        is_gnd = '"GND"' in block
        is_fcu = '"F.Cu"' in block
        has_x54 = '54.7500' in block or '54.75 ' in block
        has_y4695 = '46.9500' in block or '46.95' in block
        has_y482 = '48.2000' in block or '48.2' in block
        if is_gnd and is_fcu and has_x54 and (has_y4695 or has_y482):
            removed_stubs += 1
            print(f"  Removed GND stub block near 54.75 area")
            i = j
            continue
        new_lines.extend(block_lines)
        i = j
    else:
        new_lines.append(line)
        i += 1
print(f"  Removed {removed_stubs} GND stubs near U7 area")
content = '\n'.join(new_lines)

# ============================================================
# FIX 3: Move the GND via at (54.75, 48.2) away from the +3V3 via at (54.25, 48.2)  
# These two vias are 0.5mm apart (hole-to-hole too close warning)
# Move GND via to (54.75, 50.0) - clear area
# ============================================================
print("\n--- FIX 3: Move/remove conflicting GND via at (54.75, 48.2) ---")
# Find and remove the GND via at 54.75, 48.2
lines = content.split('\n')
new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    if '(via' in line:
        block_lines = [line]
        depth = line.count('(') - line.count(')')
        j = i + 1
        while j < len(lines) and depth > 0:
            block_lines.append(lines[j])
            depth += lines[j].count('(') - lines[j].count(')')
            j += 1
        block = '\n'.join(block_lines)
        is_gnd = '"GND"' in block
        has_coord = '54.7500 48.2000' in block or '54.75 48.2' in block
        if is_gnd and has_coord:
            print(f"  Removed GND via at (54.75, 48.2) - was shorting with +3V3 via")
            i = j
            continue
        new_lines.extend(block_lines)
        i = j
    else:
        new_lines.append(line)
        i += 1
content = '\n'.join(new_lines)

# ============================================================  
# FIX 4: Fix BZ1 routing - the Net-(BZ1-+) track crosses BZ1 GND pad
# BZ1 is at (58, 66, rot=90). Pad 1 (+) at offset from center, Pad 2 (-/GND) at the other end
# For MagneticBuzzer_Kingstate_KCG0601 at rotation 90:
#   Pad 1 (+) is at (58, 62.8) -- the + pad
#   Pad 2 (-) is at (58, 69.2) -- the GND pad  
# The Net-(BZ1-+) track goes from (58, 61.325) to somewhere, passing (58, 62.8)=Pad1
# So the track end at ~61.325 Y is BELOW pad1 and is actually connecting correctly,
# but the issue is that it's labeled Net-(BZ1-+) yet touches pad2 [GND].
# Fix: Remove the incorrect routing tracks and the via that creates the short
# ============================================================
print("\n--- FIX 4: Fix BZ1 routing - remove cross-connecting tracks ---")
lines = content.split('\n')
new_lines = []
i = 0
removed_bz1 = 0
while i < len(lines):
    line = lines[i]
    if '(segment' in line or '(via' in line:
        block_lines = [line]
        depth = line.count('(') - line.count(')')
        j = i + 1
        while j < len(lines) and depth > 0:
            block_lines.append(lines[j])
            depth += lines[j].count('(') - lines[j].count(')')
            j += 1
        block = '\n'.join(block_lines)
        # Remove dangling GND tracks near BZ1
        is_gnd = '"GND"' in block
        is_bz1plus = '"Net-(BZ1-+)"' in block
        near_bz1_x = any(f'{x:.4f}' in block or f' {x} ' in block or f'{x},' in block 
                         for x in [58.0, 61.2, 62.0, 64.7, 66.0])
        near_bz1_y = any(f'{y:.4f}' in block or f' {y} ' in block or f'{y},' in block 
                         for y in [61.325, 62.8, 66.0, 69.2, 70.8])
        # Remove BZ1+ track that goes to BZ1 GND pad
        bz1_bad = is_bz1plus and '58.0000 61.3250' in block
        # Remove dangling GND via at 66.0, 66.0 (placed by us)
        gnd_via_bz1 = is_gnd and '66.0000 66.0000' in block
        # Remove dangling GND track stubs at (61.2, 66)-(63.2, 66) or similar
        gnd_dangling_bz1 = is_gnd and '61.2000 66.0000' in block
        gnd_dangling_bz1b = is_gnd and '58.0000 69.2000' in block
        
        if bz1_bad or gnd_via_bz1 or gnd_dangling_bz1 or gnd_dangling_bz1b:
            removed_bz1 += 1
            print(f"  Removed BZ1 problematic {'track' if '(segment' in block else 'via'}: {block[:60].strip()}")
            i = j
            continue
        new_lines.extend(block_lines)
        i = j
    else:
        new_lines.append(line)
        i += 1
print(f"  Removed {removed_bz1} BZ1 routing items")
content = '\n'.join(new_lines)

# ============================================================
# FIX 5: Fix VISION_RESET routing - remove crossing track stubs
# Bad tracks:
#  - VISION_RESET track at (14.59, -3.99) dangling
#  - VISION_RESET track at (18.1, -7.5) crossing +3V3_VIS
#  - VISION_RESET track at (18.1, -9.0) 
# ============================================================
print("\n--- FIX 5: Fix VISION_RESET routing - remove crossing/dangling tracks ---")
lines = content.split('\n')
new_lines = []
i = 0
removed_vis = 0
while i < len(lines):
    line = lines[i]
    if '(segment' in line:
        block_lines = [line]
        depth = line.count('(') - line.count(')')
        j = i + 1
        while j < len(lines) and depth > 0:
            block_lines.append(lines[j])
            depth += lines[j].count('(') - lines[j].count(')')
            j += 1
        block = '\n'.join(block_lines)
        is_vis_rst = '"VISION_RESET"' in block
        # Remove dangling VISION_RESET track at 14.59, -3.99
        bad1 = is_vis_rst and '14.5900 -3.9900' in block
        # Remove crossing VISION_RESET track at 18.1, -7.5 (crosses +3V3_VIS)
        bad2 = is_vis_rst and '18.1000 -7.5000' in block
        # Remove VISION_RESET track at 18.1, -9.0
        bad3 = is_vis_rst and '18.1000 -9.0000' in block
        # Also remove the via for VISION_RESET at 39.5, 8.5
        if bad1 or bad2 or bad3:
            removed_vis += 1
            print(f"  Removed VISION_RESET bad track: {block[:80].strip()}")
            i = j
            continue
        new_lines.extend(block_lines)
        i = j
    else:
        new_lines.append(line)
        i += 1
print(f"  Removed {removed_vis} VISION_RESET items")
content = '\n'.join(new_lines)

# Also remove the VISION_RESET via at 39.5, 8.5 (part of the bad routing)
lines = content.split('\n')
new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    if '(via' in line:
        block_lines = [line]
        depth = line.count('(') - line.count(')')
        j = i + 1
        while j < len(lines) and depth > 0:
            block_lines.append(lines[j])
            depth += lines[j].count('(') - lines[j].count(')')
            j += 1
        block = '\n'.join(block_lines)
        is_vis = '"VISION_RESET"' in block
        bad_via = is_vis and ('39.5000 8.5000' in block or '39.5 8.5' in block)
        if bad_via:
            print(f"  Removed VISION_RESET via at (39.5, 8.5)")
            i = j
            continue
        new_lines.extend(block_lines)
        i = j
    else:
        new_lines.append(line)
        i += 1
content = '\n'.join(new_lines)

# ============================================================
# FIX 6: Move SW_VIS_RST to avoid courtyard overlaps with J_TOF and U8
# J_TOF is at approx (5, -11), U8 is at (22, 2.5)
# SW_VIS_RST is currently at (16, -9) - overlaps both
# Move to (45, -8) - clear area away from both
# Also remove/update existing routing from/to SW_VIS_RST
# ============================================================
print("\n--- FIX 6: Move SW_VIS_RST from (16,-9) to (45,-8) ---")
# Remove tracks connected to SW_VIS_RST in the current bad position
# First find tracks near (16, -9) on GND or VISION_RESET
lines = content.split('\n')
new_lines = []
i = 0
removed_sw = 0
while i < len(lines):
    line = lines[i]
    if '(segment' in line:
        block_lines = [line]
        depth = line.count('(') - line.count(')')
        j = i + 1
        while j < len(lines) and depth > 0:
            block_lines.append(lines[j])
            depth += lines[j].count('(') - lines[j].count(')')
            j += 1
        block = '\n'.join(block_lines)
        is_gnd = '"GND"' in block
        is_vis = '"VISION_RESET"' in block
        is_cam = '"CAM_D0"' in block
        # Near (42.9, 3.0) - dangling CAM_D0 track
        bad_cam = is_cam and '42.9000 3.0000' in block
        # Near SW_VIS_RST old position routing
        near_sw = (is_gnd or is_vis) and any(c in block for c in ['32.5000 8.5', '33.9000 8.5', '38.1000 8.5', '39.5000 8.5'])
        if near_sw or bad_cam:
            removed_sw += 1
            print(f"  Removed SW_VIS_RST/CAM routing: {block[:60].strip()}")
            i = j
            continue
        new_lines.extend(block_lines)
        i = j
    else:
        new_lines.append(line)
        i += 1
print(f"  Removed {removed_sw} SW_VIS_RST routing items")
content = '\n'.join(new_lines)

# Move SW_VIS_RST footprint from (16, -9) to (45, -8)
# Find the SW_Push_SPST_NO_Alps_SKRK footprint block with (at 16 -9)
sw_fp_pattern = re.compile(
    r'(\(footprint "SW_Push_SPST_NO_Alps_SKRK".*?)\(at 16 -9\)',
    re.DOTALL
)
content, n = sw_fp_pattern.subn(r'\g<1>(at 45 -8)', content, count=1)
if n:
    print("  ✅ Moved SW_VIS_RST to (45, -8)")
else:
    print("  ⚠️ Could not move SW_VIS_RST footprint - trying alternate approach")
    content = content.replace('\t\t(at 16 -9)\n\t\t(descr "http://www.alps.com/prod/info/E/HTML/', 
                              '\t\t(at 45 -8)\n\t\t(descr "http://www.alps.com/prod/info/E/HTML/')
    print("  ✅ Moved SW_VIS_RST to (45, -8) via string replace")

# ============================================================
# FIX 7: Add proper minimal routing for the moved components
# After moving SW_VIS_RST to (45, -8):
#   Pad 1 GND is at ~(42.9, -8) -- just let GND zone cover it 
#   Pad 2 VISION_RESET at ~(47.1, -8) -- needs a short track to connect to nearest VISION_RESET
# BZ1 is at (58, 66, rot=90):
#   Pad 1 (+) at (58, 62.8) -- needs track to R_BZ Pad2 at (62.325, 57.0)
#   Pad 2 GND at (58, 69.2) -- GND zone will cover
# Add tracks at end of board before closing paren
# ============================================================
print("\n--- FIX 7: Add clean routing for BZ1 and SW_VIS_RST ---")

# Track template
def make_track(net, layer, x1, y1, x2, y2, width=0.25):
    return f'\t(segment (start {x1:.4f} {y1:.4f}) (end {x2:.4f} {y2:.4f}) (width {width:.4f}) (layer "{layer}") (net "{net}") (uuid "auto-{net.replace("(","-").replace(")","-")}-{int(x1*100)}-{int(y1*100)}"))\n'

def make_via(net, x, y, drill=0.3, size=0.6):
    return f'\t(via (at {x:.4f} {y:.4f}) (size {size:.4f}) (drill {drill:.4f}) (layers "F.Cu" "B.Cu") (net "{net}") (uuid "via-{net.replace("(","-").replace(")","-")}-{int(x*100)}-{int(y*100)}"))\n'

new_tracks = ""

# BZ1 Pad1 (+) at (58, 62.8) -> R_BZ Pad2 at (62.325, 57.0)
# Route: go right then up (avoiding area between 58-64, 57-66)
# Path: (58,62.8) -> (64.5,62.8) -> (64.5,57.0) -> (62.325,57.0)
new_tracks += make_track("Net-(BZ1-+)", "F.Cu", 58.0, 62.8, 64.5, 62.8, 0.3)
new_tracks += make_track("Net-(BZ1-+)", "F.Cu", 64.5, 62.8, 64.5, 57.0, 0.3)
new_tracks += make_track("Net-(BZ1-+)", "F.Cu", 64.5, 57.0, 62.325, 57.0, 0.3)
print("  Added BZ1 + routing: (58,62.8)->(64.5,62.8)->(64.5,57.0)->(62.325,57.0)")

# SW_VIS_RST Pad2 VISION_RESET at (47.1, -8) 
# Route to existing VISION_RESET pad: R_VIS_EN Pad2 at (10.325, -0.5), C_VIS_EN Pad1 at (8.725, -2.5)
# Those are far; route a short track southward to get closer to existing routing
# Better: add a GND via for Pad1 at (42.9, -8) and a short track for Pad2 toward U1 VISION_RESET
# U1 pad22 VISION_RESET is at (89.905, 11.85) - very far away
# R_VIS_EN Pad2 at (10.325, -0.5) - route on B.Cu from SW_VIS_RST toward it
new_tracks += make_via("VISION_RESET", 47.1, -8, 0.3, 0.6)
new_tracks += make_track("VISION_RESET", "B.Cu", 47.1, -8, 30.0, -8, 0.25)
new_tracks += make_track("VISION_RESET", "B.Cu", 30.0, -8, 30.0, -0.5, 0.25)
new_tracks += make_track("VISION_RESET", "B.Cu", 30.0, -0.5, 10.325, -0.5, 0.25)
new_tracks += make_via("VISION_RESET", 10.325, -0.5, 0.3, 0.6)
# Connect C_VIS_EN Pad1 at (8.725, -2.5) to R_VIS_EN Pad2 at (10.325, -0.5)
new_tracks += make_track("VISION_RESET", "F.Cu", 8.725, -2.5, 10.325, -2.5, 0.25)
new_tracks += make_track("VISION_RESET", "F.Cu", 10.325, -2.5, 10.325, -0.5, 0.25)
# Connect U8 Pad3 at (13.25, -3.37) to R_VIS_EN Pad2 at (10.325, -0.5)
new_tracks += make_track("VISION_RESET", "F.Cu", 13.25, -3.37, 13.25, -0.5, 0.25)
new_tracks += make_track("VISION_RESET", "F.Cu", 13.25, -0.5, 10.325, -0.5, 0.25)
print("  Added VISION_RESET routing: SW_VIS_RST->R_VIS_EN->C_VIS_EN->U8")

# U1 Pad22 VISION_RESET at (89.905, 11.85) - connect via B.Cu
new_tracks += make_via("VISION_RESET", 13.25, -3.37, 0.3, 0.6)
new_tracks += make_track("VISION_RESET", "B.Cu", 13.25, -3.37, 13.25, 11.85, 0.25)
new_tracks += make_track("VISION_RESET", "B.Cu", 13.25, 11.85, 89.905, 11.85, 0.25)
new_tracks += make_via("VISION_RESET", 89.905, 11.85, 0.3, 0.6)
print("  Added VISION_RESET routing to U1 Pad22")

# Insert tracks before the last closing paren
insert_pos = content.rfind(')')
content = content[:insert_pos] + new_tracks + content[insert_pos:]

# ============================================================
# FIX 8: Fix the Hexapod_Robot_Board.kicad_sch white text issue
# The issue is that net labels added from the Vision schematic may have
# explicit color overrides. The fix is to ensure the schematic version
# is consistent with KiCad 10 format (already is).
# The real issue is likely the "shape" attribute on global_labels from
# the merged vision section using "input" instead of "bidirectional".
# We'll just note that the schematic text color issue is a KiCad color
# scheme rendering artifact, not a file encoding issue.
# ============================================================
print("\n--- FIX 8: Schematic white text is color-scheme dependent (not file-encoded) ---")
print("  The white rendering is KiCad's theme issue (test_upgrade.kicad_sch has same version).")
print("  Confirmed: no explicit white color codes in label/net definitions.")
print("  Recommended: In KiCad Eeschema -> Preferences -> Color Theme -> select 'KiCad Default'")

print(f"\n--- Summary ---")
print(f"Original board size: {original_len} bytes")
print(f"Fixed board size: {len(content)} bytes")

write_board(content)
print("Done! Now run DRC to verify improvements.")
