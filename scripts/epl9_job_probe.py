"""Connect native E-PL9 job construction and execution with explicit host inputs."""
import argparse
import hashlib
import json
import struct
import subprocess
from pathlib import Path

from epl9_integrated_probe import EXTRA_WINDOWS, WINDOWS, SERVICE_WINDOWS, EXPECTED, RETURN
from epl9_art_routing_probe import ROOT, BASE, MAIN_SHA, STOCK_SHA
from epl9_offline_prototype import header, RECIPES, check_packing
from mn103_subset import Memory, Region, Fault, parse_listing
from mn103_calls import CallMachine
from mn103_models import FillModel
from epl9_placement import module_regions

JOB, CACHE = 0x11000000, 0x11010000
PARAMS, ERROR, STACK, SP = 0x10020000, 0x10030000, 0x10010000, 0x10013c00
OWNER_CALLBACK, OWNER_CONTEXT, SOURCE, OUTPUT = 0x0f000000, 0x10040000, 0x12000000, 0x16000000
SCRATCH = 0x18000000
PARAMETER_OBJECT, RECIPE_TABLE = 0x19000000, 0x19010000
JOB_WINDOWS = {
    'wide_arithmetic_helpers': (0x604bbecc, 0x604bc028),
    'job_destructor': (0x6074e2fd, 0x6074e33b),
    'cache_destructor': (0x6073e57a, 0x6073e588),
    'owner_buffer_free': (0x6074ad9f, 0x6074adbe),
    'event_clear_wrapper': (0x6074b0ce, 0x6074b10d),
    'consumer_id_cleanup_wrapper': (0x6072fac5, 0x6072fb1b),
    'cache_constructor': (0x6073e562, 0x6073e6ac),
    'cache_descriptor_init': (0x60749fa5, 0x60749fb6),
    'job_services': (0x6074eca0, 0x6074ed70),
    'job_builder_wrappers': (0x607507b9, 0x60750808),
    'job_effect_objects': (0x60752b86, 0x60752f56),
    'job_effect_cleanup': (0x60752f56, 0x60753040),
    'dimension_tables': (0x60749187, 0x607491e9),
    'request_parameter_views': (0x60750498, 0x607504f6),
    'buffer_allocation': (0x6074a824, 0x6074aaa5),
    'job_start': (0x6074e348, 0x6074e6eb),
    'buffer_release_and_reset': (0x6074abc7, 0x6074acf9),
    'job_pending_reset': (0x6074ed70, 0x6074edac),
    'buffer_available_slot': (0x6074ae89, 0x6074aea9),
    'start_callback_bodies': (0x607503e6, 0x60750498),
    'pending_wait_wrapper': (0x6074b125, 0x6074b143),
    'processing_classifier': (0x60792399, 0x60792510),
    'processing_classifier_support': (0x607925d2, 0x60792764),
    'early_processing_classifier': (0x6078e82d, 0x6078e890),
    'bayer_short_configuration': (0x6078e890, 0x6078ef28),
    'bayer_area_geometry': (0x6078ffb0, 0x607900d8),
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
    'consumer_cleanup': (0x6073f33d, 0x6073f74f),
    'pending_signal_wrapper': (0x6074af81, 0x6074af9e),
    'request_type_helpers': (0x607a3bed, 0x607a3df6),
    'processing_dispatch': (0x60734068, 0x60734302),
    'processing_configuration_start': (0x6073af53, 0x6073b603),
    'processing_configuration_helpers': (0x60734519, 0x6073a880),
    'input_format_dispatch': (0x60799f48, 0x60799fac),
    'input_format_configuration': (0x607a01b1, 0x607a038d),
    'input_format_parameters': (0x60799fdc, 0x6079a304),
    'input_format_table': (0x60749150, 0x60749187),
    'optional_raw_parameters_prefix': (0x6078ac47, 0x6078ace6),
    'color_configuration_full': (0x60799eb6, 0x607a038d),
    'parameter_interpolation': (0x607a460d, 0x607a476b),
    'parameter_interpolation_tables': (0x607a44c9, 0x607a460d),
    'post_color_configuration': (0x6073e1c7, 0x6073e562),
    'post_color_gate': (0x60792332, 0x60792399),
    'post_color_parameters': (0x60792332, 0x60799eb6),
    'consumer_output_configuration': (0x6073abd3, 0x6073af53),
    'frame_gates': (0x607a399b, 0x607a3bed),
    'processing_store_configuration': (0x6073b603, 0x6073e1c7),
    'optional_processing_stage': (0x6078bd18, 0x6078c250),
    'processing_resource_wait': (0x607a18ae, 0x607a18f3),
    'hardware_start': (0x6073f74f, 0x6073f860),
    'hardware_synchronization': (0x6073eaea, 0x6073eb1a),
    'parameter_object_builder': (0x6078ab39, 0x6078ac47),
    'parameter_slot_selection': (0x6074b433, 0x6074b487),
    'optional_geometry_configuration': (0x6078c378, 0x6078c43d),
}
JOB_ANCHORS = {
    0x604bbf63: 'subc\td3,d1',
    0x604bbf6e: 'addc\td1,d1',
    0x604bbf85: 'ror\td2',
    0x6073920e: 'call\t0x604bbfac,[d2,d3],8',
    0x6078e837: 'call\t0x6078ea3d,[d2,d3,a2,a3],44',
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
    0x6073eafa: 'mov\td0,(0x9880014c)',
    0x6078ab52: 'mov\td0,(a2)',
    0x6078ab6b: 'mov\ta0,(8,a2)',
    0x6078ab94: 'mov\ta0,(16,a2)',
    0x6078ac23: 'mov\t-100,d1',
    0x6078ac40: 'movbu\td0,(28,a2)',
    0x6074f354: 'mov\t3710,a1',
    0x6074f359: 'mov\t1576,a0',
    0x6079565d: 'movhu\t(2,a0),d3',
    0x6079fc15: 'call\t0x6079ebcc,[d2,d3,a2,a3],20',
    0x6074b44d: 'udfu01\t4184,d2',
}


class FixtureOwner:
    """Declared host descriptors and bounded buffers, never an ISP model."""
    name = 'synthetic-frame-owner'

    def __init__(self, continue_processing=True, accept_request=True, provide_slot=False,
                 source_bounds=(4608,3456)):
        self.buffers = []
        self.released_buffers = set()
        self.provide_slot = provide_slot
        self.slot_buffers = {}
        self.active_slots = set()
        # Caller supplies ff00 before dispatch; selector 2 releases this
        # reference without fetching it through event 14 first.
        self.descriptor_refs = {0xff00:1} if provide_slot else {}
        self.continue_processing = continue_processing
        self.accept_request = accept_request
        self.source_bounds=source_bounds

    def validate(self,m,mask,frame):
        if (mask,frame,m.r['a1']) != (0,0,OWNER_CONTEXT):
            raise Fault('fixture owner callback ABI/context mismatch')
        event, arg = m.r['d0'],m.r['a0']
        if event == 2:
            # 6079c026 offers nine native halfword coefficients to the owner.
            if not max(STACK,m.r['sp']+4) <= arg or arg+18 > STACK+16384 or arg%2:
                raise Fault('coefficient notification outside declared stack')
            if not any(e.get('pc') == 0x6079c026 for e in m.events[-3:]):
                raise Fault('undeclared coefficient callback caller')
        elif event == 14:
            descriptor_id = m.memory.read(arg+4,2)
            if descriptor_id in (0xff07,0xff0b) and self.provide_slot:
                self.validate_slot(m,arg,descriptor_id)
                return
            offsets={1:36,2:100,0xff12:4264}
            if self.provide_slot:
                offsets[0xff00]=3984
            if m.memory.read(arg,4) != JOB+36 or descriptor_id not in offsets:
                raise Fault(f'owner descriptor {descriptor_id:#x} not declared by fixture')
            offset = offsets[descriptor_id]
            pointer = m.memory.read(JOB+offset,4)
            if pointer != (SOURCE if descriptor_id == 1 else OUTPUT):
                raise Fault('fixture descriptor points outside its assigned payload')
            stride,width,height = [m.memory.read(JOB+offset+n,2) for n in (10,12,14)]
            size = stride*height*2  # Declared two-byte fixture layout only.
            max_stride,max_height=self.source_bounds if descriptor_id==1 else (4608,3456)
            if not (0 < width <= stride <= max_stride and 0 < height <= max_height):
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
        elif event == 20:
            if not JOB+5668 <= arg < JOB+9892 or (arg-JOB-5668)%88:
                raise Fault('buffer release outside native buffer table')
            pointer=m.memory.read(arg+64,4)
            if pointer in self.released_buffers or not any(b['address']==pointer and
                    b['size']==m.memory.read(arg+72,4) and b['id']==m.memory.read(arg+76,4)
                    for b in self.buffers):
                raise Fault('buffer release requires matching live owned allocation')
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
        elif event == 23 and self.provide_slot:
            identifier=m.memory.read(arg+4,2)
            if identifier not in (0xff07,0xff0b) or identifier in self.active_slots:
                raise Fault('unexpected slot activation')
            if not m.memory.read(JOB+{0xff07:4960,0xff0b:5200}[identifier],4):
                raise Fault('activation requires an allocated or borrowed payload')
            self.validate_slot(m,arg,identifier)
        elif event == 22 and self.provide_slot:
            if arg != 0:
                raise Fault('unexpected finished-request notification')
        elif event == 16 and self.provide_slot:
            identifier=m.memory.read(arg+4,2)
            if m.memory.read(arg,4)!=JOB+36 or not self.descriptor_refs.get(identifier,0):
                raise Fault(f'undeclared descriptor release {identifier:#x}')
        else:
            raise Fault(f'unmodeled owner event {event}')

    def validate_slot(self,m,arg,identifier):
        offset={0xff07:4960,0xff0b:5200}[identifier]
        if m.memory.read(arg,4) != JOB+36 or m.memory.read(JOB+offset+8,2) != 0x302:
            raise Fault('slot descriptor context or format mismatch')
        stride,width,height=[m.memory.read(JOB+offset+n,2) for n in (10,12,14)]
        if not (0 < width <= stride <= 4608 and 0 < height <= 3456):
            raise Fault(f'invalid slot dimensions: stride={stride}, width={width}, height={height}')
        size=stride*height*2
        pointer=m.memory.read(JOB+offset,4)
        if identifier==0xff07 and pointer==OUTPUT:
            if not any(r.writable and r.address<=pointer and pointer+size<=r.address+len(r.data) for r in m.memory.regions):
                raise Fault('borrowed slot exceeds output payload')
            return
        slot=self.slot_buffers.get(identifier)
        if slot is None:
            if pointer or size > 32*1024*1024:
                raise Fault('unexpected slot payload or size')
            m.memory.region(JOB+offset,4,True)
            address=0x1b000000 if identifier==0xff07 else 0x1c000000
            if any(address < r.address+len(r.data) and r.address < address+size+16 for r in m.memory.regions):
                raise Fault('slot allocation overlaps memory')
        elif pointer != slot['address'] or size != slot['size']:
            raise Fault('slot payload changed during use')

    def apply(self,m):
        event,arg = m.r['d0'],m.r['a0']
        detail = dict(event=event,argument=hex(arg))
        if event == 2:
            detail['coefficients_preserved'] = [m.memory.read(arg+i*2,2) for i in range(9)]
        elif event == 19:
            size = m.memory.read(arg+72,4)
            address = 0x20000000+len(self.buffers)*0x03000000
            region = Region(address,bytearray([0xcd])*size+bytearray([0xa5])*16,True,'fixture output buffer')
            m.memory = Memory([*m.memory.regions,region])
            m.memory.write(arg+64,address,4)
            self.buffers.append(dict(address=address,size=size,id=m.memory.read(arg+76,4)))
            detail.update(self.buffers[-1])
        elif event == 14:
            detail['descriptor_id'] = m.memory.read(arg+4,2)
            identifier=detail['descriptor_id']
            self.descriptor_refs[identifier]=self.descriptor_refs.get(identifier,0)+1
            if identifier in (0xff07,0xff0b) and m.memory.read(JOB+{0xff07:4960,0xff0b:5200}[identifier],4) != OUTPUT:
                offset={0xff07:4960,0xff0b:5200}[identifier]
                if identifier not in self.slot_buffers:
                    size=m.memory.read(JOB+offset+10,2)*m.memory.read(JOB+offset+14,2)*2
                    address=0x1b000000 if identifier==0xff07 else 0x1c000000
                    region=Region(address,bytearray([0xcd])*size+bytearray([0xa5])*16,True,'owner slot payload')
                    m.memory=Memory([*m.memory.regions,region])
                    m.memory.write(JOB+offset,region.address,4)
                    self.slot_buffers[identifier]=dict(address=region.address,size=size,id=identifier)
                    self.buffers.append(self.slot_buffers[identifier])
                detail.update(self.slot_buffers[identifier])
        elif event == 20:
            pointer=m.memory.read(arg+64,4)
            self.released_buffers.add(pointer)
            detail.update(released=hex(pointer),bytes_retained_for_audit=True)
        elif event == 23:
            identifier=m.memory.read(arg+4,2)
            self.active_slots.add(identifier)
            detail.update(slot_active=True,descriptor_id=identifier)
        elif event == 16:
            identifier=m.memory.read(arg+4,2)
            self.descriptor_refs[identifier]-=1
            self.active_slots.discard(identifier)
            detail.update(descriptor_id=identifier,slot_active=False,payload_retained_for_audit=True)
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


class FixturePoolFree:
    """Release a declared pool slot once; retain bytes only for audit."""
    name='fixture-pool-free'

    def __init__(self,pool):
        self.pool=pool

    def validate(self,m,mask,frame):
        if (mask,frame)!=(0,4) or m.r['a0'] not in self.pool.live:
            raise Fault('pool free requires a live declared slot')
        if any(m.memory.read(JOB+13640+n,4) for n in range(0,56,4)):
            raise Fault('pool free with pending request')

    def apply(self,m):
        address=m.r['a0']; self.pool.live.remove(address)
        return dict(released=hex(address),bytes_retained_for_audit=True)


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
        if kind not in ('id','workspace','release'):
            raise ValueError('unknown consumer fixture kind')
        self.kind, self.used = kind, False
        self.identity = identity

    def validate(self,m,mask,frame):
        expected = {'id':(0xf0,20),'workspace':(0xf0,36),'release':(0xf0,24)}[self.kind]
        if (mask,frame) != expected or self.used:
            raise Fault('consumer slot ABI or capacity mismatch')
        if self.kind == 'workspace':
            if (m.r['d0'] != 0x8000 or self.identity is None
                    or self.identity.kind != 'id' or not self.identity.used):
                raise Fault('workspace requires the declared live consumer ID')
            if not any(r.address == SCRATCH and len(r.data) == 9596 and r.writable for r in m.memory.regions):
                raise Fault('missing declared consumer workspace')
        if self.kind == 'release':
            if (m.r['a0'] != SCRATCH or self.identity is None or self.identity.kind != 'workspace'
                    or not self.identity.used or m.memory.read(SCRATCH+9592,1) != 1):
                raise Fault('release requires a live declared workspace')

    def apply(self,m):
        self.used = True
        if self.kind == 'release':
            m.memory.write(SCRATCH+9592,2,1)
            return dict(address=hex(SCRATCH),state=2,completed=False)
        if self.kind == 'id':
            m.r['d0'] = 0x8000
            return dict(request_id='0x8000',completed=False)
        m.memory.write(SCRATCH+9584,0,4)  # Explicit synthetic owner/task tag.
        m.memory.write(SCRATCH+9588,0x8000,4)
        m.memory.write(SCRATCH+9592,1,1)
        m.r['a0'] = SCRATCH
        return dict(address=hex(SCRATCH),size=9596,completed=False)


class FixtureSignal:
    """Signal an allocated host event token; no image completion is implied."""
    name='fixture-event-signal'

    def __init__(self,pool):
        self.pool=pool
        self.signalled=0

    def validate(self,m,mask,frame):
        bit=m.r['d1']
        if ((mask,frame,m.r['d0']) != (0xc0,12,0) or bit == 0 or
                bit & (bit-1) or not self.pool.allocated & bit or self.signalled & bit):
            raise Fault('event signal requires one live unsignalled token')

    def apply(self,m):
        bit=m.r['d1']; self.signalled|=bit; m.r['d0']=0
        return dict(bit=bit,signalled=self.signalled,pixels_completed=False)


class FixtureCompletion:
    """Finite host event/pool contracts; native request cleanup stays executable.

    Non-autoclearing event and one idle consumer are explicit assumptions.
    An unsignalled wait stops; it never fabricates scheduler progress.
    """
    name='fixture-completion-resources'

    def __init__(self,kind,signal,identity,workspace):
        self.kind,self.signal,self.identity,self.workspace=kind,signal,identity,workspace

    def validate(self,m,mask,frame):
        expected={'wait':(0xf0,40),'clear':(0xf0,20),'token':(0xe0,16),
                  'consumer':(0xf0,28),'workspace':(0x80,8),'id':(0xc0,12)}
        if (mask,frame)!=expected[self.kind]:
            raise Fault('completion resource ABI mismatch')
        if self.kind=='wait':
            if (m.r['d0'],m.r['a1'],m.memory.read(m.r['sp']+4,4))!=(0xe3,1,1000):
                raise Fault('undeclared event wait ID/mode/timeout')
            if not m.r['d1'] or m.r['d1'] & ~self.signal.pool.allocated or not m.r['d1'] & self.signal.signalled:
                raise Fault('wait requires an allocated already-signalled event')
            if not m.r['sp']+8 <= m.r['a0'] <= STACK+16384-4:
                raise Fault('wait result overlaps call frame or exceeds stack')
            m.memory.region(m.r['a0'],4,True)
        elif self.kind=='clear':
            removed=self.signal.signalled & ~m.r['d1']
            if m.r['d0']!=0xe3 or not removed or removed & ~self.signal.pool.allocated:
                raise Fault('event clear requires a live signalled token')
        elif self.kind=='token':
            bit=m.r['d0']
            if not bit or bit & (bit-1) or not self.signal.pool.allocated & bit or self.signal.signalled & bit:
                raise Fault('token release requires a live cleared token')
        else:
            if m.r['d0']!=0x8000 or not self.identity.used or not self.workspace.used:
                raise Fault('cleanup requires the declared live consumer')
            if getattr(m,'processor_return',None)!=0x9e40:
                raise Fault('consumer teardown only declared for configuration rejection')
            state=m.memory.read(SCRATCH+9592,1)
            if state != (0 if self.kind=='id' else 2):
                raise Fault('consumer cleanup order mismatch')

    def apply(self,m):
        if self.kind=='wait':
            m.memory.write(m.r['a0'],self.signal.signalled,4)
        elif self.kind=='clear':
            self.signal.signalled &= m.r['d1']
        elif self.kind=='token':
            self.signal.pool.allocated &= ~m.r['d0']
        elif self.kind=='workspace':
            for offset,size in ((9584,4),(9588,4),(9592,1)):
                m.memory.write(SCRATCH+offset,0,size)
        elif self.kind=='id':
            self.identity.used=False
        m.r['d0']=0
        return dict(resource_operation=self.kind,pixels_completed=False)


class FixtureLock:
    """One uncontended single-thread acquisition; no IRQ or device emulation."""
    name = 'fixture-uncontended-lock'

    def __init__(self, value, mask, frame):
        self.expected = (value,mask,frame)
        self.held = False

    def validate(self,m,mask,frame):
        if (m.r['d0'],mask,frame) != self.expected or self.held:
            raise Fault('lock fixture ABI/key mismatch or already held')

    def apply(self,m):
        self.held = True
        m.r['d0'] = self.expected[0]
        return dict(key=hex(m.r['d0']),held=True,device_accessed=False)


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
        result = m.run(pc, [RETURN,*stops,0x6072fdd3],limit=500000)
        if result.get('pc') == 0x6072fdd3:
            m.processor_return=m.r['d0']
            result=m.run(0x6072fdd3,[RETURN,*stops],limit=500000)
    except Fault as error:
        result = dict(status='fault',error=str(error))
    return result | dict(registers={k:hex(v) for k,v in m.r.items()},
                         instructions=len(m.trace),last_instructions=[hex(p) for p in m.trace[-8:]])


def invoke(m, entry, mask, frame, regs, stops=()):
    if m.r['sp'] != SP:
        raise ValueError('cannot invoke with unbalanced caller stack')
    m.r.update(regs)
    return resume(m,m.enter(entry,RETURN,mask,frame),stops)


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


def validate_bayer_source(source,width,height,fmt):
    """Bound the explicit owner's expanded mosaic without assigning HW packing."""
    sw,sh,stride=source['width'],source['height'],source['stride']
    if fmt not in (0x108,0x109) or not (0<width<=sw<=stride<=4672 and 0<height<=sh<=3472):
        raise ValueError('undeclared expanded 12-bit source geometry/format')
    if stride%64 or len(source['data'])!=stride*sh*2 or len(source['data'])>32*1024*1024:
        raise ValueError('expanded source extent/alignment mismatch')
    if not isinstance(source['data'],bytes):
        raise ValueError('source payload must be immutable bytes')


def experiment(image, code, key, kind, selector, *, start_frame=True,
               continue_processing=True, accept_request=True, provide_long_output=True,
               attach_table=False, provide_reference_dimensions=True, provide_slot=False,
               input_format=None, input_stride=None, destroy_job=False,
               legacy_output_offsets=False, source_fixture=None, native_module=None, machine_observer=None,
               gain_fixture=None, parameter_fixture=None):
    kinds=(0x200,0x100,0x40,0x1000) if parameter_fixture is not None else (0x200,0x100,0x40)
    if key not in RECIPES or kind not in kinds or selector not in (0,2):
        raise ValueError('only the declared target/key/type/selector grid is supported')
    if native_module is not None and attach_table:
        raise ValueError('native late hook must not be mixed with host table attachment')
    job, cache = bytearray([0xa5])*16384, bytearray([0xa5])*16384
    params = bytearray(32)
    params[8:12] = header(key)
    struct.pack_into('<H',params,16,kind)
    params[19] = 1  # Explicit ROM dimension-table selector, not a null entry.
    params[21] = selector
    struct.pack_into('<2I',params,0,OWNER_CALLBACK,OWNER_CONTEXT)
    if parameter_fixture is not None:
        if (not isinstance(parameter_fixture,bytes) or len(parameter_fixture)!=32 or
                parameter_fixture[8:12]!=header(key) or
                struct.unpack_from('<H',parameter_fixture,16)[0]!=kind or
                parameter_fixture[21]!=selector or not all(struct.unpack_from('<2I',parameter_fixture))):
            raise ValueError('native parameter fixture identity/size mismatch')
        params[:]=parameter_fixture
    source_bounds=(source_fixture['stride'],source_fixture['height']) if source_fixture else (4608,3456)
    owner = FixtureOwner(continue_processing,accept_request,provide_slot,source_bounds)
    pool = FixturePool()
    consumer_id = FixtureConsumerSlot('id')
    workspace = FixtureConsumerSlot('workspace',consumer_id)
    event_pool=FixtureEventBits()
    signal=FixtureSignal(event_pool)
    completion={address:FixtureCompletion(operation,signal,consumer_id,workspace) for address,operation in
        [(0x60418b31,'wait'),(0x60410a51,'clear'),(0x6074aef3,'token'),
         (0x60740038,'consumer'),(0x607a08aa,'workspace'),(0x60749116,'id')]}
    memory = Memory([Region(BASE,image),Region(JOB,job,True,'job'),Region(CACHE,cache,True,'cache'),
                     Region(PARAMS,params),Region(ERROR,bytearray(4),True),
                     Region(STACK,bytearray(16384),True,'stack'),Region(0x8050,bytearray(4)),
                     Region(OWNER_CONTEXT,bytearray(4)),
                     Region(0x8ff001b0,bytearray(5),True,'declared zero synchronization counters'),
                     Region(SCRATCH,bytearray(9596),True,'consumer workspace')])
    if native_module is not None:
        memory = Memory([*memory.regions,*module_regions(image,native_module)])
    m = CallMachine(code,memory,{'sp':SP,'a0':PARAMS,'a1':ERROR,'d0':0},
                    models={**completion,0x60402595:pool,0x604023b2:FixturePoolFree(pool),
                            0x4700111e:FillModel(),OWNER_CALLBACK:owner,
                            0x6074aea9:event_pool,
                            0x6074af2c:signal,
                            0x607490c8:consumer_id,
                            0x607a038d:workspace,
                            0x607a06d2:FixtureConsumerSlot('release',workspace),
                            0x607a17b7:FixtureLock(32 if kind==0x40 else 16,0xa0,12),
                            0x607a1841:FixtureLock(8,0xc0,16)})
    output_address_writes=[]
    native_write=m.write
    def observe_output_address(operand,value,size=4):
        if operand.startswith('(') and m.address(operand)==SCRATCH+9068+208:
            output_address_writes.append(dict(pc=hex(m.trace[-1]),value=hex(value&0xffffffff)))
        native_write(operand,value,size)
    m.write=observe_output_address
    source_reads=[]
    if machine_observer is not None:
        machine_observer(m)
    native_read=m.read
    def observe_source_read(operand,size=4):
        if operand.startswith('(') and SOURCE<=m.address(operand)<SOURCE+32*1024*1024:
            source_reads.append(dict(pc=hex(m.trace[-1]),address=hex(m.address(operand)),bytes=size))
        return native_read(operand,size)
    m.read=observe_source_read
    # Historical host routing is disabled when the emitted native gate is used.
    result = resume(m,m.enter(0x6074df04,RETURN,0xf0,44),[] if native_module is not None else [0x60752202])
    redirected = result.get('pc') == 0x60752202
    if redirected:
        result = resume(m,0x607523a5)
    report = dict(key=hex(key),kind=hex(kind),selector=selector,constructor=result,
                  parameter_fixture=parameter_fixture.hex() if parameter_fixture is not None else None,
                  redirected=redirected,events=list(m.events),
                  cache_pointer=hex(memory.read(JOB+12316,4)),
                  error=hex(memory.read(ERROR,2)),allocations=list(pool.live))
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
    # Historical synthetic four-halfword records; not camera data. A fresh
    # trace shows the +3730 record reaches the color-gain producer, so these
    # values must not all be interpreted as image geometry.
    for offset in (3730,3738):
        struct.pack_into('<4H',job,offset,640,480,640,480)
    if gain_fixture is not None:
        if len(gain_fixture)!=4 or any(type(v) is not int or not 0<=v<=65535 for v in gain_fixture):
            raise ValueError('four synthetic unsigned coefficient values required')
        # Caller inputs only. Native stores 607a4499..607a44b6 build +10406;
        # the native request constructor subsequently copies it to R+1568.
        for offset in (3730,3738): struct.pack_into('<4H',job,offset,*gain_fixture)
    if provide_reference_dimensions:
        # Copied natively to request+1576/+1584; the first pair is used as
        # reference dimensions by 6079565b/6079565d, not optional zero padding.
        for offset in (3746,3754):
            struct.pack_into('<4H',job,offset,640,480,640,480)
    width,height = (640,480) if kind == 0x40 else (4608,3456)
    # Buffer layout/format are a synthetic caller fixture, not decoded sensor data.
    input_format=kind if input_format is None else input_format
    if input_format not in (0x40,0x100,0x107,0x108,0x109,0x200):
        raise ValueError('undeclared synthetic input format')
    report['input_format']=hex(input_format)
    descriptors = [(36,SOURCE,input_format),(100,OUTPUT,0x0302)]
    if provide_slot:
        descriptors.append((3984,OUTPUT,0x0302))
    if provide_long_output:
        descriptors.append((4264,OUTPUT,0x0302))
    for offset,address,fmt in descriptors:
        struct.pack_into('<I',job,offset,address)
        # SRC +16/+18 are area dimensions; DST +16/+18 are H/V offsets.
        # Confirmed by native diagnostic printers 6176a567 / 6176a650.
        tail=(width,height) if offset==36 or legacy_output_offsets else (0,0)
        struct.pack_into('<6H',job,offset+8,fmt,width,width,height,*tail)
    stride=width if input_stride is None else input_stride
    if not width<=stride<=4608 or stride%64:
        raise ValueError('input fixture requires a bounded 64-unit aligned stride')
    struct.pack_into('<H',job,46,stride)
    source_bytes=stride*height*2
    source_data=bytearray(source_bytes)
    if source_fixture is not None:
        validate_bayer_source(source_fixture,width,height,input_format)
        stride=source_fixture['stride']
        source_data=source_fixture['data']
        source_bytes=len(source_data)
        struct.pack_into('<H',job,46,stride)
        struct.pack_into('<2H',job,52,source_fixture['width'],source_fixture['height'])
        report['source_fixture']=dict(width=source_fixture['width'],height=source_fixture['height'],
            stride=stride,use_width=width,use_height=height,window_origin=[0,0],
            camera_crop_verified=False,sha256=hashlib.sha256(source_data).hexdigest())
    report['source_allocation_bytes']=source_bytes
    m.memory = Memory([*m.memory.regions,Region(SOURCE,source_data,False,'declared source payload'),
                       Region(OUTPUT,bytearray([0xcd])*(width*height*2),True,'synthetic destination')])
    if start_frame:
        report['start'] = invoke(m,0x6074e348,0xf0,96,{'d0':JOB})
        if report['start'].get('pc') != RETURN or m.r['d0'] != 0:
            report['events'] = m.events
            return report
    report['index_before_executor'] = memory.read(JOB+10388,2)
    # Mode handoff after the complete constructor, before execution.
    if native_module is None:
        job[12:16] = header(11)
        struct.pack_into('<I',job,10384,11)
    if attach_table:
        memory.write(JOB+12320,PARAMETER_OBJECT,4)
        preparation=invoke(m,0x6074e6eb,0xf0,32,{'d0':JOB,'d1':count},[0x6072fd27])
        assert preparation.get('pc') == 0x6072fd27,preparation
        # Run the native object builder on a private copy of this request: it
        # intentionally changes its key to 2 while selecting companion tables.
        request=bytearray(job[10440:10440+1876])
        struct.pack_into('<I',request,1524,0)
        parameter=bytearray([0xa5])*(4184+16)
        builder=CallMachine(code,Memory([Region(BASE,image),
            Region(0x1a000000,request,True),Region(PARAMETER_OBJECT,parameter,True),
            Region(STACK,bytearray(16384),True)]),{'sp':SP},models={0x4700111e:FillModel()})
        construction=invoke(builder,0x6078ab39,0xb0,36,{'a0':0x1a000000,'a1':PARAMETER_OBJECT})
        assert construction.get('pc') == RETURN and builder.r['sp']==SP,construction
        # For these requests all companion pointers refer to ROM. Only the
        # 129-byte header is initialized; enforce that exact readable extent.
        assert parameter[129:] == b'\xa5'*(len(parameter)-129)
        assert all(BASE <= struct.unpack_from('<I',parameter,o)[0] <= BASE+len(image)-512
                   for o in (0,8))
        assert parameter[20:24] == b'\xa5'*4  # Native builder leaves comparison token to its owner.
        table=bytearray(image[0x4ee340:0x4ee340+3028])
        struct.pack_into('<h',table,14,50 if key==0x01010078 else -50)
        struct.pack_into('<2I',parameter,16,RECIPE_TABLE,1 if key==0x01010078 else 2)
        m.memory=Memory([*m.memory.regions,Region(PARAMETER_OBJECT,parameter[:129]),Region(RECIPE_TABLE,table)])
        report['parameter_construction']=dict(result=construction,events=builder.events,
            native_slot_bytes=4184,mapped_header_bytes=129,
            sha256=hashlib.sha256(parameter[:129]).hexdigest(),
            fields={str(o):hex(struct.unpack_from('<I',parameter,o)[0]) for o in (0,4,8,12,16,20)},
            gamma_variant=parameter[28],inline_block_sha256=hashlib.sha256(parameter[29:129]).hexdigest())
        execution=resume(m,0x6072fd27,[0x6079ebcc])
    else:
        execution=invoke(m,0x6074e6eb,0xf0,32,{'d0':JOB,'d1':count})
    if attach_table:
        assert execution.get('pc') == 0x6079ebcc,execution
        context=m.r['a0']
        out=m.memory.read(context+12,4)
        assert out == CACHE and m.memory.read(context+60,4) & 0x10000000
        assert m.memory.read(JOB+10440+1524,4) == PARAMETER_OBJECT
        initial=bytes(cache[:5200])
        color_call=m.events[-1]
        assert color_call == dict(op='call',pc=0x6079fc15,target=0x6079ebcc)
        raw,op,_=code[color_call['pc']]
        assert op == 'call' and raw[-2:] == b'\xf0\x14'
        return_pc=m.memory.read(m.r['sp']+raw[-1],4)
        assert return_pc == color_call['pc']+len(raw)
        trace_start=len(m.trace)
        color=resume(m,0x6079ebcc,[return_pc])
        assert color.get('pc') == return_pc and 0x6079e50e in m.trace[trace_start:]
        packed=bytes(cache[:5200])
        check_packing(packed,table,[struct.unpack_from('<h',table,r*28+14)[0] for r in range(12)],
                      initial=initial,table_address=RECIPE_TABLE)
        report['connected_color'] = dict(result=color,bytes_checked=5200,
            output_sha256=hashlib.sha256(packed).hexdigest(),table_sha256=hashlib.sha256(table).hexdigest(),
            synthetic_marker=struct.unpack_from('<h',table,14)[0],
            lifetime='host-owned readonly object/table retained through the stopped native request')
        execution=resume(m,return_pc)
    report['executor'] = execution
    report['processor_return']=hex(m.processor_return) if hasattr(m,'processor_return') else None
    if m.trace[-1] == 0x60795691:
        pointer=m.memory.read(m.r['sp']+164,4)
        report['dimension_fault']=dict(pointer=hex(pointer),request_offset=pointer-(JOB+10440),
            values=[m.memory.read(pointer+i*2,2) for i in range(2)],events=m.events[-6:])
    # This is a native cursor, NOT a successful-entry counter (see controls).
    report['executor_index'] = memory.read(JOB+10388,2)
    report['events'] = list(m.events)
    report['fixture_buffers'] = owner.buffers
    report['active_owner_slots'] = sorted(owner.active_slots)
    report['descriptor_refs'] = {hex(k):v for k,v in owner.descriptor_refs.items()}
    report['workspace_state'] = m.memory.read(SCRATCH+9592,1)
    report['event_bits_signalled']=signal.signalled
    report['event_bits_allocated']=event_pool.allocated
    report['consumer_id_live']=consumer_id.used
    report['request_words'] = {str(o):hex(m.memory.read(JOB+10440+o,4))
                               for o in (0,4,8,12,16,20,84,212,276,340,404,916,972,1196,1252,1484,1524,1640)}
    report['cache_compare_executed'] = 0x6073e6ac in m.trace and 0x6073e950 in m.trace
    report['processor_entered'] = 0x60734068 in m.trace
    report['native_color_entered'] = 0x6079ebcc in m.trace
    if native_module is not None:
        report['native_film'] = dict(route_gate=native_module['symbols']['film_route_gate'] in m.trace,
            color_entry=native_module['symbols']['film_color_entry'] in m.trace,
            recipe_applied=native_module['symbols']['color_post_hsl'] in m.trace,
            gamma_hook=native_module['symbols']['film_gamma_hook'] in m.trace,
            job_header_unchanged=job[12:16] == header(key),
            cached_key_unchanged=memory.read(JOB+10384,4) == key,
            request_header=job[10448:10452].hex(),
            early_gain_hook=native_module['symbols'].get('film_wb_entry') in m.trace,
            source_gain_record=list(struct.unpack_from('<4H',job,10406)),
            request_gain_record=list(struct.unpack_from('<4H',job,10440+1568)),
            matrix_words=list(struct.unpack_from('<9H',cache,80)),
            request_fields={str(o):memory.read(JOB+10440+o,s) for o,s in ((14,2),(28,2),(48,1),(1832,2))},
            gamma_pointers=[hex(memory.read(CACHE+2596+i*4,4)) for i in range(3)])
    report['pending_record'] = {str(o):hex(m.memory.read(JOB+13640+o,4)) for o in (0,8,12,16)}
    report['pending_record_zero']=not any(job[13640:13640+56])
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
    report['cpu_source_reads']=source_reads
    report['input_configuration']={str(o):hex(m.memory.read(SCRATCH+o,4))
                                  for o in (112,116,120,124,128,132,136,9260,9264,9308)}
    report['input_register_words']=[m.memory.read(SCRATCH+112+4*i,4) for i in range(24)]
    if m.trace[-1]==0x6073eafa:
        context=m.r['a3']
        outputs=[m.memory.read(context+32+4*i,4) for i in range(5)]
        report['output_views']=[dict(request_offset=pointer-(JOB+10440),
            pointer=hex(m.memory.read(pointer,4)),format=hex(m.memory.read(pointer+8,2)),
            fields={name:m.memory.read(pointer+o,2) for name,o in
                    (('memory_width',10),('width',12),('height',14),('offset_h',16),('offset_v',18))})
            for pointer in outputs if pointer]
        report['output_memory_configuration']={str(o):hex(m.memory.read(SCRATCH+9068+o,4))
            for o in range(208,324,4)}
        report['output_address_writes']=output_address_writes
        primary=report['output_views'][0]
        origin=int(primary['pointer'],16)
        extent=primary['fields']['memory_width']*primary['fields']['height']*2
        native_base=m.memory.read(SCRATCH+9068+208,4)
        report['output_base_in_destination']=(origin<=native_base<origin+extent and any(
            r.writable and r.address<=origin and origin+extent<=r.address+len(r.data)
            for r in m.memory.regions))
        report['legacy_output_offsets']=legacy_output_offsets
    if destroy_job:
        if execution.get('pc')!=RETURN or not report['pending_record_zero']:
            raise ValueError('destruction requires returned executor and empty pending record')
        report['destructor']=invoke(m,0x6074e2fd,0xa0,12,{'d0':JOB})
        report['pool_live_after_destructor']=list(pool.live)
        report['owner_slots_after_destructor']=sorted(owner.active_slots)
        report['destructor_events']=m.events[len(report['events']):]
    return report


def buffer_release_experiment(image,code):
    """Native 48-record sweep: owned callback, borrowed record, repeat sweep."""
    job=bytearray(16384); owner=FixtureOwner()
    struct.pack_into('<2I',job,4,OWNER_CALLBACK,OWNER_CONTEXT)
    m=CallMachine(code,Memory([Region(BASE,image),Region(JOB,job,True),
        Region(STACK,bytearray(16384),True),Region(OUTPUT,bytearray([0xcd])*64,True)]),
        {'sp':SP},models={OWNER_CALLBACK:owner,0x4700111e:FillModel()})
    record=JOB+5668
    m.memory.write(record+72,64,4); m.memory.write(record+76,0x1000,4)
    m.r.update(a1=OWNER_CONTEXT,a0=record,d0=19)
    owner.validate(m,0,0); owner.apply(m)
    # The second record borrows caller memory and must never deliver event 20.
    struct.pack_into('<I',job,5668+88+64,OUTPUT)
    job[5668+88+84]=1
    result=invoke(m,0x6074accb,0xa0,12,{'a0':JOB})
    assert result.get('pc')==RETURN and m.r['sp']==SP,result
    assert not any(job[5668:5668+176])
    assert owner.released_buffers=={owner.buffers[0]['address']}
    count=len([e for e in m.events if e.get('event')==20])
    again=invoke(m,0x6074accb,0xa0,12,{'a0':JOB})
    assert again.get('pc')==RETURN
    assert count==1==len([e for e in m.events if e.get('event')==20])
    assert bytes(next(r for r in m.memory.regions if r.address==OUTPUT).data)==b'\xcd'*64
    return dict(result=result,repeat=again,owner_free_callbacks=count,
                borrowed_payload_preserved=True,records_zero=True,events=m.events)


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
            assert not case['cache_compare_executed'] and not case['processor_entered'] and not case['native_color_entered']
        else:
            assert_hardware_boundary(case)
            assert case['cache_compare_executed'] and case['processor_entered']
            assert case['request_words']['1484'] == hex(CACHE) and case['request_words']['8'] == '0xb0000'
            assert case['request_words']['916'] != '0x0'
    connected=[experiment(image,code,k,kind,s,attach_table=True)
               for k in RECIPES for kind in (0x200,0x100) for s in (0,2)]
    for case in connected:
        assert_hardware_boundary(case)
        assert case['connected_color']['bytes_checked'] == 5200
        assert case['parameter_construction']['result']['registers']['d0'] == '0x0'
    for kind in ('0x200','0x100'):
        assert len({c['connected_color']['output_sha256'] for c in connected if c['kind']==kind}) == 2
    slot_cases=[experiment(image,code,k,0x40,s,provide_slot=True) for k in RECIPES for s in (0,2)]
    for case in slot_cases:
        assert case['executor'].get('pc')==RETURN and case['executor']['registers']['sp']==hex(SP)
        assert case['executor']['registers']['d0']=='0x9e40'
        assert case['event_bits_signalled']==case['event_bits_allocated']==0
        assert not case['consumer_id_live'] and case['pending_record_zero']
        assert case['processor_return']=='0x9e40'
        assert case['workspace_state']==0 and case['active_owner_slots']==[0xff07,0xff0b]
        assert not case['output_changed'] and case['allocation_canaries_intact']
        expected=[dict(address=0x1c000000,size=2560,id=0xff0b,payload_changed=False)]
        if case['selector']==2:
            expected.insert(0,dict(address=0x1b000000,size=614400,id=0xff07,payload_changed=False))
        assert case['fixture_buffers']==expected
    short_inputs=[experiment(image,code,k,0x40,s,provide_slot=True,input_format=f)
                  for k in RECIPES for s in (0,2) for f in (0x100,0x200)]
    for case in short_inputs:
        assert_hardware_boundary(case)
        assert case['processor_return'] is None and not case['output_changed']
    destruction=[experiment(image,code,k,0x40,s,provide_slot=True,destroy_job=True)
                 for k in RECIPES for s in (0,2)]
    for case in destruction:
        assert case['destructor'].get('pc')==RETURN and case['destructor']['registers']['sp']==hex(SP)
        assert case['pool_live_after_destructor']==[]
        assert case['owner_slots_after_destructor']==[0xff07,0xff0b]
    packing=[experiment(image,code,k,0x40,s,provide_slot=True,input_format=0x200,input_stride=stride)
             for k in RECIPES for s in (0,2) for stride in (640,704)]
    for index,case in enumerate(packing):
        stride=(640,704)[index%2]; cfg=case['input_configuration']
        assert_hardware_boundary(case)
        assert int(cfg['112'],16)==stride*2
        assert int(cfg['9260'],16)==SOURCE
        assert int(cfg['9264'],16)==stride*480*2==case['source_allocation_bytes']
        assert cfg['120']=='0x76543210' and cfg['128']=='0x1000d00'
    bad_offsets=[experiment(image,code,k,0x40,0,provide_slot=True,input_format=0x100,
                            legacy_output_offsets=True) for k in RECIPES]
    for case in bad_offsets:
        assert case['output_memory_configuration']['208']==hex(OUTPUT+640*480*2)
        assert not case['output_base_in_destination']
    controls = []
    for key in RECIPES:
        for name,options,selector in [('no_frame_start',{'start_frame':False},0),
                ('owner_cancel',{'continue_processing':False},0),
                ('request_rejected',{'accept_request':False},0),
                ('missing_long_output',{'provide_long_output':False},2),
                ('missing_reference_dimensions',{'provide_reference_dimensions':False},0)]:
            kind=0x100 if name == 'missing_reference_dimensions' else 0x200
            case=experiment(image,code,key,kind,selector,**options)
            case['control']=name
            assert not case['output_changed']
            if name == 'missing_reference_dimensions':
                assert case['executor'].get('error') == "0x60795691 div ['d3', 'd2']: division by zero"
                assert case['dimension_fault']['request_offset']==1576 and case['dimension_fault']['values']==[0,0]
                assert case['processor_entered'] and case['native_color_entered']
            elif name == 'no_frame_start':
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
            if name != 'missing_reference_dimensions':
                assert not case['processor_entered']
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
                full_pixel_cycle_passed=False,cases=cases,connected_color_cases=connected,
                owner_slot_cases=slot_cases,
                short_input_cases=short_inputs,
                destruction_cases=destruction,input_stride_cases=packing,
                buffer_release_audit=buffer_release_experiment(image,code),
                invalid_output_offset_controls=bad_offsets,
                controls=controls,cache_audit=cache_experiment(image,code),
                source_sha256=source_hashes,decode_anchors=len({**EXPECTED,**JOB_ANCHORS}),
                new_windows={k:[hex(a),hex(b)] for k,(a,b) in JOB_WINDOWS.items()},
                limitations=['synthetic descriptors and software resource contracts',
                             'no RTOS scheduling, DMA, ISP or camera measurement; error cleanup uses finite host resources',
                             'attached tables use diagnostic saturation markers, not calibrated film recipes',
                             'parameter owner lifetime/comparison-token production not integrated',
                             'short route input 0x200 reaches hardware boundary; pixel packing remains unverified'])
    args.out.mkdir(parents=True)
    (args.out/'results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    def brief(v):
        return {k:hex(x) if k in ('pc','target') else x for k,x in v.items()
                if k in ('status','pc','target','error','instructions')} | {'d0':v['registers']['d0']}
    print(json.dumps([{'key':r['key'],'kind':r['kind'],'selector':r['selector'],
        **{k:brief(r[k]) for k in ('constructor','start','executor') if k in r}} for r in cases]))


def assert_hardware_boundary(case):
    assert case['executor']['status'] == 'fault'
    assert case['executor'].get('error') == "0x6073eafa mov ['d0', '(0x9880014c)']: unmapped access at 0x9880014c, size 4"
    assert case['executor']['registers']['d0'] == '0x800'
    assert case['cache_compare_executed'] and case['processor_entered'] and case['native_color_entered']
    assert not case['output_changed'] and not any(b['payload_changed'] for b in case['fixture_buffers'])
    assert case['allocation_canaries_intact']
    assert case['output_base_in_destination']
    assert all(case['output_memory_configuration'][str(208+4*i)]==view['pointer']
               for i,view in enumerate(case['output_views']))


if __name__=='__main__':
    main()
