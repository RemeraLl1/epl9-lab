"""Bounded native parameter-owner lifecycle, not a safe recipe release hook."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import struct
import subprocess
from epl9_workspace_bridge import BASE, MAIN_SHA
from mn103_tooling import verify_reader
from mn103_subset import Machine, Memory, Region, parse_listing
from mn103_calls import CallMachine

WINDOWS=((0x6074b20b,0x6074b22c),(0x6074b41f,0x6074b4f8),
         (0x60763913,0x6076395b),(0x6073e57a,0x6073e588),
         (0x6074e323,0x6074e32e))
OWNER,JOB,STACK,OUT=0x21000000,0x22000000,0x23000000,0x24000000
END=0xdeadbeef

def fixture(code):
    owner,job,stack,out=bytearray([0xa5])*16000,bytearray(15000),bytearray(1024),bytearray(8)
    mem=Memory([Region(OWNER,owner,True),Region(JOB,job,True),Region(STACK,stack,True),Region(OUT,out,True)])
    return CallMachine(code,mem,dict(sp=STACK+512)),owner,job

def bounded(m,start,stops):
    r=m.run(start,stops,limit=1000)
    assert r['status']=='stop' and r['pc'] in stops,r
    return r

def run(code):
    m,owner,job=fixture(code)
    m.r['a3']=OWNER
    bounded(m,0x6074b20b,[0x6074b22c])
    zeroed=[]
    for i in range(3):
        for off in (4,12,20):
            at=2400+4184*i+off
            assert owner[at:at+4]==b'\0'*4
            zeroed.append(at)
    expected=bytearray([0xa5])*16000
    for at in zeroed:expected[at:at+4]=b'\0'*4
    assert owner==expected
    # Execute selection loop only: exclusion entry/exit are NOT modeled locks.
    selection=[]
    slots=[OWNER+2400+i*4184 for i in range(3)]
    for mask in range(8):
        m,owner,job=fixture(code)
        held=[s for i,s in enumerate(slots) if mask&(1<<i)]
        for off,val in zip((15408,15412,15416),held+[0]*3):m.memory.write(OWNER+off,val,4)
        m.r.update(a2=OWNER,a3=OUT,d2=0)
        m.memory.write(STACK+516,0,1)
        bounded(m,0x6074b441,[0x6074b474])
        want=next((s for s in slots if s not in held),0)
        assert m.memory.read(OUT,4)==want
        assert m.memory.read(STACK+516,1)==int(bool(want))
        selection.append({'held_mask':mask,'selected_slot':slots.index(want) if want else None})
    # Native borrow -> J+12320 publication, excluding actual image processing.
    m,owner,job=fixture(code)
    m.memory.write(OWNER+15428,0,2);m.memory.write(OWNER+15408,slots[1],4)
    m.memory.write(JOB+3980,OWNER,4)
    m.r.update(a2=JOB,d2=JOB+100,d3=0)
    bounded(m,0x60763913,[0x60763938])
    assert m.memory.read(JOB+12320,4)==slots[1]
    assert m.memory.read(OWNER+15428,2)==1
    # Native publisher waits while borrowed. Stop before sleep, no scheduler.
    m.r.update(a2=OWNER,a3=OWNER+15428,d2=1)
    m.memory.write(STACK+516,OUT,4);m.memory.write(OUT,slots[2],4)
    bounded(m,0x6074b497,[0x6074b4c5])
    assert m.memory.read(OWNER+15408,4)==slots[1]
    # Resume caller after skipped processing: native release/clear is tested,
    # not evidence that processing succeeds or drains hardware.
    m.r.update(a2=JOB,a3=JOB+3980,d0=0)
    bounded(m,0x60763948,[0x6076395b])
    assert m.memory.read(OWNER+15428,2)==0
    assert m.memory.read(JOB+12320,4)==0
    # Unborrowed publication (critical section excluded) moves/clears source.
    m.r.update(a2=OWNER,a3=OWNER+15428,d2=1)
    bounded(m,0x6074b497,[0x6074b4bc])
    assert m.memory.read(OWNER+15408,4)==slots[2]
    assert m.memory.read(OUT,4)==0
    # Cache destructor only forwards storage to allocator free; no table walk.
    m,_,_=fixture(code);m.r['a0']=0
    bounded(m,m.enter(0x6073e57a,END,0,4),[END])
    m,_,_=fixture(code);m.r['a0']=0x25000000
    r=m.run(m.enter(0x6073e57a,END,0,4),[END])
    assert r['status']=='external_call' and r['target']==0x604023b2,r
    assert m.r['a0']==0x25000000
    # Exact job cache alias, stopping before native cache-destructor call.
    m.memory.write(JOB+12316,0x25000000,4);m.r['a2']=JOB
    bounded(m,0x6074e323,[0x6074e327]);assert m.r['a0']==0x25000000
    return {'slot_stride':4184,'slot_count':3,'slot_token_initialization_offsets':zeroed,
            'selection_controls':selection,'borrow_counter_offset':15428,
            'job_parameter_pointer_offset':12320,'borrow_publish_release_clear':True,
            'borrowed_publication_waits':True,'unborrowed_publication_moves_pointer':True,
            'job_cache_pointer_offset':12316,'cache_destructor_forwards_to_free':True,
            'scope':'Native bounded fragments with synthetic owner/job. No image-processing call, locks, scheduler, allocator free, DMA, full job teardown or global last-consumer proof.'}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--main',type=Path,required=True)
    p.add_argument('--reader',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    image=a.main.read_bytes();assert sha256(image).hexdigest()==MAIN_SHA;verify_reader(a.reader);code={}
    for start,end in WINDOWS:
        listing=subprocess.check_output([str(a.reader.resolve()),str(a.main.resolve()),hex(BASE),hex(start-BASE),hex(end-BASE)],text=True)
        code.update(parse_listing(listing,image,BASE))
    result=run(code);result['main_sha256']=MAIN_SHA
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
