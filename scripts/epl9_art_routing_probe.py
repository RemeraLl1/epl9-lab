"""Read-only routing evidence for exact E-PL9 1.1/build 1101.

The bounded table lookup is a model of one dispatch lookup, not CPU emulation
or execution of the complete processing pipeline. No patch is produced.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess

from epl9_art_probe import BASE, ROOT
from epl9_color_audit import MAIN_SHA, STOCK_SHA

KEYS = {'watercolor_i_gold200_target': 0x01010078,
        'watercolor_ii_portra400_target': 0x01020078,
        'native_color': 11}
NORMALIZATION = 0x01010067
WINDOWS = {
    'job_constructor': (0x6074df04, 0x6074e066),
    'request_header_and_color_fields': (0x6074f225, 0x6074f5db),
    'late_request_constructor': (0x6074f873, 0x6074f971),
    'worklist': (0x607519b8, 0x60752915),
    'watercolor_jobs': (0x60754834, 0x60754c7a),
    'first_pass_request': (0x60761b6a, 0x60761be3),
    'color_dispatch': (0x60799eb6, 0x60799f26),
    'full_table_builder': (0x6079e50e, 0x6079e6a0),
    'sector_builder_and_selectors': (0x6079e9e2, 0x6079ed15),
    'color_pipeline': (0x6079fb88, 0x6079fcb3),
    'color_wrappers': (0x6079fef0, 0x6079ffd7),
}
EXPECTED = {
    0x6074df09: 'mov\t14552,d0',
    0x6074e053: 'mov\t10384,a0',
    0x6074f237: 'mov\t8,a2',
    0x6074f23b: 'movhu\td0,(a2)',
    0x6074f240: 'movhu\td0,(2,a2)',
    0x6074f26a: 'movbu\td0,(16,a2)',
    0x6074f280: 'mov\t(12320,a0),a0',
    0x6074f286: 'mov\ta0,(1524,a2)',
    0x6074f400: 'mov\t4764,a1',
    0x6074f4e5: 'mov\t1813,a0',
    0x6074f507: 'cmp\t12,d2',
    0x6074f892: 'mov\t3,d0',
    0x6074f894: 'movbu\td0,(16,a2)',
    0x607519c0: 'add\t10060,a3',
    0x60751b13: 'and\t15,d0',
    0x60751ed3: 'and\t31,d0',
    0x607521e1: 'and\t3840,d0',
    0x607521f0: 'cmp\t64,d0',
    0x607521f9: 'mov\t1618285337,d1',
    0x60752208: 'mov\t1618298932,d1',
    0x60752215: 'mov\t1618299204,d1',
    0x6075222d: 'mov\t1618299467,d1',
    0x60752241: 'mov\t1618299814,d1',
    0x607523e2: 'mov\t1618285337,d1',
    0x60754a8a: 'mov\t1538,d0',
    0x60754c17: 'mov\t1536,d0',
    0x60754c24: 'mov\t1537,d0',
    0x60754c57: 'mov\t1538,d1',
    0x60761bc2: 'call\t0x6074f931,[a2],8',
    0x60799ec1: 'cmp\t16,d0',
    0x60799ec9: 'cmp\t3,d0',
    0x6079ebdd: 'btst\t268435456,d0',
    0x6079ebf6: 'call\t0x6079e50e,[d2,d3,a2,a3],80',
    0x6079ec3b: 'cmp\t11,d1',
    0x6079ec42: 'add\t1813,a3',
    0x6079ec53: 'call\t0x6079e9e2,[d2,d3,a2,a3],96',
    0x6079ecc6: 'cmp\t16842860,d0',
    0x6079ecd0: 'cmp\t16842876,d0',
    0x6079ed0d: 'call\t0x6079ebc1,[],0',
    0x6079fc15: 'call\t0x6079ebcc,[d2,d3,a2,a3],20',
    0x6079fc5e: 'call\t0x6079ecbf,[a2],8',
    0x6079ff24: 'call\t0x6079fb88,[d2,d3,a2,a3],40',
    0x6079ff4e: 'call\t0x6079fc39,[a2],8',
}


def mode_key(header):
    """Four mode bytes: group, variant, little-endian 16-bit ID."""
    if len(header) != 4:
        raise ValueError('mode header must have four bytes')
    return header[0] << 24 | header[1] << 16 | int.from_bytes(header[2:], 'little')


def lookup(rows, key):
    """Bounded linear probing; zero stored key terminates an absent lookup."""
    count = len(rows)
    if not count or count & (count - 1):
        raise ValueError('table size must be a power of two')
    if not 0x01010068 <= key <= 0x0102007b:
        return {'status': 'outside_key_range', 'visited': []}
    normalized = key - NORMALIZATION
    index = normalized & (count - 1)
    visited = []
    for _ in range(count):
        visited.append(index)
        stored, target = rows[index]
        if stored == normalized:
            return {'status': 'found', 'index': index, 'target': target,
                    'normalized': normalized, 'visited': visited}
        if stored == 0:
            return {'status': 'absent', 'normalized': normalized, 'visited': visited}
        index = (index + 1) & (count - 1)
    raise ValueError('full table has no matching key or empty sentinel')


def audit_tables(data):
    reports = {}
    for name, address, count in [('early_special', 0x608f23c0, 16),
                                 ('main_art', 0x608f22c0, 32)]:
        rows = [struct.unpack_from('<II', data, address - BASE + 8 * i)
                for i in range(count)]
        results = {label: lookup(rows, key) for label, key in KEYS.items()}
        for result in results.values():
            if result['status'] == 'found':
                result['row_address'] = address + 8 * result['index']
                result['row_file_offset'] = result['row_address'] - BASE
        reports[name] = {'address': address, 'entries': count, 'lookups': results}
        if name == 'main_art':
            shared_keys = [stored + NORMALIZATION for stored, target in rows
                           if target == 0x607521db]
            if sorted(shared_keys) != sorted(list(KEYS.values())[:2]):
                raise ValueError('unexpected keys sharing Watercolor branch')
            reports[name]['all_keys_targeting_watercolor_branch'] = shared_keys
    for label in list(KEYS)[:2]:
        if reports['early_special']['lookups'][label]['status'] != 'absent':
            raise ValueError('unexpected early Watercolor route')
        found = reports['main_art']['lookups'][label]
        if found.get('target') != 0x607521db:
            raise ValueError('unexpected Watercolor worklist branch')
    return reports


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--image', type=Path, default=ROOT / 'local/epl9-1101-analysis/decoded/00_0100_406e0020.decoded.bin')
    p.add_argument('--reader', type=Path, default=ROOT / 'local/mn103-tooling/mn103-reader.exe')
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    if args.out.exists() or not args.out.resolve().is_relative_to((ROOT / 'local').resolve()):
        p.error('output must be a new directory within ignored local/')
    data = args.image.read_bytes()
    if len(data) != 26214336 or hashlib.sha256(data).hexdigest() != MAIN_SHA:
        p.error('requires exact decoded E-PL9 1.1/build 1101 main')
    tables = audit_tables(data)
    listings, instructions = {}, {}
    for name, (start, stop) in WINDOWS.items():
        result = subprocess.run([str(args.reader.resolve()), str(args.image.resolve()),
                                 hex(BASE), hex(start - BASE), hex(stop - BASE)],
                                check=True, text=True, capture_output=True)
        listings[name] = result.stdout
        for line in result.stdout.splitlines():
            address, raw, instruction = line.split('\t', 2)
            instructions[int(address, 16)] = instruction.rstrip()
    for address, expected in EXPECTED.items():
        if instructions.get(address) != expected:
            raise ValueError(f'decoder mismatch at {address:#x}: {instructions.get(address)!r}')
    report = {
        'model': 'E-PL9', 'displayed_version': '1.1', 'main_build': '1101',
        'stock_container_bytes': 104552480, 'stock_container_sha256': STOCK_SHA,
        'container_note': 'Identity from initial audit; this probe reads decoded main only.',
        'input_bytes': len(data), 'input_sha256': MAIN_SHA, 'candidate_base': hex(BASE),
        'reader_sha256': hashlib.sha256(args.reader.read_bytes()).hexdigest(),
        'key_identification': 'Watercolor names inferred from pinned E-P7 research; E-PL9 routes verified statically, UI mapping unmeasured.',
        'dispatch_tables': tables,
        'checked_instructions': {hex(k): v for k, v in EXPECTED.items()},
        'windows': {name: {'start': hex(start), 'stop_exclusive': hex(stop)}
                    for name, (start, stop) in WINDOWS.items()},
        'camera_accessed': False, 'firmware_modified': False,
        'limits': ['Static decoding and bounded table lookup only; no CPU or pixel emulation.',
                   'Whole-job branches, custom instructions, buffer lifetimes and flags not executed.',
                   'No validated live-view/still mapping, color recipe, or installable patch.'],
    }
    args.out.mkdir(parents=True)
    for name, listing in listings.items():
        (args.out / (name + '.tsv')).write_text(listing, encoding='utf-8')
    (args.out / 'audit.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'out': str(args.out), 'instruction_checks': len(EXPECTED),
                      'dispatch_tables': tables, 'camera_accessed': False}, indent=2))


if __name__ == '__main__':
    main()
