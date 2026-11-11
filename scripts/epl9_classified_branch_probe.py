"""Exercise the classified ART prefix with coherent native-produced inputs.

Only finite host output/scratch allocations are expanded. No ISP ready bits,
completion signals, output pixels or successful hardware returns are supplied.
The source address and owner properties remain declared fixtures.
"""
import argparse
import json
import struct
import subprocess
from pathlib import Path

from epl9_workspace_bridge import ROOT,MAIN,BASE,sha
from epl9_film_late_module import build_late_module
from epl9_film_late_probe import prepare_probe
from epl9_native_source_probe import Observe,source_suffix,checked_classified_prefix
from epl9_owner_binding_probe import load_factories,load_owners,create_parameters,BoundOwner
from epl9_owner_callback_probe import CALLBACKS
from epl9_job_probe import experiment,JOB,OWNER_CALLBACK,OWNER_BUFFER_ARENAS
from epl9_wb_math_probe import extend
from epl9_wb_extension import adjusted
from epl9_v3_package import PRIVATE_CANDIDATE_HASHES
from mn103_tooling import default_reader,verify_reader,reader_provenance
from mn103_subset import Memory,Region,parse_listing
from mn103_calls import CallMachine

SEPARATE_MAIN_SHA='2d003930675b47774e9ed3535ee49c64f56ff519bd6f1a33ddafd1a8c688b9b7'
CLASSIFIED_WINDOWS=((0x6078c812,0x6078e82d),(0x6073a880,0x6073abd3))


def extend_code(image,code,out,windows):
    for start,end in windows:
        listing=subprocess.check_output([str(default_reader()),str(MAIN),hex(BASE),
            hex(start-BASE),hex(end-BASE)],text=True)
        (out/f'{start:08x}.tsv').write_text(listing)
        parsed=parse_listing(listing,image,BASE)
        if any(at in code and code[at]!=row for at,row in parsed.items()):
            raise ValueError('conflicting native instruction window')
        code.update(parsed)


def source_fields(image,out,sv):
    """Produce D268/270/278/280/284/285 with actual stock stores/callees."""
    descriptor,suffix=source_suffix(image,out,0)
    code={}
    extend_code(image,code,out,((0x607d32f0,0x607d332b),(0x607d3160,0x607d3171),
        (0x607d513d,0x607d52b1),(0x607d3000,0x607d3064),(0x607d2562,0x607d25a7)))
    owner,props,sp=0x2c000000,0x2e000000,0x10013c00
    context,properties,job=bytearray(512),bytearray(0x7000),bytearray(16384)
    context[72:74]=struct.pack('<H',0x1003)
    struct.pack_into('<I',context,152,props)
    struct.pack_into('<H',context,280,sv)
    job[36:100]=descriptor
    m=CallMachine(code,Memory([Region(BASE,image),Region(owner,context),Region(props,properties),
        Region(JOB,job,True),Region(sp-16384,bytearray(32768),True)]),dict(sp=sp,a3=props))
    m.memory.write(sp+4,JOB+36,4);m.memory.write(sp+16,owner,4)
    first=m.run(0x607d32f0,[0x607d332b])
    second=m.run(0x607d3160,[0x607d3171])
    assert first.get('pc')==0x607d332b and second.get('pc')==0x607d3171 and m.r['sp']==sp
    assert not any(e['op']=='modeled_call' for e in m.events)
    fields={str(o):m.memory.read(JOB+36+o,s) for o,s in ((268,2),(270,2),(278,2),(280,2),(284,1),(285,1))}
    assert fields=={'268':sv,'270':0,'278':0,'280':0,'284':0,'285':6}
    return descriptor,bytes(job[36+268:36+286]),dict(source_suffix=suffix,
        declared_owner_operation='0x1003',declared_owner_280=sv,declared_properties='zero including property23120',
        native_fields=fields,native_instructions=len(m.trace),modeled_calls=0,
        source_address_acquisition_executed=False,full_owner_preparation_executed=False)


def checked_inputs(meter,sv):
    phases={}
    for p in meter.checkpoints:phases.setdefault(p['phase'],[]).append(p)
    for name in ('native_classification_stored','repeat_classifier_result','companion_result'):
        if len(phases.get(name,[]))!=1:raise ValueError('classified input: missing/duplicate '+name)
    if phases['native_classification_stored'][0]['native_d0']!=1:
        raise ValueError('native frame-start classifier did not return one')
    if phases['repeat_classifier_result'][0]['native_d0']!=1:
        raise ValueError('repeated native classifier disagrees')
    if phases['companion_result'][0]['native_d0']!=3:
        raise ValueError('native companion classifier did not select stage three')
    entry=next(p for p in meter.checkpoints if p['phase']=='gain_entry')
    if entry['job_sv']!=sv or entry['request_sv']!=sv or entry['job_classifier_flags']!=[1,0,0]:
        raise ValueError('classified input: source/request Sv or companion flags differ')
    if meter.force_classification:
        raise ValueError('classified input must not force the result bit')


def audit(out,rgb_path,wb_path):
    if out.exists() or not out.resolve().is_relative_to((ROOT/'local').resolve()):
        raise ValueError('new ignored output required')
    out.mkdir()
    rgb=json.loads(rgb_path.read_text());wb=json.loads(wb_path.read_text())
    options=dict(base=0x604a1300,rgb_document=rgb,wb_document=wb,private_color=True)
    image,patched,_,code,module,manifest=prepare_probe(out/'module',**options,native_source_gate=True)
    assert sha(patched)==SEPARATE_MAIN_SHA
    old=build_late_module(image,**options)
    prior=bytearray(image);prior[old['base']-BASE:old['base']-BASE+len(old['data'])]=old['data']
    for p in old['patches']:
        raw=bytes.fromhex(p['after']);at=p['address']-BASE;prior[at:at+len(raw)]=raw
    assert sha(prior)==PRIVATE_CANDIDATE_HASHES[0x100] and old['data'][4096:]==module['data'][4096:]
    extend(image,code);extend_code(image,code,out,CLASSIFIED_WINDOWS)
    owner_code=load_owners(image,out);producer_code={**owner_code,**load_factories(image,out)}
    descriptor,tail,provenance=source_fields(image,out,2560)
    rows=[]
    for owner in ('primary','primary_wrapper'):
        for variant in (1,2):
            for capacity,stop in ((6,'buffer_limit'),(7,'first_submission'),(7,'first_hardware')):
                key=0x01000078+(variant<<16)
                params,state,producer=create_parameters(image,producer_code,owner,variant,sv_fixture=2560)
                assert struct.unpack_from('<H',state['context'],280)[0]==2560
                meter=Observe(descriptor,0,stop_before_submission=stop!='first_hardware')
                meter.descriptor_tail=tail
                def attach(m):
                    meter(m)
                    m.memory=Memory([*m.memory.regions,*[r for r in state['regions'] if r.address!=0x8050]])
                    m.models[OWNER_CALLBACK].source_bounds=(4640,3472)
                    m.models[CALLBACKS[owner]]=BoundOwner(m.models[OWNER_CALLBACK],owner_code,CALLBACKS[owner],state)
                case=experiment(patched,{a:v for a,v in code.items() if a!=CALLBACKS[owner]},key,0x1000,0,
                    parameter_fixture=params,input_format=0x107,native_module=module,gain_fixture=(1024,)*4,
                    machine_observer=attach,owner_buffer_capacity=capacity)
                # Save unexpected outcomes before the fail-closed validator.
                partial=dict(owner=owner,key=hex(key),capacity=capacity,expected_stop=stop,case=case,
                    checkpoints=meter.checkpoints,input_provenance=provenance)
                (out/'latest-case.json').write_text(json.dumps(partial,indent=2)+'\n')
                checked_inputs(meter,2560)
                gains=adjusted((1024,)*4,module['wb_controls'][f'0x{key:08x}'])
                prefix='GOLD' if variant==1 else 'PORTRA'
                gamma=[hex(module['constants'][prefix+f'_RGB{i}']) for i in range(3)]
                validation=checked_classified_prefix(case,meter.checkpoints,gains,expected_stop=stop,
                    expected_gamma=gamma if stop=='first_hardware' else None)
                allocations=case['fixture_buffers']
                assert [b['id'] for b in allocations]==([0x1000,7,8,10,11,12] if capacity==6 else [0x1000,7,8,10,11,12,13])
                assert [b['address'] for b in allocations]==list(OWNER_BUFFER_ARENAS[:capacity])
                assert all(not b['payload_changed'] for b in allocations)
                rows.append(dict(owner=owner,key=hex(key),capacity=capacity,expected_stop=stop,
                    validation=validation,producer=producer,film=case['native_film'],
                    executor=case['executor'],allocations=allocations,checkpoints=meter.checkpoints,
                    source_pixel_reads=case['cpu_source_reads'],output_changed=case['output_changed'],
                    completion_signalled=case['event_bits_signalled'],whole_job_completed=False))
                (out/'progress.json').write_text(json.dumps(rows,indent=2)+'\n')
                print(json.dumps(dict(owner=owner,key=hex(key),capacity=capacity,stop=stop,verified=True)),flush=True)
    result=dict(stock_main_sha256=sha(image),separate_main_sha256=sha(patched),module=manifest,
        baseline_private_main_sha256=sha(prior),recipe_tables_unchanged=True,reader=reader_provenance(),
        input_provenance=provenance,cases=rows,classification_forced=False,
        physical_sv_to_iso_verified=False,physical_source_packing_verified=False,
        whole_job_completed=False,multiple_submissions_completed=False,camera_accessed=False,
        firmware_container_created=False,install_ready=False,
        source_sha256={n:sha((ROOT/'scripts'/n).read_bytes()) for n in (
            'epl9_classified_branch_probe.py','epl9_native_source_probe.py','epl9_job_probe.py')})
    assert MAIN.read_bytes()==image
    (out/'classified-branch.json').write_text(json.dumps(result,indent=2)+'\n')
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
    print(json.dumps(dict(cases=len(result['cases']),classification_forced=False,
        multiple_submissions_completed=False,install_ready=False),indent=2))


if __name__=='__main__':main()
