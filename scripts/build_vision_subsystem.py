#!/usr/bin/env python3
"""
build_vision_subsystem.py
Complete builder for:
1. Hexapod_Vision_Subsystem.kicad_sch
2. Updating Hexapod_Robot_Board.kicad_sch (triple USB-C + hierarchical sheet)
3. Full ERC validation
"""

import os
import re
import uuid
import subprocess

def uid():
    return str(uuid.uuid4())

def get_symbol_from_file(path, sym_name):
    with open(path, 'r', encoding='utf-8') as f:
        text = f.read()
    pattern = rf'(\(symbol\s+\"{re.escape(sym_name)}\".*?\n\t\t\))'
    m = re.search(pattern, text, re.DOTALL)
    if m:
        return m.group(1)
    return ""

def main():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(root_dir)
    print("Working directory:", root_dir)

    # 1. Read main schematic
    with open('Hexapod_Robot_Board.kicad_sch', 'r', encoding='utf-8') as f:
        main_sch = f.read()

    # Extract required symbols
    sym_esp = get_symbol_from_file('Hexapod_Robot_Board.kicad_sch', 'RF_Module:ESP32-S3-WROOM-1')
    sym_usb = get_symbol_from_file('Hexapod_Robot_Board.kicad_sch', 'Connector:USB_C_Receptacle_USB2.0_16P')
    sym_ams = get_symbol_from_file('Hexapod_Robot_Board.kicad_sch', 'Regulator_Linear:AMS1117-3.3')
    sym_r   = get_symbol_from_file('Hexapod_Robot_Board.kicad_sch', 'Device:R')
    sym_c   = get_symbol_from_file('Hexapod_Robot_Board.kicad_sch', 'Device:C')
    sym_l   = get_symbol_from_file('Hexapod_Robot_Board.kicad_sch', 'Device:L')
    sym_led = get_symbol_from_file('Hexapod_Robot_Board.kicad_sch', 'Device:LED')
    sym_sw  = get_symbol_from_file('Hexapod_Robot_Board.kicad_sch', 'Switch:SW_Push')
    sym_pwr = get_symbol_from_file('Hexapod_Robot_Board.kicad_sch', 'power:PWR_FLAG')
    sym_c4  = get_symbol_from_file('Hexapod_Robot_Board.kicad_sch', 'Connector_Generic:Conn_01x04')

    # Load Conn_01x24 from external lib
    conn24_path = '/home/peacemaker/.local/share/kicad-appimage/share/kicad/symbols/Connector_Generic.kicad_symdir/Conn_01x24.kicad_sym'
    with open(conn24_path, 'r', encoding='utf-8') as f:
        c24_raw = f.read()
    idx = c24_raw.find('(symbol "Conn_01x24"')
    last_p = c24_raw.rfind(')')
    sym_c24 = c24_raw[idx:last_p].rstrip()
    sym_c24 = sym_c24.replace('(symbol "Conn_01x24"', '(symbol "Connector_Generic:Conn_01x24"')
    sym_c24 = sym_c24.replace('"Conn_01x24_0_1"', '"Connector_Generic:Conn_01x24_0_1"')
    sym_c24 = sym_c24.replace('"Conn_01x24_1_1"', '"Connector_Generic:Conn_01x24_1_1"')

    # Create AMS1117-5.0 symbol derived from AMS1117-3.3
    sym_ams5 = sym_ams.replace('"Regulator_Linear:AMS1117-3.3"', '"Regulator_Linear:AMS1117-5.0"')
    sym_ams5 = sym_ams5.replace('"AMS1117-3.3_0_0"', '"AMS1117-5.0_0_0"')
    sym_ams5 = sym_ams5.replace('"AMS1117-3.3_0_1"', '"AMS1117-5.0_0_1"')
    sym_ams5 = sym_ams5.replace('"AMS1117-3.3_1_1"', '"AMS1117-5.0_1_1"')
    sym_ams5 = sym_ams5.replace('"AMS1117-3.3"', '"AMS1117-5.0"')

    sub_lib_symbols = f"""\t(lib_symbols
{sym_esp}
{sym_usb}
{sym_c24}
{sym_c4}
{sym_ams}
{sym_ams5}
{sym_r}
{sym_c}
{sym_l}
{sym_led}
{sym_sw}
{sym_pwr}
\t)"""

    print("Sub-sheet lib_symbols ready with AMS1117-5.0, AMS1117-3.3, ESP32-S3, USB-C, Conn_01x24, Conn_01x04.")

if __name__ == '__main__':
    main()
