"""Qualify opt-in private COLOR snapshots against frozen v3, without flashing."""
import argparse
import json
from pathlib import Path
from epl9_workspace_bridge import ROOT, sha
from epl9_film_late_probe import prepare_probe, frame_case, cache_sequence, passthrough_cases
from epl9_v3_concurrency_probe import build_frame, execute, snapshot
from epl9_v3_package import CANDIDATE_HASHES
from epl9_offline_prototype import REQUEST, CONTEXT, OUTPUT
from epl9_job_probe import experiment
from epl9_lifecycle_probe import Lifecycle
from epl9_wb_math_probe import extend
from mn103_subset import Memory, Region
from mn103_calls import CallMachine
from epl9_integrated_probe import RETURN


def larger_stack(frame):
    m=frame['m']
    m.memory=Memory([Region(r.address-8192,bytearray(8192)+r.data,True,r.name)
                    if r.name=='private stack' else r for r in m.memory.regions])
    return frame


def memory_bytes(m,address,size):
    region,offset=m.memory.region(address,4)
    return bytes(region.data[offset:offset+size])


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args()
    if args.out.exists() or not args.out.resolve().is_relative_to((ROOT/'local').resolve()):
        raise ValueError('new ignored output directory required')
    args.out.mkdir()
    rgb=json.loads((ROOT/'local/epl9-native-film-curves-v3-20261107/native-rgb-tables.json').read_text())
    wb=json.loads((ROOT/'recipes/epl9-native-wb-trial-v1.json').read_text())
    options=dict(base=0x604a1300,rgb_document=rgb,wb_document=wb)
    old=prepare_probe(args.out/'baseline',**options)
    new=prepare_probe(args.out/'private',private_color=True,**options)
    image,patched,original_code,code,module,manifest=new
    if sha(old[1])!=CANDIDATE_HASHES[0x100] or module['data'][4096:]!=old[4]['data'][4096:]:
        raise ValueError('frozen main or all recipe table bytes differ')
    shared=bytearray(patched)
    rows=[]
    for recipe in module['recipes']:
        for fmt in (0x200,0x100,0x40,0x1000):
            for secondary in (0x100,0x200):
                for owner in (False,True):
                    row,state=frame_case(patched,code,image,original_code,module,recipe,fmt,
                        with_owner=owner,secondary=secondary)
                    _,baseline=frame_case(old[1],old[3],image,old[2],old[4],recipe,fmt,
                        with_owner=owner,secondary=secondary)
                    if state!=baseline:
                        raise ValueError('private configuration/cache differs from frozen v3')
                    rows.append(row)
        for contrast,user in ((2,(3,-2,7,7,7)),(-2,(-3,2,-7,-7,-7)),(0,None),
                (-recipe['picture_mode_contrast'],(0,0,-recipe['tone_level']['highlights'],
                    -recipe['tone_level']['midtones'],-recipe['tone_level']['shadows']))):
            row,state=frame_case(patched,code,image,original_code,module,recipe,user=user,contrast=contrast)
            _,baseline=frame_case(old[1],old[3],image,old[2],old[4],recipe,user=user,contrast=contrast)
            if state!=baseline:raise ValueError('private user control result differs')
            rows.append(row)
    cache=cache_sequence(patched,code,image,original_code,module)
    passthrough=passthrough_cases(patched,code,image,original_code,module)
    nested=[]
    for key in (0x01010078,0x01020078):
        for fmt in (0x200,0x100,0x40,0x1000):
            ref=larger_stack(build_frame(image,original_code,patched,code,shared,key,fmt,0))
            execute(ref)
            expected=snapshot(ref)
            for point in ('color_native_call','color_after_native_call','color_restore'):
                outer=larger_stack(build_frame(image,original_code,patched,code,shared,key,fmt,0))
                original_request=memory_bytes(outer['m'],REQUEST,1876)
                original_context=memory_bytes(outer['m'],CONTEXT,128)
                execute(outer,[module['symbols'][point]])
                if (memory_bytes(outer['m'],REQUEST,1876)!=original_request or
                        memory_bytes(outer['m'],CONTEXT,128)!=original_context):
                    raise ValueError('caller-visible request/context became temporary')
                child=CallMachine(code,Memory([*outer['m'].memory.regions,
                    Region(0x1f000000,bytearray(65536),True)]),dict(sp=0x1f008000,a0=CONTEXT))
                start=child.enter(0x6079fb88,RETURN,0xf0,40)
                result=child.run(start,[RETURN])
                if result.get('pc')!=RETURN or child.r['sp']!=0x1f008000:
                    raise ValueError('nested native configuration did not return')
                if memory_bytes(child,OUTPUT,5200)!=expected[0][OUTPUT]:
                    raise ValueError('nested output differs from isolated v3')
                execute(outer)
                if snapshot(outer)!=expected:
                    raise ValueError('resumed outer output differs from isolated v3')
                nested.append(dict(key=hex(key),kind=hex(fmt),point=point,
                    caller_request_context_unchanged=True,inner_outer_match_isolated=True))
    extend(image,code)
    jobs=[]
    for key in (0x01010078,0x01020078):
        for kind in (0x200,0x100,0x40):
            observer=Lifecycle(module['base'])
            opts=dict(provide_slot=True,input_format=0x100) if kind==0x40 else {}
            r=experiment(patched,code,key,kind,0,native_module=module,
                gain_fixture=(1024,)*4,machine_observer=observer,**opts)
            if not observer.restored or observer.pending or r['output_changed'] or r['event_bits_signalled']:
                raise ValueError('job request lifecycle/pixel boundary changed')
            if r['executor'].get('error')!="0x6073eafa mov ['d0', '(0x9880014c)']: unmapped access at 0x9880014c, size 4":
                raise ValueError('job did not reach the same hardware boundary: '+str(r['executor']))
            jobs.append(dict(key=hex(key),kind=hex(kind),stack=observer.result(),
                film=r['native_film'],executor=r['executor'],restored=observer.restored))
    if shared!=patched:raise ValueError('shared code/tables modified')
    report=dict(main_sha256=sha(image),frozen_main_sha256=sha(old[1]),
        candidate_main_sha256=sha(patched),module=manifest,
        complete_table_region_unchanged=True,frames=rows,cache=cache,passthrough=passthrough,
        nested_color_cases=nested,jobs=jobs,
        sources={n:sha((ROOT/n).read_bytes()) for n in
            ('scripts/epl9_private_color_probe.py','scripts/epl9_film_late_module.py',
             'scripts/epl9_film_late_probe.py','firmware_src/epl9_films_private_color.s.in')},
        whole_job_concurrency_supported=False,irq_preemption_verified=False,
        firmware_package_created=False,install_ready=False)
    (args.out/'private-color.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(frames=len(rows),nested=len(nested),jobs=len(jobs),
        stack_peak=max(j['stack']['observed_stack_depth'] for j in jobs),
        candidate_main_sha256=sha(patched)),indent=2))


if __name__=='__main__':
    main()
