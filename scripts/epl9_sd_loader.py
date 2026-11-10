"""Original standalone MN103 SD loader emitter; no firmware patch is created.

The extra encodings are local to this experiment. The shared emitter and
interpreter are unchanged. GNU decoding must verify every emitted instruction.
"""
from pathlib import Path
from string import Template
import struct

from epl9_workspace_bridge import ROOT
from mn103_emit import encode as base_encode, number, reg, memory
from mn103_subset import operands

MODULE_BASE = 0x69000000  # Synthetic, no camera placement claim.
TEMPLATE = ROOT/'firmware_src/epl9_sd_loader.s.in'
INVERSE = {'beq':'bne','bne':'beq','blt':'bge','bge':'blt','ble':'bgt','bgt':'ble',
           'bhi':'bls','bls':'bhi','bcs':'bcc','bcc':'bcs'}
BRANCH = {'blt':0xc0,'bgt':0xc1,'bhi':0xc5,'bls':0xc7,'bcs':0xc4,'bcc':0xc6}


def encode(op,args,pc,symbols):
    if op in BRANCH:
        delta=number(args[0],symbols)-pc
        if not -128<=delta<=127: raise ValueError('branch span')
        return bytes([BRANCH[op],delta & 255])
    if op=='cmp' and reg(args[0],'d') is not None and reg(args[1],'d') is not None:
        return bytes([0xa0+4*reg(args[0],'d')+reg(args[1],'d')])
    if op=='movhu' and args[0].startswith('(') and reg(args[1],'d') is not None:
        offset,base=memory(args[0])
        if base=='sp':
            if not 0<=offset<=255: raise ValueError('SP load displacement')
            return bytes([0xf8,0xbc+reg(args[1],'d'),offset])
    if op in ('xor','and'):
        dest,source=reg(args[1],'d'),reg(args[0],'d')
        if dest is None: raise ValueError('only Dn bitwise operands supported')
        if source is not None:
            return bytes([0xf2,(0x20 if op=='xor' else 0)+4*source+dest])
        return bytes([0xfc,(0xe8 if op=='xor' else 0xe0)+dest])+struct.pack('<I',number(args[0],symbols)&0xffffffff)
    return base_encode(op,args,pc,symbols)


def assemble(source,base=MODULE_BASE):
    # Always expand conditions to a local inverse branch + a full-range jump.
    lines=[]
    for i,line in enumerate(source.splitlines()):
        line=line.split('#',1)[0].strip()
        if not line: continue
        parts=line.split(None,1)
        if parts[0] in INVERSE:
            label=f'_skip_{i}'
            lines += [f'{INVERSE[parts[0]]} {label}',f'jmp {parts[1]}',label+':']
        else: lines.append(line)
    symbols,rows,pc={},[],base
    for line in lines:
        if line.endswith(':'):
            if line[:-1] in symbols: raise ValueError('duplicate label')
            symbols[line[:-1]]=pc
            continue
        fields=line.split(None,1)
        op=fields[0];args=operands(fields[1]) if len(fields)>1 else []
        provisional=dict(symbols)
        if op in set(INVERSE)|{'jmp','call'}:
            try: int(args[0],0)
            except ValueError: provisional.setdefault(args[0],pc)
        raw=encode(op,args,pc,provisional)
        rows.append((pc,op,args,len(raw)));pc+=len(raw)
    data=b''.join(encode(op,args,pc,symbols) for pc,op,args,_ in rows)
    return data,symbols,rows


def validator_source():
    lines=['sd_validate:',' mov a0,a2']
    for offset,value in ((0,0x30523945),(4,0x00400000),(8,(1101<<16)|1330),
                         (12,660),(24,1),(28,0)):
        lines += [f' mov ({offset},a2),d0',f' cmp {value},d0',' bne check_bad']
    lines += [' mov (20,a2),d0',' cmp 0,d0',' beq check_bad',
              ' mov a2,a1',' mov -1,d0',' mov 0,d2','crc_byte:',
              ' movbu (0,a1),d1',' cmp 16,d2',' blt crc_mix',' cmp 19,d2',
              ' bgt crc_mix',' mov 0,d1','crc_mix:',' xor d1,d0',' mov 8,d3',
              'crc_bit:',' mov d0,d1',' and 1,d1',' lsr 1,d0',' cmp 0,d1',
              ' beq crc_next',' xor 0xedb88320,d0','crc_next:',' add -1,d3',
              ' cmp 0,d3',' bne crc_bit',' add 1,a1',' add 1,d2',' cmp 660,d2',
              ' bne crc_byte',' xor 0xffffffff,d0',' mov (16,a2),d1',
              ' cmp d1,d0',' bne check_bad',
              ' mov a2,a1',' add 32,a1',' mov 0,d2',' mov 0,d3','name_byte:',
              ' movbu (0,a1),d0',' cmp 0,d0',' bne name_nonzero',' cmp 0,d2',
              ' beq check_bad',' mov 1,d3',' jmp name_next','name_nonzero:',
              ' cmp 0,d3',' bne check_bad',' cmp 31,d2',' beq check_bad',
              ' cmp 32,d0',' blt check_bad',' cmp 126,d0',' bgt check_bad',
              ' cmp 64,d0',' beq check_bad','name_next:',' add 1,a1',' add 1,d2',
              ' cmp 32,d2',' bne name_byte',' cmp 1,d3',' bne check_bad',
              ' mov a2,a1',' add 64,a1',' mov 12,d2','hsl_row:']
    for offset,limit in ((0,1000),(2,240),(4,100)):
        lines += [f' movhu ({offset},a1),d0',' exth d0',f' cmp {-limit},d0',
                  ' blt check_bad',f' cmp {limit},d0',' bgt check_bad']
    lines += [' add 6,a1',' add -1,d2',' cmp 0,d2',' bne hsl_row']
    for offset,lo,hi in ((136,-2,2),(138,-7,7),(140,-7,7),(142,-7,7),(144,512,2048),(146,512,2048)):
        lines += [f' movhu ({offset},a2),d0']
        if lo<0: lines.append(' exth d0')
        lines += [f' cmp {lo},d0',' blt check_bad',f' cmp {hi},d0',' bgt check_bad']
    lines += [' mov a2,a1',' add 127,a1',' add 21,a1',' mov 256,d2',' mov 0,d3',
              'gamma_value:',' movhu (0,a1),d0',' cmp 4095,d0',' bhi check_bad',
              ' cmp d3,d0',' bcs check_bad',' mov d0,d3',' add 2,a1',' add -1,d2',
              ' cmp 0,d2',' bne gamma_value',' mov 0,d0',' jmp check_return',
              'check_bad:',' mov 1,d0','check_return:',' ret [d2,d3,a2,a3],24']
    return '\n'.join(lines)+'\n'


def build():
    source=Template(TEMPLATE.read_text()).substitute(VALIDATOR=validator_source())
    data,symbols,rows=assemble(source)
    return dict(source=source,data=data,symbols=symbols,rows=rows,base=MODULE_BASE)
