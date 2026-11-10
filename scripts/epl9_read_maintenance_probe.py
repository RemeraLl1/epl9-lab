"""Native read mapping/maintenance tests against synthetic NAND registers.

All controller completion/status, storage operations and flash data are models
or stop boundaries. This script cannot access a camera or produce a dump.
"""
import argparse
import json
import struct
from pathlib import Path

from epl9_workspace_bridge import ROOT, MAIN, MAIN_SHA, BASE, sha
from epl9_component_readback import ADDRESSES, SIZE
from epl9_recovery_audit import Boundary
from mn103_subset import Memory, Region, parse_listing
from mn103_calls import CallMachine

SP, END, DEST = 0x18008000, 0x1a000000, 0xa9000000
MAP, SAMPLE = 0xa03fdf80, 0x98d01194
LISTINGS = ROOT/'local/epl9-v3-diagnostic-init-20261107'
READERS = {
    'logical-page': (0x604009bf, 44, 2048, 0x60400ac8, 0x604009e6, 0x60400a97),
    'logical-bulk': (0x60400d2f, 44, 131072, 0x60400e3f, 0x60400d56, 0x60400e07),
    'direct-page': (0x60400c60, 28, 2048, None, 0x60400c80, 0x60400d03),
}


def checked(condition, message):
    if not condition:
        raise ValueError(message)


class MemoryTrace(Memory):
    def __init__(self, regions):
        super().__init__(regions)
        self.mmio_reads, self.mmio_writes = [], []

    def read(self, address, size):
        value = super().read(address, size)
        if 0x98000000 <= address < 0x99000000:
            self.mmio_reads.append((address, value, size))
        return value

    def write(self, address, value, size):
        super().write(address, value, size)
        if 0x98000000 <= address < 0x99000000:
            self.mmio_writes.append((address, value & 0xffffffff, size))


class Return(Boundary):
    def apply(self, m):
        m.r['d0'] = self.backend_result
        return dict(injected_result=self.backend_result, controller_executed=False)


class Request(Boundary):
    def apply(self, m):
        row = dict(d0=hex(m.r['d0']), d1=hex(m.r['d1']), a0=hex(m.r['a0']),
                   storage_executed=False, bytes_obtained=False)
        m.r['d0'] = 0
        return row


def run(out, directory=LISTINGS):
    checked(not out.exists() and out.resolve().is_relative_to((ROOT/'local').resolve()),
            'new ignored output required')
    image = MAIN.read_bytes()
    checked(sha(image) == MAIN_SHA, 'stock identity differs')
    paths = [directory/(n+'.tsv') for n in ('read-page', 'page-bulk', 'page-direct',
             'read-map', 'read-translate', 'read-translate-tail', 'read-maintenance')]
    code = {}
    for p in paths:
        incoming = parse_listing(p.read_text(encoding='utf-8-sig'), image, BASE)
        checked(all(code[a] == incoming[a] for a in code.keys() & incoming.keys()),
                'listing overlap differs')
        code.update(incoming)
    # Load only audited functions; unrelated neighboring functions are omitted.
    windows = ((0x604009bf, 0x60400ade), (0x60400c60, 0x60400e55),
               (0x604008a7, 0x604008e8), (0x60401180, 0x604011ed))
    leaf_code = {a: ins for a, ins in code.items() if any(lo <= a < hi for lo, hi in windows)}
    rows = []

    def make(source, sample=0, remap=False, status=0, selected_code=None):
        table = bytearray().join(struct.pack('<II', i, i) for i in range(1024))
        block = (source-0x40000000)//131072
        physical = block+17 if remap else block
        struct.pack_into('<I', table, block*8, physical)
        mem = MemoryTrace([Region(BASE, image), Region(SP-32768, bytearray(65536), True),
                           Region(MAP, table, True),
                           Region(0x9880014c, bytearray(4), True),
                           Region(0x98d01000, bytearray(4096), True)])
        mem.write(SAMPLE, sample, 4)
        mem.mmio_writes.clear()
        models = {
            0x6040113a: Return('synthetic-controller-completion', [(0xe0, 16)], 0),
            0x604010f2: Return('injected-controller-status', [(0xc0, 12)], status),
            0x604013d0: Return('suppressed-diagnostic', [(0, 4)], 0),
        }
        return CallMachine(leaf_code if selected_code is None else selected_code, mem,
                           dict(sp=SP, d0=DEST, d1=source), models=models), physical

    for component, source in ADDRESSES.items():
        for name, (entry, frame, size, maintenance_pc, loop_pc, status_pc) in READERS.items():
            for sample in (0, 13, 14, 15):
                for remap in (False, True):
                    m, physical = make(source, sample, remap)
                    m.r['a0'] = size
                    stop = maintenance_pc if name != 'direct-page' and sample > 13 else END
                    r = m.run(m.enter(entry, END, 0xf0, frame), [stop])
                    checked(r.get('pc') == stop, 'native read branch differs: '+str(r))
                    requests = [v for a, v, _ in m.memory.mmio_writes if a == 0x98d01800]
                    expected_block = (source-0x40000000)//131072 if name == 'direct-page' else physical
                    checked(requests == [0x08000000 + expected_block*64], 'native physical page differs')
                    mapping_seen = any(e.get('target') == 0x604008a7 for e in m.events)
                    checked(mapping_seen == (name != 'direct-page'), 'mapping helper reachability differs')
                    sampled = any(a == SAMPLE for a, _, _ in m.memory.mmio_reads)
                    checked(sampled == (name != 'direct-page'), 'maintenance register sampling differs')
                    if stop == END:
                        checked(m.r['sp'] == SP and m.r['d0'] == 0, 'leaf return differs')
                    else:
                        checked(m.r['d0'] == physical, 'maintenance block argument differs')
                    rows.append(dict(kind='threshold-and-mapping', component=component, reader=name,
                                     register_low_nibble=sample, synthetic_remap=remap,
                                     physical_block=expected_block, mapping_executed=mapping_seen,
                                     maintenance_call_reached=stop != END,
                                     maintenance_executed=False, bytes_obtained=False))

    # Full 25 MiB envelopes are exact multiples of the native 128 KiB bulk unit.
    # Execute all iterations; there is no bulk-loop accelerator in this probe.
    for component, source in ADDRESSES.items():
        m, _ = make(source, 13)
        m.r['a0'] = SIZE
        r = m.run(m.enter(0x60400d2f, END, 0xf0, 44), [END, 0x60400e3f])
        requests = [v for a, v, _ in m.memory.mmio_writes if a == 0x98d01800]
        packets = [v for a, v, _ in m.memory.mmio_writes if a == 0x98d01804]
        count = SIZE//131072
        checked(r.get('pc') == END and m.r['sp'] == SP and len(requests) == count and
                requests == [0x08000000+(source-0x40000000)//2048+64*i for i in range(count)] and
                packets == [v for i in range(count) for v in (0x01402040, 0x29000000+131072*i, 0)],
                'full envelope native bulk requests differ')
        rows.append(dict(kind='full-envelope-control', component=component, bytes=SIZE,
                         blocks=count, native_instructions=len(m.trace), register_low_nibble=13,
                         loop_acceleration=False, bytes_obtained=False))

    for name, (entry, frame, size, maintenance_pc, loop_pc, status_pc) in READERS.items():
        m, _ = make(ADDRESSES['main'], 0, status=1)
        m.r['a0'] = size
        r = m.run(m.enter(entry, END, 0xf0, frame), [loop_pc])
        checked(r.get('pc') == loop_pc, 'initial read loop not reached')
        for _ in range(2):
            r = m.run(loop_pc, [status_pc])
            checked(r.get('pc') == status_pc, 'status fixture not reached')
            r = m.run(status_pc, [loop_pc, END])
            checked(r.get('pc') == loop_pc, 'persistent status did not retry')
        requests = [v for a, v, _ in m.memory.mmio_writes if a == 0x98d01800]
        checked(len(requests) == 2 and requests[0] == requests[1], 'retry advanced physical page')
        rows.append(dict(kind='persistent-status', reader=name, injected_status=1,
                         repeated_requests=2, same_physical_page=True,
                         returned_to_loop=True, caller_has_not_regained_control=True))

    # Execute the relocation planner with storage leaves trapped, not a flash
    # transaction. Start with one explicitly free spare at native table slot 992.
    maintenance_code = {a: ins for a, ins in code.items() if 0x604007b0 <= a < 0x604008a7}
    m, _ = make(ADDRESSES['main'], selected_code=maintenance_code)
    block = (ADDRESSES['main']-0x40000000)//131072
    m.memory.write(MAP+992*8+4, 0xffffffff, 4)
    m.models = {
        0x60400c60: Request('unexecuted-read-old-block', [(0xf0, 28)]),
        0x60401066: Request('unexecuted-erase-request', [(0xf0, 24)]),
        0x60400e55: Request('unexecuted-program-request', [(0xf0, 36)]),
        0x60400f67: Request('unexecuted-page-metadata-request', [(0xf0, 20)]),
        0x6040129c: Return('unexecuted-local-buffer-helper', [(0xc0, 8)], 0),
        0x604009b7: Return('suppressed-maintenance-diagnostic', [(0, 4)], 0),
    }
    m.r['d0'] = block
    r = m.run(m.enter(0x604007b0, END, 0xf0, 36), [END])
    requests = [e for e in m.events if e.get('target') in (0x60400c60, 0x60401066, 0x60400e55, 0x60400f67)]
    checked(r.get('pc') == END and m.r['sp'] == SP and m.memory.read(MAP+block*8, 4) == 992,
            'native relocation planner differs')
    expected = [0x60400c60, 0x60401066, 0x60400e55, 0x60400f67,
                0x60401066, 0x60400e55, 0x60400e55, 0x60400e55]
    checked([e['target'] for e in requests] == expected, 'native maintenance operation order differs')
    checked([(int(e['d0'], 0), int(e['d1'], 0)) for e in requests if e['target'] == 0x60401066]
            == [(0x40000000+992*131072, 131072), (0x47ec0000, 393216)], 'erase ranges differ')
    checked([(int(e['d1'], 0), int(e['a0'], 0)) for e in requests if e['target'] == 0x60400e55]
            == [(0x40000000+992*131072, 131072), (0x47ec0000, 8192),
                (0x47ee0000, 8192), (0x47f00000, 8192)], 'program ranges differ')
    rows.append(dict(kind='native-maintenance-planner', old_block=block, synthetic_spare_block=992,
                     requests=requests, mapping_changed_in_synthetic_ram=True,
                     physical_storage_executed=False, bytes_obtained=False))

    report = dict(model='E-PL9 / IM008 / 1330', displayed_version='1.1 (owner report)', build='1101',
                  main_bytes=len(image), main_sha256=sha(image), cases=rows,
                  source_sha256=sha(Path(__file__).read_bytes()),
                  listing_sha256={str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in paths},
                  mmio_and_controller_results_are_synthetic=True, flash_bytes_supplied=False,
                  bulk_mode_excludes_maintenance=False,
                  direct_page_preserves_logical_mapping=False,
                  physical_transport_qualified=False, camera_accessed=False, install_ready=False)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows), maintenance_branch_controls=sum(
        r.get('maintenance_call_reached', False) for r in rows),
        full_envelope_controls=2, physical_storage_executed=False)))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--listings', type=Path, default=LISTINGS)
    args = ap.parse_args()
    run(args.out, args.listings)
