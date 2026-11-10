"""Trace diagnostic-session messages into TAKE_FUNC/TAKE_FUNC_CP offline.

All fragments stop before queue I/O, handler calls or initialization. No
successful physical session and no absence of downstream side effects claimed.
"""
import argparse
import json
import struct
from pathlib import Path
from epl9_workspace_bridge import ROOT, MAIN, MAIN_SHA, BASE, sha
from mn103_subset import Memory, Region, Machine, parse_listing
from mn103_calls import CallMachine

SP, PACKET, PAYLOAD, CONTEXT = 0x18008000,0x19000000,0x19001000,0x19002000
END=0x1a000000


def run(out):
    if out.exists() or not out.resolve().is_relative_to((ROOT/'local').resolve()):
        raise ValueError('new ignored report required')
    image=MAIN.read_bytes()
    if sha(image)!=MAIN_SHA:raise ValueError('stock identity differs')
    directory=ROOT/'local/epl9-v3-readback-service-20261107'
    paths=[directory/(name+'.tsv') for name in ('notify-queue','take-task','take-worker',
        'take-cp-task','take-cp-open','take-cp-close')]
    code={}
    for p in paths:code.update(parse_listing(p.read_text(encoding='utf-8-sig'),image,BASE))
    def word(a):return struct.unpack_from('<I',image,a-BASE)[0]
    def half(a):return struct.unpack_from('<H',image,a-BASE)[0]
    if (half(0x6042102a),half(0x6042102c))!=(98,99):raise ValueError('queue IDs differ')
    for at,name,ident in ((0x61780ffe,b'TAKE_FUNC',115),
        (0x61786208,b'TAKE_FUNC',98),(0x61786222,b'TAKE_FUNC_CP',99)):
        if image[at-BASE:at-BASE+24].rstrip(b'\0')!=name or half(at+24)!=ident:
            raise ValueError('native object-name record differs')
    if word(0x60419958)!=115 or word(0x60419958+12)!=0x605f9168:
        raise ValueError('TAKE_FUNC task descriptor differs')
    if word(0x60419974)!=116 or word(0x60419974+12)!=0x605f94a7:
        raise ValueError('TAKE_FUNC_CP task descriptor differs')
    rows=[]
    def make(**regs):
        mem=Memory([Region(BASE,image),Region(SP-32768,bytearray(65536),True),
            Region(PACKET,bytearray(64),True),Region(PAYLOAD,struct.pack('<II',2,0),True),
            Region(CONTEXT,bytearray(512),True),Region(0x62615588,bytearray(64),True)])
        mem.write(PACKET+12,PAYLOAD,4)
        return CallMachine(code,mem,dict(sp=SP,**regs))
    for command in (0,1):
        m=make(a3=PACKET,a2=PAYLOAD)
        m.memory.write(SP+16,command,4);m.memory.write(SP+12,98,4)
        r=m.run(0x60434a72,[0x60434a88])
        if (r.get('pc')!=0x60434a88 or m.memory.read(PACKET+8,4)!=command or
            m.memory.read(PACKET+12,4)!=PAYLOAD or m.r['d0']!=98 or
            m.memory.read(m.r['a0'],4)!=PACKET or m.memory.read(m.r['a0']+4,4)!=16):
            raise ValueError('native queue packet construction differs')
        rows.append(dict(kind='packet-build',queue=98,command=command,payload_word=2,
            stopped_before='0x604314e5 queue send'))
    for entry,stop,queue in ((0x605f9175,0x605f9185,98),(0x605f94b5,0x605f94c5,99)):
        m=make(a2=PACKET);r=m.run(entry,[stop])
        if r.get('pc')!=stop or (m.r['d0'],m.r['d1'],m.r['a0'],m.r['a1'])!=(queue,16,PACKET,0xffffffff):
            raise ValueError('native task receive arguments differ')
        rows.append(dict(kind='task-receive',queue=queue,bytes=16,timeout=-1,queue_io_executed=False))
    for command,target in ((0,0x605f92d4),(1,0x60678d88),(2,0x60678d7e)):
        m=make(a3=PACKET+8,d3=PACKET)
        m.memory.write(PACKET+8,command,4);m.memory.write(SP+24,CONTEXT,4)
        r=m.run(0x605f9209,[0x605f921f])
        if r.get('pc')!=0x605f921f or (m.r['a2'],m.r['a0'],m.r['a1'])!=(target,PACKET,CONTEXT):
            raise ValueError('TAKE_FUNC dispatch differs')
        rows.append(dict(kind='take-dispatch',command=command,target=hex(target),handler_executed=False))
    for command,target in ((0,0x605f9573),(1,0x605f957c),(2,0x605f95bc)):
        m=make(a3=0x60600d00);m.memory.write(SP+24,command,4)
        r=m.run(0x605f94f8,[0x605f9530,0x605f95bc])
        selected=m.r['a0'] if r.get('pc')==0x605f9530 else r.get('pc')
        if selected!=target:raise ValueError('TAKE_FUNC_CP hash dispatch differs')
        rows.append(dict(kind='cp-dispatch',command=command,target=hex(target),handler_executed=False))
    m=make(a0=PACKET,a1=CONTEXT)
    r=m.run(0x605f92d4,[0x605f9314])
    if (r.get('pc')!=0x605f9314 or m.memory.read(CONTEXT,4)!=1 or
        m.memory.read(CONTEXT+325,1)!=0 or (m.r['d0'],m.r['d1'],m.r['a0'],m.r['a1'])!=(99,16,PACKET,0xffffffff)):
        raise ValueError('native open forwarding differs')
    rows.append(dict(kind='open-forward',from_queue=98,to_queue=99,command=0,payload_word=2,
        context_active_bit=True,context_325=0,queue_io_executed=False))
    for label,entry,initial,expected,stop in (
        ('open',0x605f9604,0,4,0x605f9688),
        ('close',0x6067d52c,4,0,0x6067d59b)):
        m=make(a0=PAYLOAD);m.memory.write(0x62615588,initial,4)
        r=m.run(m.enter(entry,END,0x80,24),[stop])
        if r.get('pc')!=stop or m.memory.read(0x62615588,4)!=expected or m.r['d0']!=0:
            raise ValueError('native diagnostic state transition differs: '+str(r))
        rows.append(dict(kind='cp-state-'+label,payload_word=2,before=initial,after=expected,
            state_address='0x62615588',next_call='0x605f96c0' if label=='open' else '0x6067d641',
            next_argument=0,initialization_or_teardown_executed=False))
    report=dict(model='E-PL9 / IM008 / 1330',displayed_version='1.1 (owner report)',build='1101',
        main_bytes=len(image),main_sha256=sha(image),cases=rows,
        source_sha256=sha(Path(__file__).read_bytes()),
        listing_sha256={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in paths},
        task_ids=dict(TAKE_FUNC=115,TAKE_FUNC_CP=116),queue_ids=dict(TAKE_FUNC=98,TAKE_FUNC_CP=99),
        payload_two_is_not_dispatch_command=True,open_command=0,close_command=1,
        open_initializer='0x605f96c0',close_initializer='0x6067d641',
        full_session_side_effects_qualified=False,physical_transport_qualified=False,
        camera_accessed=False,firmware_modified=False)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(native_fragment_cases=len(rows),open_command=0,close_command=1,
        payload_word=2,open_cp_state=4,full_session_side_effects_qualified=False)))


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',type=Path,required=True)
    run(ap.parse_args().out)
