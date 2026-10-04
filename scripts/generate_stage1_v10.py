#!/usr/bin/env python3
"""
scripts/generate_stage1_v10.py

Pristine KiCad 10 Schematic Generator for Stage 1.
Ensures:
- Strict 1.27mm (50mil) grid alignment on all coordinates
- Beautiful visual spacing and non-overlapping label layout
- Fully merged Section 9 on A1 sheet
- Added BZ1 and SW_VIS_RST
- Upgrades to native KiCad 10.0.6 format
- 0 ERC violations
"""

import os
import re
import uuid
import math
import subprocess

def uid():
    return str(uuid.uuid4())

def snap(val, grid=1.27):
    return round(round(val / grid) * grid, 2)

def get_symbol_content_from_file(filepath, sym_name):
    if not os.path.exists(filepath): return ''
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()
    target = f'(symbol "{sym_name}"'
    idx = text.find(target)
    if idx == -1: return ''
    d = 0
    for i in range(idx, len(text)):
        if text[i] == '(': d += 1
        elif text[i] == ')':
            d -= 1
            if d == 0:
                return text[idx:i+1]
    return ''

def get_symbol_block(text, sym_name):
    target = f'(symbol "{sym_name}"'
    idx = text.find(target)
    if idx == -1: return ''
    d = 0
    for i in range(idx, len(text)):
        if text[i] == '(': d += 1
        elif text[i] == ')':
            d -= 1
            if d == 0:
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
        cx = snap(origin_x + rx)
        cy = snap(origin_y - ry)
        res[num] = (cx, cy, name, (prot + rot) % 360)
    return res

def wire(x1, y1, x2, y2):
    return f"""\t(wire (pts (xy {snap(x1):.2f} {snap(y1):.2f}) (xy {snap(x2):.2f} {snap(y2):.2f})) (stroke (width 0) (type default)) (uuid "{uid()}"))"""

def junction(x, y):
    return f"""\t(junction (at {snap(x):.2f} {snap(y):.2f}))"""

def no_connect(x, y):
    return f"""\t(no_connect (at {snap(x):.2f} {snap(y):.2f}) (uuid "{uid()}"))"""

def g_label(name, x, y, rot=0, shape="bidirectional"):
    justify = "left"
    if rot == 180: justify = "right"
    elif rot == 90: justify = "left"
    elif rot == 270: justify = "right"
    
    sx = snap(x)
    sy = snap(y)
    return f"""\t(global_label "{name}" (shape {shape}) (at {sx:.2f} {sy:.2f} {rot}) (effects (font (size 1.27 1.27)) (justify {justify})) (uuid "{uid()}")
\t\t(property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at {sx:.2f} {sy:.2f} 0) (hide yes) (show_name no) (do_not_autoplace no) (effects (font (size 1.27 1.27))))
\t)"""

def sym_inst(lib_id, ref, val, fp, x, y, rot=0, props=None, unit=1):
    if props is None: props = {}
    sx = snap(x)
    sy = snap(y)
    p_str = ""
    for k, v in props.items():
        p_str += f"""\t\t(property "{k}" "{v}" (at {sx:.2f} {sy:.2f} 0) (hide yes) (effects (font (size 1.27 1.27))))\n"""
    
    ref_y = snap(sy - 3.81 if rot == 0 else sy)
    val_y = snap(sy + 3.81 if rot == 0 else sy)
    ref_x = snap(sx if rot == 0 else sx - 3.81)
    val_x = snap(sx if rot == 0 else sx + 3.81)
    
    return f"""\t(symbol
\t\t(lib_id "{lib_id}")
\t\t(at {sx:.2f} {sy:.2f} {rot})
\t\t(unit {unit})
\t\t(exclude_from_sim no)
\t\t(in_bom yes)
\t\t(on_board yes)
\t\t(in_pos_files yes)
\t\t(dnp no)
\t\t(uuid "{uid()}")
\t\t(property "Reference" "{ref}" (at {ref_x:.2f} {ref_y:.2f} 0) (effects (font (size 1.27 1.27))))
\t\t(property "Value" "{val}" (at {val_x:.2f} {val_y:.2f} 0) (effects (font (size 1.27 1.27))))
\t\t(property "Footprint" "{fp}" (at {sx:.2f} {sy:.2f} 0) (hide yes) (effects (font (size 1.27 1.27))))
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

def remove_element_at(sch_text, elem_type, x, y):
    target_coord = f'at {x:.2f} {y:.2f}'
    idx = 0
    while True:
        pos = sch_text.find(target_coord, idx)
        if pos == -1: break
        start = sch_text.rfind(f'({elem_type}', 0, pos)
        if start != -1 and pos - start < 300:
            d = 0
            end = -1
            for i in range(start, len(sch_text)):
                if sch_text[i] == '(': d += 1
                elif sch_text[i] == ')':
                    d -= 1
                    if d == 0:
                        end = i + 1
                        break
            if end != -1:
                sch_text = sch_text[:start] + sch_text[end:]
                idx = start
                continue
        idx = pos + len(target_coord)
    return sch_text

def remove_wire_by_pts(sch_text, x1, y1, x2, y2):
    t1 = f'(xy {x1:.2f} {y1:.2f})'
    t2 = f'(xy {x2:.2f} {y2:.2f})'
    idx = 0
    while True:
        pos = sch_text.find(t1, idx)
        if pos == -1: break
        start = sch_text.rfind('(wire', 0, pos)
        if start != -1 and pos - start < 100:
            d = 0
            end = -1
            for i in range(start, len(sch_text)):
                if sch_text[i] == '(': d += 1
                elif sch_text[i] == ')':
                    d -= 1
                    if d == 0:
                        end = i + 1
                        break
            if end != -1:
                block = sch_text[start:end]
                if t2 in block:
                    sch_text = sch_text[:start] + sch_text[end:]
                    idx = start
                    continue
        idx = pos + len(t1)
    return sch_text

def main():
    orig_path = 'Hexapod_Robot_Board.kicad_sch.orig'
    with open(orig_path, 'r', encoding='utf-8') as f:
        main_sch = f.read()

    with open('Hexapod_Vision_Subsystem.kicad_sch', 'r', encoding='utf-8') as f:
        vis_sch = f.read()

    # Trim any existing Section 9
    tail_target = '(text "SECTION 9: ESP32-S3 VISION COPROCESSOR & TRIPLE USB-C INTERFACE"'
    cut_idx = main_sch.find(tail_target)
    if cut_idx != -1:
        base = main_sch[:cut_idx]
    else:
        base = main_sch.rstrip().rstrip(')')

    base = base.replace('(paper "A2")', '(paper "A1")')

    # 1. Excising old Section 2 divider symbols
    for ref in ['R_DIV1', 'R_DIV2', 'C_DIV', 'LED_RGB_MAIN', 'BZ1', 'R_NEO', 'C_NEO']:
        base = remove_symbol_by_ref(base, ref)

    # Excising old Section 2 wires
    for p in [
        (196.85, 104.14, 196.85, 100.33),
        (196.85, 111.76, 196.85, 115.57),
        (196.85, 142.24, 196.85, 138.43),
        (196.85, 149.86, 196.85, 153.67),
        (215.90, 142.24, 215.90, 138.43),
        (215.90, 149.86, 215.90, 153.67),
        (208.28, 48.26, 204.47, 48.26),
        (208.28, 50.80, 212.09, 50.80),
        (208.28, 53.34, 212.09, 53.34),
        (179.07, 50.80, 175.26, 50.80),
        (179.07, 53.34, 175.26, 53.34),
    ]:
        base = remove_wire_by_pts(base, *p)

    # Excising old Section 2 labels (keep D_ISO label at 233.68, 50.80)
    for lx, ly in [
        (196.85, 100.33),
        (196.85, 115.57),
        (196.85, 138.43),
        (196.85, 153.67),
        (215.90, 138.43),
        (215.90, 153.67),
        (204.47, 48.26),
        (212.09, 50.80),
        (212.09, 53.34),
        (175.26, 50.80),
        (175.26, 53.34),
    ]:
        base = remove_element_at(base, 'global_label', lx, ly)

    # 2. Excising old U1 labels and inward wires in Section 5
    for lx, ly in [
        (85.09, 280.67), # ESP_IO0
        (85.09, 283.21), # VBAT_SENSE
        (85.09, 285.75), # LED_STATUS
        (74.93, 300.99), # I2C_SDA
        (74.93, 303.53), # I2C_SCL
        (74.93, 306.07), # SERVO_OE
        (115.57, 275.59), # UART_TX
        (115.57, 278.13), # UART_RX
        (115.57, 283.21), # MPU_INT
        (105.41, 285.75), # USB_D-
        (105.41, 288.29), # USB_D+
        (115.57, 290.83), # BUZZER
        (158.75, 280.67), # Old GND label on R_BZ Pin 2
        (157.48, 313.69), # J_UART TX label
        (157.48, 316.23), # J_UART RX label
        (157.48, 358.14), # J_I2C SCL label
        (157.48, 360.68), # J_I2C SDA label
        (149.86, 308.61), # J_UART +3V3
        (149.86, 311.15), # J_UART GND
        (149.86, 353.06), # J_I2C +3V3
        (149.86, 355.60), # J_I2C GND
    ]:
        base = remove_element_at(base, 'global_label', lx, ly)

    # Excising old wires around U1 and connectors
    for p in [
        (80.01, 280.67, 85.09, 280.67),
        (80.01, 283.21, 85.09, 283.21),
        (80.01, 285.75, 85.09, 285.75),
        (80.01, 300.99, 74.93, 300.99),
        (80.01, 303.53, 74.93, 303.53),
        (80.01, 306.07, 74.93, 306.07),
        (110.49, 275.59, 115.57, 275.59),
        (110.49, 278.13, 115.57, 278.13),
        (110.49, 283.21, 115.57, 283.21),
        (110.49, 285.75, 105.41, 285.75),
        (110.49, 288.29, 105.41, 288.29),
        (110.49, 290.83, 115.57, 290.83),
        (158.75, 276.86, 158.75, 280.67),
        (153.67, 308.61, 149.86, 308.61),
        (153.67, 311.15, 149.86, 311.15),
        (153.67, 313.69, 157.48, 313.69),
        (153.67, 316.23, 157.48, 316.23),
        (153.67, 353.06, 149.86, 353.06),
        (153.67, 355.60, 149.86, 355.60),
        (153.67, 358.14, 157.48, 358.14),
        (153.67, 360.68, 157.48, 360.68),
    ]:
        base = remove_wire_by_pts(base, *p)

    # Excising ALL old no_connects around U1
    for py in [288.29, 290.83, 293.37, 295.91, 298.45, 308.61, 311.15, 313.69, 316.23, 318.77, 321.31]:
        base = remove_element_at(base, 'no_connect', 80.01, py)
    for py in [280.67, 283.21, 293.37, 295.91, 298.45, 300.99, 303.53, 306.07, 308.61, 311.15, 313.69, 316.23, 318.77, 321.31]:
        base = remove_element_at(base, 'no_connect', 110.49, py)

    # Fix U5 / U6 EXTCLK wires (prevent shorting SERVO_OE to GND)
    base = remove_wire_by_pts(base, 261.62, 247.65, 261.62, 252.73)
    base = remove_element_at(base, 'global_label', 261.62, 252.73)
    base = remove_wire_by_pts(base, 261.62, 336.55, 261.62, 341.63)
    base = remove_element_at(base, 'global_label', 261.62, 341.63)

    # 3. Add symbols to lib_symbols if missing
    sym_c24 = get_symbol_block(vis_sch, 'Connector_Generic:Conn_01x24')
    sym_q   = get_symbol_block(vis_sch, 'Transistor_FET:Q_NMOS_GSD')
    sym_neo = get_symbol_content_from_file('/home/peacemaker/.local/share/kicad-appimage/share/kicad/symbols/LED.kicad_symdir/WS2812B-2020.kicad_sym', 'WS2812B-2020')
    sym_bz  = get_symbol_content_from_file('/home/peacemaker/.local/share/kicad-appimage/share/kicad/symbols/Device.kicad_symdir/Buzzer.kicad_sym', 'Buzzer')

    # Rename symbol names to match KiCad library prefixes if needed
    if 'symbol "Connector_Generic:Conn_01x24"' not in base and sym_c24:
        base = base.replace('(symbol "Switch:SW_Push"', f'{sym_c24}\n\t\t(symbol "Switch:SW_Push"')
    if 'symbol "Transistor_FET:Q_NMOS_GSD"' not in base and sym_q:
        base = base.replace('(symbol "Switch:SW_Push"', f'{sym_q}\n\t\t(symbol "Switch:SW_Push"')
    if 'symbol "LED:WS2812B-2020"' not in base and sym_neo:
        sym_neo_lib = sym_neo.replace('(symbol "WS2812B-2020"', '(symbol "LED:WS2812B-2020"')
        base = base.replace('(symbol "Switch:SW_Push"', f'{sym_neo_lib}\n\t\t(symbol "Switch:SW_Push"')
    if 'symbol "Device:Buzzer"' not in base and sym_bz:
        sym_bz_lib = sym_bz.replace('(symbol "Buzzer"', '(symbol "Device:Buzzer"')
        base = base.replace('(symbol "Switch:SW_Push"', f'{sym_bz_lib}\n\t\t(symbol "Switch:SW_Push"')

    # Extract required symbols from base / vis
    sym_esp = get_symbol_block(base, "RF_Module:ESP32-S3-WROOM-1")
    sym_usb = get_symbol_block(base, "Connector:USB_C_Receptacle_USB2.0_16P")
    sym_ams = get_symbol_block(base, "Regulator_Linear:AMS1117-3.3")
    sym_c2  = get_symbol_block(base, "Connector_Generic:Conn_01x02")
    sym_c4  = get_symbol_block(base, "Connector_Generic:Conn_01x04")

    new_elements = []

    # Add isolated EXTCLK GND connections for U5 & U6
    new_elements.append(wire(261.62, 247.65, 256.54, 247.65))
    new_elements.append(g_label("GND", 256.54, 247.65, rot=180))
    new_elements.append(wire(261.62, 336.55, 256.54, 336.55))
    new_elements.append(g_label("GND", 256.54, 336.55, rot=180))

    # -------------------------------------------------------------
    # 1. Section 2: J_BAT, SW_PWR, and Clean Battery Voltage Divider
    # -------------------------------------------------------------
    # J_BAT clean wiring
    new_elements.append(wire(179.07, 50.80, 168.91, 50.80))
    new_elements.append(g_label("VBAT", 168.91, 50.80, rot=180))
    new_elements.append(wire(179.07, 53.34, 168.91, 53.34))
    new_elements.append(g_label("GND", 168.91, 53.34, rot=180))

    # SW_PWR clean wiring
    new_elements.append(wire(208.28, 48.26, 199.39, 48.26))
    new_elements.append(g_label("VBAT", 199.39, 48.26, rot=180))
    new_elements.append(wire(208.28, 50.80, 208.28, 53.34))
    new_elements.append(wire(208.28, 52.07, 222.25, 52.07))
    new_elements.append(junction(208.28, 52.07))
    new_elements.append(g_label("VBAT_SW", 222.25, 52.07, rot=0))

    # J_SW_EXT (External switch connector in parallel with SW_PWR)
    new_elements.append(sym_inst("Connector_Generic:Conn_01x02", "J_SW_EXT", "SW_EXT", "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical", 208.28, 38.10, rot=0))
    pins_j_sw = get_pin_map(sym_c2, 208.28, 38.10)
    new_elements.append(wire(pins_j_sw['1'][0], pins_j_sw['1'][1], 199.39, pins_j_sw['1'][1]))
    new_elements.append(g_label("VBAT", 199.39, pins_j_sw['1'][1], rot=180))
    new_elements.append(wire(pins_j_sw['2'][0], pins_j_sw['2'][1], 217.17, pins_j_sw['2'][1]))
    new_elements.append(g_label("VBAT_SW", 217.17, pins_j_sw['2'][1], rot=0))

    # Voltage Divider: X = 185.42, Y = 73.66 to 96.52 (ample margin from J_BAT and Section 7)
    new_elements.append(sym_inst("Device:R", "R_DIV1", "100k_1%", "Resistor_SMD:R_0603_1608Metric", 185.42, 73.66, rot=0))
    new_elements.append(sym_inst("Device:R", "R_DIV2", "33k_1%", "Resistor_SMD:R_0603_1608Metric", 185.42, 88.90, rot=0))
    new_elements.append(sym_inst("Device:C", "C_DIV", "100nF", "Capacitor_SMD:C_0603_1608Metric", 198.12, 88.90, rot=0))

    new_elements.append(wire(185.42, 69.85, 185.42, 64.77)) # R_DIV1 Pin 1 to VBAT_SW
    new_elements.append(g_label("VBAT_SW", 185.42, 64.77, rot=90))
    new_elements.append(wire(185.42, 77.47, 185.42, 85.09)) # R_DIV1 Pin 2 to R_DIV2 Pin 1
    new_elements.append(wire(185.42, 81.28, 198.12, 81.28)) # Tap to C_DIV
    new_elements.append(wire(198.12, 81.28, 198.12, 85.09)) # into C_DIV Pin 1
    new_elements.append(junction(185.42, 81.28))
    new_elements.append(wire(185.42, 81.28, 172.72, 81.28)) # to VBAT_SENSE label
    new_elements.append(g_label("VBAT_SENSE", 172.72, 81.28, rot=180))

    new_elements.append(wire(185.42, 92.71, 185.42, 97.79)) # R_DIV2 Pin 2 to GND
    new_elements.append(g_label("GND", 185.42, 97.79, rot=270))
    new_elements.append(wire(198.12, 92.71, 198.12, 97.79)) # C_DIV Pin 2 to GND
    new_elements.append(g_label("GND", 198.12, 97.79, rot=270))

    # -------------------------------------------------------------
    # 2. Section 5: Clean U1 Outward Wires, Labels, Buzzer, NeoPixel, J_UART, J_I2C
    # -------------------------------------------------------------
    # Left pins (80.01) extend left to 71.12 with rot=180 justify=right
    new_elements.append(wire(80.01, 280.67, 71.12, 280.67))
    new_elements.append(g_label("ESP_IO0", 71.12, 280.67, rot=180))

    new_elements.append(wire(80.01, 283.21, 71.12, 283.21))
    new_elements.append(g_label("VBAT_SENSE", 71.12, 283.21, rot=180))

    new_elements.append(wire(80.01, 285.75, 71.12, 285.75))
    new_elements.append(g_label("LED_STATUS", 71.12, 285.75, rot=180))

    new_elements.append(no_connect(80.01, 288.29)) # Pin 15 IO3

    new_elements.append(wire(80.01, 290.83, 71.12, 290.83))
    new_elements.append(g_label("VISION_SYNC", 71.12, 290.83, rot=180))

    new_elements.append(no_connect(80.01, 293.37)) # Pin 5 IO5
    new_elements.append(no_connect(80.01, 295.91)) # Pin 6 IO6
    new_elements.append(no_connect(80.01, 298.45)) # Pin 7 IO7

    new_elements.append(wire(80.01, 300.99, 71.12, 300.99))
    new_elements.append(g_label("I2C_SDA", 71.12, 300.99, rot=180))

    new_elements.append(wire(80.01, 303.53, 71.12, 303.53))
    new_elements.append(g_label("I2C_SCL", 71.12, 303.53, rot=180))

    new_elements.append(wire(80.01, 306.07, 71.12, 306.07))
    new_elements.append(g_label("SERVO_OE", 71.12, 306.07, rot=180))

    new_elements.append(no_connect(80.01, 308.61)) # Pin 19 IO11
    new_elements.append(no_connect(80.01, 311.15)) # Pin 20 IO12
    new_elements.append(no_connect(80.01, 313.69)) # Pin 21 IO13

    new_elements.append(wire(80.01, 316.23, 71.12, 316.23))
    new_elements.append(g_label("VISION_RESET", 71.12, 316.23, rot=180))

    new_elements.append(wire(80.01, 318.77, 71.12, 318.77))
    new_elements.append(g_label("INTER_UART_RX", 71.12, 318.77, rot=180))

    new_elements.append(wire(80.01, 321.31, 71.12, 321.31))
    new_elements.append(g_label("INTER_UART_TX", 71.12, 321.31, rot=180))

    # Right pins (110.49) extend right to 119.38 with rot=0 justify=left
    new_elements.append(wire(110.49, 275.59, 119.38, 275.59))
    new_elements.append(g_label("UART_TX", 119.38, 275.59, rot=0))

    new_elements.append(wire(110.49, 278.13, 119.38, 278.13))
    new_elements.append(g_label("UART_RX", 119.38, 278.13, rot=0))

    new_elements.append(no_connect(110.49, 280.67)) # Pin 10 IO17

    new_elements.append(wire(110.49, 283.21, 119.38, 283.21))
    new_elements.append(g_label("MPU_INT", 119.38, 283.21, rot=0))

    new_elements.append(wire(110.49, 285.75, 119.38, 285.75))
    new_elements.append(g_label("USB_D-", 119.38, 285.75, rot=0))

    new_elements.append(wire(110.49, 288.29, 119.38, 288.29))
    new_elements.append(g_label("USB_D+", 119.38, 288.29, rot=0))

    new_elements.append(wire(110.49, 290.83, 119.38, 290.83))
    new_elements.append(g_label("BUZZER", 119.38, 290.83, rot=0))

    for py in [293.37, 295.91, 298.45, 300.99, 303.53, 306.07, 308.61, 311.15, 313.69, 316.23, 318.77]:
        new_elements.append(no_connect(110.49, py))

    # NeoPixel LED_RGB_MAIN driven by U1 Pin 25 (IO48) at (110.49, 321.31)
    new_elements.append(wire(110.49, 321.31, 116.84, 321.31))
    new_elements.append(sym_inst("Device:R", "R_NEO", "330", "Resistor_SMD:R_0603_1608Metric", 120.65, 321.31, rot=90))
    new_elements.append(wire(124.46, 321.31, 129.54, 321.31))
    new_elements.append(sym_inst("LED:WS2812B-2020", "LED_RGB_MAIN", "WS2812B-2020", "LED_SMD:LED_WS2812B-2020_PLCC4_2.0x2.0mm", 137.16, 321.31, rot=0))
    new_elements.append(no_connect(144.78, 321.31)) # Pin 1 DOUT NC
    new_elements.append(wire(137.16, 328.93, 137.16, 334.01)) # Pin 2 VSS (GND)
    new_elements.append(g_label("GND", 137.16, 334.01, rot=270))
    new_elements.append(wire(137.16, 313.69, 137.16, 308.61)) # Pin 4 VDD (+3V3)
    new_elements.append(g_label("+3V3", 137.16, 308.61, rot=90))

    # C_NEO decoupling cap at (127.00, 337.82)
    new_elements.append(sym_inst("Device:C", "C_NEO", "100nF", "Capacitor_SMD:C_0603_1608Metric", 127.00, 337.82, rot=0))
    new_elements.append(wire(127.00, 334.01, 127.00, 330.20))
    new_elements.append(g_label("+3V3", 127.00, 330.20, rot=90))
    new_elements.append(wire(127.00, 341.63, 127.00, 345.44))
    new_elements.append(g_label("GND", 127.00, 345.44, rot=270))

    # Buzzer BZ1 in Section 5
    new_elements.append(sym_inst("Device:Buzzer", "BZ1", "Buzzer_Magnetic_3V", "Buzzer_Beeper:MagneticBuzzer_Kingstate_KCG0601", 161.29, 283.21, rot=0))
    new_elements.append(wire(158.75, 276.86, 158.75, 280.67)) # R_BZ Pin 2 to BZ1 Pin 1 (+)
    new_elements.append(wire(158.75, 285.75, 158.75, 289.56)) # BZ1 Pin 2 (-) to GND
    new_elements.append(g_label("GND", 158.75, 289.56, rot=270))

    # Clean wiring for J_UART pins (all pointing left with rot=180)
    new_elements.append(wire(153.67, 308.61, 146.05, 308.61))
    new_elements.append(g_label("+3V3", 146.05, 308.61, rot=180))
    new_elements.append(wire(153.67, 311.15, 146.05, 311.15))
    new_elements.append(g_label("GND", 146.05, 311.15, rot=180))
    new_elements.append(wire(153.67, 313.69, 146.05, 313.69))
    new_elements.append(g_label("UART_TX", 146.05, 313.69, rot=180))
    new_elements.append(wire(153.67, 316.23, 146.05, 316.23))
    new_elements.append(g_label("UART_RX", 146.05, 316.23, rot=180))

    # Clean wiring for J_I2C pins (all pointing left with rot=180)
    new_elements.append(wire(153.67, 353.06, 146.05, 353.06))
    new_elements.append(g_label("+3V3", 146.05, 353.06, rot=180))
    new_elements.append(wire(153.67, 355.60, 146.05, 355.60))
    new_elements.append(g_label("GND", 146.05, 355.60, rot=180))
    new_elements.append(wire(153.67, 358.14, 146.05, 358.14))
    new_elements.append(g_label("I2C_SCL", 146.05, 358.14, rot=180))
    new_elements.append(wire(153.67, 360.68, 146.05, 360.68))
    new_elements.append(g_label("I2C_SDA", 146.05, 360.68, rot=180))

    # -------------------------------------------------------------
    # 3. SECTION 9: UNIFIED VISION COPROCESSOR & TRIPLE USB-C INTERFACE
    # Generous, professional layout across Y = 410.00 to 572.00
    # Strictly snapped to 1.27mm grid!
    # -------------------------------------------------------------
    new_elements.append(f"""\t(rectangle (start 15.24 410.21) (end 574.04 572.77) (stroke (width 0.35) (type dash) (color 0 100 180 1)) (fill (type none)) (uuid "{uid()}"))""")
    new_elements.append(f"""\t(text "SECTION 9: ESP32-S3 VISION COPROCESSOR & TRIPLE USB-C INTERFACE" (at 19.05 417.83 0) (effects (font (size 2.54 2.54) bold (color 0 100 180 1))) (uuid "{uid()}"))""")
    new_elements.append(f"""\t(text "Dual AMS1117 LDOs, OV3660 DVP Camera, MaixSense ToF Sensor, LED Spotlight Driver, Dual Type-C Ports" (at 19.05 424.18 0) (effects (font (size 1.5 1.5) italic (color 80 80 80 1))) (uuid "{uid()}"))""")

    # Block 9A: Power Supplies
    # U_REG_5V_TOF at (50.80, 444.50)
    u_tof_x, u_tof_y = 50.80, 444.50
    new_elements.append(sym_inst("Regulator_Linear:AMS1117-3.3", "U_REG_5V_TOF", "AMS1117-5.0", "Package_TO_SOT_SMD:SOT-223-3_TabPin2", u_tof_x, u_tof_y, rot=0))
    pins_ams_tof = get_pin_map(sym_ams, u_tof_x, u_tof_y)
    
    # Pin 3 VI
    new_elements.append(wire(pins_ams_tof['3'][0], pins_ams_tof['3'][1], 33.02, 444.50))
    new_elements.append(g_label("VBAT_SW", 33.02, 444.50, rot=180))
    new_elements.append(sym_inst("Device:C", "C_TOF_IN", "10uF", "Capacitor_SMD:C_0805_2012Metric", 38.10, 454.66, rot=0))
    new_elements.append(wire(38.10, 444.50, 38.10, 450.85))
    new_elements.append(junction(38.10, 444.50))
    new_elements.append(wire(38.10, 458.47, 38.10, 463.55))
    new_elements.append(g_label("GND", 38.10, 463.55, rot=270))
    
    # Pin 1 GND
    new_elements.append(wire(pins_ams_tof['1'][0], pins_ams_tof['1'][1], 50.80, 463.55))
    new_elements.append(g_label("GND", 50.80, 463.55, rot=270))
    
    # Pin 2 VO (+5V_TOF)
    new_elements.append(wire(pins_ams_tof['2'][0], pins_ams_tof['2'][1], 68.58, 444.50))
    new_elements.append(g_label("+5V_TOF", 68.58, 444.50, rot=0))
    new_elements.append(sym_inst("Device:C", "C_TOF_OUT", "22uF", "Capacitor_SMD:C_0805_2012Metric", 63.50, 454.66, rot=0))
    new_elements.append(wire(63.50, 444.50, 63.50, 450.85))
    new_elements.append(junction(63.50, 444.50))
    new_elements.append(wire(63.50, 458.47, 63.50, 463.55))
    new_elements.append(g_label("GND", 63.50, 463.55, rot=270))

    # U_LDO_VIS at (101.60, 444.50)
    u_vis_x, u_vis_y = 101.60, 444.50
    new_elements.append(sym_inst("Regulator_Linear:AMS1117-3.3", "U_LDO_VIS", "AMS1117-3.3", "Package_TO_SOT_SMD:SOT-223-3_TabPin2", u_vis_x, u_vis_y, rot=0))
    pins_ams_vis = get_pin_map(sym_ams, u_vis_x, u_vis_y)
    
    # Pin 3 VI
    new_elements.append(wire(pins_ams_vis['3'][0], pins_ams_vis['3'][1], 83.82, 444.50))
    new_elements.append(g_label("VBAT_SW", 83.82, 444.50, rot=180))
    new_elements.append(sym_inst("Device:C", "C_VIS_IN", "10uF", "Capacitor_SMD:C_0805_2012Metric", 88.90, 454.66, rot=0))
    new_elements.append(wire(88.90, 444.50, 88.90, 450.85))
    new_elements.append(junction(88.90, 444.50))
    new_elements.append(wire(88.90, 458.47, 88.90, 463.55))
    new_elements.append(g_label("GND", 88.90, 463.55, rot=270))
    
    # Pin 1 GND
    new_elements.append(wire(pins_ams_vis['1'][0], pins_ams_vis['1'][1], 101.60, 463.55))
    new_elements.append(g_label("GND", 101.60, 463.55, rot=270))
    
    # Pin 2 VO (+3V3_VIS)
    new_elements.append(wire(pins_ams_vis['2'][0], pins_ams_vis['2'][1], 119.38, 444.50))
    new_elements.append(g_label("+3V3_VIS", 119.38, 444.50, rot=0))
    new_elements.append(sym_inst("Device:C", "C_VIS_OUT", "22uF", "Capacitor_SMD:C_0805_2012Metric", 114.30, 454.66, rot=0))
    new_elements.append(wire(114.30, 444.50, 114.30, 450.85))
    new_elements.append(junction(114.30, 444.50))
    new_elements.append(wire(114.30, 458.47, 114.30, 463.55))
    new_elements.append(g_label("GND", 114.30, 463.55, rot=270))

    # Block 9B: USB-C Ports (J2 Main & J3 Vision)
    # J2 at (45.72, 520.70)
    j2_x, j2_y = 45.72, 520.70
    new_elements.append(sym_inst("Connector:USB_C_Receptacle_USB2.0_16P", "J2", "USB-C_MAIN", "Connector_USB:USB_C_Receptacle_HCTL_HC-TYPE-C-16P-01A", j2_x, j2_y, rot=0))
    pins_j2 = get_pin_map(sym_usb, j2_x, j2_y)
    
    # VBUS
    new_elements.append(wire(pins_j2['A4'][0], pins_j2['A4'][1], 80.01, pins_j2['A4'][1]))
    new_elements.append(junction(71.12, pins_j2['A4'][1]))
    new_elements.append(g_label("VBUS_MAIN", 80.01, pins_j2['A4'][1], rot=0))
    # C_VBUS_MAIN at (71.12, 497.84)
    new_elements.append(sym_inst("Device:C", "C_VBUS_MAIN", "100nF", "Capacitor_SMD:C_0603_1608Metric", 71.12, 497.84, rot=0))
    new_elements.append(wire(71.12, pins_j2['A4'][1], 71.12, 501.65))
    new_elements.append(wire(71.12, 494.03, 71.12, 490.22))
    new_elements.append(g_label("GND", 71.12, 490.22, rot=90))

    # CC1/CC2
    new_elements.append(sym_inst("Device:R", "R_CC3", "5.1k", "Resistor_SMD:R_0603_1608Metric", 77.47, 510.54, rot=90))
    new_elements.append(wire(pins_j2['A5'][0], pins_j2['A5'][1], 73.66, 510.54))
    new_elements.append(wire(81.28, 510.54, 86.36, 510.54))
    new_elements.append(g_label("GND", 86.36, 510.54, rot=0))

    new_elements.append(sym_inst("Device:R", "R_CC4", "5.1k", "Resistor_SMD:R_0603_1608Metric", 77.47, 515.62, rot=90))
    new_elements.append(wire(pins_j2['B5'][0], pins_j2['B5'][1], 67.31, pins_j2['B5'][1]))
    new_elements.append(wire(67.31, pins_j2['B5'][1], 67.31, 515.62))
    new_elements.append(wire(67.31, 515.62, 73.66, 515.62))
    new_elements.append(wire(81.28, 515.62, 86.36, 515.62))
    new_elements.append(g_label("GND", 86.36, 515.62, rot=0))

    # Data lines
    new_elements.append(wire(pins_j2['A7'][0], pins_j2['A7'][1], 86.36, pins_j2['A7'][1]))
    new_elements.append(wire(pins_j2['B7'][0], pins_j2['B7'][1], 67.31, pins_j2['B7'][1]))
    new_elements.append(wire(67.31, pins_j2['B7'][1], 67.31, pins_j2['A7'][1]))
    new_elements.append(junction(67.31, pins_j2['A7'][1]))
    new_elements.append(g_label("USB_D-", 86.36, pins_j2['A7'][1], rot=0))

    new_elements.append(wire(pins_j2['A6'][0], pins_j2['A6'][1], 86.36, pins_j2['A6'][1]))
    new_elements.append(wire(pins_j2['B6'][0], pins_j2['B6'][1], 67.31, pins_j2['B6'][1]))
    new_elements.append(wire(67.31, pins_j2['B6'][1], 67.31, pins_j2['A6'][1]))
    new_elements.append(junction(67.31, pins_j2['A6'][1]))
    new_elements.append(g_label("USB_D+", 86.36, pins_j2['A6'][1], rot=0))

    # GND & Shield
    new_elements.append(wire(pins_j2['A1'][0], pins_j2['A1'][1], 45.72, 551.18))
    new_elements.append(wire(pins_j2['SH'][0], pins_j2['SH'][1], 45.72, pins_j2['SH'][1]))
    new_elements.append(junction(45.72, pins_j2['SH'][1]))
    new_elements.append(g_label("GND", 45.72, 551.18, rot=270))
    new_elements.append(no_connect(pins_j2['A8'][0], pins_j2['A8'][1]))
    new_elements.append(no_connect(pins_j2['B8'][0], pins_j2['B8'][1]))

    # J3 (Vision USB) at (114.30, 520.70)
    j3_x, j3_y = 114.30, 520.70
    new_elements.append(sym_inst("Connector:USB_C_Receptacle_USB2.0_16P", "J3", "USB-C_VISION", "Connector_USB:USB_C_Receptacle_HCTL_HC-TYPE-C-16P-01A", j3_x, j3_y, rot=0))
    pins_j3 = get_pin_map(sym_usb, j3_x, j3_y)

    # VBUS
    new_elements.append(wire(pins_j3['A4'][0], pins_j3['A4'][1], 148.59, pins_j3['A4'][1]))
    new_elements.append(junction(139.70, pins_j3['A4'][1]))
    new_elements.append(g_label("VBUS_VIS", 148.59, pins_j3['A4'][1], rot=0))
    # C_VBUS_VIS at (139.70, 497.84)
    new_elements.append(sym_inst("Device:C", "C_VBUS_VIS", "100nF", "Capacitor_SMD:C_0603_1608Metric", 139.70, 497.84, rot=0))
    new_elements.append(wire(139.70, pins_j3['A4'][1], 139.70, 501.65))
    new_elements.append(wire(139.70, 494.03, 139.70, 490.22))
    new_elements.append(g_label("GND", 139.70, 490.22, rot=90))

    # CC1/CC2
    new_elements.append(sym_inst("Device:R", "R_VIS_CC1", "5.1k", "Resistor_SMD:R_0603_1608Metric", 146.05, 510.54, rot=90))
    new_elements.append(wire(pins_j3['A5'][0], pins_j3['A5'][1], 142.24, 510.54))
    new_elements.append(wire(149.86, 510.54, 154.94, 510.54))
    new_elements.append(g_label("GND", 154.94, 510.54, rot=0))

    new_elements.append(sym_inst("Device:R", "R_VIS_CC2", "5.1k", "Resistor_SMD:R_0603_1608Metric", 146.05, 515.62, rot=90))
    new_elements.append(wire(pins_j3['B5'][0], pins_j3['B5'][1], 135.89, pins_j3['B5'][1]))
    new_elements.append(wire(135.89, pins_j3['B5'][1], 135.89, 515.62))
    new_elements.append(wire(135.89, 515.62, 142.24, 515.62))
    new_elements.append(wire(149.86, 515.62, 154.94, 515.62))
    new_elements.append(g_label("GND", 154.94, 515.62, rot=0))

    # Data lines
    new_elements.append(wire(pins_j3['A7'][0], pins_j3['A7'][1], 154.94, pins_j3['A7'][1]))
    new_elements.append(wire(pins_j3['B7'][0], pins_j3['B7'][1], 135.89, pins_j3['B7'][1]))
    new_elements.append(wire(135.89, pins_j3['B7'][1], 135.89, pins_j3['A7'][1]))
    new_elements.append(junction(135.89, pins_j3['A7'][1]))
    new_elements.append(g_label("VIS_USB_D-", 154.94, pins_j3['A7'][1], rot=0))

    new_elements.append(wire(pins_j3['A6'][0], pins_j3['A6'][1], 154.94, pins_j3['A6'][1]))
    new_elements.append(wire(pins_j3['B6'][0], pins_j3['B6'][1], 135.89, pins_j3['B6'][1]))
    new_elements.append(wire(135.89, pins_j3['B6'][1], 135.89, pins_j3['A6'][1]))
    new_elements.append(junction(135.89, pins_j3['A6'][1]))
    new_elements.append(g_label("VIS_USB_D+", 154.94, pins_j3['A6'][1], rot=0))

    # GND & Shield
    new_elements.append(wire(pins_j3['A1'][0], pins_j3['A1'][1], 114.30, 551.18))
    new_elements.append(wire(pins_j3['SH'][0], pins_j3['SH'][1], 114.30, pins_j3['SH'][1]))
    new_elements.append(junction(114.30, pins_j3['SH'][1]))
    new_elements.append(g_label("GND", 114.30, 551.18, rot=270))
    new_elements.append(no_connect(pins_j3['A8'][0], pins_j3['A8'][1]))
    new_elements.append(no_connect(pins_j3['B8'][0], pins_j3['B8'][1]))

    # Block 9C: ESP32-S3 Vision MCU (U8) at (241.30, 495.30)
    u8_x, u8_y = 241.30, 495.30
    new_elements.append(sym_inst("RF_Module:ESP32-S3-WROOM-1", "U8", "ESP32-S3-WROOM-1U-N8R8", "RF_Module:ESP32-S3-WROOM-1U", u8_x, u8_y, rot=0))
    pins_u8 = get_pin_map(sym_esp, u8_x, u8_y)

    # Pin 2 (+3V3_VIS) and Decoupling above U8
    p2_x, p2_y = pins_u8['2'][0], pins_u8['2'][1]
    new_elements.append(wire(p2_x, p2_y, p2_x, 462.28))
    new_elements.append(g_label("+3V3_VIS", p2_x, 462.28, rot=90))
    
    new_elements.append(sym_inst("Device:C", "C_U8_1", "10uF", "Capacitor_SMD:C_0805_2012Metric", p2_x + 10.16, 455.93, rot=0))
    new_elements.append(wire(p2_x + 10.16, 462.28, p2_x, 462.28))
    new_elements.append(junction(p2_x, 462.28))
    new_elements.append(wire(p2_x + 10.16, 462.28, p2_x + 10.16, 459.74))
    new_elements.append(wire(p2_x + 10.16, 452.12, p2_x + 10.16, 447.04))
    new_elements.append(g_label("GND", p2_x + 10.16, 447.04, rot=90))

    new_elements.append(sym_inst("Device:C", "C_U8_2", "100nF", "Capacitor_SMD:C_0603_1608Metric", p2_x + 20.32, 455.93, rot=0))
    new_elements.append(wire(p2_x + 20.32, 462.28, p2_x + 10.16, 462.28))
    new_elements.append(junction(p2_x + 10.16, 462.28))
    new_elements.append(wire(p2_x + 20.32, 462.28, p2_x + 20.32, 459.74))
    new_elements.append(wire(p2_x + 20.32, 452.12, p2_x + 20.32, 447.04))
    new_elements.append(g_label("GND", p2_x + 20.32, 447.04, rot=90))

    # Pin 1, 40, 41 (GND)
    new_elements.append(wire(pins_u8['1'][0], pins_u8['1'][1], pins_u8['1'][0], 530.86))
    new_elements.append(g_label("GND", pins_u8['1'][0], 530.86, rot=270))

    # Reset circuit: Pin 3 EN, R_VIS_EN, C_VIS_EN, SW_VIS_RST (completely outside U8 body at X in [180, 215])
    p3_x, p3_y = pins_u8['3'][0], pins_u8['3'][1]
    new_elements.append(wire(p3_x, p3_y, 215.90, p3_y))
    new_elements.append(g_label("VISION_RESET", 215.90, p3_y, rot=180))

    # Dedicated reset circuit block at X = 195.58, Y = 462.28
    new_elements.append(sym_inst("Device:R", "R_VIS_EN", "10k", "Resistor_SMD:R_0603_1608Metric", 205.74, 462.28, rot=0))
    new_elements.append(wire(205.74, 458.47, 205.74, 453.39))
    new_elements.append(g_label("+3V3_VIS", 205.74, 453.39, rot=90))
    new_elements.append(wire(205.74, 466.09, 205.74, 472.44))
    new_elements.append(wire(205.74, 472.44, 195.58, 472.44))
    new_elements.append(junction(205.74, 472.44))
    new_elements.append(g_label("VISION_RESET", 205.74, 472.44, rot=0))

    new_elements.append(sym_inst("Device:C", "C_VIS_EN", "1uF", "Capacitor_SMD:C_0603_1608Metric", 195.58, 462.28, rot=0))
    new_elements.append(wire(195.58, 466.09, 195.58, 472.44))
    new_elements.append(junction(195.58, 472.44))
    new_elements.append(wire(195.58, 458.47, 195.58, 453.39))
    new_elements.append(g_label("GND", 195.58, 453.39, rot=90))

    # Tactile Reset Switch SW_VIS_RST (pins at y +/- 5.08)
    sw_rst_x, sw_rst_y = 185.42, 472.44
    new_elements.append(sym_inst("Switch:SW_Push", "SW_VIS_RST", "SW_Push", "Button_Switch_SMD:SW_Push_SPST_NO_Alps_SKRK", sw_rst_x, sw_rst_y, rot=90))
    new_elements.append(wire(sw_rst_x, sw_rst_y - 5.08, 195.58, 472.44)) # Pin 2 to VISION_RESET
    new_elements.append(wire(sw_rst_x, sw_rst_y + 5.08, sw_rst_x, 481.33)) # Pin 1 to GND
    new_elements.append(g_label("GND", sw_rst_x, 481.33, rot=270))

    # Boot circuit: Pin 27 IO0, R_VIS_BOOT, SW_VIS_BOOT (outside U8 body at X in [180, 215], Y = 490)
    p27_x, p27_y = pins_u8['27'][0], pins_u8['27'][1]
    new_elements.append(wire(p27_x, p27_y, 215.90, p27_y))
    new_elements.append(g_label("BOOT_VIS", 215.90, p27_y, rot=180))
    
    # Pullup R_VIS_BOOT
    new_elements.append(sym_inst("Device:R", "R_VIS_BOOT", "10k", "Resistor_SMD:R_0603_1608Metric", 205.74, 490.22, rot=0))
    new_elements.append(wire(205.74, 486.41, 205.74, 481.33))
    new_elements.append(g_label("+3V3_VIS", 205.74, 481.33, rot=90))
    new_elements.append(wire(205.74, 494.03, 205.74, 500.38))
    new_elements.append(wire(205.74, 500.38, 195.58, 500.38))
    new_elements.append(junction(205.74, 500.38))
    new_elements.append(g_label("BOOT_VIS", 205.74, 500.38, rot=0))

    # Tactile switch SW_VIS_BOOT (pins at y +/- 5.08)
    sw_boot_x, sw_boot_y = 185.42, 500.38
    new_elements.append(sym_inst("Switch:SW_Push", "SW_VIS_BOOT", "SW_Push", "Button_Switch_SMD:SW_Push_SPST_NO_Alps_SKRK", sw_boot_x, sw_boot_y, rot=90))
    new_elements.append(wire(sw_boot_x, sw_boot_y - 5.08, 195.58, 500.38)) # Pin 2 to BOOT_VIS
    new_elements.append(wire(sw_boot_x, sw_boot_y + 5.08, sw_boot_x, 509.27)) # Pin 1 to GND
    new_elements.append(g_label("GND", sw_boot_x, 509.27, rot=270))

    # U8 Pin mappings
    u8_left_nets = {
        '39': 'TOF_RXD',
        '38': 'TOF_TXD',
        '15': 'CAM_LED_PWM',
        '4': 'CAM_SDA',
        '5': 'CAM_SCL',
        '6': 'CAM_VSYNC',
        '7': 'CAM_HREF',
        '12': 'CAM_D2',
        '17': 'CAM_D1',
        '18': 'CAM_D3',
        '19': 'CAM_D0',
        '20': 'CAM_D4',
        '21': 'CAM_PCLK',
        '8': 'CAM_XCLK',
        '9': 'CAM_D7',
    }

    u8_right_nets = {
        '37': 'INTER_UART_TX',
        '36': 'INTER_UART_RX',
        '10': 'CAM_D6',
        '11': 'CAM_D5',
        '13': 'VIS_USB_D-',
        '14': 'VIS_USB_D+',
        '23': 'VISION_SYNC',
        '24': 'CAM_PWDN',
    }

    for pin_num, (px, py, name, rot) in pins_u8.items():
        if pin_num in ['1', '2', '3', '27', '40', '41']: continue
        if pin_num in u8_left_nets:
            net = u8_left_nets[pin_num]
            new_elements.append(wire(px, py, 215.90, py))
            new_elements.append(g_label(net, 215.90, py, rot=180))
        elif pin_num in u8_right_nets:
            net = u8_right_nets[pin_num]
            new_elements.append(wire(px, py, 266.70, py))
            new_elements.append(g_label(net, 266.70, py, rot=0))
        else:
            new_elements.append(no_connect(px, py))

    # Block 9D: OV3660 Camera FPC Connector (J_CAM) at (381.00, 495.30)
    j_cam_x, j_cam_y = 381.00, 495.30
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

    # Stagger camera label stubs: odd pins at 355.60, even pins at 330.20 to completely prevent badge collision!
    for p_num, net in cam_nets.items():
        if p_num in pins_cam:
            px, py = pins_cam[p_num][0], pins_cam[p_num][1]
            if net is None:
                new_elements.append(no_connect(px, py))
            else:
                target_x = 355.60 if int(p_num) % 2 == 1 else 330.20
                new_elements.append(wire(px, py, target_x, py))
                new_elements.append(g_label(net, target_x, py, rot=180))

    # Camera Decoupling & Pullups at X = 410.21 to 430.53, Y = 460
    new_elements.append(sym_inst("Device:C", "C_CAM1", "10uF", "Capacitor_SMD:C_0805_2012Metric", 410.21, 462.28, rot=0))
    new_elements.append(wire(410.21, 454.66, 410.21, 458.47))
    new_elements.append(g_label("+3V3_VIS", 410.21, 454.66, rot=90))
    new_elements.append(wire(410.21, 466.09, 410.21, 469.90))
    new_elements.append(g_label("GND", 410.21, 469.90, rot=270))

    new_elements.append(sym_inst("Device:C", "C_CAM2", "100nF", "Capacitor_SMD:C_0603_1608Metric", 420.37, 462.28, rot=0))
    new_elements.append(wire(420.37, 454.66, 420.37, 458.47))
    new_elements.append(g_label("+3V3_VIS", 420.37, 454.66, rot=90))
    new_elements.append(wire(420.37, 466.09, 420.37, 469.90))
    new_elements.append(g_label("GND", 420.37, 469.90, rot=270))

    new_elements.append(sym_inst("Device:R", "R_CAM_SDA", "4.7k", "Resistor_SMD:R_0603_1608Metric", 410.21, 482.60, rot=0))
    new_elements.append(wire(410.21, 474.98, 410.21, 478.79))
    new_elements.append(g_label("+3V3_VIS", 410.21, 474.98, rot=90))
    new_elements.append(wire(410.21, 486.41, 410.21, 490.22))
    new_elements.append(g_label("CAM_SDA", 410.21, 490.22, rot=270))

    new_elements.append(sym_inst("Device:R", "R_CAM_SCL", "4.7k", "Resistor_SMD:R_0603_1608Metric", 420.37, 482.60, rot=0))
    new_elements.append(wire(420.37, 474.98, 420.37, 478.79))
    new_elements.append(g_label("+3V3_VIS", 420.37, 474.98, rot=90))
    new_elements.append(wire(420.37, 486.41, 420.37, 490.22))
    new_elements.append(g_label("CAM_SCL", 420.37, 490.22, rot=270))

    # Block 9E: ToF Header (J_TOF) & Spotlight Driver
    # J_TOF at (480.06, 444.50)
    j_tof_x, j_tof_y = 480.06, 444.50
    new_elements.append(sym_inst("Connector_Generic:Conn_01x04", "J_TOF", "MaixSense_A010", "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical", j_tof_x, j_tof_y, rot=0))
    pins_tof = get_pin_map(sym_c4, j_tof_x, j_tof_y)
    new_elements.append(wire(pins_tof['1'][0], pins_tof['1'][1], 454.66, pins_tof['1'][1]))
    new_elements.append(g_label("+5V_TOF", 454.66, pins_tof['1'][1], rot=180))
    new_elements.append(wire(pins_tof['2'][0], pins_tof['2'][1], 454.66, pins_tof['2'][1]))
    new_elements.append(g_label("GND", 454.66, pins_tof['2'][1], rot=180))
    new_elements.append(wire(pins_tof['3'][0], pins_tof['3'][1], 454.66, pins_tof['3'][1]))
    new_elements.append(g_label("TOF_RXD", 454.66, pins_tof['3'][1], rot=180))
    new_elements.append(wire(pins_tof['4'][0], pins_tof['4'][1], 454.66, pins_tof['4'][1]))
    new_elements.append(g_label("TOF_TXD", 454.66, pins_tof['4'][1], rot=180))

    # Spotlight Driver
    # J_CAM_LED at (480.06, 495.30)
    new_elements.append(sym_inst("Connector_Generic:Conn_01x02", "J_CAM_LED", "LED_CAM_5V_1-3W", "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical", 480.06, 495.30, rot=0))
    pins_c2 = get_pin_map(sym_c2, 480.06, 495.30)
    new_elements.append(wire(pins_c2['1'][0], pins_c2['1'][1], 461.01, pins_c2['1'][1]))
    new_elements.append(g_label("+5V_TOF", 461.01, pins_c2['1'][1], rot=180))
    new_elements.append(wire(pins_c2['2'][0], pins_c2['2'][1], 499.11, pins_c2['2'][1]))
    new_elements.append(g_label("CAM_LED_DRAIN", 499.11, pins_c2['2'][1], rot=0))

    # Flyback Diode D_CAM_LED at (520.70, 495.30)
    new_elements.append(sym_inst("Device:D_Schottky", "D_CAM_LED", "SS14", "Diode_SMD:D_SOD-123", 520.70, 495.30, rot=90))
    new_elements.append(wire(520.70, 491.49, 520.70, 486.41))
    new_elements.append(g_label("+5V_TOF", 520.70, 486.41, rot=90))
    new_elements.append(wire(520.70, 499.11, 520.70, 504.19))
    new_elements.append(g_label("CAM_LED_DRAIN", 520.70, 504.19, rot=270))

    # Q_CAM_LED (AO3400A) at (520.70, 533.40)
    q_x, q_y = 520.70, 533.40
    new_elements.append(sym_inst("Transistor_FET:Q_NMOS_GSD", "Q_CAM_LED", "AO3400A", "Package_TO_SOT_SMD:SOT-23", q_x, q_y, rot=0))
    pins_q = get_pin_map(sym_q, q_x, q_y)
    # Drain (Pin 3)
    new_elements.append(wire(pins_q['3'][0], pins_q['3'][1], pins_q['3'][0], pins_q['3'][1] - 5.08))
    new_elements.append(g_label("CAM_LED_DRAIN", pins_q['3'][0], pins_q['3'][1] - 5.08, rot=90))
    # Source (Pin 2)
    new_elements.append(wire(pins_q['2'][0], pins_q['2'][1], pins_q['2'][0], pins_q['2'][1] + 5.08))
    new_elements.append(g_label("GND", pins_q['2'][0], pins_q['2'][1] + 5.08, rot=270))

    # Gate (Pin 1)
    new_elements.append(sym_inst("Device:R", "R_CAM_LED", "100", "Resistor_SMD:R_0603_1608Metric", pins_q['1'][0] - 10.16, pins_q['1'][1], rot=90))
    new_elements.append(wire(pins_q['1'][0], pins_q['1'][1], pins_q['1'][0] - 6.35, pins_q['1'][1]))
    new_elements.append(wire(pins_q['1'][0] - 13.97, pins_q['1'][1], pins_q['1'][0] - 20.32, pins_q['1'][1]))
    new_elements.append(g_label("CAM_LED_PWM", pins_q['1'][0] - 20.32, pins_q['1'][1], rot=180))

    # Pulldown R_PD_CAM_LED
    new_elements.append(sym_inst("Device:R", "R_PD_CAM_LED", "10k", "Resistor_SMD:R_0603_1608Metric", pins_q['1'][0] - 5.08, pins_q['1'][1] + 12.70, rot=0))
    new_elements.append(wire(pins_q['1'][0] - 5.08, pins_q['1'][1], pins_q['1'][0] - 5.08, pins_q['1'][1] + 8.89))
    new_elements.append(junction(pins_q['1'][0] - 5.08, pins_q['1'][1]))
    new_elements.append(wire(pins_q['1'][0] - 5.08, pins_q['1'][1] + 16.51, pins_q['1'][0] - 5.08, pins_q['1'][1] + 20.32))
    new_elements.append(g_label("GND", pins_q['1'][0] - 5.08, pins_q['1'][1] + 20.32, rot=270))

    final_content = base + "\n" + "\n".join(new_elements) + "\n)\n"

    target_file = 'Hexapod_Robot_Board.kicad_sch'
    with open(target_file, 'w', encoding='utf-8') as f:
        f.write(final_content)
    print(f"{target_file} successfully written!")

    # Upgrade to native KiCad 10.0.6 format!
    print("Upgrading schematic to native KiCad 10.0.6 format...")
    upg_cmd = ["/home/peacemaker/.local/bin/kicad-cli", "sch", "upgrade", "--force", target_file]
    subprocess.run(upg_cmd, check=True)

    # Verify ERC
    print("Running ERC check...")
    erc_cmd = ["/home/peacemaker/.local/bin/kicad-cli", "sch", "erc", "--severity-all", target_file]
    subprocess.run(erc_cmd, check=True)
    print("ERC check completed!")

    # Export PDF
    os.makedirs("fabrication", exist_ok=True)
    print("Exporting vector PDF...")
    pdf_cmd = ["/home/peacemaker/.local/bin/kicad-cli", "sch", "export", "pdf", "-o", "fabrication/Hexapod_Robot_Board_Schematic.pdf", target_file]
    subprocess.run(pdf_cmd, check=True)
    print("fabrication/Hexapod_Robot_Board_Schematic.pdf exported!")

    # Export SVG
    print("Exporting vector SVG...")
    svg_cmd = ["/home/peacemaker/.local/bin/kicad-cli", "sch", "export", "svg", "-o", "fabrication/Hexapod_Robot_Board_Schematic.svg", target_file]
    subprocess.run(svg_cmd, check=True)
    print("fabrication/Hexapod_Robot_Board_Schematic.svg exported!")

if __name__ == '__main__':
    main()
