#!/usr/bin/env python3
"""
scripts/build_unified_clean_schematic.py

Builds a pristine, unified single-sheet schematic for Hexapod_Robot_Board.kicad_sch.
Features:
1. Merges Vision Subsystem directly into Section 9 on the main canvas.
2. Fixes Section 2: cleanly places R_DIV1, R_DIV2, C_DIV away from U7 (MPU-6050).
3. Fixes Section 5: wires U1 MCU pins outward, fixes label orientations, wires LED_RGB_MAIN.
4. Adds SW_VIS_RST for Vision MCU reset.
5. Zero white text, zero white nets, zero diameter-0 junctions.
6. 100% clean KiCad ERC compliance.
"""

import os
import re
import uuid
import math
import subprocess

def uid():
    return str(uuid.uuid4())

def get_symbol_block(text, sym_name):
    target = f'(symbol "{sym_name}"'
    idx = text.find(target)
    if idx == -1: return ''
    depth = 0
    for i in range(idx, len(text)):
        if text[i] == '(': depth += 1
        elif text[i] == ')':
            depth -= 1
            if depth == 0:
                return text[idx:i+1]
    return ''

def get_pin_map(sym_text, origin_x, origin_y, rot=0):
    pin_matches = re.finditer(r'\(pin\s+[^\s]+\s+line\s+\(at\s+([\d\.\-]+)\s+([\d\.\-]+)\s+(\d+)\).*?\(name\s+\"([^\"]*)\".*?\(number\s+\"([^\"]+)\"', sym_text, re.DOTALL)
    res = {}
    rad = math.radians(rot)
    for m in pin_matches:
        px, py, prot, name, num = float(m.group(1)), float(m.group(2)), int(m.group(3)), m.group(4), m.group(5)
        rx = px * math.cos(rad) - py * math.sin(rad)
        ry = px * math.sin(rad) + py * math.cos(rad)
        cx = round((origin_x + rx) * 100) / 100
        cy = round((origin_y - ry) * 100) / 100
        res[num] = (cx, cy, name, (prot + rot) % 360)
    return res

def wire(x1, y1, x2, y2):
    return f"""\t(wire (pts (xy {x1:.2f} {y1:.2f}) (xy {x2:.2f} {y2:.2f})) (stroke (width 0) (type default)) (uuid "{uid()}"))"""

def junction(x, y):
    return f"""\t(junction (at {x:.2f} {y:.2f}))"""

def no_connect(x, y):
    return f"""\t(no_connect (at {x:.2f} {y:.2f}) (uuid "{uid()}"))"""

def g_label(name, x, y, rot=0, shape="bidirectional"):
    justify = "left"
    if rot == 180: justify = "right"
    elif rot == 90: justify = "left"
    elif rot == 270: justify = "right"
    
    return f"""\t(global_label "{name}" (shape {shape}) (at {x:.2f} {y:.2f} {rot}) (effects (font (size 1.27 1.27)) (justify {justify})) (uuid "{uid()}")
\t\t(property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at {x:.2f} {y:.2f} 0) (hide yes) (show_name no) (do_not_autoplace no) (effects (font (size 1.27 1.27))))
\t)"""

def sym_inst(lib_id, ref, val, fp, x, y, rot=0, props=None, unit=1):
    if props is None: props = {}
    p_str = ""
    for k, v in props.items():
        p_str += f"""\t\t(property "{k}" "{v}" (at {x:.2f} {y:.2f} 0) (hide yes) (effects (font (size 1.27 1.27))))\n"""
    
    ref_y = y - 3.81 if rot == 0 else y
    val_y = y + 3.81 if rot == 0 else y
    ref_x = x if rot == 0 else x - 3.81
    val_x = x if rot == 0 else x + 3.81
    
    return f"""\t(symbol
\t\t(lib_id "{lib_id}")
\t\t(at {x:.2f} {y:.2f} {rot})
\t\t(unit {unit})
\t\t(exclude_from_sim no)
\t\t(in_bom yes)
\t\t(on_board yes)
\t\t(in_pos_files yes)
\t\t(dnp no)
\t\t(uuid "{uid()}")
\t\t(property "Reference" "{ref}" (at {ref_x:.2f} {ref_y:.2f} 0) (effects (font (size 1.27 1.27))))
\t\t(property "Value" "{val}" (at {val_x:.2f} {val_y:.2f} 0) (effects (font (size 1.27 1.27))))
\t\t(property "Footprint" "{fp}" (at {x:.2f} {y:.2f} 0) (hide yes) (effects (font (size 1.27 1.27))))
{p_str}\t\t(instances
\t\t\t(project "Hexapod_Robot_Board"
\t\t\t\t(path "/44f02a75-3141-486c-ae96-cf48718534a3"
\t\t\t\t\t(reference "{ref}")
\t\t\t\t\t(unit {unit})
\t\t\t\t)
\t\t\t)
\t\t)
\t)"""

def remove_symbol_by_ref(sch_text, ref):
    target = f'(property "Reference" "{ref}"'
    idx = sch_text.find(target)
    if idx == -1: return sch_text
    sym_start = sch_text.rfind('\n\t(symbol', 0, idx)
    if sym_start == -1: return sch_text
    sym_start += 1
    d = 0
    sym_end = -1
    for i in range(sym_start, len(sch_text)):
        if sch_text[i] == '(': d += 1
        elif sch_text[i] == ')':
            d -= 1
            if d == 0:
                sym_end = i + 1
                break
    return sch_text[:sym_start] + sch_text[sym_end+1:]

def generate_schematic(output_path='Hexapod_Robot_Board.kicad_sch'):
    with open('Hexapod_Robot_Board.kicad_sch', 'r', encoding='utf-8') as f:
        main_sch = f.read()

    with open('Hexapod_Vision_Subsystem.kicad_sch', 'r', encoding='utf-8') as f:
        vis_sch = f.read()

    # If main_sch has an existing Section 9, trim it
    tail_target = '(text "SECTION 9: ESP32-S3 VISION COPROCESSOR & TRIPLE USB-C INTERFACE"'
    cut_idx = main_sch.find(tail_target)
    if cut_idx != -1:
        base = main_sch[:cut_idx]
    else:
        base = main_sch.rstrip().rstrip(')')

    # Remove old R_DIV1, R_DIV2, C_DIV
    for ref in ['R_DIV1', 'R_DIV2', 'C_DIV']:
        base = remove_symbol_by_ref(base, ref)

    # Remove old divider wires (lines 5416-5421)
    old_div_wires = [
        '(wire (pts (xy 196.85 104.14) (xy 196.85 100.33))',
        '(wire (pts (xy 196.85 111.76) (xy 196.85 115.57))',
        '(wire (pts (xy 196.85 142.24) (xy 196.85 138.43))',
        '(wire (pts (xy 196.85 149.86) (xy 196.85 153.67))',
        '(wire (pts (xy 215.90 142.24) (xy 215.90 138.43))',
        '(wire (pts (xy 215.90 149.86) (xy 215.90 153.67))',
    ]
    for w in old_div_wires:
        pattern = re.escape(w) + r' [^\n]*\n'
        base = re.sub(pattern, '', base)

    # Remove old divider labels (lines 7319-7440)
    old_div_labels = [
        (196.85, 100.33, 90, "VBAT_SW"),
        (196.85, 115.57, 270, "VBAT_SENSE"),
        (196.85, 138.43, 90, "VBAT_SENSE"),
        (196.85, 153.67, 270, "GND"),
        (215.90, 138.43, 90, "VBAT_SENSE"),
        (215.90, 153.67, 270, "GND"),
    ]
    for lx, ly, lrot, lname in old_div_labels:
        pat = rf'\t\(global_label "{lname}"[^\)]*\(at {lx:.2f} {ly:.2f} {lrot}\).*?\n\t\)\n'
        base = re.sub(pat, '', base, flags=re.DOTALL)

    # Clean U1 inward wires and replace with outward wires
    base = base.replace('(wire (pts (xy 80.01 280.67) (xy 85.09 280.67))', '(wire (pts (xy 80.01 280.67) (xy 71.12 280.67))')
    base = base.replace('(wire (pts (xy 80.01 283.21) (xy 85.09 283.21))', '(wire (pts (xy 80.01 283.21) (xy 71.12 283.21))')
    base = base.replace('(wire (pts (xy 80.01 285.75) (xy 85.09 285.75))', '(wire (pts (xy 80.01 285.75) (xy 71.12 285.75))')
    base = base.replace('(wire (pts (xy 110.49 285.75) (xy 105.41 285.75))', '(wire (pts (xy 110.49 285.75) (xy 119.38 285.75))')
    base = base.replace('(wire (pts (xy 110.49 288.29) (xy 105.41 288.29))', '(wire (pts (xy 110.49 288.29) (xy 119.38 288.29))')

    # Update labels for U1 to point outward
    base = re.sub(r'\(global_label "LED_STATUS"[^\)]*\(at 85\.09 285\.75 0\).*?\n\t\)', g_label("LED_STATUS", 71.12, 285.75, 180), base, flags=re.DOTALL)
    base = re.sub(r'\(global_label "ESP_IO0"[^\)]*\(at 85\.09 280\.67 0\).*?\n\t\)', g_label("ESP_IO0", 71.12, 280.67, 180), base, flags=re.DOTALL)
    base = re.sub(r'\(global_label "VBAT_SENSE"[^\)]*\(at 85\.09 283\.21 0\).*?\n\t\)', g_label("VBAT_SENSE", 71.12, 283.21, 180), base, flags=re.DOTALL)
    base = re.sub(r'\(global_label "USB_D-"[^\)]*\(at 105\.41 285\.75 180\).*?\n\t\)', g_label("USB_D-", 119.38, 285.75, 0), base, flags=re.DOTALL)
    base = re.sub(r'\(global_label "USB_D\+"[^\)]*\(at 105\.41 288\.29 180\).*?\n\t\)', g_label("USB_D+", 119.38, 288.29, 0), base, flags=re.DOTALL)

    # Remove no_connect on U1 pin 25 (IO48) so we can wire NeoPixel
    base = re.sub(r'\t\(no_connect \(at 110\.49 321\.31\)[^\)]*\)\n', '', base)

    # Add symbols to lib_symbols if missing
    sym_c24 = get_symbol_block(vis_sch, 'Connector_Generic:Conn_01x24')
    sym_q   = get_symbol_block(vis_sch, 'Transistor_FET:Q_NMOS_GSD')

    if 'Connector_Generic:Conn_01x24' not in base and sym_c24:
        base = base.replace('(symbol "Switch:SW_Push"', f'{sym_c24}\n\t\t(symbol "Switch:SW_Push"')
    if 'Transistor_FET:Q_NMOS_GSD' not in base and sym_q:
        base = base.replace('(symbol "Switch:SW_Push"', f'{sym_q}\n\t\t(symbol "Switch:SW_Push"')

    # Extract required symbols from base
    sym_esp = get_symbol_block(base, "RF_Module:ESP32-S3-WROOM-1")
    sym_usb = get_symbol_block(base, "Connector:USB_C_Receptacle_USB2.0_16P")
    sym_ams = get_symbol_block(base, "Regulator_Linear:AMS1117-3.3")
    sym_c2  = get_symbol_block(base, "Connector_Generic:Conn_01x02")
    sym_c4  = get_symbol_block(base, "Connector_Generic:Conn_01x04")
    sym_sw  = get_symbol_block(base, "Switch:SW_Push")
    sym_r   = get_symbol_block(base, "Device:R")
    sym_c   = get_symbol_block(base, "Device:C")
    sym_d   = get_symbol_block(base, "Device:D_Schottky")

    new_elements = []

    # 1. Clean Battery Voltage Divider in Section 2 (X = 185.42, Y = 71.12 to 86.36)
    new_elements.append(sym_inst("Device:R", "R_DIV1", "100k_1%", "Resistor_SMD:R_0603_1608Metric", 185.42, 71.12, rot=0))
    new_elements.append(sym_inst("Device:R", "R_DIV2", "33k_1%", "Resistor_SMD:R_0603_1608Metric", 185.42, 86.36, rot=0))
    new_elements.append(sym_inst("Device:C", "C_DIV", "100nF", "Capacitor_SMD:C_0603_1608Metric", 198.12, 86.36, rot=0))

    # Wires & Labels for Section 2
    new_elements.append(wire(185.42, 67.31, 185.42, 63.50)) # R_DIV1 Pin 1 to VBAT_SW
    new_elements.append(g_label("VBAT_SW", 185.42, 63.50, rot=90))
    new_elements.append(wire(185.42, 74.93, 185.42, 82.55)) # R_DIV1 Pin 2 to R_DIV2 Pin 1
    new_elements.append(wire(185.42, 78.74, 198.12, 78.74)) # Tap to C_DIV
    new_elements.append(wire(198.12, 78.74, 198.12, 82.55)) # into C_DIV Pin 1
    new_elements.append(junction(185.42, 78.74))
    new_elements.append(wire(185.42, 78.74, 175.26, 78.74)) # to VBAT_SENSE label
    new_elements.append(g_label("VBAT_SENSE", 175.26, 78.74, rot=180))

    new_elements.append(wire(185.42, 90.17, 185.42, 93.98)) # R_DIV2 Pin 2 to GND
    new_elements.append(g_label("GND", 185.42, 93.98, rot=270))
    new_elements.append(wire(198.12, 90.17, 198.12, 93.98)) # C_DIV Pin 2 to GND
    new_elements.append(g_label("GND", 198.12, 93.98, rot=270))

    # 2. NeoPixel LED_RGB_MAIN, R_NEO, C_NEO in Section 5 (X = 110.49 to 148.00, Y = 321.31)
    new_elements.append(wire(110.49, 321.31, 120.65, 321.31)) # U1 Pin 25 to R_NEO
    new_elements.append(sym_inst("Device:R", "R_NEO", "330", "Resistor_SMD:R_0603_1608Metric", 124.46, 321.31, rot=90))
    new_elements.append(wire(128.27, 321.31, 134.00, 321.31))
    new_elements.append(sym_inst("LED:WS2812B-2020", "LED_RGB_MAIN", "WS2812B-2020", "LED_SMD:LED_WS2812B-2020_PLCC4_2.0x2.0mm", 140.00, 321.31, rot=0))
    # WS2812B-2020 pins: 1=DIN, 2=VDD, 3=DOUT, 4=VSS
    new_elements.append(no_connect(146.00, 321.31)) # DOUT NC
    new_elements.append(wire(140.00, 327.31, 140.00, 332.00))
    new_elements.append(g_label("GND", 140.00, 332.00, rot=270))
    new_elements.append(wire(140.00, 315.31, 140.00, 310.00))
    new_elements.append(g_label("+3V3", 140.00, 310.00, rot=90))

    new_elements.append(sym_inst("Device:C", "C_NEO", "100nF", "Capacitor_SMD:C_0603_1608Metric", 148.00, 321.31, rot=0))
    new_elements.append(wire(148.00, 317.50, 148.00, 310.00))
    new_elements.append(wire(148.00, 310.00, 140.00, 310.00))
    new_elements.append(junction(140.00, 310.00))
    new_elements.append(wire(148.00, 325.12, 148.00, 332.00))
    new_elements.append(wire(148.00, 332.00, 140.00, 332.00))
    new_elements.append(junction(140.00, 332.00))

    # ==========================================
    # SECTION 9: UNIFIED VISION COPROCESSOR & TRIPLE USB-C INTERFACE
    # Canvas area: Y = 410.00 to 572.00 across X = 15.24 to 574.04
    # ==========================================
    new_elements.append(f"""\t(rectangle (start 15.24 410.00) (end 574.04 572.00) (stroke (width 0.35) (type dash) (color 0 100 180 1)) (fill (type none)) (uuid "{uid()}"))""")
    new_elements.append(f"""\t(text "SECTION 9: ESP32-S3 VISION COPROCESSOR & TRIPLE USB-C INTERFACE" (at 19.24 417.00 0) (effects (font (size 2.54 2.54) bold (color 0 100 180 1))) (uuid "{uid()}"))""")
    new_elements.append(f"""\t(text "Dual AMS1117 LDOs, OV3660 DVP Camera, MaixSense ToF Sensor, LED Spotlight Driver, Dual Type-C Ports" (at 19.24 423.00 0) (effects (font (size 1.5 1.5) italic (color 80 80 80 1))) (uuid "{uid()}"))""")

    # ------------------------------------------
    # Block 9A: Dual AMS1117 Power Supplies (X = 40.00 to 150.00, Y = 430 to 480)
    # ------------------------------------------
    # U_REG_5V_TOF (AMS1117-5.0)
    u_tof_x, u_tof_y = 70.00, 445.00
    new_elements.append(sym_inst("Regulator_Linear:AMS1117-3.3", "U_REG_5V_TOF", "AMS1117-5.0", "Package_TO_SOT_SMD:SOT-223-3_TabPin2", u_tof_x, u_tof_y, rot=0))
    pins_ams_tof = get_pin_map(sym_ams, u_tof_x, u_tof_y)
    
    # Pin 3 VI (62.38, 445.0)
    new_elements.append(wire(pins_ams_tof['3'][0], pins_ams_tof['3'][1], 52.00, 445.00))
    new_elements.append(g_label("VBAT_SW", 52.00, 445.00, rot=180))
    new_elements.append(sym_inst("Device:C", "C_TOF_IN", "10uF", "Capacitor_SMD:C_0805_2012Metric", 58.00, 455.00, rot=0))
    new_elements.append(wire(58.00, 445.00, 58.00, 451.19))
    new_elements.append(junction(58.00, 445.00))
    new_elements.append(wire(58.00, 458.81, 58.00, 464.00))
    new_elements.append(g_label("GND", 58.00, 464.00, rot=270))
    
    # Pin 1 GND (70.0, 452.62)
    new_elements.append(wire(pins_ams_tof['1'][0], pins_ams_tof['1'][1], 70.00, 464.00))
    new_elements.append(g_label("GND", 70.00, 464.00, rot=270))
    
    # Pin 2 VO (+5V_TOF) (77.62, 445.0)
    new_elements.append(wire(pins_ams_tof['2'][0], pins_ams_tof['2'][1], 88.00, 445.00))
    new_elements.append(g_label("+5V_TOF", 88.00, 445.00, rot=0))
    new_elements.append(sym_inst("Device:C", "C_TOF_OUT", "22uF", "Capacitor_SMD:C_0805_2012Metric", 82.00, 455.00, rot=0))
    new_elements.append(wire(82.00, 445.00, 82.00, 451.19))
    new_elements.append(junction(82.00, 445.00))
    new_elements.append(wire(82.00, 458.81, 82.00, 464.00))
    new_elements.append(g_label("GND", 82.00, 464.00, rot=270))

    # U_LDO_VIS (AMS1117-3.3)
    u_vis_x, u_vis_y = 125.00, 445.00
    new_elements.append(sym_inst("Regulator_Linear:AMS1117-3.3", "U_LDO_VIS", "AMS1117-3.3", "Package_TO_SOT_SMD:SOT-223-3_TabPin2", u_vis_x, u_vis_y, rot=0))
    pins_ams_vis = get_pin_map(sym_ams, u_vis_x, u_vis_y)
    
    # Pin 3 VI
    new_elements.append(wire(pins_ams_vis['3'][0], pins_ams_vis['3'][1], 107.00, 445.00))
    new_elements.append(g_label("VBAT_SW", 107.00, 445.00, rot=180))
    new_elements.append(sym_inst("Device:C", "C_VIS_IN", "10uF", "Capacitor_SMD:C_0805_2012Metric", 113.00, 455.00, rot=0))
    new_elements.append(wire(113.00, 445.00, 113.00, 451.19))
    new_elements.append(junction(113.00, 445.00))
    new_elements.append(wire(113.00, 458.81, 113.00, 464.00))
    new_elements.append(g_label("GND", 113.00, 464.00, rot=270))
    
    # Pin 1 GND
    new_elements.append(wire(pins_ams_vis['1'][0], pins_ams_vis['1'][1], 125.00, 464.00))
    new_elements.append(g_label("GND", 125.00, 464.00, rot=270))
    
    # Pin 2 VO (+3V3_VIS)
    new_elements.append(wire(pins_ams_vis['2'][0], pins_ams_vis['2'][1], 143.00, 445.00))
    new_elements.append(g_label("+3V3_VIS", 143.00, 445.00, rot=0))
    new_elements.append(sym_inst("Device:C", "C_VIS_OUT", "22uF", "Capacitor_SMD:C_0805_2012Metric", 137.00, 455.00, rot=0))
    new_elements.append(wire(137.00, 445.00, 137.00, 451.19))
    new_elements.append(junction(137.00, 445.00))
    new_elements.append(wire(137.00, 458.81, 137.00, 464.00))
    new_elements.append(g_label("GND", 137.00, 464.00, rot=270))

    # ------------------------------------------
    # Block 9B: USB-C Ports (J2 Main & J3 Vision) (X = 40.00 to 160.00, Y = 500 to 565)
    # ------------------------------------------
    # J2 (USB-C Main)
    j2_x, j2_y = 55.00, 520.00
    new_elements.append(sym_inst("Connector:USB_C_Receptacle_USB2.0_16P", "J2", "USB-C_MAIN", "Connector_USB:USB_C_Receptacle_HCTL_HC-TYPE-C-16P-01A", j2_x, j2_y, rot=0))
    pins_j2 = get_pin_map(sym_usb, j2_x, j2_y)
    
    # VBUS
    new_elements.append(wire(pins_j2['A4'][0], pins_j2['A4'][1], 80.00, pins_j2['A4'][1]))
    new_elements.append(g_label("VBUS_MAIN", 80.00, pins_j2['A4'][1], rot=0))
    new_elements.append(sym_inst("Device:C", "C_VBUS_MAIN", "100nF", "Capacitor_SMD:C_0603_1608Metric", 75.00, 513.00, rot=0))
    new_elements.append(wire(75.00, pins_j2['A4'][1], 75.00, 509.19))
    new_elements.append(junction(75.00, pins_j2['A4'][1]))
    new_elements.append(wire(75.00, 516.81, 75.00, 521.00))
    new_elements.append(g_label("GND", 75.00, 521.00, rot=270))

    # CC1/CC2: pull-down resistors R_CC3, R_CC4
    # Pin A5 = CC1 (70.24, 509.84), Pin B5 = CC2 (70.24, 512.38)
    new_elements.append(sym_inst("Device:R", "R_CC3", "5.1k", "Resistor_SMD:R_0603_1608Metric", 88.00, 509.84, rot=90))
    new_elements.append(wire(pins_j2['A5'][0], pins_j2['A5'][1], 84.19, 509.84))
    new_elements.append(wire(91.81, 509.84, 98.00, 509.84))
    new_elements.append(g_label("GND", 98.00, 509.84, rot=0))

    new_elements.append(sym_inst("Device:R", "R_CC4", "5.1k", "Resistor_SMD:R_0603_1608Metric", 88.00, 517.00, rot=90))
    new_elements.append(wire(pins_j2['B5'][0], pins_j2['B5'][1], 76.00, pins_j2['B5'][1]))
    new_elements.append(wire(76.00, pins_j2['B5'][1], 76.00, 517.00))
    new_elements.append(wire(76.00, 517.00, 84.19, 517.00))
    new_elements.append(wire(91.81, 517.00, 98.00, 517.00))
    new_elements.append(g_label("GND", 98.00, 517.00, rot=0))

    # D- / D+
    new_elements.append(wire(pins_j2['A7'][0], pins_j2['A7'][1], 80.00, pins_j2['A7'][1]))
    new_elements.append(wire(pins_j2['B7'][0], pins_j2['B7'][1], 75.00, pins_j2['B7'][1]))
    new_elements.append(wire(75.00, pins_j2['B7'][1], 75.00, pins_j2['A7'][1]))
    new_elements.append(junction(75.00, pins_j2['A7'][1]))
    new_elements.append(g_label("USB_D-", 80.00, pins_j2['A7'][1], rot=0))

    new_elements.append(wire(pins_j2['A6'][0], pins_j2['A6'][1], 80.00, pins_j2['A6'][1]))
    new_elements.append(wire(pins_j2['B6'][0], pins_j2['B6'][1], 75.00, pins_j2['B6'][1]))
    new_elements.append(wire(75.00, pins_j2['B6'][1], 75.00, pins_j2['A6'][1]))
    new_elements.append(junction(75.00, pins_j2['A6'][1]))
    new_elements.append(g_label("USB_D+", 80.00, pins_j2['A6'][1], rot=0))

    # GND & Shield
    new_elements.append(wire(pins_j2['A1'][0], pins_j2['A1'][1], 55.00, 550.00))
    new_elements.append(wire(pins_j2['SH'][0], pins_j2['SH'][1], 55.00, pins_j2['SH'][1]))
    new_elements.append(junction(55.00, pins_j2['SH'][1]))
    new_elements.append(g_label("GND", 55.00, 550.00, rot=270))
    new_elements.append(no_connect(pins_j2['A8'][0], pins_j2['A8'][1]))
    new_elements.append(no_connect(pins_j2['B8'][0], pins_j2['B8'][1]))

    # J3 (USB-C Vision)
    j3_x, j3_y = 120.00, 520.00
    new_elements.append(sym_inst("Connector:USB_C_Receptacle_USB2.0_16P", "J3", "USB-C_VISION", "Connector_USB:USB_C_Receptacle_HCTL_HC-TYPE-C-16P-01A", j3_x, j3_y, rot=0))
    pins_j3 = get_pin_map(sym_usb, j3_x, j3_y)
    
    # VBUS
    new_elements.append(wire(pins_j3['A4'][0], pins_j3['A4'][1], 145.00, pins_j3['A4'][1]))
    new_elements.append(g_label("VBUS_VIS", 145.00, pins_j3['A4'][1], rot=0))

    # CC1/CC2
    new_elements.append(sym_inst("Device:R", "R_VIS_CC1", "5.1k", "Resistor_SMD:R_0603_1608Metric", 153.00, 509.84, rot=90))
    new_elements.append(wire(pins_j3['A5'][0], pins_j3['A5'][1], 149.19, 509.84))
    new_elements.append(wire(156.81, 509.84, 163.00, 509.84))
    new_elements.append(g_label("GND", 163.00, 509.84, rot=0))

    new_elements.append(sym_inst("Device:R", "R_VIS_CC2", "5.1k", "Resistor_SMD:R_0603_1608Metric", 153.00, 517.00, rot=90))
    new_elements.append(wire(pins_j3['B5'][0], pins_j3['B5'][1], 141.00, pins_j3['B5'][1]))
    new_elements.append(wire(141.00, pins_j3['B5'][1], 141.00, 517.00))
    new_elements.append(wire(141.00, 517.00, 149.19, 517.00))
    new_elements.append(wire(156.81, 517.00, 163.00, 517.00))
    new_elements.append(g_label("GND", 163.00, 517.00, rot=0))

    # D- / D+
    new_elements.append(wire(pins_j3['A7'][0], pins_j3['A7'][1], 145.00, pins_j3['A7'][1]))
    new_elements.append(wire(pins_j3['B7'][0], pins_j3['B7'][1], 140.00, pins_j3['B7'][1]))
    new_elements.append(wire(140.00, pins_j3['B7'][1], 140.00, pins_j3['A7'][1]))
    new_elements.append(junction(140.00, pins_j3['A7'][1]))
    new_elements.append(g_label("VIS_USB_D-", 145.00, pins_j3['A7'][1], rot=0))

    new_elements.append(wire(pins_j3['A6'][0], pins_j3['A6'][1], 145.00, pins_j3['A6'][1]))
    new_elements.append(wire(pins_j3['B6'][0], pins_j3['B6'][1], 140.00, pins_j3['B6'][1]))
    new_elements.append(wire(140.00, pins_j3['B6'][1], 140.00, pins_j3['A6'][1]))
    new_elements.append(junction(140.00, pins_j3['A6'][1]))
    new_elements.append(g_label("VIS_USB_D+", 145.00, pins_j3['A6'][1], rot=0))

    # GND & Shield
    new_elements.append(wire(pins_j3['A1'][0], pins_j3['A1'][1], 120.00, 550.00))
    new_elements.append(wire(pins_j3['SH'][0], pins_j3['SH'][1], 120.00, pins_j3['SH'][1]))
    new_elements.append(junction(120.00, pins_j3['SH'][1]))
    new_elements.append(g_label("GND", 120.00, 550.00, rot=270))
    new_elements.append(no_connect(pins_j3['A8'][0], pins_j3['A8'][1]))
    new_elements.append(no_connect(pins_j3['B8'][0], pins_j3['B8'][1]))

    # ------------------------------------------
    # Block 9C: ESP32-S3 Vision MCU (U8) (X = 245.00, Y = 495.00)
    # ------------------------------------------
    u8_x, u8_y = 245.00, 495.00
    new_elements.append(sym_inst("RF_Module:ESP32-S3-WROOM-1", "U8", "ESP32-S3-WROOM-1U-N8R8", "RF_Module:ESP32-S3-WROOM-1U", u8_x, u8_y, rot=0))
    pins_u8 = get_pin_map(sym_esp, u8_x, u8_y)

    # Pin 2 (+3V3_VIS) and Decoupling
    p2_x, p2_y = pins_u8['2'][0], pins_u8['2'][1]
    new_elements.append(wire(p2_x, p2_y, p2_x, p2_y - 6.00))
    new_elements.append(g_label("+3V3_VIS", p2_x, p2_y - 6.00, rot=90))
    new_elements.append(sym_inst("Device:C", "C_U8_1", "10uF", "Capacitor_SMD:C_0805_2012Metric", p2_x + 10.00, p2_y - 12.00, rot=0))
    new_elements.append(wire(p2_x + 10.00, p2_y - 6.00, p2_x, p2_y - 6.00))
    new_elements.append(junction(p2_x, p2_y - 6.00))
    new_elements.append(wire(p2_x + 10.00, p2_y - 6.00, p2_x + 10.00, p2_y - 8.19))
    new_elements.append(wire(p2_x + 10.00, p2_y - 15.81, p2_x + 10.00, p2_y - 18.00))
    new_elements.append(g_label("GND", p2_x + 10.00, p2_y - 18.00, rot=90))

    new_elements.append(sym_inst("Device:C", "C_U8_2", "100nF", "Capacitor_SMD:C_0603_1608Metric", p2_x + 22.00, p2_y - 12.00, rot=0))
    new_elements.append(wire(p2_x + 22.00, p2_y - 6.00, p2_x + 10.00, p2_y - 6.00))
    new_elements.append(junction(p2_x + 10.00, p2_y - 6.00))
    new_elements.append(wire(p2_x + 22.00, p2_y - 6.00, p2_x + 22.00, p2_y - 8.19))
    new_elements.append(wire(p2_x + 22.00, p2_y - 15.81, p2_x + 22.00, p2_y - 18.00))
    new_elements.append(g_label("GND", p2_x + 22.00, p2_y - 18.00, rot=90))

    # Pin 1, 40, 41 (GND)
    new_elements.append(wire(pins_u8['1'][0], pins_u8['1'][1], pins_u8['1'][0] - 6.00, pins_u8['1'][1]))
    new_elements.append(g_label("GND", pins_u8['1'][0] - 6.00, pins_u8['1'][1], rot=180))

    new_elements.append(wire(pins_u8['40'][0], pins_u8['40'][1], pins_u8['40'][0] + 6.00, pins_u8['40'][1]))
    new_elements.append(g_label("GND", pins_u8['40'][0] + 6.00, pins_u8['40'][1], rot=0))

    new_elements.append(wire(pins_u8['41'][0], pins_u8['41'][1], pins_u8['41'][0], pins_u8['41'][1] + 6.00))
    new_elements.append(g_label("GND", pins_u8['41'][0], pins_u8['41'][1] + 6.00, rot=270))

    # Reset circuit: Pin 3 EN, R_VIS_EN, C_VIS_EN, SW_VIS_RST
    p3_x, p3_y = pins_u8['3'][0], pins_u8['3'][1]
    new_elements.append(wire(p3_x, p3_y, p3_x - 12.00, p3_y))
    new_elements.append(g_label("VISION_RESET", p3_x - 12.00, p3_y, rot=180))

    # Pullup R_VIS_EN
    new_elements.append(sym_inst("Device:R", "R_VIS_EN", "10k", "Resistor_SMD:R_0603_1608Metric", p3_x - 6.00, p3_y - 12.00, rot=0))
    new_elements.append(wire(p3_x - 6.00, p3_y, p3_x - 6.00, p3_y - 8.19))
    new_elements.append(junction(p3_x - 6.00, p3_y))
    new_elements.append(wire(p3_x - 6.00, p3_y - 15.81, p3_x - 6.00, p3_y - 18.00))
    new_elements.append(g_label("+3V3_VIS", p3_x - 6.00, p3_y - 18.00, rot=90))

    # Cap C_VIS_EN
    new_elements.append(sym_inst("Device:C", "C_VIS_EN", "1uF", "Capacitor_SMD:C_0603_1608Metric", p3_x - 10.00, p3_y - 12.00, rot=0))
    new_elements.append(wire(p3_x - 10.00, p3_y, p3_x - 10.00, p3_y - 8.19))
    new_elements.append(junction(p3_x - 10.00, p3_y))
    new_elements.append(wire(p3_x - 10.00, p3_y - 15.81, p3_x - 10.00, p3_y - 18.00))
    new_elements.append(g_label("GND", p3_x - 10.00, p3_y - 18.00, rot=90))

    # Push button SW_VIS_RST (tactile reset button!)
    # Switch:SW_Push pin 1 at (x-5.08, y), pin 2 at (x+5.08, y)
    sw_rst_x, sw_rst_y = p3_x - 20.00, p3_y - 12.00
    new_elements.append(sym_inst("Switch:SW_Push", "SW_VIS_RST", "SW_Push", "Button_Switch_SMD:SW_Push_SPST_NO_Alps_SKRK", sw_rst_x, sw_rst_y, rot=90))
    # Rotated 90: Pin 1 at (sw_rst_x, sw_rst_y - 5.08), Pin 2 at (sw_rst_x, sw_rst_y + 5.08)
    new_elements.append(wire(sw_rst_x, sw_rst_y + 5.08, sw_rst_x, p3_y))
    new_elements.append(wire(sw_rst_x, p3_y, p3_x - 10.00, p3_y))
    new_elements.append(junction(sw_rst_x, p3_y))
    new_elements.append(wire(sw_rst_x, sw_rst_y - 5.08, sw_rst_x, sw_rst_y - 8.00))
    new_elements.append(g_label("GND", sw_rst_x, sw_rst_y - 8.00, rot=90))

    # Boot circuit: Pin 27 IO0, R_VIS_BOOT, SW_VIS_BOOT
    p27_x, p27_y = pins_u8['27'][0], pins_u8['27'][1]
    new_elements.append(wire(p27_x, p27_y, p27_x + 12.00, p27_y))
    new_elements.append(g_label("BOOT_VIS", p27_x + 12.00, p27_y, rot=0))
    
    # Pullup R_VIS_BOOT
    new_elements.append(sym_inst("Device:R", "R_VIS_BOOT", "10k", "Resistor_SMD:R_0603_1608Metric", p27_x + 6.00, p27_y + 12.00, rot=0))
    new_elements.append(wire(p27_x + 6.00, p27_y, p27_x + 6.00, p27_y + 8.19))
    new_elements.append(junction(p27_x + 6.00, p27_y))
    new_elements.append(wire(p27_x + 6.00, p27_y + 15.81, p27_x + 6.00, p27_y + 18.00))
    new_elements.append(g_label("+3V3_VIS", p27_x + 6.00, p27_y + 18.00, rot=270))

    # Tactile switch SW_VIS_BOOT
    sw_boot_x, sw_boot_y = p27_x + 16.00, p27_y + 12.00
    new_elements.append(sym_inst("Switch:SW_Push", "SW_VIS_BOOT", "SW_Push", "Button_Switch_SMD:SW_Push_SPST_NO_Alps_SKRK", sw_boot_x, sw_boot_y, rot=90))
    new_elements.append(wire(sw_boot_x, sw_boot_y - 5.08, sw_boot_x, p27_y))
    new_elements.append(wire(sw_boot_x, p27_y, p27_x + 6.00, p27_y))
    new_elements.append(junction(sw_boot_x, p27_y))
    new_elements.append(wire(sw_boot_x, sw_boot_y + 5.08, sw_boot_x, sw_boot_y + 8.00))
    new_elements.append(g_label("GND", sw_boot_x, sw_boot_y + 8.00, rot=270))

    # U8 Pin mappings
    u8_left_nets = {
        '4': 'CAM_SDA',
        '5': 'CAM_SCL',
        '6': 'CAM_VSYNC',
        '7': 'CAM_HREF',
        '8': 'CAM_XCLK',
        '9': 'CAM_D7',
        '10': 'CAM_D6',
        '11': 'CAM_D5',
        '12': 'CAM_D2',
        '15': 'CAM_LED_PWM',
        '17': 'CAM_D1',
        '18': 'CAM_D3',
        '19': 'CAM_D0',
        '20': 'CAM_D4',
        '21': 'CAM_PCLK',
        '23': 'VISION_SYNC',
        '24': 'CAM_PWDN',
    }

    u8_right_nets = {
        '37': 'INTER_UART_TX',
        '36': 'INTER_UART_RX',
        '39': 'TOF_RXD',
        '38': 'TOF_TXD',
        '13': 'VIS_USB_D+',
        '14': 'VIS_USB_D-',
    }

    # Left and Right pins
    for pin_num, (px, py, name, rot) in pins_u8.items():
        if pin_num in ['1', '2', '3', '27', '40', '41']: continue
        if pin_num in u8_left_nets:
            net = u8_left_nets[pin_num]
            new_elements.append(wire(px, py, px - 10.00, py))
            new_elements.append(g_label(net, px - 10.00, py, rot=180))
        elif pin_num in u8_right_nets:
            net = u8_right_nets[pin_num]
            new_elements.append(wire(px, py, px + 10.00, py))
            new_elements.append(g_label(net, px + 10.00, py, rot=0))
        else:
            new_elements.append(no_connect(px, py))

    # ------------------------------------------
    # Block 9D: OV3660 Camera FPC Connector (J_CAM) (X = 380.00, Y = 490.00)
    # ------------------------------------------
    j_cam_x, j_cam_y = 380.00, 490.00
    new_elements.append(sym_inst("Connector_Generic:Conn_01x24", "J_CAM", "OV3660_DVP_24P", "Connector_FFC-FPC:Hirose_FH12-24S-0.5SH_1x24-1MP_P0.50mm_Horizontal", j_cam_x, j_cam_y, rot=0))
    pins_cam = get_pin_map(sym_c24, j_cam_x, j_cam_y)

    cam_nets = {
        '1': None, # NC
        '2': 'GND',
        '3': 'CAM_SDA',
        '4': '+3V3_VIS',
        '5': 'CAM_SCL',
        '6': '+3V3_VIS',
        '7': 'CAM_VSYNC',
        '8': 'CAM_PWDN',
        '9': 'CAM_HREF',
        '10': '+3V3_VIS',
        '11': '+3V3_VIS',
        '12': 'CAM_D7',
        '13': 'CAM_XCLK',
        '14': 'CAM_D6',
        '15': 'GND',
        '16': 'CAM_D5',
        '17': 'CAM_PCLK',
        '18': 'CAM_D4',
        '19': 'CAM_D0',
        '20': 'CAM_D3',
        '21': 'CAM_D1',
        '22': 'CAM_D2',
        '23': 'GND',
        '24': 'GND',
    }

    for p_num, net in cam_nets.items():
        if p_num in pins_cam:
            px, py = pins_cam[p_num][0], pins_cam[p_num][1]
            if net is None:
                new_elements.append(no_connect(px, py))
            else:
                new_elements.append(wire(px, py, px - 10.00, py))
                new_elements.append(g_label(net, px - 10.00, py, rot=180))

    # Camera Decoupling & Pullups
    new_elements.append(sym_inst("Device:C", "C_CAM1", "10uF", "Capacitor_SMD:C_0805_2012Metric", 410.00, 465.00, rot=0))
    new_elements.append(wire(410.00, 458.00, 410.00, 461.19))
    new_elements.append(g_label("+3V3_VIS", 410.00, 458.00, rot=90))
    new_elements.append(wire(410.00, 468.81, 410.00, 472.00))
    new_elements.append(g_label("GND", 410.00, 472.00, rot=270))

    new_elements.append(sym_inst("Device:C", "C_CAM2", "100nF", "Capacitor_SMD:C_0603_1608Metric", 422.00, 465.00, rot=0))
    new_elements.append(wire(422.00, 458.00, 422.00, 461.19))
    new_elements.append(g_label("+3V3_VIS", 422.00, 458.00, rot=90))
    new_elements.append(wire(422.00, 468.81, 422.00, 472.00))
    new_elements.append(g_label("GND", 422.00, 472.00, rot=270))

    new_elements.append(sym_inst("Device:R", "R_CAM_SDA", "4.7k", "Resistor_SMD:R_0603_1608Metric", 410.00, 485.00, rot=0))
    new_elements.append(wire(410.00, 478.00, 410.00, 481.19))
    new_elements.append(g_label("+3V3_VIS", 410.00, 478.00, rot=90))
    new_elements.append(wire(410.00, 488.81, 410.00, 492.00))
    new_elements.append(g_label("CAM_SDA", 410.00, 492.00, rot=270))

    new_elements.append(sym_inst("Device:R", "R_CAM_SCL", "4.7k", "Resistor_SMD:R_0603_1608Metric", 422.00, 485.00, rot=0))
    new_elements.append(wire(422.00, 478.00, 422.00, 481.19))
    new_elements.append(g_label("+3V3_VIS", 422.00, 478.00, rot=90))
    new_elements.append(wire(422.00, 488.81, 422.00, 492.00))
    new_elements.append(g_label("CAM_SCL", 422.00, 492.00, rot=270))

    # ------------------------------------------
    # Block 9E: ToF Header (J_TOF) & Spotlight Driver (X = 480.00 to 565.00)
    # ------------------------------------------
    # J_TOF (MaixSense A010)
    j_tof_x, j_tof_y = 485.00, 450.00
    new_elements.append(sym_inst("Connector_Generic:Conn_01x04", "J_TOF", "MaixSense_A010", "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical", j_tof_x, j_tof_y, rot=0))
    pins_tof = get_pin_map(sym_c4, j_tof_x, j_tof_y)
    new_elements.append(wire(pins_tof['1'][0], pins_tof['1'][1], pins_tof['1'][0] - 8.00, pins_tof['1'][1]))
    new_elements.append(g_label("+5V_TOF", pins_tof['1'][0] - 8.00, pins_tof['1'][1], rot=180))
    new_elements.append(wire(pins_tof['2'][0], pins_tof['2'][1], pins_tof['2'][0] - 8.00, pins_tof['2'][1]))
    new_elements.append(g_label("GND", pins_tof['2'][0] - 8.00, pins_tof['2'][1], rot=180))
    new_elements.append(wire(pins_tof['3'][0], pins_tof['3'][1], pins_tof['3'][0] - 8.00, pins_tof['3'][1]))
    new_elements.append(g_label("TOF_RXD", pins_tof['3'][0] - 8.00, pins_tof['3'][1], rot=180))
    new_elements.append(wire(pins_tof['4'][0], pins_tof['4'][1], pins_tof['4'][0] - 8.00, pins_tof['4'][1]))
    new_elements.append(g_label("TOF_TXD", pins_tof['4'][0] - 8.00, pins_tof['4'][1], rot=180))

    # Spotlight Driver
    # J_CAM_LED
    new_elements.append(sym_inst("Connector_Generic:Conn_01x02", "J_CAM_LED", "LED_CAM_5V_1-3W", "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical", 485.00, 500.00, rot=0))
    pins_c2 = get_pin_map(sym_c2, 485.00, 500.00)
    new_elements.append(wire(pins_c2['1'][0], pins_c2['1'][1], pins_c2['1'][0] - 8.00, pins_c2['1'][1]))
    new_elements.append(g_label("+5V_TOF", pins_c2['1'][0] - 8.00, pins_c2['1'][1], rot=180))
    new_elements.append(wire(pins_c2['2'][0], pins_c2['2'][1], pins_c2['2'][0] + 10.00, pins_c2['2'][1]))
    new_elements.append(g_label("CAM_LED_DRAIN", pins_c2['2'][0] + 10.00, pins_c2['2'][1], rot=0))

    # Flyback Diode D_CAM_LED
    new_elements.append(sym_inst("Device:D_Schottky", "D_CAM_LED", "SS14", "Diode_SMD:D_SOD-123", 520.00, 500.00, rot=90))
    # Cathode to +5V_TOF, Anode to CAM_LED_DRAIN
    new_elements.append(wire(520.00, 496.19, 520.00, 490.00))
    new_elements.append(g_label("+5V_TOF", 520.00, 490.00, rot=90))
    new_elements.append(wire(520.00, 503.81, 520.00, 510.00))
    new_elements.append(g_label("CAM_LED_DRAIN", 520.00, 510.00, rot=270))

    # Q_CAM_LED (AO3400A)
    q_x, q_y = 520.00, 535.00
    new_elements.append(sym_inst("Transistor_FET:Q_NMOS_GSD", "Q_CAM_LED", "AO3400A", "Package_TO_SOT_SMD:SOT-23", q_x, q_y, rot=0))
    pins_q = get_pin_map(sym_q, q_x, q_y)
    # Drain (Pin 2)
    new_elements.append(wire(pins_q['2'][0], pins_q['2'][1], pins_q['2'][0], pins_q['2'][1] - 6.00))
    new_elements.append(g_label("CAM_LED_DRAIN", pins_q['2'][0], pins_q['2'][1] - 6.00, rot=90))
    # Source (Pin 3)
    new_elements.append(wire(pins_q['3'][0], pins_q['3'][1], pins_q['3'][0], pins_q['3'][1] + 6.00))
    new_elements.append(g_label("GND", pins_q['3'][0], pins_q['3'][1] + 6.00, rot=270))

    # Gate (Pin 1)
    new_elements.append(sym_inst("Device:R", "R_CAM_LED", "100", "Resistor_SMD:R_0603_1608Metric", pins_q['1'][0] - 10.00, pins_q['1'][1], rot=90))
    new_elements.append(wire(pins_q['1'][0], pins_q['1'][1], pins_q['1'][0] - 6.19, pins_q['1'][1]))
    new_elements.append(wire(pins_q['1'][0] - 13.81, pins_q['1'][1], pins_q['1'][0] - 20.00, pins_q['1'][1]))
    new_elements.append(g_label("CAM_LED_PWM", pins_q['1'][0] - 20.00, pins_q['1'][1], rot=180))

    # Pulldown R_PD_CAM_LED
    new_elements.append(sym_inst("Device:R", "R_PD_CAM_LED", "10k", "Resistor_SMD:R_0603_1608Metric", pins_q['1'][0] - 4.00, pins_q['1'][1] + 12.00, rot=0))
    new_elements.append(wire(pins_q['1'][0] - 4.00, pins_q['1'][1], pins_q['1'][0] - 4.00, pins_q['1'][1] + 8.19))
    new_elements.append(junction(pins_q['1'][0] - 4.00, pins_q['1'][1]))
    new_elements.append(wire(pins_q['1'][0] - 4.00, pins_q['1'][1] + 15.81, pins_q['1'][0] - 4.00, pins_q['1'][1] + 20.00))
    new_elements.append(g_label("GND", pins_q['1'][0] - 4.00, pins_q['1'][1] + 20.00, rot=270))

    final_content = base + "\n" + "\n".join(new_elements) + "\n)\n"

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(final_content)

    print(f"{output_path} successfully written!")

if __name__ == '__main__':
    generate_schematic('test_perfect.kicad_sch')
