"""Execute native mailbox publish/receive slices; never synthesize delivery.

The scheduler, unlock helper and RTOS mailbox receive are deliberate boundaries.
Stages are explicitly invoked; native RTOS ring slices carry the token to the
worker stack. Allocation, wakeup and context switching are not emulated.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import struct
from epl9_art_queue_probe import BASE, MAIN_SHA, SP, QUEUE, DATA, END
from mn103_subset import Memory, Region, parse_listing
from mn103_calls import CallMachine
from mn103_tooling import reader_provenance

WINDOWS=((0x604383c1,0x6043848d),(0x604113a1,0x60411401),
 (0x6041894c,0x60418980),(0x604385ba,0x604385f4),
 (0x6043e341,0x6043e3b4),(0x6043e76a,0x6043e79e),
 (0x60445069,0x604450ad),(0x60410bc3,0x60410c2d),
 (0x60438037,0x604380ad),(0x60438121,0x604381c9),
 (0x604384ea,0x60438501),(0x60411d4f,0x60411d9c),(0x60416cc0,0x60416cfe))

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
                Region(bank,bytearray(256),True),
                Region(0xa2abae2c,bytearray(0x310),True),Region(0xa2abb948,bytearray(4),True),Region(QUEUE,bytearray(452),True),
                Region(DATA,bytearray(16),True),Region(0x22000000,bytearray(512),True)]),dict(sp=SP,d0=0,a0=0x6043e341,a1=QUEUE),psw=0x800)
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
            # Native RTOS ring initializer, with caller-provided backing storage.
            # Stock worker passes NULL: its allocator remains outside this slice.
            obj=0x22000000;buffer=obj+128
            m.memory.write(obj+24,33,4);m.memory.write(obj+28,buffer,4)
            m.r.update(sp=SP,a0=obj)
            result=m.run(m.enter(0x60410bc3,END,0xb0,16),[END])
            if result['status']!='stop' or m.r['d0']!=0 or m.memory.read(obj+44,4)!=33:
                raise ValueError('RTOS ring initialization differs: '+str(result))
            # Choose the final ring position in one control to execute wrap.
            pos=32 if slot==31 else 0
            m.memory.write(obj+32,buffer+pos*4,4)
            m.memory.write(obj+36,buffer+pos*4,4)
            m.memory.write(0xa2abb948,1,4) # declared RTOS handle, not allocated
            # Load the real sender/target transport descriptor from ROM.
            headp,tailp,transport,signal=struct.unpack_from('<4I',image,0x604560ec+sender*16-BASE)
            transport_pos=31 if slot==31 else 0
            m.memory.write(headp,transport_pos,1);m.memory.write(tailp,transport_pos,1)
            m.r.update(sp=SP,a3=headp,a2=tailp)
            for off,value in ((4,transport),(12,0x604384ea),(16,token)):
                m.memory.write(SP+off,value,4)
            result=m.run(0x60438037,[0x604380ad])
            if result['status']!='stop' or m.memory.read(headp,1)!=(transport_pos+1)%32:
                raise ValueError('inter-context producer differs: '+str(result))
            # No fake MMIO: stop before interrupt signalling, invoke receiver explicitly.
            m.r['sp']=SP;m.memory.write(0x8050,0,4)
            result=m.run(m.enter(0x60438121 if sender==1 else 0x60438175,END,0x20,8),[0x604384fa])
            delivered=m.r['d1']
            if result['status']!='stop' or delivered!=token or m.r['d0']!=1:
                raise ValueError('inter-context callback differs: '+str(result))
            m.r.update(sp=SP,d2=obj);m.memory.write(SP+4,delivered,4)
            result=m.run(0x60411d4f,[0x60411d9c])
            if result['status']!='stop' or m.memory.read(obj+44,4)!=32:
                raise ValueError('RTOS enqueue differs: '+str(result))
            # Native receive writes directly to the worker's token stack slot.
            # Scheduling/context handover is still explicit, not emulated.
            m.memory.write(SP+4,0,4);m.memory.write(SP-64+20,SP+4,4)
            m.r.update(sp=SP-64,d2=obj);m.memory.write(0x8050,0,4)
            result=m.run(0x60416cc0,[0x60416db5])
            if (result['status']!='stop' or m.memory.read(SP+4,4)!=token or
                    m.memory.read(obj+44,4)!=33 or
                    m.memory.read(obj+36,4)!=buffer+((pos+1)%33)*4):
                raise ValueError('RTOS dequeue differs: '+str(result))
            m.r["sp"]=SP
            result=m.run(0x604385ba,[0x6043859d])
            if result['status']!='stop' or result['pc']!=0x6043859d:
                raise ValueError('receiver differs: '+str(result))
            if m.memory.read(DATA,1)!=120 or m.memory.read(QUEUE+450,2)!=1 or m.memory.read(bank+slot*8,4)!=0:
                raise ValueError('receiver mutation differs')
            rows.append(dict(sender=sender,target=0,slot=slot,token=hex(token),bank=hex(bank),
                dispatch_instructions=dispatched,rtos_init_transport_and_write_instructions=len(m.trace)-dispatched,
                rtos_ring_wrap=pos==32,transport_ring_wrap=transport_pos==31,
                transport_bank=hex(transport),interrupt_signal_mask=hex(signal),
                raw_mode_readback=120,slot_released=True))
    return dict(schema='epl9-art-mailbox-probe-v3',reader_provenance=provenance,controls=rows,
        publish_boundary='0x60438486 before unlock helper 0x60411489',
        receiver_boundary='0x604385ba after RTOS receive 0x60416bf7',
        receive_token_explicitly_supplied=False,transport_entry_token_explicitly_supplied=True,intercontext_ring_native=True,
        interrupt_signal_executed=False,intercontext_consumer_completion_proven=False,
        rtos_ring_initialized_natively=True,rtos_ring_backing_memory="caller-supplied fixture",
        stock_allocator_executed=False,stage_invocation_explicit=True,pending_storage_record='declared fixture',
        interrupt_delivery_emulated=False,scheduler_emulated=False,
        full_ui_to_processing_proven=False,install_ready=False)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--main',type=Path,required=True);p.add_argument('--reader',type=Path,required=True)
    a=p.parse_args();print(json.dumps(probe(a.main,a.reader),indent=2))
