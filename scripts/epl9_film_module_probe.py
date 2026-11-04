"""Execute emitted film machine code with exact E-PL9 native instructions.

Owner buffers/callers remain explicit fixtures. No host PC redirection or
Python write installs a recipe in a running request. No hardware is modeled.
"""
import argparse
import json
from pathlib import Path
import struct
import subprocess

from epl9_film_module import build_module, emit_files, require, MODULE_BASE
from epl9_film_handoff import load_code, base_request, native_tone, matrix_oracle
from epl9_workspace_bridge import ROOT, BASE, MAIN, sha
from epl9_integrated_probe import native, attempt, RETURN, full_route, WINDOWS, EXTRA_WINDOWS, SERVICE_WINDOWS
from epl9_offline_prototype import JOB, REQUEST, CONTEXT, OUTPUT, OBJECT, TABLE, SP, header, route
from mn103_subset import Region, parse_listing
from mn103_models import FillModel

CONTROLS, USER_CONTROLS = 0x1a000000, 0x1a001000


def call(m, entry, mask, frame, regs):
    m.r.update(regs)
    saved = {k:m.r[k] for k in m.saved(mask)}
    result = attempt(m,entry,mask,frame)
    require(result.get('pc') == RETURN and m.r['sp'] == SP
            and all(m.r[k] == v for k,v in saved.items()), f'native module call failed: {result}')
    return result


def native_routes(image, code, original_image, original_code, module):
    results = []
    for key in (0x01010078,0x01020078,1,11,0x01030078):
        for kind in (0x200,0x100,0x40):
            for selector in (0,2):
                for flags in (0,0x10000,0x20000,0x30000):
                    expected, reference = full_route(original_image,original_code,key,kind,selector,flags,True)
                    job, parameter = bytearray(14552), bytearray([0xa5])*4200
                    job[12:16] = header(key)
                    struct.pack_into('<I',job,10384,key)
                    struct.pack_into('<I',job,16,flags)
                    struct.pack_into('<H',job,20,kind)
                    job[25] = selector
                    m = native(image,code,[Region(JOB,job,True),Region(OBJECT,parameter,True),
                        Region(module['base'],module['data'])],{})
                    call(m,0x607519b8,0xf0,40,dict(a0=JOB))
                    routed = module['symbols']['film_route_gate'] in m.trace
                    call(m,module['symbols']['film_commit_job'],0,0,dict(a0=JOB,a1=OBJECT))
                    if key in (0x01010078,0x01020078):
                        require(struct.unpack_from('<I',job,12320)[0] == OBJECT, 'job object not attached')
                        require(struct.unpack_from('<I',parameter,20)[0] == key, 'recipe identity lost')
                        oracle = bytearray(expected)
                        struct.pack_into('<I',oracle,12320,OBJECT)
                        require(job == oracle, 'native schedule/handoff differs from historical scoped fix')
                    else:
                        require(job == expected and parameter == b'\xa5'*4200, 'non-target job changed')
                    require(routed == reference['redirected'], 'native gate reached a different routing context')
                    results.append(dict(key=hex(key),kind=hex(kind),selector=selector,flags=hex(flags),
                        native_gate=routed, complete_job_bytes_compared=14552))
    return results


def flag_routes(image,code,original_image,original_code):
    count = 0
    for key in (0x01010078,0x01020078,1,11,0x01030078):
        for kind in (0x200,0x100,0x40):
            for selector in (0,2):
                for flags in (0,*[1<<n for n in range(32)],0x30000,0x60000):
                    _,expected = route(original_image,original_code,key,kind,selector,True,
                                       flags=flags,return_job=True)
                    _,actual = route(image,code,key,kind,selector,False,flags=flags,return_job=True)
                    if key in (0x01010078,0x01020078):
                        actual[12:16] = header(11)
                        struct.pack_into('<I',actual,10384,11)
                    require(actual == expected, 'native gate differs from historical flag-grid oracle')
                    count += 1
    return count


def frame(image, code, module, recipe, fmt=0x200, contrast=0, user=(0,0,0,0,0), inplace=False):
    key = int(recipe['watercolor_key'],16)
    r, c, o = base_request(fmt=fmt), bytearray(128), bytearray(5200)
    r[8:12] = header(key)
    r[1795] = contrast & 255
    r[1797] = 23  # Must survive normalization before the native constructor.
    struct.pack_into('<I',r,1512,0 if user is None else CONTROLS if inplace else USER_CONTROLS)
    matrix = (128,4,-2,2,128,0,0,-2,128)
    struct.pack_into('<9h',r,1592,*matrix)
    original = bytes(r)
    parameter, controls = bytearray([0xa5])*4200, bytearray([0xcc])*26
    user_values = user if user is not None else (0,0,0,0,0)
    user_bytes = struct.pack('<5h',*user_values)
    if inplace:
        controls[:10] = user_bytes
    param_region = Region(OBJECT,parameter,True)
    for at,value in ((4,REQUEST),(12,OUTPUT),(52,11),(60,0x10000000)):
        struct.pack_into('<I',c,at,value)
    m = native(image,code,[Region(REQUEST,r,True),Region(CONTEXT,c,True),Region(OUTPUT,o,True),
        param_region,Region(CONTROLS,controls,True),Region(USER_CONTROLS,user_bytes),
        Region(module['base'],module['data'])],{}, {0x4700111e:FillModel()})
    call(m,module['symbols']['film_prepare_frame'],0xf0,44,
         dict(a0=REQUEST,a1=OBJECT,d0=key,d1=CONTROLS))
    index = 0 if key == 0x01010078 else 1
    require(m.r['d0'] == index+1, 'wrong native recipe result')
    row = recipe['tone_level']
    clamp = lambda value, limit: max(-limit,min(limit,value))
    expected_controls = (*user_values[:2],clamp(user_values[2]+row['highlights'],7),
        clamp(user_values[3]+row['midtones'],7),clamp(user_values[4]+row['shadows'],7))
    expected_contrast = clamp(contrast+recipe['picture_mode_contrast'],2)
    require(struct.unpack_from('<5h',controls) == expected_controls, 'native H/S/M merge differs from oracle')
    require(controls[10:] == b'\xcc'*16 and parameter[4184:] == b'\xa5'*16, 'owner allocation guard changed')
    require(r[8:12] == header(11) and struct.unpack_from('<b',r,1795)[0] == expected_contrast,
            'request key or contrast incorrect')
    require(struct.unpack_from('<I',r,1512)[0] == CONTROLS and struct.unpack_from('<I',r,1524)[0] == OBJECT,
            'request did not retain owner buffers')
    require(struct.unpack_from('<I',parameter,20)[0] == key, 'native constructor lost recipe token')
    allowed = [(8,12),(1512,1516),(1524,1528),(1795,1796)]
    require(all(a == b or any(start <= n < end for start,end in allowed)
        for n,(a,b) in enumerate(zip(original,r))), 'unrelated request field changed')
    param_region.writable = False
    call(m,0x6074a061,0,16,dict(a0=CONTROLS,a1=CONTEXT+64))
    call(m,0x6079fb88,0xf0,40,dict(a0=CONTEXT))
    require(module['symbols']['film_gamma_hook'] in m.trace, 'emitted gamma hook was not executed')
    prefix = 'GOLD' if index == 0 else 'PORTRA'
    require(struct.unpack_from('<3I',o,2596) == tuple(module['constants'][f'{prefix}_RGB{n}'] for n in range(3)),
            'machine-code gamma hook failed to retain pointers')
    expected_tone = native_tone(image,code,dict(recipe,picture_mode_contrast=expected_contrast,
        tone_level=dict(highlights=expected_controls[2],midtones=expected_controls[3],shadows=expected_controls[4])))
    tone_pointer = struct.unpack_from('<I',o,2608)[0]
    actual_tone = b''.join(m.memory.read(tone_pointer+n*2,2).to_bytes(2,'little') for n in range(256))
    require(actual_tone == expected_tone, 'full native frame tone differs from once-applied oracle')
    require(struct.unpack_from('<9h',o,80) == matrix_oracle(matrix), 'native calibration matrix changed')
    table_at = module['constants'][prefix+'_HSL']-module['base']
    expected_hsl = [struct.unpack_from('<3h',module['data'],table_at+n*28+12) for n in range(12)]
    require([struct.unpack_from('<3h',o,688+n*24+18) for n in range(12)] == expected_hsl, 'native HSL recipe lost')
    return dict(name=recipe['name'],input_format=hex(fmt),user_contrast=contrast,
        user_tone=list(user) if user is not None else None,inplace_controls=inplace,
        merged_contrast=expected_contrast,merged_tone=list(expected_controls),instructions=len(m.trace),
        native_prepare=True,native_gamma=True,active_hsm=any(expected_controls),unrelated_request_fields_preserved=True,
        tone_sha256=sha(expected_tone),pixel_processing_executed=False)


def non_target_frames(image,code,module):
    reports = []
    for key in (1,11,0x01030078,0x01010079):
        r = base_request(key)
        parameter,controls = bytearray([0xa5])*4200,bytearray([0xcc])*26
        before = bytes(r)
        m = native(image,code,[Region(REQUEST,r,True),Region(OBJECT,parameter,True),
            Region(CONTROLS,controls,True),Region(module['base'],module['data'])],{})
        call(m,module['symbols']['film_prepare_frame'],0xf0,44,
             dict(a0=REQUEST,a1=OBJECT,d0=key,d1=CONTROLS))
        require(m.r['d0'] == 0 and r == before and parameter == b'\xa5'*4200
            and controls == b'\xcc'*26, 'native preparation touched a non-target frame')
        reports.append(dict(key=hex(key),all_payload_bytes_unchanged=True))
    for absent in ('parameter','controls'):
        r,parameter,controls = base_request(),bytearray([0xa5])*4200,bytearray([0xcc])*26
        before = bytes(r)
        m = native(image,code,[Region(REQUEST,r,True),Region(OBJECT,parameter,True),
            Region(CONTROLS,controls,True),Region(module['base'],module['data'])],{})
        call(m,module['symbols']['film_prepare_frame'],0xf0,44,dict(a0=REQUEST,
             a1=0 if absent == 'parameter' else OBJECT,d0=0x01010078,d1=0 if absent == 'controls' else CONTROLS))
        require(m.r['d0'] == 0 and r == before and parameter == b'\xa5'*4200
            and controls == b'\xcc'*26, 'missing owner buffer caused partial mutation')
        reports.append(dict(missing_owner_buffer=absent,all_payload_bytes_unchanged=True))
    return reports


def passthrough_frames(image,code,original_image,original_code,module):
    reports = []
    for key in (1,11):
        for fmt in (0x200,0x100,0x40):
            observed = []
            for binary,instructions in ((original_image,original_code),(image,code)):
                r,c,o = base_request(key,fmt),bytearray(128),bytearray(5200)
                for at,value in ((4,REQUEST),(12,OUTPUT),(52,key),(60,2)):
                    struct.pack_into('<I',c,at,value)
                m = native(binary,instructions,[Region(REQUEST,r),Region(CONTEXT,c,True),Region(OUTPUT,o,True),
                    Region(module['base'],module['data'])],{})
                call(m,0x6079fb88,0xf0,40,dict(a0=CONTEXT))
                observed.append(bytes(o))
            require(observed[0] == observed[1], 'gamma call replacement changed a non-recipe configuration')
            reports.append(dict(key=hex(key),input_format=hex(fmt),full_configuration_bytes_compared=5200))
    return reports


def gamma_guard_cases(image,code,original_image,original_code,module):
    r,parameter,controls = base_request(),bytearray([0xa5])*4200,bytearray(10)
    m = native(image,code,[Region(REQUEST,r,True),Region(OBJECT,parameter,True),
        Region(CONTROLS,controls,True),Region(module['base'],module['data'])],{},
        {0x4700111e:FillModel()})
    call(m,module['symbols']['film_prepare_frame'],0xf0,44,
        dict(a0=REQUEST,a1=OBJECT,d0=0x01010078,d1=CONTROLS))
    reports = []
    for field,value,size in ((14,0x209,2),(28,0x209,2),(48,4,1),(1832,0x101,2)):
        request = bytearray(r)
        request[field:field+size] = value.to_bytes(size,'little')
        observations = []
        for binary,instructions,entry in ((original_image,original_code,0x6079d328),
                                         (image,code,module['symbols']['film_gamma_hook'])):
            output = bytearray(5200)
            trial = native(binary,instructions,[Region(REQUEST,request),Region(OBJECT,bytes(parameter)),
                Region(CONTROLS,bytes(controls)),Region(OUTPUT,output,True),
                Region(module['base'],module['data'])],{})
            call(trial,entry,0xf0,28,dict(a0=REQUEST,a1=OUTPUT+4000,d0=OUTPUT+4004,d1=OUTPUT+4008))
            observations.append((bytes(output),trial.r['d0']))
            if entry != 0x6079d328:
                require(trial.memory.read(SP+61,1) == (trial.r['d0'] & 255),
                        'displaced selector-result store was not reproduced')
        require(observations[0] == observations[1], 'gamma guard changed a native special-format result')
        reports.append(dict(field_offset=field,value=hex(value),selector_outputs_and_return_unchanged=True))
    return reports


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--diagnostic-rgb',action='store_true')
    args = ap.parse_args()
    require(not args.out.exists() and args.out.resolve().is_relative_to((ROOT/'local').resolve()),
            'requires a new ignored local directory')
    reader = ROOT/'local/mn103-tooling/mn103-reader.exe'
    image,original_code,_ = load_code(MAIN,reader)
    module = build_module(image,diagnostic_rgb=args.diagnostic_rgb)
    module_code,manifest = emit_files(module,args.out)
    code = dict(original_code)
    # Needed only for complete historical worklist comparisons.
    for start,stop in set([*WINDOWS.values(),*EXTRA_WINDOWS.values(),*SERVICE_WINDOWS.values()]):
        listing = subprocess.check_output([str(reader),str(MAIN),hex(BASE),hex(start-BASE),hex(stop-BASE)],text=True)
        code.update(parse_listing(listing,image,BASE))
    original_code = dict(code)
    patched = bytearray(image)
    for index,p in enumerate(module['patches']):
        raw = bytes.fromhex(p['after'])
        patched[p['address']-BASE:p['address']-BASE+len(raw)] = raw
        path = args.out/f'candidate-hook-{index}.bin'
        path.write_bytes(raw)
        listing = subprocess.check_output([str(reader),str(path.resolve()),hex(p['address']),'0',hex(len(raw))],text=True)
        # Remove every displaced original instruction, then load actual patch bytes.
        for at in [at for at in code if p['address'] <= at < p['address']+len(raw)]:
            del code[at]
        code.update(parse_listing(listing,raw,p['address']))
    code.update(module_code)
    routes = native_routes(bytes(patched),code,image,original_code,module)
    flags = flag_routes(bytes(patched),code,image,original_code)
    frames = [frame(bytes(patched),code,module,row,fmt) for row in module['recipes'] for fmt in (0x200,0x100,0x40)]
    for row in module['recipes']:
        for contrast,user in ((-2,(0,0,-7,-7,-7)),(2,(0,0,7,7,7))):
            frames.append(frame(bytes(patched),code,module,row,contrast=contrast,user=user))
        frames.append(frame(bytes(patched),code,module,row,user=None))
        frames.append(frame(bytes(patched),code,module,row,user=(0,0,2,-1,-2),inplace=True))
        levels = row['tone_level']
        frames.append(frame(bytes(patched),code,module,row,contrast=-row['picture_mode_contrast'],
            user=(0,0,-levels['highlights'],-levels['midtones'],-levels['shadows'])))
    controls = non_target_frames(bytes(patched),code,module)
    passthrough = passthrough_frames(bytes(patched),code,image,original_code,module)
    gamma_guards = gamma_guard_cases(bytes(patched),code,image,original_code,module)
    require(MAIN.read_bytes() == image, 'original main changed')
    report = dict(module=manifest,worklist_cases=routes,branch_flag_cases=flags,frame_cases=frames,
        non_target_frames=controls,passthrough_frames=passthrough,gamma_guards=gamma_guards,
        host_pc_redirection=False,host_recipe_pointer_injection=False,full_pixel_cycle=False,
        limits=['Owner buffers and invocation points are synthetic; real owner call sites remain unbound.',
                'Default RGB contents are stock; diagnostic RGB is not film calibrated.',
                'No hardware completion, image, camera operation, firmware container or placement claim.'])
    (args.out/'validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(out=str(args.out),code_bytes=module['code_bytes'],worklist_cases=len(routes),
        branch_flag_cases=flags,native_frame_cases=len(frames),non_target_frames=len(controls),
        passthrough_frames=len(passthrough),full_pixel_cycle=False),indent=2))


if __name__ == '__main__':
    main()
