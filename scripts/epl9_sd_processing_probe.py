"""Offline SD -> persistent descriptor -> native COLOR/WB configuration.

Hardware processing stops at its real unmapped peripheral boundary.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import types
from dataclasses import replace

from epl9_workspace_bridge import ROOT, MAIN, MAIN_SHA, BASE
from epl9_sd_state import build as build_state, ROOT_ADDRESS
from epl9_sd_state_probe import StateFixture, PublicationMemory, stock_listings, MANAGER
from epl9_sd_loader_probe import require, GUARD, STOP, STACK
from epl9_sd_processing import build, overlay, descriptor, TEST_KEYS, RECORD, GAMMA, STRIDE, BASE_ADDRESS
from epl9_sd_recipes import unpack_recipe, pack_recipe
from epl9_wifi_prototype import Evidence, span
from epl9_tonal_drafts import READER_SHA
from epl9_film_handoff import WINDOWS as FILM_WINDOWS, base_request
from epl9_film_late_probe import LATE_WINDOWS, owner_object
from epl9_integrated_probe import WINDOWS, EXTRA_WINDOWS, SERVICE_WINDOWS
from epl9_job_probe import JOB_WINDOWS, experiment
from epl9_offline_prototype import header
from epl9_wb_extension import adjusted
from epl9_float_contract import models as float_models
from mn103_subset import Memory, Region, parse_listing
from mn103_calls import CallMachine
from mn103_emit import memory as memory_operand
from mn103_models import FillModel

ARENA=0x61fc0000
REQ,CTX,OUT,CACHE,OWNER,USER=(0x18000000,0x18001000,0x18002000,0x18004000,0x18006000,0x18008000)


def decode(module,out,reader):
    out.mkdir();raw=module['data'][:module['code_bytes']]
    path=out/'code.bin';path.write_bytes(raw)
    listing=subprocess.check_output([str(reader),str(path),hex(module['base']),'0',hex(len(raw))],text=True)
    code=parse_listing(listing,raw,module['base'])
    require(set(code)=={r[0] for r in module['rows']},'GNU instruction boundaries differ')
    for pc,op,args,n in module['rows']:
        binary,actual,observed=code[pc]
        require(actual==op and len(binary)==n and len(args)==len(observed),'GNU opcode/length differs')
        for expected,got in zip(args,observed):
            if expected in module['symbols']:require(int(got,0)==module['symbols'][expected],'GNU target differs')
            elif expected.startswith('('):require(memory_operand(expected)==memory_operand(got),'GNU memory operand differs')
            elif expected.startswith('[') or expected in ('d0','d1','d2','d3','a0','a1','a2','a3','sp'):
                require(expected==got,'GNU register differs')
            else:require(int(expected,0)&0xffffffff==int(got,0)&0xffffffff,'GNU scalar differs')
    module['code']=code;(out/'native.tsv').write_text(listing);(out/'native.s').write_text(module['source'])
    (out/'module-SYNTHETIC-ONLY.bin').write_bytes(module['data'])


class ProcessingFixture(StateFixture):
    def __init__(self,state,consumer,files,image,code,evidence,**kw):
        super().__init__(state,files,image=image,code=code,evidence=evidence,**kw)
        self.consumer=consumer
        self.pools[0x10004].append(ARENA)
        self.regions += [Region(ARENA-16,bytearray(GUARD+b'\xcd'*16384+GUARD),True,'finite pool descriptor arena'),
                         Region(consumer['base'],bytearray(consumer['data']),False,'processing module')]
        self.memory=PublicationMemory(self.regions,self)
        self.code.update(consumer['code'])
        self.fail_arena=False

    def pool_allocate(self,m):
        if self.requested==8192 and self.fail_arena:
            self.counts['alloc_8192']+=1;m.r['a0']=0;return
        return super().pool_allocate(m)

    def selected_descriptor(self,slot):
        return self.invoke(self.consumer['symbols']['sd_descriptor'],0xf0,24,d0=slot).r['a0']


def frame(f,stock,original,slot,*,fmt=0x200,user=(0,)*5,contrast=0,owner=True,state=None,oracle=False,key=None,stock_only=False,force=False):
    key=TEST_KEYS[slot-1] if key is None else key
    desc=f.selected_descriptor(slot)
    raw=bytes(span(f.memory,desc+RECORD,660));recipe=unpack_recipe(raw)
    request=base_request(key,fmt);request[1795]=contrast&255
    struct.pack_into('<I',request,1484,CACHE)
    struct.pack_into('<I',request,1512,USER if user is not None else 0)
    struct.pack_into('<9h',request,1592,128,10,-6,8,128,-4,-2,6,128)
    neutral=base_request(11,fmt)
    obj=owner_object(original,stock,neutral,user) if owner else bytes(4200)
    struct.pack_into('<I',request,1524,OWNER if owner else 0)
    before=bytes(request)
    context=bytearray(128)
    for at,value in ((4,REQ),(12,OUT),(52,key),(60,0 if state and not force else 0x10000002)):
        struct.pack_into('<I',context,at,value)
    output,cache=(bytearray(v) for v in state) if state else (bytearray(5200),bytearray(6000))
    merged=user or (0,)*5
    if oracle:
        clamp=lambda x,n:max(-n,min(n,x))
        request[8:12]=header(11);request[1795]=clamp(contrast+recipe.contrast,2)&255
        merged=(*merged[:2],*(clamp(x+y,7) for x,y in zip(merged[2:],recipe.tone)))
        struct.pack_into('<I',request,1512,USER)
        struct.pack_into('<I',context,52,11);struct.pack_into('<I',context,60,0x10000002)
    regions=[Region(r.address,r.data,False,r.name) if r.name.startswith('finite pool') else r
             for r in f.regions if r.address!=BASE]
    regions += [Region(BASE,original if oracle or stock_only else f.image),Region(REQ,request,True,'frame request'),
        Region(CTX,context,True,'frame context'),Region(OUT,output,True,'native ISP configuration'),
        Region(CACHE,cache,True,'native cache'),Region(OWNER,bytearray(obj),False,'unchanged native owner'),
        Region(USER,bytearray(struct.pack('<5h',*merged)),False,'user controls')]
    m=CallMachine(stock if oracle or stock_only else f.code,Memory(regions),dict(sp=STACK+0x30000),models={0x4700111e:FillModel()})
    def call(entry,mask,fr,**regs):
        m.r.update(regs);sp=m.r['sp'];saved={r:m.r[r] for r in m.saved(mask)}
        result=m.run(m.enter(entry,STOP,mask,fr),[STOP],limit=500000)
        require(result.get('pc')==STOP and m.r['sp']==sp and all(m.r[k]==v for k,v in saved.items()),f'frame call failed: {result}')
    if user is not None or oracle:call(0x6074a061,0,16,a0=USER,a1=CTX+64)
    before_context=bytes(context)
    call(0x6079fb88,0xf0,40,a0=CTX)
    native_return=m.r['d0']
    if oracle:
        table=m.memory.read(desc+16,4);gamma=m.memory.read(desc+24,4)
        call(0x6079e50e,0xf0,80,a0=table,a1=OUT,d0=m.memory.read(table+3024,2))
        m.memory.write(REQ+1524,0,4)
        call(0x6079f309,0xf0,32,a0=CTX)
        call(0x6079d7a0,0xa0,8,a0=OUT,a1=gamma,d0=gamma,d1=gamma)
    elif not stock_only:
        require(bytes(request)==before and bytes(context)==before_context,'caller request/context changed')
    return dict(output=bytes(output),cache=bytes(cache),ret=native_return,m=m,descriptor=desc,recipe=recipe)


def wb_case(f,slot,values,fmt=0x200,valid_header=True):
    request=base_request(TEST_KEYS[slot-1] if valid_header else 11,fmt)
    struct.pack_into('<4H',request,1568,*values);before=bytes(request)
    desc=f.selected_descriptor(slot);recipe=unpack_recipe(bytes(span(f.memory,desc+RECORD,660)))
    m=CallMachine(f.code,Memory([*f.regions,Region(REQ,request,True)]),
        dict(sp=STACK+0x30000,a0=0x12340000,a2=REQ,a3=0x33445566,d3=0x55667788))
    sp=m.r['sp'];saved={k:m.r[k] for k in ('a0','a2','a3','d3')}
    result=m.run(f.consumer['symbols']['sd_pipeline_wb_hook'],[0x6074f357])
    require(result.get('pc')==0x6074f357 and m.r['sp']==sp and
            all(m.r[k]==v for k,v in saved.items()),'early WB hook lost live registers')
    expected=adjusted(values,recipe.wb_q10) if valid_header else values
    require(tuple(struct.unpack_from('<4H',request,1568))==expected,'dynamic WB arithmetic differs')
    control=bytearray(before);struct.pack_into('<4H',control,1568,*expected)
    require(request==control and m.r['d0']==0 and m.r['d2']==0 and m.r['a1']==3710,'WB replay/output differs')
    return dict(slot=slot,input=values,output=expected,request_bytes_checked=1876)


def connected(f):
    # Extend only this harness's accepted input grid; shared probe is unchanged.
    globals_copy=dict(experiment.__globals__,RECIPES={k:f'T{i+1}' for i,k in enumerate(TEST_KEYS)})
    run=types.FunctionType(experiment.__code__,globals_copy,experiment.__name__,experiment.__defaults__)
    run.__kwdefaults__=experiment.__kwdefaults__
    symbols=dict(f.consumer['symbols'])
    for alias,label in dict(film_route_gate='sd_pipeline_route',film_color_entry='sd_pipeline_color',
        color_post_hsl='pipeline_post_hsl',film_gamma_hook='pipeline_post_hsl',film_wb_entry='sd_pipeline_wb_hook').items():
        symbols[alias]=symbols[label]
    module=dict(f.consumer,symbols=symbols)
    rows=[]
    for slot,key in enumerate(TEST_KEYS,1):
        for kind in (0x200,0x100,0x40):
            observed=[]
            def observer(m):
                regions=[Region(r.address,r.data,False,r.name) for r in f.regions if r.name.startswith('finite pool') or
                         r.address in (ROOT_ADDRESS,f.module['base'])]
                m.memory=Memory([*m.memory.regions,*regions])
                require(not m.code.keys() & float_models().keys(),'float model shadows native code')
                m.models.update(float_models());observed.append(m)
            options=dict(provide_slot=True,input_format=0x100) if kind==0x40 else {}
            job_code={pc:row for pc,row in f.code.items() if pc!=0x604023b2}
            report=run(f.image,job_code,key,kind,0,native_module=module,machine_observer=observer,
                       gain_fixture=(2048,1536,1024,1056),**options)
            require(report.get('native_film',{}).get('recipe_applied'),
                    'connected slot did not apply: '+repr({k:report.get(k) for k in ('constructor','start','executor')}))
            require(report['executor'].get('error', '').endswith('unmapped access at 0x9880014c, size 4'),
                    f'connected path stopped before declared TruePic boundary: {report.get("executor")}')
            film=report['native_film'];desc=f.selected_descriptor(slot)
            recipe=unpack_recipe(bytes(span(f.memory,desc+RECORD,660)))
            require(tuple(film['request_gain_record'])==adjusted((2048,1536,1024,1056),recipe.wb_q10),'connected WB did not reach request')
            require(film['job_header_unchanged'] and film['cached_key_unchanged'],'job identity changed')
            require([int(p,16) for p in film['gamma_pointers']]==[desc+GAMMA]*3,'connected gamma not selected')
            rows.append(dict(slot=slot,kind=kind,executor=report['executor'],film=film,
                             event_bits_signalled=report['event_bits_signalled'],pixels=False))
    return rows


def transitions(f,stock,image):
    state=None;rows=[]
    for slot in (1,1,2,2,1):
        result=frame(f,stock,image,slot,state=state)
        expected=frame(f,stock,image,slot,state=state,oracle=True)
        require(result['output']==expected['output'],'warm T1/T2 cache mismatch')
        state=(result['output'],result['cache']);rows.append(dict(slot=slot,bytes_checked=5200))
    for key in (11,11,1,1):
        result=frame(f,stock,image,1,state=state,key=key)
        expected=frame(f,stock,image,1,state=state,key=key,stock_only=True,force=True)
        require(result['output']==expected['output'],'recipe exit left cached parameters')
        state=(result['output'],result['cache']);rows.append(dict(key=key,bytes_checked=5200))
    for key in (1,11,0x01010078,0x01020078):
        result=frame(f,stock,image,1,key=key)
        expected=frame(f,stock,image,1,key=key,stock_only=True)
        require(result['output']==expected['output'] and result['ret']==expected['ret'],'unrelated mode changed')
        rows.append(dict(passthrough=hex(key),bytes_checked=5200))
    return rows


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--reuse',type=Path)
    ap.add_argument('--jobs-only',action='store_true',help='development run; not a complete validation report')
    a=ap.parse_args()
    require(not a.out.exists() and a.out.resolve().is_relative_to((ROOT/'local').resolve()),'new local output required')
    a.out.mkdir();image=MAIN.read_bytes();require(hashlib.sha256(image).hexdigest()==MAIN_SHA,'wrong E-PL9 main')
    previous=json.loads((ROOT/'local/epl9-sd-state-probe-20261107-final-v2/validation.json').read_text())
    protected=previous['protected_inputs']
    # Seal the previous state/loader implementation as well as both v3 packages.
    for name in ('scripts/epl9_sd_state.py','firmware_src/epl9_sd_state.s.in','scripts/epl9_sd_state_probe.py'):
        require(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==previous['source_sha256'][str(Path(name))],
                'preceding state generation differs')
        protected.append(dict(path=name,sha256=hashlib.sha256((ROOT/name).read_bytes()).hexdigest()))
    for row in protected:require(hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest()==row['sha256'],'protected source changed')
    reader=ROOT/'local/mn103-tooling/mn103-reader.exe'
    require(hashlib.sha256(reader.read_bytes()).hexdigest()==READER_SHA,'wrong GNU reader')
    defaults=[(ROOT/f'local/epl9-sd-slot-prototype-20261107-final/recipe-{i}-EXPERIMENTAL.RCP').read_bytes() for i in (1,2)]
    state=build_state(defaults)
    require(hashlib.sha256(state['data']).hexdigest()==previous['module_sha256'],'preceding state module differs')
    decode(state,a.out/'state',reader)
    consumer=build(image,state);decode(consumer,a.out/'consumer',reader)
    stock,hashes=stock_listings(image,ROOT/'local/epl9-sd-state-discovery-20261107-final',
        ROOT/'local/epl9-sd-loader-trigger-20261107',ROOT/'local/epl9-sd-slot-audit-20261107-final')
    windows=set([*FILM_WINDOWS,*WINDOWS.values(),*EXTRA_WINDOWS.values(),*SERVICE_WINDOWS.values(),
                 *JOB_WINDOWS.values(),*LATE_WINDOWS.values(),(0x604b83c1,0x604b8900)])
    listings=a.out/'stock';listings.mkdir()
    for start,end in sorted(windows):
        name=f'{start:08x}-{end:08x}.tsv'
        text=(a.reuse/'stock'/name).read_text() if a.reuse else subprocess.check_output(
            [str(reader),str(MAIN),hex(BASE),hex(start-BASE),hex(end-BASE)],text=True)
        stock.update(parse_listing(text,image,BASE));(listings/name).write_text(text)
        hashes[name]=hashlib.sha256(text.encode()).hexdigest()
    patched,patches=overlay(image,state,consumer);code=dict(stock)
    for i,p in enumerate(patches):
        at=p['address'];raw=bytes.fromhex(p['after']);path=a.out/f'hook-{i}.bin';path.write_bytes(raw)
        text=subprocess.check_output([str(reader),str(path),hex(at),'0',hex(len(raw))],text=True)
        for pc in list(code):
            if at<=pc<at+len(raw):del code[pc]
        code.update(parse_listing(text,raw,at))
    evidence=Evidence(ROOT/'local/wifi-limits-20261102-v6')
    def fixture(files=None,**kw):
        f=ProcessingFixture(state,consumer,files or {},patched,code,evidence,**kw);f.image=patched
        return f
    paths=('C:\\EPL9MOD\\SLOT01.RCP','C:\\EPL9MOD\\SLOT02.RCP')
    loader_cases=[];frames=[];wb=[]
    for name,files,options in (('missing',{},{}),('swapped',dict(zip(paths,reversed(defaults))),{}),
        ('mixed',{paths[1]:defaults[0]},{}),('corrupt',{paths[0]:b'bad',paths[1]:defaults[0]},{}),
        ('not_ready',dict(zip(paths,reversed(defaults))),dict(sd_status=0)),
        ('pending',dict(zip(paths,reversed(defaults))),dict(stall=True)),
        ('close_uncertain',dict(zip(paths,reversed(defaults))),dict(close_error=paths[0]))) if not a.jobs_only else ():
        f=fixture(files,**options);f.getter();f.start_task();f.event()
        arena=f.memory.read(MANAGER+212,4)
        require(arena==(0 if name in ('not_ready','pending') else ARENA),'descriptor publication failed')
        for slot in (1,2):
            desc=f.selected_descriptor(slot);source=f.selected(slot)
            raw=bytes(span(f.memory,source,660))
            want=descriptor(image,raw,desc,slot,source)
            actual=bytes(span(f.memory,desc,3764))
            # Padding is intentionally unspecified; compare actual native fields/data.
            require(actual[:28]==want[:28] and actual[64:3092]==want[64:3092] and
                    actual[RECORD:RECORD+660]==raw,'native materializer differs from host oracle')
            for fmt in (0x200,0x100,0x40,0x1000):
                result=frame(f,stock,image,slot,fmt=fmt,user=(1,-1,6,-6,2),contrast=2)
                expected=frame(f,stock,image,slot,fmt=fmt,user=(1,-1,6,-6,2),contrast=2,oracle=True)
                require(result['output']==expected['output'] and result['ret']==expected['ret'],
                        f'{name}/{slot}/{fmt:x}: native processing differs from oracle')
                frames.append(dict(case=name,slot=slot,fmt=fmt,descriptor=hex(desc),bytes_checked=5200,
                    output_sha256=hashlib.sha256(result['output']).hexdigest(),instructions=len(result['m'].trace)))
            for values in ((1,1,1,1),(65535,65535,65535,65535),(2048,1536,1024,1056),(0,100,100,100),(100,100,100,0)):
                wb.append(wb_case(f,slot,values))
        count=dict(f.counts);f.event()
        require(f.counts['alloc_8192']==count.get('alloc_8192',0),'session arena was allocated again')
        f.guards();loader_cases.append(dict(name=name,states=f.states(),arena=hex(arena),counts=dict(f.counts)))
    f=fixture(dict(zip(paths,reversed(defaults))));f.getter();f.start_task();f.event()
    jobs=connected(f)
    warm=transitions(f,stock,image) if not a.jobs_only else []
    if not a.jobs_only:
        missing=fixture();missing.getter();missing.start_task();missing.event()
        jobs+=connected(missing)
        exotic=replace(unpack_recipe(defaults[0]),recipe_id=9999,name='Generic SD boundary',
            hsl=((-1000,-240,-100),(1000,240,100))*6,contrast=-2,tone=(-7,7,-7),wb_q10=(512,2048),
            gamma=tuple(n*16 for n in range(256)))
        x=fixture({paths[0]:pack_recipe(exotic)});x.getter();x.start_task();x.event()
        for user,contrast,owner in (((-7,7,-7,7,-7),-2,False),(None,2,False),((0,)*5,0,True)):
            actual=frame(x,stock,image,1,user=user,contrast=contrast,owner=owner)
            expected=frame(x,stock,image,1,user=user,contrast=contrast,owner=owner,oracle=True)
            require(actual['output']==expected['output'],'arbitrary recipe fields did not reach native configuration')
            frames.append(dict(case='generic_sd_extremes',bytes_checked=5200,owner=owner,user=user))
        wb.append(wb_case(x,1,(65535,65535,100,100)))
        fail=fixture(dict(zip(paths,reversed(defaults))));fail.fail_arena=True
        fail.getter();fail.start_task();fail.event()
        require(fail.selected_descriptor(1)==BASE_ADDRESS+0x2000,'arena failure lost embedded fallback')
        fail.fail_arena=False;fail.event()
        require(fail.selected_descriptor(1)==ARENA,'arena failure did not retry')
    report=dict(model='Olympus E-PL9 / IM008',displayed_version='1.1 (owner)',main_build=1101,
        main_bytes=len(image),main_sha256=MAIN_SHA,module_bytes=len(consumer['data']),code_bytes=consumer['code_bytes'],
        module_sha256=hashlib.sha256(consumer['data']).hexdigest(),module_base=hex(consumer['base']),
        patches=patches,synthetic_keys=[hex(k) for k in TEST_KEYS],frames=frames,loader_cases=loader_cases,wb_cases=wb,connected_jobs=jobs,
        transitions_and_passthrough=warm,complete_validation=not a.jobs_only,
        source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
            (Path(__file__),ROOT/'scripts/epl9_sd_processing.py',ROOT/'firmware_src/epl9_sd_processing.s.in',
             ROOT/'scripts/test_epl9_sd_processing.py')},
        read_backend_listing_hashes=evidence.hashes,state_module_sha256=previous['module_sha256'],
        reader_sha256=READER_SHA,protected_inputs_unchanged=True,
        source_listing_hashes=hashes,protected_inputs=protected,camera_accessed=False,firmware_package_created=False,
        boundaries=['finite pool backing, RTOS/owner/file-service/SD fixtures','native ISP configuration, no hardware pixels'])
    for row in protected:require(hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest()==row['sha256'],'protected input changed')
    (a.out/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(frames=len(frames),code_bytes=consumer['code_bytes'],protected=True)))


if __name__=='__main__':main()
