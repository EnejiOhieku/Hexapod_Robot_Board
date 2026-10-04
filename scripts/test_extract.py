with open('Hexapod_Robot_Board.kicad_sch', 'r', encoding='utf-8') as f:
    text = f.read()

def get_full_symbol(text, sym_name):
    target = f'(symbol "{sym_name}"'
    idx = text.find(target)
    if idx == -1: return ''
    depth = 0
    for i in range(idx, len(text)):
        if text[i] == '(':
            depth += 1
        elif text[i] == ')':
            depth -= 1
            if depth == 0:
                return text[idx:i+1]
    return ''

symbols_to_test = [
    'RF_Module:ESP32-S3-WROOM-1',
    'Connector:USB_C_Receptacle_USB2.0_16P',
    'Regulator_Linear:AMS1117-3.3',
    'Device:R',
    'Device:C',
    'Device:L',
    'Device:LED',
    'Switch:SW_Push',
    'power:PWR_FLAG',
    'Connector_Generic:Conn_01x04'
]

for s in symbols_to_test:
    res = get_full_symbol(text, s)
    print(f'Symbol {s:<40}: {len(res):>6} bytes, ends valid: {res.endswith(")")}')
