"""Validate the standalone reader with upstream AM33-2 opcode fixtures.

No camera access. The caller supplies GNU binutils sources and a local work dir.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

VECTOR_COUNT, VECTOR_BYTES = 1294, 5694


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reader', type=Path, required=True)
    parser.add_argument('--vectors', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads((Path(__file__).with_name('upstream.json')).read_text(encoding='utf-8'))
    vector_identity = next(row for row in manifest['files'] if row['path'] == 'gas/testsuite/gas/mn10300/am33-2.d')
    vector_sha = hashlib.sha256(args.vectors.read_bytes()).hexdigest()
    if vector_sha != vector_identity['sha256']:
        raise ValueError('changed upstream vector identity')
    args.out.mkdir(parents=True, exist_ok=True)
    fixtures = []
    data = bytearray()
    for line in args.vectors.read_text().splitlines():
        match = re.fullmatch(r'0\*([0-9a-f]+) <[^>]+> (.*?)\t(.*)', line)
        if not match:
            continue
        address = int(match[1], 16)
        raw = bytes.fromhex(''.join(re.findall(r'\b[0-9a-f]{2}\b', match[2])))
        if address != len(data) or not raw:
            raise ValueError(f'Noncontiguous/unsupported vector at {address:#x}')
        # This raw-binary adapter prints addresses without objdump symbol labels.
        # Keep the numeric target constraints from the upstream expectations.
        expected = re.sub(r'0\*([0-9a-f]+) <\[\^>\]\*>',
                          lambda m: '0x0*' + m[1], match[3])
        expected = re.sub(r'0\*([0-9a-f]+) <[^>]+>',
                          lambda m: '0x0*' + m[1], expected)
        fixtures.append((address, raw, expected))
        data.extend(raw)
    if len(fixtures) != VECTOR_COUNT or len(data) != VECTOR_BYTES:
        raise ValueError(f'Unexpected vector inventory: {len(fixtures)} instructions, {len(data)} bytes')
    image = args.out / 'am33-2-vectors.bin'
    image.write_bytes(data)
    reader = str(args.reader.resolve())
    result = subprocess.run([reader, str(image), '0', '0', str(len(data))],
                            text=True, capture_output=True, check=True)
    lines = result.stdout.splitlines()
    if len(lines) != len(fixtures):
        raise AssertionError(f'Instruction count differs: {len(lines)} != {len(fixtures)}')
    failures = []
    for line, (address, raw, expected) in zip(lines, fixtures):
        actual_address, actual_raw, instruction = line.split('\t', 2)
        if (int(actual_address, 16) != address or actual_raw != raw.hex()
                or not re.fullmatch(expected, instruction)):
            failures.append({'offset': hex(address), 'actual': line, 'expected': expected})
    if failures:
        print(json.dumps(failures[:20], indent=2))
        raise AssertionError(f'{len(failures)} opcode mismatches')
    # Exercise failure paths with independent malformed inputs.
    truncated = args.out / 'truncated.bin'
    truncated.write_bytes(bytes.fromhex('fc dc 01'))
    rejected = []
    cases = [
        ('truncated instruction', [str(truncated), '0', '0', '3']),
        ('outside image', [str(image), '0', '0', str(len(data) + 1)]),
        ('mapping overflow', [str(image), '0xffffffff', '0', '1']),
        ('negative offset', [str(image), '0', '-1', '1']),
        ('invalid machine', [str(image), '0', '0', '1', '123']),
    ]
    for label, params in cases:
        bad = subprocess.run([reader, *params], capture_output=True, text=True)
        if bad.returncode != 2:
            raise AssertionError(f'{label}: expected exit 2, got {bad.returncode}')
        rejected.append(label)
    report = {'upstream_opcode_vectors_passed': len(fixtures), 'fixture_bytes': len(data), 'vectors_sha256': vector_sha,
              'negative_cases_passed': rejected, 'camera_accessed': False,
              'scope': 'Decoder/host-adapter validation; not firmware reachability or patch validation.'}
    (args.out / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
