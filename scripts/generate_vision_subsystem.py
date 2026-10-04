import os
import uuid
import re

def uid():
    return str(uuid.uuid4())

def extract_lib_symbol(sch_text, sym_name):
    # Find symbol "name"
    pattern = rf'(\(symbol\s+\"{re.escape(sym_name)}\".*?\n\t\t\))'
    m = re.search(pattern, sch_text, re.DOTALL)
    if m:
        return m.group(1)
    return ""

def load_external_symbol(path):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    # Extract from (symbol "..." to the matching end
    # The file has (kicad_symbol_lib ... (symbol "Conn_01x24" ... ))
    m = re.search(r'(\(symbol\s+\"Conn_01x24\".*\n\t\))', content, re.DOTALL)
    if m:
        return m.group(1)
    return ""

print("Helper functions ready")
