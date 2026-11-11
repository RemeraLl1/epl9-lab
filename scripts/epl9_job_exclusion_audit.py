"""Read-only native job ownership evidence, not an RTOS exclusion proof.

Direct-reference scanning is deliberately a byte-candidate inventory. Native
callback controls use declared owner/task state with logging output disabled.
No scheduler, IRQ, hardware success, processing output or lock is supplied.
"""
import argparse
import json
from pathlib import Path
import struct
import subprocess

from epl9_workspace_bridge import ROOT, MAIN, MAIN_SHA, BASE, sha
from epl9_owner_callback_probe import (load_owners, fixture, CALLBACKS,
    CONTEXT, COEFFICIENTS, SP, END)
from mn103_tooling import default_reader, reader_provenance
from mn103_subset import Memory, Region, parse_listing
from mn103_calls import CallMachine

EXECUTOR = 0x6074e6eb
EXPECTED_CALLS = (0x6071bbda,0x6074e923,0x6074e970,0x607cd705,
    0x607ce63f,0x609a64bc,0x609a8e82,0x61028f7f)
CALL_CONTEXTS = ((0x6071bb87,0x6071bc29),(0x6074e7ca,0x6074e97d),
    (0x607ccf26,0x607cd7e4),(0x607ce5ae,0x607ce6b8),
    (0x609a6496,0x609a6539),(0x609a8e3f,0x609a8ed3),(0x61028f22,0x61028ffb))
ALIAS_WINDOWS = ((0x607ce1b5,0x607ce1cc),(0x607d9cb8,0x607d9ccd),
    (0x607cf0a1,0x607cf0ad),(0x607d9d59,0x607d9d62),
    (0x607ce6e1,0x607ce6ec),(0x6074e341,0x6074e348),
    (0x607ce634,0x607ce63f),(0x607cf028,0x607cf02c))
CALLBACK_WINDOWS = ((0x607d004d,0x607d01db),(0x607d4ece,0x607d4f38))


def direct_candidates(image, base, target):
    """Find six relative CALL/CALLS/JMP encoding forms, not code reachability."""
    rows=[]
    for prefix,width,trailer,op in ((b'\xcd',2,2,'call'),(b'\xdd',4,2,'call'),
            (b'\xcc',2,0,'jmp'),(b'\xdc',4,0,'jmp'),
            (b'\xfa\xff',2,0,'calls'),(b'\xfc\xff',4,0,'calls')):
        start=0
        while True:
            offset=image.find(prefix,start)
            if offset<0:
                break
            start=offset+1
            size=len(prefix)+width+trailer
            if offset+size>len(image):
                continue
            displacement=int.from_bytes(image[offset+len(prefix):offset+len(prefix)+width],'little',signed=True)
            if (base+offset+displacement)&0xffffffff==target:
                rows.append(dict(pc=hex(base+offset),op=op,
                    raw=image[offset:offset+size].hex()))
    return sorted(rows,key=lambda r:int(r['pc'],16))


def literal_positions(image, base, value):
    rows=[];start=0;pattern=struct.pack('<I',value)
    while True:
        at=image.find(pattern,start)
        if at<0:
            return rows
        rows.append(hex(base+at));start=at+1


def inventory(image):
    rows=direct_candidates(image,BASE,EXECUTOR)
    if [int(r['pc'],16) for r in rows]!=list(EXPECTED_CALLS) or any(r['op']!='call' for r in rows):
        raise ValueError('native executor reference inventory differs')
    literals=literal_positions(image,BASE,EXECUTOR)
    if literals:
        raise ValueError('native executor literal inventory differs')
    return dict(relative_byte_candidates=rows,executor_literal_positions=literals,
        complete_call_graph_proven=False,
        computed_indirect_targets_excluded=False,
        scope='Exact byte inventory; not exhaustive executable call graph or same-job alias proof')


def decode_windows(image,out,windows):
    code={}
    for a,b in windows:
        listing=subprocess.check_output([str(default_reader()),str(MAIN),hex(BASE),
            hex(a-BASE),hex(b-BASE)],text=True)
        (out/f'{a:08x}-{b:08x}.tsv').write_text(listing)
        code.update(parse_listing(listing,image,BASE))
    return code


def alias_controls(image,out):
    """Execute actual stack/publish/reload fragments with synthetic addresses.

    Calls at boundaries are not executed. Fresh declared objects are not a
    real allocator, task instantiation, complete lifecycle or scheduler.
    """
    code=decode_windows(image,out,ALIAS_WINDOWS)
    sp,owner,job=0x10012000,0x20000000,0x21000000
    rows=[]
    def machine(regs=None):
        return CallMachine(code,Memory([
            Region(0x10010000,bytearray(16384),True,'declared stack'),
            Region(owner,bytearray(4096),True,'declared owner'),
            Region(job,bytearray(14552),True,'declared native-sized job')]),
            dict(sp=sp,**(regs or {})))
    def checked(name,m,start,stop,registers,memory=()):
        result=m.run(start,[stop])
        if (result.get('status')!='stop' or result.get('pc')!=stop or m.events or m.models or
                any(m.r[k]!=v for k,v in registers.items()) or
                any(m.memory.read(a,size)!=v for a,size,v in memory)):
            raise ValueError('native owner alias differs: '+name+': '+str(result))
        rows.append(dict(name=name,start=hex(start),stop_before_instruction=hex(stop),
            native_instructions=len(m.trace),registers={k:hex(m.r[k]) for k in registers},
            checked_memory=[dict(address=hex(a),size=size,value=hex(v)) for a,size,v in memory],
            external_calls_executed=False,modeled_calls=0))
    checked('primary stack owner',machine(),0x607ce1b5,0x607ce1cc,
        dict(sp=sp-372,a3=sp-372+16,d2=sp-372+300))
    checked('wrapper stack owner',machine(),0x607d9cb8,0x607d9ccd,
        dict(sp=sp-360,a3=sp-360+28,a2=sp-360+42),[(sp-360+16,4,sp-360+312)])
    checked('primary publish',machine(dict(a3=owner,d0=job)),0x607cf0a1,0x607cf0ad,
        dict(a0=owner),[(owner+156,4,job)])
    checked('wrapper publish',machine(dict(a3=sp+28,a2=sp+42,d0=job)),
        0x607d9d59,0x607d9d62,dict(a0=sp+28),[(sp+184,4,job)])
    m=machine();m.memory.write(sp+28,owner,4);m.memory.write(owner+156,job,4)
    checked('preparation reload',m,0x607ce6e1,0x607ce6ec,dict(d0=job))
    checked('descriptor alias',machine(dict(d0=job)),0x6074e341,0x6074e345,dict(a0=job+36))
    m=machine(dict(a2=owner));m.memory.write(owner+156,job,4)
    checked('executor arguments',m,0x607ce634,0x607ce63f,dict(d0=job,d1=65535,a3=owner+156))
    m=machine(dict(a3=owner));m.memory.write(owner+156,job,4)
    checked('destructor argument',m,0x607cf028,0x607cf02c,dict(d0=job))
    return rows


def context_decodes(image,out,rows):
    code=decode_windows(image,out,CALL_CONTEXTS)
    for row in rows:
        pc=int(row['pc'],16)
        instruction=code.get(pc)
        if (instruction is None or instruction[0].hex()!=row['raw'] or
                instruction[1]!='call' or instruction[2][0]!=hex(EXECUTOR)):
            raise ValueError('candidate is not the expected containing-context instruction')
        row['containing_context_decode_confirmed']=True
    return rows


def callback_controls(image,out):
    code=load_owners(image,out)
    code.update(decode_windows(image,out,CALLBACK_WINDOWS))
    rows=[]
    # 100c is a contrasting branch, not another admitted film operation.
    for operation in (0x1003,0x100c):
        state=fixture(ready=1,phase=16)
        struct.pack_into('<H',state['context'],72,operation)
        before_context=bytes(state['context']);before_object=bytes(state['object'])
        m=CallMachine(code,Memory([Region(BASE,image),*state['regions'],
            Region(COEFFICIENTS,bytes(8)),Region(SP-8192,bytearray(16384),True)]),
            dict(sp=SP,d0=16,a0=COEFFICIENTS,a1=CONTEXT))
        stops=[END] if operation==0x1003 else [0x607d0067]
        result=m.run(m.enter(CALLBACKS['primary'],END),stops)
        expected=END if operation==0x1003 else 0x607d0067
        if result.get('status')!='stop' or result.get('pc')!=expected:
            raise ValueError('event16 stopped at an unexpected boundary: '+str(result))
        if (any(e['op']=='modeled_call' for e in m.events) or
                any(pc in (EXECUTOR,0x6074e765,0x6079fb88,0x607d00f2) for pc in m.trace) or
                state['context']!=before_context or state['object']!=before_object):
            raise ValueError('event16 control changed storage or reentered execution')
        if operation==0x1003:
            if m.r['sp']!=SP or m.r['d0']!=1 or 0x607d4ece not in m.trace or 0x607d0067 in m.trace:
                raise ValueError('ART1003 event16 predicate/return differs')
        rows.append(dict(operation=hex(operation),event=16,result=result,
            return_value=m.r['d0'] if operation==0x1003 else None,
            native_calls=[dict(pc=hex(e['pc']),target=hex(e['target'])) for e in m.events
                if e['op'] in ('call','calls')],
            owner_storage_unchanged=True,modeled_calls=0,
            callback_completed=operation==0x1003,
            same_job_exclusion_proven=False))
    return rows


def run(out):
    out=out.resolve()
    if out.exists() or not out.is_relative_to((ROOT/'local').resolve()):
        raise ValueError('use a new ignored local output directory')
    image=MAIN.read_bytes()
    if sha(image)!=MAIN_SHA:
        raise ValueError('exact E-PL9 1101 decoded main required')
    provenance=reader_provenance()
    references=inventory(image)
    out.mkdir(parents=True)
    context_decodes(image,out,references['relative_byte_candidates'])
    callbacks=callback_controls(image,out)
    aliases=alias_controls(image,out)
    result=dict(main_sha256=sha(image),main_bytes=len(image),analysis_base=hex(BASE),
        reader=provenance,references=references,event16_controls=callbacks,owner_alias_controls=aliases,
        source_sha256=sha(Path(__file__).read_bytes()),
        native_execution_sources={p:sha((ROOT/'scripts'/p).read_bytes()) for p in
            ('mn103_subset.py','mn103_calls.py','epl9_owner_callback_probe.py','mn103_tooling.py')},
        scheduler_executed=False,irq_executed=False,camera_accessed=False,
        same_job_exclusion_proven=False,firmware_guard_added=False,install_ready=False)
    (out/'job-exclusion.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    if not __debug__:
        raise SystemExit('run with assertions enabled')
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args()
    r=run(args.out)
    print(json.dumps(dict(direct_candidates=len(r['references']['relative_byte_candidates']),
        owner_alias_controls=len(r['owner_alias_controls']),
        art_event16_no_synchronous_reentry=True,
        same_job_exclusion_proven=False,firmware_guard_added=False,install_ready=False),indent=2))
