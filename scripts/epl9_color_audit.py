"""Read-only audit of exact E-PL9 1.1 firmware and its shared COLOR table."""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import struct
import sys


ROOT = Path(__file__).resolve().parents[1]
STOCK_SHA = 'aefab05396c43ecba0551b94a5d31f7e52350c18d6f4bf1d02d75761108e6028'
MAIN_SHA = '8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267'
TABLE_SHA = 'a33d64bdb78ac41ba24ccbff820380f563211a095ac08a12a7c37a51b5c00531'
TABLE_SIZE = 3028


def occurrences(data, needle):
    position = 0
    result = []
    while (position := data.find(needle, position)) >= 0:
        result.append(position)
        position += 1
    return result


def reference_from_library(path):
    data = path.read_bytes()
    view = memoryview(data)
    for alignment in range(4):
        for offset in range(alignment, len(data) - TABLE_SIZE + 1, 4):
            table = view[offset:offset + TABLE_SIZE]
            if hashlib.sha256(table).hexdigest() == TABLE_SHA:
                return bytes(table), {
                    'filename': path.name,
                    'sha256': hashlib.sha256(data).hexdigest(),
                    'table_file_offset': hex(offset),
                }
    raise ValueError('The expected COLOR reference was not found in this library')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--firmware', type=Path, default=ROOT / 'firmware/OLY_E_133_1101_0000_0000.BIN')
    parser.add_argument('--library', type=Path, default=Path(r'C:\Program Files (x86)\OMDS\OM Workspace\OlyAcacia.dll'))
    parser.add_argument('--decoder', type=Path, default=ROOT / 'references/oly_fw_analysis/tools/oly_container.py')
    parser.add_argument('--out', type=Path, required=True, help='new local evidence directory')
    args = parser.parse_args()
    if args.out.exists():
        parser.error('output directory already exists')
    raw = args.firmware.read_bytes()
    if len(raw) != 104552480 or hashlib.sha256(raw).hexdigest() != STOCK_SHA:
        parser.error('this audit requires the exact E-PL9 stock 1.1/build 1101 input')
    spec = importlib.util.spec_from_file_location('oly_container_audit', args.decoder)
    decoder = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = decoder
    spec.loader.exec_module(decoder)
    blocks = decoder.parse(raw)
    if decoder.reconstruct(blocks) != raw:
        raise ValueError('decode/re-encode differs from the source')
    if hashlib.sha256(blocks[0].payload).hexdigest() != MAIN_SHA:
        raise ValueError('unexpected main payload')
    reference, library = reference_from_library(args.library)
    rows = []
    for block in blocks:
        matches = occurrences(block.payload, reference)
        rows.append({
            'index': block.index,
            'kind': hex(block.kind),
            'payload_bytes': len(block.payload),
            'decoded_sha256': hashlib.sha256(block.payload).hexdigest(),
            'checksum_valid': True,
            'shared_color_table_file_offsets': [hex(x) for x in matches],
        })
    main_image = blocks[0].payload
    table_matches = occurrences(main_image, reference)
    mapping = None
    if (main_image[0xb6:0xb8] == b'\xfc\xdc'
            and main_image[0xbc:0xbe] == b'\xf0\xf4'
            and main_image[0xd9] == 0xcf):
        target = struct.unpack_from('<I', main_image, 0xb8)[0]
        base = target - 0xd9
        mapping = {
            'candidate_base': hex(base),
            'jump_file_offset': '0xb6',
            'jump_target': hex(target),
            'candidate_init_file_offset': '0xd9',
            'table_literal_reference_candidates': [
                {'table_file_offset': hex(offset), 'candidate_address': hex(base + offset),
                 'reference_file_offsets': [hex(x) for x in occurrences(main_image, struct.pack('<I', base + offset))]}
                for offset in table_matches
            ],
            'scope': 'startup-pattern and literal candidates; not validated disassembly or semantic cross references',
        }
    leads = []
    pattern = re.compile(rb'artfilter|arteffect|color.?creat|color.?profil|satura|hue|lightness|monochrom|picture.?mode', re.I)
    for match in re.finditer(rb'[\x20-\x7e]{6,}', main_image):
        if pattern.search(match.group()):
            leads.append({'decoded_file_offset': hex(match.start()), 'text': match.group().decode('ascii')})
    report = {
        'model': 'E-PL9', 'model_id': '1330', 'public_version': '1.1', 'main_header_build': '1101',
        'source_filename': args.firmware.name, 'source_bytes': len(raw), 'source_sha256': STOCK_SHA,
        'exact_decode_reencode': True, 'components': rows,
        'reference_table_bytes': TABLE_SIZE, 'reference_table_sha256': TABLE_SHA,
        'reference_library': library, 'mapping_candidates': mapping,
        'main_color_string_lead_count': len(leads),
        'camera_accessed': False, 'firmware_modified': False,
        'scope': 'Offline data correspondence and candidates; no E-PL9 patch, code reachability or hardware validation.',
    }
    args.out.mkdir(parents=True)
    (args.out / 'audit.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    (args.out / 'string-leads.json').write_text(json.dumps(leads, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
