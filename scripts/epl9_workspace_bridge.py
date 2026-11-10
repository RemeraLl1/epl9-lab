"""Prepare copied E-PL9 ORF controls for manual OM Workspace development.

These are CMIO transport experiments/drafts, not a TruePic emulator or calibrated film recipes.
Only measured native Natural table/parameter spans are replaced. No camera,
installed application, embedded preview, or original source file is written.
"""

from mn103_tooling import default_reader, verify_reader
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess

from epl9_color_audit import MAIN_SHA, TABLE_SHA

ROOT = Path(__file__).resolve().parents[1]
BASE = 0x60400020
MAIN = ROOT / 'local/epl9-1101-analysis/decoded/00_0100_406e0020.decoded.bin'
LAUREL = Path(r'C:\Program Files (x86)\OMDS\OM Workspace\OlyLaurel.dll')
LAUREL_SHA = 'ebe999733cabd44fcff2d292574d1d732d5d70719e1f5db8a830541949dfa5cc'
KEY_RVA = 0xabfe0
TABLE_BYTES = 3028
P_SIZE, T_SIZE = 8960, 136064
# Measured in this E-PL9 CMIO13 ORF and independently matched to its exact main.
# The color-space interpretation of these paired slots still needs GUI testing.
SLOTS = ((0x6ebe, 0x608e499c, 0x7b4), (0x7a92, 0x608e5570, 0x7fc))
COLOR_ROM = 0x608ee360
SIZES = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 6: 1, 7: 1,
         8: 2, 9: 4, 10: 8, 11: 4, 12: 8, 13: 4}


def sha(data):
    return hashlib.sha256(data).hexdigest()


class Epl9Orf:
    """Bounded, little-endian IFD reader; deliberately no generic TIFF writer."""

    def __init__(self, data):
        self.data = data
        if data[:4] not in (b'IIRO', b'IIRS'):
            raise ValueError('requires a little-endian ORF')
        self.root = self.ifd(self.integer_at(4), 0)
        if self.value(self.root[0x110]).rstrip(b'\0 ') != b'E-PL9':
            raise ValueError('requires Model E-PL9; other models are not compatible')
        exif = self.ifd(self.integers(self.root[0x8769])[0], 0)
        maker = exif[0x927c]
        self.maker_base = maker['offset']
        if self.value(maker)[:12] != b'OLYMPUS\0II\x03\0':
            raise ValueError('unexpected MakerNote header')
        mn = self.ifd(self.maker_base + 12, self.maker_base)
        self.ip = self.ifd(self.maker_base + self.integers(mn[0x2040])[0], self.maker_base)
        self.p, self.t = self.ip[0x635], self.ip[0x636]
        for entry, count in ((self.p, P_SIZE), (self.t, T_SIZE)):
            if (entry['type'], entry['count']) != (7, count):
                raise ValueError('unqualified E-PL9 CMIO block layout')
            if self.value(entry)[:8] != b'CMIO\x01\x00\x13\xdc':
                raise ValueError('requires measured little-endian CMIO13 version 1')
        starts = self.integers(self.root[0x111])
        lengths = self.integers(self.root[0x117])
        if not starts or len(starts) != len(lengths):
            raise ValueError('invalid RAW strip counts')
        self.strips = tuple(zip(starts, lengths))
        for at, n in self.strips:
            self.read(at, n)
            if not n:
                raise ValueError('empty RAW strip')
        spans = [(e['offset'], e['offset'] + e['bytes']) for e in (self.p, self.t)]
        if max(spans[0][0], spans[1][0]) < min(spans[0][1], spans[1][1]):
            raise ValueError('CMIO blocks overlap')
        for a, z in spans:
            if any(a < at+n and at < z for at, n in self.strips):
                raise ValueError('CMIO metadata overlaps RAW strip')

    def read(self, at, n):
        if at < 0 or n < 0 or at+n > len(self.data):
            raise ValueError('ORF span outside source')
        return self.data[at:at+n]

    def integer_at(self, at):
        return struct.unpack('<I', self.read(at, 4))[0]

    def ifd(self, at, base):
        count = struct.unpack('<H', self.read(at, 2))[0]
        if count > 4096:
            raise ValueError('unbounded IFD count')
        self.read(at, 2 + 12*count + 4)
        entries = {}
        for i in range(count):
            pos = at + 2 + 12*i
            tag, kind, n, pointer = struct.unpack('<HHII', self.read(pos, 12))
            if kind not in SIZES or tag in entries:
                raise ValueError('unsupported IFD type or duplicate tag')
            size = SIZES[kind]*n
            where = pos+8 if size <= 4 else base+pointer
            self.read(where, size)
            entries[tag] = dict(type=kind, count=n, offset=where, bytes=size)
        return entries

    def value(self, entry):
        return self.read(entry['offset'], entry['bytes'])

    def integers(self, entry):
        fmt = {3: 'H', 4: 'I', 8: 'h', 9: 'i', 13: 'I'}.get(entry['type'])
        if fmt is None:
            raise ValueError('integer IFD entry required')
        return struct.unpack('<'+fmt*entry['count'], self.value(entry))


def library_key(path):
    """Extract locally, without publishing a proprietary DLL or its constants."""
    data = path.read_bytes()
    if sha(data) != LAUREL_SHA:
        raise ValueError('requires the inspected OM Workspace 2.5W OlyLaurel DLL')
    pe = struct.unpack_from('<I', data, 0x3c)[0]
    opt = pe+24
    if data[pe:pe+4] != b'PE\0\0' or struct.unpack_from('<H', data, opt)[0] != 0x20b:
        raise ValueError('expected PE64 library')
    count = struct.unpack_from('<H', data, pe+6)[0]
    start = opt+struct.unpack_from('<H', data, pe+20)[0]
    for k in range(count):
        _, rva, n, raw = struct.unpack_from('<4I', data, start+40*k+8)
        if rva <= KEY_RVA and KEY_RVA+252 <= rva+n:
            return struct.unpack_from('<63I', data, raw+KEY_RVA-rva)
    raise ValueError('key RVA is not backed by file bytes')


def decode_cmio(encoded, key):
    """Measured native recurrence; only qualified table spans are interpreted."""
    if len(encoded) < 8 or encoded[:4] != b'CMIO' or len(key) != 63:
        raise ValueError('invalid encoded block/key')
    plain = bytearray(encoded)
    previous, index, shift = 0xde, 10, 13
    for at in range(8, len(encoded)):
        word = key[index]
        plain[at] = encoded[at] ^ previous ^ ((word >> shift) & 255)
        previous = (word & 255) ^ plain[at]
        index, shift = (index+1) % 63, (shift+1) % 24
    return bytes(plain)


def replace_span(encoded, offset, before, after):
    """Plaintext differences affect C[p] and C[p+1]; retain both boundaries."""
    if len(before) != len(after) or not 9 <= offset < offset+len(before) < len(encoded):
        raise ValueError('replacement must be a same-size interior span')
    for i, (old, new) in enumerate(zip(before, after)):
        delta = old ^ new
        encoded[offset+i] ^= delta
        encoded[offset+i+1] ^= delta


def validate_recipes(document):
    """Only the accepted two slots and bounded, physical-record coefficients."""
    if document.get('schema') != 'epl9-native-hsl-drafts-v1':
        raise ValueError('unsupported recipe schema')
    recipes = document.get('recipes')
    if not isinstance(recipes, list) or len(recipes) != 2:
        raise ValueError('requires exactly two accepted recipe slots')
    expected = {'gold200-draft-v0': '0x01010078', 'portra400-draft-v0': '0x01020078'}
    seen = set()
    for recipe in recipes:
        name = recipe.get('name')
        if name not in expected or name in seen or recipe.get('watercolor_key') != expected[name]:
            raise ValueError('invalid/duplicate recipe identity or Watercolor binding')
        seen.add(name)
        rows = recipe.get('native_hsl')
        if not isinstance(rows, list) or len(rows) != 12:
            raise ValueError('requires twelve physical H/S/L records')
        for row in rows:
            if not isinstance(row, list) or len(row) != 3 or any(type(v) is not int for v in row):
                raise ValueError('each H/S/L record must contain three integers')
            if not (-1000 <= row[0] <= 1000 and -240 <= row[1] <= 240 and -100 <= row[2] <= 100):
                raise ValueError('draft coefficient outside conservative experiment bounds')
    return recipes


def prepare(source, main, key, recipes=None):
    if recipes is not None:
        validate_recipes(dict(schema='epl9-native-hsl-drafts-v1', recipes=recipes))
    if len(main) != 26214336 or sha(main) != MAIN_SHA:
        raise ValueError('requires exact E-PL9 build 1101 decoded main')
    layout = Epl9Orf(source)
    parameters, encoded = layout.value(layout.p), layout.value(layout.t)
    if encoded != main[0x54b9e0:0x54b9e0+T_SIZE]:
        raise ValueError('source CMIO T differs from exact E-PL9 stock block')
    decoded = decode_cmio(encoded, key)
    creative = main[COLOR_ROM-BASE:COLOR_ROM-BASE+TABLE_BYTES]
    if sha(creative) != TABLE_SHA or decoded[0xe506:0xe506+TABLE_BYTES] != creative:
        raise ValueError('CMIO decode does not recover the complete shared COLOR table')
    for t_at, rom, p_at in SLOTS:
        template = main[rom-BASE:rom-BASE+TABLE_BYTES]
        if decoded[t_at:t_at+TABLE_BYTES] != template:
            raise ValueError('Natural T slot does not match this E-PL9 main')
        coefficients = b''.join(template[r*28+12:r*28+18] for r in range(12))
        if parameters[p_at:p_at+72] != coefficients:
            raise ValueError('Natural P coefficients differ; refusing an already edited source')
    results = []
    definitions = (recipes if recipes is not None else [
        dict(name=name, native_hsl=[[0, saturation, 0] for _ in range(12)])
        for name, saturation in (('epl9-cmio-neutral', 0), ('epl9-cmio-desat-control', -240))])
    for recipe in definitions:
        name = recipe['name']
        p, t = bytearray(parameters), bytearray(encoded)
        expected_plain = bytearray(decoded)
        weights = struct.pack('<36h', *[v for row in recipe['native_hsl'] for v in row])
        for t_at, _, p_at in SLOTS:
            replace_span(t, t_at, decoded[t_at:t_at+TABLE_BYTES], creative)
            expected_plain[t_at:t_at+TABLE_BYTES] = creative
            p[p_at:p_at+72] = weights
        if decode_cmio(t, key) != expected_plain:
            raise ValueError('CMIO replacement changed unrelated decoded bytes')
        result = bytearray(source)
        for entry, block in ((layout.p, p), (layout.t, t)):
            result[entry['offset']:entry['offset']+entry['bytes']] = block
        allowed = [(layout.p['offset']+at, 72) for _, _, at in SLOTS]
        allowed += [(layout.t['offset']+at, TABLE_BYTES+1) for at, _, _ in SLOTS]
        verify_copy(source, result, allowed, layout.strips)
        results.append((name, bytes(result), dict(
            coefficients=list(struct.unpack('<36h', weights)),
            changed_bytes=sum(a != b for a, b in zip(source, result)),
            only_declared_cmio_spans_changed=True, raw_strips_unchanged=True,
            decoded_tables_checked=True, pixel_render_observed=False,
            film_recipe_draft=recipes is not None, film_calibrated=False,
            watercolor_key=recipe.get('watercolor_key'),
            camera_art_route_executed=False, sha256=sha(result))))
    return layout, results


def verify_copy(source, result, allowed, strips):
    if len(source) != len(result):
        raise ValueError('ORF length changed')
    mask = bytearray(len(source))
    for at, n in allowed:
        if at < 0 or n < 0 or at+n > len(mask):
            raise ValueError('allowed span outside ORF')
        mask[at:at+n] = b'\x01'*n
    if any(a != b and not ok for a, b, ok in zip(source, result, mask)):
        raise ValueError('unrelated source bytes changed')
    if any(source[at:at+n] != result[at:at+n] for at, n in strips):
        raise ValueError('RAW samples changed')


def native_recipe_configs(image_path, recipes):
    """Execute the exact camera coefficient packer, without an ISP model."""
    from epl9_integrated_probe import native, attempt, RETURN
    from epl9_offline_prototype import TABLE, OUTPUT, SP, check_packing
    from mn103_subset import Region, parse_listing
    image = image_path.read_bytes()
    if len(image) != 26214336 or sha(image) != MAIN_SHA:
        raise ValueError('exact E-PL9 build 1101 required for native comparison')
    reader = default_reader()
    verify_reader(reader)
    listing = subprocess.check_output([str(reader), str(image_path.resolve()), hex(BASE),
        hex(0x6079e50e-BASE), hex(0x6079e6a0-BASE)], text=True)
    code = parse_listing(listing, image, BASE)
    results = []
    for recipe in recipes:
        table = bytearray(image[COLOR_ROM-BASE:COLOR_ROM-BASE+TABLE_BYTES])
        for r, row in enumerate(recipe['native_hsl']):
            struct.pack_into('<3h', table, r*28+12, *row)
        output = bytearray(5200)
        machine = native(image, code, [Region(TABLE, table), Region(OUTPUT, output, True)],
            dict(a0=TABLE, a1=OUTPUT, d0=struct.unpack_from('<H', table, 3024)[0]))
        result = attempt(machine, 0x6079e50e, 0xf0, 80)
        if result.get('pc') != RETURN or machine.r['sp'] != SP:
            raise ValueError(f'native recipe builder did not return: {result}')
        check_packing(output, table, [row[1] for row in recipe['native_hsl']])
        observed = [list(struct.unpack_from('<3h', output, 688+r*24+18)) for r in range(12)]
        if observed != recipe['native_hsl']:
            raise ValueError('native configuration and CMIO recipe triplets differ')
        results.append((recipe['name'], bytes(table), bytes(output), dict(
            entry='0x6079e50e', instructions=len(machine.trace), native_return=True,
            full_configuration_bytes_checked=5200, native_coefficients_equal_cmio=True,
            table_sha256=sha(table), configuration_sha256=sha(output),
            pixel_processing_executed=False)))
    return results


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--raw', type=Path, required=True)
    ap.add_argument('--image', type=Path, default=MAIN)
    ap.add_argument('--library', type=Path, default=LAUREL)
    ap.add_argument('--reference-tiff', type=Path)
    ap.add_argument('--recipes', type=Path, help='validated two-slot native HSL draft JSON')
    ap.add_argument('--native-config', action='store_true', help='compare draft triplets with native camera packer')
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    if args.out.exists() or not args.out.resolve().is_relative_to((ROOT/'local').resolve()):
        ap.error('output must be a new ignored directory under local/')
    source = args.raw.read_bytes()
    recipes = validate_recipes(json.loads(args.recipes.read_text(encoding='utf-8'))) if args.recipes else None
    if args.native_config and not recipes:
        ap.error('--native-config requires --recipes')
    layout, cases = prepare(source, args.image.read_bytes(), library_key(args.library), recipes)
    configs = native_recipe_configs(args.image, recipes) if args.native_config else []
    report = dict(model='E-PL9', owner_body_version='1.1', downloaded_main_build='1101',
                  main_sha256=MAIN_SHA, source_sha256=sha(source), source_bytes=len(source),
                  cmio_p=layout.p, cmio_t=layout.t,
                  original_cmio_t_sha256=sha(layout.value(layout.t)),
                  library_sha256=LAUREL_SHA, cases=[], camera_accessed=False,
                  full_pixel_cycle_passed=False,
                  scope=('Manual Workspace native HSL draft trials; not a validated ART replacement'
                         if recipes else 'Manual Workspace CMIO transport controls, not ART replacements or film recipes'))
    if args.recipes:
        report['recipe_definition_sha256'] = sha(args.recipes.read_bytes())
        report['recipes'] = recipes
    if args.reference_tiff:
        from PIL import Image, ImageCms
        import io
        with Image.open(args.reference_tiff) as im:
            if im.format != 'TIFF' or im.mode != 'RGB' or im.size != (4608, 3456):
                raise ValueError('expected full-size E-PL9 RGB TIFF reference')
            report['workspace_reference'] = dict(sha256=sha(args.reference_tiff.read_bytes()),
                bytes=args.reference_tiff.stat().st_size, size=im.size,
                bits_per_sample=im.tag_v2.get(258), software=im.tag_v2.get(305),
                profile=ImageCms.getProfileName(ImageCms.ImageCmsProfile(
                    io.BytesIO(im.info['icc_profile']))).strip(),
                provenance='Owner manually exported Natural using OM Workspace GUI')
    args.out.mkdir()
    for name, table, output, detail in configs:
        (args.out/(name+'-native-table.bin')).write_bytes(table)
        (args.out/(name+'-native-config.bin')).write_bytes(output)
    if configs:
        report['native_configuration_checks'] = [dict(name=name, **detail) for name, _, _, detail in configs]
    for name, data, detail in cases:
        target = args.out/(name+'.ORF')
        with target.open('xb') as f:
            f.write(data)
        report['cases'].append(dict(file=target.name, **detail))
    if args.raw.read_bytes() != source:
        raise ValueError('original changed while preparing controls')
    (args.out/'manifest.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(out=str(args.out), files=[c['file'] for c in report['cases']],
                         original_unchanged=True, raw_strips_unchanged=True,
                         needs_manual_workspace_export=True, full_pixel_cycle_passed=False), indent=2))


if __name__ == '__main__':
    main()
