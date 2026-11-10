"""Bounded E-PL9 OK/wake/task-selection audit. No camera or media interface.

This does not emulate physical reset or invent an OK-to-SD selector. Native
fragments use declared RAM/register fixtures; task activation is trapped.
"""

from mn103_tooling import default_reader, verify_reader
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess

from epl9_color_audit import MAIN_SHA, STOCK_SHA
from epl9_video_audit import ROOT, BASE, MAIN_NAME, verified_input, checked_listing, local_output
from epl9_boot_recovery_audit import task_records
from mn103_subset import Memory, Region, Machine, Fault, parse_listing
from mn103_calls import CallMachine

STACK, SP, RETURN = 0x18000000, 0x18008000, 0x1a000000
CONFIG, ROOT_SLOT = 0x6042143c, 0x8ff00004
WINDOWS = {
    'task_constructor': (0x604129aa, 0x60412a06),
    'task_initializer': (0x60410b0c, 0x60410b8a),
    'task_autostart': (0x604127b4, 0x60412804),
    'wake_decode': (0x6044463c, 0x6044476f),
    'key_state': (0x604f427f, 0x604f4347),
    'key_lookup': (0x604f4e7a, 0x604f4fc7),
    'ordinary_sd_hooks': (0x6056bf3c, 0x6056bf58),
    'sd_hook_zero': (0x61003c54, 0x61003c58),
    'sd_hook_return': (0x61003e82, 0x61003e85),
    'request_reply': (0x60434bbe, 0x60434c51),
    'boot_kind': (0x61004520, 0x61004561),
    'boot_write': (0x610049ee, 0x61004a4f),
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def u32(image, address):
    return struct.unpack_from('<I', image, address-BASE)[0]


def cstring(image, address):
    start = address-BASE
    if not 0 <= start < len(image):
        raise ValueError('string outside image')
    end = image.find(b'\0', start)
    if end < 0:
        raise ValueError('unterminated string')
    return image[start:end].decode('ascii')


def transfers(image, targets):
    """Raw relative-transfer candidates; these are not a reachability proof."""
    rows = []
    for match in re.finditer(rb'[\xc0-\xcd\xdc\xdd]|\xfa\xff|\xfc\xff', image):
        p = match.start(); op = image[p]
        if op == 0xcb:
            continue
        if op <= 0xca:
            width, skip, kind = 1, 1, 'branch8'
        elif op in (0xcc, 0xcd):
            width, skip, kind = 2, 1, 'jmp16' if op == 0xcc else 'call16'
        elif op in (0xdc, 0xdd):
            width, skip, kind = 4, 1, 'jmp32' if op == 0xdc else 'call32'
        else:
            width, skip, kind = (2 if op == 0xfa else 4), 2, 'calls'
        if p+skip+width > len(image):
            continue
        target = (BASE+p+int.from_bytes(image[p+skip:p+skip+width], 'little', signed=True)) & 0xffffffff
        if target in targets:
            rows.append(dict(site=hex(BASE+p), target=hex(target), encoding=kind))
    return rows


def pointer_candidates(image, target):
    pattern = re.escape(struct.pack('<I', target))
    return [hex(BASE+m.start()) for m in re.finditer(pattern, image)]


def load_code(image, out):
    reader = default_reader()
    verify_reader(reader)
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


class Boundary:
    def __init__(self, name, abi):
        self.name, self.abi, self.cursor = name, abi, 0x20000000

    def validate(self, m, mask, frame):
        if (mask, frame) != self.abi:
            raise Fault(f'undeclared {self.name} ABI {mask:#x}/{frame}')

    def apply(self, m):
        if self.name == 'declared-stack-address-allocator':
            size, pointer = m.r['d0'], self.cursor
            if not 0 < size < 0x10000:
                raise Fault('unexpected requested stack size')
            self.cursor += (size+15) & ~15
            m.r['a0'], m.r['d0'] = pointer, 0
            return dict(requested_bytes=size, declared_pointer=hex(pointer),
                        note='addresses supplied; no task stack executes')
        if self.name == 'task-activation-trap':
            tcb = m.r['a0']
            row = dict(task_id=m.memory.read(tcb+16, 2), tcb=hex(tcb),
                       argument=m.r['d0'], entry=hex(m.memory.read(tcb+76, 4)),
                       attributes=hex(m.memory.read(tcb+68, 4)), scheduled=False)
            m.r['d0'] = 0
            return row
        raise Fault('unknown boundary')


def autostart_case(image, code):
    pointer_table = u32(image, CONFIG+204)
    counts = u32(image, CONFIG+60)
    count = struct.unpack_from('<H', image, counts+2-BASE)[0]
    pointers = struct.unpack_from('<'+str(count)+'I', image, pointer_table-BASE)
    if count != 255 or len(set(pointers)) != count:
        raise ValueError('unqualified TCB pointer table')
    regions = [Region(BASE, image, False, 'exact main'),
               Region(0x8050, bytes(4), False, 'declared CPU zero'),
               Region(ROOT_SLOT, struct.pack('<I', CONFIG), False, 'stock CPU-zero context'),
               Region(STACK, bytearray(0x10000), True, 'synthetic caller stack'),
               Region(u32(image, CONFIG+260), bytearray(4), False, 'declared zero hook gate')]
    regions += [Region(p, bytearray(120), True, 'declared zeroed TCB') for p in pointers]
    models = {0x6041600d: Boundary('declared-stack-address-allocator', (0xf0, 16)),
              0x60412230: Boundary('task-activation-trap', (0xe0, 16))}
    m = CallMachine(code, Memory(regions), {'sp': SP}, models=models)
    m.enter(0x604129aa, RETURN, 0xb0, 16)
    first = m.run(0x604129aa, stops={RETURN}, limit=100000)
    assert first.get('pc') == RETURN and m.r['sp'] == SP, first
    constructed = []
    for descriptor in task_records(image):
        ident = descriptor['id']; tcb = pointers[(ident & 0xfff)-1]
        assert m.memory.read(tcb+16, 2) == ident
        assert m.memory.read(tcb+76, 4) == int(descriptor['entry'], 16)
        attributes = m.memory.read(tcb+68, 4)
        assert attributes & 2 == descriptor['attributes'] & 2
        constructed.append(dict(id=ident, tcb=hex(tcb), attributes=hex(attributes),
                                auto_bit=bool(attributes & 2), entry=descriptor['entry']))
    m.enter(0x604127b4, RETURN, 0xb0, 16)
    second = m.run(0x604127b4, stops={RETURN}, limit=100000)
    assert second.get('pc') == RETURN and m.r['sp'] == SP, second
    starts = [e for e in m.events if e.get('model') == 'task-activation-trap']
    assert [e['task_id'] for e in starts] == [1]
    assert [r['id'] for r in constructed if r['auto_bit']] == [1]
    return dict(tcb_slots=count, descriptors_constructed=len(constructed),
                pointer_table=hex(pointer_table), constructed=constructed,
                activation_requests=starts, events=m.events,
                native_instructions=len(m.trace),
                whole_boot_executed=False, task_execution=False)


def wake_cases(image, code):
    rows = []
    fixtures = [(0, 0, 0, 0), (2, 0, 0, 9), (2, 1, 0, 1),
                (2, 4, 0, 3), (2, 8, 0, 4), (2, 8, 0x80000000, 9),
                (2, 16, 0, 5), (2, 32, 0, 6), (2, 64, 0, 7),
                (2, 128, 0, 8), (2, 256, 0, 8)]
    for gate, wake, level, expected in fixtures:
        registers = bytearray(0x1000)
        for offset, value in ((0, gate), (0x48, wake), (0x64, level)):
            struct.pack_into('<I', registers, offset, value)
        memory = Memory([Region(BASE, image, False, 'exact main'),
                         Region(0x98e00000, registers, True, 'RAM register fixture'),
                         Region(0xa2ad2a10, bytearray(2), True, 'declared wake result')])
        # Start after controller setup: a RAM register model must not pretend
        # that writes to control bits reproduce reads of a live input bit.
        m = Machine(code, memory, {'a0':0x98e00048, 'a1':0x98e00064, 'd1':1})
        stop = m.run(0x604446ee, stops={0x6044476f}, limit=1000)
        assert stop.get('pc') == 0x6044476f, stop
        value = memory.read(0xa2ad2a10, 2)
        assert value == expected, (gate, wake, level, value)
        rows.append(dict(register_98e00000=hex(gate), wake_98e00048=hex(wake),
                         level_98e00064=hex(level), decoded_reason=value,
                         instructions=len(m.trace),
                         start='selection slice after unexecuted controller setup',
                         stop='before wake acknowledgement / hardware commit',
                         physical_button_identity_proven=False))
    return rows


def key_cases(image, code):
    # Exact initialized pointer data: early-main read 408ff800 -> a238a540.
    source, destination, length = 0x6061f800, 0x6238a540, 0x2ef18
    initial = image[source-BASE:source-BASE+length]
    assert len(initial) == length
    results = []
    for snapshot, want in ((0, 0), (0x40, 1), (0xbf, 0), (0xff, 1)):
        globals_ram = bytearray(0x800)
        struct.pack_into('<I', globals_ram, 0x14, 0)  # Declared board-table variant.
        struct.pack_into('<H', globals_ram, 0x268, snapshot)  # a2ae73e8.
        m = CallMachine(code, Memory([
            Region(BASE, image, False, 'exact main'),
            Region(destination, initial, False, 'stock initialized pointer data'),
            Region(0xa2ae7180, globals_ram, True, 'declared key state / variant zero'),
            Region(STACK, bytearray(0x10000), True, 'synthetic caller stack')]),
            {'sp': SP, 'd0': 0x02000004})
        m.enter(0x604f427f, RETURN, 0xf0, 24)
        stop = m.run(0x604f427f, stops={RETURN}, limit=5000)
        assert stop.get('pc') == RETURN and m.r['sp'] == SP, stop
        assert m.r['d0'] == want, (snapshot, m.r['d0'])
        results.append(dict(event='0x02000004', board_variant_fixture=0,
                            snapshot_a2ae73e8=hex(snapshot), returned_state=m.r['d0'],
                            instructions=len(m.trace), task_activation=False))
    return dict(initializer_source=hex(source), initializer_destination=hex(destination),
                initializer_bytes=length, initializer_sha256=sha(initial), cases=results,
                physical_OK_to_SD_entry_proven=False)


def static_contracts(image, code):
    anchors = {
        0x604129e2: 'add\t68,a0',
        0x604129e9: 'mov\td0,(a0)',
        0x604127e7: 'btst\t2,d0',
        0x604127f4: 'call\t0x60412230,[d2,d3,a2],16',
        0x60434c1d: 'mov\t(8,sp),d0',
        0x60434c21: 'call\t0x604313e9,[d2,d3,a2,a3],24',
        0x6056bf3c: 'call\t0x61003c54,[],0',
        0x6056bf43: 'call\t0x61003e82,[],0',
        0x6056bf51: 'call\t0x604318bb,[d2,d3],12',
        0x61003c54: 'clr\td0',
        0x61003c55: 'retf\t[],0',
        0x61003e82: 'retf\t[],0',
        0x6100452a: 'cmp\t16,d0',
        0x61004534: 'mov\t1630700972,a0',
        0x610049fa: 'mov\t1630701711,a0',
    }
    for address, want in anchors.items():
        _, op, args = code[address]
        if op+'\t'+','.join(args) != want:
            raise ValueError(f'anchor mismatch at {address:#x}')
    assert struct.unpack_from('<2I', image, 0x60e3e6ec-BASE) == (0x02000004, 0x44)
    assert struct.unpack_from('<2I', image, 0x60dda22c-BASE) == (0x44, 0x60dd89c6)
    assert cstring(image, 0x60dd89c6) == 'EV_PRESS_OK_KEY'
    assert cstring(image, 0x613285ac).rstrip('\r\n') == '[firmup]...BOOT Gets'
    assert cstring(image, 0x6132888f).rstrip('\r\n') == '[firmup]TYPE_FIRMUP_WRITE_BOOT'
    hooks = []
    for entry, abi in ((0x61003c54, (0, 0)), (0x61003e82, (0, 0))):
        m = CallMachine(code, Memory([Region(BASE, image, False, 'exact main'),
                                     Region(STACK, bytearray(0x10000), True, 'synthetic stack')]),
                        {'sp': SP, 'd0': 0xa5})
        m.enter(entry, RETURN, *abi)
        stop = m.run(entry, stops={RETURN}, limit=10)
        assert stop.get('pc') == RETURN and m.r['sp'] == SP
        assert m.r['d0'] == (0 if entry == 0x61003c54 else 0xa5)
        hooks.append(dict(entry=hex(entry), return_value=hex(m.r['d0']),
                          task_activation=False, instructions=len(m.trace)))
    return dict(instruction_anchors=len(anchors), native_hook_cases=hooks,
                OK_event_mapping=['0x02000004', '0x44', 'EV_PRESS_OK_KEY'],
                number_89_at_60421018='reply queue identifier, not task-activation evidence',
                optional_BOOT_low_kind='0x10', physical_reset_selector_located=False)


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
    code = load_code(image, out)
    tasks, wake, keys = autostart_case(image, code), wake_cases(image, code), key_cases(image, code)
    static = static_contracts(image, code)
    candidates = transfers(image, {0x610039fd, 0x61003c54, 0x61003e82, 0x60410727, 0x604318bb})
    pointers = {hex(a):pointer_candidates(image, a) for a in (0x610039fd, 0x60420c36, 0x60421018)}
    assert pointers == {'0x610039fd':['0x6041968c'], '0x60420c36':[], '0x60421018':['0x60f59c96']}
    component_rows = []
    offset = 0
    while offset < len(stock):
        size = struct.unpack_from('<I', stock, offset+12)[0]
        kind = struct.unpack_from('<H', stock, offset+20)[0]
        assert 0 < size and offset+size+64 <= len(stock)
        component_rows.append(dict(kind=hex(kind), payload_bytes=size))
        offset += size+64
    assert offset == len(stock) and [r['kind'] for r in component_rows] == ['0x100','0x101','0x106','0x10e','0x102']
    report = dict(model='Olympus PEN E-PL9', model_bytes='1330',
                  displayed_version='1.1 (owner report)', downloaded_main_build='1101',
                  stock_bytes=len(stock), stock_sha256=STOCK_SHA,
                  main_bytes=len(image), main_sha256=MAIN_SHA, reader_sha256=verify_reader(),
                  source_sha256=sha(Path(__file__).read_bytes()),
                  dependencies={n:sha((ROOT/'scripts'/n).read_bytes()) for n in (
                      'mn103_subset.py','mn103_calls.py','epl9_color_audit.py',
                      'epl9_video_audit.py','epl9_boot_recovery_audit.py')},
                  autostart=tasks, wake_reason_cases=wake, key_state=keys,
                  static_contracts=static, raw_transfer_candidates=candidates,
                  raw_pointer_candidates=pointers,
                  stock_component_kinds=component_rows,
                  physical_OK_to_SD_proven=False, arbitrary_main_recovery_proven=False,
                  camera_accessed=False, media_accessed=False, firmware_modified=False,
                  reference_revision='539fcf1fa9eda5fdef8ede4deeab94a4691d94c3')
    (out/'results.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf8')
    print(json.dumps(dict(descriptors_constructed=tasks['descriptors_constructed'],
                          tcb_slots=tasks['tcb_slots'],
                          requested_tasks=[r['task_id'] for r in tasks['activation_requests']],
                          native_wake_cases=len(wake), native_OK_cases=len(keys['cases']),
                          native_stub_cases=len(static['native_hook_cases']),
                          instruction_anchors=static['instruction_anchors'],
                          physical_OK_to_SD_proven=False, camera_accessed=False), indent=2))


if __name__ == '__main__':
    main()
