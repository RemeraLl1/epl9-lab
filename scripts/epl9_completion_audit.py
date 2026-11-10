"""Execute native owner/notification contracts; no pixel or ISP completion model."""

from mn103_tooling import default_reader, verify_reader
import argparse
import hashlib
import json
import struct
import subprocess
import random
from pathlib import Path

from epl9_job_probe import (load, invoke, ROOT, BASE, MAIN_SHA, STOCK_SHA, RETURN,
                            JOB, STACK, SP, FixtureEventBits, FixtureSignal,
                            FixtureCompletion)
from mn103_calls import CallMachine
from mn103_subset import Memory, Region, Fault, parse_listing
from mn103_models import FillModel

OWNER, TAG, PENDING = 0x10040000, 0x10050000, JOB+13640
WINDOWS = {
    'format_family_printer': (0x61767948, 0x6176799f),
    'format_subtype_printer': (0x6176799f, 0x61767a50),
    'owner_wrapper_end': (0x607d16c7, 0x607d173a),
}
ANCHORS = {
    0x6176795c: 'cmp\t2,d1',
    0x6176796e: 'mov\t1635379064,d0',
    0x607505a9: 'call\t0x6074fbd3,[],12',
    0x607505c9: 'call\t0x6074fbd3,[],12',
    0x607d1724: 'call\t0x607cfe92,[d2,d3,a2,a3],44',
}


def read_cstring(m,address,limit=128):
    result=bytearray()
    for offset in range(limit):
        value=m.memory.read(address+offset,1)
        if not value:
            return result.decode('ascii')
        result.append(value)
    raise Fault('unterminated diagnostic string')


class DiagnosticSink:
    """Declared logging sink, not the native logging implementation."""
    name='bounded-diagnostic-sink'

    def __init__(self,kind):
        if kind not in ('owner','format'):
            raise ValueError('unknown diagnostic sink contract')
        self.kind=kind

    def validate(self,m,mask,frame):
        expected=(0xf0,172) if self.kind=='owner' else (0,12)
        if (mask,frame)!=expected:
            raise Fault('diagnostic sink ABI mismatch')
        if self.kind=='owner':
            if not any(e.get('pc') in (0x607cfee4,0x607d1718) for e in m.events[-1:]):
                # A modeled call has not yet been appended; use native PC trace.
                if not m.trace or m.trace[-1] not in (0x607cfee2,0x607d1712):
                    raise Fault('undeclared native diagnostic caller')
            if m.r['d1'] not in (0x5b0081,0xcd026f):
                raise Fault('undeclared diagnostic source tag')
        else:
            pointer=m.memory.read(m.r['sp']+4,4)
            if not BASE<=pointer<BASE+26214336:
                raise Fault('diagnostic string must come from exact ROM')
            read_cstring(m,pointer)

    def apply(self,m):
        detail={'logging_only':True,'pixels_completed':False}
        if self.kind=='format':
            # Native call has now allocated its 12-byte frame.
            detail['text']=read_cstring(m,m.memory.read(m.r['sp']+16,4))
        m.r['d0']=0
        return detail


def extend_code(image,code):
    code=dict(code)
    path=ROOT/'local/epl9-1101-analysis/decoded/00_0100_406e0020.decoded.bin'
    reader=default_reader()
    for start,end in WINDOWS.values():
        verify_reader(reader)
        listing=subprocess.check_output([str(reader),str(path),hex(BASE),hex(start-BASE),hex(end-BASE)],text=True)
        decoded=parse_listing(listing,image,BASE)
        for at in code.keys() & decoded.keys():
            if code[at]!=decoded[at]:
                raise ValueError(f'conflicting decode at {at:#x}')
        code.update(decoded)
    for at,expected in ANCHORS.items():
        _,op,args=code[at]
        assert op+'\t'+','.join(args)==expected
    return code


def machine(image,code,status=1):
    job,owner=bytearray(16384),bytearray(512)
    struct.pack_into('<2I',job,4,0x607cfe8d,OWNER)
    struct.pack_into('<I',owner,4,TAG)
    owner[195]=status
    pool=FixtureEventBits(); pool.allocated=1
    signal=FixtureSignal(pool)
    models={0x607cc266:DiagnosticSink('owner'),0x604b9ded:DiagnosticSink('format'),
            0x6074af2c:signal,0x4700111e:FillModel()}
    for address,kind in ((0x60418b31,'wait'),(0x60410a51,'clear'),(0x6074aef3,'token')):
        models[address]=FixtureCompletion(kind,signal,None,None)
    m=CallMachine(code,Memory([Region(BASE,image),Region(JOB,job,True,'job'),
        Region(OWNER,owner,True,'native owner state'),Region(TAG,bytearray(4)),
        Region(STACK,bytearray(16384),True,'stack'),Region(0x8050,bytearray(4))]),
        {'sp':SP},models=models)
    return m,pool,signal


def owner_cases(image,code):
    rows=[]
    for entry in (0x607cfe8d,0x607d16c7):
        for event in (23,24):
            for status in (0,1):
                m,_,_=machine(image,code,status)
                before=bytes(next(r for r in m.memory.regions if r.address==OWNER).data)
                result=invoke(m,entry,0,0,{'d0':event,'a0':0,'a1':OWNER})
                assert result.get('pc')==RETURN and m.r['sp']==SP,result
                assert m.r['d0']==status
                assert bytes(next(r for r in m.memory.regions if r.address==OWNER).data)==before
                assert all(e.get('target')==0x607cc266 for e in m.events if e['op']=='modeled_call')
                rows.append(dict(entry=hex(entry),event=event,owner_status=status,
                                 owner_state_preserved=True,result=result,events=m.events))
    return rows


def notification_cases(image,code):
    """Inject a software notification only; no hardware event is synthesized."""
    rows=[]
    for enabled in (0,1):
        for status in (0,0x9e40):
            m,pool,signal=machine(image,code)
            m.memory.write(JOB+10396,enabled,1)
            for offset,value,size in ((0,JOB,4),(16,1,4),(36,0xff07,2),(38,0xff0b,2)):
                m.memory.write(PENDING+offset,value,size)
            result=invoke(m,0x607504f6,0,0,{'d0':10,'a0':status,'a1':PENDING})
            assert result.get('pc')==RETURN and m.r['d0']==1 and m.r['sp']==SP,result
            assert m.memory.read(PENDING+32,2)==status and signal.signalled==1
            slot_calls=[e['pc'] for e in m.events if e.get('target')==0x6074fbd3]
            assert slot_calls==([0x607505a9,0x607505c9] if enabled else [])
            signal_position=next(i for i,e in enumerate(m.events) if e.get('model')=='fixture-event-signal')
            assert all(i<signal_position for i,e in enumerate(m.events) if e.get('target')==0x6074fbd3)
            cleanup=invoke(m,0x6074edd9,0x70,28,{'a0':PENDING})
            assert cleanup.get('pc')==RETURN and m.r['d0']==status and m.r['sp']==SP,cleanup
            assert not pool.allocated and not signal.signalled
            assert all(m.memory.read(PENDING+n,4)==0 for n in range(0,56,4))
            rows.append(dict(owner_slot_notification_enabled=enabled,injected_status=hex(status),
                result=result,cleanup=cleanup,notification_precedes_signal=True,pending_zero=True,
                synthetic_notification_only=True,pixel_cycle=False,events=m.events))
    return rows


def format_cases(image,code):
    rows=[]
    for fmt in (0x100,0x200,0x302,0x305,0x307):
        m,_,_=machine(image,code)
        family=invoke(m,0x61767948,0,8,{'d0':fmt,'a0':OWNER})
        assert family.get('pc')==RETURN and m.r['sp']==SP,family
        subtype=invoke(m,0x6176799f,0x20,12,{'d0':fmt,'a0':OWNER})
        assert subtype.get('pc')==RETURN and m.r['sp']==SP,subtype
        texts=[e['text'].rstrip('\r\n') for e in m.events if 'text' in e]
        expected={0x100:['type     : Bayer','BayerBit : 8'],
                  0x200:['type     : 4AspectsData'],
                  0x302:['type     : YCC','YC Type  : YCC422'],
                  0x305:['type     : YCC','YC Type  : YCC444'],
                  0x307:['type     : YC420','YC Type  : YYCC']}[fmt]
        assert texts==expected,(hex(fmt),texts)
        rows.append(dict(format=hex(fmt),native_labels=texts,events=m.events))
    return rows


def wide_arithmetic_cases(image,code):
    rng=random.Random(1331101)
    rows=[]
    values=[0,1,0xffffffff,0x100000000,0x7fffffffffffffff,0xffffffffffffffff]
    values += [rng.randrange(1<<64) for _ in range(24)]
    m,_,_=machine(image,code)
    for value in values:
        for count in (0,1,12,31,32,33,63):
            result=invoke(m,0x604bbfac,0xc0,8,
                          {'d0':value&0xffffffff,'d1':value>>32,'a0':count})
            got=(m.r['d1']<<32)|m.r['d0']
            assert result.get('pc')==RETURN and m.r['sp']==SP,result
            assert got==(value<<count)&((1<<64)-1),(value,count,got)
            rows.append(dict(operation='shift_left_64',value=hex(value),count=count,output=hex(got)))
        for divisor in (1,100,0x100000001,0xffffffffffffffff):
            result=invoke(m,0x604bbecc,0xf0,28,
                {'d0':value&0xffffffff,'d1':value>>32,'a0':divisor&0xffffffff,'a1':divisor>>32})
            got=(m.r['d1']<<32)|m.r['d0']
            assert result.get('pc')==RETURN and m.r['sp']==SP,result
            assert got==value//divisor,(value,divisor,got,value//divisor)
            rows.append(dict(operation='divide_unsigned_64',value=hex(value),divisor=hex(divisor),output=hex(got)))
    return rows


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    if not __debug__ or args.out.exists() or not args.out.resolve().is_relative_to((ROOT/'local').resolve()):
        parser.error('assertions and new ignored local directory required')
    image,code=load(); code=extend_code(image,code)
    report=dict(model='Olympus E-PL9',displayed_version='1.1 (owner report)',main_build='1101',
        stock_bytes=104552480,stock_sha256=STOCK_SHA,main_bytes=len(image),main_sha256=MAIN_SHA,
        camera_accessed=False,firmware_modified=False,full_pixel_cycle_passed=False,
        owner_cases=owner_cases(image,code),notification_cases=notification_cases(image,code),
        format_cases=format_cases(image,code),
        wide_arithmetic_cases=wide_arithmetic_cases(image,code),
        source_sha256={name:hashlib.sha256((ROOT/'scripts'/name).read_bytes()).hexdigest()
                       for name in ('epl9_completion_audit.py','epl9_job_probe.py','mn103_calls.py','mn103_subset.py')},
        limitations=['logging fronts use declared host sink',
                     'two native owners do not identify every camera caller',
                     'software-injected notification is not ISP or successful pixel completion',
                     'format labels do not establish physical sample bit/channel order'])
    args.out.mkdir(parents=True)
    (args.out/'results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(owner_cases=len(report['owner_cases']),notification_cases=len(report['notification_cases']),
                          format_cases=len(report['format_cases']),
                          wide_arithmetic_cases=len(report['wide_arithmetic_cases']),full_pixel_cycle=False)))


if __name__=='__main__':
    main()
