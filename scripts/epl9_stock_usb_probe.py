"""Stock USB mode -> PTP type, diagnostic gate and selector controls offline.

Stops before all real queue, device, service and response operations. No camera
operation is sent; other USB initialization is not modeled as successful.
"""
import argparse
import json
import struct
from pathlib import Path
from epl9_workspace_bridge import ROOT, MAIN, MAIN_SHA, BASE, sha
from epl9_recovery_audit import Boundary
from mn103_subset import Memory, Region, parse_listing
from mn103_calls import CallMachine

SP, REQ, PARAM, END = 0x18008000, 0x19000000, 0x19001000, 0x1a000000
MARKER, GATE = 0x626f5bca, 0x626f3d04
DIRECTORY = ROOT/'local/epl9-stock-usb-entry-v5-20261110'
OLD = ROOT/'local/epl9-memdump-entry-size-20261104'


def require(ok, message):
    if not ok: raise ValueError(message)


def run(out, directory=DIRECTORY):
    require(not out.exists() and out.resolve().is_relative_to((ROOT/'local').resolve()),
            'new ignored output required')
    image = MAIN.read_bytes()
    require(sha(image) == MAIN_SHA, 'stock image identity differs')
    code = {}; paths = []
    for p, lo, hi in [
        (directory/'usb-ptp-open-caller.tsv', 0x60faa835, 0x60faa864),
        (directory/'ptp-open-api.tsv', 0x60faf23f, 0x60faf257),
        (directory/'ptp-main-task.tsv', 0x60faf0a1, 0x60faf0f5),
        (directory/'ptp-setup.tsv', 0x60faf4fa, 0x60faf511),
        (directory/'diagnostic-dispatch.tsv', 0x60f51774, 0x60f51962),
        (directory/'none-dispatch.tsv', 0x60f535d8, 0x60f5473d),
        (directory/'in-dispatch.tsv', 0x60f5473d, 0x60f55674),
        (directory/'out-dispatch.tsv', 0x60f564b2, 0x60f56e54),
        (OLD/'usb_offline_worker_modes.lst', 0x60f51571, 0x60f5165b),
        (OLD/'ptp_operation_entry.lst', 0x60faf5ae, 0x60faf641),
        (OLD/'diagnostic_gate.lst', 0x60ef1fe4, 0x60ef1fed)]:
        native = parse_listing(p.read_text(encoding='utf-8-sig'), image, BASE)
        code.update({a: v for a, v in native.items() if lo <= a < hi}); paths.append(p)
    half = lambda a: struct.unpack_from('<H', image, a-BASE)[0]
    word = lambda a: struct.unpack_from('<I', image, a-BASE)[0]
    queue = half(0x60421086)
    rows = []

    def make(**regs):
        mem = Memory([Region(BASE, image), Region(SP-32768, bytearray(65536), True),
                      Region(REQ, bytearray(256), True), Region(PARAM, bytearray(64), True),
                      Region(MARKER-6, bytearray(32), True), Region(GATE, bytearray(4), True)])
        return CallMachine(code, mem, dict(sp=SP, **regs), models={
            0x60fafcd8: Boundary('unexecuted-PTP-phase-notification', [(0, 0)])})

    # These native fragments preserve each message's actual fields and widths.
    for mode, expected in ((0, 2), (1, 3), (2, 2), (3, 2), (4, 1),
                           (5, 2), (6, 2), (7, 1), (8, None)):
        m = make(a3=PARAM); m.memory.write(PARAM, mode, 1)
        r = m.run(0x60faa835, [0x60faa85f, 0x60faa864])
        if expected is None:
            require(r.get('pc') == 0x60faa864, 'bypass mode differs')
        else:
            require(r.get('pc') == 0x60faa85f and m.r['d0'] == expected, 'mode/type branch differs')
        rows.append(dict(kind='USB-mode-to-PTP-type', usb_mode=mode, ptp_type=expected,
                         prior_USB_initialization_executed=False))
    for typ in (1, 2, 3):
        m = make(d0=typ)
        r = m.run(m.enter(0x60faf23f, END, 0, 8), [0x60faf24d])
        require(r.get('pc') == 0x60faf24d and (m.r['d0'], m.r['d1']) == (queue, 1)
                and m.memory.read(m.r['a0'], 2) == typ, 'PTPCOM message differs')
        m.memory.write(PARAM, m.memory.read(m.r['a0'], 2), 4)
        # Separate task fragment with the same observed payload, not a modeled
        # queue exchange or continuation on the caller's partially entered stack.
        m.r['sp'] = SP
        m.memory.write(SP+40, 1, 4); m.memory.write(SP+44, PARAM, 4)
        r = m.run(0x60faf0a1, [0x60faf0c3])
        require(r.get('pc') == 0x60faf0c3 and m.memory.read(MARKER, 2) == typ
                and m.memory.read(0x626f5bc4, 4) == m.memory.read(0x626f5bc8, 2) == 0,
                'PTPCOM did not apply supplied type')
        rows.append(dict(kind='PTPCOM-init-message', command=1, queue=queue, supplied_type=typ,
                         stored_type=typ, queue_exchange_executed=False))
    for typ, want in ((1, 0x60faf641), (2, 0x60faf5bb), (3, 0x60faf641)):
        m = make(); m.memory.write(MARKER, typ, 2)
        r = m.run(0x60faf5ae, [0x60faf641, 0x60faf5bb])
        require(r.get('pc') == want, 'session observer type gate differs')
        rows.append(dict(kind='diagnostic-session-observer-gate', ptp_type=typ,
                         invokes_observer=typ == 2, observer_executed=False))

    admitted = {}
    for op in range(0x9000, 0x9035):
        m = make(); m.memory.write(REQ, op, 2)
        m.memory.write(SP+88, 9, 4); m.memory.write(SP+92, REQ, 4)
        r = m.run(0x60f51571, [0x60f5165b])
        require(r.get('pc') == 0x60f5165b, 'MTP classifier did not return')
        if m.memory.read(REQ+2, 2):
            admitted[op] = m.memory.read(REQ+4, 4)
    require(set(admitted) == {0x9029, 0x902a, 0x902b, 0x9030, 0x9031, 0x9032, 0x9033, 0x9034},
            'MTP vendor inventory changed')
    rows.append(dict(kind='MTP-vendor-classifier-range', first='0x9000', last='0x9034',
                     cases=53, admitted={hex(k): v for k, v in admitted.items()},
                     direct_READ_DATA_9021_admitted=False, direct_WRITE_DATA_9022_admitted=False))

    dispatch = {word(a)+0x1001: word(a+4) for a in range(0x612776d0, 0x612777d0, 8) if word(a)}
    stops = set(dispatch.values()) | {0x60f51958, 0x60f51946}
    for op in admitted:
        for gate in (0, 1):
            m = make(a0=REQ); m.memory.write(REQ, op, 2); m.memory.write(GATE, gate, 2)
            r = m.run(m.enter(0x60f51774, END, 0xa0, 24), stops)
            expected = dispatch[op] if gate else (0x60f51946 if op == 0x9034 else 0x60f51958)
            require(r.get('pc') == expected, 'session gate/dispatch changed: '+hex(op))
            if not gate and op != 0x9034:
                require(m.memory.read(REQ+48, 2) == 0x2003, 'closed session response changed')
            rows.append(dict(kind='admitted-vendor-session-gate', opcode=hex(op), diagnostic_gate=gate,
                             destination=hex(expected), handler_executed=False))

    inventories = {}
    for label, entry, low, high, table, error in (
        ('none', 0x60f535d8, 2, 73, 0x6127780c, 0x60f54720),
        ('in', 0x60f5473d, 2, 60, 0x61277974, 0x60f5564d),
        ('out', 0x60f564b2, 4, 23, 0x61277a88, 0x60f56e2d)):
        entries = {s: word(table+(s-low)*4) for s in range(low, high+1)}
        targets = set(entries.values()) | {error}
        for selector in list(range(low, high+1))+[0, low-1, high+1, 0xffff]:
            m = make(a0=REQ); m.memory.write(REQ+4, selector, 4)
            r = m.run(m.enter(entry, END, 0xf0, 16), targets)
            expected = entries.get(selector, error)
            require(r.get('pc') == expected, 'selector target changed')
            rows.append(dict(kind='model-selector', direction=label, selector=selector,
                             destination=hex(expected), unsupported=expected == error,
                             selected_handler_executed=False))
        inventories[label] = dict(total_entries=len(entries),
                                 unsupported=sum(a == error for a in entries.values()),
                                 supported={str(s): hex(a) for s, a in entries.items() if a != error})
    require(inventories['in']['supported']['47'] == '0x60f5503b' and
            '23' not in inventories['in']['supported'], 'capture/STL inventory changed')
    result = dict(model='E-PL9 / IM008 / 1330', body='1.1 (owner report)', build='1101',
                  main_bytes=len(image), main_sha256=sha(image), cases=rows,
                  selector_inventory=inventories, ptp_main_task=64, ptp_main_queue=queue,
                  mode_4_MTP_selects_type=1, type_two_session_observer_runs_for_MTP=False,
                  source_sha256=sha(Path(__file__).read_bytes()),
                  listing_sha256={str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in paths},
                  initialization_fragments_do_not_qualify_whole_USB_init=True,
                  no_qualified_stock_component_export_found=True,
                  physical_session_type_measured=False, camera_accessed=False,
                  physical_readback_qualified=False, firmware_modified=False)
    out.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(dict(fragment_rows=len(rows), native_cases=len(rows)+52,
                          MTP_type=1, diagnostic_observer=False, selectors=inventories)))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--directory', type=Path, default=DIRECTORY)
    a = ap.parse_args(); run(a.out, a.directory)
