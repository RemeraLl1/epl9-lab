"""Native ART RAM queue serialization and consumer, not scheduler emulation.

Producer starts after external locking; consumer is explicitly invoked, not
claimed to have been scheduled. Context selector 0x8050 is NOT a service flag.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from epl9_embedded_art_inventory import BASE,MAIN_SHA
from mn103_subset import Memory,Region,parse_listing
from mn103_calls import CallMachine
from mn103_tooling import reader_provenance
SP=0x10012000
QUEUE=0xa2ad2710
DATA=0x20000000
END=0x10000000
WINDOWS=((0x6043e3e4,0x6043e448),(0x6043e341,0x6043e3b4),
 (0x6043e76a,0x6043e79e),(0x60445069,0x604450ad),(0x604383c1,0x604383fd),
 (0x604113a1,0x60411401),(0x6041894c,0x60418950))


def probe(main,reader):
    image=main.read_bytes()
    if hashlib.sha256(image).hexdigest()!=MAIN_SHA:raise ValueError('wrong stock image')
    provenance=reader_provenance(reader);code={}
    for a,b in WINDOWS:
        listing=subprocess.check_output([str(reader),str(main),hex(BASE),hex(a-BASE),hex(b-BASE)],text=True)
        code.update(parse_listing(listing,image,BASE))
    def machine(head,tail,selector=1):
        m=CallMachine(code,Memory([Region(BASE,image),Region(0x8050,bytearray(4),True),
            Region(SP-8192,bytearray(16384),True),Region(QUEUE,bytearray(452),True),
            Region(DATA,bytearray(16),True),Region(0x8ff00004,bytearray(12),True),
            Region(0x21000000,bytearray(1024),True)]),dict(sp=SP,a2=0x9481))
        m.memory.write(0x8050,selector,4)
        m.memory.write(0x8ff00004+selector*4,0x21000000,4)
        m.memory.write(0x21000000+28,0x21000200,4)
        m.memory.write(QUEUE+448,head,2);m.memory.write(QUEUE+450,tail,2)
        # Actual producer-frame inputs at the post-lock boundary.
        for offset,value,size in ((24,1,2),(20,DATA,4),(48,0,2),(52,0,2),
                                  (16,0,4),(60,0,4),(56,120,4)):
            m.memory.write(SP+offset,value,size)
        return m
    rows=[]
    for head in (0,15):
        m=machine(head,head);result=m.run(0x6043e3e4,[0x6043e448])
        if result['status']!='stop':raise ValueError('producer did not enqueue')
        record=QUEUE+28*head
        expected=((0,1,2),(2,0x9481,2),(4,0,2),(8,DATA,4),(12,120,4))
        if any(m.memory.read(record+o,s)!=v for o,v,s in expected):raise ValueError('queue payload mismatch')
        if m.memory.read(DATA,1)!=0:raise ValueError('producer wrote data early')
        produced=len(m.trace)
        m.r.update(sp=SP,a0=QUEUE)
        result=m.run(m.enter(0x6043e341,END),[END])
        if (result['status']!='stop' or result['pc']!=END or m.memory.read(DATA,1)!=120 or
            m.memory.read(QUEUE+450,2)!=(head+1)%16):raise ValueError('consumer mutation differs')
        if not any(e['op']=='call' and e['target']==0x6043e76a for e in m.events):raise ValueError('raw writer not executed')
        rows.append(dict(initial_head=head,final_head=m.memory.read(QUEUE+448,2),
            final_tail=m.memory.read(QUEUE+450,2),native_producer_instructions=produced,
            native_consumer_instructions=len(m.trace)-produced,readback=120))
    m=machine(15,0);result=m.run(0x6043e3e4,[0x6043e478])
    if result['status']!='stop' or m.memory.read(QUEUE+15*28,2)!=0 or m.memory.read(DATA,1)!=0:
        raise ValueError('full queue branch differs')
    full_head=m.memory.read(QUEUE+448,2)
    # Different target/current contexts enter the unresolved locking path.
    m=machine(0,0);m.r.update(d0=0,a0=0x6043e341,a1=QUEUE)
    dispatch=m.run(m.enter(0x604383c1,END,0xf0,40),[0x6041894e])
    if dispatch['status']!='stop' or dispatch['pc']!=0x6041894e:
        raise ValueError('cross-context boundary differs: '+str(dispatch))
    return dict(schema='epl9-art-queue-probe-v1',reader_provenance=provenance,controls=rows,
        full_queue_branch=dict(payload_untouched=True,observed_head_after_branch=full_head,
            recovery_after_full_not_executed=True),
        cross_context_dispatch_boundary=hex(dispatch['pc']),
        boundary_instruction='mov psw,d0',context_control_blocks='declared fixtures',
        producer_locking_executed=False,consumer_explicitly_invoked=True,
        scheduler_emulated=False,notification_lifecycle_proven=False,install_ready=False)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--main',type=Path,required=True);p.add_argument('--reader',type=Path,required=True)
    a=p.parse_args();print(json.dumps(probe(a.main,a.reader),indent=2))
