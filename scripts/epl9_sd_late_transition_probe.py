"""Join existing private-COLOR SD prototype to native late gamma/HSL reader.

Synthetic embedded recipes and null HLS root; no SD/file/manager lifecycle is
modeled. Target hooks rebuild a private context, without changing owner +20.
"""
import argparse
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
import struct
import subprocess
from types import SimpleNamespace
from epl9_workspace_bridge import BASE, MAIN_SHA
from epl9_sd_state import build as build_state
from epl9_sd_processing import build, BASE_ADDRESS
from epl9_sd_processing_probe import decode, frame, OUT
from epl9_sd_loader_probe import sample_recipe, STACK
from epl9_sd_recipes import pack_recipe
from epl9_film_handoff import WINDOWS
from mn103_subset import Memory, Region, Machine, parse_listing
from mn103_emit import encode
from mn103_tooling import verify_reader


def late(result,code):
    stack,owner,dest=0x25000000,0x25001000,0x25002000
    mem=Memory([*result['m'].memory.regions,Region(stack,bytearray(256),True),
        Region(owner,bytearray(256),True),Region(dest,bytearray(12000),True)])
    for a,v in ((stack+8,dest),(stack+16,owner),(stack+20,owner+128),
                (owner+12,OUT),(owner+128,1)):mem.write(a,v,4)
    mem.write(stack+24,1,1)  # Explicitly excludes optional +3164 branch.
    machine=Machine(code,mem,dict(sp=stack))
    r=machine.run(0x6074151f,[0x6074178d],limit=30000)
    assert r['status']=='stop',r
    assert len({mem.read(OUT+off,4) for off in (2596,2600,2604)})==1
    expected=bytearray(12000)
    for n in range(256):struct.pack_into('<I',expected,n*4,mem.read(mem.read(OUT+2596,4)+n*2,2))
    tone=mem.read(OUT+2608,4)
    if tone:
        for n in range(256):struct.pack_into('<I',expected,4096+n*4,mem.read(tone+n*2,2))
    for off,out in ((3124,5120),(3128,5632),(3132,6144),(3140,7168)):
        source=mem.read(OUT+off,4)
        for n in range(512):expected[out+n]=mem.read(source+n,1)
    for off,out in ((3136,6656),(3144,7680),(3148,8192),(3152,8704),(3156,9216),(3160,9728)):
        source=mem.read(OUT+off,4)
        for n in range(128):struct.pack_into('<I',expected,out+n*4,mem.read(source+n*2,2))
    actual=bytes(mem.read(dest+n,1) for n in range(12000))
    assert actual==expected, [(i,a,b) for i,(a,b) in enumerate(zip(actual,expected)) if a!=b][:12]
    return sha256(actual).hexdigest(),r['instructions']


def run(image,path,reader,out):
    original=sample_recipe()
    other=replace(original,recipe_id=1002,name='Synthetic contrasting control',
                  hsl=((300,40,-10),)*12,gamma=tuple(min(4095,n*8) for n in range(256)))
    state=build_state([pack_recipe(original),pack_recipe(other)])
    consumer=build(image,state)
    decode(state,out/'state',reader);decode(consumer,out/'consumer',reader)
    stock={}
    for start,end in (*WINDOWS,(0x6074151f,0x6074178d)):
        listing=subprocess.check_output([str(reader.resolve()),str(path.resolve()),hex(BASE),hex(start-BASE),hex(end-BASE)],text=True)
        stock.update(parse_listing(listing,image,BASE))
    code={**stock,**state['code'],**consumer['code']}
    pc=0x6079fb88;raw=encode('jmp',['sd_pipeline_color'],pc,consumer['symbols'])
    patched=bytearray(image);patched[pc-BASE:pc-BASE+len(raw)]=raw
    hookfile=out/'authored-hook.bin';hookfile.write_bytes(raw)
    for at in list(code):
        if pc<=at<pc+len(raw):del code[at]
    listing=subprocess.check_output([str(reader.resolve()),str(hookfile.resolve()),hex(pc),'0',hex(len(raw))],text=True)
    code.update(parse_listing(listing,raw,pc))
    f=SimpleNamespace(image=bytes(patched),code=code,
        selected_descriptor=lambda slot:BASE_ADDRESS+0x2000+(slot-1)*4096,
        regions=[Region(state['base'],bytearray(state['data']),False),
                 Region(consumer['base'],bytearray(consumer['data']),False),
                 Region(0x6239790c,bytearray(4),False),
                 Region(STACK,bytearray(0x40000),True)])
    f.memory=Memory(f.regions)
    saved=None;rows=[]
    for key in (None,None,None,None,11,11):
        slot=(1,1,2,2,1,1)[len(rows)]
        result=frame(f,stock,image,slot,state=saved,key=key)
        expected=frame(f,stock,image,slot,state=saved,key=key,
                       oracle=key is None,stock_only=key is not None,force=key is not None)
        assert result['output']==expected['output']
        actual,n=late(result,stock);oracle,_=late(expected,stock);assert actual==oracle
        rows.append({'slot':slot,'stock_exit':key is not None,'late_output_sha256':actual,
                     'late_instructions':n,'configuration_matches_oracle':True})
        saved=result['output'],result['cache']
    assert rows[0]['late_output_sha256']==rows[1]['late_output_sha256']
    assert rows[2]['late_output_sha256']==rows[3]['late_output_sha256']
    assert rows[0]['late_output_sha256']!=rows[2]['late_output_sha256']
    assert rows[4]['late_output_sha256']==rows[5]['late_output_sha256']
    return {'main_sha256':MAIN_SHA,'transitions':rows,
            'native_owner_token_changed':False,
            'scope':'Synthetic embedded descriptors, null HLS root, private-context forced rebuild and bounded late reader. No SD publication/reload, native allocation, job-cache lifetime, hardware upload/ISP, or last consumer proof.'}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--main',type=Path,required=True)
    p.add_argument('--reader',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    assert not a.output.exists();a.output.mkdir(parents=True)
    image=a.main.read_bytes();assert sha256(image).hexdigest()==MAIN_SHA;verify_reader(a.reader)
    result=run(image,a.main,a.reader,a.output)
    (a.output/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
