"""Check the exact-stock ISEQ transaction connector without inventing its graph.

Inputs are declared staged packets. Only the existing assumed-byte-fill ROM
leaf is modeled. No graph results, queue success, worker, IRQ, executor or
hardware completion is supplied. This is not an RTOS or camera execution.
"""
import argparse
import json
from pathlib import Path

from epl9_workspace_bridge import ROOT, MAIN, MAIN_SHA, BASE, sha
from epl9_job_exclusion_audit import direct_candidates, literal_positions, decode_windows
from mn103_tooling import reader_provenance
from mn103_subset import Memory, Region
from mn103_calls import CallMachine
from mn103_models import FillModel

SP, END, STAGE = 0x10012000, 0x10000000, 0x20000000
ROWS, SEQUENCE, COUNT = 0xa2a5e3b8, 0x626882bc, 0x626882c0
RESULT_BYTES = 324
PACKET = (0x44,0x010000ab,1,0x21000000)
EXPECTED_REFERENCES = {0x609a6ac7:(0x609a6a99,),0x609a6bcc:(0x609a6b7d,),
    0x609a6c22:(0x609a6b97,),0x609a6ceb:(0x609a6c97,),
    0x609a9985:(0x609a6454,0x609a68e6,0x609a6d39)}
WINDOWS = ((0x609a69ed,0x609a6d7e),(0x609a6424,0x609a6496),
    (0x609a6835,0x609a69ed),(0x61770f5a,0x61770f7e))


def references(image,code):
    rows={}
    for target,expected in EXPECTED_REFERENCES.items():
        candidates=direct_candidates(image,BASE,target)
        if ([int(r['pc'],16) for r in candidates]!=list(expected) or
                any(r['op']!='call' for r in candidates) or literal_positions(image,BASE,target)):
            raise ValueError('ISEQ exact-image reference inventory differs: '+hex(target))
        for r in candidates:
            actual=code.get(int(r['pc'],16))
            if actual is None or actual[0].hex()!=r['raw'] or actual[1]!='call' or actual[2][0]!=hex(target):
                raise ValueError('ISEQ reference is not the expected containing-context instruction')
        rows[hex(target)]=candidates
    return rows


def fixture():
    # Payload 21000000 is deliberately unmapped: this connector only retains
    # its value. It must not be mistaken for a successfully constructed J.
    memory=Memory([
        Region(0x10010000,bytearray(b'\xa5'*16384),True,'declared poisoned stack'),
        Region(STAGE,bytearray(64),True,'declared staged packet'),
        Region(SEQUENCE,bytearray(8),True,'native token/count globals'),
        Region(ROWS,bytearray(800),True,'native forty transaction rows')])
    memory.write(SEQUENCE,1,4)
    return memory


def row_words(memory):
    return [[memory.read(ROWS+i*20+j*4,4) for j in range(5)] for i in range(40)]


def checked_transaction(row,allocate):
    """Fail closed; a zero return or unrelated interpreter fault is not success."""
    expected_calls=[dict(pc='0x609a6b97',target='0x609a6c22')]
    if allocate:
        expected_calls.insert(0,dict(pc='0x609a6b7d',target='0x609a6bcc'))
    if (row.get('stop')!={'status':'stop','pc':hex(END)} or row.get('return_value')!=0 or
            row.get('sp_after')!=hex(SP) or row.get('native_calls')!=expected_calls or
            row.get('result_list_count')!=0 or row.get('result_list_hex')!='00'*RESULT_BYTES or
            row.get('graph_result_supplied') is not False or
            row.get('executor_or_worker_entered') is not False or
            row.get('kernel_or_hardware_modeled') is not False):
        raise ValueError('ISEQ transaction evidence differs')
    fills=row.get('modeled_software_fills')
    if (not isinstance(fills,list) or len(fills)!=2 or
            [(e.get('target'),e.get('model'),e.get('start'),e.get('count'),e.get('byte')) for e in fills]!=[
                (0x4700111e,'assumed-byte-fill',hex(SP-356),16,0),
                (0x4700111e,'assumed-byte-fill',hex(SP-340),324,0)]):
        raise ValueError('ISEQ declared software-fill contract differs')
    return dict(status='bounded_connector_only',worker_dispatch_observed=False,
        job_reuse_proven=False,real_completion_observed=False)


def transaction(code,memory,kind):
    memory.write(STAGE+28,kind,2)
    machine=CallMachine(code,memory,dict(sp=SP,a0=STAGE),models={0x4700111e:FillModel()})
    reached=machine.run(machine.enter(0x609a6ac7,END,0xf0,16),[0x609a6c22])
    if reached.get('status')!='stop' or reached.get('pc')!=0x609a6c22:
        raise ValueError('ISEQ did not reach exact empty-list consumer: '+str(reached))
    pointer=machine.r['a0']
    if pointer!=SP-340:
        raise ValueError('ISEQ result-list stack alias differs')
    result_count=memory.read(pointer,2)
    result=bytes(memory.read(pointer+i,1) for i in range(RESULT_BYTES))
    stopped=machine.run(reached['pc'],[END])
    row=dict(stop={k:hex(v) if k=='pc' else v for k,v in stopped.items() if k in ('pc','status')},
        return_value=machine.r['d0'],sp_after=hex(machine.r['sp']),
        result_list_count=result_count,result_list_hex=result.hex(),
        native_calls=[dict(pc=hex(e['pc']),target=hex(e['target'])) for e in machine.events
            if e['op'] in ('call','calls')],
        modeled_software_fills=[e for e in machine.events if e['op']=='modeled_call'],
        native_instructions=len(machine.trace),graph_result_supplied=False,
        executor_or_worker_entered=any(p in machine.trace for p in
            (0x6074e6eb,0x609a649b,0x609a9985,0x609a6ceb)),
        kernel_or_hardware_modeled=False)
    row['validation']=checked_transaction(row,kind==0)
    return row


def native_controls(code):
    memory=fixture()
    for i,w in enumerate(PACKET):
        memory.write(STAGE+4*i,w,4)
    first=transaction(code,memory,0)
    if row_words(memory)!=[[1,*PACKET]]+[[0]*5 for _ in range(39)] or memory.read(SEQUENCE,4)!=2:
        raise ValueError('first ISEQ packet registration differs')
    second=transaction(code,memory,0)
    expected=[[1,*PACKET],[2,*PACKET]]+[[0]*5 for _ in range(38)]
    if row_words(memory)!=expected or memory.read(SEQUENCE,4)!=3:
        raise ValueError('duplicate ISEQ packet registration differs')
    # A declared kind2 staged reply, not a native worker/hardware completion.
    for off in range(32):
        memory.write(STAGE+off,0,1)
    memory.write(STAGE+16,0,2)
    memory.write(STAGE+20,PACKET[1],4)
    memory.write(STAGE+24,0x22000000,4)
    reply=transaction(code,memory,2)
    if row_words(memory)!=expected or memory.read(SEQUENCE,4)!=3:
        raise ValueError('empty-list staged reply unexpectedly progressed/released rows')
    memory=fixture()
    for i,w in enumerate(PACKET):
        memory.write(STAGE+4*i,w,4)
    continuation=transaction(code,memory,1)
    if row_words(memory)!=[[0]*5 for _ in range(40)] or memory.read(SEQUENCE,4)!=1:
        raise ValueError('kind1 ISEQ connector unexpectedly allocated a row')
    return dict(duplicate_payload=dict(first=first,second=second,retained_rows=expected[:2],
            next_token=3,payload_unmapped=True,job_identity_or_reuse_proven=False),
        declared_kind2_reply=dict(execution=reply,rows_unchanged=True,real_completion_observed=False),
        kind1=dict(execution=continuation,rows_allocated=0))


def run(out):
    out=out.resolve()
    if out.exists() or not out.is_relative_to((ROOT/'local').resolve()):
        raise ValueError('use a new ignored local output directory')
    image=MAIN.read_bytes()
    if sha(image)!=MAIN_SHA:
        raise ValueError('exact E-PL9 1101 main required')
    reader=reader_provenance()
    out.mkdir(parents=True)
    code=decode_windows(image,out,WINDOWS)
    refs=references(image,code)
    controls=native_controls(code)
    result=dict(main_sha256=sha(image),main_bytes=len(image),reader=reader,
        references=refs,controls=controls,source_sha256=sha(Path(__file__).read_bytes()),
        execution_source_sha256={p:sha((ROOT/'scripts'/p).read_bytes()) for p in
            ('mn103_subset.py','mn103_calls.py','mn103_models.py','mn103_tooling.py',
             'epl9_job_exclusion_audit.py')},
        scheduler_executed=False,kernel_executed=False,irq_executed=False,
        graph_result_supplied=False,actual_same_job_overlap_observed=False,
        same_job_exclusion_proven=False,firmware_modified=False,camera_accessed=False,install_ready=False)
    (out/'iseq-protocol.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    if not __debug__:
        raise SystemExit('run with assertions enabled')
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args()
    run(args.out)
    print(json.dumps(dict(empty_result_connector_confirmed=True,
        worker_dispatch_observed=False,job_reuse_proven=False,install_ready=False),indent=2))
