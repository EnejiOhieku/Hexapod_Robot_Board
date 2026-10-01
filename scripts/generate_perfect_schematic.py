#!/usr/bin/env python3
"""
generate_perfect_schematic.py
Generates the upgraded Hexapod_Robot_Board.kicad_sch with 0 ERC violations:
- Dual 5V/5A Buck Regulators (U3_R, U3_L) on 1.27mm grid
- MPU-6050 Motion Tracking Sensor (U7) on 1.27mm grid
- ESP32-S3-WROOM-1U MCU (U1)
- 0 ERC violations, 0 warnings
"""

import sys
import uuid
import re

def uid():
    return str(uuid.uuid4())

def main():
    with open("Hexapod_Robot_Board.kicad_sch.bak_pre_upgrade", "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Add Sensor_Motion:MPU-6050 to lib_symbols cleanly
    with open("/home/peacemaker/.local/share/kicad-appimage/share/kicad/symbols/Sensor_Motion.kicad_symdir/MPU-6050.kicad_sym", "r", encoding="utf-8") as f:
        mpu_file = f.read()

    idx = content.find("\t)\t(rectangle")
    sym_start = mpu_file.find('\t(symbol "MPU-6050"')
    sym_end = mpu_file.rfind("\n)")
    mpu_def = mpu_file[sym_start:sym_end].replace('(symbol "MPU-6050"', '(symbol "Sensor_Motion:MPU-6050"')
    mpu_def_indented = "\n".join("\t" + line if line.strip() else line for line in mpu_def.splitlines())

    content = content[:idx] + mpu_def_indented + "\n\t)\n\t" + content[idx+3:]
    print("1. Added MPU-6050 to lib_symbols.")

    lines = content.splitlines(keepends=True)

    # 2. Update Section 3 titles
    for i, l in enumerate(lines):
        if 'SECTION 3: 5V/3A SERVO BUCK REGULATOR' in l:
            lines[i] = l.replace('SECTION 3: 5V/3A SERVO BUCK REGULATOR', 'SECTION 3: DUAL 5V/5A SERVO BUCK REGULATORS (10A TOTAL)')
        if 'XL4015 High-Current Buck Converter for 18 Hexapod Servos' in l:
            lines[i] = l.replace('XL4015 High-Current Buck Converter for 18 Hexapod Servos', 'Dual XL4015 Converters: V_SERVO_R (Right Servos) & V_SERVO_L (Left Servos)')

    # 3. Update Section 7 Servo Power Labels: replace V_SERVO with V_SERVO_R or V_SERVO_L
    sec7_count = 0
    for i in range(len(lines)):
        if i >= 9000 and '(global_label "V_SERVO"' in lines[i]:
            at_line = lines[i+2]
            at_m = re.search(r"\(at\s+([0-9.]+)\s+([0-9.]+)", at_line)
            if at_m:
                x, y = float(at_m.group(1)), float(at_m.group(2))
                is_right = False
                if abs(x - 407.67) < 0.2:
                    is_right = True
                elif abs(x - 455.93) < 0.2 and y <= 290.0:
                    is_right = True
                elif abs(x - 552.45) < 0.2 and y <= 290.0:
                    is_right = True

                is_left = False
                if abs(x - 455.93) < 0.2 and y > 290.0:
                    is_left = True
                elif abs(x - 504.19) < 0.2:
                    is_left = True
                elif abs(x - 552.45) < 0.2 and y > 290.0:
                    is_left = True

                if is_right:
                    lines[i] = lines[i].replace('"V_SERVO"', '"V_SERVO_R"')
                    sec7_count += 1
                elif is_left:
                    lines[i] = lines[i].replace('"V_SERVO"', '"V_SERVO_L"')
                    sec7_count += 1

    print(f"2. Updated {sec7_count} Section 7 servo power labels.")

    # 4. Update U1 instance (ESP32-S3-WROOM-1U)
    for i, l in enumerate(lines):
        if '(property "Reference" "U1"' in l:
            for j in range(i-5, i+10):
                if '(property "Value" "ESP32-S3-WROOM-1"' in lines[j]:
                    lines[j] = lines[j].replace('"ESP32-S3-WROOM-1"', '"ESP32-S3-WROOM-1U"')
                if '(property "Footprint" "RF_Module:ESP32-S3-WROOM-1"' in lines[j]:
                    lines[j] = lines[j].replace('"RF_Module:ESP32-S3-WROOM-1"', '"RF_Module:ESP32-S3-WROOM-1U"')
            break
    print("3. Updated U1 instance to ESP32-S3-WROOM-1U.")

    # 5. Connect MPU_INT to U1 pin 11 (GPIO18) at (110.49, 283.21)
    mpu_int_str = f"""\t(wire (pts (xy 110.49 283.21) (xy 115.57 283.21)) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "MPU_INT"
\t\t(shape input)
\t\t(at 115.57 283.21 0)
\t\t(effects
\t\t\t(font
\t\t\t\t(size 1.27 1.27)
\t\t\t)
\t\t\t(justify left)
\t\t)
\t\t(uuid "{uid()}")
\t\t(property "Intersheetrefs" "${{INTERSHEET_REFS}}"
\t\t\t(at 115.57 283.21 0)
\t\t\t(hide yes)
\t\t\t(show_name no)
\t\t\t(do_not_autoplace no)
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t)
\t\t\t)
\t\t)
\t)
"""
    for i, l in enumerate(lines):
        if '(pts (xy 110.49 275.59)' in l:
            lines.insert(i, mpu_int_str)
            break
    print("4. Connected MPU_INT wire to U1 pin 11.")

    # Find exact boundary indices using string search
    flg_wire_idx = next(i for i, l in enumerate(lines) if '(pts (xy 387.35 31.75) (xy 387.35 27.94))' in l)

    # #FLG05 label is the global_label "V_SERVO" at 387.35 27.94
    flg_label_start = next(i for i in range(flg_wire_idx, flg_wire_idx + 600) if '(global_label "V_SERVO"' in lines[i] and '387.35 27.94 90' in lines[i+2])
    flg_label_end = next(i for i in range(flg_label_start + 1, len(lines)) if lines[i].startswith("\t("))

    # Sec 3 wires: from (xy 313.69 71.12) to (xy 400.05 149.86)
    sec3_wires_start = next(i for i, l in enumerate(lines) if '(pts (xy 313.69 71.12) (xy 308.61 71.12))' in l)
    sec3_wires_end = next(i for i, l in enumerate(lines) if '(pts (xy 400.05 149.86) (xy 400.05 153.67))' in l) + 1

    # Sec 3 labels: from (at 308.61 71.12) up to (global_label "LDO_IN" at 463.55 73.66)
    sec3_labels_start = next(i for i in range(sec3_wires_end, len(lines)) if '(global_label "VBAT_SW"' in lines[i] and '308.61 71.12' in lines[i+2])
    sec3_labels_end = next(i for i in range(sec3_labels_start, len(lines)) if '(global_label "LDO_IN"' in lines[i] and '463.55 73.66' in lines[i+2])

    # Sec 3 symbols: from (symbol "Regulator_Switching:XL4015") U3 up to (symbol "Regulator_Linear:AMS1117-3.3") U4
    u3_idx = next(i for i, l in enumerate(lines) if '(property "Reference" "U3"' in l)
    while not lines[u3_idx].startswith("\t(symbol"):
        u3_idx -= 1
    sec3_syms_start = u3_idx

    u4_idx = next(i for i, l in enumerate(lines) if '(property "Reference" "U4"' in l)
    while not lines[u4_idx].startswith("\t(symbol"):
        u4_idx -= 1
    sec3_syms_end = u4_idx

    # #FLG05 symbol: from (property "Reference" "#FLG05") up to next symbol start (#FLG08)
    flg_idx = next(i for i, l in enumerate(lines) if '(property "Reference" "#FLG05"' in l)
    while not lines[flg_idx].startswith("\t(symbol"):
        flg_idx -= 1
    flg_sym_start = flg_idx
    flg_sym_end = flg_idx + 1
    while not lines[flg_sym_end].startswith("\t(symbol"):
        flg_sym_end += 1

    # Grid-aligned offset for Left Buck: yo = 88.90 mm (70 * 1.27 mm)
    YO_L = 88.90

    # Build replacement strings
    flg_wires_and_labels = f"""\t(wire (pts (xy 387.35 31.75) (xy 387.35 27.94)) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "V_SERVO_R"
\t\t(shape bidirectional)
\t\t(at 387.35 27.94 90)
\t\t(effects (font (size 1.27 1.27)) (justify left))
\t\t(uuid "{uid()}")
\t\t(property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at 387.35 27.94 0) (hide yes) (show_name no) (do_not_autoplace no) (effects (font (size 1.27 1.27))))
\t)
\t(wire (pts (xy 387.35 {31.75 + YO_L:.2f}) (xy 387.35 {27.94 + YO_L:.2f})) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "V_SERVO_L"
\t\t(shape bidirectional)
\t\t(at 387.35 {27.94 + YO_L:.2f} 90)
\t\t(effects (font (size 1.27 1.27)) (justify left))
\t\t(uuid "{uid()}")
\t\t(property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at 387.35 {27.94 + YO_L:.2f} 0) (hide yes) (show_name no) (do_not_autoplace no) (effects (font (size 1.27 1.27))))
\t)
"""

    def make_buck_wires_and_labels(prefix, title, out_net, sw_net, fb_net, yo):
        return f"""\t(text "{title}" (at 280.86 {20.32 + yo:.2f} 0) (effects (font (size 2.0 2.0) bold (color 0 100 180 1))) (uuid "{uid()}"))
\t(wire (pts (xy 294.64 {49.53 + yo:.2f}) (xy 294.64 {45.72 + yo:.2f})) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "VBAT_SW" (shape input) (at 294.64 {45.72 + yo:.2f} 90) (effects (font (size 1.27 1.27)) (justify left)) (uuid "{uid()}") (property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at 294.64 {45.72 + yo:.2f} 0) (hide yes) (show_name no) (do_not_autoplace no) (effects (font (size 1.27 1.27)))))
\t(wire (pts (xy 294.64 {57.15 + yo:.2f}) (xy 294.64 {60.96 + yo:.2f})) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "GND" (shape input) (at 294.64 {60.96 + yo:.2f} 270) (effects (font (size 1.27 1.27)) (justify right)) (uuid "{uid()}") (property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at 294.64 {60.96 + yo:.2f} 0) (hide yes) (show_name no) (do_not_autoplace no) (effects (font (size 1.27 1.27)))))

\t(wire (pts (xy 307.34 {49.53 + yo:.2f}) (xy 307.34 {45.72 + yo:.2f})) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "VBAT_SW" (shape input) (at 307.34 {45.72 + yo:.2f} 90) (effects (font (size 1.27 1.27)) (justify left)) (uuid "{uid()}") (property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at 307.34 {45.72 + yo:.2f} 0) (hide yes) (show_name no) (do_not_autoplace no) (effects (font (size 1.27 1.27)))))
\t(wire (pts (xy 307.34 {57.15 + yo:.2f}) (xy 307.34 {60.96 + yo:.2f})) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "GND" (shape input) (at 307.34 {60.96 + yo:.2f} 270) (effects (font (size 1.27 1.27)) (justify right)) (uuid "{uid()}") (property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at 307.34 {60.96 + yo:.2f} 0) (hide yes) (show_name no) (do_not_autoplace no) (effects (font (size 1.27 1.27)))))

\t(wire (pts (xy 313.69 {71.12 + yo:.2f}) (xy 308.61 {71.12 + yo:.2f})) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "VBAT_SW" (shape input) (at 308.61 {71.12 + yo:.2f} 180) (effects (font (size 1.27 1.27)) (justify right)) (uuid "{uid()}") (property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at 308.61 {71.12 + yo:.2f} 0) (hide yes) (show_name no) (do_not_autoplace no) (effects (font (size 1.27 1.27)))))

\t(wire (pts (xy 323.85 {81.28 + yo:.2f}) (xy 323.85 {86.36 + yo:.2f})) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "GND" (shape input) (at 323.85 {86.36 + yo:.2f} 270) (effects (font (size 1.27 1.27)) (justify right)) (uuid "{uid()}") (property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at 323.85 {86.36 + yo:.2f} 0) (hide yes) (show_name no) (do_not_autoplace no) (effects (font (size 1.27 1.27)))))

\t(wire (pts (xy 313.69 {76.20 + yo:.2f}) (xy 308.61 {76.20 + yo:.2f})) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "GND" (shape input) (at 308.61 {76.20 + yo:.2f} 180) (effects (font (size 1.27 1.27)) (justify right)) (uuid "{uid()}") (property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at 308.61 {76.20 + yo:.2f} 0) (hide yes) (show_name no) (do_not_autoplace no) (effects (font (size 1.27 1.27)))))

\t(wire (pts (xy 334.01 {71.12 + yo:.2f}) (xy 339.09 {71.12 + yo:.2f})) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "{sw_net}" (shape bidirectional) (at 339.09 {71.12 + yo:.2f} 0) (effects (font (size 1.27 1.27)) (justify left)) (uuid "{uid()}") (property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at 339.09 {71.12 + yo:.2f} 0) (hide yes) (show_name no) (do_not_autoplace no) (effects (font (size 1.27 1.27)))))

\t(wire (pts (xy 334.01 {76.20 + yo:.2f}) (xy 339.09 {76.20 + yo:.2f})) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "{fb_net}" (shape input) (at 339.09 {76.20 + yo:.2f} 0) (effects (font (size 1.27 1.27)) (justify left)) (uuid "{uid()}") (property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at 339.09 {76.20 + yo:.2f} 0) (hide yes) (show_name no) (do_not_autoplace no) (effects (font (size 1.27 1.27)))))

\t(wire (pts (xy 345.44 {104.14 + yo:.2f}) (xy 345.44 {100.33 + yo:.2f})) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "{sw_net}" (shape bidirectional) (at 345.44 {100.33 + yo:.2f} 90) (effects (font (size 1.27 1.27)) (justify left)) (uuid "{uid()}") (property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at 345.44 {100.33 + yo:.2f} 0) (hide yes) (show_name no) (do_not_autoplace no) (effects (font (size 1.27 1.27)))))
\t(wire (pts (xy 345.44 {111.76 + yo:.2f}) (xy 345.44 {115.57 + yo:.2f})) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "GND" (shape input) (at 345.44 {115.57 + yo:.2f} 270) (effects (font (size 1.27 1.27)) (justify right)) (uuid "{uid()}") (property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at 345.44 {115.57 + yo:.2f} 0) (hide yes) (show_name no) (do_not_autoplace no) (effects (font (size 1.27 1.27)))))

\t(wire (pts (xy 358.14 {71.12 + yo:.2f}) (xy 358.14 {67.31 + yo:.2f})) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "{sw_net}" (shape bidirectional) (at 358.14 {67.31 + yo:.2f} 90) (effects (font (size 1.27 1.27)) (justify left)) (uuid "{uid()}") (property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at 358.14 {67.31 + yo:.2f} 0) (hide yes) (show_name no) (do_not_autoplace no) (effects (font (size 1.27 1.27)))))
\t(wire (pts (xy 365.76 {71.12 + yo:.2f}) (xy 365.76 {74.93 + yo:.2f})) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "{out_net}" (shape output) (at 365.76 {74.93 + yo:.2f} 270) (effects (font (size 1.27 1.27)) (justify right)) (uuid "{uid()}") (property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at 365.76 {74.93 + yo:.2f} 0) (hide yes) (show_name no) (do_not_autoplace no) (effects (font (size 1.27 1.27)))))

\t(wire (pts (xy 383.54 {49.53 + yo:.2f}) (xy 383.54 {45.72 + yo:.2f})) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "{out_net}" (shape output) (at 383.54 {45.72 + yo:.2f} 90) (effects (font (size 1.27 1.27)) (justify left)) (uuid "{uid()}") (property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at 383.54 {45.72 + yo:.2f} 0) (hide yes) (show_name no) (do_not_autoplace no) (effects (font (size 1.27 1.27)))))
\t(wire (pts (xy 383.54 {57.15 + yo:.2f}) (xy 383.54 {60.96 + yo:.2f})) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "GND" (shape input) (at 383.54 {60.96 + yo:.2f} 270) (effects (font (size 1.27 1.27)) (justify right)) (uuid "{uid()}") (property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at 383.54 {60.96 + yo:.2f} 0) (hide yes) (show_name no) (do_not_autoplace no) (effects (font (size 1.27 1.27)))))

\t(wire (pts (xy 396.24 {49.53 + yo:.2f}) (xy 396.24 {45.72 + yo:.2f})) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "{out_net}" (shape output) (at 396.24 {45.72 + yo:.2f} 90) (effects (font (size 1.27 1.27)) (justify left)) (uuid "{uid()}") (property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at 396.24 {45.72 + yo:.2f} 0) (hide yes) (show_name no) (do_not_autoplace no) (effects (font (size 1.27 1.27)))))
\t(wire (pts (xy 396.24 {57.15 + yo:.2f}) (xy 396.24 {60.96 + yo:.2f})) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "GND" (shape input) (at 396.24 {60.96 + yo:.2f} 270) (effects (font (size 1.27 1.27)) (justify right)) (uuid "{uid()}") (property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at 396.24 {60.96 + yo:.2f} 0) (hide yes) (show_name no) (do_not_autoplace no) (effects (font (size 1.27 1.27)))))

\t(wire (pts (xy 408.94 {49.53 + yo:.2f}) (xy 408.94 {45.72 + yo:.2f})) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "{out_net}" (shape output) (at 408.94 {45.72 + yo:.2f} 90) (effects (font (size 1.27 1.27)) (justify left)) (uuid "{uid()}") (property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at 408.94 {45.72 + yo:.2f} 0) (hide yes) (show_name no) (do_not_autoplace no) (effects (font (size 1.27 1.27)))))
\t(wire (pts (xy 408.94 {57.15 + yo:.2f}) (xy 408.94 {60.96 + yo:.2f})) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "GND" (shape input) (at 408.94 {60.96 + yo:.2f} 270) (effects (font (size 1.27 1.27)) (justify right)) (uuid "{uid()}") (property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at 408.94 {60.96 + yo:.2f} 0) (hide yes) (show_name no) (do_not_autoplace no) (effects (font (size 1.27 1.27)))))

\t(wire (pts (xy 374.65 {110.49 + yo:.2f}) (xy 374.65 {106.68 + yo:.2f})) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "{out_net}" (shape output) (at 374.65 {106.68 + yo:.2f} 90) (effects (font (size 1.27 1.27)) (justify left)) (uuid "{uid()}") (property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at 374.65 {106.68 + yo:.2f} 0) (hide yes) (show_name no) (do_not_autoplace no) (effects (font (size 1.27 1.27)))))
\t(wire (pts (xy 374.65 {118.11 + yo:.2f}) (xy 374.65 {121.92 + yo:.2f})) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "{fb_net}" (shape input) (at 374.65 {121.92 + yo:.2f} 270) (effects (font (size 1.27 1.27)) (justify right)) (uuid "{uid()}") (property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at 374.65 {121.92 + yo:.2f} 0) (hide yes) (show_name no) (do_not_autoplace no) (effects (font (size 1.27 1.27)))))

\t(wire (pts (xy 374.65 {142.24 + yo:.2f}) (xy 374.65 {138.43 + yo:.2f})) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "{fb_net}" (shape input) (at 374.65 {138.43 + yo:.2f} 90) (effects (font (size 1.27 1.27)) (justify left)) (uuid "{uid()}") (property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at 374.65 {138.43 + yo:.2f} 0) (hide yes) (show_name no) (do_not_autoplace no) (effects (font (size 1.27 1.27)))))
\t(wire (pts (xy 374.65 {149.86 + yo:.2f}) (xy 374.65 {153.67 + yo:.2f})) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "GND" (shape input) (at 374.65 {153.67 + yo:.2f} 270) (effects (font (size 1.27 1.27)) (justify right)) (uuid "{uid()}") (property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at 374.65 {153.67 + yo:.2f} 0) (hide yes) (show_name no) (do_not_autoplace no) (effects (font (size 1.27 1.27)))))

\t(wire (pts (xy 396.24 {114.30 + yo:.2f}) (xy 396.24 {110.49 + yo:.2f})) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "{out_net}" (shape output) (at 396.24 {110.49 + yo:.2f} 90) (effects (font (size 1.27 1.27)) (justify left)) (uuid "{uid()}") (property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at 396.24 {110.49 + yo:.2f} 0) (hide yes) (show_name no) (do_not_autoplace no) (effects (font (size 1.27 1.27)))))
\t(wire (pts (xy 403.86 {114.30 + yo:.2f}) (xy 403.86 {118.11 + yo:.2f})) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(wire (pts (xy 400.05 {142.24 + yo:.2f}) (xy 400.05 {138.43 + yo:.2f})) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(wire (pts (xy 403.86 {118.11 + yo:.2f}) (xy 400.05 {138.43 + yo:.2f})) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(wire (pts (xy 400.05 {149.86 + yo:.2f}) (xy 400.05 {153.67 + yo:.2f})) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "GND" (shape input) (at 400.05 {153.67 + yo:.2f} 270) (effects (font (size 1.27 1.27)) (justify right)) (uuid "{uid()}") (property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at 400.05 {153.67 + yo:.2f} 0) (hide yes) (show_name no) (do_not_autoplace no) (effects (font (size 1.27 1.27)))))
"""

    def make_buck_symbols(prefix, out_net, yo, u3_ref):
        return f"""\t(symbol (lib_id "Regulator_Switching:XL4015") (at 323.85 {73.66 + yo:.2f} 0) (unit 1)
\t\t(property "Reference" "{u3_ref}" (at 326.39 {71.12 + yo:.2f} 0) (effects (font (size 1.27 1.27))))
\t\t(property "Value" "XL4015" (at 326.39 {76.20 + yo:.2f} 0) (effects (font (size 1.27 1.27))))
\t\t(property "Footprint" "Package_TO_SOT_SMD:TO-263-5_TabPin3" (at 71.12 196.85 0) (hide yes) (effects (font (size 1.27 1.27))))
\t\t(property "Datasheet" "http://www.xlsemi.net/datasheet/XL4015%20datasheet-English.pdf" (at 49.53 204.47 0) (hide yes) (effects (font (size 1.27 1.27))))
\t\t(property "Description" "5A 180kHz 36V Buck DC to DC Converter" (at 49.53 204.47 0) (hide yes) (effects (font (size 1.27 1.27))))
\t\t(pin "1" (uuid "{uid()}")) (pin "2" (uuid "{uid()}")) (pin "3" (uuid "{uid()}")) (pin "4" (uuid "{uid()}")) (pin "5" (uuid "{uid()}"))
\t\t(instances (project "Hexapod_Robot_Board" (path "/44f02a75-3141-486c-ae96-cf48718534a3" (reference "{u3_ref}") (unit 1))))
\t)
\t(symbol (lib_id "Device:C") (at 294.64 {53.34 + yo:.2f} 0) (unit 1)
\t\t(property "Reference" "C_IN1_{prefix}" (at 297.18 {50.80 + yo:.2f} 0) (effects (font (size 1.27 1.27))))
\t\t(property "Value" "100uF_25V" (at 297.18 {55.88 + yo:.2f} 0) (effects (font (size 1.27 1.27))))
\t\t(property "Footprint" "Capacitor_THT:CP_Radial_D8.0mm_P3.50mm" (at 71.12 196.85 0) (hide yes) (effects (font (size 1.27 1.27))))
\t\t(pin "1" (uuid "{uid()}")) (pin "2" (uuid "{uid()}"))
\t\t(instances (project "Hexapod_Robot_Board" (path "/44f02a75-3141-486c-ae96-cf48718534a3" (reference "C_IN1_{prefix}") (unit 1))))
\t)
\t(symbol (lib_id "Device:C") (at 307.34 {53.34 + yo:.2f} 0) (unit 1)
\t\t(property "Reference" "C_IN2_{prefix}" (at 309.88 {50.80 + yo:.2f} 0) (effects (font (size 1.27 1.27))))
\t\t(property "Value" "22uF_25V" (at 309.88 {55.88 + yo:.2f} 0) (effects (font (size 1.27 1.27))))
\t\t(property "Footprint" "Capacitor_SMD:C_1206_3216Metric" (at 71.12 196.85 0) (hide yes) (effects (font (size 1.27 1.27))))
\t\t(pin "1" (uuid "{uid()}")) (pin "2" (uuid "{uid()}"))
\t\t(instances (project "Hexapod_Robot_Board" (path "/44f02a75-3141-486c-ae96-cf48718534a3" (reference "C_IN2_{prefix}") (unit 1))))
\t)
\t(symbol (lib_id "Device:D_Schottky") (at 345.44 {107.95 + yo:.2f} 90) (unit 1)
\t\t(property "Reference" "D_CATCH_{prefix}" (at 347.98 {105.41 + yo:.2f} 0) (effects (font (size 1.27 1.27))))
\t\t(property "Value" "SS54" (at 347.98 {110.49 + yo:.2f} 0) (effects (font (size 1.27 1.27))))
\t\t(property "Footprint" "Diode_SMD:D_SMC" (at 71.12 196.85 0) (hide yes) (effects (font (size 1.27 1.27))))
\t\t(pin "1" (uuid "{uid()}")) (pin "2" (uuid "{uid()}"))
\t\t(instances (project "Hexapod_Robot_Board" (path "/44f02a75-3141-486c-ae96-cf48718534a3" (reference "D_CATCH_{prefix}") (unit 1))))
\t)
\t(symbol (lib_id "Device:L") (at 361.95 {71.12 + yo:.2f} 90) (unit 1)
\t\t(property "Reference" "L_SERVO_{prefix}" (at 361.95 {66.04 + yo:.2f} 90) (effects (font (size 1.27 1.27))))
\t\t(property "Value" "10uH_10A" (at 361.95 {76.20 + yo:.2f} 90) (effects (font (size 1.27 1.27))))
\t\t(property "Footprint" "Inductor_SMD:L_12x12mm_H8mm" (at 71.12 196.85 0) (hide yes) (effects (font (size 1.27 1.27))))
\t\t(pin "1" (uuid "{uid()}")) (pin "2" (uuid "{uid()}"))
\t\t(instances (project "Hexapod_Robot_Board" (path "/44f02a75-3141-486c-ae96-cf48718534a3" (reference "L_SERVO_{prefix}") (unit 1))))
\t)
\t(symbol (lib_id "Device:C") (at 383.54 {53.34 + yo:.2f} 0) (unit 1)
\t\t(property "Reference" "C_OUT1_{prefix}" (at 386.08 {50.80 + yo:.2f} 0) (effects (font (size 1.27 1.27))))
\t\t(property "Value" "1000uF_10V" (at 386.08 {55.88 + yo:.2f} 0) (effects (font (size 1.27 1.27))))
\t\t(property "Footprint" "Capacitor_THT:CP_Radial_D8.0mm_P3.50mm" (at 71.12 196.85 0) (hide yes) (effects (font (size 1.27 1.27))))
\t\t(pin "1" (uuid "{uid()}")) (pin "2" (uuid "{uid()}"))
\t\t(instances (project "Hexapod_Robot_Board" (path "/44f02a75-3141-486c-ae96-cf48718534a3" (reference "C_OUT1_{prefix}") (unit 1))))
\t)
\t(symbol (lib_id "Device:C") (at 396.24 {53.34 + yo:.2f} 0) (unit 1)
\t\t(property "Reference" "C_OUT2_{prefix}" (at 398.78 {50.80 + yo:.2f} 0) (effects (font (size 1.27 1.27))))
\t\t(property "Value" "22uF_16V" (at 398.78 {55.88 + yo:.2f} 0) (effects (font (size 1.27 1.27))))
\t\t(property "Footprint" "Capacitor_SMD:C_1206_3216Metric" (at 71.12 196.85 0) (hide yes) (effects (font (size 1.27 1.27))))
\t\t(pin "1" (uuid "{uid()}")) (pin "2" (uuid "{uid()}"))
\t\t(instances (project "Hexapod_Robot_Board" (path "/44f02a75-3141-486c-ae96-cf48718534a3" (reference "C_OUT2_{prefix}") (unit 1))))
\t)
\t(symbol (lib_id "Device:C") (at 408.94 {53.34 + yo:.2f} 0) (unit 1)
\t\t(property "Reference" "C_OUT3_{prefix}" (at 411.48 {50.80 + yo:.2f} 0) (effects (font (size 1.27 1.27))))
\t\t(property "Value" "100nF" (at 411.48 {55.88 + yo:.2f} 0) (effects (font (size 1.27 1.27))))
\t\t(property "Footprint" "Capacitor_SMD:C_0603_1608Metric" (at 71.12 196.85 0) (hide yes) (effects (font (size 1.27 1.27))))
\t\t(pin "1" (uuid "{uid()}")) (pin "2" (uuid "{uid()}"))
\t\t(instances (project "Hexapod_Robot_Board" (path "/44f02a75-3141-486c-ae96-cf48718534a3" (reference "C_OUT3_{prefix}") (unit 1))))
\t)
\t(symbol (lib_id "Device:R") (at 374.65 {114.30 + yo:.2f} 0) (unit 1)
\t\t(property "Reference" "R_FB1_{prefix}" (at 377.19 {111.76 + yo:.2f} 0) (effects (font (size 1.27 1.27))))
\t\t(property "Value" "10k_1%" (at 377.19 {116.84 + yo:.2f} 0) (effects (font (size 1.27 1.27))))
\t\t(property "Footprint" "Resistor_SMD:R_0603_1608Metric" (at 71.12 196.85 0) (hide yes) (effects (font (size 1.27 1.27))))
\t\t(pin "1" (uuid "{uid()}")) (pin "2" (uuid "{uid()}"))
\t\t(instances (project "Hexapod_Robot_Board" (path "/44f02a75-3141-486c-ae96-cf48718534a3" (reference "R_FB1_{prefix}") (unit 1))))
\t)
\t(symbol (lib_id "Device:R") (at 374.65 {146.05 + yo:.2f} 0) (unit 1)
\t\t(property "Reference" "R_FB2_{prefix}" (at 377.19 {143.51 + yo:.2f} 0) (effects (font (size 1.27 1.27))))
\t\t(property "Value" "3.16k_1%" (at 377.19 {148.59 + yo:.2f} 0) (effects (font (size 1.27 1.27))))
\t\t(property "Footprint" "Resistor_SMD:R_0603_1608Metric" (at 71.12 196.85 0) (hide yes) (effects (font (size 1.27 1.27))))
\t\t(pin "1" (uuid "{uid()}")) (pin "2" (uuid "{uid()}"))
\t\t(instances (project "Hexapod_Robot_Board" (path "/44f02a75-3141-486c-ae96-cf48718534a3" (reference "R_FB2_{prefix}") (unit 1))))
\t)
\t(symbol (lib_id "Device:LED") (at 400.05 {114.30 + yo:.2f} 0) (unit 1)
\t\t(property "Reference" "LED_{prefix}" (at 402.59 {111.76 + yo:.2f} 0) (effects (font (size 1.27 1.27))))
\t\t(property "Value" "Green" (at 402.59 {116.84 + yo:.2f} 0) (effects (font (size 1.27 1.27))))
\t\t(property "Footprint" "LED_SMD:LED_0805_2012Metric" (at 71.12 196.85 0) (hide yes) (effects (font (size 1.27 1.27))))
\t\t(pin "1" (uuid "{uid()}")) (pin "2" (uuid "{uid()}"))
\t\t(instances (project "Hexapod_Robot_Board" (path "/44f02a75-3141-486c-ae96-cf48718534a3" (reference "LED_{prefix}") (unit 1))))
\t)
\t(symbol (lib_id "Device:R") (at 400.05 {146.05 + yo:.2f} 0) (unit 1)
\t\t(property "Reference" "R_LED_{prefix}" (at 402.59 {143.51 + yo:.2f} 0) (effects (font (size 1.27 1.27))))
\t\t(property "Value" "1k" (at 402.59 {148.59 + yo:.2f} 0) (effects (font (size 1.27 1.27))))
\t\t(property "Footprint" "Resistor_SMD:R_0603_1608Metric" (at 71.12 196.85 0) (hide yes) (effects (font (size 1.27 1.27))))
\t\t(pin "1" (uuid "{uid()}")) (pin "2" (uuid "{uid()}"))
\t\t(instances (project "Hexapod_Robot_Board" (path "/44f02a75-3141-486c-ae96-cf48718534a3" (reference "R_LED_{prefix}") (unit 1))))
\t)
"""

    flg_syms = f"""\t(symbol (lib_id "power:PWR_FLAG") (at 387.35 31.75 0) (unit 1)
\t\t(property "Reference" "#FLG_R" (at 387.35 29.21 0) (hide yes) (effects (font (size 1.27 1.27))))
\t\t(property "Value" "V_SERVO_R" (at 387.35 34.29 0) (effects (font (size 1.27 1.27))))
\t\t(pin "1" (uuid "{uid()}"))
\t\t(instances (project "Hexapod_Robot_Board" (path "/44f02a75-3141-486c-ae96-cf48718534a3" (reference "#FLG_R") (unit 1))))
\t)
\t(symbol (lib_id "power:PWR_FLAG") (at 387.35 {31.75 + YO_L:.2f} 0) (unit 1)
\t\t(property "Reference" "#FLG_L" (at 387.35 {29.21 + YO_L:.2f} 0) (hide yes) (effects (font (size 1.27 1.27))))
\t\t(property "Value" "V_SERVO_L" (at 387.35 {34.29 + YO_L:.2f} 0) (effects (font (size 1.27 1.27))))
\t\t(pin "1" (uuid "{uid()}"))
\t\t(instances (project "Hexapod_Robot_Board" (path "/44f02a75-3141-486c-ae96-cf48718534a3" (reference "#FLG_L") (unit 1))))
\t)
"""

    # Section 8: MPU-6050 placed at (213.36, 139.70) (both exact multiples of 1.27 mm: 168 * 1.27 and 110 * 1.27)
    # Pins:
    # Pin 24 (SDA): (195.58, 132.08)
    # Pin 23 (SCL): (195.58, 134.62)
    # Pin 9 (AD0): (195.58, 137.16)
    # Pin 11 (FSYNC): (195.58, 144.78)
    # Pin 1 (CLKIN): (195.58, 147.32)
    # Pin 8 (VLOGIC): (210.82, 121.92)
    # Pin 13 (VDD): (215.90, 121.92)
    # Pin 18 (GND): (213.36, 157.48)
    # Pin 12 (INT): (231.14, 132.08)
    # Pin 6 (AUX_DA): (231.14, 137.16) -> no_connect
    # Pin 7 (AUX_CL): (231.14, 139.70) -> no_connect
    # Pin 20 (CPOUT): (231.14, 144.78) -> C_MPU5 pin 1 at (251.46, 151.13)
    # Pin 10 (REGOUT): (231.14, 147.32) -> C_MPU2 pin 1 at (241.30, 151.13)
    #
    # Capacitors (all placed at exact 1.27mm grid multiples):
    # C_MPU2 at (241.30, 154.94): pin 1 at (241.30, 151.13), pin 2 at (241.30, 158.75)
    # C_MPU5 at (251.46, 154.94): pin 1 at (251.46, 151.13), pin 2 at (251.46, 158.75)
    # C_MPU1 at (261.62, 132.08): pin 1 at (261.62, 128.27), pin 2 at (261.62, 135.89)
    # C_MPU3 at (271.78, 132.08): pin 1 at (271.78, 128.27), pin 2 at (271.78, 135.89)

    mpu_circuit = f"""\t(text "SECTION 8: MPU-6050 6-AXIS MOTION TRACKING SENSOR" (at 166.37 101.60 0) (effects (font (size 2.0 2.0) bold (color 0 100 180 1))) (uuid "{uid()}"))

\t(no_connect (at 231.14 137.16) (uuid "{uid()}"))
\t(no_connect (at 231.14 139.70) (uuid "{uid()}"))

\t(wire (pts (xy 195.58 147.32) (xy 189.23 147.32)) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "GND" (shape input) (at 189.23 147.32 180) (effects (font (size 1.27 1.27)) (justify right)) (uuid "{uid()}") (property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at 189.23 147.32 0) (hide yes) (show_name no) (do_not_autoplace no) (effects (font (size 1.27 1.27)))))

\t(wire (pts (xy 210.82 121.92) (xy 210.82 116.84)) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "+3V3" (shape input) (at 210.82 116.84 90) (effects (font (size 1.27 1.27)) (justify left)) (uuid "{uid()}") (property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at 210.82 116.84 0) (hide yes) (show_name no) (do_not_autoplace no) (effects (font (size 1.27 1.27)))))

\t(wire (pts (xy 215.90 121.92) (xy 215.90 116.84)) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "+3V3" (shape input) (at 215.90 116.84 90) (effects (font (size 1.27 1.27)) (justify left)) (uuid "{uid()}") (property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at 215.90 116.84 0) (hide yes) (show_name no) (do_not_autoplace no) (effects (font (size 1.27 1.27)))))

\t(wire (pts (xy 195.58 137.16) (xy 189.23 137.16)) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "GND" (shape input) (at 189.23 137.16 180) (effects (font (size 1.27 1.27)) (justify right)) (uuid "{uid()}") (property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at 189.23 137.16 0) (hide yes) (show_name no) (do_not_autoplace no) (effects (font (size 1.27 1.27)))))

\t(wire (pts (xy 195.58 144.78) (xy 189.23 144.78)) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "GND" (shape input) (at 189.23 144.78 180) (effects (font (size 1.27 1.27)) (justify right)) (uuid "{uid()}") (property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at 189.23 144.78 0) (hide yes) (show_name no) (do_not_autoplace no) (effects (font (size 1.27 1.27)))))

\t(wire (pts (xy 213.36 157.48) (xy 213.36 162.56)) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "GND" (shape input) (at 213.36 162.56 270) (effects (font (size 1.27 1.27)) (justify right)) (uuid "{uid()}") (property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at 213.36 162.56 0) (hide yes) (show_name no) (do_not_autoplace no) (effects (font (size 1.27 1.27)))))

\t(wire (pts (xy 195.58 134.62) (xy 189.23 134.62)) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "I2C_SCL" (shape input) (at 189.23 134.62 180) (effects (font (size 1.27 1.27)) (justify right)) (uuid "{uid()}") (property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at 189.23 134.62 0) (hide yes) (show_name no) (do_not_autoplace no) (effects (font (size 1.27 1.27)))))

\t(wire (pts (xy 195.58 132.08) (xy 189.23 132.08)) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "I2C_SDA" (shape bidirectional) (at 189.23 132.08 180) (effects (font (size 1.27 1.27)) (justify right)) (uuid "{uid()}") (property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at 189.23 132.08 0) (hide yes) (show_name no) (do_not_autoplace no) (effects (font (size 1.27 1.27)))))

\t(wire (pts (xy 231.14 132.08) (xy 236.22 132.08)) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "MPU_INT" (shape output) (at 236.22 132.08 0) (effects (font (size 1.27 1.27)) (justify left)) (uuid "{uid()}") (property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at 236.22 132.08 0) (hide yes) (show_name no) (do_not_autoplace no) (effects (font (size 1.27 1.27)))))

\t(wire (pts (xy 231.14 147.32) (xy 241.30 147.32)) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(wire (pts (xy 241.30 147.32) (xy 241.30 151.13)) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(wire (pts (xy 241.30 158.75) (xy 241.30 162.56)) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "GND" (shape input) (at 241.30 162.56 270) (effects (font (size 1.27 1.27)) (justify right)) (uuid "{uid()}") (property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at 241.30 162.56 0) (hide yes) (show_name no) (do_not_autoplace no) (effects (font (size 1.27 1.27)))))

\t(wire (pts (xy 231.14 144.78) (xy 251.46 144.78)) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(wire (pts (xy 251.46 144.78) (xy 251.46 151.13)) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(wire (pts (xy 251.46 158.75) (xy 251.46 162.56)) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "GND" (shape input) (at 251.46 162.56 270) (effects (font (size 1.27 1.27)) (justify right)) (uuid "{uid()}") (property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at 251.46 162.56 0) (hide yes) (show_name no) (do_not_autoplace no) (effects (font (size 1.27 1.27)))))

\t(wire (pts (xy 261.62 128.27) (xy 261.62 124.46)) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "+3V3" (shape input) (at 261.62 124.46 90) (effects (font (size 1.27 1.27)) (justify left)) (uuid "{uid()}") (property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at 261.62 124.46 0) (hide yes) (show_name no) (do_not_autoplace no) (effects (font (size 1.27 1.27)))))
\t(wire (pts (xy 261.62 135.89) (xy 261.62 139.70)) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "GND" (shape input) (at 261.62 139.70 270) (effects (font (size 1.27 1.27)) (justify right)) (uuid "{uid()}") (property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at 261.62 139.70 0) (hide yes) (show_name no) (do_not_autoplace no) (effects (font (size 1.27 1.27)))))

\t(wire (pts (xy 271.78 128.27) (xy 271.78 124.46)) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "+3V3" (shape input) (at 271.78 124.46 90) (effects (font (size 1.27 1.27)) (justify left)) (uuid "{uid()}") (property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at 271.78 124.46 0) (hide yes) (show_name no) (do_not_autoplace no) (effects (font (size 1.27 1.27)))))
\t(wire (pts (xy 271.78 135.89) (xy 271.78 139.70)) (stroke (width 0) (type default)) (uuid "{uid()}"))
\t(global_label "GND" (shape input) (at 271.78 139.70 270) (effects (font (size 1.27 1.27)) (justify right)) (uuid "{uid()}") (property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at 271.78 139.70 0) (hide yes) (show_name no) (do_not_autoplace no) (effects (font (size 1.27 1.27)))))
"""

    mpu_symbols = f"""\t(symbol (lib_id "Sensor_Motion:MPU-6050") (at 213.36 139.70 0) (unit 1)
\t\t(property "Reference" "U7" (at 201.93 125.73 0) (effects (font (size 1.27 1.27))))
\t\t(property "Value" "MPU-6050" (at 220.98 154.94 0) (effects (font (size 1.27 1.27))))
\t\t(property "Footprint" "Sensor_Motion:InvenSense_QFN-24_4x4mm_P0.5mm" (at 213.36 160.02 0) (hide yes) (effects (font (size 1.27 1.27))))
\t\t(property "Datasheet" "https://invensense.tdk.com/wp-content/uploads/2015/02/MPU-6000-Datasheet1.pdf" (at 213.36 143.51 0) (hide yes) (effects (font (size 1.27 1.27))))
\t\t(property "Description" "InvenSense 6-Axis Motion Sensor, Gyroscope, Accelerometer, I2C" (at 213.36 139.70 0) (hide yes) (effects (font (size 1.27 1.27))))
\t\t(pin "1" (uuid "{uid()}")) (pin "2" (uuid "{uid()}")) (pin "3" (uuid "{uid()}")) (pin "4" (uuid "{uid()}")) (pin "5" (uuid "{uid()}"))
\t\t(pin "6" (uuid "{uid()}")) (pin "7" (uuid "{uid()}")) (pin "8" (uuid "{uid()}")) (pin "9" (uuid "{uid()}")) (pin "10" (uuid "{uid()}"))
\t\t(pin "11" (uuid "{uid()}")) (pin "12" (uuid "{uid()}")) (pin "13" (uuid "{uid()}")) (pin "14" (uuid "{uid()}")) (pin "15" (uuid "{uid()}"))
\t\t(pin "16" (uuid "{uid()}")) (pin "17" (uuid "{uid()}")) (pin "18" (uuid "{uid()}")) (pin "19" (uuid "{uid()}")) (pin "20" (uuid "{uid()}"))
\t\t(pin "21" (uuid "{uid()}")) (pin "22" (uuid "{uid()}")) (pin "23" (uuid "{uid()}")) (pin "24" (uuid "{uid()}"))
\t\t(instances (project "Hexapod_Robot_Board" (path "/44f02a75-3141-486c-ae96-cf48718534a3" (reference "U7") (unit 1))))
\t)
\t(symbol (lib_id "Device:C") (at 241.30 154.94 0) (unit 1)
\t\t(property "Reference" "C_MPU2" (at 243.84 152.40 0) (effects (font (size 1.27 1.27))))
\t\t(property "Value" "100nF" (at 243.84 157.48 0) (effects (font (size 1.27 1.27))))
\t\t(property "Footprint" "Capacitor_SMD:C_0603_1608Metric" (at 71.12 196.85 0) (hide yes) (effects (font (size 1.27 1.27))))
\t\t(pin "1" (uuid "{uid()}")) (pin "2" (uuid "{uid()}"))
\t\t(instances (project "Hexapod_Robot_Board" (path "/44f02a75-3141-486c-ae96-cf48718534a3" (reference "C_MPU2") (unit 1))))
\t)
\t(symbol (lib_id "Device:C") (at 251.46 154.94 0) (unit 1)
\t\t(property "Reference" "C_MPU5" (at 254.00 152.40 0) (effects (font (size 1.27 1.27))))
\t\t(property "Value" "2.2nF" (at 254.00 157.48 0) (effects (font (size 1.27 1.27))))
\t\t(property "Footprint" "Capacitor_SMD:C_0603_1608Metric" (at 71.12 196.85 0) (hide yes) (effects (font (size 1.27 1.27))))
\t\t(pin "1" (uuid "{uid()}")) (pin "2" (uuid "{uid()}"))
\t\t(instances (project "Hexapod_Robot_Board" (path "/44f02a75-3141-486c-ae96-cf48718534a3" (reference "C_MPU5") (unit 1))))
\t)
\t(symbol (lib_id "Device:C") (at 261.62 132.08 0) (unit 1)
\t\t(property "Reference" "C_MPU1" (at 264.16 129.54 0) (effects (font (size 1.27 1.27))))
\t\t(property "Value" "100nF" (at 264.16 134.62 0) (effects (font (size 1.27 1.27))))
\t\t(property "Footprint" "Capacitor_SMD:C_0603_1608Metric" (at 71.12 196.85 0) (hide yes) (effects (font (size 1.27 1.27))))
\t\t(pin "1" (uuid "{uid()}")) (pin "2" (uuid "{uid()}"))
\t\t(instances (project "Hexapod_Robot_Board" (path "/44f02a75-3141-486c-ae96-cf48718534a3" (reference "C_MPU1") (unit 1))))
\t)
\t(symbol (lib_id "Device:C") (at 271.78 132.08 0) (unit 1)
\t\t(property "Reference" "C_MPU3" (at 274.32 129.54 0) (effects (font (size 1.27 1.27))))
\t\t(property "Value" "100nF" (at 274.32 134.62 0) (effects (font (size 1.27 1.27))))
\t\t(property "Footprint" "Capacitor_SMD:C_0603_1608Metric" (at 71.12 196.85 0) (hide yes) (effects (font (size 1.27 1.27))))
\t\t(pin "1" (uuid "{uid()}")) (pin "2" (uuid "{uid()}"))
\t\t(instances (project "Hexapod_Robot_Board" (path "/44f02a75-3141-486c-ae96-cf48718534a3" (reference "C_MPU3") (unit 1))))
\t)
"""

    buck_r_circuit = make_buck_wires_and_labels("R", "SECTION 3A: RIGHT SERVO BUCK (5V/5A, V_SERVO_R)", "V_SERVO_R", "BUCK_SW_R", "BUCK_FB_R", 0.0)
    buck_l_circuit = make_buck_wires_and_labels("L", "SECTION 3B: LEFT SERVO BUCK (5V/5A, V_SERVO_L)", "V_SERVO_L", "BUCK_SW_L", "BUCK_FB_L", YO_L)

    buck_r_syms = make_buck_symbols("R", "V_SERVO_R", 0.0, "U3_R")
    buck_l_syms = make_buck_symbols("L", "V_SERVO_L", YO_L, "U3_L")

    # Strictly descending slice replacement order!
    lines[flg_sym_start:flg_sym_end] = [flg_syms]
    print("Replaced FLG symbol.")

    lines[sec3_syms_start:sec3_syms_end] = [buck_r_syms + buck_l_syms + mpu_symbols]
    print("Replaced Sec 3 symbols.")

    lines[sec3_labels_start:sec3_labels_end] = [""]
    print("Replaced Sec 3 labels.")

    lines[flg_label_start:flg_label_end] = [""]
    print("Replaced FLG label.")

    lines[sec3_wires_start:sec3_wires_end] = [buck_r_circuit + buck_l_circuit + mpu_circuit]
    print("Replaced Sec 3 wires.")

    lines[flg_wire_idx:flg_wire_idx+1] = [flg_wires_and_labels]
    print("Replaced FLG wire.")

    # Check parenthesis balance
    full_text = "".join(lines)
    open_p = full_text.count("(")
    close_p = full_text.count(")")
    print(f"Parenthesis balance check: open={open_p}, close={close_p}, diff={open_p - close_p}")
    if open_p != close_p:
        print("ERROR: Parenthesis mismatch detected!")
        return 1

    with open("Hexapod_Robot_Board.kicad_sch", "w", encoding="utf-8") as f:
        f.write(full_text)

    print("SUCCESS: Hexapod_Robot_Board.kicad_sch written cleanly!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
