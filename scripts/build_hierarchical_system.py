#!/usr/bin/env python3
"""
build_hierarchical_system.py

Generates:
1. Hexapod_Vision_Subsystem.kicad_sch (ESP32-S3 Vision Coprocessor subsheet)
2. Updates Hexapod_Robot_Board.kicad_sch (Root schematic):
   - J1 data disconnected (charging only)
   - J2 added (Main MCU USB-C) with CC resistors
   - Vision_Coprocessor hierarchical sheet instantiated
   - U1 inter-MCU signals wired cleanly
"""

import uuid
import re
import os

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
        r'\(pin\s+[^\s]+\s+line\s+\(at\s+([-\d.]+)\s+([-\d.]+)\s+(\d+)\).*?\(name\s+"([^"]+)".*?\(number\s+"([^"]+)"',
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

def sym_inst(lib_id, ref, val, fp, x, y, rot=0, props=None):
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
\t)"""

def wire(x1, y1, x2, y2):
    return f'\t(wire (pts (xy {x1:.2f} {y1:.2f}) (xy {x2:.2f} {y2:.2f})) (stroke (width 0) (type default)) (uuid "{uid()}"))'

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

def r_vert(ref, val, x, y):
    """Vertical resistor with pin 1 at (x, y-3.81) and pin 2 at (x, y+3.81)"""
    inst = sym_inst("Device:R", ref, val, "Resistor_SMD:R_0603_1608Metric", x, y, rot=0)
    p1 = (round(x/1.27)*1.27, round((y-3.81)/1.27)*1.27)
    p2 = (round(x/1.27)*1.27, round((y+3.81)/1.27)*1.27)
    return inst, p1, p2

def c_vert(ref, val, fp, x, y):
    """Vertical capacitor with pin 1 at (x, y-3.81) and pin 2 at (x, y+3.81)"""
    inst = sym_inst("Device:C", ref, val, fp, x, y, rot=0)
    p1 = (round(x/1.27)*1.27, round((y-3.81)/1.27)*1.27)
    p2 = (round(x/1.27)*1.27, round((y+3.81)/1.27)*1.27)
    return inst, p1, p2

def build_vision_subsheet(main_sch_text):
    sym_esp = get_full_symbol(main_sch_text, "RF_Module:ESP32-S3-WROOM-1")
    conn24_path = '/home/peacemaker/.local/share/kicad-appimage/share/kicad/symbols/Connector_Generic.kicad_symdir/Conn_01x24.kicad_sym'
    with open(conn24_path, 'r', encoding='utf-8') as f:
        c24_raw = f.read()
    sym_c24 = get_full_symbol(c24_raw, 'Conn_01x24')
    sym_c24 = sym_c24.replace('(symbol "Conn_01x24"', '(symbol "Connector_Generic:Conn_01x24"', 1)
    sym_c4  = get_full_symbol(main_sch_text, "Connector_Generic:Conn_01x04")
    sym_usb = get_full_symbol(main_sch_text, "Connector:USB_C_Receptacle_USB2.0_16P")
    sym_ams = get_full_symbol(main_sch_text, "Regulator_Linear:AMS1117-3.3")
    sym_r   = get_full_symbol(main_sch_text, "Device:R")
    sym_c   = get_full_symbol(main_sch_text, "Device:C")
    sym_sw  = get_full_symbol(main_sch_text, "Switch:SW_Push")

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
\t\t{sym_usb}
\t\t{sym_ams}
\t\t{sym_r}
\t\t{sym_c}
\t\t{sym_sw}
\t)"""

    elements = []

    # Sheet hierarchical pins (left edge)
    # VBAT_SW at (25.40, 38.10)
    # GND at (25.40, 50.80)
    # INTER_UART_TX at (25.40, 114.30)
    # INTER_UART_RX at (25.40, 127.00)
    # VISION_SYNC at (25.40, 139.70)
    # VISION_RESET at (25.40, 152.40)
    elements.append(h_label("VBAT_SW", 25.40, 38.10, shape="input"))
    elements.append(h_label("GND", 25.40, 50.80, shape="input"))
    elements.append(h_label("INTER_UART_TX", 25.40, 114.30, shape="output"))
    elements.append(h_label("INTER_UART_RX", 25.40, 127.00, shape="input"))
    elements.append(h_label("VISION_SYNC", 25.40, 139.70, shape="input"))
    elements.append(h_label("VISION_RESET", 25.40, 152.40, shape="input"))

    # Connect sheet pins to local nets
    elements.append(wire(25.40, 38.10, 38.10, 38.10))
    elements.append(local_label("VBAT_SW", 38.10, 38.10))
    elements.append(wire(25.40, 50.80, 38.10, 50.80))
    elements.append(local_label("GND", 38.10, 50.80))
    elements.append(wire(25.40, 114.30, 38.10, 114.30))
    elements.append(local_label("INTER_UART_TX", 38.10, 114.30))
    elements.append(wire(25.40, 127.00, 38.10, 127.00))
    elements.append(local_label("INTER_UART_RX", 38.10, 127.00))
    elements.append(wire(25.40, 139.70, 38.10, 139.70))
    elements.append(local_label("VISION_SYNC", 38.10, 139.70))
    elements.append(wire(25.40, 152.40, 38.10, 152.40))
    elements.append(local_label("VISION_RESET", 38.10, 152.40))

    # =========================================================================
    # ROW 1: REGULATORS (Y = 63.50)
    # =========================================================================
    # U_REG_5V_TOF at (88.90, 63.50)
    # AMS1117 pin 1 (GND): (88.90, 71.12)
    # AMS1117 pin 2 (VO):  (96.52, 63.50)
    # AMS1117 pin 3 (VI):  (81.28, 63.50)
    elements.append(sym_inst("Regulator_Linear:AMS1117-3.3", "U_REG_5V_TOF", "AMS1117-5.0", "Package_TO_SOT_SMD:SOT-223-3_TabPin2", 88.90, 63.50))
    # VI
    elements.append(wire(81.28, 63.50, 63.50, 63.50))
    elements.append(local_label("VBAT_SW", 63.50, 63.50, rot=180))
    # Input Cap C_TOF_IN (10uF) at (71.12, 73.66)
    c_inst, cp1, cp2 = c_vert("C_TOF_IN", "10uF", "Capacitor_SMD:C_0805_2012Metric", 71.12, 73.66)
    elements.append(c_inst)
    elements.append(wire(cp1[0], cp1[1], 71.12, 63.50))
    elements.append(local_label("GND", cp2[0], cp2[1]))
    # GND Pin 1
    elements.append(wire(88.90, 71.12, 88.90, 76.20))
    elements.append(local_label("GND", 88.90, 76.20))
    # VO
    elements.append(wire(96.52, 63.50, 114.30, 63.50))
    elements.append(local_label("+5V_TOF", 114.30, 63.50))
    # Output Cap C_TOF_OUT (22uF) at (104.14, 73.66)
    c_inst, cp1, cp2 = c_vert("C_TOF_OUT", "22uF", "Capacitor_SMD:C_0805_2012Metric", 104.14, 73.66)
    elements.append(c_inst)
    elements.append(wire(cp1[0], cp1[1], 104.14, 63.50))
    elements.append(local_label("GND", cp2[0], cp2[1]))

    # U_LDO_VIS at (177.80, 63.50)
    # AMS1117 pin 1 (GND): (177.80, 71.12)
    # AMS1117 pin 2 (VO):  (185.42, 63.50)
    # AMS1117 pin 3 (VI):  (170.18, 63.50)
    elements.append(sym_inst("Regulator_Linear:AMS1117-3.3", "U_LDO_VIS", "AMS1117-3.3", "Package_TO_SOT_SMD:SOT-223-3_TabPin2", 177.80, 63.50))
    # VI
    elements.append(wire(170.18, 63.50, 152.40, 63.50))
    elements.append(local_label("VBAT_SW", 152.40, 63.50, rot=180))
    # Input Cap C_VIS_IN (10uF) at (160.02, 73.66)
    c_inst, cp1, cp2 = c_vert("C_VIS_IN", "10uF", "Capacitor_SMD:C_0805_2012Metric", 160.02, 73.66)
    elements.append(c_inst)
    elements.append(wire(cp1[0], cp1[1], 160.02, 63.50))
    elements.append(local_label("GND", cp2[0], cp2[1]))
    # GND Pin 1
    elements.append(wire(177.80, 71.12, 177.80, 76.20))
    elements.append(local_label("GND", 177.80, 76.20))
    # VO
    elements.append(wire(185.42, 63.50, 203.20, 63.50))
    elements.append(local_label("+3V3_VIS", 203.20, 63.50))
    # Output Cap C_VIS_OUT (22uF) at (193.04, 73.66)
    c_inst, cp1, cp2 = c_vert("C_VIS_OUT", "22uF", "Capacitor_SMD:C_0805_2012Metric", 193.04, 73.66)
    elements.append(c_inst)
    elements.append(wire(cp1[0], cp1[1], 193.04, 63.50))
    elements.append(local_label("GND", cp2[0], cp2[1]))

    # =========================================================================
    # ROW 2: CONNECTORS (J_TOF at X=63.50, Y=177.80; J3 USB-C at X=63.50, Y=241.30)
    # =========================================================================
    # J_TOF (Conn_01x04) at (63.50, 177.80)
    # Pins:
    # Pin 1: (58.42, 177.80 - (-3.81) = 181.61) -> +5V_TOF
    # Pin 2: (58.42, 177.80 - (-1.27) = 179.07) -> GND
    # Pin 3: (58.42, 177.80 - 1.27 = 176.53)    -> TOF_RXD
    # Pin 4: (58.42, 177.80 - 3.81 = 173.99)    -> TOF_TXD
    pins_tof = get_pin_map(sym_c4, 63.50, 177.80)
    elements.append(sym_inst("Connector_Generic:Conn_01x04", "J_TOF", "MaixSense_A010", "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical", 63.50, 177.80))
    for pnum, net in [('1', "+5V_TOF"), ('2', "GND"), ('3', "TOF_RXD"), ('4', "TOF_TXD")]:
        px, py, _, _ = pins_tof[pnum]
        elements.append(wire(px, py, px - 10.16, py))
        elements.append(local_label(net, px - 10.16, py, rot=180))

    # J3 (USB_C_Receptacle_USB2.0_16P) at (63.50, 241.30)
    pins_usb = get_pin_map(sym_usb, 63.50, 241.30)
    elements.append(sym_inst("Connector:USB_C_Receptacle_USB2.0_16P", "J3", "USB-C_VISION", "Connector_USB:USB_C_Receptacle_HCTL_HC-TYPE-C-16P-01A", 63.50, 241.30))
    # D+ (A6, B6)
    dp_a_x, dp_a_y, _, _ = pins_usb['A6']
    dp_b_x, dp_b_y, _, _ = pins_usb['B6']
    elements.append(wire(dp_a_x, dp_a_y, dp_a_x + 10.16, dp_a_y))
    elements.append(wire(dp_b_x, dp_b_y, dp_a_x + 10.16, dp_a_y))
    elements.append(local_label("VIS_USB_D+", dp_a_x + 10.16, dp_a_y))
    # D- (A7, B7)
    dm_a_x, dm_a_y, _, _ = pins_usb['A7']
    dm_b_x, dm_b_y, _, _ = pins_usb['B7']
    elements.append(wire(dm_a_x, dm_a_y, dm_a_x + 10.16, dm_a_y))
    elements.append(wire(dm_b_x, dm_b_y, dm_a_x + 10.16, dm_a_y))
    elements.append(local_label("VIS_USB_D-", dm_a_x + 10.16, dm_a_y))
    # GND (A1/B1/A12/B12 pin A1 at (63.50, 218.44), SH at (55.88, 218.44))
    gnd_x, gnd_y, _, _ = pins_usb['A1']
    sh_x, sh_y, _, _ = pins_usb['SH']
    elements.append(wire(sh_x, sh_y, gnd_x, gnd_y))
    elements.append(wire(gnd_x, gnd_y, gnd_x, gnd_y - 7.62))
    elements.append(local_label("GND", gnd_x, gnd_y - 7.62))
    # VBUS (A4/B4/A9/B9 pin A4 at (78.74, 256.54))
    vbus_x, vbus_y, _, _ = pins_usb['A4']
    elements.append(wire(vbus_x, vbus_y, vbus_x + 10.16, vbus_y))
    elements.append(local_label("VBUS_VIS", vbus_x + 10.16, vbus_y))
    # CC1 & CC2 with 5.1k resistors to GND
    cc1_x, cc1_y, _, _ = pins_usb['A5']
    cc2_x, cc2_y, _, _ = pins_usb['B5']
    # R_VIS_CC1 at (cc1_x + 15.24, cc1_y + 3.81)
    r_inst, rp1, rp2 = r_vert("R_VIS_CC1", "5.1k", cc1_x + 15.24, cc1_y + 3.81)
    elements.append(r_inst)
    elements.append(wire(cc1_x, cc1_y, rp1[0], rp1[1]))
    elements.append(local_label("GND", rp2[0], rp2[1]))
    # R_VIS_CC2 at (cc2_x + 25.40, cc2_y + 3.81)
    r_inst, rp1, rp2 = r_vert("R_VIS_CC2", "5.1k", cc2_x + 25.40, cc2_y + 3.81)
    elements.append(r_inst)
    elements.append(wire(cc2_x, cc2_y, rp1[0], rp1[1]))
    elements.append(local_label("GND", rp2[0], rp2[1]))
    # SBU1, SBU2
    elements.append(no_conn(pins_usb['A8'][0], pins_usb['A8'][1]))
    elements.append(no_conn(pins_usb['B8'][0], pins_usb['B8'][1]))

    # =========================================================================
    # ROW 2/3: U8 (ESP32-S3-WROOM-1U-N8R8) at (177.80, 177.80)
    # =========================================================================
    pins_u8 = get_pin_map(sym_esp, 177.80, 177.80)
    elements.append(sym_inst("RF_Module:ESP32-S3-WROOM-1", "U8", "ESP32-S3-WROOM-1U-N8R8", "RF_Module:ESP32-S3-WROOM-1U", 177.80, 177.80))
    # Pin 1 (GND)
    p_x, p_y, _, _ = pins_u8['1']
    elements.append(wire(p_x, p_y, p_x, p_y + 7.62))
    elements.append(local_label("GND", p_x, p_y + 7.62))
    # Pin 40, 41 (GND EP)
    p_x, p_y, _, _ = pins_u8['40']
    elements.append(wire(p_x, p_y, p_x, p_y + 7.62))
    # Pin 2 (3V3)
    p_x, p_y, _, _ = pins_u8['2']
    elements.append(wire(p_x, p_y, p_x, p_y - 7.62))
    elements.append(local_label("+3V3_VIS", p_x, p_y - 7.62))
    # Decoupling Caps C_U8_1 (10uF), C_U8_2 (100nF)
    c_inst, cp1, cp2 = c_vert("C_U8_1", "10uF", "Capacitor_SMD:C_0805_2012Metric", p_x + 7.62, p_y - 12.70)
    elements.append(c_inst)
    elements.append(wire(p_x, p_y - 7.62, cp1[0], cp1[1]))
    elements.append(local_label("GND", cp2[0], cp2[1]))
    c_inst, cp1, cp2 = c_vert("C_U8_2", "100nF", "Capacitor_SMD:C_0603_1608Metric", p_x + 17.78, p_y - 12.70)
    elements.append(c_inst)
    elements.append(wire(cp1[0], cp1[1], p_x, p_y - 7.62))
    elements.append(local_label("GND", cp2[0], cp2[1]))

    # Pin 3 (EN) -> VISION_RESET with R_VIS_EN (10k pullup) and C_VIS_EN (1uF)
    p_x, p_y, _, _ = pins_u8['3']
    elements.append(wire(p_x, p_y, p_x - 12.70, p_y))
    elements.append(local_label("VISION_RESET", p_x - 12.70, p_y, rot=180))
    r_inst, rp1, rp2 = r_vert("R_VIS_EN", "10k", p_x - 20.32, p_y - 7.62)
    elements.append(r_inst)
    elements.append(local_label("+3V3_VIS", rp1[0], rp1[1]))
    elements.append(wire(rp2[0], rp2[1], p_x - 12.70, p_y))
    c_inst, cp1, cp2 = c_vert("C_VIS_EN", "1uF", "Capacitor_SMD:C_0603_1608Metric", p_x - 27.94, p_y + 7.62)
    elements.append(c_inst)
    elements.append(wire(cp1[0], cp1[1], p_x - 12.70, p_y))
    elements.append(local_label("GND", cp2[0], cp2[1]))

    # Pin 27 (IO0) -> BOOT_VIS with R_VIS_BOOT (10k pullup) and SW_VIS_BOOT
    p_x, p_y, _, _ = pins_u8['27']
    elements.append(wire(p_x, p_y, p_x - 12.70, p_y))
    elements.append(local_label("BOOT_VIS", p_x - 12.70, p_y, rot=180))
    r_inst, rp1, rp2 = r_vert("R_VIS_BOOT", "10k", p_x - 20.32, p_y - 7.62)
    elements.append(r_inst)
    elements.append(local_label("+3V3_VIS", rp1[0], rp1[1]))
    elements.append(wire(rp2[0], rp2[1], p_x - 12.70, p_y))
    # Tactile switch SW_VIS_BOOT at (p_x - 30.48, p_y)
    elements.append(sym_inst("Switch:SW_Push", "SW_VIS_BOOT", "SW_Push", "Button_Switch_SMD:SW_Push_SPST_NO_Alps_SKRK", p_x - 35.56, p_y))
    elements.append(wire(p_x - 35.56 + 5.08, p_y, p_x - 12.70, p_y))
    elements.append(local_label("GND", p_x - 35.56 - 5.08, p_y, rot=180))

    # Pin 39 (IO1 / TOF_RXD)
    p_x, p_y, _, _ = pins_u8['39']
    elements.append(wire(p_x, p_y, p_x - 10.16, p_y))
    elements.append(local_label("TOF_RXD", p_x - 10.16, p_y, rot=180))
    # Pin 38 (IO2 / TOF_TXD)
    p_x, p_y, _, _ = pins_u8['38']
    elements.append(wire(p_x, p_y, p_x - 10.16, p_y))
    elements.append(local_label("TOF_TXD", p_x - 10.16, p_y, rot=180))

    # Camera pins left side:
    cam_u8_map = {
        '4': "CAM_SDA", '5': "CAM_SCL", '6': "CAM_VSYNC", '7': "CAM_HREF",
        '12': "CAM_D2", '17': "CAM_D1", '18': "CAM_D3", '19': "CAM_D0",
        '20': "CAM_D4", '21': "CAM_PCLK", '8': "CAM_XCLK", '9': "CAM_D7"
    }
    for pnum, net in cam_u8_map.items():
        p_x, p_y, _, _ = pins_u8[pnum]
        elements.append(wire(p_x, p_y, p_x - 10.16, p_y))
        elements.append(local_label(net, p_x - 10.16, p_y, rot=180))

    # I2C Pullups for Camera SCCB (CAM_SDA, CAM_SCL)
    sda_px, sda_py, _, _ = pins_u8['4']
    r_inst, rp1, rp2 = r_vert("R_CAM_SDA", "4.7k", sda_px - 20.32, sda_py - 7.62)
    elements.append(r_inst)
    elements.append(local_label("+3V3_VIS", rp1[0], rp1[1]))
    elements.append(wire(rp2[0], rp2[1], sda_px - 10.16, sda_py))

    scl_px, scl_py, _, _ = pins_u8['5']
    r_inst, rp1, rp2 = r_vert("R_CAM_SCL", "4.7k", scl_px - 20.32, scl_py - 7.62)
    elements.append(r_inst)
    elements.append(local_label("+3V3_VIS", rp1[0], rp1[1]))
    elements.append(wire(rp2[0], rp2[1], scl_px - 10.16, scl_py))

    # U8 Right side:
    # Pin 37 (TXD0): INTER_UART_TX
    p_x, p_y, _, _ = pins_u8['37']
    elements.append(wire(p_x, p_y, p_x + 10.16, p_y))
    elements.append(local_label("INTER_UART_TX", p_x + 10.16, p_y))

    # Pin 36 (RXD0): INTER_UART_RX
    p_x, p_y, _, _ = pins_u8['36']
    elements.append(wire(p_x, p_y, p_x + 10.16, p_y))
    elements.append(local_label("INTER_UART_RX", p_x + 10.16, p_y))

    # Pin 10 (IO17): CAM_D6
    p_x, p_y, _, _ = pins_u8['10']
    elements.append(wire(p_x, p_y, p_x + 10.16, p_y))
    elements.append(local_label("CAM_D6", p_x + 10.16, p_y))

    # Pin 11 (IO18): CAM_D5
    p_x, p_y, _, _ = pins_u8['11']
    elements.append(wire(p_x, p_y, p_x + 10.16, p_y))
    elements.append(local_label("CAM_D5", p_x + 10.16, p_y))

    # Pin 13 (IO20): VIS_USB_D+
    p_x, p_y, _, _ = pins_u8['13']
    elements.append(wire(p_x, p_y, p_x + 10.16, p_y))
    elements.append(local_label("VIS_USB_D+", p_x + 10.16, p_y))

    # Pin 14 (IO19): VIS_USB_D-
    p_x, p_y, _, _ = pins_u8['14']
    elements.append(wire(p_x, p_y, p_x + 10.16, p_y))
    elements.append(local_label("VIS_USB_D-", p_x + 10.16, p_y))

    # Pin 23 (IO21): VISION_SYNC
    p_x, p_y, _, _ = pins_u8['23']
    elements.append(wire(p_x, p_y, p_x + 10.16, p_y))
    elements.append(local_label("VISION_SYNC", p_x + 10.16, p_y))

    # Pin 24 (IO38): CAM_PWDN
    p_x, p_y, _, _ = pins_u8['24']
    elements.append(wire(p_x, p_y, p_x + 10.16, p_y))
    elements.append(local_label("CAM_PWDN", p_x + 10.16, p_y))

    # Unused pins on U8 marked no_connect
    u8_unused = ['15', '16', '22', '25', '26', '28', '29', '30', '31', '32', '33', '34', '35']
    for pnum in u8_unused:
        elements.append(no_conn(pins_u8[pnum][0], pins_u8[pnum][1]))

    # =========================================================================
    # ROW 2/3: J_CAM (Conn_01x24) at (266.70, 177.80)
    # =========================================================================
    pins_cam = get_pin_map(sym_c24, 266.70, 177.80)
    elements.append(sym_inst("Connector_Generic:Conn_01x24", "J_CAM", "OV3660_DVP_24P", "Connector_FFC-FPC:Hirose_FH12-24S-0.5SH_1x24-1MP_P0.50mm_Horizontal", 266.70, 177.80))
    cam_net_map = {
        '1': ("STROBE", False),  # strobe NC
        '2': ("GND", True),
        '3': ("CAM_SDA", True),
        '4': ("+3V3_VIS", True),
        '5': ("CAM_SCL", True),
        '6': ("+3V3_VIS", True), # RESET high
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
            elements.append(local_label(net, px - 10.16, py, rot=180))
        else:
            elements.append(no_conn(px, py))

    # Bypass caps for Camera: C_CAM1 (10uF), C_CAM2 (100nF)
    c_inst, cp1, cp2 = c_vert("C_CAM1", "10uF", "Capacitor_SMD:C_0805_2012Metric", 292.10, 152.40)
    elements.append(c_inst)
    elements.append(local_label("+3V3_VIS", cp1[0], cp1[1]))
    elements.append(local_label("GND", cp2[0], cp2[1]))
    c_inst, cp1, cp2 = c_vert("C_CAM2", "100nF", "Capacitor_SMD:C_0603_1608Metric", 304.80, 152.40)
    elements.append(c_inst)
    elements.append(local_label("+3V3_VIS", cp1[0], cp1[1]))
    elements.append(local_label("GND", cp2[0], cp2[1]))

    footer = "\n)\n"
    content = header + "\n" + "\n".join(elements) + footer
    return content

def update_root_schematic(root_text):
    text = root_text

    # 1. Replace J1 USB_D+/USB_D- wires with no_connect
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
    # Find UUIDs: e62d2ace-e139-4559-95fb-6e1a89d93987, 8a2dc7bb-c423-4c94-9f26-b56b8db250da, 23ae5533-d1c0-46d3-be2d-c8d460a91e32, 20623260-9653-4f66-a458-5c259cbaf404
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
    # Coordinates:
    # Pin 4: (80.01, 290.83)
    # Pin 8: (80.01, 318.77)
    # Pin 9: (80.01, 321.31)
    # Pin 22: (80.01, 316.23)
    u1_nc_coords = ["(at 80.01 290.83)", "(at 80.01 318.77)", "(at 80.01 321.31)", "(at 80.01 316.23)"]
    for nc_c in u1_nc_coords:
        idx = text.find(nc_c)
        if idx != -1:
            line_start = text.rfind('\t(no_connect', 0, idx)
            line_end = text.find('\n', idx)
            if line_start != -1 and line_end != -1:
                text = text[:line_start] + text[line_end+1:]

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

    # 5. Add J2 (J_USB_MAIN) in Section 5 at (38.10, 241.30)
    # Pins for USB_C_Receptacle_USB2.0_16P at (38.10, 241.30):
    # D+ A6/B6 at (53.34, 238.76) and (53.34, 236.22)
    # D- A7/B7 at (53.34, 243.84) and (53.34, 241.30)
    # GND A1 at (38.10, 218.44), SH at (30.48, 218.44)
    # VBUS A4 at (53.34, 256.54)
    # CC1 A5 at (53.34, 251.46), CC2 B5 at (53.34, 248.92)
    # SBU1 A8 at (53.34, 228.60), SBU2 B8 at (53.34, 226.06)
    j2_inst = sym_inst("Connector:USB_C_Receptacle_USB2.0_16P", "J2", "USB-C_MAIN", "Connector_USB:USB_C_Receptacle_HCTL_HC-TYPE-C-16P-01A", 38.10, 241.30)
    r_cc3, r3_p1, r3_p2 = r_vert("R_CC3", "5.1k", 68.58, 255.27)
    r_cc4, r4_p1, r4_p2 = r_vert("R_CC4", "5.1k", 78.74, 255.27)
    c_vbus, cv_p1, cv_p2 = c_vert("C_VBUS_MAIN", "100nF", "Capacitor_SMD:C_0603_1608Metric", 68.58, 267.97)

    j2_block = f"""
{j2_inst}
\t(wire (pts (xy 53.34 238.76) (xy 63.50 238.76)) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(wire (pts (xy 53.34 236.22) (xy 63.50 238.76)) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "USB_D+" (shape bidirectional) (at 63.50 238.76 0) (effects (font (size 1.27 1.27)) (justify left)) (uuid "{uid()}"))
\t(wire (pts (xy 53.34 243.84) (xy 63.50 241.30)) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(wire (pts (xy 53.34 241.30) (xy 63.50 241.30)) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "USB_D-" (shape bidirectional) (at 63.50 241.30 0) (effects (font (size 1.27 1.27)) (justify left)) (uuid "{uid()}"))
\t(wire (pts (xy 38.10 218.44) (xy 38.10 210.82)) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(wire (pts (xy 30.48 218.44) (xy 38.10 218.44)) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "GND" (shape bidirectional) (at 38.10 210.82 90) (effects (font (size 1.27 1.27)) (justify left)) (uuid "{uid()}"))
\t(no_connect (at 53.34 228.60) (uuid "{uid()}"))
\t(no_connect (at 53.34 226.06) (uuid "{uid()}"))
{r_cc3}
\t(wire (pts (xy 53.34 251.46) (xy {r3_p1[0]:.2f} {r3_p1[1]:.2f})) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "GND" (shape bidirectional) (at {r3_p2[0]:.2f} {r3_p2[1]:.2f} 270) (effects (font (size 1.27 1.27)) (justify right)) (uuid "{uid()}"))
{r_cc4}
\t(wire (pts (xy 53.34 248.92) (xy {r4_p1[0]:.2f} {r4_p1[1]:.2f})) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "GND" (shape bidirectional) (at {r4_p2[0]:.2f} {r4_p2[1]:.2f} 270) (effects (font (size 1.27 1.27)) (justify right)) (uuid "{uid()}"))
{c_vbus}
\t(wire (pts (xy 53.34 256.54) (xy {cv_p1[0]:.2f} {cv_p1[1]:.2f})) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "VBUS_MAIN" (shape bidirectional) (at {cv_p1[0]:.2f} {cv_p1[1]:.2f} 0) (effects (font (size 1.27 1.27)) (justify left)) (uuid "{uid()}"))
\t(global_label "GND" (shape bidirectional) (at {cv_p2[0]:.2f} {cv_p2[1]:.2f} 270) (effects (font (size 1.27 1.27)) (justify right)) (uuid "{uid()}"))"""

    # 6. Add Hierarchical Sheet for Vision_Coprocessor
    # Placed at (25.40, 340.36) with size (63.50, 43.18)
    # Left pins:
    # VBAT_SW at (25.40, 350.52)
    # GND at (25.40, 360.68)
    # Right pins:
    # INTER_UART_TX at (88.90, 350.52)
    # INTER_UART_RX at (88.90, 355.60)
    # VISION_SYNC at (88.90, 365.76)
    # VISION_RESET at (88.90, 370.84)
    sheet_block = f"""
\t(sheet (at 25.40 340.36) (size 63.50 43.18)
\t\t(stroke (width 0.1524) (type solid))
\t\t(fill (color 0 0 0 0.0000))
\t\t(uuid "{uid()}")
\t\t(property "Sheetname" "Vision_Coprocessor" (at 25.40 336.55 0) (effects (font (size 1.5 1.5)) (justify left bottom)))
\t\t(property "Sheetfile" "Hexapod_Vision_Subsystem.kicad_sch" (at 25.40 386.08 0) (effects (font (size 1.5 1.5)) (justify left top)))
\t\t(pin "VBAT_SW" power_in (at 25.40 350.52 180) (effects (font (size 1.27 1.27)) (justify left)) (uuid "{uid()}"))
\t\t(pin "GND" power_in (at 25.40 360.68 180) (effects (font (size 1.27 1.27)) (justify left)) (uuid "{uid()}"))
\t\t(pin "INTER_UART_TX" output (at 88.90 350.52 0) (effects (font (size 1.27 1.27)) (justify right)) (uuid "{uid()}"))
\t\t(pin "INTER_UART_RX" input (at 88.90 355.60 0) (effects (font (size 1.27 1.27)) (justify right)) (uuid "{uid()}"))
\t\t(pin "VISION_SYNC" input (at 88.90 365.76 0) (effects (font (size 1.27 1.27)) (justify right)) (uuid "{uid()}"))
\t\t(pin "VISION_RESET" input (at 88.90 370.84 0) (effects (font (size 1.27 1.27)) (justify right)) (uuid "{uid()}"))
\t)
\t(wire (pts (xy 25.40 350.52) (xy 15.24 350.52)) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "VBAT_SW" (shape bidirectional) (at 15.24 350.52 180) (effects (font (size 1.27 1.27)) (justify right)) (uuid "{uid()}"))
\t(wire (pts (xy 25.40 360.68) (xy 15.24 360.68)) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "GND" (shape bidirectional) (at 15.24 360.68 180) (effects (font (size 1.27 1.27)) (justify right)) (uuid "{uid()}"))
\t(wire (pts (xy 88.90 350.52) (xy 99.06 350.52)) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "INTER_UART_TX" (shape bidirectional) (at 99.06 350.52 0) (effects (font (size 1.27 1.27)) (justify left)) (uuid "{uid()}"))
\t(wire (pts (xy 88.90 355.60) (xy 99.06 355.60)) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "INTER_UART_RX" (shape bidirectional) (at 99.06 355.60 0) (effects (font (size 1.27 1.27)) (justify left)) (uuid "{uid()}"))
\t(wire (pts (xy 88.90 365.76) (xy 99.06 365.76)) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "VISION_SYNC" (shape bidirectional) (at 99.06 365.76 0) (effects (font (size 1.27 1.27)) (justify left)) (uuid "{uid()}"))
\t(wire (pts (xy 88.90 370.84) (xy 99.06 370.84)) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "VISION_RESET" (shape bidirectional) (at 99.06 370.84 0) (effects (font (size 1.27 1.27)) (justify left)) (uuid "{uid()}"))"""

    last_paren = text.rfind(')')
    final_text = text[:last_paren] + u1_wiring + j2_block + sheet_block + "\n)\n"
    return final_text

def main():
    print("Reading root schematic...")
    with open("Hexapod_Robot_Board.kicad_sch", "r", encoding="utf-8") as f:
        root_content = f.read()

    print("Building Hexapod_Vision_Subsystem.kicad_sch...")
    vis_sch = build_vision_subsheet(root_content)
    with open("Hexapod_Vision_Subsystem.kicad_sch", "w", encoding="utf-8") as f:
        f.write(vis_sch)
    print("Hexapod_Vision_Subsystem.kicad_sch created.")

    print("Updating Hexapod_Robot_Board.kicad_sch...")
    updated_root = update_root_schematic(root_content)
    with open("Hexapod_Robot_Board.kicad_sch", "w", encoding="utf-8") as f:
        f.write(updated_root)
    print("Hexapod_Robot_Board.kicad_sch updated.")

if __name__ == '__main__':
    main()
