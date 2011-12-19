import re

# partial encoding/decoding support for z-coded values, does not support unicode strings

def reverse_dict(obj):
    return dict((value, key) for key, value in obj.iteritems())

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

decode_map['Z0T'] = '()'
decode_map['Z1H'] = '(# #)'
for i in range(2, 9):
    commas = ',' * (i - 1)
    decode_map['Z{0}T'.format(i)] = '({0})'.format(commas)
    decode_map['Z{0}H'.format(i)] = '(#{0}#)'.format(commas)

encode_map = reverse_dict(decode_map)

def decode_chunk(chunk):
    if len(chunk) > 1 and (chunk[0] == 'Z' or chunk[0] == 'z'):
        return decode_map.get(chunk, chunk[1:])
    else:
        return chunk

def decode(str):
    if str == None:
        return None

    chunks = re.split('(Z[0-9][TH]|[zZ].)', str)
    return ''.join(map(decode_chunk, chunks))

def encode_char(char):
    return encode_map.get(char, char)

def encode(str):
    if str == None:
        return None

    return ''.join(map(encode_char, str))

