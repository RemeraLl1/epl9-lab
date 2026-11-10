"""Execute the standalone finite reader against explicit synthetic MMIO/DMA.

No native kernel lock, allocation, USB, storage or physical DMA is executed.
The context token only declares a fixture precondition; it is not a mutex.
"""
import argparse
import json
import struct
from pathlib import Path

from epl9_workspace_bridge import ROOT, MAIN, MAIN_SHA, BASE, sha
from epl9_bounded_read import build, MODULE_BASE, TEMPLATE
from mn103_subset import Memory, Region, parse_listing
from mn103_calls import CallMachine

CTX, BUFFER, SP, END = 0x18000000, 0xa9000000, 0x19008000, 0x1a000000
MAP = 0xa03fdf80
GUARD = b'\xa5'*16
OUT = ROOT/'local/epl9-bounded-read-20261110'


def require(ok, message):
    if not ok:
        raise ValueError(message)


class Fixture(Memory):
    def __init__(self, module, *, kind=256, page=0, remaps=(), completion_after=1,
                 completion_word=0x9004, sample=0, status=0x40, state=0, exclusive=1,
                 capacity=2048, destination=BUFFER, preexisting=0):
        self.module = module
        self.mmio = []
        self.started = False
        self.completion_after, self.completion_word = completion_after, completion_word
        self.sample, self.status, self.preexisting = sample, status, preexisting
        self.polls = self.status_polls = 0
        self.dma_delivered = False
        self.packet = []
        self.map_reads = 0
        table = bytearray().join(struct.pack('<II', i, i) for i in range(1024))
        for block, target in remaps:
            struct.pack_into('<I', table, block*8, target)
        context = struct.pack('<14I', state, 0, kind, page, destination, capacity, exclusive,
                              0, 0, 0, 0, 0, 0, 0)
        self.context = bytearray(GUARD+context+GUARD)
        self.buffer = bytearray(GUARD+b'\xcd'*2048+GUARD)
        super().__init__([
            Region(CTX-16, self.context, True, 'owned fixture context'),
            Region(BUFFER-16, self.buffer, True, 'owned fixture DMA buffer'),
            Region(MAP, table, False, 'immutable fixture mapping'),
            Region(SP-32768, bytearray(65536), True, 'private stack'),
            Region(MODULE_BASE, module['data'], False, 'separate module'),
            Region(0x9880014c, bytearray(struct.pack('<I', 0x15)), True),
            Region(0x98d01000, bytearray(4096), True)])

    def read(self, address, size):
        if MAP <= address < MAP+8192:
            self.map_reads += 1
        if address == 0x98d01104:
            if not self.started:
                return self.preexisting
            self.polls += 1
            if self.completion_after is not None and self.polls >= self.completion_after:
                if not self.dma_delivered:
                    # Synthetic data appears only after modeled completion.
                    self.buffer[16:-16] = bytes((self.physical_page+i) % 251 for i in range(2048))
                    self.dma_delivered = True
                return self.completion_word
            return 0
        if address == 0x98d01194:
            return self.sample
        if address == 0x98d01804 and size == 1:
            self.status_polls += 1
            return self.status
        return super().read(address, size)

    def write(self, address, value, size):
        if 0x98000000 <= address < 0x99000000:
            require(address in (0x9880014c, 0x98d011c0, 0x98d01800,
                                0x98d01804, 0x98d01104), 'unexpected MMIO destination')
            self.mmio.append((address, value & 0xffffffff, size))
            if address == 0x98d01800 and value < 0x0c000000:
                require(0x08000000 <= value < 0x08010000, 'unexpected physical page')
                self.physical_page = value-0x08000000
            if address == 0x98d01804:
                if not self.started:
                    self.packet.append(value)
                    if len(self.packet) == 3:
                        require(self.packet == [0x01402001, BUFFER & 0x7fffffff, 0],
                                'request is not the exact single-page read packet')
                        self.started = True
                else:
                    require(value == 0x70, 'only status reads permitted after submit')
        super().write(address, value, size)

    def machine(self):
        return CallMachine(self.module['code'], self, dict(sp=SP, a0=CTX))

    def run(self):
        m = self.machine()
        r = m.run(m.enter(MODULE_BASE, END, 0xf0, 64), [END], limit=50000)
        require(r.get('pc') == END and m.r['sp'] == SP, 'unbalanced or nonterminating reader')
        require(self.context[:16] == self.context[-16:] == self.buffer[:16] == self.buffer[-16:] == GUARD,
                'fixture guard overwritten')
        require(all(e.get('target') == self.module['symbols']['map_page']
                    for e in m.events if e['op'] == 'call'), 'external native call')
        require(self.polls <= 256 and self.status_polls <= 64 and self.map_reads <= 1024,
                'bounded loop budget exceeded')
        row = dict(result=m.r['d0'], state=self.read(CTX, 4), valid_bytes=self.read(CTX+28, 4),
                   completion_polls=self.polls, status_polls=self.status_polls,
                   map_reads=self.map_reads, submitted=self.started, instructions=len(m.trace),
                   mmio_writes=len(self.mmio), dma_bytes_modeled=self.dma_delivered,
                   physical_dma_executed=False)
        return row


def run(out, directory=OUT):
    require(not out.exists() and out.resolve().is_relative_to((ROOT/'local').resolve()),
            'new ignored report path required')
    image = MAIN.read_bytes()
    require(sha(image) == MAIN_SHA, 'stock main changed')
    module = build()
    require(module['data'] == (directory/'reader-OFFLINE-ONLY.bin').read_bytes(), 'module differs')
    listing = directory/'reader.tsv'
    module['code'] = parse_listing(listing.read_text(encoding='utf-8-sig'), module['data'], MODULE_BASE)
    require(len(module['rows']) == len(module['code']), 'GNU instruction count differs')
    rows = []
    for kind, base in ((256, 3520), (257, 17344)):
        for page in (0, 63, 64, 12799):
            block = (base+page)//64
            for chain in (0, 1, 3):
                remaps = [(block, 900)] if chain else []
                if chain == 3:
                    remaps += [(900, 901), (901, 902)]
                f = Fixture(module, kind=kind, page=page, remaps=remaps)
                row = f.run()
                physical = ((base+page)//64 if not chain else (900 if chain == 1 else 902))*64+(page % 64)
                require(row['result'] == 0 and row['state'] == 2 and row['valid_bytes'] == 2048
                        and f.physical_page == physical, 'mapped component page differs')
                require(f.buffer[16:-16] == bytes((physical+i) % 251 for i in range(2048)), 'DMA fixture bytes differ')
                require(f.read(0x9880014c, 4) == 0x15 and f.read(0x98d011c0, 4) == 0,
                        'completed controller setup not restored')
                rows.append(dict(case='component-page', kind=kind, page=page, chain=chain, **row))

    cases = [
        ('invalid-kind', dict(kind=258), 1, 4),
        ('past-component', dict(page=12800), 1, 4),
        ('negative-page', dict(page=0xffffffff), 1, 4),
        ('not-exclusive', dict(exclusive=0), 1, 4),
        ('undersized-buffer', dict(capacity=2047), 1, 4),
        ('unaligned-buffer', dict(destination=BUFFER+1), 1, 4),
        ('bad-buffer-domain', dict(destination=0x19000000), 1, 4),
        ('active-context', dict(state=1), 3, 1),
        ('quarantined-context', dict(state=3), 3, 3),
        ('stale-completion', dict(preexisting=0x9004), 3, 0),
        ('mapping-cycle', dict(remaps=[(55, 56), (56, 55)]), 2, 4),
        ('mapping-outside', dict(remaps=[(55, 1024)]), 2, 4),
        ('mapping-sentinel', dict(remaps=[(55, 0xffffffff)]), 2, 4),
        ('dma-timeout', dict(completion_after=None), 5, 3),
        ('extra-completion', dict(completion_word=0x9005), 9, 3),
        ('maintenance-threshold-14', dict(sample=14), 6, 4),
        ('maintenance-threshold-15', dict(sample=15), 6, 4),
        ('status-timeout', dict(status=0), 7, 3),
        ('status-low-bits', dict(status=0x41), 8, 4),
    ]
    for name, kwargs, result, state in cases:
        f = Fixture(module, **kwargs)
        row = f.run()
        require((row['result'], row['state'], row['valid_bytes']) == (result, state, 0),
                'error state differs: '+name)
        if name in ('dma-timeout', 'extra-completion', 'status-timeout'):
            before = bytes(f.context)
            writes = len(f.mmio)
            again = f.run()
            require(again['result'] == 3 and bytes(f.context) == before and len(f.mmio) == writes,
                    'quarantined buffer was reused')
            row['quarantined_reentry_rejected'] = True
        rows.append(dict(case=name, **row))

    # Resume after a native in-flight marker, with a second caller in between.
    f = Fixture(module)
    m = f.machine()
    stop = module['symbols']['completion_poll']
    r = m.run(m.enter(MODULE_BASE, END, 0xf0, 64), [stop])
    require(r.get('pc') == stop and f.read(CTX, 4) == 1, 'inflight stop differs')
    second = CallMachine(module['code'], f, dict(sp=SP+8192, a0=CTX))
    r = second.run(second.enter(MODULE_BASE, END, 0xf0, 64), [END])
    require(r.get('pc') == END and second.r['d0'] == 3 and not f.polls, 'nested use accepted')
    r = m.run(stop, [END])
    require(r.get('pc') == END and m.r['d0'] == 0, 'original request changed')
    rows.append(dict(case='inflight-nested-caller', rejected=True, original_completed=True,
                     atomic_entry_lock_proven=False))

    report = dict(model='E-PL9 / IM008 / 1330', displayed_version='1.1 (owner report)', build='1101',
                  stock_main_bytes=len(image), stock_main_sha256=sha(image),
                  module_bytes=len(module['data']), module_sha256=sha(module['data']),
                  synthetic_base=hex(MODULE_BASE), cases=rows,
                  listing_sha256=sha(listing.read_bytes()),
                  source_sha256={str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in
                      (Path(__file__), TEMPLATE, ROOT/'scripts/epl9_bounded_read.py',
                       ROOT/'scripts/epl9_sd_loader.py', ROOT/'scripts/mn103_emit.py',
                       ROOT/'scripts/mn103_subset.py', ROOT/'scripts/mn103_calls.py')},
                  nand_program_erase_maintenance_calls=0, read_retries=0,
                  immutable_mapping_and_exclusive_controller_are_fixture_preconditions=True,
                  polls_are_counts_not_calibrated_time=True, runtime_heap_ownership_proven=False,
                  timeout_quarantines_buffer=True, hardware_abort_qualified=False,
                  hardware_error_semantics_qualified=False, camera_cannot_hang_proven=False,
                  camera_accessed=False, firmware_patched=False, transport_qualified=False)
    out.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows), module_bytes=len(module['data']),
                          bounded_polls=True, physical_dma_executed=False)))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--directory', type=Path, default=OUT)
    a = ap.parse_args()
    run(a.out, a.directory)
