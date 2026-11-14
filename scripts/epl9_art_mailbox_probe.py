"""Execute native mailbox publish/receive slices; never synthesize delivery.

The scheduler, unlock helper and RTOS mailbox receive are deliberate boundaries.
The receive slice is invoked explicitly with the token produced by dispatch.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from epl9_art_queue_probe import BASE, MAIN_SHA, SP, QUEUE, DATA, END
from mn103_subset import Memory, Region, parse_listing
from mn103_calls import CallMachine
from mn103_tooling import reader_provenance

WINDOWS=((0x604383c1,0x6043848d),(0x604113a1,0x60411401),
 (0x6041894c,0x60418980),(0x604385ba,0x604385f4),
 (0x6043e341,0x6043e3b4),(0x6043e76a,0x6043e79e),
 (0x60445069,0x604450ad))

def probe(main,reader):
    image=main.read_bytes()
    if hashlib.sha256(image).hexdigest()!=MAIN_SHA:raise ValueError('wrong stock image')
    provenance=reader_provenance(reader); code={}; rows=[]
    for a,b in WINDOWS:
        listing=subprocess.check_output([str(reader),str(main),hex(BASE),hex(a-BASE),hex(b-BASE)],text=True)
        code.update(parse_listing(listing,image,BASE))
    for sender in (1,2):
        for slot in (0,7,31):
            bank=0xa2abb744 if sender==1 else 0xa2abb844
            m=CallMachine(code,Memory([Region(BASE,image),
                Region(SP-8192,bytearray(16384),True),Region(0x8050,bytearray(4),True),
                Region(0x8ff00004,bytearray(12),True),Region(0x21000000,bytearray(1024),True),
                Region(bank,bytearray(256),True),Region(QUEUE,bytearray(452),True),
                Region(DATA,bytearray(16),True)]),dict(sp=SP,d0=0,a0=0x6043e341,a1=QUEUE),psw=0x800)
            m.memory.write(0x8050,sender,4)
            m.memory.write(0x8ff00004+sender*4,0x21000000,4)
            m.memory.write(0x21000000+28,0x21000200,4)
            m.memory.write(0x21000000+16,0x21000300,4)
            for i in range(slot):m.memory.write(bank+i*8,0x10000004,4)
            # A declared pending ART raw-write record, same layout as queue probe.
            for offset,value,size in ((0,1,2),(2,0x9481,2),(4,0,2),(8,DATA,4),(12,120,4),(448,1,2)):
                m.memory.write(QUEUE+offset,value,size)
            result=m.run(m.enter(0x604383c1,END,0xf0,40),[0x60438486])
            token=(sender<<16)|slot
            if result['status']!='stop' or result['pc']!=0x60438486 or m.r['d3']!=token:
                raise ValueError('dispatch differs: '+str(result))
            if m.memory.read(bank+slot*8,4)!=0x6043e341 or m.memory.read(bank+slot*8+4,4)!=QUEUE:
                raise ValueError('published mailbox differs')
            dispatched=len(m.trace)
            # Do not execute/fake unlock, scheduling or mailbox receive. Supply
            # its prospective token at the observed post-receive stack position.
            m.r['sp']=SP;m.memory.write(SP+4,token,4);m.memory.write(0x8050,0,4)
            result=m.run(0x604385ba,[0x6043859d])
            if result['status']!='stop' or result['pc']!=0x6043859d:
                raise ValueError('receiver differs: '+str(result))
            if m.memory.read(DATA,1)!=120 or m.memory.read(QUEUE+450,2)!=1 or m.memory.read(bank+slot*8,4)!=0:
                raise ValueError('receiver mutation differs')
            rows.append(dict(sender=sender,target=0,slot=slot,token=hex(token),bank=hex(bank),
                dispatch_instructions=dispatched,receive_and_write_instructions=len(m.trace)-dispatched,
                raw_mode_readback=120,slot_released=True))
    return dict(schema='epl9-art-mailbox-probe-v1',reader_provenance=provenance,controls=rows,
        publish_boundary='0x60438486 before unlock helper 0x60411489',
        receiver_boundary='0x604385ba after RTOS receive 0x60416bf7',
        receive_token_explicitly_supplied=True,pending_storage_record='declared fixture',
        interrupt_delivery_emulated=False,scheduler_emulated=False,
        full_ui_to_processing_proven=False,install_ready=False)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--main',type=Path,required=True);p.add_argument('--reader',type=Path,required=True)
    a=p.parse_args();print(json.dumps(probe(a.main,a.reader),indent=2))
