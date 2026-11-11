"""Qualify the separate native-source gate variant, entirely offline.

Execute stock source-descriptor suffixes and bind their bytes to connected
ART jobs. Source-address acquisition, the complete owner preparation, physical
packing, RTOS/ISP execution and camera installation remain unqualified.
The baseline must reproduce the existing private-COLOR v3 identity exactly.
"""
import argparse
import json
import struct
import subprocess
from pathlib import Path

from epl9_workspace_bridge import ROOT, MAIN, BASE, sha
from epl9_film_late_module import build_late_module
from epl9_film_late_probe import (prepare_probe, cache_sequence, passthrough_cases,
    frame_inputs, run_color, reference_color, restored)
from epl9_owner_binding_probe import (load_factories, load_owners, create_parameters,
    BoundOwner, control_cases)
from epl9_owner_callback_probe import CALLBACKS
from epl9_job_probe import experiment, JOB, OWNER_CALLBACK, SOURCE
from epl9_deployment_probe import Registers
from epl9_float_contract import models
from epl9_wb_math_probe import extend
from epl9_wb_extension import adjusted
from epl9_v3_package import CANDIDATE_HASHES, PRIVATE_CANDIDATE_HASHES
from mn103_tooling import default_reader, verify_reader, reader_provenance
from mn103_subset import Memory, Region, parse_listing
from mn103_calls import CallMachine

FIELDS = {14: 2, 28: 2, 48: 1, 1832: 2}
CHECKPOINTS = {0x6074f352: 'old_constructor_site', 0x60761c9e: 'gain_entry',
    0x60761ca4: 'gain_return', 0x6074f11c: 'submission',
    0x60799fdc: 'gain_consumer', 0x6079fb88: 'color_entry',
    0x6074e348:'frame_start',0x6074e3f6:'native_classification_stored',
    0x6078c867:'repeat_classifier_result',0x60761e97:'companion_result'}
STOP = "0x6073eafa mov ['d0', '(0x9880014c)']: unmapped access at 0x9880014c, size 4"


def checked_classified_prefix(case,checkpoints,expected_gains,*,expected_stop='buffer_limit',expected_gamma=None):
    """Fail closed for a declared partial control, never any arbitrary fault.

    This validates the exact stop/callsite and the gain/source invariants.
    Even an expected stop does not complete multiple submissions or hardware.
    """
    def require(condition,message):
        if not condition:
            raise ValueError('classified prefix: '+message)
    film=case.get('native_film',{})
    expected_fields={'14':0x1000,'28':0x107,'48':3,'1832':0}
    require(film.get('source_gain_record')==[1024]*4,'source gain record changed or missing')
    require(film.get('request_gain_record')==list(expected_gains),'request gains changed or missing')
    require(film.get('request_fields')==expected_fields,'final source/kind/selector differs')
    phases={}
    for checkpoint in checkpoints:
        phases.setdefault(checkpoint['phase'],[]).append(checkpoint)
    for phase in ('old_constructor_site','gain_entry','gain_return'):
        require(len(phases.get(phase,[]))==1,'expected exactly one '+phase)
    old,entry,returned=(phases[p][0] for p in ('old_constructor_site','gain_entry','gain_return'))
    require(old['gains']==entry['gains']==[1024]*4,'gain bias occurred before the finalized hook')
    require(returned['gains']==list(expected_gains),'gain-return checkpoint differs')
    require(entry['fields']==returned['fields']==expected_fields,'hook source fields differ')
    require(old['index']<entry['index']<returned['index'],'hook order differs')
    require(all(p['index']>returned['index'] for p in checkpoints
        if p['phase'] in ('submission','gain_consumer','color_entry')),'consumer precedes gain return')
    for phase in ('submission','gain_consumer','color_entry'):
        for p in phases.get(phase,[]):
            require(p.get('fields')==expected_fields and p.get('gains')==list(expected_gains),
                'consumer source/gains differ at '+phase)
    executor=case.get('executor',{})
    events=case.get('events',[])
    last=events[-1] if events else {}
    if expected_stop=='buffer_limit':
        require(not any(phases.get(p) for p in ('submission','gain_consumer','color_entry')),
            'buffer-limit prefix unexpectedly reached a consumer')
        require(executor.get('status')=='fault' and executor.get('error')==
            'owner buffer request exceeds declared fixture capacity','unexpected buffer-limit stop')
        require(executor.get('last_instructions',[])[-1:]==['0x6073eac3'],
            'buffer-limit dispatch instruction differs')
        require(last.get('op')=='call' and last.get('pc')==0x6074a8bb and
            last.get('target')==0x6073eab3,'buffer-limit native requester differs')
    elif expected_stop=='first_submission':
        require(not any(phases.get(p) for p in ('submission','gain_consumer','color_entry')),
            'stopped submission entry unexpectedly executed')
        require(executor.get('status')=='stop' and executor.get('pc')==0x6074f11c,
            'did not reach the first submission')
        require(last.get('op')=='call' and last.get('pc')==0x60762276 and
            last.get('target')==0x6074f11c,'first submission callsite differs')
    elif expected_stop=='first_hardware':
        for phase in ('submission','gain_consumer','color_entry'):
            require(len(phases.get(phase,[]))==1,'expected exactly one '+phase)
        require(phases['submission'][0]['index']<phases['color_entry'][0]['index'] and
            phases['submission'][0]['index']<phases['gain_consumer'][0]['index'],
            'processing precedes submission')
        submissions=[e for e in events if e.get('op')=='call' and e.get('target')==0x6074f11c]
        require(len(submissions)==1 and submissions[0].get('pc')==0x60762276,
            'hardware prefix submission evidence differs')
        require(executor.get('status')=='fault' and executor.get('error')==STOP,
            'did not reach the exact hardware boundary')
        require(executor.get('last_instructions',[])[-1:]==['0x6073eafa'],
            'hardware stop instruction differs')
        require(film.get('recipe_applied') is True,'hardware prefix skipped the recipe')
        require(executor.get('registers',{}).get('d0')=='0x800','hardware write value differs')
        require(film.get('gamma_hook') is True and film.get('finalized_gain_hook') is True and
            film.get('early_gain_hook') is False,'hardware prefix hook evidence differs')
        require(isinstance(expected_gamma,(tuple,list)) and len(expected_gamma)==3 and
            len(set(expected_gamma))==3 and all(v not in ('0x0',0,None) for v in expected_gamma),
            'expected gamma evidence missing or invalid')
        require(film.get('gamma_pointers')==list(expected_gamma),'hardware gamma pointers differ')
    else:
        raise ValueError('unknown classified-prefix stop contract')
    require(case.get('output_changed') is False and case.get('cpu_source_reads')==[] and
        case.get('event_bits_signalled')==0,'pixels/source/completion checks failed or missing')
    return dict(status='incomplete',expected_stop_verified=expected_stop,
        gain_hook_entries=1,multiple_submissions_completed=False)


def source_suffix(image, out, option):
    code = {}
    for start, end in ((0x607d336e,0x607d3565), (0x607d2562,0x607d2634),
                       (0x607d52b1,0x607d52d4)):
        listing = subprocess.check_output([str(default_reader()), str(MAIN), hex(BASE),
            hex(start-BASE), hex(end-BASE)], text=True)
        (out/f'source-{start:08x}.tsv').write_text(listing)
        code.update(parse_listing(listing,image,BASE))
    owner, props, desc, sp, end = 0x2c000000,0x2e000000,0x11000024,0x1d004000,0x1e000000
    context, properties, descriptor = bytearray(512),bytearray(0x7000),bytearray(64)
    struct.pack_into('<H',context,72,0x1003)
    struct.pack_into('<I',context,152,props)
    struct.pack_into('<H',properties,4300,option)
    struct.pack_into('<I',descriptor,0,SOURCE)
    m = CallMachine(code,Memory([Region(BASE,image),Region(owner,context),
        Region(props,properties),Region(desc,descriptor,True),
        Region(sp-16384,bytearray(32768),True)]),
        dict(sp=sp,a2=desc,d2=owner+72,d3=props,a3=owner+148))
    m.enter(0x607d336e,end,0xf0,28)
    m.memory.write(m.r['sp']+8,owner,4)
    result = m.run(0x607d33ab,[end])
    assert result['pc']==end and m.r['sp']==sp and not any(e['op']=='modeled_call' for e in m.events)
    assert struct.unpack_from('<H',descriptor,8)[0]==0x107 and descriptor[28]==3+4*option
    return bytes(descriptor),dict(entry='0x607d33ab',source_address_acquisition_executed=False,
        declared_property_4300=option,descriptor=descriptor.hex(),instructions=len(m.trace),modeled_calls=0)


class Observe:
    def __init__(self,descriptor,selector,force_classification=False,stop_before_submission=False):
        self.descriptor,self.selector=descriptor,selector
        self.force_classification=force_classification
        self.stop_before_submission=stop_before_submission
        self.checkpoints=[]

    def __call__(self,m):
        self.m=m
        m.r=Registers(m.r)
        outer=self
        class Trace(list):
            def append(self,pc):
                if pc==0x6074e348 and not getattr(outer,'installed',False):
                    # Only the source pointer is declared. The remaining 60B
                    # come from the separately executed stock suffix.
                    region,offset=m.memory.region(JOB+36,4,True)
                    region.data[offset:offset+64]=outer.descriptor
                    if getattr(outer,'descriptor_tail',None) is not None:
                        assert len(outer.descriptor_tail)==18
                        region.data[offset+268:offset+286]=outer.descriptor_tail
                    size=int.from_bytes(outer.descriptor[10:12],'little')*int.from_bytes(outer.descriptor[14:16],'little')*2
                    assert size<=32*1024*1024
                    m.memory.region(SOURCE,4)[0].data=bytes(size)
                    outer.installed=True
                if pc==0x60761c9e and outer.selector:
                    # Negative control: model the value written by the audited
                    # pre-copy callback, not camera execution of that callback.
                    m.memory.write(JOB+10440+1832,outer.selector,2)
                if pc==0x60761dc2 and outer.force_classification:
                    # Explicit branch control, not the camera classifier's
                    # measured output. Do not fake completion of its requests.
                    m.memory.write(JOB+10414,1,1)
                if pc in CHECKPOINTS:
                    outer.checkpoints.append(dict(pc=hex(pc),phase=CHECKPOINTS[pc],index=len(self),
                        fields={str(o):m.memory.read(JOB+10440+o,s) for o,s in FIELDS.items()},
                        gains=[m.memory.read(JOB+10440+1568+2*i,2) for i in range(4)],
                        job_sv=m.memory.read(JOB+304,2),request_sv=m.memory.read(JOB+10440+1610,2),
                        native_d0=m.r['d0'],job_classifier_flags=[m.memory.read(JOB+o,1) for o in (10414,10415,10416)]))
                super().append(pc)
        m.trace=Trace(m.trace)
        if self.selector or self.force_classification or self.stop_before_submission:
            # The synthetic special-selector control is scoped to completed
            # COLOR. Its subsequent effect path needs additional native code;
            # do not add a success model or call it a hardware-boundary pass.
            run=m.run
            def stop_after_color(start,stops=(),limit=200000):
                return run(start,[*stops,0x6074f11c if outer.force_classification or outer.stop_before_submission else 0x6079ff0e],limit)
            m.run=stop_after_color
        m.models.update(models())
        m.memory=Memory([*m.memory.regions,Region(0xa2a7da44,bytearray(4),True,'declared scalar errno')])


def native_frames(image,patched,original_code,code,module):
    """Full 5200B oracles for native-source cold/warm and film -> stock exits."""
    state,rows=None,[]
    for index in (0,0,1,1,0):
        recipe=module['recipes'][index];key=int(recipe['watercolor_key'],16)
        request,obj=frame_inputs(image,original_code,key,0x1000,0,(0,)*5,True,0x107)
        request[48]=3
        before=bytes(request)
        m,r,c,old_c,result,state=run_color(patched,code,module,request,obj,(0,)*5,key,
            0 if state else 0x10000002,state)
        expected,returned=reference_color(image,original_code,module,request,obj,(0,)*5,recipe)
        restored(before,r,c,old_c)
        assert result==expected and m.r['d0']==returned
        rows.append(dict(key=hex(key),phase='film',oracle_bytes=5200,request_restored=True))
    for key in (11,11,1,1):
        request,obj=frame_inputs(image,original_code,key,0x1000,0,(0,)*5,True,0x107)
        request[48]=3
        baseline=tuple(bytearray(v) for v in state)
        m,r,c,old_c,result,state=run_color(patched,code,module,request,obj,(0,)*5,key,0,state)
        expected=run_color(image,original_code,module,request,obj,(0,)*5,key,0x10000002,baseline)[4]
        restored(request,r,c,old_c)
        assert result==expected
        assert struct.unpack_from('<I',result,2596)[0] not in (module['constants']['GOLD_RGB0'],module['constants']['PORTRA_RGB0'])
        rows.append(dict(key=hex(key),phase='stock_exit',oracle_bytes=5200,request_restored=True))
    for fmt,flags,selector in ((0x107,7,0),(0x108,0,0),(0x107,3,0x900)):
        key=0x01010078
        request,obj=frame_inputs(image,original_code,key,0x1000,0,(0,)*5,True,0x107)
        request[48]=3
        _,_,_,_,_,state=run_color(patched,code,module,request,obj,(0,)*5,key,0x10000002,state)
        struct.pack_into('<H',request,28,fmt)
        request[48]=flags
        struct.pack_into('<H',request,1832,selector)
        baseline=tuple(bytearray(v) for v in state)
        m,r,c,old_c,result,state=run_color(patched,code,module,request,obj,(0,)*5,key,0,state)
        expected=run_color(image,original_code,module,request,obj,(0,)*5,key,0x10000002,baseline)[4]
        restored(request,r,c,old_c)
        assert result==expected and module['symbols']['color_exit'] in m.trace
        assert module['symbols']['color_post_hsl'] not in m.trace
        rows.append(dict(key=hex(key),phase='rejected_after_film',source_format=hex(fmt),flags=flags,
            selector=hex(selector),oracle_bytes=5200,request_restored=True))
    return rows


def audit(out,rgb_path,wb_path):
    if out.exists() or not out.resolve().is_relative_to((ROOT/'local').resolve()):
        raise ValueError('new ignored local output required')
    out.mkdir()
    rgb=json.loads(rgb_path.read_text());wb=json.loads(wb_path.read_text())
    options=dict(base=0x604a1300,rgb_document=rgb,wb_document=wb,private_color=True)
    image,baseline,original_code,_,old,_=prepare_probe(out/'baseline',**options)
    assert sha(baseline)==PRIVATE_CANDIDATE_HASHES[0x100]
    frozen=build_late_module(image,**dict(options,private_color=False))
    frozen_main=bytearray(image)
    frozen_main[frozen['base']-BASE:frozen['base']-BASE+len(frozen['data'])]=frozen['data']
    for patch in frozen['patches']:
        raw=bytes.fromhex(patch['after']);at=patch['address']-BASE
        frozen_main[at:at+len(raw)]=raw
    assert sha(frozen_main)==CANDIDATE_HASHES[0x100]
    image,patched,_,code,module,manifest=prepare_probe(out/'native-source',**options,native_source_gate=True)
    assert module['data'][4096:]==old['data'][4096:]
    assert 0x6074f352 not in [p['address'] for p in module['patches']]
    extend(image,code)
    owner_code=load_owners(image,out)
    producer_code={**owner_code,**load_factories(image,out)}
    descriptors=[source_suffix(image,out,n) for n in (0,1)]
    rows=[]
    for owner in ('primary','primary_wrapper'):
        for variant in (1,2):
            key=0x01000078+(variant<<16)
            for option,selector in ((0,0),(1,0),(0,0x900)):
                descriptor,_=descriptors[option]
                params,state,producer=create_parameters(image,producer_code,owner,variant)
                meter=Observe(descriptor,selector)
                def attach(m):
                    meter(m)
                    m.memory=Memory([*m.memory.regions,*[r for r in state['regions'] if r.address!=0x8050]])
                    m.models[OWNER_CALLBACK].source_bounds=(4640,3472)
                    m.models[CALLBACKS[owner]]=BoundOwner(m.models[OWNER_CALLBACK],owner_code,CALLBACKS[owner],state)
                outer={a:v for a,v in code.items() if a!=CALLBACKS[owner]}
                case=experiment(patched,outer,key,0x1000,0,parameter_fixture=params,input_format=0x107,
                    native_module=module,gain_fixture=(1024,)*4,machine_observer=attach)
                accepted=option==0 and selector==0
                film=case.get('native_film',{})
                executor=case.get('executor',{})
                if selector:
                    assert executor.get('pc')==0x6079ff0e,executor
                else:
                    assert executor.get('error')==STOP,executor
                assert film['recipe_applied']==accepted and not film['early_gain_hook'] and film['finalized_gain_hook']
                expected_gains=list(adjusted((1024,)*4,module['wb_controls'][f'0x{key:08x}'])) if accepted else [1024]*4
                assert film['request_gain_record']==expected_gains
                expected_gamma=[hex(module['constants'][('GOLD' if variant==1 else 'PORTRA')+f'_RGB{i}']) for i in range(3)]
                assert (film['gamma_pointers']==expected_gamma)==accepted
                assert not case['output_changed'] and not case['cpu_source_reads'] and not case['event_bits_signalled']
                assert sum(p['phase']=='gain_entry' for p in meter.checkpoints)==1
                gain_return=next(p['index'] for p in meter.checkpoints if p['phase']=='gain_return')
                assert all(p['index']>gain_return for p in meter.checkpoints if p['phase'] in ('submission','gain_consumer','color_entry'))
                assert all(entry[1]==0 for entry in case['entries'])
                rows.append(dict(owner=owner,key=hex(key),source_flags=descriptor[28],selector_control=selector,
                    selector_control_is_injected=bool(selector),producer=producer,film=film,
                    checkpoints=meter.checkpoints,stop='completed COLOR return 0x6079ff0e' if selector else STOP,
                    special_selector_downstream_qualified=False if selector else None,
                    source_pointer_acquisition_executed=False,
                    whole_owner_preparation_executed=False,output_pixels_produced=False))
                (out/'progress.json').write_text(json.dumps(rows,indent=2)+'\n')
    # Audit the branch which can submit the main request before the old B4D
    # proposal. Stop before its first submission, without hardware completion.
    for start,end in ((0x6078c832,0x6078c8dd),(0x6078ce9c,0x6078cf30),
                       (0x6073a880,0x6073abd3)):
        listing=subprocess.check_output([str(default_reader()),str(MAIN),hex(BASE),
            hex(start-BASE),hex(end-BASE)],text=True)
        (out/f'classified-{start:08x}.tsv').write_text(listing)
        code.update(parse_listing(listing,image,BASE))
    params,state,_=create_parameters(image,producer_code,'primary',1)
    meter=Observe(descriptors[0][0],0,force_classification=True)
    def attach_classified(m):
        meter(m)
        m.memory=Memory([*m.memory.regions,*[r for r in state['regions'] if r.address!=0x8050]])
        m.models[OWNER_CALLBACK].source_bounds=(4640,3472)
        m.models[CALLBACKS['primary']]=BoundOwner(m.models[OWNER_CALLBACK],owner_code,CALLBACKS['primary'],state)
    classified=experiment(patched,{a:v for a,v in code.items() if a!=CALLBACKS['primary']},
        0x01010078,0x1000,0,parameter_fixture=params,input_format=0x107,native_module=module,
        gain_fixture=(1024,)*4,machine_observer=attach_classified)
    classified_prefix=dict(classifier_value_forced=True,executor=classified.get('executor'),
        checkpoints=meter.checkpoints,multiple_submissions_completed=False,
        source_gain_record=classified.get('native_film',{}).get('source_gain_record'),
        request_gain_record=classified.get('native_film',{}).get('request_gain_record'),
        fixture_buffers=classified.get('fixture_buffers'),host_fixture_allocation_limit=2)
    classified_prefix.update(checked_classified_prefix(classified,meter.checkpoints,[1106,901,1024,1024]))
    classified_prefix['reached_first_submission']=classified.get('executor',{}).get('pc')==0x6074f11c
    result=dict(main_sha256=sha(image),baseline_private_main_sha256=sha(baseline),
        baseline_frozen_main_sha256=sha(frozen_main),separate_main_sha256=sha(patched),module=manifest,
        recipe_table_bytes_unchanged=True,reader=reader_provenance(),source_suffixes=[r for _,r in descriptors],
        connected=rows,classified_prefix=classified_prefix,
        native_source_frames=native_frames(image,patched,original_code,code,module),
        legacy_source_cache=cache_sequence(patched,code,image,original_code,module),
        passthrough=passthrough_cases(patched,code,image,original_code,module),
        owner_controls=control_cases(image,owner_code),camera_accessed=False,install_ready=False,
        physical_source_packing_verified=False,whole_job_concurrency_qualified=False,
        arbitrary_admission_callbacks_qualified=False,firmware_container_created=False,
        source_sha256={name:sha((ROOT/'scripts'/name).read_bytes()) for name in (
            'epl9_native_source_probe.py','epl9_native_source_gate.py','epl9_wb_extension.py',
            'epl9_film_late_module.py','epl9_film_late_probe.py','epl9_job_probe.py')})
    assert MAIN.read_bytes()==image
    (out/'native-source.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--rgb-tables',type=Path,required=True)
    parser.add_argument('--wb-controls',type=Path,default=ROOT/'recipes/epl9-native-wb-trial-v1.json')
    args=parser.parse_args()
    if not __debug__:
        parser.error('assertions required')
    verify_reader()
    result=audit(args.out,args.rgb_tables,args.wb_controls)
    print(json.dumps(dict(connected=len(result['connected']),native_source_frames=len(result['native_source_frames']),
        passthrough=len(result['passthrough']),separate_main_sha256=result['separate_main_sha256'],
        classified_status=result['classified_prefix']['status'],
        classified_stop_verified=result['classified_prefix']['expected_stop_verified'],
        recipe_table_bytes_unchanged=True,install_ready=False),indent=2))


if __name__=='__main__':
    main()
