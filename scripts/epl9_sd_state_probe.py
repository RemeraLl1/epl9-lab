"""Offline singleton-tail / two-slot execution against byte-checked E-PL9 code.

Only RAM copies are overlaid. Kernel, pools, owner lookup and RPC completions
are finite declared fixtures, not camera measurements.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct

from epl9_workspace_bridge import ROOT, MAIN, MAIN_SHA, BASE
from epl9_sd_state import build, overlay, ROOT_ADDRESS, OBJECT_BYTES, MAGIC, CONTEXTS
from epl9_sd_loader import MODULE_BASE
from epl9_sd_loader_probe import (LoaderFixture, RuntimeMemory, decode_module,
    authored_code, require, GUARD, PHYSICAL, SECTION_FLAGS, SD_STATUS, STACK, STOP)
from epl9_sd_state_audit import PRIVATE
from epl9_tonal_drafts import READER_SHA
from epl9_wifi_prototype import Model, Evidence, NativeReader, span
from mn103_calls import CallMachine
from mn103_subset import Region, Fault, parse_listing

MANAGER=0x62267000


class ObservedRegisters(dict):
    """Observe the size before native allocation replaces D0 with pool ID."""
    def __init__(self, values, fixture):
        super().__init__(values);self.fixture=fixture

    def __setitem__(self, key, value):
        if key=='d0' and value in (0x10001,0x10002,0x10004):
            self.fixture.requested=self.get('d0')
        super().__setitem__(key,value)


class PublicationMemory(RuntimeMemory):
    def __init__(self,regions,fixture):
        super().__init__(regions);self.fixture=fixture

    def write(self,address,value,size):
        if address==ROOT_ADDRESS and value:
            f=self.fixture
            require(f.locked,'singleton published outside native lock')
            if f.extended:
                require(self.read(value+192,4)==MAGIC and self.read(value+200,4)==value and
                        self.read(value+204,4)==OBJECT_BYTES,'tail was not initialized before publication')
                for i,offset in enumerate(CONTEXTS):
                    record=f.module['constants'][f'FALLBACK{i}']
                    require(self.read(value+offset,4)==0 and self.read(value+offset+4,4)==record and
                            self.read(value+offset+8,4)==record,'slot missing at publication')
            f.counts['publish']+=1
        super().write(address,value,size)


class StateFixture(LoaderFixture):
    def __init__(self,module,files,*,image=None,code=None,evidence=None,extended=True,
                 sd_status=0xf000,stall=False,close_error=None,fail_manager=False):
        self.module,self.files,self.extended=module,files,extended
        self.read_evidence=evidence;self.stall_read=stall;self.close_error=close_error
        self.fail_manager=fail_manager;self.counts=Counter();self.requested=None
        self.allocated={};self.handles={};self.physical=False;self.locked=False
        self.reenter=False;self.reentrant_result=None;self.delivered_event=0x02000100
        self.pools={0x10001:[0x61f01fc0+i*192 for i in range(4)],
                    0x10002:[MANAGER+i*0x840 for i in range(10)],0x10004:[0x61fb8540]}
        self.original_pools={k:list(v) for k,v in self.pools.items()}
        kernel=bytearray(1024)
        struct.pack_into('<I',kernel,28,0x1b000100)
        struct.pack_into('<I',kernel,96,0x1b000200)
        struct.pack_into('<I',kernel,0x200,0x1b000300)
        struct.pack_into('<H',kernel,0x310,54)
        regions=[Region(ROOT_ADDRESS,bytearray(4),True,'actual singleton root'),
            Region(PHYSICAL-16,bytearray(GUARD+b'\xcd'*128+GUARD),True,'bounded RPC request'),
            Region(0x8050,bytearray(4),False,'CPU fixture'),
            Region(0x8ff00004,bytearray(struct.pack('<II',0x1b000000,0x1b000000)),False,'kernel roots fixture'),
            Region(0x1b000000,kernel,False,'kernel current task fixture'),
            Region(SECTION_FLAGS,bytearray(struct.pack('<I',511)),True,'section fixture'),
            Region(SD_STATUS,bytearray(struct.pack('<I',sd_status)),True,'SD state fixture'),
            Region(0xa2b16cfe,bytearray(struct.pack('<H',62)),False,'file task fixture'),
            Region(MODULE_BASE,bytearray(module['data']),False,'separate module'),
            Region(STACK,bytearray(0x40000),True,'two independent private caller stacks')]
        for pool,addresses in self.pools.items():
            for at in addresses:
                size={0x10001:128,0x10002:2048,0x10004:16384}[pool]
                if at==MANAGER:size=OBJECT_BYTES if extended else 180
                regions.append(Region(at-16,bytearray(GUARD+b'\xcd'*size+GUARD),True,f'finite pool {at:x}'))
        if image is not None:regions.append(Region(BASE,bytearray(image),False,'stock or RAM overlay'))
        self.regions=regions;self.memory=PublicationMemory(regions,self)
        self.code={**(code or {}),**module['code']}
        self.models={0x60402595:Model('finite pool allocation',0xe0,16,self.pool_allocate),
            0x604025d7:Model('finite pool release',0xe0,20,self.pool_release),
            0x60dbb693:Model('borrowed default owner lookup',0,0,self.owner),
            0x60ada00d:Model('select singleton lock 2',0xa0,12,self.lock_select),
            0x60ad9ff0:Model('enter singleton lock',0,4,self.lock_enter),
            0x60ada000:Model('leave singleton lock',0,4,self.lock_leave),
            0x60431d88:Model('kernel task creation',0xf0,52,self.task_create),
            0x60410727:Model('kernel task start',0xe0,16,self.task_start),
            0x604335fd:Model('task creation log',0x80,8,lambda m:None),
            0x6040240f:Model('finite wrapper request',0,4,self.phy_allocate),
            0x6040244e:Model('wrapper request release',0,4,self.phy_release),
            0x606b686a:Model('declared received event',0xf0,84,self.event_receive),
            0x60434a21:Model('declared file-service reply',0xf0,68,self.rpc)}

    def owner(self,m):self.counts['owner_lookup']+=1;m.r['a0']=0x1c000000
    def lock_select(self,m):require(m.r['d0']==2,'wrong lock ID')
    def lock_enter(self,m):require(not self.locked,'recursive singleton lock');self.locked=True
    def lock_leave(self,m):require(self.locked,'unheld singleton lock');self.locked=False

    def pool_allocate(self,m):
        pool,size=m.r['d0'],self.requested
        expected=0x10001 if size<=128 else 0x10002 if size<=2048 else 0x10004
        require(pool==expected and size<=16384,'native size classification differs')
        self.counts[f'alloc_{size}']+=1
        if self.fail_manager and size in (180,OBJECT_BYTES):m.r['a0']=0;return
        require(bool(self.pools[pool]),'finite pool exhausted')
        at=self.pools[pool].pop(0)
        self.allocated[at]=(pool,size);m.r['a0']=at

    def pool_release(self,m):
        at=m.r['a0'];require(at in self.allocated,'free of unowned block')
        pool,size=self.allocated.pop(at)
        require(pool==m.r['d0'],'native free classification differs')
        self.pools[pool].insert(0,at);self.counts[f'free_{size}']+=1

    def task_create(self,m):
        sp=m.r['sp']+52
        require(m.r['a1']==0x60ae1c12 and self.memory.read(sp+4,4)==54 and
                self.memory.read(sp+8,4)==16360,'task creation contract differs')
        at=self.memory.read(sp+12,4)
        require(self.allocated.get(at)==(0x10004,16360),'task stack not owned')
        self.counts['task_create']+=1;m.r['d0']=54

    def task_start(self,m):require(m.r['d0']==54,'wrong task started');self.counts['task_start']+=1

    def open(self,m,path,mode):
        path=self.read_string(m,path).decode('ascii')
        require(path in ('C:\\EPL9MOD\\SLOT01.RCP','C:\\EPL9MOD\\SLOT02.RCP') and
                self.read_string(m,mode)==b'r','unexpected slot path/mode')
        self.counts['open']+=1
        data=self.files.get(path)
        if data is None:return 0
        fd=0x1a000000+len(self.handles)*16
        while fd in self.handles:fd+=16
        self.handles[fd]=(path,data,NativeReader(self.read_evidence,data,'r') if self.read_evidence else None)
        return fd

    def read(self,m,dest,fd,size,count):
        require(fd in self.handles and self.allocated.get(dest)==(0x10002,2048) and
                (size,count)==(1,661),'unowned/unbounded recipe read')
        self.counts['read']+=1
        if self.stall_read:raise Fault('declared pending file RPC: no completion supplied')
        _,data,reader=self.handles[fd]
        data=reader.read(count) if reader else data[:count]
        span(self.memory,dest,len(data),True)[:]=data
        return len(data)

    def close(self,fd):
        require(fd in self.handles,'unknown/double close');self.counts['close']+=1
        if self.handles[fd][0]==self.close_error:return 0xffffffff
        del self.handles[fd];return 0

    def rpc(self,m):
        if self.reenter:
            self.reenter=False;before=self.counts['open']
            self.reentrant_result=self.event(secondary=True)
            require(self.counts['open']==before,'recursive event opened another file')
        # Reuse the checked request ABI; disable its single-context callback.
        return super().rpc(m)

    def machine(self,registers):
        m=CallMachine(self.code,self.memory,registers,models=self.models)
        m.r=ObservedRegisters(m.r,self);return m

    def invoke(self,entry,mask,frame,**registers):
        top=STACK+0x28000
        m=self.machine(dict(sp=top,d2=0x22222222,d3=0x33333333,a2=0x44444444,a3=0x55555555,**registers))
        result=m.run(m.enter(entry,STOP,mask,frame),[STOP],limit=500000)
        require(result.get('pc')==STOP and m.r['sp']==top,'native invocation did not return')
        require([m.r[r] for r in ('d2','d3','a2','a3')]==[0x22222222,0x33333333,0x44444444,0x55555555],
                'callee saved registers changed')
        return m

    def getter(self):return self.invoke(0x60ae1a4d,0x20,8).r['a0']
    def start_task(self):return self.invoke(0x60ae1bb2,0x20,20,a0=MANAGER)
    def selected(self,slot):return self.invoke(self.module['symbols']['sd_slot_get'],0xf0,24,d0=slot).r['a0']

    def event(self,secondary=False):
        top=STACK+(0x18000 if secondary else 0x8000)
        span(self.memory,top,32,True)[:]=bytes(range(32))
        m=self.machine(dict(sp=top,a0=MANAGER,a1=top+4,d0=0xffffffff,d1=0x11111111,
                            d2=0x22222222,d3=top+4,a2=0x44444444,a3=MANAGER))
        pending=False
        try:
            result=m.run(0x60ae1c6e,[0x60ae1c73],limit=500000)
            require(result.get('pc')==0x60ae1c73,'inline event hook lost continuation')
        except Fault as e:
            if not self.stall_read or str(e)!='declared pending file RPC: no completion supplied':raise
            pending=True
        return dict(pending=pending,registers={r:m.r[r] for r in ('d0','d1','d2','d3','a0','a1','a2','a3','sp')},
                    live_caller_frame=bytes(span(self.memory,top+4,28)).hex(),instructions=len(m.trace))

    def states(self):return [self.memory.read(MANAGER+c,4) for c in CONTEXTS]
    def guards(self):
        for r in self.regions:
            if r.name.startswith('finite pool') or r.address==PHYSICAL-16:
                require(r.data[:16]==GUARD and r.data[-16:]==GUARD,'allocation guard changed')


def stock_listings(image,discovery,trigger,files):
    code={};hashes={}
    names=('manager_ctor','manager_getter','debug_alloc','base_ctor','base_subobjects',
           'small_base','parent_get_set','parent_leaf','owner_factory','base_methods',
           'manager_vectors','task_create_manager','ordinary_allocate')
    paths=[*(discovery/(n+'.tsv') for n in names),
           *(trigger/(n+'.tsv') for n in ('get_task_id','hls_get','registered_getter','hls_init')),
           *(files/(n+'.tsv') for n in ('file_wrappers','file_open_route','file_classifier'))]
    for p in paths:
        text=p.read_text();rows=parse_listing(text,image,BASE)
        # Only load complete owner/base functions, never the modeled lookup.
        if p.stem=='owner_factory':rows={pc:r for pc,r in rows.items() if pc<0x60db86c0}
        if p.stem=='get_task_id':rows={pc:r for pc,r in rows.items() if pc<0x60411802}
        code.update(rows);hashes[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
    return code,hashes


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--read-listings',type=Path,required=True)
    ap.add_argument('--discovery',type=Path,default=ROOT/'local/epl9-sd-state-discovery-20261107')
    a=ap.parse_args()
    require(not a.out.exists() and a.out.resolve().is_relative_to((ROOT/'local').resolve()),'new ignored output required')
    image=MAIN.read_bytes();require(hashlib.sha256(image).hexdigest()==MAIN_SHA,'wrong E-PL9 main')
    discovery=a.discovery.resolve()
    protected=json.loads((discovery/'protected-before.json').read_text())
    for name,(size,expected) in PRIVATE.items():
        raw=(ROOT/name).read_bytes()
        require(len(raw)==size and hashlib.sha256(raw).hexdigest()==expected,'private-COLOR generation changed')
        if not any(Path(row['path'])==Path(name) for row in protected):
            protected.append(dict(path=name,bytes=size,sha256=expected))
    for row in protected:require(hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest()==row['sha256'],'protected input changed')
    defaults=[(ROOT/f'local/epl9-sd-slot-prototype-20261107-final/recipe-{i}-EXPERIMENTAL.RCP').read_bytes() for i in (1,2)]
    module=build(defaults);a.out.mkdir(parents=True)
    reader=ROOT/'local/mn103-tooling/mn103-reader.exe'
    require(hashlib.sha256(reader.read_bytes()).hexdigest()==READER_SHA,'wrong GNU reader')
    executable=dict(module,data=module['data'][:module['code_bytes']])
    decode_module(executable,a.out,reader);module['code']=executable['code']
    (a.out/'state-module-SYNTHETIC-ONLY.bin').write_bytes(module['data'])
    stock,hashes=stock_listings(image,discovery,ROOT/'local/epl9-sd-loader-trigger-20261107',ROOT/'local/epl9-sd-slot-audit-20261107-final')
    overlaid,patches=overlay(image,module)
    # Decode only the three modified instructions, checked independently by GNU.
    temp=a.out/'RAM-overlay-NOT-A-PACKAGE.bin';temp.write_bytes(overlaid)
    import subprocess
    changed={}
    for patch in patches:
        at=patch['address'];length=len(bytes.fromhex(patch['after']))
        text=subprocess.check_output([str(reader),str(temp),hex(BASE),hex(at-BASE),hex(at-BASE+length)],text=True)
        changed.update(parse_listing(text,overlaid,BASE))
    temp.unlink()  # no persistent firmware image is a deliverable
    adapted={**stock,**changed};evidence=Evidence(a.read_listings)
    def fixture(files=None,original=False,**kw):
        return StateFixture(module,files or {},image=image if original else overlaid,
                            code=stock if original else adapted,evidence=evidence,extended=not original,**kw)
    control=fixture(original=True);candidate=fixture()
    require(control.getter()==MANAGER and candidate.getter()==MANAGER,'singleton allocation failed')
    require(bytes(span(control.memory,MANAGER,180))==bytes(span(candidate.memory,MANAGER,180)),
            'stock constructor prefix changed')
    require(control.allocated[MANAGER]==(0x10002,180) and candidate.allocated[MANAGER]==(0x10002,288),'pool classification differs')
    tail=bytes(span(candidate.memory,MANAGER+180,108))
    candidate.start_task();control.start_task()
    require(bytes(span(candidate.memory,MANAGER+180,108))==tail,'native task creation changed tail')
    control_event=control.event();candidate_event=candidate.event()
    require(control_event['registers']==candidate_event['registers'] and
            control_event['live_caller_frame']==candidate_event['live_caller_frame'],'event-get caller contract changed')
    cases=[]
    p1,p2='C:\\EPL9MOD\\SLOT01.RCP','C:\\EPL9MOD\\SLOT02.RCP'
    definitions=[('both_missing',{},[2,2],{}),('both_valid',{p1:defaults[1],p2:defaults[0]},[3,3],{}),
        ('first_missing',{p2:defaults[0]},[2,3],{}),('second_missing',{p1:defaults[1]},[3,2],{}),
        ('first_corrupt',{p1:defaults[0][:-1]+b'\xff',p2:defaults[0]},[2,3],{}),
        ('not_ready',{p1:defaults[1],p2:defaults[0]},[0,0],dict(sd_status=0)),
        ('close_uncertain',{p1:defaults[1],p2:defaults[0]},[4,3],dict(close_error=p1)),
        ('pending',{p1:defaults[1],p2:defaults[0]},[1,0],dict(stall=True))]
    for name,files,expected,options in definitions:
        f=fixture(files,**options)
        require(f.selected(1)==module['constants']['FALLBACK0'] and f.selected(2)==module['constants']['FALLBACK1'],
                'pre-construction fallback failed')
        f.getter()
        f.event();require(f.states()==[0,0] and not f.counts['open'],'loader ran before manager task existed')
        f.start_task();result=f.event();require(f.states()==expected,f'{name}: wrong states')
        if not result['pending']:
            require(result['registers']==control_event['registers'] and
                    result['live_caller_frame']==control_event['live_caller_frame'],f'{name}: event outputs changed')
        for i,state in enumerate(expected):
            ptr=f.selected(i+1)
            want=files[(p1,p2)[i]] if state==3 else defaults[i]
            require(bytes(span(f.memory,ptr,660))==want,f'{name}: wrong selected record')
        count=f.counts['open'];f.getter();f.event()
        require(f.counts['open']==count,'completed/pending attempt repeated')
        if name=='not_ready':
            f.memory.write(SD_STATUS,0xf000,4);f.event();require(f.states()==[3,3],'readiness retry consumed')
        if name=='pending':require(f.physical and f.handles and f.memory.read(MANAGER+208,4)==1,'pending ownership lost')
        else:require(not f.physical and f.memory.read(MANAGER+208,4)==0,'normal completion retained busy flag')
        if name=='both_missing':
            f.files.update({p1:defaults[1],p2:defaults[0]});f.event()
            require(f.states()==[2,2] and f.counts['open']==count,'completed missing file unexpectedly reloaded')
        f.guards();cases.append(dict(name=name,initial_states=expected,final_states=f.states(),
                                    counts=dict(f.counts),pending=result['pending']))
    f=fixture({p1:defaults[1],p2:defaults[0]});f.getter();f.start_task();f.reenter=True;f.event()
    require(f.states()==[3,3] and f.reentrant_result is not None,'recursive event check failed')
    require(f.selected(0)==0 and f.selected(3)==0,'unknown slot accepted')
    f.memory.write(MANAGER+192,0,4)
    require(f.selected(1)==module['constants']['FALLBACK0'],'invalid registry accepted')
    failed=fixture(fail_manager=True)
    require(failed.getter()==0 and failed.memory.read(ROOT_ADDRESS,4)==0 and
            failed.selected(1)==module['constants']['FALLBACK0'],'allocation failure lost fallback')
    for row in protected:require(hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest()==row['sha256'],'protected input changed during run')
    report=dict(model='Olympus E-PL9 / IM008',displayed_version='1.1 (owner)',main_build=1101,
        main_bytes=len(image),main_sha256=MAIN_SHA,module_bytes=len(module['data']),code_bytes=module['code_bytes'],
        module_sha256=hashlib.sha256(module['data']).hexdigest(),module_base=hex(MODULE_BASE),synthetic_base=True,
        reader_sha256=READER_SHA,instructions=len(module['code']),patches=patches,patches_applied_only_to_ram_copy=True,
        object_bytes=dict(stock=180,prototype=288),original_prefix_equal=True,root_published_after_tail_init=True,
        task_creation_preserves_tail=True,event_caller_outputs_equal=True,dead_return_word_excluded=True,
        cases=cases,reentrant_event_excluded=True,allocation_failure_fallback=True,
        source_listing_hashes=hashes,read_backend_listing_hashes=evidence.hashes,
        source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
            (Path(__file__),ROOT/'scripts/epl9_sd_state.py',ROOT/'firmware_src/epl9_sd_state.s.in',
             ROOT/'scripts/epl9_sd_state_audit.py',ROOT/'scripts/test_epl9_sd_state.py')},
        protected_inputs=protected,protected_inputs_unchanged=True,camera_accessed=False,
        firmware_container_created=False,installation_ready=False,
        boundaries=['pool backing, default-owner lookup, singleton locking and kernel task creation are finite models',
            'native constructor, vectors, ordinary size/free classifiers, task-create adapter, get_tid, file wrappers and read backend execute',
            'module load before first getter and actual object/RTOS/cache lifetime remain unqualified',
            'T1/T2 are test aliases; no ART/menu mapping or packed-record processing consumer is installed',
            'cold-start allocation extension only; not a live extension of an existing 180-byte singleton'])
    (a.out/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(cases=len(cases),code_bytes=module['code_bytes'],prefix_equal=True,protected=True)))


if __name__=='__main__':main()
