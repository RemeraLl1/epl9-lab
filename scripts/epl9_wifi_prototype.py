"""Offline E-PL9 rd execution and persistent ISC resource experiment.

Never opens a network connection or writes firmware. Native code is byte-checked
against build 1101. SD, RTOS, ISC and TCP services are explicitly host models.
The persistent context is a Python design prototype, NOT assembled camera code.
"""
import argparse
from collections import Counter
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import struct

from epl9_wifi_firmware import BASE, COMPONENTS, ROOT, STOCK_SHA
from mn103_subset import Fault, Machine, Memory, Region, parse_listing
from mn103_calls import CallMachine

BLOCK = 16384
STOP = 0x12345678
FD, SCRATCH, TEMP, OUTPUT, STACK = 0xa1000000, 0xa1010000, 0xa1020000, 0xa1030040, 0xa1050000
REQUEST, ENVELOPE, REPLY = 0xa1070000, 0xa1080000, 0xa1090000
CONTROL, VOLUME = 0xa10a0000, 0xa10b0000
GUARD = bytes([0xa5]) * 64


def digest(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise Fault(message)


def span(memory, address, size, write=False):
    """Bounded bulk access, including unaligned byte strings (not CPU scalars)."""
    require(isinstance(size, int) and size >= 0, 'invalid span length')
    for region in memory.regions:
        if region.address <= address and address + size <= region.address + len(region.data):
            require(not write or region.writable, 'bulk write to ROM')
            return memoryview(region.data)[address-region.address:address-region.address+size]
    raise Fault(f'unmapped bulk span {address:#x}+{size}')


class Model:
    def __init__(self, name, mask, frame, function):
        self.name, self.mask, self.frame, self.function = name, mask, frame, function

    def validate(self, machine, mask, frame):
        require((mask, frame) == (self.mask, self.frame), f'{self.name}: wrong CALL ABI')

    def apply(self, machine):
        return self.function(machine) or {}


class Evidence:
    """Exact image gate plus verified, predecoded GNU instruction windows."""
    def __init__(self, listings):
        self.listings = Path(listings)
        stock_path = ROOT/'firmware/OLY_E_133_1101_0000_0000.BIN'
        stock = stock_path.read_bytes()
        require(len(stock) == 104552480 and digest(stock) == STOCK_SHA, 'wrong stock container')
        name = '00_0100_406e0020.decoded.bin'
        image = (ROOT/'local/epl9-1101-analysis/decoded'/name).read_bytes()
        require((len(image), digest(image)) == COMPONENTS[name], 'wrong main component')
        self.image = image
        self.rom = Region(BASE, bytearray(image), False, 'exact stock main ROM')
        self.hashes = {}
        self.read_code = self.load('main_file_read_backend.tsv')
        lower = self.load('main_file_sector_read.tsv')
        self.read_code.update({pc: row for pc, row in lower.items() if pc < 0x609dd7c2})
        self.mode_code = self.load('main_file_open_core.tsv')
        http = self.load('main_http_all.tsv')
        self.isc_code = {pc: row for pc, row in http.items() if 0x60f31364 <= pc < 0x60f3140f}
        require(http[0x60f30beb][0] == bytes.fromhex('fcdd4c5c2661'), 'HTTP mode load changed')
        require(image[0x61265c4c-BASE:0x61265c4c-BASE+2] == b'r\0', 'wrong r literal')
        require(image[0x60a8ba0c-BASE:0x60a8ba0c-BASE+3] == b'rd\0', 'wrong rd literal')
        require(struct.unpack_from('<II', image, 0x60a8c2c4-BASE) == (58, 0x609dcea1), 'd dispatch changed')

    def load(self, name):
        data = (self.listings/name).read_bytes()
        self.hashes[name] = digest(data)
        return parse_listing(data.decode('utf-8-sig'), self.image, BASE)

    def mode_flags(self, mode):
        require(mode in ('r', 'rd'), 'prototype permits only r and rd')
        memory = Memory([self.rom, Region(STACK, bytearray(65536), True, 'mode stack'),
                         Region(FD, bytearray(mode.encode()+b'\0'), False, 'mode fixture')])
        machine = Machine(self.mode_code, memory, {'a0': FD, 'a2': 0, 'sp': STACK+32768})
        result = machine.run(0x609dce39, stops=(0x609dcec5,))
        require(result['status'] == 'stop', 'mode parser failed')
        require(machine.r['a2'] == (1 if mode == 'r' else 17), 'unexpected mode flags')
        return machine.r['a2'], len(machine.trace)


class NativeReader:
    """Actual fread/backend instructions with a finite, local sector service."""
    def __init__(self, evidence, data, mode='r', sector_faults=None, fail_alloc=False):
        self.evidence, self.data, self.mode = evidence, bytes(data), mode
        self.flags, self.mode_instructions = evidence.mode_flags(mode)
        self.counts = Counter()
        self.sector_faults = dict(sector_faults or {})  # call index -> (status, sector count)
        self.fail_alloc, self.allocated = fail_alloc, set()
        self.memory = Memory([evidence.rom,
            Region(FD, bytearray(512), True, 'file descriptor fixture'),
            Region(SCRATCH, bytearray([0xcd])*512, True, 'per-file sector scratch'),
            Region(TEMP, bytearray([0xcd])*BLOCK, True, '16 KiB physical temporary'),
            Region(CONTROL, bytearray([0xcd])*BLOCK, True, 'physical slot for 128-byte sector request'),
            Region(VOLUME, bytearray(struct.pack('<I', 64)), False, 'synthetic volume geometry'),
            Region(OUTPUT-64, bytearray(GUARD+bytes([0xcd])*BLOCK+GUARD), True, 'HTTP output with guards'),
            Region(STACK, bytearray(65536), True, 'private stack')])
        for offset, value in [(268, len(data)), (288, 1), (308, 0), (312, self.flags),
                              (480, SCRATCH), (484, 0), (488, 0xffffffff)]:
            self.memory.write(FD+offset, value, 4)
        models = {
            0x609dc484: Model('declared file validation', 0x30, 12, self.validate_fd),
            0x6040240f: Model('finite physical temporary allocation', 0, 4, self.allocate),
            0x6040244e: Model('physical temporary release', 0, 4, self.release),
            0x609b9b40: Model('local storage request service; no SD/DMA', 0xf0, 56, self.sectors),
            0x609b9ef8: Model('declared volume geometry lookup', 0xc0, 12, self.volume),
            0x609d4f0b: Model('sector status diagnostic front', 0xa0, 36, self.status),
            0x47001012: Model('bounded memcpy', 0xf0, 28, self.copy),
        }
        self.machine = CallMachine(evidence.read_code, self.memory, models=models)

    def validate_fd(self, machine):
        require(machine.r['a0'] == FD and machine.r['d0'] == 1, 'wrong file validation arguments')
        machine.r['d0'] = 1

    def allocate(self, machine):
        size = machine.r['d0']
        require(size in (128, BLOCK), 'unexpected physical allocation size')
        address = CONTROL if size == 128 else TEMP
        require(address not in self.allocated, 'repeated physical allocation')
        self.counts['control_allocations' if size == 128 else 'bounce_allocations'] += 1
        if self.fail_alloc:
            machine.r['a0'] = 0
        else:
            self.allocated.add(address)
            machine.r['a0'] = address

    def release(self, machine):
        address = machine.r['a0']
        require(address in self.allocated, 'release without live physical slot')
        self.allocated.remove(address)
        self.counts['control_frees' if address == CONTROL else 'bounce_frees'] += 1

    def volume(self, machine):
        require(machine.r['d0'] == 0, 'unexpected synthetic volume ID')
        machine.r['a0'] = VOLUME

    def status(self, machine):
        require(machine.r['a0'] == 0x60a8c0e4 and machine.r['d1'] == 2640, 'unexpected diagnostic caller')
        # Explicit status-preserving diagnostic assumption; not an RTOS model.

    def sectors(self, machine):
        r, memory = machine.r, machine.memory
        require(r['a0'] == CONTROL and CONTROL in self.allocated, 'unowned storage request')
        require(memory.read(CONTROL+4, 2) == 0x3003, 'only ordinary sector reads permitted')
        require(memory.read(CONTROL+8, 4) == 1, 'unknown synthetic storage descriptor')
        requested = memory.read(CONTROL+16, 4)
        require(0 < requested <= 32, 'sector count outside 16 KiB prototype')
        index = self.counts['sector_calls']
        self.counts['sector_calls'] += 1
        status, count = self.sector_faults.get(index, (0, requested))
        require(0 <= count <= requested, 'bad injected sector count')
        start = memory.read(CONTROL+12, 4)*512
        require(start < len(self.data) or not count, 'sector request beyond local EOF')
        destination = memory.read(CONTROL+20, 4)
        # Real storage can return the whole last sector; bytes past logical EOF
        # are arbitrary. Deliberately poison them, never invent useful bytes.
        payload = self.data[start:start+count*512].ljust(count*512, b'\xe7')
        if destination == TEMP:
            require(TEMP in self.allocated, 'sector read to unowned physical temporary')
            self.counts['temporary_sector_bytes'] += len(payload)
        elif OUTPUT <= destination < OUTPUT+BLOCK:
            self.counts['direct_sector_bytes'] += len(payload)
        elif destination == SCRATCH:
            require(count <= 1, 'scratch overflow')
            self.counts['scratch_sector_bytes'] += len(payload)
        else:
            raise Fault('unrecognized sector destination')
        span(memory, destination, len(payload), True)[:] = payload
        memory.write(CONTROL+52, count, 4)
        memory.write(CONTROL+60, 0, 4)  # No synthetic cached physical cluster.
        r['d0'] = status
        return dict(sector=start//512, requested=requested, returned=count, status=status,
                    destination=hex(destination))

    def copy(self, machine):
        r = machine.r
        payload = bytes(span(self.memory, r['a1'], r['d0']))
        span(self.memory, r['a0'], len(payload), True)[:] = payload
        self.counts['memcpy_calls'] += 1
        self.counts['memcpy_bytes'] += len(payload)

    @property
    def position(self):
        return self.memory.read(FD+308, 4)

    def read(self, count, position=None):
        require(0 <= count <= BLOCK, 'HTTP prototype keeps the physical 16 KiB limit')
        if position is not None:
            require(0 <= position <= len(self.data), 'invalid file position')
            self.memory.write(FD+308, position, 4)
        span(self.memory, OUTPUT, BLOCK, True)[:] = bytes([0xcd])*BLOCK
        machine = self.machine
        machine.r.update(a0=OUTPUT, a1=FD, d0=1, d1=count, sp=STACK+32768)
        machine.trace.clear()
        machine.events.clear()
        machine.loop = None
        start = machine.enter(0x609ddff6, STOP, 0xf0, 20)
        result = machine.run(start, stops=(STOP,), limit=20000)
        require(result['status'] == 'stop' and machine.r['sp'] == STACK+32768, f'native read stopped: {result}')
        size = machine.r['d0']
        require(size <= count, 'read exceeded requested byte count')
        require(bytes(span(self.memory, OUTPUT-64, 64)) == GUARD and
                bytes(span(self.memory, OUTPUT+BLOCK, 64)) == GUARD, 'output guard changed')
        require(bytes(span(self.memory, OUTPUT+size, BLOCK-size)) == bytes([0xcd])*(BLOCK-size),
                'native write past reported output length')
        require(not self.allocated, 'temporary remained allocated')
        self.counts['native_instructions'] += len(machine.trace)
        self.counts['read_calls'] += 1
        return bytes(span(self.memory, OUTPUT, size))


def wire_request(queue_id, request_address, socket, source, length, flags=0):
    """64-byte channel-3 send request, after the stock local pump fills +4/+8.

    Stock stack tail is unspecified. The host prototype clears all unused words.
    No generation token is added to the camera protocol.
    """
    require(0 < length <= BLOCK, 'send size outside fixed block')
    require(0xa0000000 <= source < 0xc0000000 and source+length <= 0xc0000000,
            'source is not a bounded AM shared alias')
    words = [6, queue_id, request_address, 0, socket, source & 0x5fffffff, length, flags, 0]+[0]*7
    return struct.pack('<16I', *words)


class NativeIsc:
    """Runs stock helper 60f31364; models only its declared service boundaries."""
    def __init__(self, evidence):
        self.counts = Counter()
        self.live = set()
        self.queue = False
        self.wire = None
        self.memory = Memory([evidence.rom, Region(STACK, bytearray(65536), True, 'ISC stack'),
            Region(REQUEST, bytearray(64), True, 'BSD request'),
            Region(ENVELOPE, bytearray(128), True, 'shared pool slot for envelope'),
            Region(REPLY, bytearray(128), True, 'shared pool slot for completion')])
        models = {
            0x60f31258: Model('reply queue create front', 0xc0, 28, self.create),
            0x60f312fa: Model('128-byte-slot allocation front', 0xe0, 16, self.allocate),
            0x604117be: Model('declared task identity', 0x20, 4, self.task),
            0x604335ef: Model('uncontended synchronization front', 0x80, 8, self.synchronize),
            0x604314e5: Model('publish envelope plus modeled ISC pump', 0xf0, 28, self.publish),
            0x604313e9: Model('completion wait plus modeled reply pump', 0xf0, 24, self.wait),
            0x60f31330: Model('shared slot release front', 0xb0, 16, self.free),
            0x60f312a5: Model('reply queue delete front', 0xf0, 20, self.delete),
        }
        self.machine = CallMachine(evidence.isc_code, self.memory, models=models)

    def create(self, m):
        require(not self.queue and (m.r['d0'], m.r['d1'], m.r['a0']) == (16, 1, 0), 'bad queue create')
        self.queue = True
        self.counts['queue_creates'] += 1
        m.r['d0'] = 7

    def allocate(self, m):
        size = m.r['d0']
        address = {16: ENVELOPE, 12: REPLY}.get(size)
        require(address is not None and address not in self.live, 'bad shared allocation')
        self.live.add(address)
        self.counts['slot_allocations'] += 1
        m.r['a0'] = address

    def task(self, m):
        require(m.r['a0'] == ENVELOPE+4, 'bad task information pointer')
        self.memory.write(m.r['a0'], 3, 4)

    def synchronize(self, m):
        require(m.r['a0'] == 0x61266064, 'wrong synchronization object')
        self.counts['synchronization_calls'] += 1

    def publish(self, m):
        require(self.queue and self.live == {ENVELOPE, REPLY}, 'publication without resources')
        require((m.r['d0'], m.r['d1']) == (99, 0xffffffff), 'wrong global queue/wait')
        descriptor = m.r['a0']
        require((self.memory.read(descriptor, 4), self.memory.read(descriptor+4, 4)) == (ENVELOPE, 16), 'bad envelope descriptor')
        require(struct.unpack('<4I', span(self.memory, ENVELOPE, 16)) == (7, 3, 0, REQUEST), 'bad native envelope')
        # These two writes belong to the stock request pump, explicitly modeled.
        self.memory.write(REQUEST+4, 7, 4)
        self.memory.write(REQUEST+8, REQUEST, 4)
        self.wire = bytes(span(self.memory, REQUEST, 64))
        self.counts['publishes'] += 1
        m.r['d0'] = 0

    def wait(self, m):
        require((m.r['d0'], m.r['d1']) == (7, 0xffffffff) and self.wire is not None, 'bad completion wait')
        require(self.memory.read(m.r['a0'], 4) == REPLY, 'wrong completion buffer')
        self.memory.write(REQUEST+32, self.memory.read(REQUEST+24, 4), 4)
        self.memory.write(REPLY, 0, 2)
        self.counts['completion_waits'] += 1
        m.r['d0'] = 0

    def free(self, m):
        require(m.r['a0'] in self.live, 'double/foreign slot release')
        self.live.remove(m.r['a0'])
        self.counts['slot_frees'] += 1

    def delete(self, m):
        require(self.queue and not self.live and m.r['d0'] == 7, 'bad queue deletion')
        self.queue = False
        self.counts['queue_deletes'] += 1

    def send(self, length):
        # Synthetic caller supplies the BSD frame. The helper itself is native.
        frame = wire_request(0, REQUEST, 9, OUTPUT, length)
        span(self.memory, REQUEST, 64, True)[:] = frame
        self.memory.write(REQUEST+8, 0, 4)
        m = self.machine
        m.r.update(d0=99, d1=0, a0=REQUEST, sp=STACK+32768)
        m.trace.clear()
        m.events.clear()
        result = m.run(m.enter(0x60f31364, STOP, 0xf0, 48), stops=(STOP,))
        require(result['status'] == 'stop' and m.r['d0'] == 0 and not self.live and not self.queue,
                'stock helper did not complete/clean up')
        require(m.r['sp'] == STACK+32768, 'ISC stack imbalance')
        expected = wire_request(7, REQUEST, 9, OUTPUT, length)
        require(self.wire == expected, 'native helper wire format differs')
        self.counts['native_instructions'] += len(m.trace)
        return self.wire


class Resources:
    """Finite modeled RTOS resources, with deterministic construction failures."""
    def __init__(self, fail_step=None, queues=4, slots=8):
        self.counts = Counter()
        self.live = {}
        self.next_id = 1
        self.fail_step, self.queues, self.slots = fail_step, queues, slots
        self.attempts = 0

    def acquire(self, kind):
        self.attempts += 1
        if self.attempts == self.fail_step:
            raise Fault('injected resource construction failure')
        limit = self.queues if kind == 'queue' else self.slots
        require(sum(k == kind for k in self.live.values()) < limit, 'finite resource capacity exhausted')
        token = self.next_id
        self.next_id += 1
        require(token < 32768, 'reply queue identifier outside positive signed 16-bit fixture')
        self.live[token] = kind
        self.counts[kind+'_creates'] += 1
        return token

    def release(self, token):
        require(token in self.live, 'double/foreign resource release')
        kind = self.live.pop(token)
        self.counts[kind+'_deletes'] += 1


@dataclass(frozen=True)
class Ticket:
    owner: int
    sequence: int  # Host-only test identity; NOT a new ISC wire field.
    queue: int
    request: int


class IscContext:
    """One worker, one outstanding request, persistent queue/envelope/reply slots.

    All methods are serialized by the caller. No RTOS locks or firmware hooks
    are implemented here. Generation identity cannot fix an ambiguous wire
    timeout: uncertain publication quarantines the context until drained.
    """
    def __init__(self, resources, owner):
        require(0 <= owner < 4, 'only four worker fixtures supported')
        self.resources, self.owner = resources, owner
        self.tokens = []
        try:
            for kind in ('queue', 'slot', 'slot'):
                self.tokens.append(resources.acquire(kind))
        except Fault:
            for token in reversed(self.tokens):
                resources.release(token)
            raise
        self.queue = self.tokens[0]
        self.request = REQUEST + owner*0x100
        self.state, self.sequence = 'idle', 0
        self.ticket = self.source = self.wire = None
        self.counts = Counter()
        self.output = bytearray()

    def begin(self, owner, source, offset=0, length=None):
        require(owner == self.owner and self.state == 'idle', 'foreign worker or context not idle')
        require(isinstance(source, bytearray) and len(source) <= BLOCK,
                'fixture requires one owned mutable 16 KiB source buffer')
        length = len(source)-offset if length is None else length
        require(0 <= offset and 0 < length <= BLOCK and offset+length <= len(source), 'bad source span')
        self.sequence += 1
        self.ticket = Ticket(owner, self.sequence, self.queue, self.request)
        self.source, self.offset, self.length = source, offset, length
        self.fingerprint = digest(source)
        self.wire = wire_request(self.queue, self.request, 9, OUTPUT+offset, length)
        self.state = 'pending'
        self.counts['publishes'] += 1
        self.counts['completion_waits'] += 1
        return self.ticket

    def publication_rejected(self, ticket):
        """Only a proven pre-publication rejection permits immediate release."""
        require(self.state == 'pending' and ticket == self.ticket, 'bad rejection ticket')
        self._release_source()

    def ambiguous_timeout(self):
        require(self.state == 'pending', 'timeout without pending request')
        self.state = 'quarantined'

    def complete(self, ticket, returned, status=0):
        # Ticket authenticity is a host-test invariant. The stock ISC frame has
        # no generation tag: a raw late duplicate after reuse is NOT distinguishable
        # by this code. Exactly-once ordered delivery still needs qualification.
        require(self.state in ('pending', 'quarantined') and ticket == self.ticket, 'stale/foreign/double completion')
        require(digest(self.source) == self.fingerprint, 'source changed before completion')
        require(0 <= returned <= self.length and (status == 0 or returned == 0), 'invalid completion result')
        self.output.extend(self.source[self.offset:self.offset+returned])
        self.counts['completed_bytes'] += returned
        self.counts['completions'] += 1
        self._release_source()
        return returned

    def _release_source(self):
        self.state = 'idle'
        self.source = self.ticket = self.wire = None

    def close(self):
        require(self.state == 'idle', 'cannot tear down busy/quarantined/closed context')
        for token in reversed(self.tokens):
            self.resources.release(token)
        self.state = 'closed'


def transfer(evidence, data, mode, persistent):
    reader = NativeReader(evidence, data, mode)
    resources = Resources()
    context = IscContext(resources, 0) if persistent else None
    output_hash = hashlib.sha256()
    isc_counts = Counter()
    while reader.position < len(data):
        before = reader.position
        payload = reader.read(min(BLOCK, len(data)-before))
        require(payload == data[before:before+len(payload)] and payload, 'native read output mismatch/no progress')
        if context is None:
            current = IscContext(resources, 0)
        else:
            current = context
        buffer = bytearray(payload)
        ticket = current.begin(0, buffer)
        # Explicit local fake backend, no TCP/ISC execution or elapsed-time claim.
        current.complete(ticket, len(buffer))
        output_hash.update(current.output)
        current.output.clear()
        if not persistent:
            isc_counts.update(current.counts)
            current.close()
    if context is not None:
        isc_counts.update(context.counts)
        context.close()
    require(output_hash.hexdigest() == digest(data) and not resources.live, 'end-to-end identity/resource failure')
    return dict(mode=mode, persistent_isc=persistent, bytes=len(data), sha256=output_hash.hexdigest(),
                reader=dict(reader.counts), isc=dict(isc_counts), resources=dict(resources.counts),
                output_equal=True, balanced_resources=True)


def source_hashes():
    names = ['epl9_wifi_prototype.py', 'epl9_wifi_firmware.py', 'mn103_subset.py', 'mn103_calls.py']
    return {name: digest((ROOT/'scripts'/name).read_bytes()) for name in names}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--listings', type=Path, default=ROOT/'local/wifi-limits-20261102-v6')
    parser.add_argument('--media', type=Path, default=ROOT/'local/wifi-live-20261102-session1/baseline')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    require(out.is_relative_to((ROOT/'local').resolve()) and not out.exists(), 'use a new ignored local output directory')
    hashes = source_hashes()
    evidence = Evidence(args.listings)
    # Run native stock helper twice to prove balanced resource reacquisition.
    native = NativeIsc(evidence)
    frames = [native.send(n).hex() for n in (BLOCK, 7)]
    inputs = [('ORF', 'serial-0-PB020001.ORF', 14692005,
               '1deed5a996e6b3d0d724425ef76b8703a37b8130a3a4cb2c9344c6b691a79946'),
              ('MOV', 'serial-0-PB020002.MOV', 8105416,
               '2adb950f5ae41bf92fa01f921fb8ca06056ee8094e389e83dc266e3ad4877ad0')]
    cases = []
    for kind, name, size, expected in inputs:
        data = (args.media/name).read_bytes()
        require(len(data) == size and digest(data) == expected, 'local media identity mismatch')
        for mode, persistent in [('r', False), ('rd', False), ('rd', True)]:
            cases.append(dict(file=kind, **transfer(evidence, data, mode, persistent)))
    require(hashes == source_hashes(), 'shared interpreter/source changed during run; retry in stable state')
    report = dict(model='Olympus PEN E-PL9', displayed_version_owner_report='1.1', main_internal_build=1101,
        installed_image_dumped=False, stock_bytes=104552480, stock_sha256=STOCK_SHA,
        main_bytes=len(evidence.image), main_sha256=digest(evidence.image), main_base=hex(BASE),
        sources=hashes, listings=evidence.hashes, mode_flags={m: evidence.mode_flags(m)[0] for m in ('r', 'rd')},
        native_stock_isc=dict(native.counts), native_stock_isc_wire_fixtures=frames, cases=cases,
        media_provenance='Previously downloaded stock-camera copies; not independent card-reader originals',
        software_models=['file validation', 'finite storage request service', 'synthetic volume geometry',
                         'physical pool slots', 'status diagnostic', 'memcpy',
                         'RTOS queue/allocation fronts', 'ISC pumps', 'completion/backend byte consumption'],
        persistent_context_is_host_model=True, camera_speedup_measured=False, camera_accessed=False,
        wire_generation_tag=False, late_duplicate_wire_disambiguation_implemented=False,
        firmware_modified=False, installable_patch_created=False, art_modified=False)
    out.mkdir(parents=True)
    (out/'results.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(out=str(out), cases=cases, native_stock_isc=dict(native.counts)), indent=2))


if __name__ == '__main__':
    main()
