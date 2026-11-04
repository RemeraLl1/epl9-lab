"""Execute bounded decoded E-PL9 sections with synthetic state; never patch files."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess

from epl9_art_routing_probe import BASE, ROOT, MAIN_SHA, STOCK_SHA, WINDOWS, EXPECTED
from mn103_subset import Machine, Memory, Region, parse_listing

JOB, STACK, REQUEST, CONTEXT, OUTPUT, TABLE, OBJECT = [0x10000000 + i * 0x10000 for i in range(7)]
SP = STACK + 0x800
TABLE_SIZE = 3028
RECIPES = {0x01010078: 'gold200', 0x01020078: 'portra400'}


def header(key):
    return bytes([key >> 24, (key >> 16) & 255]) + struct.pack('<H', key & 65535)


def machine(image, code, regions, registers=None):
    return Machine(code, Memory([Region(BASE, bytearray(image), False, 'stock'),
                                Region(STACK, bytearray(0x1000), True, 'stack'), *regions]),
                   {'sp': SP, **(registers or {})})


def route(image, code, key, job_type=0x0200, selector=0, replacement=False,
          flags=0, legacy=False, return_job=False):
    recipe = RECIPES.get(key) if replacement else None
    effective = 11 if recipe else key
    job = bytearray(14552)
    routing_key = effective if legacy else key
    job[12:16] = header(routing_key)
    struct.pack_into('<I', job, 16, flags)
    struct.pack_into('<H', job, 20, job_type)
    job[25] = selector
    struct.pack_into('<I', job, 10384, routing_key)
    struct.pack_into('<I', job, 10060, 0x6075199d)
    m = machine(image, code, [Region(JOB, job, True, 'job')],
                {'d2': 1, 'a3': JOB + 10060})
    for offset, value in [(4, JOB), (8, JOB+16), (12, JOB+4), (16, JOB+10384)]:
        m.memory.write(SP+offset, value, 4)
    # Keep the original mode through its type checks. Intervene only at the
    # first actual Watercolor pass, never in the already-short continuation.
    result = m.run(0x60751eb2, [0x60752202] if recipe and not legacy else [])
    redirected = result['status'] == 'stop'
    if redirected:
        result = m.run(0x607523a5)
    if result['status'] != 'ret_boundary' or result['pc'] != 0x60752912:
        raise ValueError(f'worklist did not reach its return: {result}')
    count = m.memory.read(JOB + 10390, 2)
    if not 0 < count <= 16:
        raise ValueError('invalid worklist count')
    entries = [list(struct.unpack_from('<3I', job, 10060 + i*12)) for i in range(count)]
    # Host-only handoff: do not expose mismatched header/cache to a consumer.
    job[12:16] = header(effective)
    struct.pack_into('<I', job, 10384, effective)
    report = {'key': hex(key), 'effective_key': hex(effective), 'recipe': recipe,
            'flags': hex(flags), 'redirected': redirected, 'legacy': legacy,
            'job_type': hex(job_type), 'selector': selector, 'entries': entries,
            'entry_functions': [hex(e[0]) for e in entries], **result,
            'trace': [hex(pc) for pc in m.trace]}
    return (report, job) if return_job else report


def copy_header(image, code, key):
    job, request = bytearray(14552), bytearray(20)
    job[12:16] = header(key)
    struct.pack_into('<H', job, 20, 0x0200)
    m = machine(image, code, [Region(JOB, job), Region(REQUEST, request, True)],
                {'a0': JOB, 'a1': REQUEST})
    result = m.run(0x6074f225)
    assert result['status'] == 'retf_boundary'
    assert request[8:12] == header(key)
    assert request[12:16] == bytes.fromhex('00000002')
    return result


def select_color(image, code, key, custom=False, enabled=False, late=False):
    request, context, output, obj = bytearray(1876 if not late else 708), bytearray(112), bytearray(5200), bytearray(20)
    request[8:12] = header(key)
    struct.pack_into('<I', context, 4, REQUEST)
    struct.pack_into('<I', context, 12, OUTPUT)
    struct.pack_into('<I', context, 52, key)
    struct.pack_into('<I', context, 60, 0x10000000 if enabled else 0)
    if custom:
        struct.pack_into('<I', request, 1524, OBJECT)
        struct.pack_into('<I', obj, 16, TABLE)
    m = machine(image, code, [Region(REQUEST, request), Region(CONTEXT, context, True),
                Region(OUTPUT, output, True), Region(OBJECT, obj),
                Region(TABLE, bytearray(image[0x4ee340:0x4ee340+TABLE_SIZE]))], {'a0': CONTEXT})
    result = m.run(0x6079ecbf if late else 0x6079ebcc)
    result['target'] = result['operands'][0] if result['status'] == 'call_boundary' else None
    result['registers_at_boundary'] = dict(m.r)
    return result


def build_color(image, code, saturation=None, full=False, overrides=()):
    saturation = [0]*12 if saturation is None else saturation
    table = bytearray(image[0x4ee340:0x4ee340+TABLE_SIZE])
    for record, field, value in overrides:
        if not 0 <= record < 12 or field not in (12, 14, 16):
            raise ValueError('invalid synthetic table edit')
        struct.pack_into('<h', table, 28*record+field, value)
    output = bytearray(5200)
    regs = {'a0': TABLE, 'a1': OUTPUT if full else REQUEST,
            'd0': struct.unpack_from('<H', table, 3024)[0], 'd1': OUTPUT}
    m = machine(image, code, [Region(TABLE, table), Region(REQUEST, bytearray(struct.pack('<12b', *saturation))),
                              Region(OUTPUT, output, True)], regs)
    result = m.run(0x6079e50e if full else 0x6079e9e2)
    assert result['status'] in ('ret_boundary', 'retf_boundary'), result
    return output, table, result


def check_packing(output, table, saturation_values, *, initial=None, table_address=TABLE):
    """Independent field-layout oracle; no instruction interpretation."""
    expected = bytearray(5200) if initial is None else bytearray(initial)
    if len(expected) != 5200 or len(output) != 5200:
        raise ValueError('complete 5200-byte output and initial state required')
    for record in range(12):
        source, dest = record*28, 688+record*24
        expected[dest:dest+12] = table[source:source+12]
        expected[dest+12:dest+16] = table[source+20:source+24]
        expected[dest+16:dest+18] = table[source+24:source+26]
        expected[dest+18:dest+20] = table[source+12:source+14]
        struct.pack_into('<h', expected, dest+20, saturation_values[record])
        expected[dest+22:dest+24] = table[source+16:source+18]
    struct.pack_into('<I', expected, 976, struct.unpack_from('<H', table, 3024)[0])
    offsets = {3124:336, 3128:1680, 3132:720, 3136:1104, 3140:2064,
               3144:2448, 3148:1296, 3152:2640, 3156:1488, 3160:2832}
    for dest, relative in offsets.items():
        struct.pack_into('<I', expected, dest, table_address+relative)
    if output != expected:
        mismatches = [i for i, (a, b) in enumerate(zip(output, expected)) if a != b]
        raise ValueError(f'color packing mismatch at {mismatches[:12]}')


def run_experiments(image, code, fixture):
    results, routes = {}, []
    watercolor_functions = {0x60754834, 0x60754944, 0x60754a4b, 0x60754ba6}
    for key in [0x01010078, 0x01020078, 1, 11, 0x01030078]:
        for kind in [0x0200, 0x0100, 0x0040]:
            for selector in [0, 2]:
                stock = route(image, code, key, kind, selector)
                proposed = route(image, code, key, kind, selector, True)
                if key in RECIPES:
                    reference = route(image, code, 11, kind, selector) if kind == 0x0200 else stock
                    assert proposed['entries'] == reference['entries']
                    assert not watercolor_functions.intersection(e[0] for e in proposed['entries'])
                    assert proposed['recipe'] == RECIPES[key]
                    if kind == 0x0200:
                        assert {0x60754834, 0x60754944}.issubset(e[0] for e in stock['entries'])
                else:
                    assert stock['entries'] == proposed['entries']
                    assert proposed['recipe'] is None
                routes.append({'stock': stock, 'prototype': proposed})
    results['routes'] = routes
    results['already_ordinary_schedule_changes'] = [
        {'key': item['stock']['key'], 'job_type': item['stock']['job_type'],
         'selector': item['stock']['selector']}
        for item in routes
        if item['prototype']['recipe'] and
        not watercolor_functions.intersection(e[0] for e in item['stock']['entries']) and
        item['stock']['entries'] != item['prototype']['entries']]
    assert not results['already_ordinary_schedule_changes']
    results['legacy_already_ordinary_schedule_changes'] = [
        {'key': hex(key), 'job_type': hex(kind), 'selector': selector}
        for key in RECIPES for kind in (0x0100, 0x0040) for selector in (0, 2)
        if route(image, code, key, kind, selector)['entries'] !=
        route(image, code, key, kind, selector, True, legacy=True)['entries']]
    assert len(results['legacy_already_ordinary_schedule_changes']) == 4
    flag_cases = []
    for flags in [0] + [1 << bit for bit in range(32)] + [0x30000, 0x60000]:
        for key in [*RECIPES, 1, 11, 0x01030078]:
            for kind in (0x0200, 0x0100, 0x0040):
                for selector in (0, 2):
                    stock = route(image, code, key, kind, selector, flags=flags)
                    proposed = route(image, code, key, kind, selector, True, flags)
                    expected = (route(image, code, 11, kind, selector, flags=flags)
                                if proposed['redirected'] else stock)
                    assert proposed['entries'] == expected['entries'], (key, kind, selector, flags)
                    assert not proposed['recipe'] or not watercolor_functions.intersection(
                        e[0] for e in proposed['entries'])
                    flag_cases.append({k: proposed[k] for k in ('key', 'job_type', 'selector',
                                      'flags', 'redirected', 'entries')})
    results['flag_route_cases'] = flag_cases
    results['header_copy'] = [copy_header(image, code, k) for k in (0x01010078, 0x01020078, 11)]
    selection = {
        'ordinary_color': select_color(image, code, 11),
        'late_color': select_color(image, code, 11, late=True),
        'custom_enabled': select_color(image, code, 11, custom=True, enabled=True),
        'custom_without_flag': select_color(image, code, 11, custom=True),
    }
    assert selection['ordinary_color']['target'] == '0x6079e9e2'
    assert selection['late_color']['target'] == '0x6079ebc1'
    assert selection['custom_enabled']['target'] == '0x6079e50e'
    assert selection['custom_without_flag']['target'] is None
    assert selection['custom_enabled']['registers_at_boundary']['a0'] == TABLE
    results['selection'] = selection
    # An inconsistent cache-only rewrite still leaves the original request key.
    results['cache_only_negative'] = select_color(image, code, 0x01010078)
    assert results['cache_only_negative']['target'] != '0x6079e9e2'
    numeric = []
    neutral, table, info = build_color(image, code)
    check_packing(neutral, table, [0]*12)
    # Predictions from the independent, pinned PEN-F/Workspace investigation;
    # equality is tested, never assumed from the shared stock table alone.
    for row in fixture['saturation']:
        index, value = row['input_index'], row['input_value']
        inputs = [0]*12
        inputs[index] = value
        output, table, execution = build_color(image, code, inputs)
        record = (index % 2)*6 + index//2
        expected = [0]*12
        expected[record] = int(row['camera_static_prediction'])
        check_packing(output, table, expected)
        numeric.append({'input_index': index, 'input': value, 'record': record,
                        'coefficient': expected[record], **execution})
    full_tests = []
    for edits in [(), [(r, f, (r-6)*scale) for r in range(12)
                       for f, scale in [(12, 1000), (14, 50), (16, 25)]]]:
        output, table, execution = build_color(image, code, full=True, overrides=edits)
        check_packing(output, table, [struct.unpack_from('<h', table, r*28+14)[0] for r in range(12)])
        full_tests.append({'overrides': edits, **execution})
    # Distinct diagnostic markers, deliberately NOT Gold/Portra film recipes.
    marker_outputs = {}
    for name, inputs in [('gold200_slot', [1]+[0]*11), ('portra400_slot', [0,-1]+[0]*10)]:
        output, _, _ = build_color(image, code, inputs)
        marker_outputs[name] = hashlib.sha256(output).hexdigest()
    assert len(set(marker_outputs.values())) == 2
    results.update(neutral_builder=info, saturation_cases=numeric,
                   full_table_cases=full_tests, diagnostic_marker_outputs=marker_outputs)
    return results


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    if not __debug__:
        p.error('run without -O: experiment assertions must remain enabled')
    if args.out.exists() or not args.out.resolve().is_relative_to((ROOT/'local').resolve()):
        p.error('output must be a new ignored local/ directory')
    image_path = ROOT/'local/epl9-1101-analysis/decoded/00_0100_406e0020.decoded.bin'
    image = image_path.read_bytes()
    if len(image) != 26214336 or hashlib.sha256(image).hexdigest() != MAIN_SHA:
        p.error('exact E-PL9 1.1/build 1101 main required')
    reader = ROOT/'local/mn103-tooling/mn103-reader.exe'
    code = {}
    for start, stop in WINDOWS.values():
        listing = subprocess.check_output([str(reader), str(image_path), hex(BASE),
                                           hex(start-BASE), hex(stop-BASE)], text=True)
        code.update(parse_listing(listing, image, BASE))
    # The existing independent anchor checks still apply to the decoder output.
    for at, expected in EXPECTED.items():
        raw, op, args_decoded = code[at]
        if op+'\t'+','.join(args_decoded) != expected:
            raise ValueError(f'anchor mismatch at {at:#x}')
    fixture_path = ROOT/'references/oly_fw_analysis/tests/fixtures/color-builder-reference.json'
    if hashlib.sha256(fixture_path.read_bytes()).hexdigest() != '00f5a3f8b95c24da4699e781ab73dc5eab3c84a3e606f558c93879e6618b447f':
        p.error('independent coefficient fixture differs from pinned input')
    fixture = json.loads(fixture_path.read_text())
    result = run_experiments(image, code, fixture)
    result['provenance'] = {'model': 'E-PL9', 'displayed_version': '1.1', 'main_build': '1101',
        'stock_bytes': 104552480, 'stock_sha256': STOCK_SHA,
        'main_bytes': len(image), 'main_sha256': MAIN_SHA, 'base': hex(BASE),
        'reader_sha256': hashlib.sha256(reader.read_bytes()).hexdigest(),
        'fixture_sha256': hashlib.sha256(fixture_path.read_bytes()).hexdigest(),
        'source_sha256': {name: hashlib.sha256((ROOT/'scripts'/name).read_bytes()).hexdigest()
                          for name in ('mn103_subset.py', 'epl9_offline_prototype.py')},
        'reference_commit': '539fcf1fa9eda5fdef8ede4deeab94a4691d94c3'}
    result['limits'] = ['Decoded-instruction subset, not GNU libsim or complete CPU.',
        'Synthetic branch-entry state; early worklist paths before 0x60751eb2 excluded.',
        'Single-bit flags and two combinations checked; not all effect combinations.',
        'CALL/RET boundaries are not executed; isolated components are not an integrated pipeline.',
        'Recipe selection/rewrite occurs in host harness, not a firmware hook.',
        'Numeric fixtures are external predictions; no E-PL9 silicon/pixel validation.',
        'Gold/Portra parameters are diagnostic markers only, not film recipes.']
    result['camera_accessed'] = result['firmware_modified'] = False
    result['ready_for_patch'] = False
    args.out.mkdir(parents=True)
    (args.out/'results.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'out': str(args.out), 'route_pairs': len(result['routes']),
                      'saturation_cases': len(result['saturation_cases']),
                      'full_table_cases': len(result['full_table_cases']),
                      'flag_route_cases': len(result['flag_route_cases']),
                      'already_ordinary_schedule_changes': len(result['already_ordinary_schedule_changes']),
                      'scoped_checks_passed': True, 'ready_for_patch': False}))


if __name__ == '__main__':
    main()
