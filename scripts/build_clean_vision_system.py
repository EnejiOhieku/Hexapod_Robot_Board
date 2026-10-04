#!/usr/bin/env python3
"""
build_clean_vision_system.py

Generates:
1. Hexapod_Vision_Subsystem.kicad_sch (ESP32-S3 Vision Coprocessor subsheet)
   - U8 (ESP32-S3-WROOM-1U), J_CAM (OV3660 DVP 24P), J_TOF (MaixSense A010)
   - J3 (USB-C Vision)
   - U_REG_5V_TOF (Dedicated AMS1117-5.0 LDO for ToF)
   - U_LDO_VIS (Dedicated AMS1117-3.3 LDO for Vision ESP32)
   - High-power Camera LED driver: J_CAM_LED (2-pin), Q_CAM_LED (AO3400A N-MOSFET),
     R_CAM_LED (100R), R_PD_CAM_LED (10k), D_CAM_LED (SS14), driven by GPIO 3 (pin 15),
     powered by V_SERVO_L (5V 5A buck rail).
2. Updates Hexapod_Robot_Board.kicad_sch (Root schematic):
   - J1 data pins disconnected (battery charging only)
   - J2 added (Main MCU USB-C) with CC pull-downs & filter cap
   - Vision_Coprocessor hierarchical sheet instantiated
   - U1 inter-MCU signals wired cleanly
   - Uncrosses PCA9685 PWM routing completely:
     Left PCA9685 (U5, 0x40): Legs 4, 5, 6 (C, F, T) + AUX 4, 5, 6 (12 PWMs, strictly Left)
     Right PCA9685 (U6, 0x41): Legs 1, 2, 3 (C, F, T) + AUX 1, 2, 3 (12 PWMs, strictly Right)
     All 24 servo headers re-labeled cleanly (PWM_L1_C..PWM_L6_T, PWM_AUX1..PWM_AUX6).
   - Adds J_SW_EXT (2-pin external power switch header in parallel with SW_PWR).
   - Adds LED_RGB_MAIN (WS2812B-2020), R_NEO (330R), C_NEO (100nF) on U1 GPIO 48 (pin 25).
"""

import uuid
import re
import os
import subprocess

def uid():
    return str(uuid.uuid4())

def get_full_symbol(text, sym_name):
    target = f'(symbol "{sym_name}"'
    idx = text.find(target)
    if idx == -1:
        raise ValueError(f"Symbol {sym_name} not found")
    depth = 0
    for i in range(idx, len(text)):
        if text[i] == '(':
            depth += 1
        elif text[i] == ')':
            depth -= 1
            if depth == 0:
                return text[idx:i+1]
    raise ValueError(f"Could not parse symbol {sym_name}")

def get_pin_map(sym_text, origin_x, origin_y):
    pins = {}
    pin_matches = re.finditer(
        r'\(pin\s+[^\s]+\s+line\s+\(at\s+([-\d.]+)\s+([-\d.]+)\s+(\d+)\).*?\(name\s+"([^"]*)".*?\(number\s+"([^"]+)"',
        sym_text, re.DOTALL
    )
    for m in pin_matches:
        rel_x = float(m.group(1))
        rel_y = float(m.group(2))
        rot = int(m.group(3))
        pname = m.group(4)
        pnum = m.group(5)
        pin_x = round((origin_x + rel_x) / 1.27) * 1.27
        pin_y = round((origin_y - rel_y) / 1.27) * 1.27
        pins[pnum] = (pin_x, pin_y, rot, pname)
    return pins

def sym_inst(lib_id, ref, val, fp, x, y, rot=0, props=None, path="/44f02a75-3141-486c-ae96-cf48718534a3/3c162b70-9b48-4cb3-a9d9-df720eb9aa32"):
    prop_str = ""
    if props:
        for k, v in props.items():
            prop_str += f'\n\t\t(property "{k}" "{v}" (at {x:.2f} {y:.2f} 0) (hide yes) (effects (font (size 1.27 1.27))))'
    return f"""\t(symbol
\t\t(lib_id "{lib_id}")
\t\t(at {x:.2f} {y:.2f} {rot})
\t\t(unit 1)
\t\t(exclude_from_sim no)
\t\t(in_bom yes)
\t\t(on_board yes)
\t\t(dnp no)
\t\t(uuid "{uid()}")
\t\t(property "Reference" "{ref}" (at {x:.2f} {y-2.54:.2f} 0) (effects (font (size 1.27 1.27))))
\t\t(property "Value" "{val}" (at {x:.2f} {y+2.54:.2f} 0) (effects (font (size 1.27 1.27))))
\t\t(property "Footprint" "{fp}" (at {x:.2f} {y:.2f} 0) (hide yes) (effects (font (size 1.27 1.27))))
\t\t(property "Datasheet" "~" (at {x:.2f} {y:.2f} 0) (hide yes) (effects (font (size 1.27 1.27))))\t\t{prop_str}
\t\t(instances
\t\t\t(project "Hexapod_Robot_Board"
\t\t\t\t(path "{path}"
\t\t\t\t\t(reference "{ref}")
\t\t\t\t\t(unit 1)
\t\t\t\t)
\t\t\t)
\t\t)
\t)"""

def wire(x1, y1, x2, y2):
    return f'\t(wire (pts (xy {x1:.2f} {y1:.2f}) (xy {x2:.2f} {y2:.2f})) (stroke (width 0) (type default)) (uuid "{uid()}"))'

def junction(x, y):
    return f'\t(junction (at {x:.2f} {y:.2f}) (diameter 0) (color 0 0 0 0) (uuid "{uid()}"))'

def h_label(name, x, y, rot=0, shape="input"):
    justify = "left" if rot == 0 else "right"
    return f'\t(hierarchical_label "{name}" (shape {shape}) (at {x:.2f} {y:.2f} {rot}) (effects (font (size 1.27 1.27)) (justify {justify})) (uuid "{uid()}"))'

def local_label(name, x, y, rot=0):
    justify = "left" if rot == 0 else "right"
    return f'\t(label "{name}" (at {x:.2f} {y:.2f} {rot}) (effects (font (size 1.27 1.27)) (justify {justify})) (uuid "{uid()}"))'

def global_label(name, x, y, rot=0):
    justify = "left" if rot == 0 else "right"
    return f'\t(global_label "{name}" (shape bidirectional) (at {x:.2f} {y:.2f} {rot}) (effects (font (size 1.27 1.27)) (justify {justify})) (uuid "{uid()}"))'

def no_conn(x, y):
    return f'\t(no_connect (at {x:.2f} {y:.2f}) (uuid "{uid()}"))'

def r_vert(ref, val, x, y, path="/44f02a75-3141-486c-ae96-cf48718534a3/3c162b70-9b48-4cb3-a9d9-df720eb9aa32"):
    x = round(x / 1.27) * 1.27
    y = round(y / 1.27) * 1.27
    inst = sym_inst("Device:R", ref, val, "Resistor_SMD:R_0603_1608Metric", x, y, rot=0, path=path)
    p1 = (x, round((y - 3.81) / 1.27) * 1.27)
    p2 = (x, round((y + 3.81) / 1.27) * 1.27)
    return inst, p1, p2

def r_horiz(ref, val, x, y, path="/44f02a75-3141-486c-ae96-cf48718534a3/3c162b70-9b48-4cb3-a9d9-df720eb9aa32"):
    x = round(x / 1.27) * 1.27
    y = round(y / 1.27) * 1.27
    inst = sym_inst("Device:R", ref, val, "Resistor_SMD:R_0603_1608Metric", x, y, rot=90, path=path)
    p1 = (round((x - 3.81) / 1.27) * 1.27, y)
    p2 = (round((x + 3.81) / 1.27) * 1.27, y)
    return inst, p1, p2

def c_vert(ref, val, fp, x, y, path="/44f02a75-3141-486c-ae96-cf48718534a3/3c162b70-9b48-4cb3-a9d9-df720eb9aa32"):
    x = round(x / 1.27) * 1.27
    y = round(y / 1.27) * 1.27
    inst = sym_inst("Device:C", ref, val, fp, x, y, rot=0, path=path)
    p1 = (x, round((y - 3.81) / 1.27) * 1.27)
    p2 = (x, round((y + 3.81) / 1.27) * 1.27)
    return inst, p1, p2

def build_vision_subsheet(main_sch_text):
    sym_esp = get_full_symbol(main_sch_text, "RF_Module:ESP32-S3-WROOM-1")
    conn24_path = '/home/peacemaker/.local/share/kicad-appimage/share/kicad/symbols/Connector_Generic.kicad_symdir/Conn_01x24.kicad_sym'
    with open(conn24_path, 'r', encoding='utf-8') as f:
        c24_raw = f.read()
    sym_c24 = get_full_symbol(c24_raw, 'Conn_01x24')
    sym_c24 = sym_c24.replace('(symbol "Conn_01x24"', '(symbol "Connector_Generic:Conn_01x24"', 1)
    sym_c4  = get_full_symbol(main_sch_text, "Connector_Generic:Conn_01x04")
    sym_c2  = get_full_symbol(main_sch_text, "Connector_Generic:Conn_01x02")
    sym_usb = get_full_symbol(main_sch_text, "Connector:USB_C_Receptacle_USB2.0_16P")
    sym_ams = get_full_symbol(main_sch_text, "Regulator_Linear:AMS1117-3.3")
    sym_r   = get_full_symbol(main_sch_text, "Device:R")
    sym_c   = get_full_symbol(main_sch_text, "Device:C")
    sym_sw  = get_full_symbol(main_sch_text, "Switch:SW_Push")
    sym_d_schottky = get_full_symbol(main_sch_text, "Device:D_Schottky")

    nmos_path = '/home/peacemaker/.local/share/kicad-appimage/share/kicad/symbols/Transistor_FET.kicad_symdir/Q_NMOS_GSD.kicad_sym'
    with open(nmos_path, 'r', encoding='utf-8') as f:
        nmos_raw = f.read()
    sym_nmos = get_full_symbol(nmos_raw, 'Q_NMOS_GSD')
    sym_nmos = sym_nmos.replace('(symbol "Q_NMOS_GSD"', '(symbol "Transistor_FET:Q_NMOS_GSD"', 1)

    header = f"""(kicad_sch
\t(version 20250114)
\t(generator "kicad_sch_gen")
\t(generator_version "10.0")
\t(uuid "3c162b70-9b48-4cb3-a9d9-df720eb9aa32")
\t(paper "A3")
\t(lib_symbols
\t\t{sym_esp}
\t\t{sym_c24}
\t\t{sym_c4}
\t\t{sym_c2}
\t\t{sym_usb}
\t\t{sym_ams}
\t\t{sym_r}
\t\t{sym_c}
\t\t{sym_sw}
\t\t{sym_nmos}
\t\t{sym_d_schottky}
\t)"""

    elements = []

    # =========================================================================
    # ROW 1: REGULATORS (Y = 63.50)
    # =========================================================================
    # U_REG_5V_TOF at (88.90, 63.50) - Dedicated Linear 5V LDO for ToF sensor
    elements.append(sym_inst("Regulator_Linear:AMS1117-3.3", "U_REG_5V_TOF", "AMS1117-5.0", "Package_TO_SOT_SMD:SOT-223-3_TabPin2", 88.90, 63.50))
    elements.append(wire(81.28, 63.50, 71.12, 63.50))
    elements.append(wire(71.12, 63.50, 63.50, 63.50))
    elements.append(global_label("VBAT_SW", 63.50, 63.50, rot=180))
    c_inst, cp1, cp2 = c_vert("C_TOF_IN", "10uF", "Capacitor_SMD:C_0805_2012Metric", 71.12, 73.66)
    elements.append(c_inst)
    elements.append(wire(cp1[0], cp1[1], 71.12, 63.50))
    elements.append(junction(71.12, 63.50))
    elements.append(global_label("GND", cp2[0], cp2[1], rot=270))
    elements.append(wire(88.90, 71.12, 88.90, 76.20))
    elements.append(global_label("GND", 88.90, 76.20, rot=270))
    elements.append(wire(96.52, 63.50, 104.14, 63.50))
    elements.append(wire(104.14, 63.50, 114.30, 63.50))
    elements.append(local_label("+5V_TOF", 114.30, 63.50))
    c_inst, cp1, cp2 = c_vert("C_TOF_OUT", "22uF", "Capacitor_SMD:C_0805_2012Metric", 104.14, 73.66)
    elements.append(c_inst)
    elements.append(wire(cp1[0], cp1[1], 104.14, 63.50))
    elements.append(junction(104.14, 63.50))
    elements.append(global_label("GND", cp2[0], cp2[1], rot=270))

    # U_LDO_VIS at (177.80, 63.50) - Dedicated 3.3V Linear LDO for Vision ESP32
    elements.append(sym_inst("Regulator_Linear:AMS1117-3.3", "U_LDO_VIS", "AMS1117-3.3", "Package_TO_SOT_SMD:SOT-223-3_TabPin2", 177.80, 63.50))
    elements.append(wire(170.18, 63.50, 160.02, 63.50))
    elements.append(wire(160.02, 63.50, 152.40, 63.50))
    elements.append(global_label("VBAT_SW", 152.40, 63.50, rot=180))
    c_inst, cp1, cp2 = c_vert("C_VIS_IN", "10uF", "Capacitor_SMD:C_0805_2012Metric", 160.02, 73.66)
    elements.append(c_inst)
    elements.append(wire(cp1[0], cp1[1], 160.02, 63.50))
    elements.append(junction(160.02, 63.50))
    elements.append(global_label("GND", cp2[0], cp2[1], rot=270))
    elements.append(wire(177.80, 71.12, 177.80, 76.20))
    elements.append(global_label("GND", 177.80, 76.20, rot=270))
    elements.append(wire(185.42, 63.50, 193.04, 63.50))
    elements.append(wire(193.04, 63.50, 203.20, 63.50))
    elements.append(local_label("+3V3_VIS", 203.20, 63.50))
    c_inst, cp1, cp2 = c_vert("C_VIS_OUT", "22uF", "Capacitor_SMD:C_0805_2012Metric", 193.04, 73.66)
    elements.append(c_inst)
    elements.append(wire(cp1[0], cp1[1], 193.04, 63.50))
    elements.append(junction(193.04, 63.50))
    elements.append(global_label("GND", cp2[0], cp2[1], rot=270))

    # =========================================================================
    # ROW 1 RIGHT: HIGH-POWER CAMERA ILLUMINATION LED DRIVER (Y = 63.50)
    # =========================================================================
    # J_CAM_LED (Conn_01x02) at (266.70, 63.50)
    elements.append(sym_inst("Connector_Generic:Conn_01x02", "J_CAM_LED", "LED_CAM_5V_1-3W", "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical", 266.70, 63.50))
    elements.append(wire(261.62, 63.50, 251.46, 63.50))
    elements.append(global_label("V_SERVO_L", 251.46, 63.50, rot=180))
    elements.append(wire(261.62, 66.04, 251.46, 66.04))
    elements.append(local_label("CAM_LED_DRAIN", 251.46, 66.04, rot=180))

    # Schottky Diode D_CAM_LED across J_CAM_LED
    elements.append(sym_inst("Device:D_Schottky", "D_CAM_LED", "SS14", "Diode_SMD:D_SOD-123", 284.48, 50.80, rot=0))
    elements.append(wire(280.67, 50.80, 271.78, 50.80))
    elements.append(global_label("V_SERVO_L", 271.78, 50.80, rot=180))
    elements.append(wire(288.29, 50.80, 297.18, 50.80))
    elements.append(local_label("CAM_LED_DRAIN", 297.18, 50.80, rot=0))

    # MOSFET Q_CAM_LED (AO3400A / Q_NMOS_GSD, SOT-23)
    elements.append(sym_inst("Transistor_FET:Q_NMOS_GSD", "Q_CAM_LED", "AO3400A", "Package_TO_SOT_SMD:SOT-23", 330.20, 63.50))
    elements.append(wire(332.74, 68.58, 332.74, 76.20))
    elements.append(global_label("GND", 332.74, 76.20, rot=270))
    elements.append(wire(332.74, 58.42, 332.74, 50.80))
    elements.append(local_label("CAM_LED_DRAIN", 332.74, 50.80, rot=90))

    # Gate Drive: R_CAM_LED (100R, horiz) & R_PD_CAM_LED (10k, vert)
    r_inst, rp1, rp2 = r_horiz("R_CAM_LED", "100", 314.96, 63.50)
    elements.append(r_inst)
    elements.append(wire(rp1[0], rp1[1], rp1[0] - 8.89, rp1[1]))
    elements.append(local_label("CAM_LED_PWM", rp1[0] - 8.89, rp1[1], rot=180))
    elements.append(wire(rp2[0], rp2[1], 325.12, 63.50))

    r_inst, rp1, rp2 = r_vert("R_PD_CAM_LED", "10k", 325.12, 73.66)
    elements.append(r_inst)
    elements.append(wire(325.12, 63.50, rp1[0], rp1[1]))
    elements.append(junction(325.12, 63.50))
    elements.append(global_label("GND", rp2[0], rp2[1], rot=270))

    # =========================================================================
    # ROW 2: J_TOF (Conn_01x04) at (63.50, 177.80)
    # =========================================================================
    pins_tof = get_pin_map(sym_c4, 63.50, 177.80)
    elements.append(sym_inst("Connector_Generic:Conn_01x04", "J_TOF", "MaixSense_A010", "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical", 63.50, 177.80))
    px, py, _, _ = pins_tof['1']
    elements.append(wire(px, py, px - 10.16, py))
    elements.append(local_label("+5V_TOF", px - 10.16, py, rot=180))
    px, py, _, _ = pins_tof['2']
    elements.append(wire(px, py, px - 10.16, py))
    elements.append(global_label("GND", px - 10.16, py, rot=180))
    px, py, _, _ = pins_tof['3']
    elements.append(wire(px, py, px - 10.16, py))
    elements.append(local_label("TOF_RXD", px - 10.16, py, rot=180))
    px, py, _, _ = pins_tof['4']
    elements.append(wire(px, py, px - 10.16, py))
    elements.append(local_label("TOF_TXD", px - 10.16, py, rot=180))

    # =========================================================================
    # ROW 3: J3 USB-C VISION at (63.50, 241.30)
    # =========================================================================
    pins_usb = get_pin_map(sym_usb, 63.50, 241.30)
    elements.append(sym_inst("Connector:USB_C_Receptacle_USB2.0_16P", "J3", "USB-C_VISION", "Connector_USB:USB_C_Receptacle_HCTL_HC-TYPE-C-16P-01A", 63.50, 241.30))
    dp_a_x, dp_a_y, _, _ = pins_usb['A6']
    dp_b_x, dp_b_y, _, _ = pins_usb['B6']
    elements.append(wire(dp_a_x, dp_a_y, dp_a_x + 10.16, dp_a_y))
    elements.append(wire(dp_b_x, dp_b_y, dp_a_x + 10.16, dp_a_y))
    elements.append(local_label("VIS_USB_D+", dp_a_x + 10.16, dp_a_y))
    dm_a_x, dm_a_y, _, _ = pins_usb['A7']
    dm_b_x, dm_b_y, _, _ = pins_usb['B7']
    elements.append(wire(dm_a_x, dm_a_y, dm_a_x + 10.16, dm_a_y))
    elements.append(wire(dm_b_x, dm_b_y, dm_a_x + 10.16, dm_a_y))
    elements.append(local_label("VIS_USB_D-", dm_a_x + 10.16, dm_a_y))
    gnd_x, gnd_y, _, _ = pins_usb['A1']
    sh_x, sh_y, _, _ = pins_usb['SH']
    elements.append(wire(sh_x, sh_y, gnd_x, gnd_y))
    elements.append(wire(gnd_x, gnd_y, gnd_x, gnd_y - 7.62))
    elements.append(global_label("GND", gnd_x, gnd_y - 7.62, rot=90))
    vbus_x, vbus_y, _, _ = pins_usb['A4']
    elements.append(wire(vbus_x, vbus_y, vbus_x + 10.16, vbus_y))
    elements.append(local_label("VBUS_VIS", vbus_x + 10.16, vbus_y))
    cc1_x, cc1_y, _, _ = pins_usb['A5']
    cc2_x, cc2_y, _, _ = pins_usb['B5']
    r_inst, rp1, rp2 = r_vert("R_VIS_CC1", "5.1k", cc1_x + 15.24, cc1_y + 3.81)
    elements.append(r_inst)
    elements.append(wire(cc1_x, cc1_y, rp1[0], rp1[1]))
    elements.append(global_label("GND", rp2[0], rp2[1], rot=270))
    r_inst, rp1, rp2 = r_vert("R_VIS_CC2", "5.1k", cc2_x + 25.40, cc2_y + 3.81)
    elements.append(r_inst)
    elements.append(wire(cc2_x, cc2_y, rp1[0], rp1[1]))
    elements.append(global_label("GND", rp2[0], rp2[1], rot=270))
    elements.append(no_conn(pins_usb['A8'][0], pins_usb['A8'][1]))
    elements.append(no_conn(pins_usb['B8'][0], pins_usb['B8'][1]))

    # =========================================================================
    # ROW 2/3: U8 (ESP32-S3-WROOM-1U-N8R8) at (177.80, 177.80)
    # =========================================================================
    pins_u8 = get_pin_map(sym_esp, 177.80, 177.80)
    elements.append(sym_inst("RF_Module:ESP32-S3-WROOM-1", "U8", "ESP32-S3-WROOM-1U-N8R8", "RF_Module:ESP32-S3-WROOM-1U", 177.80, 177.80))
    p_x, p_y, _, _ = pins_u8['1']
    elements.append(wire(p_x, p_y, p_x, p_y + 7.62))
    elements.append(global_label("GND", p_x, p_y + 7.62, rot=270))
    p_x, p_y, _, _ = pins_u8['40']
    elements.append(wire(p_x, p_y, p_x, p_y + 7.62))
    p_x, p_y, _, _ = pins_u8['2']
    elements.append(wire(p_x, p_y, p_x, p_y - 7.62))
    elements.append(local_label("+3V3_VIS", p_x, p_y - 7.62, rot=90))
    c_inst, cp1, cp2 = c_vert("C_U8_1", "10uF", "Capacitor_SMD:C_0805_2012Metric", p_x + 12.70, p_y - 12.70)
    elements.append(c_inst)
    elements.append(wire(cp1[0], cp1[1], p_x + 12.70, p_y - 7.62))
    elements.append(wire(p_x, p_y - 7.62, p_x + 12.70, p_y - 7.62))
    elements.append(junction(p_x, p_y - 7.62))
    elements.append(global_label("GND", cp2[0], cp2[1], rot=270))
    c_inst, cp1, cp2 = c_vert("C_U8_2", "100nF", "Capacitor_SMD:C_0603_1608Metric", p_x + 22.86, p_y - 12.70)
    elements.append(c_inst)
    elements.append(wire(cp1[0], cp1[1], p_x + 22.86, p_y - 7.62))
    elements.append(wire(p_x + 12.70, p_y - 7.62, p_x + 22.86, p_y - 7.62))
    elements.append(junction(p_x + 12.70, p_y - 7.62))
    elements.append(global_label("GND", cp2[0], cp2[1], rot=270))

    # Pin 3 (EN)
    p_x, p_y, _, _ = pins_u8['3']
    node_x = p_x - 12.70
    elements.append(wire(p_x, p_y, node_x, p_y))
    elements.append(h_label("VISION_RESET", node_x - 7.62, p_y, rot=180, shape="input"))
    elements.append(wire(node_x, p_y, node_x - 7.62, p_y))
    r_inst, rp1, rp2 = r_vert("R_VIS_EN", "10k", node_x, p_y - 7.62)
    elements.append(r_inst)
    elements.append(local_label("+3V3_VIS", rp1[0], rp1[1], rot=90))
    elements.append(wire(rp2[0], rp2[1], node_x, p_y))
    elements.append(junction(node_x, p_y))
    c_inst, cp1, cp2 = c_vert("C_VIS_EN", "1uF", "Capacitor_SMD:C_0603_1608Metric", node_x, p_y + 7.62)
    elements.append(c_inst)
    elements.append(wire(cp1[0], cp1[1], node_x, p_y))
    elements.append(global_label("GND", cp2[0], cp2[1], rot=270))

    # Pin 27 (IO0) Boot
    p_x, p_y, _, _ = pins_u8['27']
    node_boot_x = p_x - 12.70
    elements.append(wire(p_x, p_y, node_boot_x, p_y))
    elements.append(local_label("BOOT_VIS", node_boot_x, p_y, rot=180))
    r_inst, rp1, rp2 = r_vert("R_VIS_BOOT", "10k", node_boot_x, p_y - 7.62)
    elements.append(r_inst)
    elements.append(local_label("+3V3_VIS", rp1[0], rp1[1], rot=90))
    elements.append(wire(rp2[0], rp2[1], node_boot_x, p_y))
    elements.append(junction(node_boot_x, p_y))
    sw_x = node_boot_x - 12.70
    elements.append(sym_inst("Switch:SW_Push", "SW_VIS_BOOT", "SW_Push", "Button_Switch_SMD:SW_Push_SPST_NO_Alps_SKRK", sw_x, p_y))
    elements.append(wire(sw_x + 5.08, p_y, node_boot_x, p_y))
    elements.append(wire(sw_x - 5.08, p_y, sw_x - 10.16, p_y))
    elements.append(global_label("GND", sw_x - 10.16, p_y, rot=180))

    # Pin 39 (IO1 / TOF_RXD)
    p_x, p_y, _, _ = pins_u8['39']
    elements.append(wire(p_x, p_y, p_x - 10.16, p_y))
    elements.append(local_label("TOF_RXD", p_x - 10.16, p_y, rot=180))
    # Pin 38 (IO2 / TOF_TXD)
    p_x, p_y, _, _ = pins_u8['38']
    elements.append(wire(p_x, p_y, p_x - 10.16, p_y))
    elements.append(local_label("TOF_TXD", p_x - 10.16, p_y, rot=180))

    # Pin 15 (IO3 / CAM_LED_PWM)
    p_x, p_y, _, _ = pins_u8['15']
    elements.append(wire(p_x, p_y, p_x - 10.16, p_y))
    elements.append(local_label("CAM_LED_PWM", p_x - 10.16, p_y, rot=180))

    # Camera DVP pins on left side of U8:
    cam_u8_map = {
        '4': "CAM_SDA", '5': "CAM_SCL", '6': "CAM_VSYNC", '7': "CAM_HREF",
        '12': "CAM_D2", '17': "CAM_D1", '18': "CAM_D3", '19': "CAM_D0",
        '20': "CAM_D4", '21': "CAM_PCLK", '8': "CAM_XCLK", '9': "CAM_D7"
    }
    for pnum, net in cam_u8_map.items():
        p_x, p_y, _, _ = pins_u8[pnum]
        elements.append(wire(p_x, p_y, p_x - 10.16, p_y))
        elements.append(local_label(net, p_x - 10.16, p_y, rot=180))

    # Pull-ups on Camera SCCB I2C (CAM_SDA, CAM_SCL)
    sda_px, sda_py, _, _ = pins_u8['4']
    r_inst, rp1, rp2 = r_vert("R_CAM_SDA", "4.7k", sda_px - 20.32, sda_py - 7.62)
    elements.append(r_inst)
    elements.append(local_label("+3V3_VIS", rp1[0], rp1[1], rot=90))
    elements.append(wire(rp2[0], rp2[1], sda_px - 20.32, sda_py))
    elements.append(wire(sda_px - 20.32, sda_py, sda_px - 10.16, sda_py))
    elements.append(junction(sda_px - 10.16, sda_py))

    scl_px, scl_py, _, _ = pins_u8['5']
    r_inst, rp1, rp2 = r_vert("R_CAM_SCL", "4.7k", scl_px - 20.32, scl_py - 7.62)
    elements.append(r_inst)
    elements.append(local_label("+3V3_VIS", rp1[0], rp1[1], rot=90))
    elements.append(wire(rp2[0], rp2[1], scl_px - 20.32, scl_py))
    elements.append(wire(scl_px - 20.32, scl_py, scl_px - 10.16, scl_py))
    elements.append(junction(scl_px - 10.16, scl_py))

    # U8 Right side pins:
    p_x, p_y, _, _ = pins_u8['37']
    elements.append(wire(p_x, p_y, p_x + 10.16, p_y))
    elements.append(h_label("INTER_UART_TX", p_x + 10.16, p_y, rot=0, shape="output"))

    p_x, p_y, _, _ = pins_u8['36']
    elements.append(wire(p_x, p_y, p_x + 10.16, p_y))
    elements.append(h_label("INTER_UART_RX", p_x + 10.16, p_y, rot=0, shape="input"))

    p_x, p_y, _, _ = pins_u8['23']
    elements.append(wire(p_x, p_y, p_x + 10.16, p_y))
    elements.append(h_label("VISION_SYNC", p_x + 10.16, p_y, rot=0, shape="input"))

    p_x, p_y, _, _ = pins_u8['10']
    elements.append(wire(p_x, p_y, p_x + 10.16, p_y))
    elements.append(local_label("CAM_D6", p_x + 10.16, p_y))

    p_x, p_y, _, _ = pins_u8['11']
    elements.append(wire(p_x, p_y, p_x + 10.16, p_y))
    elements.append(local_label("CAM_D5", p_x + 10.16, p_y))

    p_x, p_y, _, _ = pins_u8['13']
    elements.append(wire(p_x, p_y, p_x + 10.16, p_y))
    elements.append(local_label("VIS_USB_D+", p_x + 10.16, p_y))

    p_x, p_y, _, _ = pins_u8['14']
    elements.append(wire(p_x, p_y, p_x + 10.16, p_y))
    elements.append(local_label("VIS_USB_D-", p_x + 10.16, p_y))

    p_x, p_y, _, _ = pins_u8['24']
    elements.append(wire(p_x, p_y, p_x + 10.16, p_y))
    elements.append(local_label("CAM_PWDN", p_x + 10.16, p_y))

    # Unused pins on U8 marked no_connect
    u8_unused = ['16', '22', '25', '26', '28', '29', '30', '31', '32', '33', '34', '35']
    for pnum in u8_unused:
        elements.append(no_conn(pins_u8[pnum][0], pins_u8[pnum][1]))

    # =========================================================================
    # ROW 2/3: J_CAM (Conn_01x24) at (266.70, 177.80)
    # =========================================================================
    pins_cam = get_pin_map(sym_c24, 266.70, 177.80)
    elements.append(sym_inst("Connector_Generic:Conn_01x24", "J_CAM", "OV3660_DVP_24P", "Connector_FFC-FPC:Hirose_FH12-24S-0.5SH_1x24-1MP_P0.50mm_Horizontal", 266.70, 177.80))
    cam_net_map = {
        '1': ("STROBE", False),
        '2': ("GND", True),
        '3': ("CAM_SDA", True),
        '4': ("+3V3_VIS", True),
        '5': ("CAM_SCL", True),
        '6': ("+3V3_VIS", True),
        '7': ("CAM_VSYNC", True),
        '8': ("CAM_PWDN", True),
        '9': ("CAM_HREF", True),
        '10': ("+3V3_VIS", True),
        '11': ("+3V3_VIS", True),
        '12': ("CAM_D7", True),
        '13': ("CAM_XCLK", True),
        '14': ("CAM_D6", True),
        '15': ("GND", True),
        '16': ("CAM_D5", True),
        '17': ("CAM_PCLK", True),
        '18': ("CAM_D4", True),
        '19': ("CAM_D0", True),
        '20': ("CAM_D3", True),
        '21': ("CAM_D1", True),
        '22': ("CAM_D2", True),
        '23': ("GND", True),
        '24': ("GND", True),
    }
    for pnum, (net, conn) in cam_net_map.items():
        px, py, _, _ = pins_cam[pnum]
        if conn:
            elements.append(wire(px, py, px - 10.16, py))
            if net == "GND":
                elements.append(global_label("GND", px - 10.16, py, rot=180))
            else:
                elements.append(local_label(net, px - 10.16, py, rot=180))
        else:
            elements.append(no_conn(px, py))

    c_inst, cp1, cp2 = c_vert("C_CAM1", "10uF", "Capacitor_SMD:C_0805_2012Metric", 292.10, 152.40)
    elements.append(c_inst)
    elements.append(local_label("+3V3_VIS", cp1[0], cp1[1], rot=90))
    elements.append(global_label("GND", cp2[0], cp2[1], rot=270))
    c_inst, cp1, cp2 = c_vert("C_CAM2", "100nF", "Capacitor_SMD:C_0603_1608Metric", 304.80, 152.40)
    elements.append(c_inst)
    elements.append(local_label("+3V3_VIS", cp1[0], cp1[1], rot=90))
    elements.append(global_label("GND", cp2[0], cp2[1], rot=270))

    footer = "\n)\n"
    content = header + "\n" + "\n".join(elements) + footer
    return content

def update_root_schematic(root_text):
    text = root_text

    # 1. Disconnect J1 data pins with no_connect
    wires_to_replace = [
        '\t(wire (pts (xy 50.80 72.39) (xy 46.99 72.39)) (stroke (width 0) (type default)) (uuid "833eff8f-b585-401a-9a97-a5141c1050e2"))',
        '\t(wire (pts (xy 50.80 74.93) (xy 46.99 74.93)) (stroke (width 0) (type default)) (uuid "9e46a1c3-4d3f-4f4e-92da-c437d98ddd48"))',
        '\t(wire (pts (xy 50.80 67.31) (xy 46.99 67.31)) (stroke (width 0) (type default)) (uuid "f05eb75a-538c-44a5-b8c3-da118a2591d7"))',
        '\t(wire (pts (xy 50.80 69.85) (xy 46.99 69.85)) (stroke (width 0) (type default)) (uuid "bb846bfc-c6f8-4fec-b30c-696068f23f93"))'
    ]
    replacement_nc = f"""\t(no_connect (at 50.80 72.39) (uuid "{uid()}"))
\t(no_connect (at 50.80 74.93) (uuid "{uid()}"))
\t(no_connect (at 50.80 67.31) (uuid "{uid()}"))
\t(no_connect (at 50.80 69.85) (uuid "{uid()}"))"""

    combined_wires = "\n".join(wires_to_replace)
    if combined_wires in text:
        text = text.replace(combined_wires, replacement_nc)
    else:
        for w, coord in zip(wires_to_replace, [(50.80, 72.39), (50.80, 74.93), (50.80, 67.31), (50.80, 69.85)]):
            if w in text:
                text = text.replace(w, f'\t(no_connect (at {coord[0]:.2f} {coord[1]:.2f}) (uuid "{uid()}"))')

    # 2. Remove the 4 J1 global labels for USB_D+ and USB_D-
    label_uuids = [
        "e62d2ace-e139-4559-95fb-6e1a89d93987",
        "8a2dc7bb-c423-4c94-9f26-b56b8db250da",
        "23ae5533-d1c0-46d3-be2d-c8d460a91e32",
        "20623260-9653-4f66-a458-5c259cbaf404"
    ]
    for luuid in label_uuids:
        idx = text.find(f'(uuid "{luuid}")')
        if idx != -1:
            start_lbl = text.rfind('\t(global_label', 0, idx)
            end_lbl = text.find('\n\t)', idx)
            if start_lbl != -1 and end_lbl != -1:
                text = text[:start_lbl] + text[end_lbl+3:]

    # 3. Remove no_connect on U1 pins 4, 8, 9, 22
    u1_nc_coords = ["(at 80.01 290.83)", "(at 80.01 318.77)", "(at 80.01 321.31)", "(at 80.01 316.23)"]
    for nc_c in u1_nc_coords:
        idx = text.find(nc_c)
        if idx != -1:
            line_start = text.rfind('\t(no_connect', 0, idx)
            line_end = text.find('\n', idx)
            if line_start != -1 and line_end != -1:
                text = text[:line_start] + text[line_end+1:]

    # Update paper to A1
    text = text.replace('(paper "A2")', '(paper "A1")', 1)

    # 4. Wire U1 pins 4, 8, 9, 22 to inter-MCU signals
    u1_wiring = f"""
\t(wire (pts (xy 80.01 290.83) (xy 71.12 290.83)) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "VISION_SYNC" (shape bidirectional) (at 71.12 290.83 180) (effects (font (size 1.27 1.27)) (justify right)) (uuid "{uid()}"))
\t(wire (pts (xy 80.01 318.77) (xy 71.12 318.77)) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "INTER_UART_RX" (shape bidirectional) (at 71.12 318.77 180) (effects (font (size 1.27 1.27)) (justify right)) (uuid "{uid()}"))
\t(wire (pts (xy 80.01 321.31) (xy 71.12 321.31)) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "INTER_UART_TX" (shape bidirectional) (at 71.12 321.31 180) (effects (font (size 1.27 1.27)) (justify right)) (uuid "{uid()}"))
\t(wire (pts (xy 80.01 316.23) (xy 71.12 316.23)) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "VISION_RESET" (shape bidirectional) (at 71.12 316.23 180) (effects (font (size 1.27 1.27)) (justify right)) (uuid "{uid()}"))"""

    # 5. SECTION 9: Add J2 (J_USB_MAIN) at (60.96, 444.50)
    sec9_header = f"""\t(text "SECTION 9: ESP32-S3 VISION COPROCESSOR & TRIPLE USB-C INTERFACE" (at 19.24 400.00 0) (effects (font (size 2.54 2.54) bold (color 0 100 180 1))) (uuid "{uid()}"))\n"""

    sym_usb = get_full_symbol(root_text, "Connector:USB_C_Receptacle_USB2.0_16P")
    pins_j2 = get_pin_map(sym_usb, 60.96, 444.50)
    j2_inst = sym_inst("Connector:USB_C_Receptacle_USB2.0_16P", "J2", "USB-C_MAIN", "Connector_USB:USB_C_Receptacle_HCTL_HC-TYPE-C-16P-01A", 60.96, 444.50)

    dp_a_x, dp_a_y, _, _ = pins_j2['A6']
    dp_b_x, dp_b_y, _, _ = pins_j2['B6']
    dm_a_x, dm_a_y, _, _ = pins_j2['A7']
    dm_b_x, dm_b_y, _, _ = pins_j2['B7']
    gnd_x, gnd_y, _, _ = pins_j2['A1']
    sh_x, sh_y, _, _ = pins_j2['SH']
    vbus_x, vbus_y, _, _ = pins_j2['A4']
    cc1_x, cc1_y, _, _ = pins_j2['A5']
    cc2_x, cc2_y, _, _ = pins_j2['B5']

    r_cc3, r3_p1, r3_p2 = r_vert("R_CC3", "5.1k", cc1_x + 15.24, cc1_y + 3.81)
    r_cc4, r4_p1, r4_p2 = r_vert("R_CC4", "5.1k", cc2_x + 25.40, cc2_y + 3.81)
    c_vbus, cv_p1, cv_p2 = c_vert("C_VBUS_MAIN", "100nF", "Capacitor_SMD:C_0603_1608Metric", vbus_x + 10.16, vbus_y + 7.62)

    j2_block = f"""
{sec9_header}
{j2_inst}
\t(wire (pts (xy {dp_a_x:.2f} {dp_a_y:.2f}) (xy {dp_a_x + 10.16:.2f} {dp_a_y:.2f})) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(wire (pts (xy {dp_b_x:.2f} {dp_b_y:.2f}) (xy {dp_a_x + 10.16:.2f} {dp_a_y:.2f})) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "USB_D+" (shape bidirectional) (at {dp_a_x + 10.16:.2f} {dp_a_y:.2f} 0) (effects (font (size 1.27 1.27)) (justify left)) (uuid "{uid()}"))
\t(wire (pts (xy {dm_a_x:.2f} {dm_a_y:.2f}) (xy {dm_a_x + 10.16:.2f} {dm_a_y:.2f})) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(wire (pts (xy {dm_b_x:.2f} {dm_b_y:.2f}) (xy {dm_a_x + 10.16:.2f} {dm_a_y:.2f})) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "USB_D-" (shape bidirectional) (at {dm_a_x + 10.16:.2f} {dm_a_y:.2f} 0) (effects (font (size 1.27 1.27)) (justify left)) (uuid "{uid()}"))
\t(wire (pts (xy {sh_x:.2f} {sh_y:.2f}) (xy {gnd_x:.2f} {gnd_y:.2f})) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(wire (pts (xy {gnd_x:.2f} {gnd_y:.2f}) (xy {gnd_x:.2f} {gnd_y + 7.62:.2f})) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "GND" (shape bidirectional) (at {gnd_x:.2f} {gnd_y + 7.62:.2f} 270) (effects (font (size 1.27 1.27)) (justify right)) (uuid "{uid()}"))
\t(no_connect (at {pins_j2['A8'][0]:.2f} {pins_j2['A8'][1]:.2f}) (uuid "{uid()}"))
\t(no_connect (at {pins_j2['B8'][0]:.2f} {pins_j2['B8'][1]:.2f}) (uuid "{uid()}"))
{r_cc3}
\t(wire (pts (xy {cc1_x:.2f} {cc1_y:.2f}) (xy {r3_p1[0]:.2f} {r3_p1[1]:.2f})) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "GND" (shape bidirectional) (at {r3_p2[0]:.2f} {r3_p2[1]:.2f} 270) (effects (font (size 1.27 1.27)) (justify right)) (uuid "{uid()}"))
{r_cc4}
\t(wire (pts (xy {cc2_x:.2f} {cc2_y:.2f}) (xy {r4_p1[0]:.2f} {r4_p1[1]:.2f})) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "GND" (shape bidirectional) (at {r4_p2[0]:.2f} {r4_p2[1]:.2f} 270) (effects (font (size 1.27 1.27)) (justify right)) (uuid "{uid()}"))
{c_vbus}
\t(wire (pts (xy {vbus_x:.2f} {vbus_y:.2f}) (xy {vbus_x + 10.16:.2f} {vbus_y:.2f})) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(wire (pts (xy {vbus_x + 10.16:.2f} {vbus_y:.2f}) (xy {cv_p1[0]:.2f} {cv_p1[1]:.2f})) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(junction (at {vbus_x + 10.16:.2f} {vbus_y:.2f}))
\t(global_label "VBUS_MAIN" (shape bidirectional) (at {vbus_x + 10.16:.2f} {vbus_y:.2f} 0) (effects (font (size 1.27 1.27)) (justify left)) (uuid "{uid()}"))
\t(global_label "GND" (shape bidirectional) (at {cv_p2[0]:.2f} {cv_p2[1]:.2f} 270) (effects (font (size 1.27 1.27)) (justify right)) (uuid "{uid()}"))"""

    # 6. Add Hierarchical Sheet for Vision_Coprocessor at (165.10, 419.10)
    sheet_uuid = "3c162b70-9b48-4cb3-a9d9-df720eb9aa32"
    p_uart_tx = uid()
    p_uart_rx = uid()
    p_sync = uid()
    p_rst = uid()

    sheet_block = f"""
\t(sheet
\t\t(at 165.10 419.10)
\t\t(size 63.50 43.18)
\t\t(exclude_from_sim no)
\t\t(in_bom yes)
\t\t(on_board yes)
\t\t(dnp no)
\t\t(fields_autoplaced yes)
\t\t(stroke
\t\t\t(width 0.1524)
\t\t\t(type solid)
\t\t)
\t\t(fill
\t\t\t(color 0 0 0 0.0000)
\t\t)
\t\t(uuid "{sheet_uuid}")
\t\t(property "Sheetname" "Vision_Coprocessor"
\t\t\t(at 165.10 415.29 0)
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t)
\t\t\t\t(justify left bottom)
\t\t\t)
\t\t)
\t\t(property "Sheetfile" "Hexapod_Vision_Subsystem.kicad_sch"
\t\t\t(at 165.10 466.09 0)
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t)
\t\t\t\t(justify left top)
\t\t\t)
\t\t)
\t\t(pin "INTER_UART_TX" output
\t\t\t(at 228.60 431.80 0)
\t\t\t(uuid "{p_uart_tx}")
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t)
\t\t\t\t(justify right)
\t\t\t)
\t\t)
\t\t(pin "INTER_UART_RX" input
\t\t\t(at 228.60 436.88 0)
\t\t\t(uuid "{p_uart_rx}")
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t)
\t\t\t\t(justify right)
\t\t\t)
\t\t)
\t\t(pin "VISION_SYNC" input
\t\t\t(at 228.60 447.04 0)
\t\t\t(uuid "{p_sync}")
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t)
\t\t\t\t(justify right)
\t\t\t)
\t\t)
\t\t(pin "VISION_RESET" input
\t\t\t(at 228.60 452.12 0)
\t\t\t(uuid "{p_rst}")
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t)
\t\t\t\t(justify right)
\t\t\t)
\t\t)
\t\t(instances
\t\t\t(project "Hexapod_Robot_Board"
\t\t\t\t(path "/44f02a75-3141-486c-ae96-cf48718534a3"
\t\t\t\t\t(page "2")
\t\t\t\t)
\t\t\t)
\t\t)
\t)
\t(wire (pts (xy 228.60 431.80) (xy 238.76 431.80)) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "INTER_UART_TX" (shape bidirectional) (at 238.76 431.80 0) (effects (font (size 1.27 1.27)) (justify left)) (uuid "{uid()}"))
\t(wire (pts (xy 228.60 436.88) (xy 238.76 436.88)) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "INTER_UART_RX" (shape bidirectional) (at 238.76 436.88 0) (effects (font (size 1.27 1.27)) (justify left)) (uuid "{uid()}"))
\t(wire (pts (xy 228.60 447.04) (xy 238.76 447.04)) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "VISION_SYNC" (shape bidirectional) (at 238.76 447.04 0) (effects (font (size 1.27 1.27)) (justify left)) (uuid "{uid()}"))
\t(wire (pts (xy 228.60 452.12) (xy 238.76 452.12)) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "VISION_RESET" (shape bidirectional) (at 238.76 452.12 0) (effects (font (size 1.27 1.27)) (justify left)) (uuid "{uid()}"))"""

    # 7. Uncross PCA9685 PWM mappings
    # PCA U5 (0x40): Left PWM (L4, L5, L6, AUX4..6)
    pca_u5_map = [
        (242.57, 292.10, "PWM_0", "PWM_L4_C"),
        (245.11, 292.10, "PWM_1", "PWM_L4_F"),
        (247.65, 292.10, "PWM_2", "PWM_L4_T"),
        (250.19, 292.10, "PWM_3", "PWM_L5_C"),
        (252.73, 292.10, "PWM_4", "PWM_L5_F"),
        (255.27, 292.10, "PWM_5", "PWM_L5_T"),
        (257.81, 292.10, "PWM_6", "PWM_L6_C"),
        (260.35, 292.10, "PWM_7", "PWM_L6_F"),
        (262.89, 302.26, "PWM_8", "PWM_L6_T"),
        (265.43, 302.26, "PWM_9", "PWM_AUX4"),
        (267.97, 302.26, "PWM_10", "PWM_AUX5"),
        (270.51, 302.26, "PWM_11", "PWM_AUX6"),
    ]
    for y, x, old_name, new_name in pca_u5_map:
        pattern = re.compile(rf'(\(global_label\s+\"){re.escape(old_name)}(\"\s+\(shape\s+output\)\s+\(at\s+{x:.2f}\s+{y:.2f})')
        text = pattern.sub(rf'\g<1>{new_name}\g<2>', text)

    # U5 pins 19..22: remove global label and wire, replace with no_connect at 297.18
    for y, old_name in [(273.05, "PWM_12"), (275.59, "PWM_13"), (278.13, "PWM_14"), (280.67, "PWM_15")]:
        pattern_lbl = re.compile(rf'\t\(global_label\s+\"{old_name}\"\s+\(shape\s+output\)\s+\(at\s+302\.26\s+{y:.2f}[^\)]*\).*?\n\t\)\n', re.DOTALL)
        text = pattern_lbl.sub('', text)
        pattern_w = re.compile(rf'\t\(wire\s+\(pts\s+\(xy\s+297\.18\s+{y:.2f}\)\s+\(xy\s+302\.26\s+{y:.2f}\)\)[^\n]*\n')
        text = pattern_w.sub(f'\t(no_connect (at 297.18 {y:.2f}) (uuid "{uid()}"))\n', text)

    # PCA U6 (0x41): Right PWM (L1, L2, L3, AUX1..3)
    pca_u6_map = [
        (331.47, 292.10, "PWM_16", "PWM_L1_C"),
        (334.01, 292.10, "PWM_17", "PWM_L1_F"),
        (336.55, 292.10, "PWM_18", "PWM_L1_T"),
        (339.09, 292.10, "PWM_19", "PWM_L2_C"),
        (341.63, 292.10, "PWM_20", "PWM_L2_F"),
        (344.17, 292.10, "PWM_21", "PWM_L2_T"),
        (346.71, 292.10, "PWM_22", "PWM_L3_C"),
        (349.25, 292.10, "PWM_23", "PWM_L3_F"),
    ]
    for y, x, old_name, new_name in pca_u6_map:
        pattern = re.compile(rf'(\(global_label\s+\"){re.escape(old_name)}(\"\s+\(shape\s+output\)\s+\(at\s+{x:.2f}\s+{y:.2f})')
        text = pattern.sub(rf'\g<1>{new_name}\g<2>', text)

    # U6 pins 15..18: remove no_connect, add wire to 302.26, add global_label
    u6_new_pins = [
        (351.79, "PWM_L3_T"),
        (354.33, "PWM_AUX1"),
        (356.87, "PWM_AUX2"),
        (359.41, "PWM_AUX3"),
    ]
    for y, net in u6_new_pins:
        pattern_nc = re.compile(rf'\t\(no_connect\s+\(at\s+297\.18\s+{y:.2f}\)\s+\(uuid\s+\"[^\"]+\"\)\)\n')
        replacement = f"""\t(wire (pts (xy 297.18 {y:.2f}) (xy 302.26 {y:.2f})) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "{net}" (shape output) (at 302.26 {y:.2f} 0) (effects (font (size 1.27 1.27)) (justify left)) (uuid "{uid()}"))\n"""
        text = pattern_nc.sub(replacement, text)

    # Header labels:
    headers_map = [
        # Leg 1
        (416.56, 237.49, "PWM_0", "PWM_L1_C"),
        (416.56, 262.89, "PWM_1", "PWM_L1_F"),
        (416.56, 288.29, "PWM_2", "PWM_L1_T"),
        # Leg 2
        (416.56, 313.69, "PWM_3", "PWM_L2_C"),
        (416.56, 339.09, "PWM_4", "PWM_L2_F"),
        (416.56, 364.49, "PWM_5", "PWM_L2_T"),
        # Leg 3
        (464.82, 237.49, "PWM_6", "PWM_L3_C"),
        (464.82, 262.89, "PWM_7", "PWM_L3_F"),
        (464.82, 288.29, "PWM_8", "PWM_L3_T"),
        # Leg 4
        (464.82, 313.69, "PWM_9", "PWM_L4_C"),
        (464.82, 339.09, "PWM_10", "PWM_L4_F"),
        (464.82, 364.49, "PWM_11", "PWM_L4_T"),
        # Leg 5
        (513.08, 237.49, "PWM_12", "PWM_L5_C"),
        (513.08, 262.89, "PWM_13", "PWM_L5_F"),
        (513.08, 288.29, "PWM_14", "PWM_L5_T"),
        # Leg 6
        (513.08, 313.69, "PWM_15", "PWM_L6_C"),
        (513.08, 339.09, "PWM_16", "PWM_L6_F"),
        (513.08, 364.49, "PWM_17", "PWM_L6_T"),
        # AUX 1..3
        (561.34, 237.49, "PWM_18", "PWM_AUX1"),
        (561.34, 262.89, "PWM_19", "PWM_AUX2"),
        (561.34, 288.29, "PWM_20", "PWM_AUX3"),
        # AUX 4..6
        (561.34, 313.69, "PWM_21", "PWM_AUX4"),
        (561.34, 339.09, "PWM_22", "PWM_AUX5"),
        (561.34, 364.49, "PWM_23", "PWM_AUX6"),
    ]
    for x, y, old_name, new_name in headers_map:
        pattern = re.compile(rf'(\(global_label\s+\"){re.escape(old_name)}(\"\s+\(shape\s+input\)\s+\(at\s+{x:.2f}\s+{y:.2f})')
        text = pattern.sub(rf'\g<1>{new_name}\g<2>', text)

    # 8. Add J_SW_EXT (External Power Switch Header) at (213.36, 38.10)
    sw_ext_block = f"""
\t(symbol
\t\t(lib_id "Connector_Generic:Conn_01x02")
\t\t(at 213.36 38.10 0)
\t\t(unit 1)
\t\t(exclude_from_sim no)
\t\t(in_bom yes)
\t\t(on_board yes)
\t\t(dnp no)
\t\t(uuid "{uid()}")
\t\t(property "Reference" "J_SW_EXT" (at 213.36 35.56 0) (effects (font (size 1.27 1.27))))
\t\t(property "Value" "SW_EXT" (at 213.36 40.64 0) (effects (font (size 1.27 1.27))))
\t\t(property "Footprint" "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical" (at 213.36 38.10 0) (hide yes) (effects (font (size 1.27 1.27))))
\t\t(property "Datasheet" "~" (at 213.36 38.10 0) (hide yes) (effects (font (size 1.27 1.27))))
\t\t(instances
\t\t\t(project "Hexapod_Robot_Board"
\t\t\t\t(path "/44f02a75-3141-486c-ae96-cf48718534a3"
\t\t\t\t\t(reference "J_SW_EXT")
\t\t\t\t\t(unit 1)
\t\t\t\t)
\t\t\t)
\t\t)
\t)
\t(wire (pts (xy 208.28 38.10) (xy 200.66 38.10)) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "VBAT" (shape bidirectional) (at 200.66 38.10 180) (effects (font (size 1.27 1.27)) (justify right)) (uuid "{uid()}"))
\t(wire (pts (xy 208.28 40.64) (xy 200.66 40.64)) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "VBAT_SW" (shape bidirectional) (at 200.66 40.64 180) (effects (font (size 1.27 1.27)) (justify right)) (uuid "{uid()}"))"""

    # 9. Add Status NeoPixel LED_RGB_MAIN on U1 pin 25 (GPIO 48)
    pattern_nc25 = re.compile(r'\t\(no_connect\s+\(at\s+110\.49\s+321\.31\)\s+\(uuid\s+\"[^\"]+\"\)\)\n')
    text = pattern_nc25.sub('', text)

    with open('/home/peacemaker/.local/share/kicad-appimage/share/kicad/symbols/LED.kicad_symdir/WS2812B-2020.kicad_sym', 'r') as f:
        sym_ws = get_full_symbol(f.read(), 'WS2812B-2020')
    sym_ws = sym_ws.replace('(symbol "WS2812B-2020"', '(symbol "LED:WS2812B-2020"', 1)

    idx_lib = text.find('(lib_symbols')
    depth = 0
    close_idx = -1
    for i in range(idx_lib, len(text)):
        if text[i] == '(':
            depth += 1
        elif text[i] == ')':
            depth -= 1
            if depth == 0:
                close_idx = i
                break
    text = text[:close_idx] + f"\n\t\t{sym_ws}\n\t" + text[close_idx:]

    neo_block = f"""
\t(wire (pts (xy 110.49 321.31) (xy 120.65 321.31)) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(symbol
\t\t(lib_id "Device:R")
\t\t(at 124.46 321.31 90)
\t\t(unit 1)
\t\t(exclude_from_sim no)
\t\t(in_bom yes)
\t\t(on_board yes)
\t\t(dnp no)
\t\t(uuid "{uid()}")
\t\t(property "Reference" "R_NEO" (at 124.46 317.50 90) (effects (font (size 1.27 1.27))))
\t\t(property "Value" "330" (at 124.46 325.12 90) (effects (font (size 1.27 1.27))))
\t\t(property "Footprint" "Resistor_SMD:R_0603_1608Metric" (at 124.46 321.31 0) (hide yes) (effects (font (size 1.27 1.27))))
\t\t(property "Datasheet" "~" (at 124.46 321.31 0) (hide yes) (effects (font (size 1.27 1.27))))
\t\t(instances
\t\t\t(project "Hexapod_Robot_Board"
\t\t\t\t(path "/44f02a75-3141-486c-ae96-cf48718534a3"
\t\t\t\t\t(reference "R_NEO")
\t\t\t\t\t(unit 1)
\t\t\t\t)
\t\t\t)
\t\t)
\t)
\t(wire (pts (xy 128.27 321.31) (xy 135.89 321.31)) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(symbol
\t\t(lib_id "LED:WS2812B-2020")
\t\t(at 143.51 321.31 0)
\t\t(unit 1)
\t\t(exclude_from_sim no)
\t\t(in_bom yes)
\t\t(on_board yes)
\t\t(dnp no)
\t\t(uuid "{uid()}")
\t\t(property "Reference" "LED_RGB_MAIN" (at 143.51 313.69 0) (effects (font (size 1.27 1.27))))
\t\t(property "Value" "WS2812B-2020" (at 143.51 328.93 0) (effects (font (size 1.27 1.27))))
\t\t(property "Footprint" "LED_SMD:LED_WS2812B-2020_PLCC4_2.0x2.0mm" (at 143.51 321.31 0) (hide yes) (effects (font (size 1.27 1.27))))
\t\t(property "Datasheet" "https://cdn-shop.adafruit.com/product-files/4684/4684_WS2812B-2020_V1.3_EN.pdf" (at 143.51 321.31 0) (hide yes) (effects (font (size 1.27 1.27))))
\t\t(instances
\t\t\t(project "Hexapod_Robot_Board"
\t\t\t\t(path "/44f02a75-3141-486c-ae96-cf48718534a3"
\t\t\t\t\t(reference "LED_RGB_MAIN")
\t\t\t\t\t(unit 1)
\t\t\t\t)
\t\t\t)
\t\t)
\t)
\t(no_connect (at 151.13 321.31) (uuid "{uid()}"))
\t(wire (pts (xy 143.51 328.93) (xy 143.51 334.01)) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "GND" (shape bidirectional) (at 143.51 334.01 270) (effects (font (size 1.27 1.27)) (justify right)) (uuid "{uid()}"))
\t(wire (pts (xy 143.51 313.69) (xy 143.51 308.61)) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "+3V3" (shape bidirectional) (at 143.51 308.61 90) (effects (font (size 1.27 1.27)) (justify left)) (uuid "{uid()}"))
\t(symbol
\t\t(lib_id "Device:C")
\t\t(at 156.21 321.31 0)
\t\t(unit 1)
\t\t(exclude_from_sim no)
\t\t(in_bom yes)
\t\t(on_board yes)
\t\t(dnp no)
\t\t(uuid "{uid()}")
\t\t(property "Reference" "C_NEO" (at 156.21 316.23 0) (effects (font (size 1.27 1.27))))
\t\t(property "Value" "100nF" (at 156.21 326.39 0) (effects (font (size 1.27 1.27))))
\t\t(property "Footprint" "Capacitor_SMD:C_0603_1608Metric" (at 156.21 321.31 0) (hide yes) (effects (font (size 1.27 1.27))))
\t\t(property "Datasheet" "~" (at 156.21 321.31 0) (hide yes) (effects (font (size 1.27 1.27))))
\t\t(instances
\t\t\t(project "Hexapod_Robot_Board"
\t\t\t\t(path "/44f02a75-3141-486c-ae96-cf48718534a3"
\t\t\t\t\t(reference "C_NEO")
\t\t\t\t\t(unit 1)
\t\t\t\t)
\t\t\t)
\t\t)
\t)
\t(wire (pts (xy 156.21 317.50) (xy 156.21 308.61)) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(wire (pts (xy 156.21 308.61) (xy 143.51 308.61)) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(junction (at 143.51 308.61))
\t(wire (pts (xy 156.21 325.12) (xy 156.21 334.01)) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(wire (pts (xy 156.21 334.01) (xy 143.51 334.01)) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(junction (at 143.51 334.01))"""

    last_paren = text.rfind(')')
    final_text = text[:last_paren] + u1_wiring + j2_block + sheet_block + sw_ext_block + neo_block + "\n)\n"
    return final_text

def main():
    print("1. Reverting Hexapod_Robot_Board.kicad_sch to clean git version...")
    subprocess.run(["git", "checkout", "Hexapod_Robot_Board.kicad_sch"], check=True)

    print("2. Reading clean root schematic...")
    with open("Hexapod_Robot_Board.kicad_sch", "r", encoding="utf-8") as f:
        root_content = f.read()

    print("3. Building Hexapod_Vision_Subsystem.kicad_sch (with 1-3W Camera LED Driver)...")
    vis_sch = build_vision_subsheet(root_content)
    with open("Hexapod_Vision_Subsystem.kicad_sch", "w", encoding="utf-8") as f:
        f.write(vis_sch)
    print("   Hexapod_Vision_Subsystem.kicad_sch created successfully.")

    print("4. Updating Hexapod_Robot_Board.kicad_sch (Uncrossing PWM, J_SW_EXT, LED_RGB_MAIN, J2)...")
    updated_root = update_root_schematic(root_content)
    with open("Hexapod_Robot_Board.kicad_sch", "w", encoding="utf-8") as f:
        f.write(updated_root)
    print("   Hexapod_Robot_Board.kicad_sch updated successfully.")

if __name__ == '__main__':
    main()
