"""Prepare E-PL9 stock-tone/WB drafts for manual Workspace rendering.

The v2 default uses existing contrast/HSM and WB metadata in copies. The v1
CMIO gamma experiment is retained for reproduction of a negative pixel control.
Neither is a camera patch or an independent ISP implementation.
"""
import argparse
import io
import json
from pathlib import Path
import struct
import subprocess

from epl9_workspace_bridge import (ROOT, BASE, MAIN, MAIN_SHA, LAUREL, SLOTS,
    TABLE_BYTES, Epl9Orf, sha, library_key, decode_cmio, replace_span, prepare,
    verify_copy, validate_recipes, native_recipe_configs)

GAMMA_ROM, GAMMA_T_OFFSET = 0x608c37e4, 0xbe6
DEFAULT_RECIPES = ROOT/'recipes/epl9-film-drafts-v2.json'
BASE_RECIPES = ROOT/'recipes/epl9-film-drafts-v0.json'
READER_SHA = 'e1c9bcb2b2467a44b8f6e2b6910c9868eff6ce571c36d5b9ad41d1d8693a76ae'


def validate_curve(values):
    if len(values) != 256 or any(type(x) is not int or not 0 <= x <= 4095 for x in values):
        raise ValueError('requires 256 integer 12-bit curve entries')
    if any(a > b for a, b in zip(values, values[1:])):
        raise ValueError('curve folds backwards')


def validate_knots(knots):
    if not isinstance(knots, list) or not 2 <= len(knots) <= 32:
        raise ValueError('requires 2..32 curve knots')
    if any(not isinstance(row, list) or len(row) != 2 or
           any(type(v) is not int or not 0 <= v <= 4095 for v in row) for row in knots):
        raise ValueError('knots must be pairs of 12-bit integers')
    if knots[0][0] != 0 or knots[-1][0] != 4095:
        raise ValueError('curve knots must span the whole 12-bit input domain')
    if any(b[0] <= a[0] or b[1] < a[1] for a, b in zip(knots, knots[1:])):
        raise ValueError('knot inputs must increase strictly and outputs must be monotone')


def remap_curve(stock, knots):
    """Compose f(stock[i]), not f(i); retain the original gamma's input axis."""
    validate_curve(stock)
    validate_knots(knots)
    result, segment = [], 0
    for value in stock:
        while segment < len(knots)-2 and value > knots[segment+1][0]:
            segment += 1
        x0, y0 = knots[segment]
        x1, y1 = knots[segment+1]
        result.append(y0 + ((value-x0)*(y1-y0)+(x1-x0)//2)//(x1-x0))
    validate_curve(result)
    return result


def scale_wb(values, red, blue):
    if (len(values) != 4 or any(type(v) is not int or not 1 <= v <= 65535 for v in values)
            or any(type(v) is not int or not 850 <= v <= 1150 for v in (red, blue))):
        raise ValueError('unqualified WB vector or relative gain outside 0.85..1.15')
    scaled = ((values[0]*red+500)//1000, (values[1]*blue+500)//1000, values[2], values[3])
    if not all(1 <= x <= 65535 for x in scaled):
        raise ValueError('scaled WB gain overflows its existing field')
    return scaled


def definitions(document):
    version = {'epl9-rgb-tone-wb-drafts-v1': 1, 'epl9-stock-tone-wb-drafts-v2': 2}.get(document.get('schema'))
    if version is None:
        raise ValueError('unsupported tonal recipe schema')
    rows = document.get('recipes')
    if not isinstance(rows, list) or len(rows) != 2:
        raise ValueError('requires the two accepted recipe slots')
    expected = {f'gold200-draft-v{version}': ('gold200-draft-v0', '0x01010078'),
                f'portra400-draft-v{version}': ('portra400-draft-v0', '0x01020078')}
    seen = set()
    for row in rows:
        name = row.get('name')
        if name not in expected or name in seen or (row.get('base_name'), row.get('watercolor_key')) != expected[name]:
            raise ValueError('unqualified/duplicate recipe name or Watercolor binding')
        seen.add(name)
        if version == 1:
            validate_knots(row.get('tone_knots'))
        else:
            contrast, tone = row.get('picture_mode_contrast'), row.get('tone_level')
            if type(contrast) is not int or not -2 <= contrast <= 2:
                raise ValueError('stock contrast must be an integer in -2..2')
            if not isinstance(tone, dict) or set(tone) != {'highlights', 'shadows', 'midtones'}:
                raise ValueError('requires the three explicit stock tone settings')
            if any(type(v) is not int or not -7 <= v <= 7 for v in tone.values()):
                raise ValueError('stock tone values must be integers in -7..7')
        scale_wb((256, 256, 256, 256), row.get('red_gain_permille'), row.get('blue_gain_permille'))
    return rows


def wb_entries(layout):
    entries = [layout.ip[tag] for tag in (0x100, 0x101)]
    for entry in entries:
        if (entry['type'], entry['count']) != (3, 4):
            raise ValueError('requires measured four-halfword WB entries')
        at, n = entry['offset'], entry['bytes']
        if any(at < start+size and start < at+n for start, size in layout.strips):
            raise ValueError('WB metadata overlaps RAW data')
        if any(at < e['offset']+e['bytes'] and e['offset'] < at+n for e in (layout.p, layout.t)):
            raise ValueError('WB metadata overlaps CMIO')
    a, b = entries
    if a['offset'] < b['offset']+b['bytes'] and b['offset'] < a['offset']+a['bytes']:
        raise ValueError('WB entries alias one another')
    original = layout.integers(a)
    if layout.integers(b) != original:
        raise ValueError('this trial requires the measured equal captured/auto WB vectors')
    scale_wb(original, 1000, 1000)
    return entries, original


def tone_entries(layout):
    maker = layout.ifd(layout.maker_base+12, layout.maker_base)
    camera = layout.ifd(layout.maker_base+layout.integers(maker[0x2020])[0], layout.maker_base)
    if layout.integers(camera[0x520]) != (2, 2):
        raise ValueError('requires the measured Natural PictureMode metadata')
    contrast, tone = camera[0x523], camera[0x52e]
    if (contrast['type'], contrast['count']) != (8, 3) or layout.integers(contrast) != (0, -2, 2):
        raise ValueError('requires original stock contrast bounds/value')
    values = layout.integers(tone)
    if (tone['type'], tone['count']) != (8, 28) or values != (
            -31999, 0, -7, 7, -31998, 0, -7, 7, -31997, 0, -7, 7, *([0]*16)):
        raise ValueError('requires the measured H/S/M identifiers, values and bounds')
    for e in (contrast, tone):
        at, n = e['offset'], e['bytes']
        if any(at < a+s and a < at+n for a, s in layout.strips):
            raise ValueError('tone metadata overlaps RAW data')
        if any(at < e2['offset']+e2['bytes'] and e2['offset'] < at+n for e2 in (layout.p, layout.t)):
            raise ValueError('tone metadata overlaps CMIO')
    return contrast, tone


def prepare_tonal(source, image, key, hsl_document, tonal_document):
    base_rows = validate_recipes(hsl_document)
    recipes = definitions(tonal_document)
    original_layout, base_cases = prepare(source, image, key, base_rows)
    wb, original_wb = wb_entries(original_layout)
    stock = list(struct.unpack_from('<256H', image, GAMMA_ROM-BASE))
    validate_curve(stock)
    base_by_name = {name: data for name, data, _ in base_cases}
    out = []
    for recipe in recipes:
        data = bytearray(base_by_name[recipe['base_name']])
        layout = Epl9Orf(bytes(data))
        encoded = bytearray(layout.value(layout.t))
        plain = decode_cmio(encoded, key)
        stock_bytes = struct.pack('<256H', *stock)
        if plain[GAMMA_T_OFFSET:GAMMA_T_OFFSET+512] != stock_bytes:
            raise ValueError('CMIO shared gamma no longer equals the exact E-PL9 RGB curve')
        stock_tone = tonal_document['schema'] == 'epl9-stock-tone-wb-drafts-v2'
        curve = stock if stock_tone else remap_curve(stock, recipe['tone_knots'])
        curve_bytes = struct.pack('<256H', *curve)
        replace_span(encoded, GAMMA_T_OFFSET, stock_bytes, curve_bytes)
        expected_plain = plain[:GAMMA_T_OFFSET]+curve_bytes+plain[GAMMA_T_OFFSET+512:]
        if decode_cmio(encoded, key) != expected_plain:
            raise ValueError('gamma replacement changed unrelated decoded T bytes')
        data[layout.t['offset']:layout.t['offset']+layout.t['bytes']] = encoded
        updated_wb = scale_wb(original_wb, recipe['red_gain_permille'], recipe['blue_gain_permille'])
        for entry in wb:
            struct.pack_into('<2H', data, entry['offset'], *updated_wb[:2])
        allowed = [(original_layout.p['offset']+at, 72) for _, _, at in SLOTS]
        allowed += [(original_layout.t['offset']+at, TABLE_BYTES+1) for at, _, _ in SLOTS]
        allowed += [(original_layout.t['offset']+GAMMA_T_OFFSET, 513)]
        allowed += [(entry['offset'], 4) for entry in wb]
        tone_detail = None
        if stock_tone:
            contrast_entry, tone_entry = tone_entries(original_layout)
            struct.pack_into('<h', data, contrast_entry['offset'], recipe['picture_mode_contrast'])
            for index, name in ((1, 'highlights'), (5, 'shadows'), (9, 'midtones')):
                struct.pack_into('<h', data, tone_entry['offset']+2*index, recipe['tone_level'][name])
                allowed.append((tone_entry['offset']+2*index, 2))
            allowed.append((contrast_entry['offset'], 2))
            tone_detail = dict(contrast=recipe['picture_mode_contrast'], **recipe['tone_level'],
                               metadata_written=True, workspace_consumption_verified=False)
        verify_copy(source, data, allowed, original_layout.strips)
        result = Epl9Orf(bytes(data))
        if any(result.integers(result.ip[tag]) != updated_wb for tag in (0x100, 0x101)):
            raise ValueError('WB roundtrip failed')
        out.append((recipe, bytes(data), curve_bytes, dict(
            original_wb=list(original_wb), updated_wb=list(updated_wb),
            curve_sha256=sha(curve_bytes), curve_min=curve[0], curve_max=curve[-1],
            curve_samples={str(i): curve[i] for i in (0, 1, 16, 32, 64, 128, 192, 254, 255)},
            changed_bytes=sum(a != b for a, b in zip(source, data)),
            raw_strips_byte_identical=True, only_declared_spans_changed=True,
            full_decoded_t_changes_checked=True, pixel_render_observed=False,
            rgb_curve_changed=not stock_tone, stock_tone_metadata=tone_detail,
            camera_art_route_executed=False, sha256=sha(data))))
    return original_layout, out


def raw_checks(source, cases):
    import rawpy
    import numpy as np
    with rawpy.imread(io.BytesIO(source)) as raw:
        mosaic = raw.raw_image.copy()
        original_wb = list(raw.camera_whitebalance)
    results = []
    for recipe, data, _, detail in cases:
        with rawpy.imread(io.BytesIO(data)) as raw:
            if not np.array_equal(raw.raw_image, mosaic):
                raise ValueError('decoded mosaic changed')
            observed_wb = list(raw.camera_whitebalance)
        r, b, g0, g1 = detail['updated_wb']
        if abs(observed_wb[0]-r/g0) > 1e-6 or abs(observed_wb[2]-b/g1) > 1e-6:
            raise ValueError('LibRaw does not interpret WB as the proposed red/blue gains')
        results.append(dict(name=recipe['name'], decoded_mosaic_identical=True,
            mosaic_sha256=sha(mosaic.tobytes()), original_decoder_wb=original_wb,
            updated_decoder_wb=observed_wb, workspace_wb_consumption_verified=False))
    return results


def native_gamma_checks(image_path, cases):
    from epl9_integrated_probe import native, attempt, RETURN
    from epl9_offline_prototype import REQUEST, OUTPUT, OBJECT, TABLE, SP, header
    from mn103_subset import Region, parse_listing
    image = image_path.read_bytes()
    if sha(image) != MAIN_SHA:
        raise ValueError('requires the exact E-PL9 main')
    reader = ROOT/'local/mn103-tooling/mn103-reader.exe'
    if sha(reader.read_bytes()) != READER_SHA:
        raise ValueError('unqualified reader')
    code = {}
    for start, stop in ((0x6079d26c, 0x6079d7da), (0x607a3c9e, 0x607a3df6)):
        listing = subprocess.check_output([str(reader), str(image_path.resolve()), hex(BASE),
            hex(start-BASE), hex(stop-BASE)], text=True)
        code.update(parse_listing(listing, image, BASE))
    report = []
    for recipe, _, curve, _ in cases:
        selectors = []
        for variant in (0, 1):
            request, obj, output = bytearray(1876), bytearray(32), bytearray(5200)
            request[8:12] = header(11)
            struct.pack_into('<H', request, 14, 0x200)
            struct.pack_into('<H', request, 28, 0x100)
            struct.pack_into('<I', request, 1524, OBJECT)
            struct.pack_into('<I', obj, 0, TABLE)
            obj[28] = variant
            m = native(image, code, [Region(REQUEST, request), Region(OBJECT, obj),
                Region(TABLE, curve), Region(OUTPUT, output, True)],
                dict(a0=REQUEST, a1=OUTPUT+4000, d0=OUTPUT+4004, d1=OUTPUT+4008))
            result = attempt(m, 0x6079d328, 0xf0, 28)
            expected = bytearray(5200)
            pointers = (TABLE,)*3 if variant == 0 else (GAMMA_ROM,)*3
            struct.pack_into('<3I', expected, 4000, *pointers)
            if result.get('pc') != RETURN or m.r['sp'] != SP or output != expected:
                raise ValueError(f'native gamma selector/variant guard failed: {result}; '
                    f'sp={m.r["sp"]:#x}; variant={variant}; '
                    f'pointers={struct.unpack_from("<3I", output, 4000)}')
            selectors.append(dict(variant=variant, pointers=[hex(p) for p in pointers],
                instructions=len(m.trace), native_return=True, full_output_checked=5200))
        output = bytearray([0xa5])*5200
        expected = bytearray(output)
        struct.pack_into('<I', expected, 4, struct.unpack_from('<I', expected, 4)[0] & ~0x1000)
        struct.pack_into('<3I', expected, 2596, TABLE, TABLE, TABLE)
        m = native(image, code, [Region(TABLE, curve), Region(OUTPUT, output, True)],
                   dict(a0=OUTPUT, a1=TABLE, d0=TABLE, d1=TABLE))
        result = attempt(m, 0x6079d7a0, 0xa0, 8)
        if result.get('pc') != RETURN or m.r['sp'] != SP or output != expected:
            raise ValueError('native shared RGB-gamma setter changed unrelated configuration')
        report.append(dict(name=recipe['name'], selectors=selectors,
            setter=dict(entry='0x6079d7a0', native_return=True, instructions=len(m.trace),
                        full_output_checked=5200, all_three_pointers_equal=True),
            curve_sha256=sha(curve), hardware_pixel_consumption_verified=False))
    return report


def native_tone_checks(image_path, cases, processing_key=2):
    from epl9_integrated_probe import native, attempt, RETURN
    from epl9_offline_prototype import REQUEST, CONTEXT, OUTPUT, TABLE, SP, header
    from mn103_subset import Region, parse_listing
    if processing_key not in (2, 11):
        raise ValueError('only the measured Natural/COLOR tone contexts are accepted')
    image = image_path.read_bytes()
    if sha(image) != MAIN_SHA:
        raise ValueError('requires exact E-PL9 main')
    reader = ROOT/'local/mn103-tooling/mn103-reader.exe'
    if sha(reader.read_bytes()) != READER_SHA:
        raise ValueError('unqualified reader')
    code = {}
    for start, stop in ((0x6079ed15, 0x6079f3d2), (0x60749cbd, 0x6074a5b2), (0x607a3c9e, 0x607a3df6)):
        listing = subprocess.check_output([str(reader), str(image_path.resolve()), hex(BASE),
            hex(start-BASE), hex(stop-BASE)], text=True)
        code.update(parse_listing(listing, image, BASE))
    checks = []
    for recipe, _, _, _ in cases:
        request, context, output, tone = bytearray(1876), bytearray(128), bytearray(5200), bytearray(16)
        request[8:12] = header(processing_key)
        struct.pack_into('<H', request, 14, 0x200)
        struct.pack_into('<H', request, 28, 0x100)
        request[1795] = recipe['picture_mode_contrast'] & 255
        struct.pack_into('<I', request, 1512, TABLE)
        for index, name in ((2, 'highlights'), (3, 'midtones'), (4, 'shadows')):
            struct.pack_into('<h', tone, 2*index, recipe['tone_level'][name])
        for offset, value in ((4, REQUEST), (12, OUTPUT), (52, processing_key), (60, 2)):
            struct.pack_into('<I', context, offset, value)
        m = native(image, code, [Region(REQUEST, request), Region(CONTEXT, context, True),
                   Region(OUTPUT, output, True), Region(TABLE, tone)], dict(a0=TABLE, a1=CONTEXT+64))
        scaled = attempt(m, 0x6074a061, 0, 16)
        if scaled.get('pc') != RETURN or m.r['sp'] != SP:
            raise ValueError(f'native tone scaling failed: {scaled}')
        m.r['a0'] = CONTEXT
        rendered = attempt(m, 0x6079f309, 0xf0, 32)
        if rendered.get('pc') != RETURN or m.r['sp'] != SP:
            raise ValueError(f'native tone-curve configuration failed: {rendered}')
        pointer = struct.unpack_from('<I', output, 2608)[0]
        if pointer != OUTPUT+2612:
            raise ValueError('native tone did not use its owned curve buffer')
        values = struct.unpack_from('<256H', output, 2612)
        if values[0] != 0 or values[-1] != 1023 or any(a > b for a, b in zip(values, values[1:])):
            raise ValueError('native tone curve endpoint/range/order check failed')
        checks.append(dict(name=recipe['name'], curve=values,
            samples={str(i): values[i] for i in (0, 16, 32, 64, 128, 192, 224, 255)},
            native_return=True, input_key=processing_key, combined_instructions=len(m.trace),
            metadata_values_equal_native_inputs=True, pixel_processing_executed=False))
    return checks


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--raw', type=Path, required=True)
    ap.add_argument('--recipes', type=Path, default=DEFAULT_RECIPES)
    ap.add_argument('--base-recipes', type=Path, default=BASE_RECIPES)
    ap.add_argument('--image', type=Path, default=MAIN)
    ap.add_argument('--library', type=Path, default=LAUREL)
    ap.add_argument('--native-config', action='store_true')
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    if args.out.exists() or not args.out.resolve().is_relative_to((ROOT/'local').resolve()):
        ap.error('output must be a new ignored local directory')
    source, image = args.raw.read_bytes(), args.image.read_bytes()
    base_document = json.loads(args.base_recipes.read_text(encoding='utf-8'))
    document = json.loads(args.recipes.read_text(encoding='utf-8'))
    layout, cases = prepare_tonal(source, image, library_key(args.library), base_document, document)
    validation = raw_checks(source, cases)
    stock_tone = document['schema'] == 'epl9-stock-tone-wb-drafts-v2'
    native_checks = native_gamma_checks(args.image, cases) if args.native_config and not stock_tone else []
    tone_checks = ([*native_tone_checks(args.image, cases, 2), *native_tone_checks(args.image, cases, 11)]
                   if args.native_config and stock_tone else [])
    color_checks = native_recipe_configs(args.image, validate_recipes(base_document)) if args.native_config else []
    report = dict(model='E-PL9', body_version='1.1 (owner report)', downloaded_main_build='1101',
        main_sha256=MAIN_SHA, main_bytes=len(image), analysis_base=hex(BASE),
        original_sha256=sha(source), source_bytes=len(source),
        recipe_definition_sha256=sha(args.recipes.read_bytes()),
        hsl_definition_sha256=sha(args.base_recipes.read_bytes()),
        scope='Workspace stock-tone/captured-WB trials; v1 CMIO gamma is a negative-control experiment',
        recipes=document, raw_checks=validation, native_gamma_checks=native_checks,
        native_tone_checks=tone_checks,
        camera_accessed=False, full_camera_pixel_cycle_passed=False, cases=[])
    args.out.mkdir()
    for check in tone_checks:
        (args.out/(check['name']+f'-native-tone-key{check["input_key"]}.bin')).write_bytes(struct.pack('<256H', *check['curve']))
    for recipe, data, curve, detail in cases:
        name = recipe['name']
        with (args.out/(name+'.ORF')).open('xb') as file:
            file.write(data)
        (args.out/(name+'-rgb-curve.bin')).write_bytes(curve)
        report['cases'].append(dict(name=name, **detail))
    for name, table, output, detail in color_checks:
        (args.out/(name+'-native-hsl-table.bin')).write_bytes(table)
        (args.out/(name+'-native-hsl-config.bin')).write_bytes(output)
    report['native_hsl_checks'] = [dict(name=name, **detail) for name, _, _, detail in color_checks]
    if args.raw.read_bytes() != source:
        raise ValueError('original source changed during preparation')
    (args.out/'manifest.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(out=str(args.out), files=[r['name']+'.ORF' for r, _, _, _ in cases],
        original_and_mosaic_preserved=True, native_gamma_cases=len(native_checks), native_tone_cases=len(tone_checks),
        workspace_render_pending=True), indent=2))


if __name__ == '__main__':
    main()
