"""Re-enter native ART work on independent live native-source snapshots.

This is an adversarial same-job overlap control, not an RTOS schedule or camera
race observation. RAM/models are cloned together; no completion, hardware
success or output pixels are supplied. The historical reentry probe is intact.
"""
import argparse
import copy
import hashlib
import json
import pickle
import struct
from pathlib import Path

from epl9_workspace_bridge import ROOT, MAIN, BASE, sha
from epl9_film_late_probe import prepare_probe
from epl9_film_late_module import build_late_module
from epl9_classified_branch_probe import (SEPARATE_MAIN_SHA, CLASSIFIED_WINDOWS,
    extend_code, source_fields, checked_inputs)
from epl9_native_source_probe import Observe, CHECKPOINTS, FIELDS, STOP, checked_classified_prefix
from epl9_owner_binding_probe import load_owners, load_factories, create_parameters, BoundOwner
from epl9_owner_callback_probe import CALLBACKS, CONTEXT
from epl9_job_probe import (experiment, JOB, CACHE, STACK, RETURN, SOURCE, OUTPUT,
    OWNER_CALLBACK, resume)
from epl9_deployment_probe import Registers
from epl9_wb_math_probe import extend
from epl9_wb_extension import adjusted
from epl9_v3_package import PRIVATE_CANDIDATE_HASHES, CANDIDATE_HASHES
from mn103_tooling import verify_reader, reader_provenance
from mn103_calls import CallMachine
from mn103_subset import Memory, Fault

SITES = {0x60761ca4: 'gain_return', 0x6074f11c: 'submission', 0x6079fb88: 'COLOR'}
REENTRY_SP = STACK + 8192
REQUEST, REQUEST_BYTES = JOB + 10440, 1876


def blob(memory, address, size):
    region, offset = memory.region(address, 1)
    if offset+size > len(region.data):
        raise ValueError('snapshot exceeds a single declared region')
    return bytes(region.data[offset:offset+size])


def differences(before, after):
    """All changed bytes as contiguous spans, without discarding trailing data."""
    if len(before) != len(after):
        raise ValueError('different-sized snapshot')
    rows=[]
    for i, (a,b) in enumerate(zip(before,after)):
        if a != b:
            if not rows or rows[-1][1] != i:
                rows.append([i,i+1])
            else:
                rows[-1][1] += 1
    return [dict(offset=a,length=b-a,before=before[a:b].hex(),after=after[a:b].hex())
            for a,b in rows]


def state_digest(machine):
    """Parent bytes and model state, including alias-dependent owner state."""
    digest=hashlib.sha256()
    for region in machine.memory.regions:
        digest.update(struct.pack('<IIB',region.address,len(region.data),region.writable))
        digest.update(region.data)
    digest.update(pickle.dumps(machine.models,protocol=5))
    return digest.hexdigest()


def clone_state(parent):
    # One deepcopy memo is essential: BoundOwner.state and Memory must refer to
    # the same cloned arrays, and all token/consumer adapters share resources.
    memory, models=copy.deepcopy((parent.memory,parent.models))
    child=CallMachine(parent.code,memory,
        dict(sp=REENTRY_SP,d0=JOB,d1=memory.read(JOB+10390,2)),models=models)
    child.r=Registers(child.r)
    return child


def fields(machine):
    return dict(cursor=machine.memory.read(JOB+10388,2),
        count=machine.memory.read(JOB+10390,2),error=machine.memory.read(JOB+10392,2),
        cancelled=machine.memory.read(JOB+10394,2),
        request_fields={str(o):machine.memory.read(REQUEST+o,s) for o,s in FIELDS.items()},
        source_gains=[machine.memory.read(JOB+10406+2*i,2) for i in range(4)],
        request_gains=[machine.memory.read(REQUEST+1568+2*i,2) for i in range(4)],
        classifier_flags=[machine.memory.read(JOB+o,1) for o in (10414,10415,10416)],
        pending=blob(machine.memory,JOB+13640,56).hex(),
        gamma_pointers=[hex(machine.memory.read(CACHE+2596+4*i,4)) for i in range(3)])


def resource_state(child):
    owner=child.models[OWNER_CALLBACK]
    return dict(buffers=copy.deepcopy(owner.buffers),released_buffers=sorted(owner.released_buffers),
        descriptor_refs={hex(k):v for k,v in owner.descriptor_refs.items()},
        event_bits_allocated=child.models[0x6074aea9].allocated,
        event_bits_signalled=child.models[0x6074af2c].signalled,
        consumer_id_live=child.models[0x607490c8].used,
        workspace_live=child.models[0x607a038d].used,
        locks={hex(k):child.models[k].held for k in (0x607a17b7,0x607a1841)})


def run_clone(parent, site, owner_name, module):
    if parent.r['sp'] <= REENTRY_SP+32:
        raise ValueError('private cloned caller would overlap live outer stack')
    digest=state_digest(parent)
    child=clone_state(parent)
    adapter=child.models[CALLBACKS[owner_name]]
    if adapter.previous is not child.models[OWNER_CALLBACK]:
        raise ValueError('cloned native owner/resource alias lost')
    # Do not depend on region ordering in the fixture: verify each writable
    # owner array by address and identity, not merely equal bytes.
    for region in adapter.state['regions']:
        if region.address == 0x8050:
            continue
        mapped,_=child.memory.region(region.address,1)
        if mapped.data is not region.data:
            raise ValueError('cloned owner RAM/model alias lost')
    before=fields(child)
    outer_stack=blob(parent.memory,parent.r['sp'],STACK+16384-parent.r['sp'])
    before_request=blob(child.memory,REQUEST,REQUEST_BYTES)
    before_job=blob(child.memory,JOB,16384)
    before_cache=blob(child.memory,CACHE,5764)
    before_resources=resource_state(child)
    checkpoints=[];gain_writes=[];request_writes=[];source_reads=[]
    work_targets={parent.memory.read(JOB+10060+i*12,4) for i in range(before['count'])}
    class Trace(list):
        def append(self,pc):
            if pc in CHECKPOINTS:
                checkpoints.append(dict(pc=hex(pc),phase=CHECKPOINTS[pc],index=len(self),**fields(child)))
            super().append(pc)
    child.trace=Trace()
    read,write=child.read,child.write
    def observed_read(operand,size=4):
        if operand.startswith('(') and SOURCE<=child.address(operand)<SOURCE+32*1024*1024:
            source_reads.append(dict(pc=hex(child.trace[-1]),address=hex(child.address(operand)),size=size))
        return read(operand,size)
    def observed_write(operand,value,size=4):
        if operand.startswith('(') and REQUEST<=child.address(operand)<REQUEST+REQUEST_BYTES:
            address=child.address(operand)
            request_writes.append(dict(pc=hex(child.trace[-1]),offset=address-REQUEST,size=size,
                before=child.memory.read(address,size),after=value & ((1<<(8*size))-1)))
        if operand.startswith('(') and REQUEST+1568<=child.address(operand)<REQUEST+1576:
            address=child.address(operand)
            gain_writes.append(dict(pc=hex(child.trace[-1]),offset=address-REQUEST,size=size,
                before=child.memory.read(address,size),after=value & ((1<<(8*size))-1)))
        return write(operand,value,size)
    child.read,child.write=observed_read,observed_write
    start=child.enter(0x6074e6eb,RETURN,0xf0,32)
    try:
        result=child.run(start,[RETURN],limit=500000)
    except Fault as error:
        result=dict(status='fault',error=str(error))
    result.update(instructions=len(child.trace),last_instructions=[hex(p) for p in child.trace[-16:]],
        registers={k:hex(v) for k,v in child.r.items()})
    after=fields(child)
    request_changes=differences(before_request,blob(child.memory,REQUEST,REQUEST_BYTES))
    buffers=[]
    for allocation in child.models[OWNER_CALLBACK].buffers:
        region,_=child.memory.region(allocation['address'],1)
        size=allocation['size']
        buffers.append(dict(**allocation,payload_changed=region.data[:size].count(0xcd)!=size,
            canary_intact=region.data[size:]==b'\xa5'*16))
    output=next(r for r in child.memory.regions if r.address==OUTPUT)
    parent_unchanged=state_digest(parent)==digest
    if not parent_unchanged:
        raise ValueError('clone mutated outer RAM/models')
    dispatches=[dict(pc=hex(e['pc']),target=hex(e['target'])) for e in child.events
                if e['op'] in ('call','calls') and e['target'] in work_targets]
    row=dict(site=SITES[site],pc=hex(site),outer_instruction=len(parent.trace),
        outer_sp=hex(parent.r['sp']),synthetic_reentry_sp=hex(REENTRY_SP),
        before=before,after=after,executor=result,
        repeated_work_dispatches=dispatches,checkpoints=checkpoints,gain_writes=gain_writes,
        request_writes=request_writes,events=child.events,
        request_unchanged=not request_changes,request_changes=request_changes,
        job_changes=differences(before_job,blob(child.memory,JOB,16384)),
        cache_changes=differences(before_cache,blob(child.memory,CACHE,5764)),
        resources_before=before_resources,resources_after=resource_state(child),buffers=buffers,
        modeled_calls=[dict(target=hex(e['target']),pc=hex(e['pc']),model=e['model'])
                       for e in child.events if e['op']=='modeled_call'],
        source_pixel_reads=source_reads,output_changed=output.data.count(0xcd)!=len(output.data),
        event_bits_signalled=child.models[0x6074af2c].signalled,
        parent_ram_and_models_unchanged=True,memory_and_model_aliases_preserved=True,
        same_job_overlap_negative_control=True,camera_schedule_observed=False,
        whole_job_completed=False)
    if blob(child.memory,parent.r['sp'],STACK+16384-parent.r['sp'])!=outer_stack:
        raise ValueError('reentry caller overwrote the suspended outer stack')
    row['outer_live_stack_unchanged']=True
    # Resume actual saved native state, not a second synthetic executor call.
    # Baseline and overlapped continuations both remain bounded by the same
    # existing contracts; reaching hardware is not completing it.
    control=clone_state(parent)
    baseline=continue_outer(parent,control.memory,control.models,site)
    overlap=continue_outer(parent,child.memory,child.models,site)
    row['baseline_continuation']=baseline['report']
    row['overlap_continuation']=overlap['report']
    row['overlap_continuation']['cache_unchanged_from_snapshot']=(
        blob(overlap['machine'].memory,CACHE,5764)==before_cache)
    row['continued_request_changes_vs_baseline']=differences(
        blob(baseline['machine'].memory,REQUEST,REQUEST_BYTES),
        blob(overlap['machine'].memory,REQUEST,REQUEST_BYTES))
    row['continued_cache_changes_vs_baseline']=differences(
        blob(baseline['machine'].memory,CACHE,5764),
        blob(overlap['machine'].memory,CACHE,5764))
    if state_digest(parent)!=digest:
        raise ValueError('continuation changed outer RAM/models')
    return row


def continue_outer(parent,memory,models,site):
    machine=CallMachine(parent.code,memory,dict(parent.r),models=models)
    machine.r=Registers(machine.r)
    machine.loop=copy.deepcopy(parent.loop)
    for flag in ('n','z','c','v'):
        setattr(machine,flag,getattr(parent,flag))
    source_reads=[]
    read=machine.read
    def watched_read(operand,size=4):
        if operand.startswith('(') and SOURCE<=machine.address(operand)<SOURCE+32*1024*1024:
            source_reads.append(dict(pc=hex(machine.trace[-1]),address=hex(machine.address(operand)),size=size))
        return read(operand,size)
    machine.read=watched_read
    result=resume(machine,site)
    output=next(r for r in machine.memory.regions if r.address==OUTPUT)
    buffers=[]
    for allocation in machine.models[OWNER_CALLBACK].buffers:
        region,_=machine.memory.region(allocation['address'],1)
        size=allocation['size']
        buffers.append(dict(**allocation,payload_changed=region.data[:size].count(0xcd)!=size,
            canary_intact=region.data[size:]==b'\xa5'*16))
    report=dict(executor=result,fields=fields(machine),resources=resource_state(machine),events=machine.events,
        output_changed=output.data.count(0xcd)!=len(output.data),source_pixel_reads=source_reads,
        event_bits_signalled=machine.models[0x6074af2c].signalled,buffers=buffers,
        modeled_calls=[dict(target=hex(e['target']),pc=hex(e['pc']),model=e['model'])
                       for e in machine.events if e['op']=='modeled_call'])
    return dict(report=report,machine=machine)


CAPACITY_ERROR='owner buffer request exceeds declared fixture capacity'
EXPECTED_REQUEST_CHANGES=[
    dict(offset=279,length=1,before='00',after='16'),
    dict(offset=284,length=2,before='0000',after='0203'),
    dict(offset=287,length=1,before='00',after='12'),
    dict(offset=289,length=3,before='000000',after='12800d')]


EXPECTED_CONTINUED_REQUEST_CHANGES = [{'offset': 4, 'length': 2, 'before': '4835', 'after': '0000'},
 {'offset': 7, 'length': 1, 'before': '11', 'after': '00'},
 {'offset': 1199,
  'length': 13,
  'before': '23a5a5a5a5050570026302d301',
  'after': '00000000000000000000000000'},
 {'offset': 1216,
  'length': 36,
  'before': 'a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5',
  'after': '000000000000000000000000000000000000000000000000000000000000000000000000'},
 {'offset': 1255, 'length': 1, 'before': '36', 'after': '00'},
 {'offset': 1260, 'length': 8, 'before': '0403c0098c094c07', 'after': '0000000000000000'},
 {'offset': 1311, 'length': 1, 'before': '39', 'after': '00'},
 {'offset': 1316, 'length': 2, 'before': '0403', 'after': '0000'},
 {'offset': 1319, 'length': 5, 'before': '05c604a603', 'after': '0000000000'},
 {'offset': 1367, 'length': 1, 'before': '3c', 'after': '00'},
 {'offset': 1372, 'length': 8, 'before': '040380026302d301', 'after': '0000000000000000'},
 {'offset': 1640, 'length': 3, 'before': '010103', 'after': '000000'}]
EXPECTED_LATE_JOB_CHANGES = [{'offset': 6292, 'length': 2, 'before': '0000', 'after': '0203'},
 {'offset': 6295, 'length': 1, 'before': '00', 'after': '12'},
 {'offset': 6297, 'length': 3, 'before': '000000', 'after': '12800d'},
 {'offset': 6301, 'length': 3, 'before': '000000', 'after': '12800d'},
 {'offset': 6309, 'length': 3, 'before': '000000', 'after': '09c006'},
 {'offset': 6358, 'length': 2, 'before': '0000', 'after': 'e601'},
 {'offset': 6361, 'length': 1, 'before': '00', 'after': '10'}]


def checked_reentry(row,expected_gains,expected_gamma):
    """Reject arbitrary faults, incomplete controls and invented completion."""
    def require(condition,message):
        if not condition:
            raise ValueError('native-source reentry: '+message)
    def safe(item):
        require(item.get('output_changed') is False and item.get('source_pixel_reads')==[] and
            item.get('event_bits_signalled')==0,'pixels/source/completion failed or missing')
        require(bool(item.get('buffers')) and all(b.get('payload_changed') is False and
            b.get('canary_intact') is True for b in item['buffers']),'buffer poison/guard failed or missing')
    def stop(item,error,pc):
        result=item.get('executor',{})
        require(result.get('status')=='fault' and result.get('error')==error and
            result.get('last_instructions',[])[-1:]==[hex(pc)],'unexpected exact stop')
        if error==CAPACITY_ERROR:
            last=item.get('events',[])[-1:]
            require(bool(last) and last[0].get('op')=='call' and last[0].get('pc')==0x6074a8bb and
                last[0].get('target')==0x6073eab3,'capacity native requester differs')
        else:
            require(result.get('registers',{}).get('d0')=='0x800','hardware write value differs')
    require(row.get('site') in SITES.values(),'unknown snapshot site')
    safe(row);stop(row,CAPACITY_ERROR,0x6073eac3)
    require(row.get('repeated_work_dispatches')==[dict(pc='0x6074e765',target='0x60751319')],
        'did not execute exactly one repeated native work callback')
    require(all(row.get(k) is True for k in ('parent_ram_and_models_unchanged',
        'memory_and_model_aliases_preserved','outer_live_stack_unchanged')),'clone/stack isolation failed')
    for side in ('before','after'):
        state=row.get(side,{})
        require(state.get('source_gains')==[1024]*4 and
            state.get('request_gains')==list(expected_gains),'source/request gains differ')
        require(state.get('request_fields')=={'14':0x1000,'28':0x107,'48':3,'1832':0},
            'source/kind/selector differs')
        require((state.get('cursor'),state.get('count'),state.get('error'),state.get('cancelled'))==
            (1,2,0,0),'cursor/count/error/cancelled differs')
        require(state.get('classifier_flags')==[1,0,0],'native classifier flags differ')
    expected_pending=(struct.pack('<5I',JOB,0,REQUEST,0x8000,1)+bytes(36)).hex() if row['site']=='COLOR' else '00'*56
    require(row['before'].get('pending')==row['after'].get('pending')==expected_pending,
        'pending record changed or differs')
    require(row.get('cache_changes')==[],'reentry changed native cache before resource stop')
    phases={}
    for point in row.get('checkpoints',[]):
        phases.setdefault(point['phase'],[]).append(point)
    if row['site']=='gain_return':
        for phase in ('old_constructor_site','gain_entry','gain_return'):
            require(len(phases.get(phase,[]))==1,'missing/duplicate reconstructed gain phase')
        require(phases['old_constructor_site'][0]['request_gains']==[1024]*4 and
            phases['gain_entry'][0]['request_gains']==[1024]*4 and
            phases['gain_return'][0]['request_gains']==list(expected_gains),
            'rebuilt request did not restart from source gains')
        require(row.get('request_changes')==EXPECTED_REQUEST_CHANGES and
            row.get('request_unchanged') is False,'unfinished request changes differ')
        before_ids=[b['id'] for b in row['resources_before']['buffers']]
        after_ids=[b['id'] for b in row['resources_after']['buffers']]
        require(before_ids==[0x1000] and after_ids==[0x1000,0x1000,7,8,10,11,12],
            'duplicate output allocation pattern differs')
    else:
        require(not phases and not row.get('gain_writes') and row.get('request_changes')==[] and
            row.get('request_unchanged') is True,'late reentry unexpectedly rebuilt/touched request')
        require(row['resources_before']==row['resources_after'],'late reentry resource accounting changed')
        require(row.get('job_changes')==EXPECTED_LATE_JOB_CHANGES,
            'next unused native buffer-row changes differ')
    baseline=row.get('baseline_continuation',{});overlap=row.get('overlap_continuation',{})
    for item in (baseline,overlap):
        safe(item)
        require(item.get('fields',{}).get('request_gains')==list(expected_gains),
            'continuation gain accumulation or missing gains')
    stop(baseline,STOP,0x6073eafa)
    require(baseline.get('fields',{}).get('gamma_pointers')==expected_gamma,
        'baseline continuation gamma differs')
    if row['site']=='gain_return':
        stop(overlap,CAPACITY_ERROR,0x6073eac3)
        require(row.get('continued_request_changes_vs_baseline')==EXPECTED_CONTINUED_REQUEST_CHANGES,
            'interrupted-prefix request bytes differ')
        require(overlap.get('cache_unchanged_from_snapshot') is True and
            overlap.get('fields',{}).get('gamma_pointers')==['0x0']*3 and
            bool(row.get('continued_cache_changes_vs_baseline')),'lost unfinished native cache control')
    else:
        stop(overlap,STOP,0x6073eafa)
        require(overlap.get('fields',{}).get('gamma_pointers')==expected_gamma and
            row.get('continued_request_changes_vs_baseline')==[] and
            row.get('continued_cache_changes_vs_baseline')==[],'late continuation differs')
    return dict(status='incomplete',repeated_native_work_callback=True,
        wb_accumulation_observed=False,request_reconstructed=row['site']=='gain_return',
        original_prefix_disrupted_under_finite_capacity=row['site']=='gain_return',
        camera_schedule_observed=False,whole_job_completed=False)


class ReentrySnapshots:
    def __init__(self,meter,owner_name,module):
        self.meter,self.owner_name,self.module=meter,owner_name,module
        self.rows=[];self.seen=set()
    def __call__(self,m):
        self.meter(m)
        observer=self
        class Trace(type(m.trace)):
            def append(self,pc):
                if pc in SITES and pc not in observer.seen:
                    observer.seen.add(pc)
                    row=run_clone(m,pc,observer.owner_name,observer.module)
                    observer.rows.append(row)
                    print(json.dumps(dict(owner=observer.owner_name,site=SITES[pc],
                        gains_before=row['before']['request_gains'],gains_after=row['after']['request_gains'],
                        repeated_callbacks=len(row['repeated_work_dispatches']),stop=row['executor'].get('error',row['executor'].get('pc')))),flush=True)
                super().append(pc)
        m.trace=Trace(m.trace)


def audit(out,rgb_path,wb_path):
    if out.exists() or not out.resolve().is_relative_to((ROOT/'local').resolve()):
        raise ValueError('new ignored local output required')
    out.mkdir()
    rgb=json.loads(rgb_path.read_text());wb=json.loads(wb_path.read_text())
    opts=dict(base=0x604a1300,rgb_document=rgb,wb_document=wb)
    image,patched,_,code,module,manifest=prepare_probe(out/'module',**opts,
        private_color=True,native_source_gate=True)
    if sha(patched)!=SEPARATE_MAIN_SHA:
        raise ValueError('separate variant identity differs')
    baseline_hashes={}
    for private,expected in ((False,CANDIDATE_HASHES[0x100]),(True,PRIVATE_CANDIDATE_HASHES[0x100])):
        baseline=build_late_module(image,**opts,private_color=private)
        main=bytearray(image)
        main[baseline['base']-BASE:baseline['base']-BASE+len(baseline['data'])]=baseline['data']
        for patch in baseline['patches']:
            at=patch['address']-BASE;raw=bytes.fromhex(patch['after']);main[at:at+len(raw)]=raw
        if sha(main)!=expected or baseline['data'][4096:]!=module['data'][4096:]:
            raise ValueError('frozen identity/recipe bytes changed')
        baseline_hashes['private' if private else 'frozen']=sha(main)
    extend(image,code);extend_code(image,code,out,CLASSIFIED_WINDOWS)
    owner_code=load_owners(image,out);producer_code={**owner_code,**load_factories(image,out)}
    descriptor,tail,provenance=source_fields(image,out,2560)
    rows=[]
    for owner in ('primary','primary_wrapper'):
        for variant in (1,2):
            key=0x01000078+(variant<<16)
            params,state,producer=create_parameters(image,producer_code,owner,variant,sv_fixture=2560)
            if struct.unpack_from('<H',state['context'],280)[0]!=2560:
                raise ValueError('bound owner/source Sv disagree')
            meter=Observe(descriptor,0);meter.descriptor_tail=tail
            snapshots=ReentrySnapshots(meter,owner,module)
            def attach(m):
                snapshots(m)
                m.memory=Memory([*m.memory.regions,*[r for r in state['regions'] if r.address!=0x8050]])
                m.models[OWNER_CALLBACK].source_bounds=(4640,3472)
                m.models[CALLBACKS[owner]]=BoundOwner(m.models[OWNER_CALLBACK],owner_code,CALLBACKS[owner],state)
            case=experiment(patched,{a:v for a,v in code.items() if a!=CALLBACKS[owner]},key,0x1000,0,
                parameter_fixture=params,input_format=0x107,native_module=module,gain_fixture=(1024,)*4,
                machine_observer=attach,owner_buffer_capacity=7)
            (out/'latest-case.json').write_text(json.dumps(dict(owner=owner,key=hex(key),
                reentries=snapshots.rows,outer=case),indent=2)+'\n')
            checked_inputs(meter,2560)
            gains=adjusted((1024,)*4,module['wb_controls'][f'0x{key:08x}'])
            gamma=[hex(module['constants'][('GOLD' if variant==1 else 'PORTRA')+f'_RGB{i}']) for i in range(3)]
            checked_classified_prefix(case,meter.checkpoints,gains,expected_stop='first_hardware',expected_gamma=gamma)
            if set(snapshots.seen)!=set(SITES):
                raise ValueError('did not reach all reentry snapshots')
            for reentry in snapshots.rows:
                reentry['validation']=checked_reentry(reentry,gains,gamma)
            row=dict(owner=owner,key=hex(key),producer=producer,reentries=snapshots.rows,
                outer_executor=case['executor'],outer_checkpoints=meter.checkpoints,
                outer_film=case['native_film'],outer_output_changed=case['output_changed'],
                outer_event_bits_signalled=case['event_bits_signalled'])
            rows.append(row)
            (out/'progress.json').write_text(json.dumps(rows,indent=2)+'\n')
    result=dict(stock_main_sha256=sha(image),separate_main_sha256=sha(patched),module=manifest,
        baseline_hashes=baseline_hashes,recipe_tables_unchanged=True,reader=reader_provenance(),
        rgb_input_sha256=sha(rgb_path.read_bytes()),input_provenance=provenance,cases=rows,
        camera_schedule_observed=False,same_job_overlap_negative_control=True,
        source_acquisition_executed=False,whole_job_completed=False,hardware_success_supplied=False,
        camera_accessed=False,firmware_container_created=False,install_ready=False,
        source_sha256={n:sha((ROOT/'scripts'/n).read_bytes()) for n in (
            'epl9_native_source_reentry_probe.py','epl9_classified_branch_probe.py',
            'epl9_native_source_probe.py','epl9_job_probe.py','mn103_calls.py')})
    if MAIN.read_bytes()!=image:
        raise ValueError('stock main changed')
    (out/'native-source-reentry.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rgb-tables',type=Path,required=True)
    parser.add_argument('--wb-controls',type=Path,default=ROOT/'recipes/epl9-native-wb-trial-v1.json')
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    if not __debug__:parser.error('assertions required')
    verify_reader()
    result=audit(args.out,args.rgb_tables,args.wb_controls)
    print(json.dumps(dict(cases=len(result['cases']),clones=sum(len(c['reentries']) for c in result['cases']),
        same_job_overlap_negative_control=True,install_ready=False),indent=2))


if __name__=='__main__':main()
