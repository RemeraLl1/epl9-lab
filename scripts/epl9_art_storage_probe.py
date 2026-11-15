"""Native RAM registration/write/read controls, not service startup or persistence.

Three stock record descriptors are registered by native initializer fragments.
RAM buffers and context state are declared fixtures; no service calls are
modeled. A cross-context contrast must stop, not pretend to complete.
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
REGISTRY=0xa2abc6cc
END=0x10000000
WINDOWS=((0x6043c371,0x6043c380),(0x6043c390,0x6043c3b8),
 (0x6043c4fa,0x6043c510),(0x6043d63b,0x6043d72d),
 (0x6043e325,0x6043e341),(0x6043e62b,0x6043e64d),
 (0x6043e702,0x6043e79e),(0x6043eb2a,0x6043eb72),(0x60445069,0x604450ad),
 (0x6069cbd9,0x6069cbf1),(0x606ba38f,0x606ba3fc),
 (0x606ba478,0x606ba4ca),(0x606ba680,0x606ba6a8),(0x606ba6fe,0x606ba701),
 (0x606ba826,0x606ba84a),(0x606badd3,0x606baddc))


def probe(main,reader):
    image=main.read_bytes()
    if hashlib.sha256(image).hexdigest()!=MAIN_SHA:raise ValueError('wrong stock image')
    provenance=reader_provenance(reader);code={}
    for a,b in WINDOWS:
        s=subprocess.check_output([str(reader),str(main),hex(BASE),hex(a-BASE),hex(b-BASE)],text=True)
        code.update(parse_listing(s,image,BASE))
    def fresh():
        return CallMachine(code,Memory([Region(BASE,image),Region(0x8050,bytearray(4),True),
            Region(SP-8192,bytearray(16384),True),Region(0x20000000,bytearray(8192),True),
            Region(0xa2abc6c8,bytearray(32772),True),
            Region(0xa2ace6cc,bytearray(4),True),
            Region(0xa2a55680,bytearray(8297),True),
            Region(0x6262b670,bytearray(4),True),Region(0x6262f744,bytearray(1),True)]),dict(sp=SP))
    m=fresh();registrations=[]
    for source,key,count,buffer in ((0x6049a5cc,0x9481,1,0x20000000),
            (0x60477ca0,0x44c1,13,0x20000010),(0x604955d8,0x8b54,1630,0x20000100)):
        if m.memory.read(source,2)!=key or m.memory.read(source+2,2)!=count:
            raise ValueError('stock descriptor differs')
        m.r.update(sp=SP,a0=source,a1=buffer,d0=REGISTRY)
        result=m.run(m.enter(0x6043d697,END,0xf0,44),[0x6043d713])
        slot=REGISTRY+(key>>4)*8
        if result['status']!='stop' or m.memory.read(slot,2)!=key or m.memory.read(slot+4,4)!=buffer:
            raise ValueError('native registration failed')
        registrations.append(dict(storage_id=hex(key),elements=count,descriptor=hex(source),
            pointer_registered_by_native_code=True,initial_ram='declared zeros'))
    controls=[]
    for prop,value,key,index in ((0x6f,120,0x9481,0),(0x1d4,2,0x44c1,8),(0x16a,2,0x44c1,0)):
        m.r.update(sp=SP,d0=prop,d1=value);before=len(m.trace)
        result=m.run(m.enter(0x6069cbd9,END,0xc0,12),[END])
        if result['status']!='stop' or result['pc']!=END:raise ValueError('write did not complete: '+str(result))
        write_count=len(m.trace)-before
        m.r.update(sp=SP,d0=key,d1=index,a0=0)
        result=m.run(m.enter(0x6043e62b,END,0xc0,12),[END])
        if result['status']!='stop' or m.r['d0']!=value:raise ValueError('native readback differs')
        controls.append(dict(property_id=hex(prop),value=value,storage_id=hex(key),index=index,
            native_write_instructions=write_count,native_readback=value))
    # Nonzero current context must hit the real cross-context queue function.
    m.memory.write(0x8050,1,4);m.r.update(sp=SP,d0=0x6f,d1=119)
    contrast=m.run(m.enter(0x6069cbd9,END,0xc0,12),[END])
    if contrast['status']!='external_call' or contrast['target']!=0x6043e3b4:
        raise ValueError('cross-context boundary differs: '+str(contrast))
    if m.models or any(e['op']=='modeled_call' for e in m.events):raise ValueError('unexpected model')
    return dict(schema='epl9-art-storage-probe-v1',reader_provenance=provenance,
        registrations=registrations,controls=controls,
        context_1_contrast=dict(status=contrast['status'],target=hex(contrast['target'])),
        declared_state=dict(context_selector=0,write_lock=0,lazy_cache_initialization=0),
        service_startup_executed=False,persistent_write_proven=False,
        notification_lifecycle_executed=False,install_ready=False)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--main',type=Path,required=True);p.add_argument('--reader',type=Path,required=True)
    a=p.parse_args();print(json.dumps(probe(a.main,a.reader),indent=2))
