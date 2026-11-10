"""Execute the separate native SD loader with finite file/task/SD services.

No patch, hook, camera write or installation container is emitted. The ordinary
file-service RPC is modeled; optional stock wrappers/backend execute natively.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct
import subprocess

from epl9_workspace_bridge import ROOT, MAIN, MAIN_SHA, BASE
from epl9_tonal_drafts import READER_SHA
from epl9_sd_loader import build, MODULE_BASE
from epl9_sd_recipes import Recipe, pack_recipe, unpack_recipe, FILE_BYTES
from epl9_wifi_prototype import Model, Evidence, NativeReader, span
from mn103_calls import CallMachine
from mn103_subset import Memory, Region, Fault, parse_listing
from mn103_emit import memory as memory_operand

CTX, MANAGER, FALLBACK, STRINGS = 0x18000000,0x18001000,0x18002000,0x18003000
ROOT_POINTER=0x18004000
BUFFER, PHYSICAL, FD = 0x62267000,0xa1faffc0,0x1a000000
STACK, STOP = 0x19000000,0x12345678
SECTION_FLAGS, SD_STATUS = 0xa2aeaa3c,0x6239914c
GUARD = b'\xa5'*16


def require(condition,message):
    if not condition: raise Fault(message)


def sample_recipe():
    return Recipe(1001,'Synthetic default',((0,0,0),)*12,0,(0,0,0),(1024,1024),tuple(n*16 for n in range(256)))


def authored_code(module):
    """For synthetic tests; production probe uses independent GNU decoding."""
    code={}
    for pc,op,args,n in module['rows']:
        resolved=[hex(module['symbols'][a]) if a in module['symbols'] else a for a in args]
        code[pc]=(module['data'][pc-MODULE_BASE:pc-MODULE_BASE+n],op,resolved)
    return code


class RuntimeMemory(Memory):
    def read(self,address,size):
        # Declared runtime service IDs overlay only these two data reads. The
        # instruction listing remains checked against unchanged stock bytes.
        if (address,size)==(0x60420ba4,2): return 62
        if (address,size)==(0x60420faa,2): return 63
        return super().read(address,size)


class LoaderFixture:
    def __init__(self,module,file_data,*,image=None,stock_code=None,read_evidence=None,
                 fallback=None,task=54,manager_task=54,cpu=0,sections=511,sd_status=0xf000,
                 fail_alloc=False,close_error=False,stall_read=False,slot=1):
        self.module,self.file_data=module,file_data
        self.read_evidence=read_evidence
        self.task,self.fail_alloc,self.close_error,self.stall_read=task,fail_alloc,close_error,stall_read
        self.counts=Counter();self.owned=False;self.physical=False;self.file_open=False
        self.reader=None;self.reenter=False;self.reentrant_result=None
        self.delivered_event=0x02000100
        fallback=fallback or sample_recipe()
        self.fallback=pack_recipe(fallback)
        self.path=f'C:\\EPL9MOD\\SLOT{slot:02}.RCP'.encode()+b'\0'
        context=bytearray(32)
        struct.pack_into('<7I',context,0,0,FALLBACK,FALLBACK,0,STRINGS,STRINGS+64,0)
        manager=bytearray(180)
        struct.pack_into('<H',manager,172,manager_task & 0xffff)
        kernel=bytearray(1024)
        struct.pack_into('<I',kernel,28,0x1b000100)
        struct.pack_into('<I',kernel,96,0x1b000200)
        kernel[0x100]=1 if task is None else 0
        struct.pack_into('<I',kernel,0x200,0x1b000300)
        struct.pack_into('<H',kernel,0x310,(task or 0)&0xffff)
        self.regions=[Region(CTX-16,bytearray(GUARD+context+GUARD),True,'loader context guards'),
            Region(MANAGER-16,bytearray(GUARD+manager+GUARD),False,'declared HLS manager'),
            Region(FALLBACK,bytearray(self.fallback),False,'embedded fallback record'),
            Region(STRINGS,bytearray(self.path.ljust(64,b'\0')+b'r\0'),False,'firmware-owned path/mode'),
            Region(ROOT_POINTER,bytearray(struct.pack('<I',CTX)),True,'synthetic external context root'),
            Region(BUFFER-16,bytearray(GUARD+b'\xcd'*2048+GUARD),True,'finite retained recipe block'),
            Region(PHYSICAL-16,bytearray(GUARD+b'\xcd'*128+GUARD),True,'file wrapper request'),
            Region(0x8050,bytearray(struct.pack('<I',cpu)),False,'declared CPU identity'),
            Region(0x8ff00004,bytearray(struct.pack('<II',0x1b000000,0x1b000000)),False,'declared kernel roots'),
            Region(0x1b000000,kernel,False,'declared IRQ flags/current task/TCB'),
            Region(SECTION_FLAGS,bytearray(struct.pack('<I',sections)),True,'declared section flags'),
            Region(SD_STATUS,bytearray(struct.pack('<I',sd_status)),True,'declared SD mount status'),
            Region(SD_STATUS+12,bytearray(struct.pack('<I',0xf000)),False,'other medium mounted'),
            Region(0xa2b16cfe,bytearray(struct.pack('<H',62)),False,'registered file task'),
            Region(MODULE_BASE,bytearray(module['data']),False,'standalone loader code'),
            Region(STACK,bytearray(65536),True,'private caller stack')]
        if image is not None: self.regions.append(Region(BASE,bytearray(image),False,'exact stock main'))
        self.memory=RuntimeMemory(self.regions)
        self.code={**(stock_code or {}),**module['code']}
        self.models={0x60402373:Model('finite ordinary 2048-byte allocation',0,4,self.allocate),
            0x604023b2:Model('finite ordinary block release',0,4,self.release)}
        if 0x604117be not in self.code:
            self.models[0x604117be]=Model('declared get-task service',0x20,4,self.get_task)
        if stock_code:
            self.models.update({0x6040240f:Model('finite 128-byte wrapper request',0,4,self.phy_allocate),
                0x6040244e:Model('wrapper request release',0,4,self.phy_release),
                0x606b686a:Model('declared received application event',0xf0,84,self.event_receive),
                0x60434a21:Model('synchronous file-service reply fixture',0xf0,68,self.rpc)})
        else:
            self.models.update({0x609ce1c8:Model('synthetic public open',0,4,self.direct_open),
                0x609ce357:Model('synthetic public read',0xf0,24,self.direct_read),
                0x609ce1d1:Model('synthetic public close',0xb0,16,self.direct_close),
                0x60ae2073:Model('synthetic event-get adapter',0x20,8,self.direct_event_get)})

    def event_receive(self,m):
        self.counts['event_get']+=1
        m.r['d0']=self.delivered_event

    def direct_event_get(self,m):
        self.counts['event_get']+=1
        if m.r['a1']:
            m.memory.write(m.r['a1'],self.delivered_event,4);m.r['d0']=0
        else: m.r['d0']=0xf0000016

    def get_task(self,m):
        self.counts['get_task']+=1
        if self.task is None:
            m.r['d0']=(-25)&0xffffffff
        else:
            m.memory.write(m.r['a0'],self.task,2);m.r['d0']=0

    def allocate(self,m):
        require(m.r['d0']==2048 and not self.owned,'unexpected ordinary allocation')
        self.counts['alloc']+=1
        self.owned=not self.fail_alloc
        m.r['a0']=BUFFER if self.owned else 0

    def release(self,m):
        require(m.r['a0']==BUFFER and self.owned,'release of unowned block')
        self.owned=False;self.counts['free']+=1

    def phy_allocate(self,m):
        require(m.r['d0']==128 and not self.physical,'unexpected request allocation')
        self.physical=True;self.counts['request_alloc']+=1;m.r['a0']=PHYSICAL

    def phy_release(self,m):
        require(m.r['a0']==PHYSICAL and self.physical,'request double free')
        self.physical=False;self.counts['request_free']+=1

    def read_string(self,m,address):
        out=bytearray()
        for n in range(96):
            b=m.memory.read(address+n,1)
            if b==0: return bytes(out)
            out.append(b)
        raise Fault('unterminated file argument')

    def open(self,m,path,mode):
        require(self.read_string(m,path)==self.path[:-1] and self.read_string(m,mode)==b'r','unexpected file path/mode')
        require(not self.file_open,'repeated open without close')
        self.counts['open']+=1
        if self.file_data is None: return 0
        self.file_open=True
        if self.read_evidence: self.reader=NativeReader(self.read_evidence,self.file_data,'r')
        return FD

    def read(self,m,dest,fd,size,count):
        require(self.file_open and fd==FD and self.owned,'unowned file read')
        require((dest,size,count)==(BUFFER,1,661),'unbounded recipe read')
        self.counts['read']+=1
        if self.stall_read: raise Fault('declared pending file RPC: no completion supplied')
        data=self.reader.read(count) if self.reader else self.file_data[:count]
        span(m.memory,dest,len(data),True)[:]=data
        return len(data)

    def close(self,fd):
        require(fd==FD and self.file_open,'unknown/double close')
        self.counts['close']+=1
        if self.close_error: return 0xffffffff
        self.file_open=False;return 0

    def direct_open(self,m): m.r['a0']=self.open(m,m.r['a0'],m.r['a1'])
    def direct_read(self,m): m.r['d0']=self.read(m,m.r['a0'],m.r['a1'],m.r['d0'],m.r['d1'])
    def direct_close(self,m): m.r['d0']=self.close(m.r['a0'])

    def rpc(self,m):
        require(m.r['d0']==63,'wrong file service ID')
        at,op=m.r['a0'],m.r['d1']
        if self.reenter:
            self.reenter=False
            before=dict(self.counts)
            self.reentrant_result=self.run(secondary=True)
            require(self.reentrant_result['state']==1 and dict(self.counts)==before,'same-context reentry performed work')
        if op==0x10001:
            result=self.open(m,m.memory.read(at+4,4),m.memory.read(at+8,4))
            require(m.memory.read(at+12,2)==0,'unexpected open flags')
        elif op==0x10005:
            require(at==PHYSICAL and self.physical,'read without live request')
            result=self.read(m,m.memory.read(at+4,4),m.memory.read(at+16,4),m.memory.read(at+8,4),m.memory.read(at+12,4))
        elif op==0x10002:
            require(at==PHYSICAL and self.physical,'close without live request')
            result=self.close(m.memory.read(at+4,4))
        else: raise Fault(f'unexpected file request {op:#x}')
        m.memory.write(at,result,4);m.r['d0']=0
        return dict(operation=hex(op),result=hex(result),completion='explicit host file-service reply')

    def run(self,event=0x02000100,secondary=False):
        memory=self.memory
        stack=STACK
        if secondary:
            stack+=0x20000
            memory=RuntimeMemory([r for r in self.regions if r.address!=STACK]+
                                 [Region(stack,bytearray(65536),True,'reentrant caller stack')])
        machine=CallMachine(self.code,memory,dict(sp=stack+32768,a0=CTX,a1=MANAGER,d0=event,
            d2=0x22222222,d3=0x33333333,a2=0x44444444,a3=0x55555555),models=self.models)
        try:
            result=machine.run(machine.enter(self.module['symbols']['sd_try'],STOP,0xf0,64),[STOP],limit=300000)
            require(result.get('pc')==STOP and machine.r['sp']==stack+32768,'loader failed to return')
            require(tuple(machine.r[k] for k in ('d2','d3','a2','a3'))==
                    (0x22222222,0x33333333,0x44444444,0x55555555),'callee-saved state lost')
        except Fault as error:
            if not self.stall_read or str(error)!='declared pending file RPC: no completion supplied':
                raise
            result=dict(status='fault',error=str(error))
        for address,n in ((CTX,32),(MANAGER,180),(BUFFER,2048),(PHYSICAL,128)):
            require(bytes(span(memory,address-16,16))==GUARD and
                    bytes(span(memory,address+n,16))==GUARD,'guard overwritten')
        selected=memory.read(CTX+4,4)
        require(selected in (FALLBACK,BUFFER),'published invalid record pointer')
        record=bytes(span(memory,selected,FILE_BYTES))
        require(record==self.fallback or self.owned,'selected released recipe')
        return dict(result=result,state=memory.read(CTX,4),selected='sd' if selected==BUFFER else 'embedded',
            error_code=memory.read(CTX+24,4),owned_block=self.owned,open_file=self.file_open,
            live_request=self.physical,instructions=len(machine.trace),counts=dict(self.counts),
            native_task_id_calls=sum(e.get('target')==0x604117be and e['op']=='call' for e in machine.events),
            recipe_name=unpack_recipe(record).name)

    def event_adapter(self,event=0x02000100,original=False,null_output=False,unbound=False):
        self.delivered_event=event
        if unbound: self.memory.write(ROOT_POINTER,0,4)
        top=STACK+32768
        registers=dict(sp=top,a0=MANAGER,a1=0 if null_output else top+4,d0=0xffffffff,
                       d1=0x11111111,d2=0x22222222,d3=top+4,a2=0x44444444,a3=MANAGER)
        m=CallMachine(self.code,self.memory,registers,models=self.models)
        entry=0x60ae2073 if original else self.module['symbols']['sd_event_adapter']
        continuation=0x60ae1c73
        result=m.run(m.enter(entry,continuation,0x20,8),[continuation],limit=300000)
        require(result.get('pc')==continuation,'event adapter lost original continuation')
        observed={k:m.r[k] for k in ('d0','d1','d2','d3','a0','a1','a2','a3','sp')}
        return dict(registers=observed,event_word=self.memory.read(top+4,4) if not null_output else None,
                    caller_frame_sha256=hashlib.sha256(bytes(span(self.memory,top,32))).hexdigest(),
                    state=self.memory.read(CTX,4),counts=dict(self.counts),instructions=len(m.trace))


def decode_module(module,out,reader):
    binary=out/'sd-loader-SYNTHETIC-ONLY.bin'
    binary.write_bytes(module['data'])
    listing=subprocess.check_output([str(reader),str(binary),hex(MODULE_BASE),'0',hex(len(module['data']))],text=True)
    code=parse_listing(listing,module['data'],MODULE_BASE)
    require(set(code)=={r[0] for r in module['rows']},'GNU instruction boundaries differ')
    for pc,op,args,n in module['rows']:
        raw,actual,observed=code[pc]
        require(actual==op and len(raw)==n and len(args)==len(observed),'GNU mnemonic/length differs')
        for expected,got in zip(args,observed):
            if expected in module['symbols']: require(int(got,0)==module['symbols'][expected],'GNU label differs')
            elif expected.startswith('('): require(memory_operand(expected)==memory_operand(got),'GNU memory operand differs')
            elif expected.startswith('[') or expected in ('d0','d1','d2','d3','a0','a1','a2','a3','sp'):
                require(expected==got,'GNU register/save mask differs')
            else: require(int(expected,0)&0xffffffff==int(got,0)&0xffffffff,'GNU immediate differs')
    module['code']=code
    (out/'loader.tsv').write_text(listing)
    (out/'loader.s').write_text(module['source'])


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--discovery',type=Path,required=True)
    ap.add_argument('--file-listings',type=Path,required=True)
    ap.add_argument('--read-listings',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args()
    require(not a.out.exists() and a.out.resolve().is_relative_to((ROOT/'local').resolve()),'new ignored output required')
    image=MAIN.read_bytes();require(len(image)==26214336 and hashlib.sha256(image).hexdigest()==MAIN_SHA,'wrong stock main')
    reader=ROOT/'local/mn103-tooling/mn103-reader.exe'
    require(hashlib.sha256(reader.read_bytes()).hexdigest()==READER_SHA,'wrong GNU reader')
    before=json.loads((a.discovery/'protected-before.json').read_text())
    for row in before: require(hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest()==row['sha256'],'protected input changed before run')
    a.out.mkdir(parents=True)
    module=build();decode_module(module,a.out,reader)
    stock_code={};source_hashes={}
    for p in [*(a.file_listings/(n+'.tsv') for n in ('file_wrappers','file_open_route','file_classifier')),
              a.discovery/'registered_getter.tsv',a.discovery/'hls_get.tsv']:
        listing=p.read_text(encoding='utf-8');stock_code.update(parse_listing(listing,image,BASE))
        source_hashes[str(p.relative_to(ROOT)) if p.is_absolute() else str(p)]=hashlib.sha256(listing.encode()).hexdigest()
    task_listing=(a.discovery/'get_task_id.tsv').read_text()
    stock_code.update({pc:row for pc,row in parse_listing(task_listing,image,BASE).items() if pc<0x60411802})
    source_hashes['native_get_task_id']=hashlib.sha256(task_listing.encode()).hexdigest()
    evidence=Evidence(a.read_listings)
    discovery_code={}
    for name in ('hls_init','hls_manager','media_set','cached_sd_status'):
        text=(a.discovery/(name+'.tsv')).read_text()
        discovery_code.update(parse_listing(text,image,BASE))
        source_hashes[name]=hashlib.sha256(text.encode()).hexdigest()
    anchors={0x60ae1be4:('mov',['1622023186','a1']),
        0x60ae1bea:('call',['0x60431d88','[d2,d3,a2,a3]','52']),
        0x60ae1bf1:('movhu',['d0','(a2)']),
        0x60ae1c6e:('call',['0x60ae2073','[a2]','8']),
        0x60ae1c73:('cmp',['0','d0']),
        0x60ae1a4d:('mov',['(0x6239790c)','a0']),
        0x60aef936:('mov',['d0','(0x6239914c)']),
        0x60aef826:('mov',['(0x6239914c)','d2'])}
    for pc,expected in anchors.items():
        require(discovery_code[pc][1:]==expected,f'candidate trigger anchor changed at {pc:#x}')
    require(image[0x60dedf89-BASE:0x60dedf89-BASE+29].startswith(b'set SD MOUNT STATUS is '),'SD status label differs')
    raw=(ROOT/'local/epl9-sd-slot-prototype-20261107-final/recipe-1-EXPERIMENTAL.RCP').read_bytes()
    unpack_recipe(raw)
    cases=[]
    definitions=[('valid',raw,{}),('missing',None,{}),('short',raw[:-1],{}),('oversize',raw+b'x',{}),
        ('bad_crc',raw[:-1]+bytes([raw[-1]^1]),{}),('alloc_failure',raw,dict(fail_alloc=True)),
        ('not_mounted',raw,dict(sd_status=0)),('mount_in_progress',raw,dict(sd_status=0x3000)),
        ('sections_incomplete',raw,dict(sections=0)),('other_cpu',raw,dict(cpu=1)),
        ('no_task',raw,dict(task=None)),('wrong_task',raw,dict(task=55)),
        ('unbound_manager',raw,dict(manager_task=0xffff)),('close_uncertain',raw,dict(close_error=True)),
        ('pending_read',raw,dict(stall_read=True))]
    for name,data,options in definitions:
        f=LoaderFixture(module,data,image=image,stock_code=stock_code,read_evidence=evidence,**options)
        result=f.run();cases.append(dict(name=name,**result))
        if name=='valid':
            require(result['state']==3 and result['selected']=='sd' and not f.file_open and not f.physical,'valid load failed')
            count=dict(f.counts);require(f.run()['state']==3 and dict(f.counts)==count,'repeat load was not suppressed')
        elif name=='close_uncertain': require(result['state']==4 and f.owned and result['selected']=='embedded','close uncertainty released or published data')
        elif name=='pending_read': require(result['result']['status']=='fault' and result['state']==1 and f.owned and f.file_open and f.physical,'pending resources lost')
        elif name in ('not_mounted','mount_in_progress','sections_incomplete','other_cpu','no_task','wrong_task','unbound_manager'):
            require(result['state']==0 and not f.counts['open'] and not f.counts['alloc'],'gate did work before readiness')
        else:
            require(result['state']==2 and result['selected']=='embedded' and not f.owned and not f.file_open and not f.physical,'fallback cleanup failed')
    for event in (0,0x02000101,0x02040100,0x04030120):
        f=LoaderFixture(module,raw,image=image,stock_code=stock_code,read_evidence=evidence)
        result=f.run(event);require(result['state']==0 and not f.counts['open'],'wrong event loaded a file')
        cases.append(dict(name=f'event_{event:08x}',**result))
    f=LoaderFixture(module,raw,image=image,stock_code=stock_code,read_evidence=evidence,sd_status=0)
    require(f.run()['state']==0,'early attempt was consumed')
    f.memory.write(SD_STATUS,0xf000,4)
    require(f.run()['state']==3,'not-ready state did not retry')
    f=LoaderFixture(module,raw,image=image,stock_code=stock_code,read_evidence=evidence)
    f.reenter=True
    require(f.run()['state']==3 and f.reentrant_result['state']==1,'reentrant exclusion failed')
    adapter_cases=[]
    for name,event,options in (('load',0x02000100,{}),('release',0x02000101,{}),
                              ('early',0x02000100,dict(sd_status=0)),
                              ('null_output',0x02000100,dict(null_output=True)),
                              ('unbound_root',0x02000100,dict(unbound=True))):
        constructor={k:v for k,v in options.items() if k=='sd_status'}
        invocation={k:v for k,v in options.items() if k!='sd_status'}
        def instance():
            return LoaderFixture(module,raw,image=image,stock_code=stock_code,read_evidence=evidence,**constructor)
        control=instance().event_adapter(event,original=True,**invocation)
        adapted=instance().event_adapter(event,**invocation)
        require(control['registers']==adapted['registers'] and control['event_word']==adapted['event_word'] and
                control['caller_frame_sha256']==adapted['caller_frame_sha256'],
                'event adapter changed original event-get outputs')
        require(adapted['state']==(3 if name=='load' else 0),'event adapter loaded at wrong time')
        adapter_cases.append(dict(name=name,stock=control,prototype=adapted,outputs_equal=True))
    for row in before: require(hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest()==row['sha256'],'protected input changed')
    report=dict(model='Olympus E-PL9',displayed_version='1.1 (owner report)',main_build=1101,
        main_bytes=len(image),main_sha256=MAIN_SHA,reader_sha256=READER_SHA,
        module=dict(bytes=len(module['data']),sha256=hashlib.sha256(module['data']).hexdigest(),
            base=hex(MODULE_BASE),instructions=len(module['code']),native_crc_and_range_validation=True),
        candidate_hook=dict(site='0x60ae1c6e',stock_bytes='cd05042008',continuation='0x60ae1c73',
            event_get='0x60ae2073',task_entry='0x60ae1c12',task_field='manager+172',
            sd_status='0x6239914c',required_status='0xf000',hook_applied=False,
            runtime_pointer_binding_and_event_encoding_unverified=True),
        cases=cases,event_adapter_cases=adapter_cases,checked_trigger_anchors=len(anchors),
        readiness_retry_passed=True,same_context_reentry_rejected=True,
        source_listing_hashes=source_hashes,read_backend_listing_hashes=evidence.hashes,
        source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (
            ROOT/'scripts/epl9_sd_loader.py',ROOT/'firmware_src/epl9_sd_loader.s.in',
            ROOT/'scripts/epl9_sd_recipes.py',ROOT/'scripts/test_epl9_sd_loader.py')},
        instruction_encoding_reference=dict(upstream='https://sourceware.org/git/binutils-gdb.git',
            commit='2bc7af1ff7732451b6a7b09462a815c3284f9613',file='opcodes/m10300-opc.c',
            sha256='1e1150db856998de8366870394297e37d51db464164190e6ed0f988b44910796'),
        protected_inputs=before,protected_inputs_unchanged=True,
        code_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        native_task_id_function_executed=True,
        boundaries=['native task-ID code executes on declared kernel roots/IRQ flags/current-task records; runtime IDs/section/status fields and allocator are fixtures',
            'native public file wrappers execute; file-service RPC completion/open metadata and SD storage are host models',
            'prototype publishes a validated packed record; generalized film-descriptor consumer is not installed',
            'event adapter executes a native get wrapper with a declared delivered event; the full blocking event service is not executed',
            'native hook placement/state-root lifetime and physical card readiness/timing remain unqualified'],
        camera_accessed=False,firmware_modified=False,firmware_container_created=False)
    (a.out/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(native_cases=len(cases),module_bytes=len(module['data']),
        protected_inputs_unchanged=True,camera_accessed=False)))


if __name__=='__main__': main()
