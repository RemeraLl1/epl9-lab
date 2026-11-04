"""Exercise native color configuration with retained film-parameter bundles.

The selector intervention is host code at a declared native return boundary.
RGB shapes and matrix sources are diagnostic, not calibrated film proposals.
No firmware hook, hardware pixel engine or camera access is implemented here.
"""
import argparse
import json
from pathlib import Path
import struct
import subprocess

from epl9_workspace_bridge import (ROOT, BASE, MAIN, MAIN_SHA, COLOR_ROM,
                                   sha, validate_recipes)
from epl9_tonal_drafts import definitions, remap_curve, validate_curve, READER_SHA
from epl9_offline_prototype import (REQUEST, CONTEXT, OUTPUT, OBJECT, TABLE, SP,
                                    header, RECIPES)
from epl9_integrated_probe import native, attempt, RETURN
from mn103_subset import Fault, Region, parse_listing
from mn103_models import FillModel

RGB_RETURN = 0x6079d7f9
BUNDLE_BASE, BUNDLE_STRIDE, AUX = 0x18000000, 0x10000, 0x19000000
TONE_OFFSET, HSL_OFFSET, OBJECT_OFFSET = 0x600, 0x800, 0x2000
WINDOWS = (
    (0x60799eb6, 0x607a038d), (0x607a3bed, 0x607a476b),
    (0x60749cbd, 0x6074a5b2), (0x60749150, 0x60749187),
    (0x6073e588, 0x6073eaca), (0x6078ab39, 0x6078ac47),
    (0x60798b08, 0x60799eb6),
)
# Even off-diagonal markers avoid assigning any physical color-space meaning.
MATRICES = {
    0x01010078: (128, 4, -2, 2, 128, 0, 0, -2, 128),
    0x01020078: (128, -2, 4, 0, 128, 2, 2, 0, 128),
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def checked_output(path):
    require(not path.exists() and path.resolve().is_relative_to((ROOT/'local').resolve()),
            'output must be a new ignored local directory')


def load_code(image_path, reader):
    image = image_path.read_bytes()
    require(len(image) == 26214336 and sha(image) == MAIN_SHA, 'requires exact E-PL9 main build 1101')
    require(sha(reader.read_bytes()) == READER_SHA, 'requires inspected GNU reader')
    code, listings = {}, {}
    for start, stop in WINDOWS:
        listing = subprocess.check_output([str(reader.resolve()), str(image_path.resolve()),
            hex(BASE), hex(start-BASE), hex(stop-BASE)], text=True)
        parsed = parse_listing(listing, image, BASE)
        require(all(at not in code or code[at] == value for at, value in parsed.items()),
                'conflicting instruction windows')
        code.update(parsed)
        listings[f'{start:08x}.tsv'] = listing
    for at, expected in {
        0x6079d7f4: ('call', ['0x6079d328', '[d2,d3,a2,a3]', '28']),
        RGB_RETURN: ('movbu', ['d0', '(61,sp)']),
        0x6079d955: ('call', ['0x6079d7a0', '[d2,a2]', '8']),
        0x6079fbc8: ('call', ['0x6079d7da', '[d2,d3,a2,a3]', '220']),
        0x6079fc36: ('ret', ['[d2,d3,a2,a3]', '40']),
    }.items():
        require(code.get(at, (None,))[1:] == expected, f'instruction anchor {at:#x} mismatch')
    return image, code, listings


def invoke(m, entry, mask, frame, regs=None, stops=()):
    m.r.update(regs or {})
    saved = {name: m.r[name] for name in m.saved(mask)}
    result = attempt(m, entry, mask, frame, stops)
    if result.get('pc') == RETURN:
        require(m.r['sp'] == SP and all(m.r[k] == v for k, v in saved.items()),
                'unbalanced native frame or saved registers')
    return result


def base_request(key=11, fmt=0x200):
    require(fmt in (0x200, 0x100, 0x40), 'unqualified synthetic format')
    r = bytearray(1876)
    r[8:12] = header(key)
    struct.pack_into('<H', r, 14, fmt)
    struct.pack_into('<H', r, 28, 0x100)
    # Explicit nonzero ratio fixture; capture WB transport is not established.
    struct.pack_into('<4H', r, 1568, 256, 256, 256, 256)
    return r


def native_tone(image, code, recipe):
    r, c, o, controls = base_request(), bytearray(128), bytearray(5200), bytearray(16)
    r[1795] = recipe['picture_mode_contrast'] & 255
    struct.pack_into('<I', r, 1512, TABLE)
    for index, field in ((2, 'highlights'), (3, 'midtones'), (4, 'shadows')):
        struct.pack_into('<h', controls, index*2, recipe['tone_level'][field])
    for at, value in ((4, REQUEST), (12, OUTPUT), (52, 11), (60, 2)):
        struct.pack_into('<I', c, at, value)
    m = native(image, code, [Region(REQUEST, r), Region(CONTEXT, c, True),
        Region(OUTPUT, o, True), Region(TABLE, controls)], {})
    for entry, mask, frame, regs in (
        (0x6074a061, 0, 16, dict(a0=TABLE, a1=CONTEXT+64)),
        (0x6079f309, 0xf0, 32, dict(a0=CONTEXT)),
    ):
        result = invoke(m, entry, mask, frame, regs)
        require(result.get('pc') == RETURN, f'tone construction stopped: {result}')
    pointer = struct.unpack_from('<I', o, 2608)[0]
    require(pointer == OUTPUT+2612 or BASE <= pointer <= BASE+len(image)-512,
            'tone curve is outside its native owned/ROM storage')
    curve = b''.join(m.memory.read(pointer+n*2,2).to_bytes(2,'little') for n in range(256))
    values = struct.unpack('<256H', curve)
    require(values[0] == 0 and values[-1] == 1023 and all(a <= b for a, b in zip(values, values[1:])),
            'invalid generated tone curve')
    return curve


def make_bundle(image, code, recipe, hsl, index):
    key = int(recipe['watercolor_key'], 16)
    require(key in RECIPES and index in (0, 1), 'unqualified recipe slot')
    address = BUNDLE_BASE + index*BUNDLE_STRIDE
    r, parameter = base_request(), bytearray([0xa5])*4200
    r[1795] = recipe['picture_mode_contrast'] & 255
    before = bytes(r)
    builder = native(image, code, [Region(REQUEST, r, True), Region(OBJECT, parameter, True)],
                     {}, {0x4700111e: FillModel()})
    result = invoke(builder, 0x6078ab39, 0xb0, 36, dict(a0=REQUEST, a1=OBJECT))
    require(result.get('pc') == RETURN, f'parameter builder stopped: {result}')
    require(parameter[129:] == b'\xa5'*(4200-129), 'native builder used more than qualified header')
    require(parameter[20:24] == b'\xa5'*4, 'native builder unexpectedly owns comparison token')
    require(r[8:12] == header(2) and before[8:12] == header(11), 'private key normalization changed')
    for at in (0, 8):
        pointer = struct.unpack_from('<I', parameter, at)[0]
        require(BASE <= pointer <= BASE+len(image)-512, 'unqualified companion pointer')
    stock = struct.unpack_from('<256H', image, 0x608c37e4-BASE)
    # Distinct, mild diagnostic transfers. Slot channel order/domain is open.
    deltas = (24, 0, -32) if index == 0 else (-16, 8, 20)
    curves = [struct.pack('<256H', *remap_curve(stock,
        [[0, 0], [1024, 1024+delta], [3072, 3072-delta//2], [4095, 4095]])) for delta in deltas]
    tone = native_tone(image, code, recipe)
    table = bytearray(image[COLOR_ROM-BASE:COLOR_ROM-BASE+3028])
    for n, triplet in enumerate(hsl['native_hsl']):
        struct.pack_into('<3h', table, n*28+12, *triplet)
    # Explicit host-owned token, not a newly established native token producer.
    native_base_tone = struct.unpack_from('<I', parameter, 8)[0]
    # Precompute H/S/M once; the qualified full-chain fixture has no live controls.
    struct.pack_into('<I', parameter, 8, address+TONE_OFFSET)
    struct.pack_into('<2I', parameter, 16, address+HSL_OFFSET, index+1)
    bundle = bytearray(OBJECT_OFFSET+129)
    bundle[:1536] = b''.join(curves)
    bundle[TONE_OFFSET:TONE_OFFSET+512] = tone
    bundle[HSL_OFFSET:HSL_OFFSET+3028] = table
    bundle[OBJECT_OFFSET:] = parameter[:129]
    return dict(key=key, name=recipe['name'], address=address, data=bytes(bundle),
        pointers=tuple(address+n*512 for n in range(3)), tone=tone, hsl=hsl['native_hsl'],
        matrix=MATRICES[key], tone_fields=recipe['tone_level'],
        contrast=recipe['picture_mode_contrast'], native_builder_instructions=len(builder.trace),
        native_shared_gamma=struct.unpack_from('<I', parameter)[0], native_base_tone=native_base_tone)


def inject_gamma(m, pc, original_key, bundle):
    """Host prototype only: replace selector results, preserving flags/registers."""
    if original_key not in RECIPES:
        return False
    require(pc == RGB_RETURN and original_key == bundle['key'], 'wrong recipe or intervention boundary')
    frame = m.r['sp']
    require(m.memory.read(frame+220, 4) == 0x6079fbcd, 'unexpected native RGB-wrapper caller')
    require([m.memory.read(frame+68+n*4, 4) for n in range(3)] == [bundle['native_shared_gamma']]*3,
            'selector no longer has the qualified common-gamma results')
    pointers = bundle['pointers']
    require(len(pointers) == 3 and all(abs(a-b) >= 512 for n, a in enumerate(pointers) for b in pointers[n+1:]),
            'independent curves must have nonoverlapping 512-byte spans')
    for pointer in pointers:
        region, offset = m.memory.region(pointer, 2)
        require(not region.writable and pointer % 2 == 0 and offset+512 <= len(region.data),
                'curve must have a retained read-only 512-byte span')
        validate_curve(struct.unpack_from('<256H', region.data, offset))
    for n, pointer in enumerate(pointers):
        m.memory.write(frame+68+n*4, pointer, 4)
    return True


def tone_composition(image, code, bundle):
    cases = []
    for already_bent in (False, True):
        r, c, o, controls = base_request(), bytearray(128), bytearray(5200), bytearray(16)
        data = bytearray(bundle['data'])
        pointer = bundle['address']+TONE_OFFSET if already_bent else bundle['native_base_tone']
        struct.pack_into('<I', data, OBJECT_OFFSET+8, pointer)
        struct.pack_into('<I', r, 1524, bundle['address']+OBJECT_OFFSET)
        struct.pack_into('<I', r, 1512, TABLE)
        r[1795] = bundle['contrast'] & 255
        for index, field in ((2, 'highlights'), (3, 'midtones'), (4, 'shadows')):
            struct.pack_into('<h', controls, index*2, bundle['tone_fields'][field])
        for at, value in ((4, REQUEST), (12, OUTPUT), (52, 11), (60, 2)):
            struct.pack_into('<I', c, at, value)
        m = native(image, code, [Region(REQUEST, r), Region(CONTEXT, c, True),
            Region(OUTPUT, o, True), Region(TABLE, controls), Region(bundle['address'], bytes(data))], {})
        scaled = invoke(m, 0x6074a061, 0, 16, dict(a0=TABLE, a1=CONTEXT+64))
        require(scaled.get('pc') == RETURN, 'tone composition scaling failed')
        result = invoke(m, 0x6079f309, 0xf0, 32, dict(a0=CONTEXT))
        require(result.get('pc') == RETURN and struct.unpack_from('<I', o, 2608)[0] == OUTPUT+2612,
                'H/S/M did not copy/bend the object tone into the owned output buffer')
        require((bytes(o[2612:3124]) == bundle['tone']) == (not already_bent),
                'unexpected single/double tone composition')
        cases.append(dict(already_bent_object=already_bent, matches_once_bent_recipe=not already_bent,
            curve_sha256=sha(o[2612:3124]), instructions=len(m.trace)))
    return dict(name=bundle['name'], native_base_tone=hex(bundle['native_base_tone']),
        hsm_applies_after_object_selection=True, cases=cases, pixel_processing_executed=False)


def matrix_oracle(source):
    require(len(source) == 9 and all(type(v) is int and -64 <= v <= 192 for v in source),
            'matrix outside diagnostic bounds')
    out = list(source)
    out[1] &= ~1
    if (out[3]+out[5]) & 1:
        out[3] &= ~1
        out[5] &= ~1
    out[7] &= ~1
    for start in (0, 3, 6):
        out[start+start//3] = 128 - sum(out[start+n] for n in range(3) if n != start//3)
    return tuple(out)


def pipeline(image, code, bundles, selected, fmt=0x200, hook=True, state=None, dirty=True,
             original_key=None, live_tone=False, processing_key=11):
    require(processing_key in (11,selected['key']), 'incoherent processing identity')
    r, c, controls = base_request(processing_key,fmt), bytearray(128), bytearray(16)
    output, aux = state if state is not None else (bytearray(5200), bytearray(6000))
    struct.pack_into('<I', r, 1484, AUX)
    struct.pack_into('<I', r, 1524, selected['address']+OBJECT_OFFSET)
    if live_tone:
        struct.pack_into('<I', r, 1512, TABLE)
    r[1795] = selected['contrast'] & 255
    for index, field in ((2, 'highlights'), (3, 'midtones'), (4, 'shadows')):
        struct.pack_into('<h', controls, index*2, selected['tone_fields'][field])
    struct.pack_into('<9h', r, 1592, *selected['matrix'])
    for at, value in ((4, REQUEST), (12, OUTPUT), (52, processing_key), (60, 0x10000000 if dirty else 0)):
        struct.pack_into('<I', c, at, value)
    original_key = selected['key'] if original_key is None else original_key
    bundle_regions = []
    for bundle in bundles:
        data = bundle['data']
        if live_tone and bundle['key'] == selected['key']:
            data = bytearray(data)
            struct.pack_into('<I', data, OBJECT_OFFSET+8, selected['native_base_tone'])
            data = bytes(data)
        bundle_regions.append(Region(bundle['address'], data))
    regions = [Region(REQUEST, r), Region(CONTEXT, c, True), Region(OUTPUT, output, True),
        Region(AUX, aux, True), Region(TABLE, controls), *bundle_regions]
    m = native(image, code, regions, dict(a0=CONTEXT))
    if live_tone:
        scaled = invoke(m, 0x6074a061, 0, 16, dict(a0=TABLE, a1=CONTEXT+64))
        require(scaled.get('pc') == RETURN, 'full pipeline H/S/M scaling failed')
    m.r['a0'] = CONTEXT
    saved = {name: m.r[name] for name in m.saved(0xf0)}
    result = invoke(m, 0x6079fb88, 0xf0, 40, stops=[RGB_RETURN])
    require(result.get('pc') == RGB_RETURN, f'pipeline stopped before gamma handoff: {result}')
    injected = inject_gamma(m, result['pc'], original_key, selected) if hook else False
    try:
        result = m.run(RGB_RETURN, [RETURN])
    except Fault as error:
        raise ValueError(f'{selected["name"]}, format {fmt:#x}: {error}; '
                         f'last calls={m.events[-5:]}; tone inputs={list(struct.unpack_from("<8h", c, 64))}') from error
    require(result.get('pc') == RETURN and m.r['sp'] == SP and all(m.r[k] == v for k, v in saved.items()),
            f'complete color configuration did not return: {result}')
    pointers = struct.unpack_from('<3I', output, 2596)
    require(pointers == (selected['pointers'] if injected else (selected['native_shared_gamma'],)*3),
            'final gamma pointers changed downstream')
    tone_pointer = OUTPUT+2612 if live_tone else selected['address']+TONE_OFFSET
    require(struct.unpack_from('<I', output, 2608)[0] == tone_pointer, 'recipe tone pointer did not survive')
    if live_tone:
        require(bytes(output[2612:3124]) == selected['tone'], 'native H/S/M tone did not survive')
    require(struct.unpack_from('<9h', output, 80) == matrix_oracle(selected['matrix']), 'matrix packing mismatch')
    require([list(struct.unpack_from('<3h', output, 688+n*24+18)) for n in range(12)] == selected['hsl'],
            'HSL coefficients lost through complete pipeline')
    record = dict(name=selected['name'], original_key=hex(original_key), input_format=hex(fmt),
        injected=injected, dirty=dirty, native_return=True, instructions=len(m.trace),
        gamma_pointers=[hex(v) for v in pointers], tone_pointer=hex(tone_pointer),
        matrix=list(struct.unpack_from('<9h', output, 80)), hsl_triplets_equal=True,
        gamma_setter_calls=m.trace.count(0x6079d7a0), output_sha256=sha(output),
        gamma_cache_hit=0x6079d98d in m.trace,
        captured_wb_transport_verified=False, pixel_processing_executed=False)
    return record, bytes(output), (output, aux)


def exercise(image, code, bundles):
    reports = []
    for selected in bundles:
        for fmt in (0x200, 0x100, 0x40):
            stock, before, _ = pipeline(image, code, bundles, selected, fmt, hook=False)
            modified, after, state = pipeline(image, code, bundles, selected, fmt)
            expected = bytearray(before)
            struct.pack_into('<3I', expected, 2596, *selected['pointers'])
            require(after == expected, 'gamma intervention changed unrelated configuration bytes')
            modified['full_configuration_oracle_bytes'] = len(after)
            warm, warm_output, _ = pipeline(image, code, bundles, selected, fmt, state=state, dirty=False)
            require(warm_output == after,
                    f'unchanged immutable recipe produced a different configuration: {warm}; '
                    f'different offsets={[i for i, (a, b) in enumerate(zip(warm_output, after)) if a != b][:24]}')
            reports.extend((stock, modified, warm))
    # Same state, different retained bundle addresses; the gamma cache must rebuild.
    first, _, state = pipeline(image, code, bundles, bundles[0], 0x40)
    warm, _, state = pipeline(image, code, bundles, bundles[0], 0x40, state=state, dirty=False)
    require(warm['gamma_cache_hit'] and warm['gamma_setter_calls'] == 0, 'eligible warm gamma cache did not hit')
    changed, _, state = pipeline(image, code, bundles, bundles[1], 0x40, state=state)
    require(changed['gamma_setter_calls'] == 1, 'recipe switch failed to rebuild gamma pointers')
    reports.append(dict(kind='retained_recipe_switch', before=first, warm=warm, after=changed))
    for control in (1, 11, 0x01030078, 0x01010079):
        _, before, _ = pipeline(image, code, bundles, bundles[0], hook=False, original_key=control)
        row, after, _ = pipeline(image, code, bundles, bundles[0], original_key=control)
        require(not row['injected'] and after == before, 'non-target identity was modified')
        row['control_identity_only'] = True  # Effective processing fixture remains key 11.
        row['full_configuration_oracle_bytes'] = len(after)
        reports.append(row)
    return reports


def live_control_checks(image, code, bundles):
    reports = []
    for selected in bundles:
        for fmt in (0x200, 0x100, 0x40):
            row, _, _ = pipeline(image, code, bundles, selected, fmt, live_tone=True)
            reports.append(dict(**row, completed=True, former_stop='0x60749f80',
                immediate_extension='Panasonic MULQIU zero-extension', model_or_arithmetic_bypass=False))
    return reports


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--image', type=Path, default=MAIN)
    ap.add_argument('--reader', type=Path, default=ROOT/'local/mn103-tooling/mn103-reader.exe')
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    checked_output(args.out)
    image, code, listings = load_code(args.image, args.reader)
    paths = [ROOT/'recipes/epl9-film-drafts-v0.json', ROOT/'recipes/epl9-film-drafts-v2.json']
    hsl = validate_recipes(json.loads(paths[0].read_text()))
    recipes = definitions(json.loads(paths[1].read_text()))
    by_name = {row['name']: row for row in hsl}
    bundles = [make_bundle(image, code, row, by_name[row['base_name']], i) for i, row in enumerate(recipes)]
    composition = [tone_composition(image, code, b) for b in bundles]
    results = exercise(image, code, bundles)
    live_controls = live_control_checks(image, code, bundles)
    from epl9_job_probe import cache_experiment
    cache = cache_experiment(image, code)
    require(args.image.read_bytes() == image, 'firmware changed during execution')
    args.out.mkdir()
    for name, listing in listings.items():
        (args.out/name).write_text(listing, encoding='utf-8')
    for bundle in bundles:
        (args.out/(bundle['name']+'-diagnostic-bundle.bin')).write_bytes(bundle['data'])
    report = dict(model='Olympus E-PL9', displayed_body='1.1 (owner report)', downloaded_build='1101',
        main_bytes=len(image), main_sha256=MAIN_SHA, analysis_base=hex(BASE), reader_sha256=READER_SHA,
        recipe_definition_hashes={p.name: sha(p.read_bytes()) for p in paths},
        script_sha256=sha(Path(__file__).read_bytes()),
        decoded_instructions=len(code),
        dependencies={name: sha((ROOT/'scripts'/name).read_bytes()) for name in (
            'epl9_workspace_bridge.py', 'epl9_tonal_drafts.py', 'epl9_integrated_probe.py',
            'epl9_job_probe.py', 'epl9_offline_prototype.py', 'mn103_subset.py',
            'mn103_calls.py', 'mn103_models.py')},
        host_intervention=dict(pc=hex(RGB_RETURN), compiled_firmware_hook=False),
        results=results, tone_composition=composition, active_controls=live_controls,
        cache_comparator_regression=cache,
        bundles=[dict(name=b['name'], address=hex(b['address']), bytes=len(b['data']),
            sha256=sha(b['data']), diagnostic_rgb_and_matrix=True, tone_sha256=sha(b['tone']),
            native_builder_instructions=b['native_builder_instructions']) for b in bundles],
        limits=['Synthetic caller/configuration only; no sensor data or hardware pixels.',
                'RGB slot order/domain and diagnostic matrix color space unqualified.',
                'Original recipe identity and lifetime are retained by the host, not a native owner hook.',
                'Active H/S/M now returns after manual-qualified immediate multiply; hardware is untested.',
                'WB, native callback/refcount scheduling and actual preview/capture/save remain unverified.'],
        camera_accessed=False, firmware_modified=False)
    (args.out/'results.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(out=str(args.out), pipeline_cases=len(results),
        native_tone_and_hsl=True, independent_gamma_pointers=True, hardware_pixels=False), indent=2))


if __name__ == '__main__':
    main()
