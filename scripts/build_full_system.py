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

def sym_inst(lib_id, ref, val, fp, x, y, rot=0, props=None):
    if props is None: props = {}
    p_str = ""
    for k, v in props.items():
        p_str += f"""\t\t(property "{k}" "{v}" (at {x} {y} 0) (hide yes) (effects (font (size 1.27 1.27))))\n"""
    return f"""\t(symbol
\t\t(lib_id "{lib_id}")
\t\t(at {x} {y} {rot})
\t\t(unit 1)
\t\t(exclude_from_sim no)
\t\t(in_bom yes)
\t\t(on_board yes)
\t\t(in_pos_files yes)
\t\t(dnp no)
\t\t(uuid "{uid()}")
\t\t(property "Reference" "{ref}" (at {x} {y - 4} 0) (effects (font (size 1.27 1.27))))
\t\t(property "Value" "{val}" (at {x} {y + 4} 0) (effects (font (size 1.27 1.27))))
\t\t(property "Footprint" "{fp}" (at {x} {y} 0) (hide yes) (effects (font (size 1.27 1.27))))
{p_str}\t)"""

def wire(x1, y1, x2, y2):
    return f"""\t(wire (pts (xy {x1:.2f} {y1:.2f}) (xy {x2:.2f} {y2:.2f})) (stroke (width 0) (type default)) (uuid "{uid()}"))"""

def h_label(name, x, y, rot=0, shape="input"):
    return f"""\t(hierarchical_label "{name}" (shape {shape}) (at {x:.2f} {y:.2f} {rot}) (effects (font (size 1.27 1.27)) (justify left)) (uuid "{uid()}"))"""

def local_label(name, x, y, rot=0):
    return f"""\t(label "{name}" (at {x:.2f} {y:.2f} {rot}) (effects (font (size 1.27 1.27)) (justify left)) (uuid "{uid()}"))"""

def build_subsheet():
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

    ams5_path = '/home/peacemaker/.local/share/kicad-appimage/share/kicad/symbols/Regulator_Linear.kicad_symdir/AMS1117-5.0.kicad_sym'
    with open(ams5_path, 'r', encoding='utf-8') as f:
        ams5_raw = f.read()
    sym_ams5 = get_full_symbol(ams5_raw, 'AMS1117-5.0')
    sym_ams5 = sym_ams5.replace('(symbol "AMS1117-5.0"', '(symbol "Regulator_Linear:AMS1117-5.0"', 1)

    sub_lib_symbols = f"""\t(lib_symbols
\t\t{sym_esp}
\t\t{sym_usb}
\t\t{sym_c24}
\t\t{sym_c4}
\t\t{sym_ams}
\t\t{sym_ams5}
\t\t{sym_r}
\t\t{sym_c}
\t\t{sym_l}
\t\t{sym_led}
\t\t{sym_sw}
\t\t{sym_pwr}
\t)"""

    elements = []
    
    # Hierarchical labels
    elements.append(h_label("VBAT_SW", 30.0, 40.0, shape="input"))
    elements.append(h_label("GND", 30.0, 50.0, shape="input"))
    elements.append(h_label("INTER_UART_TX", 30.0, 60.0, shape="output"))
    elements.append(h_label("INTER_UART_RX", 30.0, 70.0, shape="input"))
    elements.append(h_label("VISION_SYNC", 30.0, 80.0, shape="output"))
    elements.append(h_label("VISION_RESET", 30.0, 90.0, shape="input"))

    # Dedicated 5V ToF Regulator U_REG_5V_TOF (AMS1117-5.0) at (80, 40)
    elements.append(sym_inst("Regulator_Linear:AMS1117-5.0", "U_REG_5V_TOF", "AMS1117-5.0", "Package_TO_SOT_SMD:SOT-223-3_TabPin2", 80.0, 40.0))
    elements.append(wire(30.0, 40.0, 72.38, 40.0)) # VBAT_SW to VI
    elements.append(wire(87.62, 40.0, 95.0, 40.0))
    elements.append(local_label("+5V_TOF", 95.0, 40.0))
    elements.append(wire(30.0, 50.0, 80.0, 50.0))
    elements.append(wire(80.0, 50.0, 80.0, 32.38)) # GND to Pin 1
    elements.append(local_label("GND", 80.0, 50.0))

    # Dedicated 3.3V Vision LDO U_LDO_VIS (AMS1117-3.3) at (130, 40)
    elements.append(sym_inst("Regulator_Linear:AMS1117-3.3", "U_LDO_VIS", "AMS1117-3.3", "Package_TO_SOT_SMD:SOT-223-3_TabPin2", 130.0, 40.0))
    elements.append(wire(72.38, 40.0, 122.38, 40.0)) # VBAT_SW bus
    elements.append(wire(137.62, 40.0, 145.0, 40.0))
    elements.append(local_label("+3V3_VIS", 145.0, 40.0))
    elements.append(wire(80.0, 50.0, 130.0, 50.0))
    elements.append(wire(130.0, 50.0, 130.0, 32.38)) # GND to Pin 1

    # MaixSense A010 Connector J_TOF (Conn_01x04) at (80, 90)
    elements.append(sym_inst("Connector_Generic:Conn_01x04", "J_TOF", "MaixSense_A010", "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical", 80.0, 90.0))
    elements.append(wire(74.92, 92.54, 65.0, 92.54))
    elements.append(local_label("+5V_TOF", 65.0, 92.54, rot=180))
    elements.append(wire(74.92, 90.0, 65.0, 90.0))
    elements.append(local_label("GND", 65.0, 90.0, rot=180))
    elements.append(wire(74.92, 87.46, 65.0, 87.46))
    elements.append(local_label("TOF_RXD", 65.0, 87.46, rot=180))
    elements.append(wire(74.92, 84.92, 65.0, 84.92))
    elements.append(local_label("TOF_TXD", 65.0, 84.92, rot=180))

    # Dedicated USB-C Receptacle J3 (J_USB_VISION) at (80, 160)
    elements.append(sym_inst("Connector:USB_C_Receptacle_USB2.0_16P", "J3", "USB-C_VISION", "Connector_USB:USB_C_Receptacle_HCTL_HC-TYPE-C-16P-01A", 80.0, 160.0))
    elements.append(wire(95.24, 157.46, 105.0, 157.46))
    elements.append(local_label("VIS_USB_D+", 105.0, 157.46))
    elements.append(wire(95.24, 154.92, 105.0, 157.46))
    elements.append(wire(95.24, 160.0, 105.0, 160.0))
    elements.append(local_label("VIS_USB_D-", 105.0, 160.0))
    elements.append(wire(95.24, 162.54, 105.0, 160.0))
    elements.append(wire(80.0, 137.14, 80.0, 130.0))
    elements.append(local_label("GND", 80.0, 130.0))

    # Vision MCU U_VIS (ESP32-S3-WROOM-1U-N8R8) at (170, 120)
    elements.append(sym_inst("RF_Module:ESP32-S3-WROOM-1", "U8", "ESP32-S3-WROOM-1U-N8R8", "RF_Module:ESP32-S3-WROOM-1U", 170.0, 120.0))
    
    # 3V3 and GND
    elements.append(wire(170.0, 147.94, 170.0, 155.0))
    elements.append(local_label("+3V3_VIS", 170.0, 155.0))
    elements.append(wire(170.0, 92.06, 170.0, 85.0))
    elements.append(local_label("GND", 170.0, 85.0))

    # EN to VISION_RESET
    elements.append(wire(154.76, 142.86, 30.0, 90.0))
    
    # BOOT button
    elements.append(wire(154.76, 137.78, 145.0, 137.78))
    elements.append(local_label("BOOT_VIS", 145.0, 137.78, rot=180))

    # TOF pins
    elements.append(wire(154.76, 135.24, 145.0, 135.24))
    elements.append(local_label("TOF_RXD", 145.0, 135.24, rot=180))
    elements.append(wire(154.76, 132.70, 145.0, 132.70))
    elements.append(local_label("TOF_TXD", 145.0, 132.70, rot=180))

    # Camera DVP pins (left side)
    elements.append(wire(154.76, 127.62, 145.0, 127.62))
    elements.append(local_label("CAM_SDA", 145.0, 127.62, rot=180))
    elements.append(wire(154.76, 125.08, 145.0, 125.08))
    elements.append(local_label("CAM_SCL", 145.0, 125.08, rot=180))
    elements.append(wire(154.76, 122.54, 145.0, 122.54))
    elements.append(local_label("CAM_VSYNC", 145.0, 122.54, rot=180))
    elements.append(wire(154.76, 120.0, 145.0, 120.0))
    elements.append(local_label("CAM_HREF", 145.0, 120.0, rot=180))
    elements.append(wire(154.76, 117.46, 145.0, 117.46))
    elements.append(local_label("CAM_D2", 145.0, 117.46, rot=180))
    elements.append(wire(154.76, 114.92, 145.0, 114.92))
    elements.append(local_label("CAM_D1", 145.0, 114.92, rot=180))
    elements.append(wire(154.76, 112.38, 145.0, 112.38))
    elements.append(local_label("CAM_D3", 145.0, 112.38, rot=180))
    elements.append(wire(154.76, 109.84, 145.0, 109.84))
    elements.append(local_label("CAM_D0", 145.0, 109.84, rot=180))
    elements.append(wire(154.76, 107.30, 145.0, 107.30))
    elements.append(local_label("CAM_D4", 145.0, 107.30, rot=180))
    elements.append(wire(154.76, 104.76, 145.0, 104.76))
    elements.append(local_label("CAM_PCLK", 145.0, 104.76, rot=180))
    elements.append(wire(154.76, 99.68, 145.0, 99.68))
    elements.append(local_label("CAM_XCLK", 145.0, 99.68, rot=180))
    elements.append(wire(154.76, 97.14, 145.0, 97.14))
    elements.append(local_label("CAM_D7", 145.0, 97.14, rot=180))

    # Right side of MCU
    elements.append(wire(185.24, 142.86, 30.0, 60.0)) # TXD0 -> INTER_UART_TX
    elements.append(wire(185.24, 140.32, 30.0, 70.0)) # RXD0 -> INTER_UART_RX
    elements.append(wire(185.24, 137.78, 195.0, 137.78))
    elements.append(local_label("CAM_D6", 195.0, 137.78))
    elements.append(wire(185.24, 135.24, 195.0, 135.24))
    elements.append(local_label("CAM_D5", 195.0, 135.24))
    elements.append(wire(185.24, 132.70, 195.0, 132.70))
    elements.append(local_label("VIS_USB_D-", 195.0, 132.70))
    elements.append(wire(185.24, 130.16, 195.0, 130.16))
    elements.append(local_label("VIS_USB_D+", 195.0, 130.16))
    elements.append(wire(185.24, 127.62, 30.0, 80.0)) # IO21 -> VISION_SYNC
    elements.append(wire(185.24, 117.46, 195.0, 117.46))
    elements.append(local_label("CAM_PWDN", 195.0, 117.46))
    elements.append(wire(185.24, 112.38, 195.0, 112.38))
    elements.append(local_label("CAM_RESET", 195.0, 112.38))

    # 24-Pin Camera Connector J_CAM (Conn_01x24) at (250, 120)
    elements.append(sym_inst("Connector_Generic:Conn_01x24", "J_CAM", "OV3660_DVP_24P", "Connector_FFC-FPC:Hirose_FH12-24S-0.5SH_1x24-1MP_P0.50mm_Horizontal", 250.0, 120.0))
    cam_pin_map = {
        1: "CAM_D7", 2: "CAM_D6", 3: "CAM_D5", 4: "CAM_D4",
        5: "CAM_D3", 6: "CAM_D2", 7: "CAM_D1", 8: "CAM_D0",
        9: "GND", 10: "CAM_PCLK", 11: "GND", 12: "CAM_XCLK",
        13: "GND", 14: "CAM_VSYNC", 15: "+3V3_VIS", 16: "CAM_HREF",
        17: "CAM_RESET", 18: "CAM_PWDN", 19: "GND", 20: "CAM_SCL",
        21: "+3V3_VIS", 22: "CAM_SDA", 23: "+3V3_VIS", 24: "GND"
    }
    for p_num, net in cam_pin_map.items():
        py = 120.0 + 27.94 - (p_num - 1) * 2.54
        elements.append(wire(244.92, py, 235.0, py))
        elements.append(local_label(net, 235.0, py, rot=180))

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
    print("Hexapod_Vision_Subsystem.kicad_sch written successfully.")

if __name__ == '__main__':
    build_subsheet()
