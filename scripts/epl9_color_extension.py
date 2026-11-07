"""Explicit, bounded native matrix/six-axis inputs; no photographic calibration claims."""

KEYS=('0x01010078','0x01020078')


def controls(document):
    if type(document) is not dict or set(document)!={'schema','recipes'} or document['schema']!='epl9-native-color-controls-v1':
        raise ValueError('unsupported native color-control schema')
    if type(document['recipes']) is not list or len(document['recipes'])!=2:
        raise ValueError('requires the two accepted recipe slots')
    out={}
    for row in document['recipes']:
        if type(row) is not dict or set(row)!={'watercolor_key','matrix_delta','six_axis'}:
            raise ValueError('unexpected color-control fields')
        key=row['watercolor_key']
        if type(key) is not str or key not in KEYS or key in out: raise ValueError('wrong/duplicate recipe key')
        delta,axes=row['matrix_delta'],row['six_axis']
        if delta is not None and (type(delta) is not list or len(delta)!=9 or
            any(type(v) is not int or not -16<=v<=16 for v in delta) or
            any(sum(delta[i:i+3]) for i in (0,3,6))):
            raise ValueError('matrix deltas must be nine bounded integers with zero row sums')
        if axes is not None and (type(axes) is not list or len(axes)!=12 or
            any(type(v) is not int or not -32768<=v<=32767 for v in axes)):
            raise ValueError('six-axis input requires twelve signed native halfwords')
        out[key]=dict(matrix_delta=tuple(delta) if delta is not None else None,
                      six_axis=tuple(axes) if axes is not None else None)
    return out


def assembly(rows,base):
    lines=[' cmp 1,d3',' beq extended_gold',' jmp extended_portra']
    for key,label,offset in zip(KEYS,('gold','portra'),(0x1c00,0x2c00)):
        row=rows[key]
        lines.extend([f'extended_{label}:',' mov d2,a0'])
        if row['six_axis'] is not None:
            lines.extend([' mov d2,a0',f' mov {base+offset},a1',f' mov {base+offset+12},d0',
                          ' call 0x6079cd40,[a2],4'])
        lines.append(' jmp color_restore')
    return '\n'.join(lines)+'\n'


def matrix_assembly(rows):
    # Inline jump replaces one native CALL. Replay it with the same ABI;
    # qualify the late wrapper's exact call frames before changing its local
    # normalized matrix, BEFORE event 2 and final native packing.
    lines=['film_matrix_hook:',' call 0x6079bedb,[d2,a2,a3],12',
        ' mov (84,sp),d0',' cmp 0x6079fbc6,d0',' beq matrix_outer',' jmp matrix_resume',
        'matrix_outer:',' mov (124,sp),d0',' cmp color_after_native_call,d0',
        ' beq matrix_record',' jmp matrix_resume',
        'matrix_record:',' mov (96,sp),a0',' cmp 0,a0',' bne matrix_controls',' jmp matrix_resume',
        'matrix_controls:',' mov (1512,a0),a1',' mov sp,a0',' add 127,a0',' add 61,a0',
        ' cmp a0,a1',' beq matrix_magic',' jmp matrix_resume',
        'matrix_magic:',' mov (16,a1),d0',' cmp 0x46504c45,d0',' beq matrix_key',' jmp matrix_resume',
        'matrix_key:',' mov (12,a1),d0',' cmp 0x01010078,d0',' beq matrix_gold_gate',
        ' cmp 0x01020078,d0',' beq matrix_portra_gate',' jmp matrix_resume',
        'matrix_gold_gate:',' jmp matrix_gold','matrix_portra_gate:',' jmp matrix_portra']
    for key,label in zip(KEYS,('gold','portra')):
        lines.extend([f'matrix_{label}:',' mov d2,a0'])
        delta=rows[key]['matrix_delta']
        if delta is not None:
            # Preflight every changed cell before any store: overflow bypasses
            # the entire matrix adjustment, preserving the native calibration.
            for i,value in enumerate(delta):
                if not value:continue
                limit=32767-value if value>0 else -32768-value
                branch='ble' if value>0 else 'bge'
                lines.extend([f' movhu ({i*2},a0),d0',' exth d0',f' cmp {limit},d0',
                    f' {branch} matrix_{label}_ok_{i}',f' jmp matrix_resume',
                    f'matrix_{label}_ok_{i}:'])
            for i,value in enumerate(delta):
                if value:lines.extend([f' movhu ({i*2},a0),d0',' exth d0',f' add {value},d0',
                    f' movhu d0,({i*2},a0)'])
        lines.append(' jmp matrix_resume')
    lines.extend(['matrix_resume:',' jmp 0x6079c01c'])
    return '\n'.join(lines)+'\n'


def matrix_result(native,delta):
    if delta is None:return tuple(native)
    result=tuple(a+b for a,b in zip(native,delta))
    return result if all(-32768<=v<=32767 for v in result) else tuple(native)
