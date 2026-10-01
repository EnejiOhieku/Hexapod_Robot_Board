#!/usr/bin/env python3
"""
update_schematic.py
Upgrades Hexapod_Robot_Board.kicad_sch:
1. Adds Sensor_Motion:MPU-6050 to lib_symbols.
2. Updates U1 to ESP32-S3-WROOM-1U with external antenna footprint.
3. Connects Pin 11 (GPIO18) of U1 to MPU_INT.
4. Splits Section 3 into Dual Buck Regulators (U3_R for V_SERVO_R, U3_L for V_SERVO_L).
5. Updates Section 7 servo headers (L1-L3 + AUX1-3 -> V_SERVO_R, L4-L6 + AUX4-6 -> V_SERVO_L).
6. Adds Section 8: MPU-6050 with all passives and connections to I2C, power, and MPU_INT.
"""

import sys
import re
import uuid

def gen_uuid():
    return str(uuid.uuid4())

def main():
    with open("Hexapod_Robot_Board.kicad_sch", "r", encoding="utf-8") as f:
        sch = f.read()

    # 1. Add Sensor_Motion:MPU-6050 to lib_symbols
    with open("/home/peacemaker/.local/share/kicad-appimage/share/kicad/symbols/Sensor_Motion.kicad_symdir/MPU-6050.kicad_sym", "r", encoding="utf-8") as f:
        mpu_lib_file = f.read()

    # extract (symbol "MPU-6050" ... down to embedded_fonts no)\n\t)
    m_sym = re.search(r"(\t\(symbol \"MPU-6050\".*?embedded_fonts no\)\s+\))", mpu_lib_file, re.DOTALL)
    if not m_sym:
        print("ERROR: could not find MPU-6050 in library file!")
        return 1
    mpu_sym_def = m_sym.group(1).replace('(symbol "MPU-6050"', '(symbol "Sensor_Motion:MPU-6050"')

    # insert into lib_symbols (before closing paren of lib_symbols)
    # find (lib_symbols ... )
    pos_lib = sch.find("(lib_symbols")
    # find where lib_symbols closes
    # Each top-level symbol starts with \t\t(symbol "
    # The lib_symbols closes at \n\t) before (wire or (rectangle
    pos_first_wire = sch.find("\n\t(wire", pos_lib)
    if pos_first_wire == -1:
        pos_first_wire = sch.find("\n\t(rectangle", pos_lib)
    # find the \t) before that
    pos_lib_close = sch.rfind("\t)", pos_lib, pos_first_wire)

    # Insert MPU symbol def indented properly
    indented_mpu = "\t\t" + mpu_sym_def.strip() + "\n"
    sch = sch[:pos_lib_close] + indented_mpu + sch[pos_lib_close:]
    print("Added Sensor_Motion:MPU-6050 to lib_symbols.")

    # 2. Update U1 in schematic
    # Find U1 symbol instance
    # (property "Reference" "U1")
    # Change Value to ESP32-S3-WROOM-1U, Footprint to RF_Module:ESP32-S3-WROOM-1U
    u1_pos = sch.find('(property "Reference" "U1"')
    if u1_pos != -1:
        # find start of symbol
        u1_start = sch.rfind('\n\t(symbol', 0, u1_pos)
        u1_end = sch.find('\n\t)', u1_pos) + 3
        u1_block = sch[u1_start:u1_end]

        u1_block = re.sub(r'\(property "Value" "ESP32-S3-WROOM-1"', '(property "Value" "ESP32-S3-WROOM-1U"', u1_block)
        u1_block = re.sub(r'\(property "Footprint" "RF_Module:ESP32-S3-WROOM-1"', '(property "Footprint" "RF_Module:ESP32-S3-WROOM-1U"', u1_block)
        sch = sch[:u1_start] + u1_block + sch[u1_end:]
        print("Updated U1 to ESP32-S3-WROOM-1U.")

    # 3. Connect Pin 11 (GPIO18) of U1 to MPU_INT
    # Pin 11 is at (110.49, 283.21)
    mpu_int_wire = f"""\t(wire (pts (xy 110.49 283.21) (xy 115.57 283.21)) (stroke (width 0) (type default)) (uuid "{gen_uuid()}"))
\t(global_label "MPU_INT"
\t\t(shape input)
\t\t(at 115.57 283.21 0)
\t\t(effects
\t\t\t(font
\t\t\t\t(size 1.27 1.27)
\t\t\t)
\t\t\t(justify left)
\t\t)
\t\t(uuid "{gen_uuid()}")
\t)
"""
    # Insert wire after the last U1 wire
    sch = sch.replace('(wire (pts (xy 110.49 278.13) (xy 115.57 278.13)) (stroke (width 0) (type default))',
                      mpu_int_wire + '\t(wire (pts (xy 110.49 278.13) (xy 115.57 278.13)) (stroke (width 0) (type default))')
    print("Connected MPU_INT to U1 pin 11 (GPIO18).")

    # 4. Update Section 7 Servo Header Power Nets
    # Right Side: J_L1_C/F/T, J_L2_C/F/T, J_L3_C/F/T, J_AUX1..3 -> V_SERVO_R
    # In schematic:
    # X = 407.67 (all 6 are Right: L1_C, L1_F, L1_T, L2_C, L2_F, L2_T)
    # X = 455.93, Y in [234.95, 260.35, 285.75] (L3_C, L3_F, L3_T)
    # X = 552.45, Y in [234.95, 260.35, 285.75] (AUX1, AUX2, AUX3)
    #
    # Left Side:
    # X = 455.93, Y in [311.15, 336.55, 361.95] (L4_C, L4_F, L4_T)
    # X = 504.19, Y in [234.95, 260.35, 285.75, 311.15, 336.55, 361.95] (L5_C..T, L6_C..T)
    # X = 552.45, Y in [311.15, 336.55, 361.95] (AUX4, AUX5, AUX6)

    def replace_servo_label(match):
        label_text = match.group(0)
        at_m = re.search(r"\(at\s+([0-9.]+)\s+([0-9.]+)", label_text)
        if not at_m:
            return label_text
        x, y = float(at_m.group(1)), float(at_m.group(2))
        
        # check if Right side
        is_right = False
        if abs(x - 407.67) < 0.1:
            is_right = True
        elif abs(x - 455.93) < 0.1 and y <= 290.0:
            is_right = True
        elif abs(x - 552.45) < 0.1 and y <= 290.0:
            is_right = True

        # check if Left side
        is_left = False
        if abs(x - 455.93) < 0.1 and y > 290.0:
            is_left = True
        elif abs(x - 504.19) < 0.1:
            is_left = True
        elif abs(x - 552.45) < 0.1 and y > 290.0:
            is_left = True

        if is_right:
            return label_text.replace('"V_SERVO"', '"V_SERVO_R"')
        elif is_left:
            return label_text.replace('"V_SERVO"', '"V_SERVO_L"')
        return label_text

    # Match all global_label "V_SERVO" in Section 7
    # They have (at X Y 180) where X >= 400 and Y >= 200
    sec7_label_pattern = re.compile(r'\t\(global_label "V_SERVO"\s+\(shape input\)\s+\(at\s+(?:407\.67|455\.93|504\.19|552\.45)\s+[0-9.]+\s+180\).*?\t\)', re.DOTALL)
    sch, count = sec7_label_pattern.subn(replace_servo_label, sch)
    print(f"Replaced {count} servo power labels in Section 7.")

    # 5. Dual Buck Regulators in Section 3
    # Replace the existing Section 3 components and wires with two clean buck circuits:
    # Right Buck (V_SERVO_R) and Left Buck (V_SERVO_L)
    # Remove existing U3, C_IN1, C_IN2, D_CATCH, L_SERVO, C_OUT1..3, R_FB1..2, LED_SERVO, R_SERVO_LED, #FLG05 symbol instances
    sec3_refs = ["U3", "C_IN1", "C_IN2", "D_CATCH", "L_SERVO", "C_OUT1", "C_OUT2", "C_OUT3", "R_FB1", "R_FB2", "LED_SERVO", "R_SERVO_LED", "#FLG05"]
    for ref in sec3_refs:
        pat = re.compile(r'\n\t\(symbol\s+\(lib_id "[^"]+"\)\s+\(at [0-9.-]+ [0-9.-]+ [0-9.-]+\).*?\(property "Reference" "' + re.escape(ref) + r'".*?\n\t\)', re.DOTALL)
        sch, n = pat.subn('', sch)
        print(f"Removed symbol instance {ref} (removed {n})")

    # Remove existing wires and labels in Section 3 (X in [276, 422], Y in [12, 191])
    # Let us remove all global labels and wires strictly in this box
    def should_remove_wire(m):
        x1, y1 = float(m.group(1)), float(m.group(2))
        x2, y2 = float(m.group(3)), float(m.group(4))
        if 276 <= x1 <= 422 and 12 <= y1 <= 191 and 276 <= x2 <= 422 and 12 <= y2 <= 191:
            return ""
        return m.group(0)

    sch = re.sub(r'\t\(wire\s+\(pts\s+\(xy\s+([0-9.]+)\s+([0-9.]+)\)\s+\(xy\s+([0-9.]+)\s+([0-9.]+)\)\).*?\t\)\n', should_remove_wire, sch)

    def should_remove_label(m):
        x, y = float(m.group(2)), float(m.group(3))
        if 276 <= x <= 422 and 12 <= y <= 191:
            return ""
        return m.group(0)

    sch = re.sub(r'\t\(global_label\s+"([^"]+)"\s+\(shape\s+[a-z]+\)\s+\(at\s+([0-9.]+)\s+([0-9.]+)\s+[0-9.]+\).*?\t\)\n', should_remove_label, sch)

    # Now define the dual buck converter subcircuits
    # Section 3 area is X: 276.86 to 421.64, Y: 12.70 to 190.50
    # Let us place Right Buck in top half (Y: 20 to 95)
    # and Left Buck in bottom half (Y: 105 to 180)
    # Or side by side: Right Buck at X: 280-345, Left Buck at X: 350-415.
    # Stacking them vertically (Top: Right Buck, Bottom: Left Buck) is very clear:
    
    # Helper to generate a complete buck converter schematic block
    def make_buck_circuit(prefix, title, out_net, sw_net, fb_net, y_offset, u3_ref):
        # Coordinates offset by y_offset
        # U3 at (323.85, 45.0 + y_offset)
        # C_IN1 at (294.64, 30.0 + y_offset), C_IN2 at (307.34, 30.0 + y_offset)
        # D_CATCH at (345.44, 55.0 + y_offset)
        # L_SERVO at (361.95, 42.0 + y_offset)
        # C_OUT1 at (383.54, 30.0 + y_offset), C_OUT2 at (396.24, 30.0 + y_offset), C_OUT3 at (408.94, 30.0 + y_offset)
        # R_FB1 at (374.65, 60.0 + y_offset), R_FB2 at (374.65, 75.0 + y_offset)
        # LED at (400.05, 60.0 + y_offset), R_LED at (400.05, 75.0 + y_offset)
        yo = y_offset

        circuit_text = f"""
\t(text "{title}" (at 280.86 {20.0 + yo} 0) (effects (font (size 2.0 2.0) bold (color 0 100 180 1))) (uuid "{gen_uuid()}"))
\t(wire (pts (xy 294.64 {25.0 + yo}) (xy 294.64 {21.0 + yo})) (stroke (width 0) (type default)) (uuid "{gen_uuid()}"))
\t(global_label "VBAT_SW" (shape input) (at 294.64 {21.0 + yo} 90) (effects (font (size 1.27 1.27))) (uuid "{gen_uuid()}"))
\t(wire (pts (xy 294.64 {35.0 + yo}) (xy 294.64 {39.0 + yo})) (stroke (width 0) (type default)) (uuid "{gen_uuid()}"))
\t(global_label "GND" (shape input) (at 294.64 {39.0 + yo} 270) (effects (font (size 1.27 1.27))) (uuid "{gen_uuid()}"))

\t(wire (pts (xy 307.34 {25.0 + yo}) (xy 307.34 {21.0 + yo})) (stroke (width 0) (type default)) (uuid "{gen_uuid()}"))
\t(global_label "VBAT_SW" (shape input) (at 307.34 {21.0 + yo} 90) (effects (font (size 1.27 1.27))) (uuid "{gen_uuid()}"))
\t(wire (pts (xy 307.34 {35.0 + yo}) (xy 307.34 {39.0 + yo})) (stroke (width 0) (type default)) (uuid "{gen_uuid()}"))
\t(global_label "GND" (shape input) (at 307.34 {39.0 + yo} 270) (effects (font (size 1.27 1.27))) (uuid "{gen_uuid()}"))

\t(wire (pts (xy 316.23 {42.46 + yo}) (xy 310.0 {42.46 + yo})) (stroke (width 0) (type default)) (uuid "{gen_uuid()}"))
\t(global_label "VBAT_SW" (shape input) (at 310.0 {42.46 + yo} 180) (effects (font (size 1.27 1.27))) (uuid "{gen_uuid()}"))

\t(wire (pts (xy 323.85 {52.62 + yo}) (xy 323.85 {56.0 + yo})) (stroke (width 0) (type default)) (uuid "{gen_uuid()}"))
\t(global_label "GND" (shape input) (at 323.85 {56.0 + yo} 270) (effects (font (size 1.27 1.27))) (uuid "{gen_uuid()}"))

\t(wire (pts (xy 316.23 {47.54 + yo}) (xy 310.0 {47.54 + yo})) (stroke (width 0) (type default)) (uuid "{gen_uuid()}"))
\t(global_label "GND" (shape input) (at 310.0 {47.54 + yo} 180) (effects (font (size 1.27 1.27))) (uuid "{gen_uuid()}"))

\t(wire (pts (xy 331.47 {42.46 + yo}) (xy 337.0 {42.46 + yo})) (stroke (width 0) (type default)) (uuid "{gen_uuid()}"))
\t(global_label "{sw_net}" (shape bidirectional) (at 337.0 {42.46 + yo} 0) (effects (font (size 1.27 1.27))) (uuid "{gen_uuid()}"))

\t(wire (pts (xy 331.47 {47.54 + yo}) (xy 337.0 {47.54 + yo})) (stroke (width 0) (type default)) (uuid "{gen_uuid()}"))
\t(global_label "{fb_net}" (shape input) (at 337.0 {47.54 + yo} 0) (effects (font (size 1.27 1.27))) (uuid "{gen_uuid()}"))

\t(wire (pts (xy 345.44 {51.19 + yo}) (xy 345.44 {47.0 + yo})) (stroke (width 0) (type default)) (uuid "{gen_uuid()}"))
\t(global_label "{sw_net}" (shape bidirectional) (at 345.44 {47.0 + yo} 90) (effects (font (size 1.27 1.27))) (uuid "{gen_uuid()}"))
\t(wire (pts (xy 345.44 {58.81 + yo}) (xy 345.44 {63.0 + yo})) (stroke (width 0) (type default)) (uuid "{gen_uuid()}"))
\t(global_label "GND" (shape input) (at 345.44 {63.0 + yo} 270) (effects (font (size 1.27 1.27))) (uuid "{gen_uuid()}"))

\t(wire (pts (xy 358.14 {42.0 + yo}) (xy 354.0 {42.0 + yo})) (stroke (width 0) (type default)) (uuid "{gen_uuid()}"))
\t(global_label "{sw_net}" (shape bidirectional) (at 354.0 {42.0 + yo} 180) (effects (font (size 1.27 1.27))) (uuid "{gen_uuid()}"))
\t(wire (pts (xy 365.76 {42.0 + yo}) (xy 370.0 {42.0 + yo})) (stroke (width 0) (type default)) (uuid "{gen_uuid()}"))
\t(global_label "{out_net}" (shape output) (at 370.0 {42.0 + yo} 0) (effects (font (size 1.27 1.27))) (uuid "{gen_uuid()}"))

\t(wire (pts (xy 383.54 {25.0 + yo}) (xy 383.54 {21.0 + yo})) (stroke (width 0) (type default)) (uuid "{gen_uuid()}"))
\t(global_label "{out_net}" (shape output) (at 383.54 {21.0 + yo} 90) (effects (font (size 1.27 1.27))) (uuid "{gen_uuid()}"))
\t(wire (pts (xy 383.54 {35.0 + yo}) (xy 383.54 {39.0 + yo})) (stroke (width 0) (type default)) (uuid "{gen_uuid()}"))
\t(global_label "GND" (shape input) (at 383.54 {39.0 + yo} 270) (effects (font (size 1.27 1.27))) (uuid "{gen_uuid()}"))

\t(wire (pts (xy 396.24 {25.0 + yo}) (xy 396.24 {21.0 + yo})) (stroke (width 0) (type default)) (uuid "{gen_uuid()}"))
\t(global_label "{out_net}" (shape output) (at 396.24 {21.0 + yo} 90) (effects (font (size 1.27 1.27))) (uuid "{gen_uuid()}"))
\t(wire (pts (xy 396.24 {35.0 + yo}) (xy 396.24 {39.0 + yo})) (stroke (width 0) (type default)) (uuid "{gen_uuid()}"))
\t(global_label "GND" (shape input) (at 396.24 {39.0 + yo} 270) (effects (font (size 1.27 1.27))) (uuid "{gen_uuid()}"))

\t(wire (pts (xy 408.94 {25.0 + yo}) (xy 408.94 {21.0 + yo})) (stroke (width 0) (type default)) (uuid "{gen_uuid()}"))
\t(global_label "{out_net}" (shape output) (at 408.94 {21.0 + yo} 90) (effects (font (size 1.27 1.27))) (uuid "{gen_uuid()}"))
\t(wire (pts (xy 408.94 {35.0 + yo}) (xy 408.94 {39.0 + yo})) (stroke (width 0) (type default)) (uuid "{gen_uuid()}"))
\t(global_label "GND" (shape input) (at 408.94 {39.0 + yo} 270) (effects (font (size 1.27 1.27))) (uuid "{gen_uuid()}"))

\t(wire (pts (xy 374.65 {56.19 + yo}) (xy 374.65 {52.0 + yo})) (stroke (width 0) (type default)) (uuid "{gen_uuid()}"))
\t(global_label "{out_net}" (shape output) (at 374.65 {52.0 + yo} 90) (effects (font (size 1.27 1.27))) (uuid "{gen_uuid()}"))
\t(wire (pts (xy 374.65 {63.81 + yo}) (xy 374.65 {67.0 + yo})) (stroke (width 0) (type default)) (uuid "{gen_uuid()}"))
\t(global_label "{fb_net}" (shape input) (at 374.65 {67.0 + yo} 270) (effects (font (size 1.27 1.27))) (uuid "{gen_uuid()}"))

\t(wire (pts (xy 374.65 {71.19 + yo}) (xy 374.65 {68.0 + yo})) (stroke (width 0) (type default)) (uuid "{gen_uuid()}"))
\t(global_label "{fb_net}" (shape input) (at 374.65 {68.0 + yo} 90) (effects (font (size 1.27 1.27))) (uuid "{gen_uuid()}"))
\t(wire (pts (xy 374.65 {78.81 + yo}) (xy 374.65 {82.0 + yo})) (stroke (width 0) (type default)) (uuid "{gen_uuid()}"))
\t(global_label "GND" (shape input) (at 374.65 {82.0 + yo} 270) (effects (font (size 1.27 1.27))) (uuid "{gen_uuid()}"))

\t(wire (pts (xy 400.05 {56.19 + yo}) (xy 400.05 {52.0 + yo})) (stroke (width 0) (type default)) (uuid "{gen_uuid()}"))
\t(global_label "{out_net}" (shape output) (at 400.05 {52.0 + yo} 90) (effects (font (size 1.27 1.27))) (uuid "{gen_uuid()}"))
\t(wire (pts (xy 400.05 {63.81 + yo}) (xy 400.05 {71.19 + yo})) (stroke (width 0) (type default)) (uuid "{gen_uuid()}"))
\t(wire (pts (xy 400.05 {78.81 + yo}) (xy 400.05 {82.0 + yo})) (stroke (width 0) (type default)) (uuid "{gen_uuid()}"))
\t(global_label "GND" (shape input) (at 400.05 {82.0 + yo} 270) (effects (font (size 1.27 1.27))) (uuid "{gen_uuid()}"))

\t(wire (pts (xy 387.35 {17.0 + yo}) (xy 387.35 {13.0 + yo})) (stroke (width 0) (type default)) (uuid "{gen_uuid()}"))
\t(global_label "{out_net}" (shape output) (at 387.35 {13.0 + yo} 90) (effects (font (size 1.27 1.27))) (uuid "{gen_uuid()}"))
"""
        # Symbol instances
        sym_instances = f"""
\t(symbol (lib_id "Regulator_Switching:XL4015") (at 323.85 {45.0 + yo} 0) (unit 1)
\t\t(property "Reference" "{u3_ref}" (at 326.39 {42.46 + yo} 0) (effects (font (size 1.27 1.27))))
\t\t(property "Value" "XL4015" (at 326.39 {47.54 + yo} 0) (effects (font (size 1.27 1.27))))
\t\t(property "Footprint" "Package_TO_SOT_SMD:TO-263-5_TabPin3" (at 71.12 196.85 0) (hide yes) (effects (font (size 1.27 1.27))))
\t\t(property "Datasheet" "http://www.xlsemi.net/datasheet/XL4015%20datasheet-English.pdf" (at 49.53 204.47 0) (hide yes) (effects (font (size 1.27 1.27))))
\t\t(property "Description" "5A 180kHz 36V Buck DC to DC Converter" (at 49.53 204.47 0) (hide yes) (effects (font (size 1.27 1.27))))
\t\t(pin "1" (uuid "{gen_uuid()}")) (pin "2" (uuid "{gen_uuid()}")) (pin "3" (uuid "{gen_uuid()}")) (pin "4" (uuid "{gen_uuid()}")) (pin "5" (uuid "{gen_uuid()}"))
\t\t(instances (project "Hexapod_Robot_Board" (path "/44f02a75-3141-486c-ae96-cf48718534a3" (reference "{u3_ref}") (unit 1))))
\t)
\t(symbol (lib_id "Device:C") (at 294.64 {30.0 + yo} 0) (unit 1)
\t\t(property "Reference" "C_IN1_{prefix}" (at 297.18 {27.46 + yo} 0) (effects (font (size 1.27 1.27))))
\t\t(property "Value" "100uF_25V" (at 297.18 {32.54 + yo} 0) (effects (font (size 1.27 1.27))))
\t\t(property "Footprint" "Capacitor_THT:CP_Radial_D8.0mm_P3.50mm" (at 71.12 196.85 0) (hide yes) (effects (font (size 1.27 1.27))))
\t\t(pin "1" (uuid "{gen_uuid()}")) (pin "2" (uuid "{gen_uuid()}"))
\t\t(instances (project "Hexapod_Robot_Board" (path "/44f02a75-3141-486c-ae96-cf48718534a3" (reference "C_IN1_{prefix}") (unit 1))))
\t)
\t(symbol (lib_id "Device:C") (at 307.34 {30.0 + yo} 0) (unit 1)
\t\t(property "Reference" "C_IN2_{prefix}" (at 309.88 {27.46 + yo} 0) (effects (font (size 1.27 1.27))))
\t\t(property "Value" "22uF_25V" (at 309.88 {32.54 + yo} 0) (effects (font (size 1.27 1.27))))
\t\t(property "Footprint" "Capacitor_SMD:C_1206_3216Metric" (at 71.12 196.85 0) (hide yes) (effects (font (size 1.27 1.27))))
\t\t(pin "1" (uuid "{gen_uuid()}")) (pin "2" (uuid "{gen_uuid()}"))
\t\t(instances (project "Hexapod_Robot_Board" (path "/44f02a75-3141-486c-ae96-cf48718534a3" (reference "C_IN2_{prefix}") (unit 1))))
\t)
\t(symbol (lib_id "Device:D_Schottky") (at 345.44 {55.0 + yo} 0) (unit 1)
\t\t(property "Reference" "D_CATCH_{prefix}" (at 347.98 {52.46 + yo} 0) (effects (font (size 1.27 1.27))))
\t\t(property "Value" "SS54" (at 347.98 {57.54 + yo} 0) (effects (font (size 1.27 1.27))))
\t\t(property "Footprint" "Diode_SMD:D_SMC" (at 71.12 196.85 0) (hide yes) (effects (font (size 1.27 1.27))))
\t\t(pin "1" (uuid "{gen_uuid()}")) (pin "2" (uuid "{gen_uuid()}"))
\t\t(instances (project "Hexapod_Robot_Board" (path "/44f02a75-3141-486c-ae96-cf48718534a3" (reference "D_CATCH_{prefix}") (unit 1))))
\t)
\t(symbol (lib_id "Device:L") (at 361.95 {42.0 + yo} 90) (unit 1)
\t\t(property "Reference" "L_SERVO_{prefix}" (at 361.95 {37.0 + yo} 90) (effects (font (size 1.27 1.27))))
\t\t(property "Value" "10uH_10A" (at 361.95 {47.0 + yo} 90) (effects (font (size 1.27 1.27))))
\t\t(property "Footprint" "Inductor_SMD:L_12x12mm_H8mm" (at 71.12 196.85 0) (hide yes) (effects (font (size 1.27 1.27))))
\t\t(pin "1" (uuid "{gen_uuid()}")) (pin "2" (uuid "{gen_uuid()}"))
\t\t(instances (project "Hexapod_Robot_Board" (path "/44f02a75-3141-486c-ae96-cf48718534a3" (reference "L_SERVO_{prefix}") (unit 1))))
\t)
\t(symbol (lib_id "Device:C") (at 383.54 {30.0 + yo} 0) (unit 1)
\t\t(property "Reference" "C_OUT1_{prefix}" (at 386.08 {27.46 + yo} 0) (effects (font (size 1.27 1.27))))
\t\t(property "Value" "1000uF_10V" (at 386.08 {32.54 + yo} 0) (effects (font (size 1.27 1.27))))
\t\t(property "Footprint" "Capacitor_THT:CP_Radial_D8.0mm_P3.50mm" (at 71.12 196.85 0) (hide yes) (effects (font (size 1.27 1.27))))
\t\t(pin "1" (uuid "{gen_uuid()}")) (pin "2" (uuid "{gen_uuid()}"))
\t\t(instances (project "Hexapod_Robot_Board" (path "/44f02a75-3141-486c-ae96-cf48718534a3" (reference "C_OUT1_{prefix}") (unit 1))))
\t)
\t(symbol (lib_id "Device:C") (at 396.24 {30.0 + yo} 0) (unit 1)
\t\t(property "Reference" "C_OUT2_{prefix}" (at 398.78 {27.46 + yo} 0) (effects (font (size 1.27 1.27))))
\t\t(property "Value" "22uF_16V" (at 398.78 {32.54 + yo} 0) (effects (font (size 1.27 1.27))))
\t\t(property "Footprint" "Capacitor_SMD:C_1206_3216Metric" (at 71.12 196.85 0) (hide yes) (effects (font (size 1.27 1.27))))
\t\t(pin "1" (uuid "{gen_uuid()}")) (pin "2" (uuid "{gen_uuid()}"))
\t\t(instances (project "Hexapod_Robot_Board" (path "/44f02a75-3141-486c-ae96-cf48718534a3" (reference "C_OUT2_{prefix}") (unit 1))))
\t)
\t(symbol (lib_id "Device:C") (at 408.94 {30.0 + yo} 0) (unit 1)
\t\t(property "Reference" "C_OUT3_{prefix}" (at 411.48 {27.46 + yo} 0) (effects (font (size 1.27 1.27))))
\t\t(property "Value" "100nF" (at 411.48 {32.54 + yo} 0) (effects (font (size 1.27 1.27))))
\t\t(property "Footprint" "Capacitor_SMD:C_0603_1608Metric" (at 71.12 196.85 0) (hide yes) (effects (font (size 1.27 1.27))))
\t\t(pin "1" (uuid "{gen_uuid()}")) (pin "2" (uuid "{gen_uuid()}"))
\t\t(instances (project "Hexapod_Robot_Board" (path "/44f02a75-3141-486c-ae96-cf48718534a3" (reference "C_OUT3_{prefix}") (unit 1))))
\t)
\t(symbol (lib_id "Device:R") (at 374.65 {60.0 + yo} 0) (unit 1)
\t\t(property "Reference" "R_FB1_{prefix}" (at 377.19 {57.46 + yo} 0) (effects (font (size 1.27 1.27))))
\t\t(property "Value" "10k_1%" (at 377.19 {62.54 + yo} 0) (effects (font (size 1.27 1.27))))
\t\t(property "Footprint" "Resistor_SMD:R_0603_1608Metric" (at 71.12 196.85 0) (hide yes) (effects (font (size 1.27 1.27))))
\t\t(pin "1" (uuid "{gen_uuid()}")) (pin "2" (uuid "{gen_uuid()}"))
\t\t(instances (project "Hexapod_Robot_Board" (path "/44f02a75-3141-486c-ae96-cf48718534a3" (reference "R_FB1_{prefix}") (unit 1))))
\t)
\t(symbol (lib_id "Device:R") (at 374.65 {75.0 + yo} 0) (unit 1)
\t\t(property "Reference" "R_FB2_{prefix}" (at 377.19 {72.46 + yo} 0) (effects (font (size 1.27 1.27))))
\t\t(property "Value" "3.16k_1%" (at 377.19 {77.54 + yo} 0) (effects (font (size 1.27 1.27))))
\t\t(property "Footprint" "Resistor_SMD:R_0603_1608Metric" (at 71.12 196.85 0) (hide yes) (effects (font (size 1.27 1.27))))
\t\t(pin "1" (uuid "{gen_uuid()}")) (pin "2" (uuid "{gen_uuid()}"))
\t\t(instances (project "Hexapod_Robot_Board" (path "/44f02a75-3141-486c-ae96-cf48718534a3" (reference "R_FB2_{prefix}") (unit 1))))
\t)
\t(symbol (lib_id "Device:LED") (at 400.05 {60.0 + yo} 0) (unit 1)
\t\t(property "Reference" "LED_{prefix}" (at 402.59 {57.46 + yo} 0) (effects (font (size 1.27 1.27))))
\t\t(property "Value" "Green" (at 402.59 {62.54 + yo} 0) (effects (font (size 1.27 1.27))))
\t\t(property "Footprint" "LED_SMD:LED_0805_2012Metric" (at 71.12 196.85 0) (hide yes) (effects (font (size 1.27 1.27))))
\t\t(pin "1" (uuid "{gen_uuid()}")) (pin "2" (uuid "{gen_uuid()}"))
\t\t(instances (project "Hexapod_Robot_Board" (path "/44f02a75-3141-486c-ae96-cf48718534a3" (reference "LED_{prefix}") (unit 1))))
\t)
\t(symbol (lib_id "Device:R") (at 400.05 {75.0 + yo} 0) (unit 1)
\t\t(property "Reference" "R_LED_{prefix}" (at 402.59 {72.46 + yo} 0) (effects (font (size 1.27 1.27))))
\t\t(property "Value" "1k" (at 402.59 {77.54 + yo} 0) (effects (font (size 1.27 1.27))))
\t\t(property "Footprint" "Resistor_SMD:R_0603_1608Metric" (at 71.12 196.85 0) (hide yes) (effects (font (size 1.27 1.27))))
\t\t(pin "1" (uuid "{gen_uuid()}")) (pin "2" (uuid "{gen_uuid()}"))
\t\t(instances (project "Hexapod_Robot_Board" (path "/44f02a75-3141-486c-ae96-cf48718534a3" (reference "R_LED_{prefix}") (unit 1))))
\t)
\t(symbol (lib_id "power:PWR_FLAG") (at 387.35 {17.0 + yo} 0) (unit 1)
\t\t(property "Reference" "#FLG_{prefix}" (at 387.35 {14.46 + yo} 0) (effects (font (size 1.27 1.27))))
\t\t(property "Value" "{out_net}" (at 387.35 {19.54 + yo} 0) (effects (font (size 1.27 1.27))))
\t\t(pin "1" (uuid "{gen_uuid()}"))
\t\t(instances (project "Hexapod_Robot_Board" (path "/44f02a75-3141-486c-ae96-cf48718534a3" (reference "#FLG_{prefix}") (unit 1))))
\t)
"""
        return circuit_text, sym_instances

    circuit_r, sym_r = make_buck_circuit("R", "SECTION 3A: RIGHT SERVO BUCK (5V/5A, V_SERVO_R)", "V_SERVO_R", "BUCK_SW_R", "BUCK_FB_R", 0.0, "U3_R")
    circuit_l, sym_l = make_buck_circuit("L", "SECTION 3B: LEFT SERVO BUCK (5V/5A, V_SERVO_L)", "V_SERVO_L", "BUCK_SW_L", "BUCK_FB_L", 90.0, "U3_L")

    # Update Section 3 title
    sch = sch.replace('SECTION 3: 5V/3A SERVO BUCK REGULATOR', 'SECTION 3: DUAL 5V/5A SERVO BUCK REGULATORS (10A TOTAL)')
    sch = sch.replace('XL4015 High-Current Buck Converter for 18 Hexapod Servos', 'Dual XL4015 Buck Converters: V_SERVO_R (Right) & V_SERVO_L (Left)')

    # 6. Add Section 8: MPU-6050 Motion Sensor
    # In Section 2 area: X: 162.56 to 274.32, Y: 12.70 to 190.50
    # Battery & Telemetry is in top half (Y: 20 to 90)
    # We place MPU-6050 in bottom half (Y: 105 to 185)
    # U7 at (213.36, 140.00)
    mpu_circuit = f"""
\t(text "SECTION 8: MPU-6050 6-AXIS MOTION TRACKING SENSOR" (at 166.56 102.0 0) (effects (font (size 2.0 2.0) bold (color 0 100 180 1))) (uuid "{gen_uuid()}"))
\t(text "I2C Gyroscope + Accelerometer (0x68) at Center of Rotation" (at 166.56 107.0 0) (effects (font (size 1.27 1.27) italic (color 80 80 80 1))) (uuid "{gen_uuid()}"))

\t(wire (pts (xy 195.58 147.62) (xy 190.0 147.62)) (stroke (width 0) (type default)) (uuid "{gen_uuid()}"))
\t(global_label "GND" (shape input) (at 190.0 147.62 180) (effects (font (size 1.27 1.27))) (uuid "{gen_uuid()}"))

\t(wire (pts (xy 210.82 122.22) (xy 210.82 117.0)) (stroke (width 0) (type default)) (uuid "{gen_uuid()}"))
\t(global_label "+3V3" (shape input) (at 210.82 117.0 90) (effects (font (size 1.27 1.27))) (uuid "{gen_uuid()}"))

\t(wire (pts (xy 215.90 122.22) (xy 215.90 117.0)) (stroke (width 0) (type default)) (uuid "{gen_uuid()}"))
\t(global_label "+3V3" (shape input) (at 215.90 117.0 90) (effects (font (size 1.27 1.27))) (uuid "{gen_uuid()}"))

\t(wire (pts (xy 195.58 137.46) (xy 190.0 137.46)) (stroke (width 0) (type default)) (uuid "{gen_uuid()}"))
\t(global_label "GND" (shape input) (at 190.0 137.46 180) (effects (font (size 1.27 1.27))) (uuid "{gen_uuid()}"))

\t(wire (pts (xy 195.58 145.08) (xy 190.0 145.08)) (stroke (width 0) (type default)) (uuid "{gen_uuid()}"))
\t(global_label "GND" (shape input) (at 190.0 145.08 180) (effects (font (size 1.27 1.27))) (uuid "{gen_uuid()}"))

\t(wire (pts (xy 213.36 157.78) (xy 213.36 162.0)) (stroke (width 0) (type default)) (uuid "{gen_uuid()}"))
\t(global_label "GND" (shape input) (at 213.36 162.0 270) (effects (font (size 1.27 1.27))) (uuid "{gen_uuid()}"))

\t(wire (pts (xy 195.58 134.92) (xy 190.0 134.92)) (stroke (width 0) (type default)) (uuid "{gen_uuid()}"))
\t(global_label "I2C_SCL" (shape input) (at 190.0 134.92 180) (effects (font (size 1.27 1.27))) (uuid "{gen_uuid()}"))

\t(wire (pts (xy 195.58 132.38) (xy 190.0 132.38)) (stroke (width 0) (type default)) (uuid "{gen_uuid()}"))
\t(global_label "I2C_SDA" (shape bidirectional) (at 190.0 132.38 180) (effects (font (size 1.27 1.27))) (uuid "{gen_uuid()}"))

\t(wire (pts (xy 231.14 132.38) (xy 236.0 132.38)) (stroke (width 0) (type default)) (uuid "{gen_uuid()}"))
\t(global_label "MPU_INT" (shape output) (at 236.0 132.38 0) (effects (font (size 1.27 1.27))) (uuid "{gen_uuid()}"))

\t(wire (pts (xy 231.14 147.62) (xy 238.0 147.62)) (stroke (width 0) (type default)) (uuid "{gen_uuid()}"))
\t(wire (pts (xy 238.0 147.62) (xy 238.0 152.0)) (stroke (width 0) (type default)) (uuid "{gen_uuid()}"))
\t(wire (pts (xy 238.0 162.0) (xy 238.0 166.0)) (stroke (width 0) (type default)) (uuid "{gen_uuid()}"))
\t(global_label "GND" (shape input) (at 238.0 166.0 270) (effects (font (size 1.27 1.27))) (uuid "{gen_uuid()}"))

\t(wire (pts (xy 231.14 145.08) (xy 248.0 145.08)) (stroke (width 0) (type default)) (uuid "{gen_uuid()}"))
\t(wire (pts (xy 248.0 145.08) (xy 248.0 152.0)) (stroke (width 0) (type default)) (uuid "{gen_uuid()}"))
\t(wire (pts (xy 248.0 162.0) (xy 248.0 166.0)) (stroke (width 0) (type default)) (uuid "{gen_uuid()}"))
\t(global_label "GND" (shape input) (at 248.0 166.0 270) (effects (font (size 1.27 1.27))) (uuid "{gen_uuid()}"))

\t(wire (pts (xy 258.0 125.0) (xy 258.0 120.0)) (stroke (width 0) (type default)) (uuid "{gen_uuid()}"))
\t(global_label "+3V3" (shape input) (at 258.0 120.0 90) (effects (font (size 1.27 1.27))) (uuid "{gen_uuid()}"))
\t(wire (pts (xy 258.0 135.0) (xy 258.0 140.0)) (stroke (width 0) (type default)) (uuid "{gen_uuid()}"))
\t(global_label "GND" (shape input) (at 258.0 140.0 270) (effects (font (size 1.27 1.27))) (uuid "{gen_uuid()}"))

\t(wire (pts (xy 268.0 125.0) (xy 268.0 120.0)) (stroke (width 0) (type default)) (uuid "{gen_uuid()}"))
\t(global_label "+3V3" (shape input) (at 268.0 120.0 90) (effects (font (size 1.27 1.27))) (uuid "{gen_uuid()}"))
\t(wire (pts (xy 268.0 135.0) (xy 268.0 140.0)) (stroke (width 0) (type default)) (uuid "{gen_uuid()}"))
\t(global_label "GND" (shape input) (at 268.0 140.0 270) (effects (font (size 1.27 1.27))) (uuid "{gen_uuid()}"))
"""
    mpu_sym_instance = f"""
\t(symbol (lib_id "Sensor_Motion:MPU-6050") (at 213.36 140.0 0) (unit 1)
\t\t(property "Reference" "U7" (at 201.93 126.03 0) (effects (font (size 1.27 1.27))))
\t\t(property "Value" "MPU-6050" (at 220.98 155.24 0) (effects (font (size 1.27 1.27))))
\t\t(property "Footprint" "Sensor_Motion:InvenSense_QFN-24_4x4mm_P0.5mm" (at 213.36 160.32 0) (hide yes) (effects (font (size 1.27 1.27))))
\t\t(property "Datasheet" "https://invensense.tdk.com/wp-content/uploads/2015/02/MPU-6000-Datasheet1.pdf" (at 213.36 143.81 0) (hide yes) (effects (font (size 1.27 1.27))))
\t\t(property "Description" "InvenSense 6-Axis Motion Sensor, Gyroscope, Accelerometer, I2C" (at 213.36 140.0 0) (hide yes) (effects (font (size 1.27 1.27))))
\t\t(pin "1" (uuid "{gen_uuid()}")) (pin "2" (uuid "{gen_uuid()}")) (pin "3" (uuid "{gen_uuid()}")) (pin "4" (uuid "{gen_uuid()}")) (pin "5" (uuid "{gen_uuid()}"))
\t\t(pin "6" (uuid "{gen_uuid()}")) (pin "7" (uuid "{gen_uuid()}")) (pin "8" (uuid "{gen_uuid()}")) (pin "9" (uuid "{gen_uuid()}")) (pin "10" (uuid "{gen_uuid()}"))
\t\t(pin "11" (uuid "{gen_uuid()}")) (pin "12" (uuid "{gen_uuid()}")) (pin "13" (uuid "{gen_uuid()}")) (pin "14" (uuid "{gen_uuid()}")) (pin "15" (uuid "{gen_uuid()}"))
\t\t(pin "16" (uuid "{gen_uuid()}")) (pin "17" (uuid "{gen_uuid()}")) (pin "18" (uuid "{gen_uuid()}")) (pin "19" (uuid "{gen_uuid()}")) (pin "20" (uuid "{gen_uuid()}"))
\t\t(pin "21" (uuid "{gen_uuid()}")) (pin "22" (uuid "{gen_uuid()}")) (pin "23" (uuid "{gen_uuid()}")) (pin "24" (uuid "{gen_uuid()}"))
\t\t(instances (project "Hexapod_Robot_Board" (path "/44f02a75-3141-486c-ae96-cf48718534a3" (reference "U7") (unit 1))))
\t)
\t(symbol (lib_id "Device:C") (at 238.0 157.0 0) (unit 1)
\t\t(property "Reference" "C_MPU2" (at 240.54 154.46 0) (effects (font (size 1.27 1.27))))
\t\t(property "Value" "100nF" (at 240.54 159.54 0) (effects (font (size 1.27 1.27))))
\t\t(property "Footprint" "Capacitor_SMD:C_0603_1608Metric" (at 71.12 196.85 0) (hide yes) (effects (font (size 1.27 1.27))))
\t\t(pin "1" (uuid "{gen_uuid()}")) (pin "2" (uuid "{gen_uuid()}"))
\t\t(instances (project "Hexapod_Robot_Board" (path "/44f02a75-3141-486c-ae96-cf48718534a3" (reference "C_MPU2") (unit 1))))
\t)
\t(symbol (lib_id "Device:C") (at 248.0 157.0 0) (unit 1)
\t\t(property "Reference" "C_MPU5" (at 250.54 154.46 0) (effects (font (size 1.27 1.27))))
\t\t(property "Value" "2.2nF" (at 250.54 159.54 0) (effects (font (size 1.27 1.27))))
\t\t(property "Footprint" "Capacitor_SMD:C_0603_1608Metric" (at 71.12 196.85 0) (hide yes) (effects (font (size 1.27 1.27))))
\t\t(pin "1" (uuid "{gen_uuid()}")) (pin "2" (uuid "{gen_uuid()}"))
\t\t(instances (project "Hexapod_Robot_Board" (path "/44f02a75-3141-486c-ae96-cf48718534a3" (reference "C_MPU5") (unit 1))))
\t)
\t(symbol (lib_id "Device:C") (at 258.0 130.0 0) (unit 1)
\t\t(property "Reference" "C_MPU1" (at 260.54 127.46 0) (effects (font (size 1.27 1.27))))
\t\t(property "Value" "100nF" (at 260.54 132.54 0) (effects (font (size 1.27 1.27))))
\t\t(property "Footprint" "Capacitor_SMD:C_0603_1608Metric" (at 71.12 196.85 0) (hide yes) (effects (font (size 1.27 1.27))))
\t\t(pin "1" (uuid "{gen_uuid()}")) (pin "2" (uuid "{gen_uuid()}"))
\t\t(instances (project "Hexapod_Robot_Board" (path "/44f02a75-3141-486c-ae96-cf48718534a3" (reference "C_MPU1") (unit 1))))
\t)
\t(symbol (lib_id "Device:C") (at 268.0 130.0 0) (unit 1)
\t\t(property "Reference" "C_MPU3" (at 270.54 127.46 0) (effects (font (size 1.27 1.27))))
\t\t(property "Value" "100nF" (at 270.54 132.54 0) (effects (font (size 1.27 1.27))))
\t\t(property "Footprint" "Capacitor_SMD:C_0603_1608Metric" (at 71.12 196.85 0) (hide yes) (effects (font (size 1.27 1.27))))
\t\t(pin "1" (uuid "{gen_uuid()}")) (pin "2" (uuid "{gen_uuid()}"))
\t\t(instances (project "Hexapod_Robot_Board" (path "/44f02a75-3141-486c-ae96-cf48718534a3" (reference "C_MPU3") (unit 1))))
\t)
"""

    # Insert circuits into wires and labels section
    # Find a good place to insert wires (before first symbol instance)
    first_sym_pos = sch.find("\n\t(symbol\n\t\t(lib_id")
    sch = sch[:first_sym_pos] + circuit_r + circuit_l + mpu_circuit + sch[first_sym_pos:]

    # Append symbol instances before the final closing paren
    last_paren = sch.rfind(")")
    sch = sch[:last_paren] + sym_r + sym_l + mpu_sym_instance + "\n)\n"

    with open("Hexapod_Robot_Board.kicad_sch", "w", encoding="utf-8") as f:
        f.write(sch)

    print("Successfully wrote updated Hexapod_Robot_Board.kicad_sch!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
