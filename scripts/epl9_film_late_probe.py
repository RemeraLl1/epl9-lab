"""Execute the late film hooks with original ART keys and owner objects."""
import argparse
import json
from pathlib import Path
import struct
import subprocess

from epl9_film_late_module import build_late_module
from epl9_film_module import emit_files, require
from epl9_film_handoff import load_code, base_request, make_bundle, pipeline, definitions, validate_recipes
from epl9_film_module_probe import call, flag_routes, USER_CONTROLS
from epl9_workspace_bridge import ROOT, BASE, MAIN, sha
from epl9_integrated_probe import native, full_route, WINDOWS, EXTRA_WINDOWS, SERVICE_WINDOWS
from epl9_offline_prototype import JOB, REQUEST, CONTEXT, OUTPUT, OBJECT, SP, header
from mn103_subset import Memory, Region, parse_listing
from mn103_models import FillModel
from epl9_job_probe import JOB_WINDOWS, experiment
from epl9_color_extension import matrix_result
from epl9_wb_extension import adjusted
from epl9_wb_probe import boundaries as wb_boundaries, CoefficientReads
from epl9_placement import module_regions, with_module_data
from epl9_film_module import MODULE_BASE

AUX = 0x19000000
NATIVE_OWNER = 0x1b000000
LATE_WINDOWS = {'short_color_parameter_selection': (0x607902b0,0x607909c0)}


def owner_object(image,code,request,user):
    obj = bytearray([0xa5])*4200
    m = native(image,code,[Region(REQUEST,bytearray(request),True),Region(OBJECT,obj,True),
        Region(USER_CONTROLS,struct.pack('<5h',*(user or (0,)*5)))],{}, {0x4700111e:FillModel()})
    call(m,0x6078ab39,0xb0,36,dict(a0=REQUEST,a1=OBJECT))
    require(obj[4184:] == b'\xa5'*16,'native owner constructor exceeded its slot')
    struct.pack_into('<I',obj,20,17)  # Explicit owner fixture token, never changed by the hook.
    return bytes(obj)


def frame_inputs(image,original_code,key,fmt,contrast,user,with_owner,secondary=0x100):
    r = base_request(key,fmt)
    struct.pack_into('<H',r,28,secondary)
    r[1795] = contrast & 255
    struct.pack_into('<I',r,1484,AUX)
    struct.pack_into('<I',r,1512,USER_CONTROLS if user is not None else 0)
    struct.pack_into('<9h',r,1592,128,10,-6,8,128,-4,-2,6,128)
    obj = owner_object(image,original_code,r,user) if with_owner else bytes(4200)
    struct.pack_into('<I',r,1524,OBJECT if with_owner else 0)
    return r,obj


def run_color(image,code,module,request,obj,user,key,flags=0x10000002,state=None):
    image=with_module_data(image,module)
    r,c = bytearray(request),bytearray(128)
    output,cache = state if state is not None else (bytearray(5200),bytearray(6000))
    controls = struct.pack('<5h',*(user or (0,)*5))
    for at,value in ((4,REQUEST),(12,OUTPUT),(52,key),(60,flags)):
        struct.pack_into('<I',c,at,value)
    m = native(image,code,[Region(REQUEST,r,True),Region(CONTEXT,c,True),Region(OUTPUT,output,True),
        Region(AUX,cache,True),Region(OBJECT,obj),Region(USER_CONTROLS,controls),
        *module_regions(image,module)],{})
    if module.get('metadata',{}).get('private_color_snapshot'):
        # Explicitly provision enough synthetic stack for the opt-in snapshot.
        # Existing baseline fixtures keep their historical bounds.
        m.memory=Memory([Region(v.address-8192,bytearray(8192)+v.data,True,v.name)
                         if v.name=='stack' else v for v in m.memory.regions])
    if user is not None:
        call(m,0x6074a061,0,16,dict(a0=USER_CONTROLS,a1=CONTEXT+64))
    before_c = bytes(c)
    call(m,0x6079fb88,0xf0,40,dict(a0=CONTEXT))
    return m,r,c,before_c,bytes(output),(output,cache)


def restored(request,r,c,before_c):
    require(r == request,'late hook did not restore the complete original request')
    require(c[52:56] == before_c[52:56] and c[60:80] == before_c[60:80],
            'late hook did not restore caller identity/flags/scaled tone')


def reference_color(image,code,module,request,obj,user,recipe):
    # Independent Python arithmetic supplies the oracle inputs. All packing and
    # tone generation here still execute the original native functions.
    r = bytearray(request)
    r[8:12] = header(11)
    clamp = lambda v,limit:max(-limit,min(limit,v))
    r[1795] = clamp(struct.unpack_from('<b',r,1795)[0]+recipe['picture_mode_contrast'],2) & 255
    u = user or (0,)*5
    tone = recipe['tone_level']
    merged = (*u[:2],clamp(u[2]+tone['highlights'],7),clamp(u[3]+tone['midtones'],7),clamp(u[4]+tone['shadows'],7))
    struct.pack_into('<I',r,1512,USER_CONTROLS)
    m,r,c,_,_,state = run_color(image,code,module,r,obj,merged,11)
    native_return = m.r['d0']
    prefix = 'GOLD' if int(recipe['watercolor_key'],16)==0x01010078 else 'PORTRA'
    table = module['constants'][prefix+'_HSL']
    call(m,0x6079e50e,0xf0,80,dict(a0=table,a1=OUTPUT,d0=m.memory.read(table+3024,2)))
    struct.pack_into('<I',r,1524,0)
    call(m,0x6079f309,0xf0,32,dict(a0=CONTEXT))
    call(m,0x6079d7a0,0xa0,8,dict(a0=OUTPUT,a1=module['constants'][prefix+'_RGB0'],
        d0=module['constants'][prefix+'_RGB1'],d1=module['constants'][prefix+'_RGB2']))
    if module.get('color_controls'):
        row=module['color_controls'][recipe['watercolor_key']]
        output=state[0]
        struct.pack_into('<9h',output,80,*matrix_result(struct.unpack_from('<9h',output,80),row['matrix_delta']))
        if row['six_axis'] is not None:struct.pack_into('<12h',output,100,*row['six_axis'])
    return bytes(state[0]),native_return


def frame_case(image,code,original_image,original_code,module,recipe,fmt=0x200,user=(0,)*5,
               contrast=0,with_owner=True,state=None,flags=0x10000002,secondary=0x100,owner_fixture=None):
    key = int(recipe['watercolor_key'],16)
    request,obj = frame_inputs(original_image,original_code,key,fmt,contrast,user,with_owner,secondary)
    if owner_fixture is not None:
        obj = owner_fixture
    before = bytes(request)
    m,r,c,before_c,result,state = run_color(image,code,module,request,obj,user,key,flags,state)
    restored(before,r,c,before_c)
    pointer = struct.unpack_from('<I',result,2608)[0]
    require(not 0x10010000 <= pointer < 0x10011000,'tone configuration retains temporary stack memory')
    reference,native_return = reference_color(original_image,original_code,module,request,obj,user,recipe)
    require(m.r['d0'] == native_return,'late hook changed the original native return value')
    require(result == reference,f'late configuration differs from COLOR oracle: key={key:#x}, fmt={fmt:#x}, '
        f'owner={with_owner}, offsets={[n for n,(a,b) in enumerate(zip(result,reference)) if a!=b][:30]}')
    return dict(key=hex(key),fmt=hex(fmt),secondary=hex(secondary),owner=with_owner,user=user,contrast=contrast,
        native_return=hex(native_return),request_restored_bytes=1876,original_owner_readonly=True,
        configuration_oracle_bytes=5200,instructions=len(m.trace),pixels=False),state


def cache_sequence(image,code,original_image,original_code,module):
    """Reuse real native output/cache payloads; do not clear them between frames."""
    state,rows = None,[]
    for index in (0,0,1,1,0):
        row,state = frame_case(image,code,original_image,original_code,module,module['recipes'][index],
            state=state,flags=0 if state else 0x10000002)
        rows.append(dict(row,phase='film_warm' if rows else 'film_cold'))
    # A normal frame must rebuild even when its caller supplies no dirty flags.
    # The stock comparison starts with precisely the same output/cache snapshot.
    for key in (11,11,1,1):
        r,obj = frame_inputs(original_image,original_code,key,0x200,0,(0,)*5,True)
        baseline = tuple(bytearray(v) for v in state)
        observed,request,c,before_c,result,state = run_color(image,code,module,r,obj,(0,)*5,key,0,state)
        expected = run_color(original_image,original_code,module,r,obj,(0,)*5,key,0x10000002,baseline)[4]
        restored(r,request,c,before_c)
        require(result == expected,'film exit left stale configuration in native output')
        require(struct.unpack_from('<I',result,2596)[0] not in
            (module['constants']['GOLD_RGB0'],module['constants']['PORTRA_RGB0']),
            'ordinary mode retained film gamma pointer')
        rows.append(dict(key=hex(key),phase='ordinary_after_film',configuration_oracle_bytes=5200,
            exit_cleanup_executed=module['symbols']['color_exit'] in observed.trace,pixels=False))
    return rows


def passthrough_cases(image,code,original_image,original_code,module):
    rows = []
    for key in (1,11,0x01030078):
        for fmt in (0x200,0x100,0x40,0x1000):
            r,obj = frame_inputs(original_image,original_code,key,fmt,0,(0,)*5,True)
            m,request,c,before_c,result,_ = run_color(image,code,module,r,obj,(0,)*5,key)
            expected = run_color(original_image,original_code,module,r,obj,(0,)*5,key)[4]
            restored(r,request,c,before_c)
            require(result == expected,'late entry changed a non-target configuration')
            require(module['symbols']['color_save'] not in m.trace,'non-target unnecessarily extended its frame')
            rows.append(dict(key=hex(key),fmt=hex(fmt),configuration_oracle_bytes=5200))
    for offset,size,value in ((28,2,0),(48,1,1),(1832,2,1)):
        r,obj = frame_inputs(original_image,original_code,0x01010078,0x200,0,(0,)*5,True)
        r[offset:offset+size] = value.to_bytes(size,'little')
        m,request,c,before_c,result,_ = run_color(image,code,module,r,obj,(0,)*5,0x01010078)
        expected = run_color(original_image,original_code,module,r,obj,(0,)*5,0x01010078)[4]
        restored(r,request,c,before_c)
        require(result == expected and module['symbols']['color_save'] not in m.trace,
                'unqualified request entered the late recipe path')
        rows.append(dict(qualification_field=offset,value=value,configuration_oracle_bytes=5200))
    return rows


def owner_reference_case(image,code,original_image,original_code,module):
    """Two retained native references; sequential frames, not an RTOS race test."""
    owner = bytearray(15432)
    struct.pack_into('<I',owner,15408,OBJECT)
    before = bytes(owner)
    m = native(image,code,[Region(NATIVE_OWNER,owner,True)],{})
    counts = []
    for _ in range(2):
        call(m,0x6074b41f,0,4,dict(d0=NATIVE_OWNER))
        require(m.r['a0'] == OBJECT,'native acquire selected a different object')
        counts.append(struct.unpack_from('<H',owner,15428)[0])
    state = None
    _,obj = frame_inputs(original_image,original_code,11,0x200,0,(0,)*5,True)
    for recipe in module['recipes']:
        _,state = frame_case(image,code,original_image,original_code,module,recipe,state=state,flags=0,
                            owner_fixture=obj)
        require(struct.unpack_from('<H',owner,15428)[0] == 2,'configuration changed native owner reference count')
    for _ in range(2):
        call(m,0x6074b429,0,4,dict(d0=NATIVE_OWNER))
        counts.append(struct.unpack_from('<H',owner,15428)[0])
    require(owner == before and counts == [1,2,1,0],'unbalanced native owner references')
    return dict(counts=counts,original_owner_readonly=True,sequential_fixture=True,rtos_concurrency=False)


def connected_cases(image,code,module):
    rows = []
    for recipe in module['recipes']:
        for kind in (0x200,0x100,0x40):
            for selector in (0,2):
                options = dict(provide_slot=True,input_format=0x100) if kind == 0x40 else {}
                wb=module.get('wb_controls')
                meter=CoefficientReads(module)
                if wb is not None:
                    options.update(gain_fixture=(2048,1536,1024,1056),machine_observer=meter)
                report = experiment(image,code,int(recipe['watercolor_key'],16),kind,selector,
                                    native_module=module,**options)
                film = report['native_film']
                notified=[e['coefficients_preserved'] for e in report['events'] if e.get('event')==2 and 'coefficients_preserved' in e]
                require(notified and all(values==film['matrix_words'] for values in notified),
                        'owner notification and final ISP matrix disagree')
                film['owner_matrix_matches_isp']=True
                if wb is not None:
                    expected=adjusted(options['gain_fixture'],wb[recipe['watercolor_key']])
                    require(film['early_gain_hook'] and tuple(film['request_gain_record'])==expected,
                            'connected constructor did not apply early gain bias')
                    require(tuple(film['source_gain_record'])==options['gain_fixture'],'source gains mutated')
                    require(meter.reads and {r['index'] for r in meter.reads}==set(range(4)) and
                            all(r['value']==expected[r['index']] for r in meter.reads),
                            'native consumers did not read adjusted coefficients')
                    film['native_gain_consumers']=meter.reads
                require(film['color_entry'] and film['recipe_applied'] and film['gamma_hook'],
                        'connected native job missed recipe configuration')
                require(film['job_header_unchanged'] and film['cached_key_unchanged'],
                        'connected job identity changed')
                require(film['request_header'] == header(int(recipe['watercolor_key'],16)).hex(),
                        'connected request identity not restored')
                prefix = 'GOLD' if int(recipe['watercolor_key'],16) == 0x01010078 else 'PORTRA'
                require(film['gamma_pointers'] == [hex(module['constants'][f'{prefix}_RGB{n}']) for n in range(3)],
                        'connected job did not retain the selected curve pointers')
                require(not report['output_changed'] and report['allocation_canaries_intact'],
                        'hardware-bound probe changed pixels or an allocation guard')
                require(report['executor']['status'] == 'fault' and report['executor'].get('error') ==
                    "0x6073eafa mov ['d0', '(0x9880014c)']: unmapped access at 0x9880014c, size 4",
                    'connected job stopped before the established TruePic boundary')
                require(not report['cpu_source_reads'] and not report['event_bits_signalled'] and
                    not report['pending_record_zero'],'probe fabricated hardware processing or completion')
                rows.append(dict(key=report['key'],kind=report['kind'],selector=selector,native_film=film,
                    executor=report['executor'],source_reads=len(report['cpu_source_reads']),
                    event_bits_signalled=report['event_bits_signalled'],
                    pending_record_zero=report['pending_record_zero'],pixels=False))
    return rows


def original_key_crosscheck(image,code):
    """Independently reproduce the other chat's narrower attached-object result."""
    hsl = validate_recipes(json.loads((ROOT/'recipes/epl9-film-drafts-v0.json').read_text()))
    tone = definitions(json.loads((ROOT/'recipes/epl9-film-drafts-v2.json').read_text()))
    bundles = [make_bundle(image,code,r,h,n) for n,(r,h) in enumerate(zip(tone,hsl))]
    rows = []
    for selected in bundles:
        for fmt in (0x200,0x100,0x40):
            for live in (False,True):
                for gamma in (False,True):
                    a = pipeline(image,code,bundles,selected,fmt,hook=gamma,live_tone=live)[1]
                    b = pipeline(image,code,bundles,selected,fmt,hook=gamma,live_tone=live,
                                 processing_key=selected['key'])[1]
                    require(a == b,'attached-object original-key crosscheck no longer matches COLOR')
                    rows.append(dict(key=hex(selected['key']),fmt=hex(fmt),live_hsm=live,
                        independent_gamma=gamma,bytes_compared=5200,equal=True))
    return rows


def extension_boundaries(image,code,module):
    if not module.get('color_controls'):return []
    rows=[]
    for slot,(key,label) in enumerate((('0x01010078','gold'),('0x01020078','portra')),1):
        settings=module['color_controls'][key]
        for value in (-32768,32767):
            for index in range(9):
                matrix=[0]*9;matrix[index]=value
                output=bytearray(5200)
                struct.pack_into('<9h',output,80,*matrix)
                m=native(image,code,[Region(OUTPUT,output,True),*module_regions(image,module)],
                         dict(d2=OUTPUT+80,d3=slot))
                result=m.run(module['symbols']['matrix_'+label],[0x6079c01c])
                require(result['pc']==0x6079c01c and m.r['sp']==SP,'matrix boundary failed')
                m.r['d2']=OUTPUT
                result=m.run(module['symbols']['extended_'+label],[module['symbols']['color_restore']])
                require(result['pc']==module['symbols']['color_restore'] and m.r['sp']==SP,'extension boundary failed')
                require(struct.unpack_from('<9h',output,80)==matrix_result(matrix,settings['matrix_delta']),
                        'native matrix overflow preflight differs from independent oracle')
                if settings['six_axis'] is not None:
                    require(struct.unpack_from('<12h',output,100)==settings['six_axis'],'native six-axis packing failed')
                rows.append(dict(key=key,index=index,value=value,atomic_matrix_guard=True))
    return rows


def route_cases(image,code,original_image,original_code,module):
    results = []
    for key in (0x01010078,0x01020078,1,11,0x01030078):
        for kind in (0x200,0x100,0x40):
            for selector in (0,2):
                for flags in (0,0x10000,0x20000,0x30000):
                    expected,reference = full_route(original_image,original_code,key,kind,selector,flags,True)
                    expected[12:16] = header(key)
                    struct.pack_into('<I',expected,10384,key)
                    job = bytearray(14552)
                    job[12:16] = header(key)
                    struct.pack_into('<I',job,10384,key)
                    struct.pack_into('<I',job,16,flags)
                    struct.pack_into('<H',job,20,kind)
                    job[25] = selector
                    m = native(image,code,[Region(JOB,job,True),*module_regions(image,module)],{})
                    call(m,0x607519b8,0xf0,40,dict(a0=JOB))
                    require(job == expected,'late routing changed an undeclared job field')
                    results.append(dict(key=hex(key),kind=hex(kind),selector=selector,flags=hex(flags),bytes_compared=14552))
    return results


def prepare_probe(out,diagnostic_rgb=False,rgb_document=None,color_document=None,wb_document=None,base=MODULE_BASE,private_color=False):
    require(not out.exists() and out.resolve().is_relative_to((ROOT/'local').resolve()),'new ignored output required')
    reader = ROOT/'local/mn103-tooling/mn103-reader.exe'
    image,code,_ = load_code(MAIN,reader)
    for start,stop in set([*WINDOWS.values(),*EXTRA_WINDOWS.values(),*SERVICE_WINDOWS.values(),
                          *JOB_WINDOWS.values(),*LATE_WINDOWS.values()]):
        listing = subprocess.check_output([str(reader),str(MAIN),hex(BASE),hex(start-BASE),hex(stop-BASE)],text=True)
        code.update(parse_listing(listing,image,BASE))
    original_code = dict(code)
    module = build_late_module(image,base=base,diagnostic_rgb=diagnostic_rgb,rgb_document=rgb_document,color_document=color_document,wb_document=wb_document,private_color=private_color)
    generated,manifest = emit_files(module,out)
    modified = bytearray(image)
    if BASE<=base and base+len(module['data'])<=BASE+len(image):
        modified[base-BASE:base-BASE+len(module['data'])]=module['data']
    for index,p in enumerate(module['patches']):
        raw = bytes.fromhex(p['after'])
        modified[p['address']-BASE:p['address']-BASE+len(raw)] = raw
        path = out/f'candidate-hook-{index}.bin'
        path.write_bytes(raw)
        listing = subprocess.check_output([str(reader),str(path.resolve()),hex(p['address']),'0',hex(len(raw))],text=True)
        for at in [at for at in code if p['address']<=at<p['address']+len(raw)]: del code[at]
        code.update(parse_listing(listing,raw,p['address']))
    code.update(generated)
    if BASE<=base<BASE+len(image):
        (out/'main-with-module-OFFLINE-ONLY.decoded.bin').write_bytes(modified)
    return image,bytes(modified),original_code,code,module,manifest


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--diagnostic-rgb',action='store_true')
    ap.add_argument('--rgb-tables',type=Path)
    ap.add_argument('--color-controls',type=Path)
    ap.add_argument('--wb-controls',type=Path)
    ap.add_argument('--base',type=lambda v:int(v,0),default=MODULE_BASE)
    args = ap.parse_args()
    document = json.loads(args.rgb_tables.read_text(encoding='utf-8')) if args.rgb_tables else None
    color_document=json.loads(args.color_controls.read_text(encoding='utf-8')) if args.color_controls else None
    wb_document=json.loads(args.wb_controls.read_text(encoding='utf-8')) if args.wb_controls else None
    image,modified,original_code,code,module,manifest = prepare_probe(args.out,args.diagnostic_rgb,document,color_document,wb_document,args.base)
    crosscheck = original_key_crosscheck(image,original_code)
    frames = []
    for recipe in module['recipes']:
        for fmt in (0x200,0x100,0x40,0x1000):
            for secondary in (0x100,0x200):
                for owner in (False,True):
                    row,_ = frame_case(modified,code,image,original_code,module,recipe,fmt,
                        with_owner=owner,secondary=secondary)
                    frames.append(row)
        for contrast,user in ((2,(3,-2,7,7,7)),(-2,(-3,2,-7,-7,-7)),(0,None),
                (-recipe['picture_mode_contrast'],(0,0,-recipe['tone_level']['highlights'],
                    -recipe['tone_level']['midtones'],-recipe['tone_level']['shadows']))):
            row,_ = frame_case(modified,code,image,original_code,module,recipe,user=user,contrast=contrast)
            frames.append(row)
    print(f'Validated {len(frames)} native frame configurations',flush=True)
    extended=extension_boundaries(modified,code,module)
    wb_cases=wb_boundaries(modified,code,module)
    cache = cache_sequence(modified,code,image,original_code,module)
    passthrough = passthrough_cases(modified,code,image,original_code,module)
    refs = owner_reference_case(modified,code,image,original_code,module)
    connected = connected_cases(modified,code,module)
    print(f'Validated {len(connected)} connected native jobs (no hardware completion)',flush=True)
    routes = route_cases(bytes(modified),code,image,original_code,module)
    flags = flag_routes(bytes(modified),code,image,original_code)
    require(MAIN.read_bytes()==image,'original main changed')
    sources = ('epl9_film_late_module.py','epl9_film_late_probe.py','epl9_film_module.py',
        'epl9_film_handoff.py','epl9_film_module_probe.py','epl9_job_probe.py','mn103_emit.py',
        'mn103_subset.py','mn103_calls.py','mn103_models.py','epl9_color_extension.py','epl9_wb_extension.py','epl9_wb_probe.py','epl9_placement.py')
    report = dict(module=manifest,frame_cases=frames,route_cases=routes,flag_cases=flags,
        attached_object_original_key_crosscheck=crosscheck,
        cache_sequence=cache,passthrough_cases=passthrough,native_owner_reference_case=refs,connected_jobs=connected,
        extended_color_boundary_cases=extended,
        early_gain_boundary_cases=wb_cases,
        source_sha256={name:sha((ROOT/'scripts'/name).read_bytes()) for name in sources},
        added_native_windows={name:[hex(a),hex(b)] for name,(a,b) in LATE_WINDOWS.items()},
        original_art_identity_preserved=True,new_owner_allocation=False,owner_header_mutation=False,
        original_firmware_unchanged=True,private_instruction_copy_modified=True,hardware_pixels=False)
    (args.out/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(out=str(args.out),frames=len(frames),routes=len(routes),flags=flags,
        owner_object_unchanged=True),indent=2))


if __name__ == '__main__':
    main()
