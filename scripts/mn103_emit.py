"""Small original MN103 code emitter for this project's reviewed hook source.

It supports only the forms below, not general GNU assembly. Every production
build independently disassembles emitted bytes with the hash-pinned GNU reader.
"""
import re
import struct
from mn103_subset import operands


def mask(text):
    names = text.strip('[]').split(',') if text != '[]' else []
    values = {'d2':128, 'd3':64, 'a2':32, 'a3':16}
    if len(set(names)) != len(names) or any(n not in values for n in names):
        raise ValueError('unsupported save mask')
    return sum(values[n] for n in names)


def reg(text, prefix):
    return int(text[1]) if re.fullmatch(prefix+'[0-3]', text) else None


def memory(text):
    match = re.fullmatch(r'\((?:(-?\d+|0x[0-9a-fA-F]+),)?(a[0-3]|sp)\)', text)
    if not match:
        raise ValueError(f'unsupported memory operand {text}')
    return int(match[1] or '0', 0), match[2]


def number(value, symbols):
    return symbols[value] if value in symbols else int(value, 0)


def encode(op, args, pc, symbols):
    if op in ('beq','bne','ble','bge','bra'):
        delta = number(args[0], symbols)-pc
        if not -128 <= delta <= 127:
            raise ValueError(f'branch out of range at {pc:#x}')
        return bytes([{'beq':0xc8,'bne':0xc9,'ble':0xc3,'bge':0xc2,'bra':0xca}[op],delta & 255])
    if op == 'jmp':
        return b'\xdc'+struct.pack('<i', number(args[0], symbols)-pc)
    if op == 'call':
        frame = int(args[2],0)
        if not 0 <= frame <= 255:
            raise ValueError('call frame out of range')
        return b'\xdd'+struct.pack('<i', number(args[0],symbols)-pc)+bytes([mask(args[1]),frame])
    if op in ('ret','retf'):
        frame = int(args[1],0)
        if not 0 <= frame <= 255:
            raise ValueError('return frame out of range')
        return bytes([0xdf if op == 'ret' else 0xde,mask(args[0]),frame])
    if op == 'nop':
        return b'\xcb'
    if op == 'clr' and reg(args[0],'d') is not None:
        return bytes([4*reg(args[0],'d')])
    if op == 'inc4' and reg(args[0],'a') is not None:
        return bytes([0x50+reg(args[0],'a')])
    if op in ('extb','exth','exthu') and reg(args[0],'d') is not None:
        return bytes([{'extb':0x10,'exth':0x18,'exthu':0x1c}[op]+reg(args[0],'d')])
    if op == 'udfu01':
        value, dest = number(args[0],symbols), reg(args[1],'d')
        if dest is None or not 0 <= value <= 255:
            raise ValueError('emitter supports only unsigned imm8 multiply')
        return bytes([0xf9,0x14+dest,value])
    if op == 'add':
        source, target = reg(args[0],'d'), reg(args[1],'d')
        if source is not None and target is not None:
            return bytes([0xe0+4*source+target])
        dest, address, value = reg(args[1],'d'), reg(args[1],'a'), number(args[0],symbols)
        if args[1]=='sp' and not -128<=value<=127 and -32768<=value<=32767:
            return b'\xfa\xfe'+struct.pack('<h',value)
        if not -128 <= value <= 127:
            raise ValueError('emitter supports only signed imm8 add')
        if args[1] == 'sp': return bytes([0xf8,0xfe,value & 255])
        if dest is None and address is None: raise ValueError('unsupported add destination')
        return bytes([(0x28+dest) if dest is not None else (0x20+address),value & 255])
    if op in ('asl','lsr') and reg(args[1],'d') is not None:
        count=number(args[0],symbols)
        if not 0 <= count < 32: raise ValueError('shift count outside supported subset')
        return bytes([0xf8,(0xc0 if op=='asl' else 0xc4)+reg(args[1],'d'),count])
    if op == 'or' and reg(args[1],'d') is not None:
        return bytes([0xfc,0xe4+reg(args[1],'d')])+struct.pack('<I',number(args[0],symbols) & 0xffffffff)
    if op == 'cmp':
        dest, a = reg(args[1],'d'), reg(args[1],'a')
        source_a = reg(args[0],'a')
        if source_a is not None and a is not None and source_a != a:
            return bytes([0xb0+4*source_a+a])
        if dest is None and a is None:
            raise ValueError('compare destination must be Dn/An')
        return bytes([0xfc,(0xc8+dest) if dest is not None else (0xd8+a)])+struct.pack('<I',number(args[0],symbols) & 0xffffffff)
    if op not in ('mov','movbu','movhu'):
        raise ValueError(f'unsupported instruction {op}')
    src,dest = args
    ds,dd,as_,ad = reg(src,'d'),reg(dest,'d'),reg(src,'a'),reg(dest,'a')
    if op == 'mov' and src == 'sp' and ad is not None:
        return bytes([0x3c+ad])
    if op == 'mov' and (ds is not None or as_ is not None) and (dd is not None or ad is not None):
        if src == dest:
            raise ValueError('self move has no supported compact encoding')
        if ds is not None and dd is not None: return bytes([0x80+4*ds+dd])
        if as_ is not None and ad is not None: return bytes([0x90+4*as_+ad])
        return bytes([0xf1,(0xe0+4*ds+ad) if ds is not None else (0xd0+4*as_+dd)])
    if src.startswith('(') or dest.startswith('('):
        load = src.startswith('(')
        offset, base = memory(src if load else dest)
        d, a = (dd,ad) if load else (ds,as_)
        if d is None and a is None:
            raise ValueError('memory transfer requires a register')
        if base == 'sp':
            if not 0 <= offset <= 255:
                raise ValueError('SP displacement out of range')
            if op == 'mov':
                opcode = (0x58+d if d is not None else 0x5c+a) if load else (0x42+4*d if d is not None else 0x43+4*a)
                return bytes([opcode,offset])
            if not load and d is not None:
                return bytes([0xf8,(0x92 if op=='movbu' else 0x93)+4*d,offset])
            raise ValueError('unsupported SP load')
        b = reg(base,'a')
        if not -32768 <= offset <= 32767:
            raise ValueError('An displacement out of range')
        if op == 'mov':
            opcode = (4*d+b if d is not None else 0x20+4*a+b) if load else (0x10+4*d+b if d is not None else 0x30+4*a+b)
        else:
            if d is None: raise ValueError('byte/halfword transfer requires Dn')
            opcode = (0x40 if op=='movbu' else 0x60)+4*d+b+(0 if load else 0x10)
        return bytes([0xfa,opcode])+struct.pack('<h',offset)
    if op == 'mov' and (dd is not None or ad is not None):
        return bytes([0xfc,(0xcc+dd) if dd is not None else (0xdc+ad)])+struct.pack('<I',number(src,symbols) & 0xffffffff)
    raise ValueError(f'unsupported operands {op} {args}')


def assemble(source, base):
    rows, symbols, pc = [], {}, base
    for original in source.splitlines():
        line = original.split('#',1)[0].strip()
        if not line: continue
        if line.endswith(':'):
            name = line[:-1]
            if not re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*',name) or name in symbols:
                raise ValueError('invalid/duplicate label')
            symbols[name] = pc
            continue
        parts = line.split(None,1)
        op, rest = parts[0], parts[1] if len(parts) == 2 else ''
        args = operands(rest.replace(' ','')) if rest else []
        # Label references in this first pass need only an in-range placeholder.
        provisional = dict(symbols)
        if op in ('beq','bne','ble','bge','bra','jmp','call') and args[0] not in symbols:
            try: int(args[0],0)
            except ValueError: provisional[args[0]] = pc
        raw = encode(op,args,pc,provisional)
        rows.append((pc,op,args,len(raw)))
        pc += len(raw)
    output = bytearray()
    for pc,op,args,length in rows:
        raw = encode(op,args,pc,symbols)
        if len(raw) != length: raise ValueError('instruction size changed')
        output.extend(raw)
    return bytes(output), symbols, rows
