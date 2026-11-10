"""Read-only E-PL9 early-main/section-loading evidence; never a boot emulator.

Executes bounded native fragments with explicit RAM fixtures and storage-read
traps. No camera, media, update package or modified firmware is written.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess

from epl9_color_audit import MAIN_SHA, STOCK_SHA
from epl9_video_audit import ROOT, BASE, MAIN_NAME, verified_input, checked_listing, local_output
from mn103_subset import Memory, Region, Machine, Fault, parse_listing
from mn103_calls import CallMachine

READER_SHA = 'e1c9bcb2b2467a44b8f6e2b6910c9868eff6ce571c36d5b9ad41d1d8693a76ae'
WINDOWS = {
    'main_entry': (0x60400020, 0x604003cf),
    'initial_task': (0x60432197, 0x604322f0),
    'initial_services': (0x60421d35, 0x604229df),
    'sections': (0x604229df, 0x60422d10),
    'address_translation': (0x60445069, 0x604450ad),
    'startup_workers': (0x6056aacf, 0x6056c08e),
    'task_activation_walk': (0x604127b4, 0x60412804),
    'kernel_entry': (0x604125e0, 0x604127b4),
    'kernel_trampoline': (0x6041009c, 0x6041009f),
}
STACK, SP, RETURN = 0x18000000, 0x18008000, 0x1a000000
SECTION_FLAGS = 0xa2aeaa3c


def sha(data):
    return hashlib.sha256(data).hexdigest()


def expected_address(value):
    # Contract of 60445069, checked against native execution in each request.
    if 0x40000000 <= value < 0x41000000 or 0x60000000 <= value < 0x80000000:
        return (value & 0x3fffffff) | 0x80000000
    return value


def task_records(image):
    """Slots are not IDs: the final rows skip ID 138."""
    rows = []
    for slot in range(144):
        address = 0x60418cc4 + slot * 28
        words = struct.unpack_from('<7I', image, address - BASE)
        if not any(words):
            if slot != 143:
                raise ValueError('unexpected task-table sentinel')
            break
        ident, attributes, argument, entry, priority, stack, extra = words
        if not (0 < ident <= 143 or (slot == 0 and ident == 0x808a)) or not BASE <= entry < BASE + len(image):
            raise ValueError('unexpected task descriptor')
        rows.append(dict(slot=slot, address=hex(address), id=ident,
                         attributes=attributes, argument=argument, entry=hex(entry),
                         priority=priority, stack_bytes=stack, extra=extra))
    if len(rows) != 143 or len({r['id'] for r in rows}) != 143:
        raise ValueError('unexpected task-table size/duplicate ID')
    return rows


def load_code(image, reader, out):
    if sha(reader.read_bytes()) != READER_SHA:
        raise ValueError('unqualified disassembler')
    code = {}
    for name, (start, end) in WINDOWS.items():
        listing = subprocess.check_output([
            str(reader.resolve()), str((ROOT/'local/epl9-1101-analysis/decoded'/MAIN_NAME).resolve()),
            hex(BASE), hex(start-BASE), hex(end-BASE)], text=True)
        checked_listing(listing, image, start, end)
        native = parse_listing(listing, image, BASE)
        if any(code[a] != native[a] for a in code.keys() & native.keys()):
            raise ValueError('conflicting instruction boundaries')
        code.update(native)
        (out/(name+'.tsv')).write_text(listing, encoding='utf8')
    return code


def section_endpoint(image, code, ident):
    if ident not in range(1, 10):
        raise ValueError('section ID must be 1..9')
    m = Machine(code, Memory([Region(BASE, image, False, 'exact main')]), {'d0': ident})
    stop = m.run(0x604229df, stops={0x60422a3a}, limit=50)
    if stop.get('pc') != 0x60422a3a:
        raise Fault(f'endpoint helper failed: {stop}')
    return m.r['d0']


class Boundary:
    def __init__(self, name, abi, value=0):
        self.name, self.abi, self.value = name, abi, value

    def validate(self, m, mask, frame):
        if (mask, frame) != self.abi:
            raise Fault(f'undeclared {self.name} ABI: {mask:#x}/{frame}')

    def apply(self, m):
        detail = dict(injected_return=self.value)
        if self.name == 'endpoint-RETS-bridge':
            ident = m.r['d0']
            detail['section'] = ident
            # The helper's exact instructions were executed separately up to
            # RETS. This bridge avoids adding RETS support to the shared engine.
            m.r['d0'] = self.value[ident]
            detail['injected_return'] = hex(m.r['d0'])
        else:
            if self.name == 'storage-read-trap':
                detail.update(destination=hex(m.r['a0']), source=hex(m.r['a1']),
                              bytes=m.r['d0'], mode=m.r['d1'], physical_read=False)
            m.r['d0'] = self.value
        return detail


def section_cases(image, code):
    endpoints = {i: section_endpoint(image, code, i) for i in range(1, 10)}
    # Exclude the RETS helper so the declared bridge cannot shadow native code.
    executable = {a: v for a, v in code.items() if not 0x604229df <= a < 0x60422a3c}
    rows = []
    for ident, error in [(i, 0) for i in range(1, 10)] + [(1, 0x3101), (6, 0x3101)]:
        models = {
            0x604229df: Boundary('endpoint-RETS-bridge', (0, 0), endpoints),
            0x6043ae0d: Boundary('storage-read-trap', (0xf0, 20), error),
            0x604022d4: Boundary('diagnostic-suppressed', (0xa0, 40)),
            0x6056838a: Boundary('section-7-extra-init-suppressed', (0xa0, 12)),
        }
        memory = Memory([Region(BASE, image, False, 'exact main'),
                         Region(STACK, bytearray(0x10000), True, 'synthetic stack'),
                         Region(SECTION_FLAGS, bytearray(4), True, 'synthetic section flags')])
        m = CallMachine(executable, memory, {'sp': SP, 'd0': ident}, models=models)
        m.enter(0x60422a3c, RETURN, 0xf0, 24)
        stop = m.run(0x60422a3c, stops={RETURN}, limit=1000)
        if stop.get('pc') != RETURN or m.r['sp'] != SP:
            raise Fault(f'section reader did not return: {stop}')
        requests = [e for e in m.events if e.get('model') == 'storage-read-trap']
        assert len(requests) == 1
        start, source, destination = struct.unpack_from('<3I', image, 0x60405f94-BASE+(ident-1)*12)
        end = endpoints[ident]
        request = requests[0]
        assert 0 <= end-start <= len(image)  # Stock section 8 is empty.
        assert request['bytes'] == end-start and request['mode'] == 257
        assert int(request['source'], 16) == expected_address(source)
        assert int(request['destination'], 16) == expected_address(destination)
        assert memory.read(SECTION_FLAGS, 4) == 1 << (ident-1)
        rows.append(dict(section=ident, start=hex(start), end_exclusive=hex(end),
                         length=end-start, injected_read_error=hex(error), request=request,
                         loaded_bit_set=True, events=m.events,
                         whole_boot_executed=False, physical_storage_access=False))
    return rows


def wait_cases(image, code):
    rows = []
    for flags in (0, 1 << 5):
        m = CallMachine(code, Memory([
            Region(BASE, image, False, 'exact main'),
            Region(SECTION_FLAGS, struct.pack('<I', flags), False, 'declared flag fixture')]), {'d0': 6})
        stop = m.run(0x60422ac1, stops={0x60422ade}, limit=50)
        if flags:
            assert stop.get('status') == 'stop' and stop['pc'] == 0x60422ade
        else:
            assert stop.get('status') == 'external_call' and stop['target'] == 0x60411401
        rows.append(dict(section=6, flags=hex(flags), stop=stop,
                         note='stop before delay or post-load initialization; no scheduler model'))
    return rows


def static_contracts(image, code):
    anchors = {
        0x60400029: 'calls\t0x604000e9',
        0x604000d6: 'mov\t1614807289,a0',
        0x604000dc: 'jmp\t(a0)',
        0x604000ef: 'mov\t(a0),d0',
        0x604000f6: 'mov\td0,(a0)',
        0x604001cb: 'call\t0x604014c6,[d2,d3,a2,a3],32',
        0x604003c5: 'call\t0x6041009c,[],0',
        0x6041009c: 'jmp\t0x604125e0',
        0x604322d6: 'call\t0x604005d3,[],0',
        0x604322e1: 'call\t0x60421d35,[],8',
        0x60421d6a: 'call\t0x60422bb1,[],24',
        0x60422432: 'call\t0x604318bb,[d2,d3],12',
        0x60422a54: 'mov\t(8,a3),d0',
        0x60422a6d: 'sub\td1,d2',
        0x60422a74: 'call\t0x6043ae0d,[d2,d3,a2,a3],20',
        0x60422ab8: 'mov\td0,(0xa2aeaa3c)',
        0x6056b7e0: 'call\t0x60422ac1,[d2,d3],32',
        0x6056bf4a: 'movhu\t(0x60420ba8),d0',
        0x6056bf51: 'call\t0x604318bb,[d2,d3],12',
    }
    for address, want in anchors.items():
        _, op, args = code[address]
        if op+'\t'+','.join(args) != want:
            raise ValueError(f'instruction anchor mismatch at {address:#x}')
    tasks = task_records(image)
    assert [(r['id'], r['attributes']) for r in tasks if r['attributes']] == [(1, 2)]
    assert struct.unpack_from('<H', image, 0x60420ba8-BASE)[0] == 18
    assert next(r for r in tasks if r['id'] == 89)['entry'] == '0x610039fd'
    assert next(r for r in tasks if r['id'] == 18)['entry'] == '0x61003e85'
    return dict(checked_instruction_anchors=len(anchors), task_records=tasks,
                nonzero_descriptor_attributes=[r for r in tasks if r['attributes']],
                physical_reset_to_main_traced=False, physical_OK_to_task_89_traced=False,
                immutable_rescue_loader_proven=False)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    if not __debug__:
        p.error('assertions required')
    out = local_output(args.out)
    image = verified_input(ROOT/'local/epl9-1101-analysis/decoded'/MAIN_NAME, 26214336, MAIN_SHA)
    stock = verified_input(ROOT/'firmware/OLY_E_133_1101_0000_0000.BIN', 104552480, STOCK_SHA)
    out.mkdir()
    code = load_code(image, ROOT/'local/mn103-tooling/mn103-reader.exe', out)
    rows = section_cases(image, code)
    waits = wait_cases(image, code)
    contracts = static_contracts(image, code)
    report = dict(model='Olympus PEN E-PL9', model_bytes='1330',
                  displayed_version='1.1 (owner report)', main_build='1101 (download)',
                  stock_bytes=len(stock), stock_sha256=STOCK_SHA,
                  main_bytes=len(image), main_sha256=MAIN_SHA, reader_sha256=READER_SHA,
                  source_sha256=sha(Path(__file__).read_bytes()),
                  dependencies={n: sha((ROOT/'scripts'/n).read_bytes()) for n in (
                      'mn103_subset.py', 'mn103_calls.py', 'epl9_video_audit.py', 'epl9_color_audit.py')},
                  section_cases=rows, section_wait_cases=waits, static_contracts=contracts,
                  camera_accessed=False, firmware_modified=False, media_accessed=False,
                  reference_revision='539fcf1fa9eda5fdef8ede4deeab94a4691d94c3')
    (out/'results.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf8')
    print(json.dumps(dict(native_section_cases=len(rows), native_wait_cases=len(waits),
                          instruction_anchors=contracts['checked_instruction_anchors'],
                          task_descriptors=len(contracts['task_records']), camera_accessed=False,
                          sections=[{k:r[k] for k in ('section','start','end_exclusive','length')}
                                    for r in rows[:9]]), indent=2))


if __name__ == '__main__':
    main()
