"""Prepare isolated, non-film CMIO gamma controls for ordinary Workspace export."""
import argparse
import json
from pathlib import Path
import struct

from epl9_workspace_bridge import (BASE, MAIN, ROOT, Epl9Orf, LAUREL, MAIN_SHA,
                                  decode_cmio, library_key, replace_span, sha)
from epl9_tonal_drafts import remap_curve, definitions

SLOTS = (0xbe6, 0xde6, 0xfe6, 0x11e6)
IDENTITY_SHA = '0f63c5ff71faf9fb002272de6fb38485eb45bb0abc761d2032b2ac0761297218'


def native_curve_document(image, recipe_document):
    """Reuse the output remap on the native variant-zero base, not Workspace's base.

    This is a configuration experiment. Pixel equivalence and the meaning of
    variant flags are unverified. All three slots receive the same curve.
    """
    if sha(image) != MAIN_SHA:
        raise ValueError('requires exact E-PL9 1101 main')
    recipes = definitions(recipe_document)
    pairs = struct.unpack_from('<8I', image, 0x608ff65c-BASE)
    if pairs[::2] != (0x608c37e4,)*4:
        raise ValueError('native normal-table variant-zero mapping changed')
    stock = struct.unpack_from('<256H', image, 0x608c37e4-BASE)
    rows = []
    for recipe in recipes:
        values = remap_curve(stock, recipe['tone_knots'])
        rows.append(dict(watercolor_key=recipe['watercolor_key'],
                         curves=[list(values) for _ in range(3)]))
    document = dict(schema='epl9-native-rgb-tables-v1', recipes=rows)
    from epl9_film_late_module import rgb_tables
    rgb_tables(document)
    evidence = dict(scope='Native configuration trial, not a calibrated camera result',
        model='E-PL9', owner_body_version='1.1', downloaded_main_build='1101',
        main_bytes=len(image), main_sha256=MAIN_SHA,
        native_base_address='0x608c37e4', workspace_active_base_address='0x608c39e4',
        native_normal_selector_table='0x608ff65c', selector_words=[hex(x) for x in pairs],
        native_variant=0, current_hook_requires_request_byte_48_zero=True,
        composition='f(native_stock[i]); same f as Workspace v3, different base table',
        independent_channel_order_required=False, pixel_equivalence_verified=False,
        other_selector_states_qualified=False,
        curves=[dict(watercolor_key=row['watercolor_key'],
                     sha256=sha(struct.pack('<256H', *row['curves'][0]))) for row in rows])
    return document, evidence


def apply_active_curve(raw, image, key, knots, *, restore=False):
    """Set/restore measured T+0xde6 only; no other settings/camera equivalence assumed."""
    if sha(image) != MAIN_SHA:
        raise ValueError('requires exact E-PL9 1101 main')
    layout = Epl9Orf(raw)
    encoded = layout.value(layout.t)
    plain = decode_cmio(encoded, key)
    offset = 0xde6
    stock = image[0x608c39e4-BASE:0x608c39e4-BASE+512]
    remapped = remap_curve(struct.unpack('<256H', stock), knots)
    expected = struct.pack('<256H', *remapped) if restore else stock
    old = plain[offset:offset+512]
    if old != expected:
        raise ValueError('active curve differs from the qualified input curve')
    values = list(struct.unpack('<256H', stock)) if restore else remapped
    replacement = struct.pack('<256H', *values)
    modified = bytearray(encoded)
    replace_span(modified, offset, old, replacement)
    if decode_cmio(modified, key) != plain[:offset]+replacement+plain[offset+512:]:
        raise AssertionError('decoded active-curve change escaped selected span')
    at = layout.t['offset']
    result = bytearray(raw)
    result[at:at+len(modified)] = modified
    if any(a != b and not at+offset <= i <= at+offset+512
           for i, (a, b) in enumerate(zip(raw, result))):
        raise AssertionError('encoded active-curve change escaped selected span')
    return bytes(result), values


def prepare(raw, main, key):
    if sha(main) != MAIN_SHA:
        raise ValueError('requires exact E-PL9 1101 main')
    orf = Epl9Orf(raw)
    encoded = orf.value(orf.t)
    plain = decode_cmio(encoded, key)
    identity = plain[0x9e6:0xbe6]
    if sha(identity) != IDENTITY_SHA:
        raise ValueError('unqualified identity table')
    outputs, controls = {}, []
    for offset in SLOTS:
        stock = plain[offset:offset+512]
        rom = 0x608c35e4 + offset - 0x9e6
        if stock != main[rom-BASE:rom-BASE+512]:
            raise ValueError('input curve does not match exact stock firmware')
        values = struct.unpack('<256H', stock)
        if values[0] != 0 or values[-1] != 4095 or any(a > b for a, b in zip(values, values[1:])):
            raise ValueError('unexpected gamma domain')
        modified = bytearray(encoded)
        replace_span(modified, offset, stock, identity)
        expected = plain[:offset] + identity + plain[offset+512:]
        if decode_cmio(modified, key) != expected:
            raise AssertionError('decoded changes escaped the selected table')
        result = bytearray(raw)
        at = orf.t['offset']
        result[at:at+len(modified)] = modified
        changed = [i for i, (a, b) in enumerate(zip(raw, result)) if a != b]
        if not changed or any(not at+offset <= i <= at+offset+512 for i in changed):
            raise AssertionError('encoded changes escaped the qualified span')
        check = Epl9Orf(result)
        if check.value(check.p) != orf.value(orf.p) or check.strips != orf.strips:
            raise AssertionError('parameter/RAW layout changed')
        if any(result[a:a+n] != raw[a:a+n] for a, n in orf.strips):
            raise AssertionError('RAW bytes changed')
        name = f'gamma-{offset:04x}-identity.ORF'
        outputs[name] = bytes(result)
        controls.append(dict(file=name, cmio_t_offset=hex(offset), rom_address=hex(rom),
                             stock_table_sha256=sha(stock), output_sha256=sha(result),
                             changed_file_bytes=len(changed)))
    return outputs, controls


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    source = ap.add_mutually_exclusive_group(required=True)
    source.add_argument('--raw', type=Path)
    source.add_argument('--film-dir', type=Path,
                        help='existing v2 ORFs; add the v1 remap at the observed active slot')
    source.add_argument('--native-curves', action='store_true',
                        help='adapt the v3 output remap to the native variant-zero base')
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    if args.out.exists() or not args.out.resolve().is_relative_to((ROOT/'local').resolve()):
        ap.error('output must be a new ignored local directory')
    image, key = MAIN.read_bytes(), library_key(LAUREL)
    if args.native_curves:
        document = json.loads((ROOT/'recipes/epl9-film-drafts-v1.json').read_text())
        native_tables, report = native_curve_document(image, document)
        outputs = {'native-rgb-tables.json': (json.dumps(native_tables, indent=2)+'\n').encode()}
    elif args.film_dir:
        recipes = json.loads((ROOT/'recipes/epl9-film-drafts-v1.json').read_text())['recipes']
        outputs, controls = {}, []
        for recipe in recipes:
            name = recipe['name'].replace('-v1', '-v3-active-gamma') + '.ORF'
            path = args.film_dir / (recipe['name'].replace('-v1', '-v2')+'.ORF')
            raw = path.read_bytes()
            result, values = apply_active_curve(raw, image, key, recipe['tone_knots'])
            outputs[name] = result
            controls.append(dict(file=name, source_file=path.name, source_sha256=sha(raw),
                                 output_sha256=sha(result), cmio_t_offset='0xde6',
                                 table_sha256=sha(struct.pack('<256H', *values)),
                                 tone_knots=recipe['tone_knots'],
                                 inherited_wb_hsl_stock_tone='v2 unchanged'))
        report = dict(scope='Uncalibrated software film drafts with active shared gamma; not camera validation',
                      main_sha256=MAIN_SHA, controls=controls)
    else:
        raw = args.raw.read_bytes()
        outputs, controls = prepare(raw, image, key)
        outputs['natural-control.ORF'] = raw
        report = dict(scope='Isolated software-renderer controls, not film recipes or camera validation',
                      source_sha256=sha(raw), main_sha256=MAIN_SHA,
                      identity_table_sha256=IDENTITY_SHA, controls=controls)
    args.out.mkdir(parents=True)
    for name, data in outputs.items():
        (args.out/name).write_bytes(data)
    (args.out/'manifest.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
