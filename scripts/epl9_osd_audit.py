"""Read-only E-PL9 OSD audit using a pinned external decoder; no firmware edits."""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import struct

from epl9_source_identity import verified_source

ROOT = Path(__file__).resolve().parents[1]
BASE = 0x60400020
MAIN_SHA = '8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267'
OSD_SHA = 'ee9a9c3ad1974dd212483ca7d012e51ae23083ce0119589a3b42996aa13ccf1e'
# Historical Windows checkout raw identity; keep for earlier evidence.
DECODER_SHA = '16e310d988012e56091ce883ab6ab95d5f1eaf3abb00a0aac733a54edb99a9b8'
# LF bytes from tools/osd_extract.py at DECODER_COMMIT.
DECODER_LF_SHA = 'c7fe693c1322553758a7f312c8e31009b9f45016702f83c24eaec6cbd2910396'
DECODER_COMMIT = '7d42c1f258737b7196c6b17cec5d643b5080ece6'
ASSETS = [688, 689, 1024, 4387, 4388, 4420, 4421, 4458, 4459, 4556, 4557, 4573]
# Deliberately selected matched label lists, not every occurrence of value 19.
LABEL_ROWS = {
    0x6157192c: (0x1301, 3, 4387), 0x61571938: (0x1302, 3, 4388),
    0x61571f08: (0x1301, 3, 4420), 0x61571f14: (0x1302, 3, 4421),
    0x615725c8: (0x1301, 4, 2694), 0x615725d4: (0x1302, 4, 2695),
    0x615731bc: (0x10013, 3, 4458), 0x615731c8: (0x20013, 3, 4459),
    0x61572eec: (0x10013, 4, 1800), 0x61572ef8: (0x20013, 4, 1800),
    0x61583fe8: (0x1301, 3, 4556), 0x61583ff4: (0x1302, 3, 4557),
}


def verified_bytes(path, expected, size=None):
    data = Path(path).read_bytes()
    if (size is not None and len(data) != size) or hashlib.sha256(data).hexdigest() != expected:
        raise ValueError(f'input identity mismatch: {Path(path).name}')
    return data


def load_decoder(path=None):
    path = path or ROOT / 'references/caduceus-ep7/tools/osd_extract.py'
    source, identity = verified_source(path, DECODER_LF_SHA, DECODER_SHA)
    spec = importlib.util.spec_from_file_location('pinned_external_osd', path)
    module = importlib.util.module_from_spec(spec)
    # Execute the verified snapshot, not a potentially stale cached .pyc.
    exec(compile(source, str(path), 'exec'), module.__dict__)
    module._source_identity = identity
    # Reuse format parsing, NOT other-model offsets or compatibility claims.
    # Hash checks stay enabled and now require the identified E-PL9 components.
    module.COMPONENT_ADDR = 0x421e0020
    module.MAIN_BASE = BASE
    module.COMPONENT_SHA, module.MAIN_SHA = OSD_SHA, MAIN_SHA
    return module


def check_labels(data):
    if len(data) < max(LABEL_ROWS) - BASE + 12:
        raise ValueError('input too short for E-PL9 label tables')
    rows = []
    for address, expected in LABEL_ROWS.items():
        value, kind, ident, text = struct.unpack_from('<IHHI', data, address - BASE)
        if (value, kind, ident) != expected:
            raise ValueError(f'label mismatch at {address:#x}')
        off = text - BASE
        if not 0 <= off < len(data) or data[off] != 0:
            raise ValueError('label text pointer is not an in-image empty string')
        rows.append(dict(address=hex(address), value=hex(value), kind=kind, id=ident))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    decoded = ROOT / 'local/epl9-1101-analysis/decoded'
    parser.add_argument('--main', type=Path, default=decoded / '00_0100_406e0020.decoded.bin')
    parser.add_argument('--osd', type=Path, default=decoded / '01_0101_421e0020.decoded.bin')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists() or not args.out.resolve().is_relative_to((ROOT / 'local').resolve()):
        parser.error('output must be a new directory within ignored local/')
    main_data = verified_bytes(args.main, MAIN_SHA, 26214336)
    verified_bytes(args.osd, OSD_SHA, 26214336)
    labels = check_labels(main_data)
    decoder = load_decoder()
    osd = decoder.OSD(args.osd, args.main)
    if set(osd.resources) != set(range(70)) or osd.bitmap_count != 7490 or osd.symbol_count != 240:
        raise ValueError('unexpected E-PL9 directory/table shape')
    catalog, selected, modes = [], {}, Counter()
    for index in range(osd.bitmap_count):
        row = osd.descriptor(index)
        if row['kind'] == 'rle':
            if any(row['reserved']):
                raise ValueError('nonzero descriptor reserved fields')
            pixels, mode, payload = osd.decode_bitmap(row)
            modes[mode] += 1
            row.update(mode=mode, pixel_sha256=hashlib.sha256(pixels).hexdigest(),
                       payload_sha256=hashlib.sha256(payload).hexdigest())
            if index in ASSETS:
                selected[index] = (row, pixels)
        elif row['kind'] not in ('placeholder', 'null'):
            raise ValueError(f'unrecognized descriptor {index}')
        catalog.append(row)
    symbols = {}
    for index in range(osd.symbol_count):
        row, pixels = osd.symbol(index)
        if index in (0x54, 0x55, 0x62, 0x76, 0x77):
            symbols[index] = (row, pixels)
    string_base, strings = osd.strings(8)
    if strings[2694] != 'Watercolor@A054@' or strings[2695] != 'Watercolor@A055@':
        raise ValueError('English variant labels do not match')
    palettes = osd.palettes()
    palette = next(p['entries'] for p in palettes if p['address'] == 0x6151b980)
    counts = dict(Counter(row['kind'] for row in catalog))
    if counts != {'null': 1, 'rle': 5417, 'placeholder': 2072} or set(selected) != set(ASSETS):
        raise ValueError('unexpected asset coverage')
    args.out.mkdir(parents=True)
    sheet = []
    for index, (row, pixels) in selected.items():
        image = decoder.palette_image(pixels, row['width'], row['height'], palette)
        image.save(args.out / f'b{index}.png')
        sheet.append((str(index), image.convert('RGBA')))
    for index, (row, pixels) in symbols.items():
        image = decoder.rgba_image(pixels, row['width'], row['height'], decoder.level_palette(palette))
        image.save(args.out / f'A{index:03X}.png')
        sheet.append((f'A{index:03X}', image))
    decoder.contact_sheet(sheet, args.out / 'watercolor-icons.png', cols=4, cell=(150, 86))
    report = {
        'model': 'Olympus E-PL9', 'displayed_version': '1.1 (owner report)', 'main_build': '1101',
        'stock_bytes': 104552480,
        'stock_sha256': 'aefab05396c43ecba0551b94a5d31f7e52350c18d6f4bf1d02d75761108e6028',
        'stock_note': 'Container identity from initial audit; only decoded components read here.',
        'main': {'bytes': len(main_data), 'sha256': MAIN_SHA, 'analysis_base': hex(BASE)},
        'osd': {'bytes': 26214336, 'sha256': OSD_SHA, 'component_header_version': '0x0100',
                'container_payload_address': '0x421e0020'},
        'decoder': {'upstream': 'https://github.com/cakelesscoder/caduceus-ep7',
                    'commit': DECODER_COMMIT, 'file': 'tools/osd_extract.py',
                    'sha256': decoder._source_identity['raw_sha256'],
                    **decoder._source_identity},
        'adapter_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'resources': osd.resources, 'bank0_base': hex(osd.base0), 'bank69_base': hex(osd.base69),
        'bitmap_count': osd.bitmap_count, 'kinds': counts, 'rle_modes': dict(modes),
        'symbols_decoded': osd.symbol_count, 'english_base': hex(string_base), 'english_count': len(strings),
        'palette_candidate': '0x6151b980; runtime selection unverified',
        'label_rows': labels, 'assets': [selected[i][0] for i in ASSETS],
        'inline_symbols': [r for r, _ in symbols.values()],
        'strings': {str(i): strings[i] for i in [1800, 2694, 2695, 2709, 2729, 2730]},
        'camera_accessed': False, 'firmware_modified': False,
        'limits': ['Table extents/bases follow structural rules, not measured RAM.',
                   'Matched labels plus decoded artwork identify candidates; all screen call paths are not traced.',
                   'Generic ART12 badges and shared Roman numerals are not variant-specific assets.',
                   'No replacement art, binary encoding, firmware patch or on-camera verification.'],
    }
    (args.out / 'audit.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    (args.out / 'catalog.json').write_text(json.dumps(catalog, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'out': str(args.out), 'kinds': counts, 'symbols': osd.symbol_count,
                      'modes': dict(modes), 'selected': ASSETS, 'label_checks': len(labels)}, indent=2))


if __name__ == '__main__':
    main()
