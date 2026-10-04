import os
import re
import uuid

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

def get_pin_map(sym_text, origin_x, origin_y):
    pin_matches = re.finditer(r'\(pin\s+[^\s]+\s+line\s+\(at\s+([\d\.\-]+)\s+([\d\.\-]+)\s+(\d+)\).*?\(name\s+\"([^\"]+)\".*?\(number\s+\"([^\"]+)\"', sym_text, re.DOTALL)
    res = {}
    for m in pin_matches:
        px, py, rot, name, num = float(m.group(1)), float(m.group(2)), int(m.group(3)), m.group(4), m.group(5)
        cx = round((origin_x + px) * 100) / 100
        cy = round((origin_y - py) * 100) / 100
        res[num] = (cx, cy, name, rot)
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

print("Helper functions ready.")
