"""Native interrupt/status replay; explicit synthetic registers, no ISP model."""
import argparse
import hashlib
import json
import struct
import subprocess
from pathlib import Path

from epl9_completion_audit import machine, extend_code, PENDING
from epl9_job_probe import (load, invoke, ROOT, BASE, MAIN_SHA, STOCK_SHA, JOB, SP,
                            OUTPUT, SCRATCH, RECIPES, header, RETURN)
from mn103_subset import Memory, Region, Fault, parse_listing

WINDOWS={
    'interrupt_status_dispatch':(0x607491e9,0x6074930a),
    'native_consumer_slot':(0x6074001a,0x60740038),
    'native_task_submission':(0x607419ea,0x60741adf),
    'descriptor_diagnostic_fields':(0x6176a567,0x6176a6f9),
}
RECORD=0x62636adc  # Exact task-0 base selected by ROM 608be540.
CONTEXT=0x1d000000


class RegisterReplay(Memory):
    """An exact finite read sequence, not RAM pretending to be hardware.

    Reads are consumed independently of writes. No W1C/IRQ/DMA semantics are
    inferred; these are declared test stimuli and observable write intents.
    """
    def __init__(self,regions,reads,writes):
        super().__init__(regions)
        self.reads={address:list(values) for address,values in reads.items()}
        self.allowed_writes=set(writes)
        self.transactions=[]

    @staticmethod
    def peripheral(address):
        return 0x98000000<=address<0xa0000000

    def read(self,address,size):
        if not self.peripheral(address):
            return super().read(address,size)
        if size!=4 or address%4 or not self.reads.get(address):
            raise Fault(f'undeclared/exhausted hardware read {address:#x}/{size}')
        value=self.reads[address].pop(0)
        self.transactions.append(dict(operation='read',address=hex(address),value=hex(value)))
        return value

    def write(self,address,value,size):
        if not self.peripheral(address):
            return super().write(address,value,size)
        if size!=4 or address%4 or address not in self.allowed_writes:
            raise Fault(f'undeclared hardware write {address:#x}/{size}')
        self.transactions.append(dict(operation='write',address=hex(address),value=hex(value&0xffffffff)))

    def exhausted(self):
        return not any(self.reads.values())


def native_code(image,code):
    code=extend_code(image,code)
    path=ROOT/'local/epl9-1101-analysis/decoded/00_0100_406e0020.decoded.bin'
    reader=ROOT/'local/mn103-tooling/mn103-reader.exe'
    for start,end in WINDOWS.values():
        listing=subprocess.check_output([str(reader),str(path),hex(BASE),hex(start-BASE),hex(end-BASE)],text=True)
        decoded=parse_listing(listing,image,BASE)
        for address in code.keys() & decoded.keys():
            assert code[address]==decoded[address]
        code.update(decoded)
    anchors={0x60749205:'and\td0,d2',0x607492da:'movhu\t(44,a0),d0',
             0x607492ea:'mov\t10,d0',0x60749300:'call\t0x6073eab3,[a2,a3],12',
             0x607419fe:'mov\td1,(a1)'}
    for address,expected in anchors.items():
        _,op,args=code[address]
        assert op+'\t'+','.join(args)==expected
    assert struct.unpack_from('<I',image,0x608be540-BASE)[0]==RECORD
    # Same 56-byte envelope, different meanings at +16/+18.
    for address,expected in {
        0x6176a5d6:'movhu\t(16,a2),d0',0x6176a5e6:'movhu\t(18,a2),d0',
        0x6176a6bf:'movhu\t(16,a2),d0',0x6176a6cf:'movhu\t(18,a2),d0',
    }.items():
        _,op,args=code[address]
        assert op+'\t'+','.join(args)==expected
    for address,label in ((0x617a2e77,b'usAreaHw'),(0x617a2e8b,b'usAreaVw'),
                          (0x617a2e9f,b'usOffsetH'),(0x617a2eb3,b'usOffsetV')):
        assert image[address-BASE:address-BASE+len(label)]==label
    return code


def replay_case(image,code,key,selector,scenario):
    m,pool,signal=machine(image,code)
    m.memory=Memory([*m.memory.regions,Region(RECORD,bytearray(48*9),True,'native worker records'),
                     Region(OUTPUT,bytearray([0xcd])*64+bytearray([0xa5])*16,True,'unprocessed output')])
    m.memory.write(JOB+10396,1,1)
    for offset,value,size in ((0,JOB,4),(16,1,4),(36,0xff07,2),(38,0xff0b,2)):
        m.memory.write(PENDING+offset,value,size)
    # Identity is retained for comparison; ISR itself does not select the look.
    for index,value in enumerate(header(key)):
        m.memory.write(JOB+12+index,value,1)
    for offset,value,size in ((0,0x8000,4),(4,0x607504f6,4),(8,PENDING,4),(44,0x9e01,2)):
        m.memory.write(RECORD+offset,value,size)
    reads={0x9f000068:[0],0x9f000078:[0],0x9f000070:[0x2000],0x9f00007c:[0x2000]}
    expected_status=0
    if scenario=='success_status':
        reads.update({0x9f009c24:[1],0x9f009c20:[1]})
    elif scenario=='error_status':
        reads.update({0x9f009c24:[2],0x9f009c20:[2]}); expected_status=0x9e01
    elif scenario=='masked':
        reads[0x9f00007c]=[0]
    elif scenario=='empty':
        reads[0x9f000070]=[0]
    elif scenario=='busy_record':
        m.memory.write(RECORD+47,0x20,1)
        reads.update({0x9f009c24:[1],0x9f009c20:[1]})
    elif scenario=='secondary_status':
        m.memory.write(RECORD+47,0x40,1)
        reads[0x9f000070]=[0,0x2000]; reads[0x9f00007c]=[0]
        reads.update({0x9f000084:[0x2000],0x9f009c24:[1],0x9f009c20:[1]})
    else:
        raise ValueError('undeclared interrupt scenario')
    replay=RegisterReplay(m.memory.regions,reads,
        (0x9f000068,0x9f000070,0x9f000078,0x9f00007c,0x9f000060,0x9f000084,0x9f00009c))
    m.memory=replay
    result=invoke(m,0x607491e9,0,0,{'d0':selector})
    assert result.get('pc')==RETURN and m.r['sp']==SP,result
    assert replay.exhausted()
    notification=scenario in ('success_status','error_status','secondary_status')
    assert signal.signalled==int(notification)
    if notification:
        assert m.memory.read(PENDING+32,2)==expected_status
        cleanup=invoke(m,0x6074edd9,0x70,28,{'a0':PENDING})
        assert cleanup.get('pc')==RETURN and m.r['d0']==expected_status and m.r['sp']==SP,cleanup
        assert not pool.allocated and not signal.signalled
        assert all(m.memory.read(PENDING+n,4)==0 for n in range(0,56,4))
    else:
        cleanup=None
        assert m.memory.read(PENDING,4)==JOB and pool.allocated==1
        assert not any(e.get('target')==0x607504f6 for e in m.events)
    output=next(r for r in m.memory.regions if r.address==OUTPUT)
    assert output.data==bytearray([0xcd])*64+bytearray([0xa5])*16
    return dict(key=hex(key),selector=selector,scenario=scenario,result=result,cleanup=cleanup,
        request_notification=notification,status=hex(expected_status) if notification else None,
        output_written=False,pixel_cycle=False,synthetic_register_reads=True,
        transactions=replay.transactions,events=m.events)


class TaskWake:
    name='declared-task-wakeup'
    def validate(self,m,mask,frame):
        if (mask,frame)!=(0,4) or m.r['d0']!=148:
            raise Fault('unexpected task wakeup ID/ABI')
    def apply(self,m):
        return dict(task_id=148,scheduler_executed=False)


def submission_case(image,code):
    m,_,_=machine(image,code)
    context,workspace=bytearray(204),bytearray(9596)
    struct.pack_into('<4I',context,0,0x8000,JOB+10440,SCRATCH,0)
    struct.pack_into('<2I',workspace,0,0x1001,0)
    struct.pack_into('<2I',next(r for r in m.memory.regions if r.address==JOB).data,
                     10440,0x607504f6,PENDING)
    context[201]=1
    m.memory=Memory([*m.memory.regions,Region(CONTEXT,context,True),Region(SCRATCH,workspace),
                     Region(RECORD,bytearray(48*9),True)])
    m.models[0x60449079]=TaskWake()
    result=invoke(m,0x607419ea,0xf0,28,{'a0':CONTEXT,'a1':JOB+10440,'d0':0,'d1':0x8000})
    assert result.get('pc')==RETURN and m.r['sp']==SP,result
    assert [m.memory.read(RECORD+o,4) for o in (0,4,8)]==[0x8000,0x607504f6,PENDING]
    assert m.memory.read(RECORD+47,1)==2
    assert [e.get('task_id') for e in m.events if e.get('model')=='declared-task-wakeup']==[148]
    return dict(result=result,events=m.events,record_header=['0x8000','0x607504f6',hex(PENDING)],
                hardware_started=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    if not __debug__ or args.out.exists() or not args.out.resolve().is_relative_to((ROOT/'local').resolve()):
        parser.error('assertions and a new ignored local directory required')
    image,code=load(); code=native_code(image,code)
    scenarios=('success_status','error_status','masked','empty','busy_record','secondary_status')
    rows=[replay_case(image,code,k,s,n) for k in RECIPES for s in (0,2) for n in scenarios]
    report=dict(model='Olympus E-PL9',displayed_version='1.1 (owner report)',main_build='1101',
        stock_bytes=104552480,stock_sha256=STOCK_SHA,main_bytes=len(image),main_sha256=MAIN_SHA,
        synthetic_register_replay=True,camera_accessed=False,firmware_modified=False,
        full_pixel_cycle_passed=False,cases=rows,submission=submission_case(image,code),
        descriptor_contract={'source_16_18':['area_width','area_height'],
                             'destination_16_18':['offset_h','offset_v']},
        source_sha256={name:hashlib.sha256((ROOT/'scripts'/name).read_bytes()).hexdigest() for name in
            ('epl9_hardware_audit.py','epl9_completion_audit.py','epl9_job_probe.py','mn103_subset.py','mn103_calls.py')})
    args.out.mkdir(parents=True)
    (args.out/'results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status_replays=len(rows),native_submission=True,full_pixel_cycle=False)))


if __name__=='__main__':
    main()
