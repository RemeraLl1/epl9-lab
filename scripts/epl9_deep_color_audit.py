"""Read-only deep color audit of exact E-PL9 1.1/build 1101.

Listings and synthetic execution are offline evidence, never a firmware patch.
"""

from mn103_tooling import default_reader, verify_reader
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess

from epl9_art_probe import BASE, ROOT
from epl9_color_audit import MAIN_SHA, STOCK_SHA
from epl9_offline_prototype import header, REQUEST, CONTEXT, OUTPUT, OBJECT, TABLE, SP, STACK
from mn103_subset import parse_listing, Region, Memory
from mn103_calls import CallMachine

WINDOWS = {
    'matrix_helpers': (0x6079bc7c, 0x6079bf86),
    'matrix_candidate': (0x6079bf86, 0x6079c0a2),
    'six_axis_candidate': (0x6079cdb0, 0x6079d26c),
    'rgb_gamma_candidate': (0x6079d7da, 0x6079dc23),
    'rgb_gamma_selectors': (0x6079d26c, 0x6079d7da),
    'chroma_candidate': (0x6079e14b, 0x6079e50e),
    'tone_selection': (0x6079ed15, 0x6079f3d2),
    'chroma_suppression_candidate': (0x6079f40f, 0x6079f915),
    'ordinary_pipeline': (0x6079fb88, 0x6079fc39),
    'request_constructor': (0x6074f225, 0x6074f5db),
    'tone_control_helpers': (0x60749cbd, 0x6074a5b2),
    'format_helpers': (0x607a3c9e, 0x607a3df6),
    'six_axis_packer': (0x6079cd40, 0x6079cdb0),
}
RETURN = 0x0badf00d
SAMPLE_KNOTS = (0, 16, 32, 64, 128, 160, 192, 224, 255)
EXPECTED = {
    0x6079fc1c: ('call', ['0x6079f309', '[d2,d3,a2,a3]', '32']),
    0x6079d394: ('ret', ['[d2,d3,a2,a3]', '28']),
    0x6079d7b0: ('mov', ['a1', '(a0)']),
    0x6079d7b2: ('mov', ['d1', '(4,a0)']),
    0x6079d7b5: ('mov', ['d2', '(8,a0)']),
    0x6079f320: ('mov', ['(8,a0)', 'd0']),
    0x6079f325: ('mov', ['d0', '(2608,a0)']),
    0x6079f347: ('call', ['0x6079f2a9', '[d2,a2,a3]', '20']),
    0x6079f3bb: ('call', ['0x6074a322', '[d2,d3,a2,a3]', '16']),
    0x6074f462: ('movbu', ['(4752,a3)', 'd0']),
    0x6074f466: ('movbu', ['d0', '(1796,a2)']),
    0x6074f45a: ('movbu', ['(4751,a3)', 'd0']),
    0x6074f45e: ('movbu', ['d0', '(1795,a2)']),
    0x6079cd4c: ('mov', ['d1', '(100,a0)']),
    0x6079cd91: ('mov', ['d1', '(120,a0)']),
    0x6079c03a: ('mov', ['d1', '(a0)']),
}


def checked_image(data):
    if len(data) != 26214336 or hashlib.sha256(data).hexdigest() != MAIN_SHA:
        raise ValueError('requires exact E-PL9 1.1/build 1101 decoded main')


def checked_output(path):
    if path.exists() or not path.resolve().is_relative_to((ROOT / 'local').resolve()):
        raise ValueError('requires a new output directory inside ignored local/')


def curve_summary(data, offset, maximum):
    if offset < 0 or offset + 512 > len(data):
        raise ValueError('curve outside image/buffer')
    values = struct.unpack_from('<256H', data, offset)
    if max(values) > maximum:
        raise ValueError('curve outside declared output range')
    return dict(samples={str(k): values[k] for k in SAMPLE_KNOTS},
                minimum=min(values), maximum=max(values),
                monotone=all(a <= b for a, b in zip(values, values[1:])),
                sha256=hashlib.sha256(data[offset:offset+512]).hexdigest())


def unchanged_outside(before, after, spans):
    return len(before) == len(after) and all(
        a == b or any(start <= i < stop for start, stop in spans)
        for i, (a, b) in enumerate(zip(before, after)))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def synthetic(image, code, key=11, flags=2):
    request, context, output = bytearray(1876), bytearray(128), bytearray(5200)
    obj, table = bytearray(32), bytearray(2048)
    request[8:12] = header(key)
    struct.pack_into('<H', request, 14, 0x0200)
    struct.pack_into('<H', request, 28, 0x0100)
    for offset, value in ((4, REQUEST), (12, OUTPUT), (52, key), (60, flags)):
        struct.pack_into('<I', context, offset, value)
    regs = dict(sp=SP, a0=CONTEXT, d2=0x22222222, d3=0x33333333,
                a2=0xaaaa2222, a3=0xaaaa3333)
    memory = Memory([Region(BASE, image, False, 'stock'),
                     Region(STACK, bytearray(0x2000), True, 'stack'),
                     Region(REQUEST, request, False, 'request'),
                     Region(CONTEXT, context, True, 'context'),
                     Region(OUTPUT, output, True, 'output'),
                     Region(OBJECT, obj, False, 'synthetic parameter object'),
                     Region(TABLE, table, False, 'synthetic table/input')])
    return CallMachine(code, memory, regs), request, context, output, obj, table


def execute(m, entry, mask, frame):
    saved = {r: m.r[r] for r in m.saved(mask)}
    result = m.run(m.enter(entry, RETURN, mask, frame), [RETURN])
    require(result.get('pc') == RETURN and result['status'] == 'stop', f'incomplete native chain: {result}')
    require(m.r['sp'] == SP and all(m.r[r] == v for r, v in saved.items()), 'call-frame/register mismatch')
    return dict(instructions=result['instructions'], calls=len(m.events), returned=True)


def exercise(image, code):
    results = dict(contrast=[], tone_controls=[], gamma_selection=[],
                   custom_object=[], matrix=[], six_axis=[])
    # Independent observed pointer oracle, not inferred from the result curves.
    contrast_pointers = {-2: 0x608d05ee, -1: 0x608cf9ee, 0: 0x608cf3ee,
                         1: 0x608cf7ee, 2: 0x608d07ee}
    for contrast, expected in contrast_pointers.items():
        m, r, c, o, j, t = synthetic(image, code)
        r[1795] = contrast & 255
        before = bytes(o)
        execution = execute(m, 0x6079f309, 0xf0, 32)
        pointer = struct.unpack_from('<I', o, 2608)[0]
        require(pointer == expected, 'unexpected contrast LUT')
        require(unchanged_outside(before, o, [(4, 8), (2608, 2612)]), 'tone wrote unrelated output')
        summary = curve_summary(image, pointer-BASE, 1023)
        require(summary['monotone'], 'stock contrast curve is not monotone')
        results['contrast'].append(dict(contrast=contrast, pointer=hex(pointer), **summary, **execution))
    for slot, family, knot in ((2, 'highlights_response', 192),
                               (3, 'midtones_response', 128), (4, 'shadows_response', 32)):
        for value in (-7, -3, 3, 7):
            m, r, c, o, j, t = synthetic(image, code)
            struct.pack_into('<I', r, 1512, TABLE)
            struct.pack_into('<h', t, slot*2, value)
            m.r.update(a0=TABLE, a1=CONTEXT+64)
            before_context = bytes(c)
            scaling = execute(m, 0x6074a061, 0, 16)
            require(unchanged_outside(before_context, c, [(64, 80)]), 'tone scaling wrote unrelated context')
            before = bytes(o)
            m.r['a0'] = CONTEXT
            execution = execute(m, 0x6079f309, 0xf0, 32)
            require(struct.unpack_from('<I', o, 2608)[0] == OUTPUT+2612, 'tone did not use owned curve buffer')
            require(unchanged_outside(before, o, [(4, 8), (2608, 3124)]), 'tone bend wrote unrelated output')
            summary = curve_summary(o, 2612, 1023)
            require(summary['monotone'] and summary['samples']['0'] == 0
                    and summary['samples']['255'] == 1023, 'invalid tone curve endpoints/order')
            base_value = struct.unpack_from('<H', image, 0x608cf3ee-BASE+2*knot)[0]
            require((summary['samples'][str(knot)]-base_value)*value > 0, 'unexpected tone-control direction')
            results['tone_controls'].append(dict(halfword=slot, family=family, value=value,
                                                 scaling=scaling, **summary, **execution))
    for key in (1, 2, 3, 4, 5, 8, 10, 11, 0x01010078, 0x01020078, 0x01010079):
        m, r, c, o, j, t = synthetic(image, code, key)
        m.r.update(a0=REQUEST, a1=OUTPUT+4000, d0=OUTPUT+4004, d1=OUTPUT+4008)
        before = bytes(o)
        execution = execute(m, 0x6079d328, 0xf0, 28)
        pointers = struct.unpack_from('<3I', o, 4000)
        expected = (0x608c63e4, 0x608c65e4, 0x608c67e4) if key == 0x01010079 else (0x608c37e4,)*3
        require(pointers == expected, 'unexpected stock gamma selection')
        require(unchanged_outside(before, o, [(4000, 4012)]), 'gamma selector wrote unrelated output')
        results['gamma_selection'].append(dict(key=hex(key), pointers=[hex(p) for p in pointers],
            curves=[curve_summary(image, p-BASE, 4095) for p in pointers], **execution))
    # A shared override object's +0 supplies a single gamma curve; +8 supplies
    # an independent tone curve. This does not magically expose three overrides.
    for variant in (0, 1):
        m, r, c, o, j, t = synthetic(image, code, flags=0)
        struct.pack_into('<I', r, 1524, OBJECT)
        struct.pack_into('<I', j, 0, TABLE)
        struct.pack_into('<I', j, 8, TABLE+512)
        j[28] = variant
        struct.pack_into('<256H', t, 0, *(round(i*4095/255) for i in range(256)))
        struct.pack_into('<256H', t, 512, *(round(i*1023/255) for i in range(256)))
        m.r.update(a0=REQUEST, a1=OUTPUT+4000, d0=OUTPUT+4004, d1=OUTPUT+4008)
        before = bytes(o)
        gamma = execute(m, 0x6079d328, 0xf0, 28)
        pointers = struct.unpack_from('<3I', o, 4000)
        require(pointers == ((TABLE,)*3 if variant == 0 else (0x608c37e4,)*3), 'gamma variant guard mismatch')
        m.r['a0'] = CONTEXT
        tone = execute(m, 0x6079f309, 0xf0, 32)
        require(struct.unpack_from('<I', o, 2608)[0] == TABLE+512, 'custom tone pointer not propagated')
        require(unchanged_outside(before, o, [(4000, 4012), (2608, 2612)]), 'override wrote unrelated output')
        results['custom_object'].append(dict(variant=variant, gamma=gamma, tone=tone,
            gamma_accepted=variant == 0, tone_accepted=True, pixel_consumption_tested=False))
    # Exercise the stock setter with three deliberately distinct valid pointers.
    m, r, c, o, j, t = synthetic(image, code)
    pointers = (TABLE, TABLE+512, TABLE+1024)
    for n in range(3):
        struct.pack_into('<256H', t, n*512, *(round(i*4095/255) for i in range(256)))
    m.r.update(a0=OUTPUT, a1=pointers[0], d0=pointers[1], d1=pointers[2])
    before = bytes(o)
    result = execute(m, 0x6079d7a0, 0xa0, 8)
    expected = bytearray(before)
    struct.pack_into('<I', expected, 4, struct.unpack_from('<I', before, 4)[0] & ~4096)
    struct.pack_into('<3I', expected, 2596, *pointers)
    require(o == expected, 'three-channel pointer setter full output mismatch')
    results['independent_gamma_setter'] = dict(**result, full_output_bytes_checked=len(o),
        pointers=[hex(p) for p in pointers], hardware_consumption_tested=False)
    for marker in (False, True):
        m, r, c, o, j, t = synthetic(image, code)
        source = [128, 10, -6, 8, 128, -4, -2, 6, 128] if marker else [128, 0, 0, 0, 128, 0, 0, 0, 128]
        struct.pack_into('<9h', t, 0, *source)
        m.r.update(a0=OUTPUT+80, a1=TABLE, d0=11, d1=0)
        before = bytes(o)
        result = execute(m, 0x6079bf86, 0xf0, 84)
        matrix = struct.unpack_from('<9h', o, 80)
        expected = (124, 10, -6, 8, 124, -4, -2, 6, 124) if marker else tuple(source)
        require(matrix == expected, 'matrix normalization mismatch')
        require(unchanged_outside(before, o, [(80, 100)]), 'matrix wrote unrelated output')
        results['matrix'].append(dict(marker=marker, input=source, output=list(matrix),
                                     row_sums=[sum(matrix[n:n+3]) for n in (0, 3, 6)], **result))
    for key in (1, 2, 3, 4, 11, 0x01010078, 0x01020078):
        m, r, c, o, j, t = synthetic(image, code, key)
        before = bytes(o)
        result = execute(m, 0x6079cdb0, 0xf0, 100)
        require(unchanged_outside(before, o, [(100, 124)]), 'six-axis stage wrote unrelated output')
        results['six_axis'].append(dict(key=hex(key), coefficients=list(struct.unpack_from('<12h', o, 100)), **result))
    require(len({tuple(row['coefficients']) for row in results['six_axis']}) >= 4,
            'six-axis presets did not differ')
    results['component_cases'] = sum(len(results[k]) for k in ('contrast', 'tone_controls', 'gamma_selection',
                                                               'custom_object', 'matrix', 'six_axis')) + 1
    return results


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--image', type=Path, default=ROOT / 'local/epl9-1101-analysis/decoded/00_0100_406e0020.decoded.bin')
    p.add_argument('--reader', type=Path, default=default_reader())
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    checked_output(args.out)
    data = bytearray(args.image.read_bytes())
    checked_image(data)
    listings, code = {}, {}
    for name, (start, stop) in WINDOWS.items():
        verify_reader(args.reader)
        result = subprocess.run([str(args.reader.resolve()), str(args.image.resolve()),
                                 hex(BASE), hex(start-BASE), hex(stop-BASE)],
                                check=True, text=True, capture_output=True)
        parsed = parse_listing(result.stdout, data, BASE)
        for at, instruction in parsed.items():
            if at in code and code[at] != instruction:
                raise ValueError(f'conflicting instruction at {at:#x}')
        code.update(parsed)
        listings[name] = result.stdout
    for address, expected in EXPECTED.items():
        require(address in code and code[address][1:] == expected, f'instruction anchor mismatch at {address:#x}')
    experiments = exercise(data, code)
    checked_image(data)
    report = dict(model='Olympus E-PL9', displayed_version='1.1 (owner reported)',
                  main_build='1101', stock_container_bytes=104552480,
                  stock_container_sha256=STOCK_SHA,
                  container_note='Identity carried from prior audit; decoded main is read here.',
                  input_bytes=len(data), input_sha256=MAIN_SHA,
                  reader_sha256=verify_reader(args.reader),
                  script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  dependencies={name: hashlib.sha256((ROOT/'scripts'/name).read_bytes()).hexdigest()
                                for name in ('mn103_subset.py', 'mn103_calls.py', 'epl9_offline_prototype.py')},
                  candidate_base=hex(BASE), decoded_instructions=len(code),
                  instruction_anchors=len(EXPECTED), experiments=experiments,
                  limits=['Synthetic caller state; component configuration only.',
                          'No ISP/MMIO execution, pixel model, preview/JPEG or native firmware hook.',
                          'No complete frame, cache invalidation or parameter-object lifetime validation.',
                          'Processing-key names remain inferred until mapped on the camera.'],
                  windows={k: [hex(v) for v in window] for k, window in WINDOWS.items()},
                  camera_accessed=False, firmware_modified=False)
    args.out.mkdir(parents=True)
    for name, listing in listings.items():
        (args.out / (name+'.tsv')).write_text(listing, encoding='utf-8')
    (args.out / 'audit.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(out=str(args.out), instructions=len(code),
                          anchors=len(EXPECTED), component_cases=experiments['component_cases'],
                          camera_accessed=False, firmware_modified=False), indent=2))


if __name__ == '__main__':
    main()
