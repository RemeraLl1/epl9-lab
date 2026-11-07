"""Opt-in early four-coefficient bias; physical channel labels remain unverified.

Request +1568 is freshly copied from job +10406 before this hook. Native
consumers normalize slots 0/1 by min(2,3), or pack [0,2,3,1]. This is evidence
for a WB gain record, not proof of a physical R/B order or photographic match.
"""
from epl9_color_extension import KEYS


def controls(document):
    if type(document) is not dict or set(document)!={'schema','recipes'} or document['schema']!='epl9-native-wb-controls-v1':
        raise ValueError('unsupported WB control schema')
    if type(document['recipes']) is not list or len(document['recipes'])!=2:
        raise ValueError('requires both accepted slots')
    result={}
    for row in document['recipes']:
        if type(row) is not dict or set(row)!={'watercolor_key','gain_q10'}:
            raise ValueError('unexpected WB control fields')
        key,gains=row['watercolor_key'],row['gain_q10']
        if type(key) is not str or key not in KEYS or key in result:
            raise ValueError('wrong/duplicate WB recipe key')
        if type(gains) is not list or len(gains)!=2 or any(type(v) is not int or not 512<=v<=2048 for v in gains):
            raise ValueError('two native-order Q10 gains in [512,2048] required')
        result[key]=tuple(gains)
    return result


def adjusted(values,gains):
    if not all(values): return tuple(values)
    return tuple(min(65535,(v*g+512)//1024) for v,g in zip(values[:2],gains))+tuple(values[2:])


def assembly(rows):
    # Only D0/D1/D2/A1 are clobbered. Original continuation overwrites all
    # four before reading them. No stack, multiply, divide, MDR/MDRQ or LB
    # operations; the next native setlb establishes the next loop cache.
    lines=['film_wb_entry:',' movhu (14,a2),d0']
    for value in (0x200,0x100,0x40,0x1000):
        lines += [f' cmp {value},d0',' beq wb_key_check']
    lines += [' jmp wb_resume','wb_key_check:',' mov (8,a2),d0',
              ' cmp 7864577,d0',' beq wb_gold_gate',
              ' cmp 7864833,d0',' beq wb_portra_gate',' jmp wb_resume',
              'wb_gold_gate:',' jmp wb_gold','wb_portra_gate:',' jmp wb_portra']
    for key,label in zip(KEYS,('gold','portra')):
        lines.append('wb_'+label+':')
        for i in range(4):
            lines += [f' movhu ({1568+2*i},a2),d0',' cmp 0,d0',f' bne wb_{label}_valid_{i}',
                      ' jmp wb_resume',f'wb_{label}_valid_{i}:']
        for i,gain in enumerate(rows[key]):
            lines += [f' movhu ({1568+2*i},a2),d0',' mov 0,d1']
            # Binary expansion, bounded to 27 bits for accepted inputs.
            for bit in range(gain.bit_length()-1,-1,-1):
                lines.append(' add d1,d1')
                if gain & (1<<bit): lines.append(' add d0,d1')
            lines += [' add 127,d1']*4+[' add 4,d1',' lsr 10,d1',
                      ' cmp 65535,d1',f' ble wb_{label}_store_{i}',' mov 65535,d1',
                      f'wb_{label}_store_{i}:',f' movhu d1,({1568+2*i},a2)']
        lines.append(' jmp wb_resume')
    # Replay clr D0, clr D2, mov 3710,A1 (same values/flags as native).
    lines += ['wb_resume:',' clr d0',' clr d2',' mov 3710,a1',' jmp 0x6074f357']
    return '\n'.join(lines)+'\n'
