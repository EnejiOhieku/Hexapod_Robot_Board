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

def main():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(root_dir)

    with open('Hexapod_Robot_Board.kicad_sch', 'r', encoding='utf-8') as f:
        main_sch = f.read()

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

    # Placement Origins
    u8_x, u8_y = 152.40, 127.00
    j_cam_x, j_cam_y = 254.00, 127.00
    j_tof_x, j_tof_y = 76.20, 101.60
    j_usb_x, j_usb_y = 76.20, 177.80
    u_tof_x, u_tof_y = 76.20, 50.80
    u_vis_ldo_x, u_vis_ldo_y = 127.00, 50.80

    # Pin maps
    pins_u8 = get_pin_map(sym_esp, u8_x, u8_y)
    pins_cam = get_pin_map(sym_c24, j_cam_x, j_cam_y)
    pins_tof = get_pin_map(sym_c4, j_tof_x, j_tof_y)
    pins_usb = get_pin_map(sym_usb, j_usb_x, j_usb_y)
    pins_ams5 = get_pin_map(sym_ams, u_tof_x, u_tof_y)
    pins_ams3 = get_pin_map(sym_ams, u_vis_ldo_x, u_vis_ldo_y)

    elements = []

    # 1. Hierarchical labels (X = 25.40)
    elements.append(h_label("VBAT_SW", 25.40, 50.80, shape="input"))
    elements.append(h_label("GND", 25.40, 63.50, shape="input"))
    elements.append(h_label("INTER_UART_TX", 25.40, 104.14, shape="output"))
    elements.append(h_label("INTER_UART_RX", 25.40, 106.68, shape="input"))
    elements.append(h_label("VISION_SYNC", 25.40, 119.38, shape="output"))
    elements.append(h_label("VISION_RESET", 25.40, 93.98, shape="input"))

    # 2. U_REG_5V_TOF (AMS1117-5.0)
    elements.append(sym_inst("Regulator_Linear:AMS1117-3.3", "U_REG_5V_TOF", "AMS1117-5.0", "Package_TO_SOT_SMD:SOT-223-3_TabPin2", u_tof_x, u_tof_y))
    p3_x, p3_y, _, _ = pins_ams5['3'] # VI
    elements.append(wire(25.40, 50.80, p3_x, p3_y))
    p2_x, p2_y, _, _ = pins_ams5['2'] # VO (+5V_TOF)
    elements.append(wire(p2_x, p2_y, p2_x + 10.16, p2_y))
    elements.append(local_label("+5V_TOF", p2_x + 10.16, p2_y))
    p1_x, p1_y, _, _ = pins_ams5['1'] # GND
    elements.append(wire(p1_x, p1_y, p1_x, 63.50))
    elements.append(wire(25.40, 63.50, p1_x, 63.50))
    elements.append(local_label("GND", p1_x, 63.50))

    # 3. U_LDO_VIS (AMS1117-3.3)
    elements.append(sym_inst("Regulator_Linear:AMS1117-3.3", "U_LDO_VIS", "AMS1117-3.3", "Package_TO_SOT_SMD:SOT-223-3_TabPin2", u_vis_ldo_x, u_vis_ldo_y))
    p3_x, p3_y, _, _ = pins_ams3['3']
    elements.append(wire(pins_ams5['3'][0], pins_ams5['3'][1], p3_x, p3_y)) # VBAT_SW bus
    p2_x, p2_y, _, _ = pins_ams3['2']
    elements.append(wire(p2_x, p2_y, p2_x + 10.16, p2_y))
    elements.append(local_label("+3V3_VIS", p2_x + 10.16, p2_y))
    p1_x, p1_y, _, _ = pins_ams3['1']
    elements.append(wire(p1_x, p1_y, p1_x, 63.50))
    elements.append(wire(pins_ams5['1'][0], 63.50, p1_x, 63.50))

    # 4. J_TOF (MaixSense A010)
    elements.append(sym_inst("Connector_Generic:Conn_01x04", "J_TOF", "MaixSense_A010", "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical", j_tof_x, j_tof_y))
    p_x, p_y, _, _ = pins_tof['1']
    elements.append(wire(p_x, p_y, p_x - 10.16, p_y))
    elements.append(local_label("+5V_TOF", p_x - 10.16, p_y, rot=180))
    p_x, p_y, _, _ = pins_tof['2']
    elements.append(wire(p_x, p_y, p_x - 10.16, p_y))
    elements.append(local_label("GND", p_x - 10.16, p_y, rot=180))
    p_x, p_y, _, _ = pins_tof['3']
    elements.append(wire(p_x, p_y, p_x - 10.16, p_y))
    elements.append(local_label("TOF_RXD", p_x - 10.16, p_y, rot=180))
    p_x, p_y, _, _ = pins_tof['4']
    elements.append(wire(p_x, p_y, p_x - 10.16, p_y))
    elements.append(local_label("TOF_TXD", p_x - 10.16, p_y, rot=180))

    # 5. J3 USB-C (USB-C_VISION)
    elements.append(sym_inst("Connector:USB_C_Receptacle_USB2.0_16P", "J3", "USB-C_VISION", "Connector_USB:USB_C_Receptacle_HCTL_HC-TYPE-C-16P-01A", j_usb_x, j_usb_y))
    # D+ (A6, B6)
    dp_a_x, dp_a_y, _, _ = pins_usb['A6']
    dp_b_x, dp_b_y, _, _ = pins_usb['B6']
    elements.append(wire(dp_a_x, dp_a_y, dp_a_x + 10.16, dp_a_y))
    elements.append(local_label("VIS_USB_D+", dp_a_x + 10.16, dp_a_y))
    elements.append(wire(dp_b_x, dp_b_y, dp_a_x + 10.16, dp_a_y))
    # D- (A7, B7)
    dm_a_x, dm_a_y, _, _ = pins_usb['A7']
    dm_b_x, dm_b_y, _, _ = pins_usb['B7']
    elements.append(wire(dm_a_x, dm_a_y, dm_a_x + 10.16, dm_a_y))
    elements.append(local_label("VIS_USB_D-", dm_a_x + 10.16, dm_a_y))
    elements.append(wire(dm_b_x, dm_b_y, dm_a_x + 10.16, dm_a_y))
    # GND (A1, B1, A12, B12, SH)
    gnd_x, gnd_y, _, _ = pins_usb['A1']
    elements.append(wire(gnd_x, gnd_y, gnd_x, gnd_y + 10.16))
    elements.append(local_label("GND", gnd_x, gnd_y + 10.16))
    sh_x, sh_y, _, _ = pins_usb['SH']
    elements.append(wire(sh_x, sh_y, gnd_x, gnd_y + 10.16))
    # CC1, CC2 pulled down
    cc1_x, cc1_y, _, _ = pins_usb['A5']
    elements.append(wire(cc1_x, cc1_y, cc1_x + 5.08, cc1_y))
    elements.append(local_label("VIS_CC1", cc1_x + 5.08, cc1_y))
    cc2_x, cc2_y, _, _ = pins_usb['B5']
    elements.append(wire(cc2_x, cc2_y, cc2_x + 5.08, cc2_y))
    elements.append(local_label("VIS_CC2", cc2_x + 5.08, cc2_y))

    # 6. Vision MCU U8 (ESP32-S3-WROOM-1U-N8R8)
    elements.append(sym_inst("RF_Module:ESP32-S3-WROOM-1", "U8", "ESP32-S3-WROOM-1U-N8R8", "RF_Module:ESP32-S3-WROOM-1U", u8_x, u8_y))

    # Pin 1 (GND): (152.40, 154.94)
    p_x, p_y, _, _ = pins_u8['1']
    elements.append(wire(p_x, p_y, p_x, p_y + 7.62))
    elements.append(local_label("GND", p_x, p_y + 7.62))

    # Pin 2 (3V3): (152.40, 99.06)
    p_x, p_y, _, _ = pins_u8['2']
    elements.append(wire(p_x, p_y, p_x, p_y - 7.62))
    elements.append(local_label("+3V3_VIS", p_x, p_y - 7.62))

    # Pin 3 (EN) -> VISION_RESET
    p_x, p_y, _, _ = pins_u8['3']
    elements.append(wire(p_x, p_y, p_x - 10.16, p_y))
    elements.append(local_label("VISION_RESET", p_x - 10.16, p_y, rot=180))
    elements.append(wire(25.40, 93.98, 35.56, 93.98))
    elements.append(local_label("VISION_RESET", 35.56, 93.98))

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

    # 7. J_CAM (Conn_01x24)
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
        p_x, p_y, _, _ = pins_cam[pnum]
        elements.append(wire(p_x, p_y, p_x - 10.16, p_y))
        elements.append(local_label(net, p_x - 10.16, p_y, rot=180))

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
    print("Exact pin-mapped Hexapod_Vision_Subsystem.kicad_sch written.")

if __name__ == '__main__':
    main()
