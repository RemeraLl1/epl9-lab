"""Placed SD modules: native load chunks, pool exclusion and session retention.

No camera, NAND write, encoded package or hardware lifetime claim.
"""

from mn103_tooling import default_reader, verify_reader
import argparse
import json
import struct
import subprocess
from pathlib import Path
from epl9_workspace_bridge import ROOT, MAIN, MAIN_SHA, BASE, sha
from epl9_sd_placement import build, SPANS, STATE_BASE, CONSUMER_BASE, V3_SPAN
from epl9_sd_state import build as synthetic_state, ROOT_ADDRESS
from epl9_sd_processing import build as synthetic_consumer, RECORD
from epl9_sd_processing_probe import (ProcessingFixture, decode, frame, connected, transitions, wb_case,
                                      ARENA, STACK, GUARD, STOP)
from epl9_sd_loader_probe import require
from epl9_sd_state_probe import MANAGER, PublicationMemory
from epl9_wifi_prototype import Evidence, span
from epl9_load_sequence_probe import (LocalStorageRead, EARLY_START, EARLY_END, DESTINATION, cached)
from epl9_deployment_probe import SECTIONS
from epl9_v3_pool_probe import POOLS
from mn103_subset import Machine, Memory, Region, parse_listing, Fault
from mn103_calls import CallMachine


def intersects(lo,hi):return any(lo<a+n and a<hi for a,n in SPANS)


def load_audit(image,candidate,modules,code,drop_last=False):
    size=EARLY_END-EARLY_START
    buffer=bytearray(GUARD+b'\xcd'*size+GUARD)
    stack=bytearray(4096);struct.pack_into('<I',stack,2056,0x406f0000)
    class Read(LocalStorageRead):
        def apply(self,m):
            if drop_last and m.r['d1']==0x40780000:
                m.r['d0']=0;return dict(deliberately_dropped=True)
            return super().apply(m)
    read=Read(candidate,DESTINATION,size)
    m=CallMachine(code,Memory([Region(BASE,image),Region(0x10000000,stack,True),
        Region(DESTINATION-16,buffer,True)]),dict(sp=0x10000800,a2=DESTINATION,d2=size),
        models={0x604009bf:read,0x60400d2f:read})
    result=m.run(0x60401561,[0x6040168b])
    require(result.get('pc')==0x6040168b,'early read planner did not return')
    require(buffer[16:-16]==candidate[EARLY_START-BASE:EARLY_END-BASE],
            'native early read bytes differ or a read was omitted')
    require(buffer[:16]==GUARD and buffer[-16:]==GUARD,'early destination guard changed')
    for module in modules:
        start=16+module['base']-EARLY_START
        require(bytes(buffer[start:start+len(module['data'])])==module['data'],'module was not loaded')
    memory=Memory([Region(BASE,image),Region(0x10000000,bytearray(4096),True),
                   Region(0x6257d800,bytearray(20),True)])
    later=[];initializers=[]
    for entry,end in ((0x60400174,0x604001cb),(0x604001d0,0x604001f0),
        (0x604001f5,0x60400215),(0x6040021a,0x6040023a),(0x6040023f,0x6040025f),(0x60400264,0x6040027b)):
        q=Machine(code,memory,dict(sp=0x10000800));r=q.run(entry,[end]);require(r.get('pc')==end,'startup arguments stopped')
        lo=cached(q.r['a1']);hi=lo+q.r['d1']
        later.append(dict(call=hex(end),start=hex(lo),end=hex(hi),intersects=intersects(lo,hi)))
    require(later[0]['intersects'] and not any(x['intersects'] for x in later[1:]),'competing startup load')
    for entry,end in ((0x6040004d,0x60400059),(0x60400068,0x60400074)):
        q=Machine(code,memory,dict(sp=0x10000800));q.run(entry,[end])
        lo,hi=cached(q.r['d0']),cached(q.r['d1'])
        require(not intersects(lo,hi),'startup initializer overwrites module')
        initializers.append([hex(lo),hex(hi)])
    require(not any(intersects(lo,hi) for lo,hi in SECTIONS),'later section overwrites modules')
    # Subsequent execution receives bytes from the native planned reads, rather
    # than separately mapping/injecting the two module binaries.
    loaded=bytearray(candidate)
    loaded[EARLY_START-BASE:EARLY_END-BASE]=buffer[16:-16]
    return bytes(loaded),dict(chunks=read.calls,loaded_bytes=size,both_modules_match=True,guards_intact=True,
        startup_loads=later,initializers=initializers,later_sections_disjoint=True,
        storage_completion_modeled=True,physical_cache_or_dma_verified=False)


def pool_audit(code,image):
    memory=Memory([])
    def classify(at,row):
        entry,yes,no,_,_,ident=row
        m=Machine(code,memory,dict(a0=at));r=m.run(entry,[yes,no])
        require(r.get('pc') in (yes,no),'classifier crossed free/log boundary')
        return r['pc']==yes,m.r['d0']
    for row in POOLS:
        for at in (row[3],row[4]-1):require(classify(at,row)==(True,row[5]),'pool boundary differs')
    count=0
    for base,size in SPANS:
        for lo in (base,(base&0x3fffffff)|0x80000000):
            for at in range(lo,lo+size,4):
                for row in (POOLS[0],POOLS[3],POOLS[6]):
                    require(not classify(at,row)[0],'module address accepted as pool block');count+=1
    tables=[]
    for at in range(0x60405f10,0x60405f80,16):
        start,block,n,marker=struct.unpack_from('<4I',image,at-BASE)
        row=next(r for r in POOLS if r[3]==start)
        require(start+(block+64)*n==row[4],'ROM pool extent differs')
        lo,hi=start&0x3fffffff,row[4]&0x3fffffff
        require(not any(lo<(a&0x3fffffff)+size and (a&0x3fffffff)<hi for a,size in SPANS),'pool alias overlap')
        tables.append(dict(start=hex(start),end=hex(row[4]),block_bytes=block,count=n,id=hex(row[5])))
    return dict(boundary_controls=14,rejected_native_word_checks=count,rom_pools=tables,
                classified_pool_overlap=False,all_runtime_writers_excluded=False)


class PlacedFixture(ProcessingFixture):
    def __init__(self,state,consumer,synthetics,files,image,code,evidence):
        super().__init__(*synthetics,files,image,code,evidence)
        self.module,self.consumer=state,consumer
        self.code={pc:r for pc,r in code.items() if not any(a<=pc<a+n for a,n in SPANS)}
        self.code.update(state['code']);self.code.update(consumer['code'])
        self.regions=[r for r in self.regions if r.address not in (synthetics[0]['base'],synthetics[1]['base'])]
        self.memory=PublicationMemory(self.regions,self);self.image=image


def retained(f,stock,reference):
    f.getter();f.start_task();f.event()
    require(f.memory.read(MANAGER+212,4)==ARENA,'arena was not published')
    selection=[f.selected_descriptor(i) for i in (1,2)]
    snapshots={at:bytes(span(f.memory,at,4096)) for at in selection}
    slots=[f.selected(i) for i in (1,2)]
    before=list(f.allocated);opens=f.counts['open'];arenas=f.counts['alloc_8192']
    rows=[]
    for slot in (1,2):
        for fmt in (0x200,0x100,0x40,0x1000):
            actual=frame(f,stock,reference,slot,fmt=fmt,user=(1,-1,7,-7,4),contrast=-2)
            expected=frame(f,stock,reference,slot,fmt=fmt,user=(1,-1,7,-7,4),contrast=-2,oracle=True)
            require(actual['output']==expected['output'] and actual['ret']==expected['ret'],'placed configuration oracle mismatch')
            rows.append(dict(slot=slot,fmt=fmt,checked_bytes=5200))
    warm=transitions(f,stock,reference)
    for slot in (1,2):wb_case(f,slot,(65535,50000,1024,1056))
    spare=0x61fc5000
    region=Region(spare-16,bytearray(GUARD+b'\xcd'*16384+GUARD),True,'finite pool temporary reuse')
    f.regions.append(region);f.pools[0x10004].append(spare)
    f.memory=PublicationMemory(f.regions,f)
    addresses=[]
    for _ in range(16):
        for size in (2048,8192):
            ptr=f.invoke(0x60402373,0,4,d0=size).r['a0']
            require(ptr not in before,'temporary allocation reused a retained block')
            addresses.append(hex(ptr));f.invoke(0x604023b2,0,4,a0=ptr)
        f.getter();f.event()
    require(f.counts['open']==opens and f.counts['alloc_8192']==arenas+16,'frame/event performed another file load or arena allocation')
    require(all(bytes(span(f.memory,at,4096))==raw for at,raw in snapshots.items()),'retained descriptor changed')
    require(all(at in f.allocated for at in (*slots,ARENA,MANAGER) if at in before),'retained block freed')
    f.guards()
    jobs=connected(f)
    return dict(configurations=rows,cache_controls=warm,connected_jobs=jobs,temporary_reuse_calls=32,
        temporary_addresses=sorted(set(addresses)),retained_blocks_unchanged=True,
        module_separate_regions_absent=not any(r.address in (STATE_BASE,CONSUMER_BASE) for r in f.regions),
        manager_pointer=hex(MANAGER),arena_pointer=hex(ARENA),selection=[hex(a) for a in selection])


def lifetime_negative_controls(f):
    f.getter();f.start_task();f.event()
    # Execute only the native HLS destructor prefix, stopping before its base
    # destructor. This is not a simulated complete shutdown or task cancellation.
    m=f.machine(dict(sp=STACK+0x28000,a0=MANAGER))
    result=m.run(m.enter(0x60ae1910,STOP,0,0),[0x60ae1944])
    require(result.get('pc')==0x60ae1944,'destructor prefix did not reach base cleanup boundary')
    require(f.counts['free_40']==2 and f.counts['free_1024']==3,'native vectors did not free')
    require(ARENA in f.allocated,'destructor prefix unexpectedly released new arena')
    # Deliberate allocator-boundary violation to falsify any whole-lifetime claim:
    # native free + native getter show that the singleton root is not ownership.
    f.invoke(0x604023b2,0,4,a0=MANAGER)
    require(MANAGER not in f.allocated and f.getter()==MANAGER and f.memory.read(ROOT_ADDRESS,4)==MANAGER,
            'stale-root negative control no longer reproduces')
    return dict(native_destructor_prefix_stopped='0x60ae1944',native_vector_releases=5,
        descriptor_arena_not_released_by_prefix=True,
        deliberately_freed_manager_is_returned_by_getter=True,
        actual_shutdown_or_camera_race_measured=False,full_teardown_qualified=False,
        requirement='retain singleton, descriptor arena and accepted file blocks until all consumers are quiescent; teardown protocol remains open')


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();require(not a.out.exists() and a.out.resolve().is_relative_to((ROOT/'local').resolve()),'new ignored output required')
    image=MAIN.read_bytes();require(len(image)==26214336 and sha(image)==MAIN_SHA,'wrong E-PL9 main')
    prior=ROOT/'local/epl9-sd-processing-20261110-final';previous=json.loads((prior/'validation.json').read_text())
    protected=list(previous['protected_inputs'])
    for name,value in previous['source_sha256'].items():
        require(sha((ROOT/name).read_bytes())==value,'prior consumer source changed')
        protected.append(dict(path=name,sha256=value))
    for row in protected:require(sha((ROOT/row['path']).read_bytes())==row['sha256'],'protected input changed')
    reader=default_reader();verify_reader(reader)
    defaults=[(ROOT/f'local/epl9-sd-slot-prototype-20261107-final/recipe-{i}-EXPERIMENTAL.RCP').read_bytes() for i in (1,2)]
    state,consumer,candidate,reference,patches=build(image,defaults)
    a.out.mkdir();decode(state,a.out/'state',reader);decode(consumer,a.out/'consumer',reader)
    stock={};listing_hashes={}
    for p in sorted((prior/'stock').glob('*.tsv')):
        stock.update(parse_listing(p.read_text(),image,BASE));listing_hashes[p.name]=sha(p.read_bytes())
    # State constructors/classifiers are additional to the processing windows.
    from epl9_sd_state_probe import stock_listings
    extra,hashes=stock_listings(image,ROOT/'local/epl9-sd-state-discovery-20261107-final',
        ROOT/'local/epl9-sd-loader-trigger-20261107',ROOT/'local/epl9-sd-slot-audit-20261107-final')
    stock.update(extra);listing_hashes.update(hashes)
    for name,start,end in (('startup',0x60400020,0x60400280),('early-chunks',0x60401561,0x6040168b),
                           ('pool-classifiers',0x604023b2,0x604024f0)):
        text=subprocess.check_output([str(reader),str(MAIN),hex(BASE),hex(start-BASE),hex(end-BASE)],text=True)
        stock.update(parse_listing(text,image,BASE));(a.out/(name+'.tsv')).write_text(text);listing_hashes[name]=sha(text.encode())
    # Physical-request allocation/free fronts remain the explicit file fixture.
    # Their newly decoded classifier bodies are used only by pool_audit.
    code={pc:r for pc,r in stock.items() if not 0x6040240f<=pc<0x604024f0}
    for i,p in enumerate(patches):
        at=p['address'];raw=bytes.fromhex(p['after']);path=a.out/f'hook-{i}.bin';path.write_bytes(raw)
        text=subprocess.check_output([str(reader),str(path),hex(at),'0',hex(len(raw))],text=True)
        for pc in list(code):
            if at<=pc<at+len(raw):del code[pc]
        code.update(parse_listing(text,raw,at))
    loaded,load=load_audit(image,candidate,(state,consumer),stock)
    try:load_audit(image,candidate,(state,consumer),stock,drop_last=True)
    except Fault as error:require('omitted' in str(error),'negative load failed unexpectedly')
    else:raise Fault('missing-read negative control was accepted')
    pools=pool_audit(stock,image)
    s0=synthetic_state(defaults);c0=synthetic_consumer(image,s0)
    for module,name in ((s0,'state'),(c0,'consumer')):
        module['code']=parse_listing((prior/name/'native.tsv').read_text(),module['data'],module['base'])
    evidence=Evidence(ROOT/'local/wifi-limits-20261102-v6')
    paths=('C:\\EPL9MOD\\SLOT01.RCP','C:\\EPL9MOD\\SLOT02.RCP')
    def fixture(files):return PlacedFixture(state,consumer,(s0,c0),files,loaded,code,evidence)
    cases=[]
    for name,files in (('embedded_fallback',{}),('exchanged_sd',dict(zip(paths,reversed(defaults))))):
        f=fixture(files);cases.append(dict(name=name,**retained(f,stock,reference)))
    negative=lifetime_negative_controls(fixture(dict(zip(paths,reversed(defaults)))))
    refs=[]
    for pc in range(len(image)-6):
        if image[pc]!=0xfc:continue
        value=struct.unpack_from('<I',image,pc+2)[0]&0x3fffffff
        if any((at&0x3fffffff)<=value<(at&0x3fffffff)+n for at,n in SPANS):refs.append(hex(BASE+pc))
    # Only the declared two data spans and six hook spans may differ.
    expected=bytearray(reference)
    for p in patches:
        at=p['address']-BASE;expected[at:at+len(bytes.fromhex(p['after']))]=bytes.fromhex(p['after'])
    require(candidate==expected and candidate[V3_SPAN[0]-BASE:V3_SPAN[1]-BASE]==image[V3_SPAN[0]-BASE:V3_SPAN[1]-BASE],
            'undeclared bytes or old v3 slot changed')
    for row in protected:require(sha((ROOT/row['path']).read_bytes())==row['sha256'],'protected input changed during run')
    (a.out/'main-SD-PLACED-OFFLINE-ONLY.decoded.bin').write_bytes(candidate)
    report=dict(model='Olympus E-PL9 / IM008 / 1330',displayed_version='1.1 (owner)',main_build=1101,
        main_bytes=len(image),main_sha256=MAIN_SHA,candidate_sha256=sha(candidate),reader_sha256=verify_reader(reader),
        modules=[dict(base=hex(m['base']),end=hex(m['base']+len(m['data'])),bytes=len(m['data']),code_bytes=m['code_bytes'],sha256=sha(m['data'])) for m in (state,consumer)],
        patches=patches,load=load,omitted_chunk_rejected=True,pools=pools,session_cases=cases,
        lifetime_negative_controls=negative,absolute_fc_reference_candidates=refs,computed_writers_excluded=False,
        frozen_v3_slot_untouched=True,only_declared_spans_changed=True,protected_inputs=protected,protected_inputs_unchanged=True,
        stock_listing_hashes=listing_hashes,source_sha256={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in
            (Path(__file__),ROOT/'scripts/epl9_sd_placement.py',ROOT/'scripts/test_epl9_sd_placement.py')},camera_accessed=False,firmware_package_created=False,
        install_ready=False,physical_execution_cache_dma_verified=False)
    (a.out/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(modules=2,configuration_cases=16,connected_jobs=12,pool_checks=pools['rejected_native_word_checks'],
                         normal_retention=True,full_teardown_qualified=False,protected=True)))


if __name__=='__main__':main()
