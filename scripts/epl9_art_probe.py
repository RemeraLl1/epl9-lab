"""Read-only Watercolor/Gold 200 research probe for exact E-PL9 1.1 main.

Disassembly observations are static, with a candidate RAM mapping. They do not
establish on-camera reachability, live-view/capture coverage or safe patch sites.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess

from epl9_color_audit import MAIN_SHA, STOCK_SHA, occurrences

ROOT = Path(__file__).resolve().parents[1]
BASE = 0x60400020
KEYS = {'watercolor_i_candidate': 0x01010078, 'watercolor_ii_candidate': 0x01020078}
WINDOWS = {
    'startup': (0xb6, 0xd9),
    'watercolor_key_comparison': (0x393461, 0x39347a),
    'watercolor_tone_shared': (0x39cfa5, 0x39cfb4),
    'watercolor_separate_parameters': (0x39e375, 0x39e387),
    'combiner_type_selector': (0x38f481, 0x38f4a8),
    'color_sector_builder': (0x39e9c2, 0x39eba1),
    'color_key_11_selection': (0x39ebac, 0x39ec38),
}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--image', type=Path, default=ROOT / 'local/epl9-1101-analysis/decoded/00_0100_406e0020.decoded.bin')
    p.add_argument('--reader', type=Path, default=ROOT / 'local/mn103-tooling/mn103-reader.exe')
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    if args.out.exists():
        p.error('output directory already exists')
    if not args.out.resolve().is_relative_to(ROOT / 'local'):
        p.error('derived firmware evidence must stay in ignored local/')
    data = args.image.read_bytes()
    if len(data) != 26214336 or hashlib.sha256(data).hexdigest() != MAIN_SHA:
        p.error('requires exact decoded E-PL9 1.1/build 1101 main')
    # Structural checks are observations, not patch-offset validation.
    if data[0xb6:0xbe] != bytes.fromhex('fc dc f9 00 40 60 f0 f4'):
        raise ValueError('unexpected startup sequence')
    listings = {}
    instructions = {}
    for name, (start, stop) in WINDOWS.items():
        result = subprocess.run([str(args.reader.resolve()), str(args.image.resolve()),
                                 hex(BASE), hex(start), hex(stop)],
                                check=True, text=True, capture_output=True)
        listings[name] = result.stdout
        for line in result.stdout.splitlines():
            address, raw, text = line.split('\t', 2)
            instructions[int(address, 16)] = (raw, text.rstrip())
    expected = {
        0x60793481: 'cmp\t16842872,d0',
        0x60793489: 'jmp\t0x60793584',
        0x6079348c: 'cmp\t16908408,d0',
        0x60793494: 'jmp\t0x607936f7',
        0x6079e395: 'mov\t1620050116,a0',
        0x6079e39e: 'mov\t1620050168,a0',
        0x6079ec3b: 'cmp\t11,d1',
        0x6079ec4d: 'mov\t1619977056,a0',
        0x6079ec53: 'call\t0x6079e9e2,[d2,d3,a2,a3],96',
    }
    for address, text in expected.items():
        if instructions.get(address, (None, None))[1] != text:
            raise ValueError(f'unexpected decoder output at {address:#x}')
    pair_tables = []
    for name, start in [('shared_tone_candidate', 0x5009d8), ('separate_parameters_candidate', 0x500f70)]:
        rows = []
        for offset in (start, start + 8):
            key, target = struct.unpack_from('<II', data, offset)
            rows.append({'file_offset': hex(offset), 'key': hex(key),
                         'target_candidate_address': hex(target), 'target_file_offset': hex(target - BASE)})
        pair_tables.append({'name': name, 'rows': rows})
    report = {
        'model': 'E-PL9', 'displayed_version': '1.1', 'main_build': '1101',
        'stock_container_bytes': 104552480, 'stock_container_sha256': STOCK_SHA,
        'input_bytes': len(data), 'input_sha256': MAIN_SHA,
        'container_note': 'Container identity carried from the initial audit; this probe reads the decoded main only.',
        'reader_sha256': hashlib.sha256(args.reader.read_bytes()).hexdigest(),
        'candidate_base': hex(BASE),
        'key_literal_offsets': {name: [hex(x) for x in occurrences(data, struct.pack('<I', key))]
                                for name, key in KEYS.items()},
        'key_identification': 'Watercolor names inferred from pinned E-P7 research; exact E-PL9 bytes and separate branches verified offline.',
        'key_target_pairs': pair_tables,
        'combiner_parameter_candidates': [
            {'file_offset': hex(offset), 'signed_16bit_values': list(struct.unpack_from('<5h', data, offset))}
            for offset in (0x4f415c, 0x4f4166)
        ],
        'checked_instructions': {hex(k): v for k, v in expected.items()},
        'windows': {name: {'start_file_offset': hex(start), 'stop_file_offset_exclusive': hex(stop)}
                    for name, (start, stop) in WINDOWS.items()},
        'camera_accessed': False, 'firmware_modified': False,
        'limits': ['Window starts follow local code patterns and references; no whole-image CFG.',
                   'Unknown/custom MN103 instructions are not emulated.',
                   'No live-view/still routing or isolated replacement validated on hardware.'],
    }
    args.out.mkdir(parents=True)
    for name, listing in listings.items():
        (args.out / (name + '.tsv')).write_text(listing, encoding='utf-8')
    (args.out / 'audit.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'out': str(args.out), 'verified_instruction_checks': len(expected),
                      'pair_tables': pair_tables, 'camera_accessed': False}, indent=2))


if __name__ == '__main__':
    main()
