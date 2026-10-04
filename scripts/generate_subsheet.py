import os
import uuid

def uid():
    return str(uuid.uuid4())

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
    return f"""\t(wire (pts (xy {x1} {y1}) (xy {x2} {y2})) (stroke (width 0) (type default)) (uuid "{uid()}"))"""

def label(name, x, y, rot=0, shape="input"):
    return f"""\t(hierarchical_label "{name}" (shape {shape}) (at {x} {y} {rot}) (effects (font (size 1.27 1.27)) (justify left)) (uuid "{uid()}"))"""

def glabel(name, x, y, rot=0):
    return f"""\t(label "{name}" (at {x} {y} {rot}) (effects (font (size 1.27 1.27)) (justify left)) (uuid "{uid()}"))"""

print("Subsheet primitives ready")
