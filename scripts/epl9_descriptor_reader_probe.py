"""Execute an OEM late gamma-reader fragment against synthetic cache arenas.

No OEM bytes are distributed. This identifies a real later reader, not the
last asynchronous consumer or a safe native release hook.
"""
import argparse
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
import struct
import subprocess

from epl9_descriptor_cache import DescriptorCache, CacheBusy
from epl9_recipe_banks import Bank
from epl9_sd_loader_probe import sample_recipe
from epl9_sd_processing import GAMMA
from epl9_workspace_bridge import BASE, MAIN_SHA
from mn103_subset import Memory, Region, Machine, parse_listing
from mn103_tooling import verify_reader

START, STOP = 0x6074151f, 0x60741647
STACK, OWNER, CONFIG, DEST = 0x20000000, 0x20001000, 0x20002000, 0x20004000


def read_gamma(code, handle, resident, *, replace_source=False):
    """Begin after owner bookkeeping; caller/stack and destination are models."""
    data=bytearray(resident.data)
    # Deliberately distinctive, synthetic values: no photographic recipe claim.
    values=tuple((i*7+123) & 0xffff for i in range(256))
    struct.pack_into('<256H', data, GAMMA, *values)
    if replace_source:
        struct.pack_into('<256H', data, GAMMA, *(65535-x for x in values))
    stack,owner,config,dest=bytearray(128),bytearray(128),bytearray(4096),bytearray(5120)
    struct.pack_into('<I',stack,8,DEST)
    struct.pack_into('<I',stack,16,OWNER)
    stack[24]=1
    struct.pack_into('<I',owner,12,CONFIG)
    pointer=handle.descriptor_address+GAMMA
    struct.pack_into('<3I',config,2596,pointer,pointer,pointer)
    memory=Memory([Region(STACK,stack,True,'synthetic post-bookkeeping stack'),
        Region(OWNER,owner,False,'synthetic owner'),Region(CONFIG,config,False,'retained configuration'),
        Region(DEST,dest,True,'synthetic destination, not physical ISP'),
        Region(handle.descriptor_address,data,False,'resident descriptor')])
    m=Machine(code,memory,dict(sp=STACK))
    result=m.run(START,[STOP],limit=10000)
    assert result['status']=='stop',result
    output=struct.unpack_from('<256I',dest)
    return output, values, result['instructions']


def probe(image,code):
    cache=DescriptorCache(image)
    bank=Bank(1,tuple(replace(sample_recipe(),recipe_id=i+1,name=f'Synthetic {i}') for i in range(31)))
    first=cache.acquire(bank,1)
    second=cache.acquire(bank,2)
    try:
        cache.acquire(bank,3)
    except CacheBusy:
        pinned_refused=True
    else:
        raise AssertionError('pinned slot was replaced')
    output,expected,steps=read_gamma(code,first,cache.read(first))
    assert output==expected
    corrupted,_,_=read_gamma(code,first,cache.read(first),replace_source=True)
    assert corrupted!=expected and corrupted==tuple(65535-x for x in expected)
    # Finishing this fragment is NOT permission to release on a real camera.
    cache.release(first)
    replacement=cache.acquire(bank,3)
    assert replacement.slot==first.slot and replacement.generation>first.generation
    cache.read(second)
    return {'main_sha256':sha256(image).hexdigest(),'fragment_start':hex(START),'fragment_stop':hex(STOP),
        'gamma_dereference':hex(0x60741592),'native_instructions':steps,'samples':len(output),
        'pinned_eviction_refused':pinned_refused,'retained_descriptor_matches':True,
        'premature_overwrite_changes_output':True,'host_generation_advanced':True,
        'scope':'Native late gamma-copy fragment with modeled stack/owner/destination. Not a last-consumer, camera, allocator, SD or Delete test.'}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--main',required=True,type=Path)
    ap.add_argument('--reader',required=True,type=Path)
    ap.add_argument('--output',required=True,type=Path)
    args=ap.parse_args()
    image=args.main.read_bytes()
    if sha256(image).hexdigest()!=MAIN_SHA:raise ValueError('wrong stock main')
    verify_reader(args.reader)
    listing=subprocess.check_output([str(args.reader.resolve()),str(args.main.resolve()),hex(BASE),hex(START-BASE),hex(STOP-BASE)],text=True)
    code=parse_listing(listing,image,BASE)
    result=probe(image,code)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
