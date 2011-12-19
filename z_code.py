import re

decode_map = {'ZL': '('
             ,'ZR': ')' 
             ,'ZM': '['
             ,'ZN': ']'
             ,'ZC': ':'
             ,'ZZ': 'Z'
             ,'zz': 'z'
             ,'za': '&'
             ,'zb': '|'
             ,'zc': '^'
             ,'zd': '$'
             ,'ze': '='
             ,'zg': '>'
             ,'zh': '#'
             ,'zi': '.'
             ,'zl': '<'
             ,'zm': '-'
             ,'zn': '!'
             ,'zp': '+'
             ,'zq': '\''
             ,'zr': '\\'
             ,'zs': '/'
             ,'zt': '*'
             ,'zu': '_'
             ,'zv': '%'}

def decode_chunk(chunk):
    if len(chunk) == 2 and (chunk[0] == 'Z' or chunk[0] == 'z'):
        return decode_map.get(chunk, chunk[1])
    else:
        return chunk

def decode(str):
    if str == None:
        return None

    chunks = re.split('([zZ].)', str)
    return ''.join(map(decode_chunk, chunks))

