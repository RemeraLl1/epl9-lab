"""Build a separate manager-tail/two-slot native prototype; no packaging.

Fallback records are supplied locally, never copied into public source.
"""
from string import Template

from epl9_workspace_bridge import ROOT,BASE
from epl9_sd_loader import assemble,validator_source,TEMPLATE as LOADER_TEMPLATE,MODULE_BASE
from epl9_sd_recipes import unpack_recipe
from mn103_emit import encode

TEMPLATE=ROOT/'firmware_src/epl9_sd_state.s.in'
ROOT_ADDRESS=0x6239790c
OBJECT_BYTES=288
TAIL=192
MAGIC=0x31534445  # EDS1
CONTEXTS=(216,248)
OFFSETS=dict(PATH0=0x1000,PATH1=0x1040,MODE=0x1080,FALLBACK0=0x1200,FALLBACK1=0x1500)


def build(defaults):
    if len(defaults)!=2: raise ValueError('requires exactly two test-slot defaults')
    for raw in defaults: unpack_recipe(raw)
    # Keep the first standalone loader's entry/validator intact in its source.
    loader=LOADER_TEMPLATE.read_text().split('\n# Test-only adapter',1)[0]
    values={k:str(MODULE_BASE+v) for k,v in OFFSETS.items()}
    values.update(MAGIC=str(MAGIC),LOADER=loader,VALIDATOR=validator_source())
    source=Template(TEMPLATE.read_text()).substitute(values)
    code,symbols,rows=assemble(source)
    if len(code)>0x1000: raise ValueError('code overlaps prototype data')
    data=bytearray(0x1800);data[:len(code)]=code
    for key,path in (('PATH0',b'C:\\EPL9MOD\\SLOT01.RCP\0'),('PATH1',b'C:\\EPL9MOD\\SLOT02.RCP\0'),('MODE',b'r\0')):
        at=OFFSETS[key];data[at:at+len(path)]=path
    for key,raw in zip(('FALLBACK0','FALLBACK1'),defaults):
        at=OFFSETS[key];data[at:at+len(raw)]=raw
    return dict(source=source,data=bytes(data),symbols=symbols,rows=rows,base=MODULE_BASE,
                code_bytes=len(code),defaults=tuple(defaults),constants={k:MODULE_BASE+v for k,v in OFFSETS.items()})


def overlay(image,module):
    specs=[(0x60ae1a6f,'2cb400',bytes.fromhex('2c2001')),
           (0x60ae1a8a,'cdf5fdf020',encode('jmp',['sd_ctor_hook'],0x60ae1a8a,module['symbols'])),
           (0x60ae1c6e,'cd05042008',encode('jmp',['sd_event_hook'],0x60ae1c6e,module['symbols']))]
    patched=bytearray(image);rows=[]
    for pc,expected,after in specs:
        before=bytes.fromhex(expected)
        if image[pc-BASE:pc-BASE+len(before)]!=before or len(after)!=len(before):
            raise ValueError('state prototype overlay byte mismatch')
        patched[pc-BASE:pc-BASE+len(before)]=after
        rows.append(dict(address=pc,before=before.hex(),after=after.hex()))
    return bytes(patched),rows
