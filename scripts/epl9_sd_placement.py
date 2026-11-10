"""Rebuild the separate SD prototypes at in-image, early-load addresses.

The frozen synthetic builders and both Watercolor generations are inputs only.
No encoded installation package is created.
"""
import re
import struct
from epl9_workspace_bridge import BASE
from epl9_sd_loader import assemble
from epl9_sd_state import build as state_build
from epl9_sd_processing import build as consumer_build, descriptor, overlay

STATE_BASE=0x604a5000
CONSUMER_BASE=0x604a8100
SPANS=((STATE_BASE,6144),(CONSUMER_BASE,16384))
V3_SPAN=(0x604a1300,0x604a4f00)


def relocate_constants(source,mapping):
    # Replace only complete numeric operands, never labels/partial numbers.
    return re.sub(r'(?<![\w])\d+(?![\w])',lambda m:str(mapping.get(int(m[0]),int(m[0]))),source)


def check_spans(image,spans=SPANS):
    previous=0
    for at,size in sorted(spans):
        if at%256 or size<=0 or at<previous or not 0x60410000<=at<at+size<=0x604b0800:
            raise ValueError('SD placement escapes aligned early-load bounds or overlaps')
        if at<V3_SPAN[1] and V3_SPAN[0]<at+size:raise ValueError('SD placement overlaps frozen v3 slot')
        if image[at-BASE:at-BASE+size]!=b'\xff'*size:raise ValueError('SD placement is not exact stock FF padding')
        previous=at+size


def build(image,defaults):
    check_spans(image)
    synthetic=state_build(defaults)
    constants={k:STATE_BASE+(v-synthetic['base']) for k,v in synthetic['constants'].items()}
    source=relocate_constants(synthetic['source'],dict(zip(synthetic['constants'].values(),constants.values())))
    raw,symbols,rows=assemble(source,STATE_BASE)
    if len(raw)>4096:raise ValueError('state relocation overlaps paths')
    data=bytearray(synthetic['data']);data[:4096]=bytes(4096);data[:len(raw)]=raw
    state=dict(synthetic,source=source,data=bytes(data),symbols=symbols,rows=rows,
               base=STATE_BASE,code_bytes=len(raw),constants=constants)
    intermediate=consumer_build(image,state)
    offset=CONSUMER_BASE-intermediate['base']
    mapping={intermediate['base']+n:intermediate['base']+n+offset for n in (0x2000,0x3000,0x2000+3252,0x3000+3252)}
    source=relocate_constants(intermediate['source'],mapping)
    raw,symbols,rows=assemble(source,CONSUMER_BASE)
    if len(raw)>8192:raise ValueError('consumer relocation overlaps defaults')
    data=bytearray(intermediate['data']);data[:8192]=bytes(8192);data[:len(raw)]=raw
    for i in range(2):
        at=0x2000+4096*i
        data[at:at+4096]=descriptor(image,defaults[i],CONSUMER_BASE+at,i+1,constants[f'FALLBACK{i}'])
    consumer=dict(intermediate,source=source,data=bytes(data),symbols=symbols,rows=rows,
                  base=CONSUMER_BASE,code_bytes=len(raw))
    patched,patches=overlay(image,state,consumer)
    patched=bytearray(patched);reference=bytearray(image)
    for m in (state,consumer):
        at=m['base']-BASE
        patched[at:at+len(m['data'])]=m['data']
        reference[at:at+len(m['data'])]=m['data']
    return state,consumer,bytes(patched),bytes(reference),patches
