"""Compare two complete logical component acquisitions with frozen v3/stock.

Local files only. Never acquires device memory and never certifies provenance.
The required layout is the decoded envelope passed to the native writer,
including its 32-byte header and trailer, not an encoded update or RAM slice.
"""
import argparse
import json
from pathlib import Path

from epl9_workspace_bridge import ROOT, sha
from epl9_recovery_audit import inspect_package, decoded_payload

PACKAGES = {
    'v3': ('Gold-Portra-v3-candidate.bin', '8d606a028f4b533db6431f1a0271a92d8f3f1c71e08833b481dcb2310d79ef8f'),
    'stock': ('Stock-1101-main-osd-restore.bin', '10a7b949d1509ce627cb3c098c0a01a8ae5758fb2ce84b6c887e34b46e349387'),
}
PRIVATE_PACKAGES = {**PACKAGES,
    'v3': ('Gold-Portra-v3-private-color-candidate.bin',
           '230c4853b41d069da2a4fb22ace1eb043b28b71c9fa5b634cdc8baa037170256')}
GENERATIONS = ('frozen-v3', 'private-color-v3')
KINDS = ('main', 'osd')
ADDRESSES = {'main': 0x406e0000, 'osd': 0x421e0000}
SIZE = 26214400


def package_files(generation):
    if generation == 'frozen-v3':return PACKAGES
    if generation == 'private-color-v3':return PRIVATE_PACKAGES
    raise ValueError('unknown readback generation')


def references(directory, generation='frozen-v3'):
    result = {}
    for label, (name, digest) in package_files(generation).items():
        raw = (directory/name).read_bytes()
        if len(raw) != 2*SIZE or sha(raw) != digest:
            raise ValueError('frozen package identity differs: '+name)
        rows = inspect_package(raw)
        if [r['kind'] for r in rows] != ['0x100', '0x101']:
            raise ValueError('component inventory differs')
        result[label] = {}
        for kind, row in zip(KINDS, rows):
            at, size = int(row['offset'], 16), row['package_bytes']
            if size != SIZE or int(row['destination'], 16) != ADDRESSES[kind]:
                raise ValueError('component address/length differs')
            block = raw[at:at+size]
            result[label][kind] = block[:32]+decoded_payload(block[32:-32])+block[-32:]
    return result


def difference(actual, expected):
    if len(actual) != len(expected):
        return dict(size_matches=False, expected_bytes=len(expected), actual_bytes=len(actual))
    count, first, last = 0, None, None
    if actual != expected:
        for i, (a, b) in enumerate(zip(actual, expected)):
            if a != b:
                if first is None:
                    first = i
                last, count = i, count+1
    return dict(size_matches=True, differing_bytes=count,
        first_difference=hex(first) if first is not None else None,
        last_difference=hex(last) if last is not None else None)


def compare(samples, refs, expected):
    if expected not in PACKAGES or set(samples) != set(KINDS):
        raise ValueError('both components and an explicit target are required')
    rows = []
    for kind in KINDS:
        if len(samples[kind]) != 2:
            raise ValueError('two separate reads are required for each component')
        first, second = samples[kind]
        target = refs[expected][kind]
        identity = [label for label in PACKAGES if first == refs[label][kind]]
        repeat_matches = first == second
        matched = first == target and repeat_matches
        rows.append(dict(component=kind, logical_destination=hex(ADDRESSES[kind]),
            bytes=len(first), first_sha256=sha(first), repeat_bytes=len(second),
            repeat_sha256=sha(second), stable=repeat_matches, first_identity=identity,
            target_matches=matched, difference=difference(first, target)))
    return dict(schema='epl9-component-readback-comparison-v1', expected=expected,
        layout='logical-decoded-envelope-v1', components=rows,
        both_component_bytes_match=all(r['target_matches'] for r in rows),
        acquisition_provenance_verified=False, physical_write_verified=False,
        boot_recovery_verified=False, camera_accessed=False,
        limitation='Byte comparison only: source files are not proof of device acquisition.')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--packages', type=Path)
    ap.add_argument('--generation', choices=GENERATIONS, default='frozen-v3')
    ap.add_argument('--expected', choices=PACKAGES, required=True)
    for kind in KINDS:
        ap.add_argument('--'+kind, type=Path, required=True)
        ap.add_argument('--'+kind+'-repeat', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    if args.packages is None:
        args.packages=ROOT/('local/epl9-v3-private-packages-20261107' if
            args.generation=='private-color-v3' else 'local/epl9-v3-packages-20261107')
    if not args.out.resolve().is_relative_to((ROOT/'local').resolve()) or args.out.exists():
        ap.error('use a new ignored local report path')
    samples, paths = {}, {}
    for kind in KINDS:
        a, b = getattr(args, kind).resolve(), getattr(args, kind+'_repeat').resolve()
        if a.samefile(b):
            ap.error('repeat read must be a separate file')
        samples[kind] = (a.read_bytes(), b.read_bytes())
        paths[kind] = [str(a), str(b)]
    report = compare(samples, references(args.packages,args.generation), args.expected)
    report['generation'] = args.generation
    report['input_files'] = paths
    report['source_sha256'] = sha(Path(__file__).read_bytes())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report['both_component_bytes_match'] else 1)


if __name__ == '__main__':
    main()
