"""Connect native E-PL9 job construction and execution with explicit host inputs."""
import argparse
import hashlib
import json
import struct
import subprocess
from pathlib import Path

from epl9_integrated_probe import EXTRA_WINDOWS, WINDOWS, SERVICE_WINDOWS, EXPECTED, RETURN
from epl9_art_routing_probe import ROOT, BASE, MAIN_SHA, STOCK_SHA
from epl9_offline_prototype import header, RECIPES
from mn103_subset import Memory, Region, Fault, parse_listing
from mn103_calls import CallMachine
from mn103_models import FillModel

JOB, CACHE = 0x11000000, 0x11010000
PARAMS, ERROR, STACK, SP = 0x10020000, 0x10030000, 0x10010000, 0x10013c00
OWNER_CALLBACK, OWNER_CONTEXT, SOURCE, OUTPUT = 0x0f000000, 0x10040000, 0x12000000, 0x16000000
SCRATCH = 0x18000000
JOB_WINDOWS = {
    'cache_constructor': (0x6073e562, 0x6073e6ac),
    'cache_descriptor_init': (0x60749fa5, 0x60749fb6),
    'job_services': (0x6074eca0, 0x6074ed70),
    'job_builder_wrappers': (0x607507b9, 0x60750808),
    'job_effect_objects': (0x60752b86, 0x60752f56),
    'dimension_tables': (0x60749187, 0x607491e9),
    'request_parameter_views': (0x60750498, 0x607504f6),
    'buffer_allocation': (0x6074a824, 0x6074aaa5),
    'job_start': (0x6074e348, 0x6074e6eb),
    'buffer_release_and_reset': (0x6074abc7, 0x6074acf9),
    'job_pending_reset': (0x6074ed70, 0x6074edac),
    'buffer_available_slot': (0x6074ae89, 0x6074aea9),
    'start_callback_bodies': (0x607503e6, 0x60750478),
    'processing_classifier': (0x60792399, 0x60792510),
    'processing_classifier_support': (0x607925d2, 0x60792764),
    'early_processing_classifier': (0x6078e83f, 0x6078e890),
    'crop_ratios_and_coordinates': (0x607a3df6, 0x607a44bc),
    'first_pass_complete': (0x60761b6a, 0x60762cf1),
    'early_initializer_complete': (0x60761333, 0x607617dd),
    'input_descriptor_fetch': (0x6074ae57, 0x6074ae89),
    'input_descriptor_wrappers': (0x6074f9a9, 0x6074fb0c),
    'active_dimensions': (0x6074fd86, 0x6074fdf6),
    'descriptor_services': (0x6074fb0c, 0x6074fd86),
    'request_buffer_ids': (0x60762d61, 0x60762d9a),
    'request_dispatch': (0x6074fdf6, 0x607503e6),
    'request_pending_lookup': (0x6074edac, 0x6074edd9),
    'request_dispatch_table': (0x6072fb1b, 0x6072fb2d),
    'request_processor': (0x6072fd27, 0x6072fdd6),
    'consumer_constructor': (0x6073effd, 0x6073f33d),
    'cache_compare': (0x6073e6ac, 0x6073e953),
    'cache_update': (0x6073e953, 0x6073eab3),
    'pending_callback': (0x607504f6, 0x60750638),
    'descriptor_comparisons': (0x60749fb6, 0x6074a061),
    'consumer_outputs': (0x6073f60c, 0x6073f678),
    'request_type_helpers': (0x607a3bed, 0x607a3df6),
    'processing_dispatch': (0x60734068, 0x60734302),
    'processing_configuration_start': (0x6073af53, 0x6073b603),
    'processing_configuration_helpers': (0x60734519, 0x6073595c),
    'input_format_dispatch': (0x60799f48, 0x60799fac),
    'input_format_configuration': (0x607a01b1, 0x607a038d),
    'input_format_parameters': (0x60799fdc, 0x6079a304),
    'input_format_table': (0x60749150, 0x60749187),
    'optional_raw_parameters_prefix': (0x6078ac47, 0x6078ace6),
}
JOB_ANCHORS = {
    0x6073e5b3: 'movhu\td0,(5694,a2)',
    0x6073e8f3: 'mov\t(4,a0),a0',
    0x6073e915: 'mov\t(20,a0),d0',
    0x6073ea95: 'mov\t(12,a0),a0',
    0x6074f1dd: 'call\t0x6073eab3,[a2,a3],12',
    0x60750360: 'call\t0x6072fb1b,[],4',
    0x60763917: 'mov\t4228,a0',
    0x6073f107: 'call\t0x6073e6ac,[d2,d3,a2,a3],20',
    0x6073f22f: 'movhu\t(8,a0),d0',
    0x6073b218: 'udf01\td2,d1',
}


class FixtureOwner:
    """Declared host descriptors and bounded buffers, never an ISP model."""
    name = 'synthetic-frame-owner'

    def __init__(self, continue_processing=True, accept_request=True):
        self.buffers = []
        self.continue_processing = continue_processing
        self.accept_request = accept_request

    def validate(self,m,mask,frame):
        if (mask,frame,m.r['a1']) != (0,0,OWNER_CONTEXT):
            raise Fault('fixture owner callback ABI/context mismatch')
        event, arg = m.r['d0'],m.r['a0']
        if event == 14:
            descriptor_id = m.memory.read(arg+4,2)
            if m.memory.read(arg,4) != JOB+36 or descriptor_id not in (1,2,0xff12):
                raise Fault(f'owner descriptor {descriptor_id:#x} not declared by fixture')
            offset = {1:36,2:100,0xff12:4264}[descriptor_id]
            pointer = m.memory.read(JOB+offset,4)
            if pointer != (SOURCE if descriptor_id == 1 else OUTPUT):
                raise Fault('fixture descriptor points outside its assigned payload')
            stride,width,height = [m.memory.read(JOB+offset+n,2) for n in (10,12,14)]
            size = stride*height*2  # Declared two-byte fixture layout only.
            if not (0 < width <= stride <= 4608 and 0 < height <= 3456):
                raise Fault('missing or invalid fixture descriptor dimensions')
            if not any(r.address <= pointer and pointer+size <= r.address+len(r.data)
                       and (descriptor_id == 1 or r.writable) for r in m.memory.regions):
                raise Fault('fixture descriptor exceeds its declared payload')
        elif event == 19:
            if not JOB+5668 <= arg < JOB+9892 or (arg-JOB-5668)%88:
                raise Fault('owner allocation outside native buffer table')
            size = m.memory.read(arg+72,4)
            if not 0 < size <= 32*1024*1024 or len(self.buffers) >= 2:
                raise Fault('owner buffer request exceeds declared fixture capacity')
            m.memory.region(arg+64,4,True)
            address = 0x20000000+len(self.buffers)*0x03000000
            if any(address < r.address+len(r.data) and r.address < address+size+16 for r in m.memory.regions):
                raise Fault('fixture buffer address overlaps existing memory')
        elif event == 12:
            if arg != JOB+10398:
                raise Fault('unexpected crop notification pointer')
        elif event == 13:
            if arg != 0:
                raise Fault('unexpected cancellation query argument')
        elif event == 21:
            if (arg != JOB+10440 or m.memory.read(arg+16,1) != 0
                    or m.memory.read(arg+1484,4) != CACHE):
                raise Fault('unexpected development request notification')
        else:
            raise Fault(f'unmodeled owner event {event}')

    def apply(self,m):
        event,arg = m.r['d0'],m.r['a0']
        detail = dict(event=event,argument=hex(arg))
        if event == 19:
            size = m.memory.read(arg+72,4)
            address = 0x20000000+len(self.buffers)*0x03000000
            region = Region(address,bytearray([0xcd])*size+bytearray([0xa5])*16,True,'fixture output buffer')
            m.memory = Memory([*m.memory.regions,region])
            m.memory.write(arg+64,address,4)
            self.buffers.append(dict(address=address,size=size,id=m.memory.read(arg+76,4)))
            detail.update(self.buffers[-1])
        elif event == 14:
            detail['descriptor_id'] = m.memory.read(arg+4,2)
        # Native 6074f035 treats a zero event-13 response as cancellation.
        m.r['d0'] = int(self.continue_processing) if event == 13 else 1
        if event == 21:
            m.r['d0'] = int(self.accept_request)
        detail['returned'] = m.r['d0']
        return detail


class FixturePool:
    """Two predeclared 16KiB slots, never an unbounded success allocator."""
    name = 'two-slot-fixture-pool'

    def __init__(self):
        self.available = [JOB, CACHE]
        self.live = []

    def validate(self, m, mask, frame):
        if (mask,frame,m.r['d0']) != (0xe0,16,0x10004) or not self.available:
            raise Fault('fixture pool ABI, pool ID or capacity mismatch')
        if not any(r.address == self.available[0] and len(r.data) == 16384 and r.writable
                   for r in m.memory.regions):
            raise Fault('missing declared pool slot')

    def apply(self, m):
        address = self.available.pop(0)
        self.live.append(address)
        m.r['a0'] = address
        return dict(pool='0x10004',returned=hex(address),capacity=16384)


class FixtureEventBits:
    """Single-thread host completion-token allocation; never completes a request."""
    name = 'fixture-event-bit-pool'

    def __init__(self):
        self.allocated = 0

    def validate(self,m,mask,frame):
        if (mask,frame) != (0xe0,16) or m.memory.read(0x8050,4) != 0:
            raise Fault('event-bit fixture ABI/task mismatch')
        if self.allocated == 0xffffffff:
            raise Fault('fixture event bits exhausted; native wait not modeled')

    def apply(self,m):
        bit = next(1 << n for n in range(32) if not self.allocated & (1 << n))
        self.allocated |= bit
        m.r['d0'] = bit
        return dict(bit=bit,allocated=self.allocated,completed=False)


class FixtureConsumerSlot:
    """One declared request ID and workspace; no scheduler/ISP/completion model."""
    name = 'fixture-consumer-slot'

    def __init__(self, kind, identity=None):
        if kind not in ('id','workspace'):
            raise ValueError('unknown consumer fixture kind')
        self.kind, self.used = kind, False
        self.identity = identity

    def validate(self,m,mask,frame):
        expected = (0xf0,20) if self.kind == 'id' else (0xf0,36)
        if (mask,frame) != expected or self.used:
            raise Fault('consumer slot ABI or capacity mismatch')
        if self.kind == 'workspace':
            if (m.r['d0'] != 0x8000 or self.identity is None
                    or self.identity.kind != 'id' or not self.identity.used):
                raise Fault('workspace requires the declared live consumer ID')
            if not any(r.address == SCRATCH and len(r.data) == 9596 and r.writable for r in m.memory.regions):
                raise Fault('missing declared consumer workspace')

    def apply(self,m):
        self.used = True
        if self.kind == 'id':
            m.r['d0'] = 0x8000
            return dict(request_id='0x8000',completed=False)
        m.memory.write(SCRATCH+9584,0,4)  # Explicit synthetic owner/task tag.
        m.memory.write(SCRATCH+9588,0x8000,4)
        m.memory.write(SCRATCH+9592,1,1)
        m.r['a0'] = SCRATCH
        return dict(address=hex(SCRATCH),size=9596,completed=False)


def load():
    path = ROOT/'local/epl9-1101-analysis/decoded/00_0100_406e0020.decoded.bin'
    image = path.read_bytes()
    if len(image) != 26214336 or hashlib.sha256(image).hexdigest() != MAIN_SHA:
        raise ValueError('exact E-PL9 1.1 main required')
    reader = ROOT/'local/mn103-tooling/mn103-reader.exe'
    if hashlib.sha256(reader.read_bytes()).hexdigest() != 'e1c9bcb2b2467a44b8f6e2b6910c9868eff6ce571c36d5b9ad41d1d8693a76ae':
        raise ValueError('reader identity mismatch')
    code = {}
    for start,end in {**WINDOWS,**SERVICE_WINDOWS,**EXTRA_WINDOWS,**JOB_WINDOWS}.values():
        listing = subprocess.check_output([str(reader),str(path),hex(BASE),hex(start-BASE),hex(end-BASE)],text=True)
        decoded = parse_listing(listing,image,BASE)
        for at in code.keys() & decoded.keys():
            if code[at] != decoded[at]:
                raise ValueError(f'conflicting decode at {at:#x}')
        code.update(decoded)
    for at, expected in {**EXPECTED,**JOB_ANCHORS}.items():
        _,op,args = code[at]
        assert op+'\t'+','.join(args) == expected
    return image,code


def resume(m, pc, stops=()):
    try:
        result = m.run(pc, [RETURN,*stops],limit=500000)
    except Fault as error:
        result = dict(status='fault',error=str(error))
    return result | dict(registers={k:hex(v) for k,v in m.r.items()},
                         instructions=len(m.trace),last_instructions=[hex(p) for p in m.trace[-8:]])


def invoke(m, entry, mask, frame, regs):
    if m.r['sp'] != SP:
        raise ValueError('cannot invoke with unbalanced caller stack')
    m.r.update(regs)
    return resume(m,m.enter(entry,RETURN,mask,frame))


def cache_experiment(image,code):
    """Native cold/update/warm comparisons; no processing success is modeled."""
    request,context,obj = 0x10050000,0x10051000,0x10052000
    cache,req,ctx,parameter = bytearray([0xa5])*16384,bytearray(1876),bytearray(112),bytearray(24)
    req[8:12] = header(11)
    struct.pack_into('<I',req,1524,obj)
    struct.pack_into('<I',ctx,4,request)
    struct.pack_into('<2I',ctx,12,0x19020000,0x19020000+3680)
    struct.pack_into('<6I',parameter,0,0,17,0,23,0x19000000,29)
    m=CallMachine(code,Memory([Region(BASE,image),Region(CACHE,cache,True),
        Region(request,req,True),Region(context,ctx),Region(obj,parameter,True),
        Region(0x19020000,bytearray(5200)),
        Region(STACK,bytearray(16384),True)]),{'sp':SP},models={0x4700111e:FillModel()})
    def call(entry,mask,frame,regs):
        r=invoke(m,entry,mask,frame,regs)
        assert r.get('pc') == RETURN and m.r['sp'] == SP,r
        return m.r['d0']
    call(0x6073e588,0x30,12,{'a0':CACHE})
    def compare():
        return call(0x6073e6ac,0xf0,20,{'a0':CACHE,'a1':request})
    cold=compare()
    call(0x6073e953,0x30,16,{'a0':CACHE,'a1':context})
    warm=compare()
    struct.pack_into('<I',parameter,16,0x19010000)
    table_pointer_only=compare()
    struct.pack_into('<I',parameter,20,30)
    table_token=compare()
    struct.pack_into('<I',parameter,20,29)
    req[8:12]=header(0x01010078)
    mode_change=compare()
    req[8:12]=header(11)
    req[1813]=50
    recipe_byte=compare()
    assert table_pointer_only == warm and table_token ^ warm == 0x10000000
    assert mode_change ^ warm == 2 and recipe_byte == warm
    assert cold & 0x10000000 and not warm & 0x10000000
    assert cache[5764:] == b'\xa5'*(16384-5764)
    return dict(cold=hex(cold),warm=hex(warm),table_pointer_only=hex(table_pointer_only),
                table_token_change=hex(table_token),mode_change=hex(mode_change),
                request_byte_1813_change=hex(recipe_byte),
                scope='only native cache comparator/update, not downstream behavior',events=m.events)


def experiment(image, code, key, kind, selector, *, start_frame=True,
               continue_processing=True, accept_request=True, provide_long_output=True):
    if key not in RECIPES or kind not in (0x200,0x100,0x40) or selector not in (0,2):
        raise ValueError('only the declared target/key/type/selector grid is supported')
    job, cache = bytearray([0xa5])*16384, bytearray([0xa5])*16384
    params = bytearray(32)
    params[8:12] = header(key)
    struct.pack_into('<H',params,16,kind)
    params[19] = 1  # Explicit ROM dimension-table selector, not a null entry.
    params[21] = selector
    struct.pack_into('<2I',params,0,OWNER_CALLBACK,OWNER_CONTEXT)
    owner = FixtureOwner(continue_processing,accept_request)
    pool = FixturePool()
    consumer_id = FixtureConsumerSlot('id')
    memory = Memory([Region(BASE,image),Region(JOB,job,True,'job'),Region(CACHE,cache,True,'cache'),
                     Region(PARAMS,params),Region(ERROR,bytearray(4),True),
                     Region(STACK,bytearray(16384),True,'stack'),Region(0x8050,bytearray(4)),
                     Region(OWNER_CONTEXT,bytearray(4)),
                     Region(SCRATCH,bytearray(9596),True,'consumer workspace')])
    m = CallMachine(code,memory,{'sp':SP,'a0':PARAMS,'a1':ERROR,'d0':0},
                    models={0x60402595:pool,0x4700111e:FillModel(),OWNER_CALLBACK:owner,
                            0x6074aea9:FixtureEventBits(),
                            0x607490c8:consumer_id,
                            0x607a038d:FixtureConsumerSlot('workspace',consumer_id)})
    # Host redirects only the Watercolor-specific branch and retains early paths.
    result = resume(m,m.enter(0x6074df04,RETURN,0xf0,44),[0x60752202])
    redirected = result.get('pc') == 0x60752202
    if redirected:
        result = resume(m,0x607523a5)
    report = dict(key=hex(key),kind=hex(kind),selector=selector,constructor=result,
                  redirected=redirected,events=list(m.events),
                  cache_pointer=hex(memory.read(JOB+12316,4)),
                  error=hex(memory.read(ERROR,2)),allocations=pool.live)
    if result.get('pc') != RETURN:
        return report
    assert m.r['sp'] == SP and m.r['d0'] == JOB
    assert memory.read(JOB+12316,4) == CACHE
    assert job[14552:] == b'\xa5'*(16384-14552)
    assert cache[5764:] == b'\xa5'*(16384-5764)
    count = memory.read(JOB+10390,2)
    assert 0 < count <= 16
    report['entries'] = [list(struct.unpack_from('<3I',job,10060+i*12)) for i in range(count)]
    report['index_after_constructor'] = memory.read(JOB+10388,2)
    report['cache_sentinels'] = {str(o):hex(memory.read(CACHE+o,s))
        for o,s in ((5682,2),(5684,2),(5694,2),(5699,1),(5748,4),(5760,4))}
    # Explicit synthetic caller data for two crop ratio records; not camera data.
    for offset in (3730,3738):
        struct.pack_into('<4H',job,offset,640,480,640,480)
    width,height = (640,480) if kind == 0x40 else (4608,3456)
    # Buffer layout/format are a synthetic caller fixture, not decoded sensor data.
    descriptors = [(36,SOURCE,kind),(100,OUTPUT,0x0302)]
    if provide_long_output:
        descriptors.append((4264,OUTPUT,0x0302))
    for offset,address,fmt in descriptors:
        struct.pack_into('<I',job,offset,address)
        struct.pack_into('<6H',job,offset+8,fmt,width,width,height,width,height)
    m.memory = Memory([*m.memory.regions,Region(SOURCE,bytearray(width*height*2),False,'synthetic source'),
                       Region(OUTPUT,bytearray([0xcd])*(width*height*2),True,'synthetic destination')])
    if start_frame:
        report['start'] = invoke(m,0x6074e348,0xf0,96,{'d0':JOB})
        if report['start'].get('pc') != RETURN or m.r['d0'] != 0:
            report['events'] = m.events
            return report
    report['index_before_executor'] = memory.read(JOB+10388,2)
    # Mode handoff after the complete constructor, before execution.
    job[12:16] = header(11)
    struct.pack_into('<I',job,10384,11)
    report['executor'] = invoke(m,0x6074e6eb,0xf0,32,{'d0':JOB,'d1':count})
    # This is a native cursor, NOT a successful-entry counter (see controls).
    report['executor_index'] = memory.read(JOB+10388,2)
    report['events'] = m.events
    report['fixture_buffers'] = owner.buffers
    report['request_words'] = {str(o):hex(m.memory.read(JOB+10440+o,4))
                               for o in (0,4,8,12,16,20,84,212,276,340,404,916,972,1196,1252,1484,1524,1640)}
    report['cache_compare_executed'] = 0x6073e6ac in m.trace and 0x6073e950 in m.trace
    report['processor_entered'] = 0x60734068 in m.trace
    report['native_color_entered'] = 0x6079ebcc in m.trace
    report['pending_record'] = {str(o):hex(m.memory.read(JOB+13640+o,4)) for o in (0,8,12,16)}
    report['cancelled'] = memory.read(JOB+10394,2)
    report['worklist_calls'] = [hex(e['target']) for e in m.events
        if e['op'] in ('call','calls') and e.get('target') in {row[0] for row in report['entries']}]
    assert job[14552:] == b'\xa5'*(16384-14552) and cache[5764:] == b'\xa5'*(16384-5764)
    for buffer in owner.buffers:
        region = next(r for r in m.memory.regions if r.address == buffer['address'])
        assert region.data[buffer['size']:] == b'\xa5'*16
        buffer['payload_changed'] = region.data[:buffer['size']].count(0xcd) != buffer['size']
    output_region = next(r for r in m.memory.regions if r.address == OUTPUT)
    report['output_changed'] = output_region.data.count(0xcd) != len(output_region.data)
    report['allocation_canaries_intact'] = True
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,required=True)
    args=p.parse_args()
    if not __debug__ or args.out.exists() or not args.out.resolve().is_relative_to((ROOT/'local').resolve()):
        p.error('assertions and a new ignored local output directory are required')
    image,code=load()
    cases=[experiment(image,code,k,kind,s) for k in RECIPES for kind in (0x200,0x100,0x40) for s in (0,2)]
    for case in cases:
        assert case['constructor'].get('pc') == case['start'].get('pc') == RETURN
        assert case['start']['registers']['d0'] == '0x0'
        assert case['index_after_constructor'] == 16 and case['index_before_executor'] == 0
        assert case['executor_index'] == 1 and len(case['worklist_calls']) == 2
        assert not case['output_changed'] and not any(b['payload_changed'] for b in case['fixture_buffers'])
        assert case['cache_sentinels'] == {'5682':'0xffff','5684':'0xffff','5694':'0x8001',
                                         '5699':'0x81','5748':'0xffffffff','5760':'0x0'}
        if case['kind'] == '0x40':
            assert case['executor'].get('error') == 'owner descriptor 0xff07 not declared by fixture'
            assert not case['cache_compare_executed'] and not case['processor_entered']
        else:
            target = 0x6079bf86 if case['kind'] == '0x200' else 0x6079a304
            assert case['executor'].get('target') == target and case['executor']['status'] == 'external_call'
            assert case['cache_compare_executed'] and case['processor_entered']
            assert case['request_words']['1484'] == hex(CACHE) and case['request_words']['8'] == '0xb0000'
            assert case['request_words']['916'] != '0x0'
    controls = []
    for key in RECIPES:
        for name,options,selector in [('no_frame_start',{'start_frame':False},0),
                ('owner_cancel',{'continue_processing':False},0),
                ('request_rejected',{'accept_request':False},0),
                ('missing_long_output',{'provide_long_output':False},2)]:
            case=experiment(image,code,key,0x200,selector,**options)
            case['control']=name
            assert not case['output_changed'] and not case['processor_entered']
            if name == 'no_frame_start':
                assert case['executor']['registers']['d0'] == '0x0' and not case['worklist_calls']
                assert case['executor_index'] == 16
            elif name == 'missing_long_output':
                assert case['executor'].get('error') == "0x6073f22f movhu ['(8,a0)', 'd0']: unmapped access at 0x8, size 2"
            else:
                assert case['executor'].get('pc') == RETURN and case['executor']['registers']['d0'] == '0x9e01'
                assert case['cancelled'] == 1
                if name == 'owner_cancel':
                    assert not case['worklist_calls'] and case['executor_index'] == 0
                else:
                    assert all(v == '0x0' for v in case['pending_record'].values())
            controls.append(case)
    source_hashes={name:hashlib.sha256((ROOT/'scripts'/name).read_bytes()).hexdigest() for name in
                   ('epl9_job_probe.py','epl9_integrated_probe.py','epl9_offline_prototype.py',
                    'epl9_art_routing_probe.py','epl9_service_audit.py',
                    'mn103_subset.py','mn103_calls.py','mn103_models.py')}
    report=dict(model='Olympus E-PL9',displayed_version='1.1 (owner report)',main_build='1101',
                stock_bytes=104552480,stock_sha256=STOCK_SHA,main_bytes=len(image),main_sha256=MAIN_SHA,
                stock_identity_from_prior_audit=True,analysis_base=hex(BASE),
                reader_sha256='e1c9bcb2b2467a44b8f6e2b6910c9868eff6ce571c36d5b9ad41d1d8693a76ae',
                synthetic_inputs=True,camera_accessed=False,firmware_modified=False,
                full_pixel_cycle_passed=False,cases=cases,controls=controls,cache_audit=cache_experiment(image,code),
                source_sha256=source_hashes,decode_anchors=len({**EXPECTED,**JOB_ANCHORS}),
                new_windows={k:[hex(a),hex(b)] for k,(a,b) in JOB_WINDOWS.items()},
                limitations=['synthetic descriptors and software resource contracts',
                             'no RTOS scheduling, DMA, ISP, request completion or camera measurement',
                             'no calibrated film table attached in the connected job grid'])
    args.out.mkdir(parents=True)
    (args.out/'results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    def brief(v):
        return {k:hex(x) if k in ('pc','target') else x for k,x in v.items()
                if k in ('status','pc','target','error','instructions')} | {'d0':v['registers']['d0']}
    print(json.dumps([{'key':r['key'],'kind':r['kind'],'selector':r['selector'],
        **{k:brief(r[k]) for k in ('constructor','start','executor') if k in r}} for r in cases]))


if __name__=='__main__':
    main()
