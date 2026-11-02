"""Run native call chains with synthetic state; report unmodeled boundaries."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess

from epl9_art_routing_probe import BASE, ROOT, MAIN_SHA, STOCK_SHA, WINDOWS, EXPECTED
from epl9_offline_prototype import (JOB, SP, REQUEST, CONTEXT, OUTPUT, TABLE, OBJECT,
                                    RECIPES, header, machine, check_packing, route)
from epl9_service_audit import WINDOWS as SERVICE_WINDOWS, exercise
from mn103_subset import Region, Fault, parse_listing
from mn103_calls import CallMachine

RETURN = 0x0badf00d
EXTRA_WINDOWS = {
    'constructor_complete': (0x6074df04, 0x6074e341),
    'executor': (0x6074e6eb, 0x6074e7ca),
    'initializer': (0x6075199d, 0x607519b8),
    'abort_check': (0x6074f035, 0x6074f05a),
    'worklist_helpers': (0x60750fb2, 0x607511db),
    'early_callback_select': (0x60755e64, 0x60755ee4),
    'early_entries': (0x607511e9, 0x60751319),
    'early_processing': (0x60750b1e, 0x60750c2e),
    'owner_refs': (0x6074b41f, 0x6074b445),
    'buffer_get': (0x6074a8e4, 0x6074a8fc),
    'descriptor_copy': (0x6074f05a, 0x6074f225),
}


def native(image, code, regions, regs):
    m = machine(image, code, regions, regs)
    return CallMachine(code, m.memory, m.r)


def attempt(m, entry, mask, frame, stops=()):
    pc = m.enter(entry, RETURN, mask, frame)
    try:
        result = m.run(pc, [RETURN, *stops])
    except Fault as error:
        result = dict(status='fault', error=str(error), instructions=len(m.trace))
    return result


def full_route(image, code, key, kind, selector, flags=0, replacement=False):
    job = bytearray(14552)
    job[12:16] = header(key)
    struct.pack_into('<I', job, 10384, key)
    struct.pack_into('<I', job, 16, flags)
    struct.pack_into('<H', job, 20, kind)
    job[25] = selector
    m = native(image, code, [Region(JOB, job, True)], {'a0': JOB})
    result = attempt(m, 0x607519b8, 0xf0, 40,
                     [0x60752202] if replacement and key in RECIPES else [])
    redirected = result.get('pc') == 0x60752202
    if redirected:
        result = m.run(0x607523a5, [RETURN])
    if result.get('pc') != RETURN or m.r['sp'] != SP or m.r['d0'] != 0:
        raise ValueError(f'full worklist failed: {result}, sp={m.r["sp"]:#x}')
    count = struct.unpack_from('<H', job, 10390)[0]
    if not 0 < count <= 16:
        raise ValueError('invalid worklist count')
    entries = [list(struct.unpack_from('<3I', job, 10060+i*12)) for i in range(count)]
    if replacement and key in RECIPES:
        job[12:16] = header(11)
        struct.pack_into('<I', job, 10384, 11)
    return job, dict(key=hex(key), kind=hex(kind), selector=selector, flags=hex(flags),
                     redirected=redirected, entries=entries, result=result, calls=m.events)


def integrated_color(image, code, key):
    request, context, output, obj = bytearray(1876), bytearray(112), bytearray(5200), bytearray(20)
    request[8:12] = header(11)
    struct.pack_into('<I', request, 1524, OBJECT)
    struct.pack_into('<I', obj, 16, TABLE)
    struct.pack_into('<I', context, 4, REQUEST)
    struct.pack_into('<I', context, 12, OUTPUT)
    struct.pack_into('<I', context, 60, 0x10000000)
    table = bytearray(image[0x4ee340:0x4ee340+3028])
    # Deliberately distinct synthetic markers, NOT calibrated film recipes.
    struct.pack_into('<h', table, 14, 50 if key == 0x01010078 else -50)
    regions = [Region(REQUEST, request), Region(CONTEXT, context, True),
               Region(OUTPUT, output, True), Region(OBJECT, obj), Region(TABLE, table)]
    regs = {'a0': CONTEXT, 'd2': 0x22222222, 'd3': 0x33333333,
            'a2': 0xaaaa2222, 'a3': 0xaaaa3333}
    m = native(image, code, regions, regs)
    result = attempt(m, 0x6079ebcc, 0xf0, 20)
    assert result.get('pc') == RETURN and m.r['sp'] == SP, result
    assert all(m.r[r] == regs[r] for r in ('d2', 'd3', 'a2', 'a3'))
    assert any(e['op'] == 'call' and e['target'] == 0x6079e50e for e in m.events)
    check_packing(output, table, [struct.unpack_from('<h', table, r*28+14)[0] for r in range(12)])
    return dict(key=hex(key), recipe=RECIPES[key], result=result, calls=m.events,
                output_sha256=hashlib.sha256(output).hexdigest(), bytes_checked=len(output),
                synthetic_table_lifetime='retained throughout selector and builder; hardware consumption untested')


def executor(image, code, job, abort=False):
    count = struct.unpack_from('<H', job, 10390)[0]
    if abort:
        struct.pack_into('<H', job, 10394, 1)
    m = native(image, code, [Region(JOB, job, True), Region(OBJECT, bytearray(15500), True)],
               {'d0': JOB, 'd1': count})
    result = attempt(m, 0x6074e6eb, 0xf0, 32)
    return dict(result=result, calls=m.events, final_d0=m.r['d0'],
                completed_entries=struct.unpack_from('<H', job, 10388)[0],
                status=struct.unpack_from('<H', job, 10392)[0],
                abort=struct.unpack_from('<H', job, 10394)[0],
                last_instructions=[hex(p) for p in m.trace[-12:]])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    if not __debug__:
        p.error('assertions must remain enabled')
    path = ROOT/'local/epl9-1101-analysis/decoded/00_0100_406e0020.decoded.bin'
    image = path.read_bytes()
    if len(image) != 26214336 or hashlib.sha256(image).hexdigest() != MAIN_SHA:
        p.error('exact E-PL9 1.1 main required')
    if args.out.exists() or not args.out.resolve().is_relative_to((ROOT/'local').resolve()):
        p.error('output must be a new ignored local directory')
    code = {}
    reader = ROOT/'local/mn103-tooling/mn103-reader.exe'
    for start, end in {**WINDOWS, **SERVICE_WINDOWS, **EXTRA_WINDOWS}.values():
        listing = subprocess.check_output([str(reader), str(path), hex(BASE),
                    hex(start-BASE), hex(end-BASE)], text=True)
        decoded = parse_listing(listing, image, BASE)
        for at in code.keys() & decoded.keys():
            if code[at] != decoded[at]:
                raise ValueError(f'conflicting decode at {at:#x}')
        code.update(decoded)
    for at, expected in EXPECTED.items():
        _, op, operands = code[at]
        assert op+'\t'+','.join(operands) == expected
    report = dict(provenance=dict(model='E-PL9', displayed_version='1.1', main_build='1101',
        stock_bytes=104552480, stock_sha256=STOCK_SHA, main_bytes=len(image), main_sha256=MAIN_SHA,
        base=hex(BASE), reader_sha256=hashlib.sha256(reader.read_bytes()).hexdigest(),
        source_sha256={name: hashlib.sha256((ROOT/'scripts'/name).read_bytes()).hexdigest()
          for name in ('mn103_subset.py', 'mn103_calls.py', 'epl9_integrated_probe.py', 'epl9_offline_prototype.py')}),
        camera_accessed=False, firmware_modified=False, ready_for_patch=False)
    routes, executions = [], []
    for key in [*RECIPES, 1, 11, 0x01030078]:
        for kind in (0x0200, 0x0100, 0x0040):
            for selector in (0, 2):
                for flags in (0, 0x20000, 0x10000, 0x30000):
                    stock_job, stock = full_route(image, code, key, kind, selector, flags)
                    job, proposed = full_route(image, code, key, kind, selector, flags, True)
                    reference = full_route(image, code, 11, kind, selector, flags)[1] if proposed['redirected'] else stock
                    assert proposed['entries'] == reference['entries']
                    if not proposed['redirected']:
                        normalized = bytearray(job)
                        normalized[12:16] = stock_job[12:16]
                        normalized[10384:10388] = stock_job[10384:10388]
                        assert normalized == stock_job, 'retained path changed other job fields'
                    routes.append(dict(stock=stock, proposed=proposed))
                    if key in RECIPES and flags == 0:
                        execution = executor(image, code, bytearray(job))
                        cancelled = executor(image, code, bytearray(job), True)
                        assert cancelled['final_d0'] == 0x9e01 and cancelled['completed_entries'] == 0
                        assert cancelled['result'].get('pc') == RETURN
                        executions.append(dict(key=hex(key), kind=hex(kind), selector=selector,
                                               execution=execution, cancelled=cancelled))
    report['complete_worklist_pairs'] = routes
    report['color_call_chains'] = [integrated_color(image, code, k) for k in RECIPES]
    assert len({r['output_sha256'] for r in report['color_call_chains']}) == 2
    report['executor_attempts'] = executions
    m = native(image, code, [Region(REQUEST, bytearray(32)), Region(OUTPUT, bytearray(4), True)],
               {'a0': REQUEST, 'a1': OUTPUT})
    report['constructor_attempt'] = attempt(m, 0x6074df04, 0xf0, 44)
    report['service_components'] = exercise(image, code)
    report['full_pixel_cycle_passed'] = False
    report['limits'] = ['Synthetic RAM/caller state; no measured capture or live-view job.',
        'Host intervention at 0x60752202 and post-worklist key handoff, not an installed hook.',
        'Native CALL/RET subset, not full CPU/RTOS/ISP emulation. No external success stubs.',
        'Software constructor and executor dependencies remain unresolved; no processed JPEG.',
        'COLOR markers distinguish the slots but do not implement calibrated Gold/Portra.']
    args.out.mkdir(parents=True)
    (args.out/'results.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(out=str(args.out), complete_worklist_pairs=len(routes),
          color_call_chains=len(report['color_call_chains']),
          executor_attempts=[{k: e[k] for k in ('key', 'kind', 'selector')} |
              {'boundary': e['execution']['result'], 'completed_entries': e['execution']['completed_entries']}
              for e in executions],
          constructor_attempt=report['constructor_attempt'], full_pixel_cycle_passed=False)))


if __name__ == '__main__':
    main()
