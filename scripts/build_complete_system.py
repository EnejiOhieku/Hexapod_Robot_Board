import os
import re
import uuid
import subprocess

def uid():
    return str(uuid.uuid4())

def get_full_symbol(text, sym_name):
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

def get_pin_map(sym_text, origin_x, origin_y):
    pin_matches = re.finditer(r'\(pin\s+[^\s]+\s+line\s+\(at\s+([\d\.\-]+)\s+([\d\.\-]+)\s+(\d+)\).*?\(name\s+\"([^\"]+)\".*?\(number\s+\"([^\"]+)\"', sym_text, re.DOTALL)
    res = {}
    for m in pin_matches:
        px, py, rot, name, num = float(m.group(1)), float(m.group(2)), int(m.group(3)), m.group(4), m.group(5)
        cx = round((origin_x + px) * 100) / 100
        cy = round((origin_y - py) * 100) / 100
        res[num] = (cx, cy, name, rot)
    return res

def sym_inst(lib_id, ref, val, fp, x, y, rot=0, props=None):
    if props is None: props = {}
    p_str = ""
    for k, v in props.items():
        p_str += f"""\t\t(property "{k}" "{v}" (at {x:.2f} {y:.2f} 0) (hide yes) (effects (font (size 1.27 1.27))))\n"""
    return f"""\t(symbol
\t\t(lib_id "{lib_id}")
\t\t(at {x:.2f} {y:.2f} {rot})
\t\t(unit 1)
\t\t(exclude_from_sim no)
\t\t(in_bom yes)
\t\t(on_board yes)
\t\t(in_pos_files yes)
\t\t(dnp no)
\t\t(uuid "{uid()}")
\t\t(property "Reference" "{ref}" (at {x:.2f} {y - 4:.2f} 0) (effects (font (size 1.27 1.27))))
\t\t(property "Value" "{val}" (at {x:.2f} {y + 4:.2f} 0) (effects (font (size 1.27 1.27))))
\t\t(property "Footprint" "{fp}" (at {x:.2f} {y:.2f} 0) (hide yes) (effects (font (size 1.27 1.27))))
{p_str}\t)"""

def wire(x1, y1, x2, y2):
    return f"""\t(wire (pts (xy {x1:.2f} {y1:.2f}) (xy {x2:.2f} {y2:.2f})) (stroke (width 0) (type default)) (uuid "{uid()}"))"""

def h_label(name, x, y, rot=0, shape="input"):
    return f"""\t(hierarchical_label "{name}" (shape {shape}) (at {x:.2f} {y:.2f} {rot}) (effects (font (size 1.27 1.27)) (justify left)) (uuid "{uid()}"))"""

def local_label(name, x, y, rot=0):
    return f"""\t(label "{name}" (at {x:.2f} {y:.2f} {rot}) (effects (font (size 1.27 1.27)) (justify left)) (uuid "{uid()}"))"""

def no_conn(x, y):
    return f"""\t(no_connect (at {x:.2f} {y:.2f}) (uuid "{uid()}"))"""

def main():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(root_dir)

    with open('Hexapod_Robot_Board.kicad_sch', 'r', encoding='utf-8') as f:
        main_sch = f.read()

    # Step 1: Build Hexapod_Vision_Subsystem.kicad_sch
    sym_esp = get_full_symbol(main_sch, 'RF_Module:ESP32-S3-WROOM-1')
    sym_usb = get_full_symbol(main_sch, 'Connector:USB_C_Receptacle_USB2.0_16P')
    sym_ams = get_full_symbol(main_sch, 'Regulator_Linear:AMS1117-3.3')
    sym_r   = get_full_symbol(main_sch, 'Device:R')
    sym_c   = get_full_symbol(main_sch, 'Device:C')
    sym_l   = get_full_symbol(main_sch, 'Device:L')
    sym_led = get_full_symbol(main_sch, 'Device:LED')
    sym_sw  = get_full_symbol(main_sch, 'Switch:SW_Push')
    sym_pwr = get_full_symbol(main_sch, 'power:PWR_FLAG')
    sym_c4  = get_full_symbol(main_sch, 'Connector_Generic:Conn_01x04')

    conn24_path = '/home/peacemaker/.local/share/kicad-appimage/share/kicad/symbols/Connector_Generic.kicad_symdir/Conn_01x24.kicad_sym'
    with open(conn24_path, 'r', encoding='utf-8') as f:
        c24_raw = f.read()
    sym_c24 = get_full_symbol(c24_raw, 'Conn_01x24')
    sym_c24 = sym_c24.replace('(symbol "Conn_01x24"', '(symbol "Connector_Generic:Conn_01x24"', 1)

    sub_lib_symbols = f"""\t(lib_symbols
\t\t{sym_esp}
\t\t{sym_usb}
\t\t{sym_c24}
\t\t{sym_c4}
\t\t{sym_ams}
\t\t{sym_r}
\t\t{sym_c}
\t\t{sym_l}
\t\t{sym_led}
\t\t{sym_sw}
\t\t{sym_pwr}
\t)"""

    u8_x, u8_y = 152.40, 127.00
    j_cam_x, j_cam_y = 254.00, 127.00
    j_tof_x, j_tof_y = 76.20, 101.60
    j_usb_x, j_usb_y = 76.20, 177.80
    u_tof_x, u_tof_y = 76.20, 50.80
    u_vis_ldo_x, u_vis_ldo_y = 127.00, 50.80

    pins_u8 = get_pin_map(sym_esp, u8_x, u8_y)
    pins_cam = get_pin_map(sym_c24, j_cam_x, j_cam_y)
    pins_tof = get_pin_map(sym_c4, j_tof_x, j_tof_y)
    pins_usb = get_pin_map(sym_usb, j_usb_x, j_usb_y)
    pins_ams5 = get_pin_map(sym_ams, u_tof_x, u_tof_y)
    pins_ams3 = get_pin_map(sym_ams, u_vis_ldo_x, u_vis_ldo_y)

    elements = []

    # Hierarchical labels
    elements.append(h_label("VBAT_SW", 25.40, 50.80, shape="input"))
    elements.append(h_label("GND", 25.40, 63.50, shape="input"))
    elements.append(h_label("INTER_UART_TX", 25.40, 104.14, shape="output"))
    elements.append(h_label("INTER_UART_RX", 25.40, 106.68, shape="input"))
    elements.append(h_label("VISION_SYNC", 25.40, 119.38, shape="output"))
    elements.append(h_label("VISION_RESET", 25.40, 88.90, shape="input"))

    # U_REG_5V_TOF
    elements.append(sym_inst("Regulator_Linear:AMS1117-3.3", "U_REG_5V_TOF", "AMS1117-5.0", "Package_TO_SOT_SMD:SOT-223-3_TabPin2", u_tof_x, u_tof_y))
    p3_x, p3_y, _, _ = pins_ams5['3']
    elements.append(wire(25.40, 50.80, p3_x, p3_y))
    p2_x, p2_y, _, _ = pins_ams5['2']
    elements.append(wire(p2_x, p2_y, p2_x + 10.16, p2_y))
    elements.append(local_label("+5V_TOF", p2_x + 10.16, p2_y))
    p1_x, p1_y, _, _ = pins_ams5['1']
    elements.append(wire(p1_x, p1_y, p1_x, 63.50))
    elements.append(wire(25.40, 63.50, p1_x, 63.50))
    elements.append(local_label("GND", p1_x, 63.50))

    # U_LDO_VIS
    elements.append(sym_inst("Regulator_Linear:AMS1117-3.3", "U_LDO_VIS", "AMS1117-3.3", "Package_TO_SOT_SMD:SOT-223-3_TabPin2", u_vis_ldo_x, u_vis_ldo_y))
    p3_x, p3_y, _, _ = pins_ams3['3']
    elements.append(wire(pins_ams5['3'][0], pins_ams5['3'][1], p3_x, p3_y))
    p2_x, p2_y, _, _ = pins_ams3['2']
    elements.append(wire(p2_x, p2_y, p2_x + 10.16, p2_y))
    elements.append(local_label("+3V3_VIS", p2_x + 10.16, p2_y))
    p1_x, p1_y, _, _ = pins_ams3['1']
    elements.append(wire(p1_x, p1_y, p1_x, 63.50))
    elements.append(wire(pins_ams5['1'][0], 63.50, p1_x, 63.50))

    # J_TOF
    elements.append(sym_inst("Connector_Generic:Conn_01x04", "J_TOF", "MaixSense_A010", "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical", j_tof_x, j_tof_y))
    for pnum, net in [('1', "+5V_TOF"), ('2', "GND"), ('3', "TOF_RXD"), ('4', "TOF_TXD")]:
        px, py, _, _ = pins_tof[pnum]
        elements.append(wire(px, py, px - 10.16, py))
        elements.append(local_label(net, px - 10.16, py, rot=180))

    # J3 (USB-C VISION)
    elements.append(sym_inst("Connector:USB_C_Receptacle_USB2.0_16P", "J3", "USB-C_VISION", "Connector_USB:USB_C_Receptacle_HCTL_HC-TYPE-C-16P-01A", j_usb_x, j_usb_y))
    # D+
    dp_a_x, dp_a_y, _, _ = pins_usb['A6']
    dp_b_x, dp_b_y, _, _ = pins_usb['B6']
    elements.append(wire(dp_a_x, dp_a_y, dp_a_x + 10.16, dp_a_y))
    elements.append(local_label("VIS_USB_D+", dp_a_x + 10.16, dp_a_y))
    elements.append(wire(dp_b_x, dp_b_y, dp_a_x + 10.16, dp_a_y))
    # D-
    dm_a_x, dm_a_y, _, _ = pins_usb['A7']
    dm_b_x, dm_b_y, _, _ = pins_usb['B7']
    elements.append(wire(dm_a_x, dm_a_y, dm_a_x + 10.16, dm_a_y))
    elements.append(local_label("VIS_USB_D-", dm_a_x + 10.16, dm_a_y))
    elements.append(wire(dm_b_x, dm_b_y, dm_a_x + 10.16, dm_a_y))
    # GND
    gnd_x, gnd_y, _, _ = pins_usb['A1']
    elements.append(wire(gnd_x, gnd_y, gnd_x, gnd_y + 10.16))
    elements.append(local_label("GND", gnd_x, gnd_y + 10.16))
    sh_x, sh_y, _, _ = pins_usb['SH']
    elements.append(wire(sh_x, sh_y, gnd_x, gnd_y + 10.16))
    # CC1, CC2
    cc1_x, cc1_y, _, _ = pins_usb['A5']
    elements.append(wire(cc1_x, cc1_y, cc1_x + 5.08, cc1_y))
    elements.append(local_label("VIS_CC1", cc1_x + 5.08, cc1_y))
    cc2_x, cc2_y, _, _ = pins_usb['B5']
    elements.append(wire(cc2_x, cc2_y, cc2_x + 5.08, cc2_y))
    elements.append(local_label("VIS_CC2", cc2_x + 5.08, cc2_y))
    # VBUS
    vbus_x, vbus_y, _, _ = pins_usb['A4']
    elements.append(wire(vbus_x, vbus_y, vbus_x + 10.16, vbus_y))
    elements.append(local_label("VBUS_VIS", vbus_x + 10.16, vbus_y))
    # SBU1, SBU2 no_connect
    elements.append(no_conn(pins_usb['A8'][0], pins_usb['A8'][1]))
    elements.append(no_conn(pins_usb['B8'][0], pins_usb['B8'][1]))

    # U8 (Vision ESP32-S3)
    elements.append(sym_inst("RF_Module:ESP32-S3-WROOM-1", "U8", "ESP32-S3-WROOM-1U-N8R8", "RF_Module:ESP32-S3-WROOM-1U", u8_x, u8_y))

    # Power & Control
    # Pin 1 (GND)
    p_x, p_y, _, _ = pins_u8['1']
    elements.append(wire(p_x, p_y, p_x, p_y + 7.62))
    elements.append(local_label("GND", p_x, p_y + 7.62))
    # Pin 2 (3V3)
    p_x, p_y, _, _ = pins_u8['2']
    elements.append(wire(p_x, p_y, p_x, p_y - 7.62))
    elements.append(local_label("+3V3_VIS", p_x, p_y - 7.62))
    # Pin 3 (EN)
    p_x, p_y, _, _ = pins_u8['3']
    elements.append(wire(p_x, p_y, p_x - 10.16, p_y))
    elements.append(local_label("VISION_RESET", p_x - 10.16, p_y, rot=180))
    elements.append(wire(25.40, 88.90, 35.56, 88.90))
    elements.append(local_label("VISION_RESET", 35.56, 88.90))
    # Pin 27 (IO0)
    p_x, p_y, _, _ = pins_u8['27']
    elements.append(wire(p_x, p_y, p_x - 10.16, p_y))
    elements.append(local_label("BOOT_VIS", p_x - 10.16, p_y, rot=180))
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

    # MCU Right side:
    # Pin 37 (TXD0): INTER_UART_TX
    p_x, p_y, _, _ = pins_u8['37']
    elements.append(wire(p_x, p_y, p_x + 10.16, p_y))
    elements.append(local_label("INTER_UART_TX", p_x + 10.16, p_y))
    elements.append(wire(25.40, 104.14, 35.56, 104.14))
    elements.append(local_label("INTER_UART_TX", 35.56, 104.14))

    # Pin 36 (RXD0): INTER_UART_RX
    p_x, p_y, _, _ = pins_u8['36']
    elements.append(wire(p_x, p_y, p_x + 10.16, p_y))
    elements.append(local_label("INTER_UART_RX", p_x + 10.16, p_y))
    elements.append(wire(25.40, 106.68, 35.56, 106.68))
    elements.append(local_label("INTER_UART_RX", 35.56, 106.68))

    # Pin 10 (IO17): CAM_D6
    p_x, p_y, _, _ = pins_u8['10']
    elements.append(wire(p_x, p_y, p_x + 10.16, p_y))
    elements.append(local_label("CAM_D6", p_x + 10.16, p_y))

    # Pin 11 (IO18): CAM_D5
    p_x, p_y, _, _ = pins_u8['11']
    elements.append(wire(p_x, p_y, p_x + 10.16, p_y))
    elements.append(local_label("CAM_D5", p_x + 10.16, p_y))

    # Pin 13 (USB_D-)
    p_x, p_y, _, _ = pins_u8['13']
    elements.append(wire(p_x, p_y, p_x + 10.16, p_y))
    elements.append(local_label("VIS_USB_D-", p_x + 10.16, p_y))

    # Pin 14 (USB_D+)
    p_x, p_y, _, _ = pins_u8['14']
    elements.append(wire(p_x, p_y, p_x + 10.16, p_y))
    elements.append(local_label("VIS_USB_D+", p_x + 10.16, p_y))

    # Pin 23 (IO21): VISION_SYNC
    p_x, p_y, _, _ = pins_u8['23']
    elements.append(wire(p_x, p_y, p_x + 10.16, p_y))
    elements.append(local_label("VISION_SYNC", p_x + 10.16, p_y))
    elements.append(wire(25.40, 119.38, 35.56, 119.38))
    elements.append(local_label("VISION_SYNC", 35.56, 119.38))

    # Pin 31 (IO38): CAM_PWDN
    p_x, p_y, _, _ = pins_u8['31']
    elements.append(wire(p_x, p_y, p_x + 10.16, p_y))
    elements.append(local_label("CAM_PWDN", p_x + 10.16, p_y))

    # Pin 33 (IO40): CAM_RESET
    p_x, p_y, _, _ = pins_u8['33']
    elements.append(wire(p_x, p_y, p_x + 10.16, p_y))
    elements.append(local_label("CAM_RESET", p_x + 10.16, p_y))

    # Unused U8 pins -> no_connect
    used_u8 = {'1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14',
               '17', '18', '19', '20', '21', '23', '27', '31', '33', '36', '37', '38', '39', '40', '41'}
    for pnum, (px, py, _, _) in pins_u8.items():
        if pnum not in used_u8:
            elements.append(no_conn(px, py))

    # J_CAM (Conn_01x24)
    elements.append(sym_inst("Connector_Generic:Conn_01x24", "J_CAM", "OV3660_DVP_24P", "Connector_FFC-FPC:Hirose_FH12-24S-0.5SH_1x24-1MP_P0.50mm_Horizontal", j_cam_x, j_cam_y))
    cam_pin_map = {
        '1': "CAM_D7", '2': "CAM_D6", '3': "CAM_D5", '4': "CAM_D4",
        '5': "CAM_D3", '6': "CAM_D2", '7': "CAM_D1", '8': "CAM_D0",
        '9': "GND", '10': "CAM_PCLK", '11': "GND", '12': "CAM_XCLK",
        '13': "GND", '14': "CAM_VSYNC", '15': "+3V3_VIS", '16': "CAM_HREF",
        '17': "CAM_RESET", '18': "CAM_PWDN", '19': "GND", '20': "CAM_SCL",
        '21': "+3V3_VIS", '22': "CAM_SDA", '23': "+3V3_VIS", '24': "GND"
    }
    for pnum, net in cam_pin_map.items():
        px, py, _, _ = pins_cam[pnum]
        elements.append(wire(px, py, px - 10.16, py))
        elements.append(local_label(net, px - 10.16, py, rot=180))

    sub_content = f"""(kicad_sch
\t(version 20260306)
\t(generator "eeschema")
\t(generator_version "10.0")
\t(uuid "{uid()}")
\t(paper "A3")
\t(title_block
\t\t(title "Hexapod Vision & Spatial Perception Coprocessor")
\t\t(date "2026-10-03")
\t\t(rev "2.0")
\t\t(company "Antigravity Robotics")
\t\t(comment 1 "ESP32-S3-WROOM-1U-N8R8 + OV3660 DVP Camera + MaixSense A010 ToF Sensor")
\t\t(comment 2 "100% Zephyr esp32s3_eye hardware compatible + Dedicated Isolated 5V Regulator")
\t)
{sub_lib_symbols}
{chr(10).join(elements)}
)"""

    with open('Hexapod_Vision_Subsystem.kicad_sch', 'w', encoding='utf-8') as f:
        f.write(sub_content)
    print("Clean Hexapod_Vision_Subsystem.kicad_sch written.")

    # Step 2: Update Hexapod_Robot_Board.kicad_sch
    # 2a: Update J1 (rename to J_CHG, Value USB-C_CHARGER, and disconnect USB_D+/USB_D-)
    new_sch = main_sch

    # Rename Value of J1 to USB-C_CHARGER
    new_sch = re.sub(
        r'(\(property\s+\"Reference\"\s+\"J1\".*?\(property\s+\"Value\"\s+\")[^\"]+(\")',
        r'\g<1>USB-C_CHARGER\g<2>',
        new_sch,
        count=1,
        flags=re.DOTALL
    )

    # Disconnect USB_D+ and USB_D- global labels at J1
    # Replace global_label "USB_D+" at 46.99 with no_connect
    # Lines 6021..6100
    for label_to_remove in [
        '(global_label "USB_D+"\n\t\t(shape bidirectional)\n\t\t(at 46.99 72.39 180)',
        '(global_label "USB_D+"\n\t\t(shape bidirectional)\n\t\t(at 46.99 74.93 180)',
        '(global_label "USB_D-"\n\t\t(shape bidirectional)\n\t\t(at 46.99 67.31 180)',
        '(global_label "USB_D-"\n\t\t(shape bidirectional)\n\t\t(at 46.99 69.85 180)'
    ]:
        idx = new_sch.find(label_to_remove)
        if idx != -1:
            end_label = new_sch.find('\n\t)', idx)
            # Remove this label block
            new_sch = new_sch[:idx] + new_sch[end_label+4:]

    # Remove the 4 wires connecting J1 to those labels
    for w in [
        '(wire (pts (xy 50.80 72.39) (xy 46.99 72.39))',
        '(wire (pts (xy 50.80 74.93) (xy 46.99 74.93))',
        '(wire (pts (xy 50.80 67.31) (xy 46.99 67.31))',
        '(wire (pts (xy 50.80 69.85) (xy 46.99 69.85))'
    ]:
        idx = new_sch.find(w)
        if idx != -1:
            end_w = new_sch.find('))', idx)
            new_sch = new_sch[:idx] + new_sch[end_w+2:]

    # Add no_connect on J1 pins A6, B6, A7, B7 at (50.80, 72.39), (50.80, 74.93), (50.80, 67.31), (50.80, 69.85)
    j1_nc = f"""\n\t(no_connect (at 50.80 72.39) (uuid "{uid()}"))
\t(no_connect (at 50.80 74.93) (uuid "{uid()}"))
\t(no_connect (at 50.80 67.31) (uuid "{uid()}"))
\t(no_connect (at 50.80 69.85) (uuid "{uid()}"))"""
    
    insert_pt = new_sch.find('\n\t(symbol\n\t\t(lib_id "Connector:USB_C_Receptacle_USB2.0_16P"')
    new_sch = new_sch[:insert_pt] + j1_nc + new_sch[insert_pt:]

    # 2b: Add J2 (J_USB_MAIN) in Section 5 at (50.80, 260.00)
    j2_inst = sym_inst("Connector:USB_C_Receptacle_USB2.0_16P", "J2", "USB-C_MAIN", "Connector_USB:USB_C_Receptacle_HCTL_HC-TYPE-C-16P-01A", 50.80, 260.00)
    # Pins of J2 at (50.80, 260.00):
    # D+ at (50.80 + 15.24 = 66.04, 260.00 - 2.54 = 257.46) and (66.04, 254.92) -> connect to USB_D+
    # D- at (66.04, 262.54) and (66.04, 260.00) -> connect to USB_D-
    # GND at (50.80, 260.00 - 22.86 = 237.14) and SH at (43.18, 237.14) -> connect to GND
    # CC1 at (66.04, 270.16) and CC2 at (66.04, 267.62) -> connect to 5.1k resistors to GND
    # VBUS at (66.04, 275.24) -> connect to VBUS_MAIN
    # SBU1 at (66.04, 247.30) and SBU2 at (66.04, 244.76) -> no_connect
    j2_wiring = f"""
{j2_inst}
\t(wire (pts (xy 66.04 257.46) (xy 76.20 257.46)) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(wire (pts (xy 66.04 254.92) (xy 76.20 257.46)) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "USB_D+" (shape bidirectional) (at 76.20 257.46 0) (effects (font (size 1.27 1.27)) (justify left)) (uuid "{uid()}"))
\t(wire (pts (xy 66.04 262.54) (xy 76.20 260.00)) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(wire (pts (xy 66.04 260.00) (xy 76.20 260.00)) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "USB_D-" (shape bidirectional) (at 76.20 260.00 0) (effects (font (size 1.27 1.27)) (justify left)) (uuid "{uid()}"))
\t(wire (pts (xy 50.80 237.14) (xy 50.80 230.00)) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(wire (pts (xy 43.18 237.14) (xy 50.80 237.14)) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "GND" (shape bidirectional) (at 50.80 230.00 90) (effects (font (size 1.27 1.27)) (justify left)) (uuid "{uid()}"))
\t(wire (pts (xy 66.04 270.16) (xy 76.20 270.16)) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(label "MAIN_CC1" (at 76.20 270.16 0) (effects (font (size 1.27 1.27)) (justify left)) (uuid "{uid()}"))
\t(wire (pts (xy 66.04 267.62) (xy 76.20 267.62)) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(label "MAIN_CC2" (at 76.20 267.62 0) (effects (font (size 1.27 1.27)) (justify left)) (uuid "{uid()}"))
\t(no_connect (at 66.04 247.30) (uuid "{uid()}"))
\t(no_connect (at 66.04 244.76) (uuid "{uid()}"))
\t(wire (pts (xy 66.04 275.24) (xy 76.20 275.24)) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(label "VBUS_MAIN" (at 76.20 275.24 0) (effects (font (size 1.27 1.27)) (justify left)) (uuid "{uid()}"))"""

    # 2c: Add Hierarchical Sheet Vision_Coprocessor in Section 5 at (30.48, 330.20)
    # Pins:
    # VBAT_SW at (30.48, 340.36)
    # GND at (30.48, 345.44)
    # INTER_UART_TX at (91.44, 340.36)
    # INTER_UART_RX at (91.44, 345.44)
    # VISION_SYNC at (91.44, 350.52)
    # VISION_RESET at (91.44, 355.60)
    sheet_block = f"""
\t(sheet (at 30.48 330.20) (size 60.96 40.64)
\t\t(stroke (width 0.1524) (type solid))
\t\t(fill (color 0 0 0 0.0000))
\t\t(uuid "{uid()}")
\t\t(property "Sheetname" "Vision_Coprocessor" (at 30.48 326.00 0) (effects (font (size 1.5 1.5)) (justify left bottom)))
\t\t(property "Sheetfile" "Hexapod_Vision_Subsystem.kicad_sch" (at 30.48 373.00 0) (effects (font (size 1.5 1.5)) (justify left top)))
\t\t(pin "VBAT_SW" power_in (at 30.48 340.36 180) (effects (font (size 1.27 1.27)) (justify left)) (uuid "{uid()}"))
\t\t(pin "GND" power_in (at 30.48 345.44 180) (effects (font (size 1.27 1.27)) (justify left)) (uuid "{uid()}"))
\t\t(pin "INTER_UART_TX" output (at 91.44 340.36 0) (effects (font (size 1.27 1.27)) (justify right)) (uuid "{uid()}"))
\t\t(pin "INTER_UART_RX" input (at 91.44 345.44 0) (effects (font (size 1.27 1.27)) (justify right)) (uuid "{uid()}"))
\t\t(pin "VISION_SYNC" output (at 91.44 350.52 0) (effects (font (size 1.27 1.27)) (justify right)) (uuid "{uid()}"))
\t\t(pin "VISION_RESET" input (at 91.44 355.60 0) (effects (font (size 1.27 1.27)) (justify right)) (uuid "{uid()}"))
\t)
\t(wire (pts (xy 30.48 340.36) (xy 20.32 340.36)) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "VBAT_SW" (shape bidirectional) (at 20.32 340.36 180) (effects (font (size 1.27 1.27)) (justify right)) (uuid "{uid()}"))
\t(wire (pts (xy 30.48 345.44) (xy 20.32 345.44)) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "GND" (shape bidirectional) (at 20.32 345.44 180) (effects (font (size 1.27 1.27)) (justify right)) (uuid "{uid()}"))
\t(wire (pts (xy 91.44 340.36) (xy 101.60 340.36)) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "INTER_UART_TX" (shape bidirectional) (at 101.60 340.36 0) (effects (font (size 1.27 1.27)) (justify left)) (uuid "{uid()}"))
\t(wire (pts (xy 91.44 345.44) (xy 101.60 345.44)) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "INTER_UART_RX" (shape bidirectional) (at 101.60 345.44 0) (effects (font (size 1.27 1.27)) (justify left)) (uuid "{uid()}"))
\t(wire (pts (xy 91.44 350.52) (xy 101.60 350.52)) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "VISION_SYNC" (shape bidirectional) (at 101.60 350.52 0) (effects (font (size 1.27 1.27)) (justify left)) (uuid "{uid()}"))
\t(wire (pts (xy 91.44 355.60) (xy 101.60 355.60)) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "VISION_RESET" (shape bidirectional) (at 101.60 355.60 0) (effects (font (size 1.27 1.27)) (justify left)) (uuid "{uid()}"))"""

    # 2d: Wire Inter-MCU pins on U1:
    # Pin 8 (IO15): INTER_UART_RX (Main MCU TX out)
    # Pin 9 (IO16): INTER_UART_TX (Main MCU RX in)
    # Pin 4 (IO4): VISION_SYNC
    # Pin 22 (IO14): VISION_RESET
    # On U1 in Hexapod_Robot_Board.kicad_sch, U1 is at (95.25, 298.45).
    # Pin 8 is at (95.25 - 15.24 = 80.01, 298.45 - (-20.32) = 318.77)
    # Pin 9 is at (80.01, 298.45 - (-22.86) = 321.31)
    # Pin 4 is at (80.01, 298.45 - 7.62 = 290.83)
    # Pin 22 is at (80.01, 298.45 - (-17.78) = 316.23)
    u1_inter_wiring = f"""
\t(wire (pts (xy 80.01 318.77) (xy 71.12 318.77)) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "INTER_UART_RX" (shape bidirectional) (at 71.12 318.77 180) (effects (font (size 1.27 1.27)) (justify right)) (uuid "{uid()}"))
\t(wire (pts (xy 80.01 321.31) (xy 71.12 321.31)) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "INTER_UART_TX" (shape bidirectional) (at 71.12 321.31 180) (effects (font (size 1.27 1.27)) (justify right)) (uuid "{uid()}"))
\t(wire (pts (xy 80.01 290.83) (xy 71.12 290.83)) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "VISION_SYNC" (shape bidirectional) (at 71.12 290.83 180) (effects (font (size 1.27 1.27)) (justify right)) (uuid "{uid()}"))
\t(wire (pts (xy 80.01 316.23) (xy 71.12 316.23)) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "VISION_RESET" (shape bidirectional) (at 71.12 316.23 180) (effects (font (size 1.27 1.27)) (justify right)) (uuid "{uid()}"))"""

    # Insert j2_wiring, sheet_block, u1_inter_wiring before the last closing paren of Hexapod_Robot_Board.kicad_sch
    last_p = new_sch.rfind(')')
    final_main_sch = new_sch[:last_p] + j2_wiring + sheet_block + u1_inter_wiring + '\n)'

    with open('Hexapod_Robot_Board.kicad_sch', 'w', encoding='utf-8') as f:
        f.write(final_main_sch)
    print("Hexapod_Robot_Board.kicad_sch updated successfully.")

if __name__ == '__main__':
    main()
