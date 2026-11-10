"""Firmware-free Linux/Windows smoke check for a source-built MN103 reader.

Assemble the separate synthetic-address bounded-reader experiment, independently
decode its instruction boundaries/mnemonics, then run three modeled-MMIO cases.
This is not the archived exact-stock 44-case probe or camera/DMA qualification.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from mn103_tooling import default_reader, reader_provenance
from epl9_bounded_read import build, MODULE_BASE
from epl9_bounded_read_probe import Fixture
from mn103_subset import parse_listing


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reader', type=Path, default=default_reader())
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists() or not args.out.resolve().is_relative_to((ROOT / 'local').resolve()):
        parser.error('use a new ignored local output directory')
    provenance = reader_provenance(args.reader)
    module = build()
    args.out.mkdir(parents=True)
    binary = args.out / 'synthetic-bounded-reader.bin'
    binary.write_bytes(module['data'])
    listing = subprocess.check_output([str(args.reader.resolve()), str(binary.resolve()),
        hex(MODULE_BASE), '0', str(len(module['data']))], text=True)
    module['code'] = parse_listing(listing, module['data'], MODULE_BASE)
    if set(module['code']) != {row[0] for row in module['rows']}:
        raise ValueError('independent GNU boundaries differ from emitter')
    for at, mnemonic, operands, length in module['rows']:
        raw, observed, _ = module['code'][at]
        if len(raw) != length or observed != mnemonic:
            raise ValueError(f'independent GNU mnemonic/length differs at {at:#x}')
    rows = []
    for name, options, expected in [('complete', {}, (0, 2, 2048)),
            ('not-exclusive', {'exclusive': 0}, (1, 4, 0)),
            ('dma-timeout', {'completion_after': None}, (5, 3, 0))]:
        fixture = Fixture(module, **options)
        result = fixture.run()
        if tuple(result[k] for k in ('result', 'state', 'valid_bytes')) != expected:
            raise ValueError('synthetic control failed: ' + name)
        if result['physical_dma_executed']:
            raise ValueError('unexpected physical DMA claim')
        rows.append(dict(case=name, **result))
    (args.out / 'listing.tsv').write_text(listing, encoding='utf-8')
    report = dict(schema='epl9-mn103-source-only-smoke-v1', reader=provenance,
        module_bytes=len(module['data']), decoded_instructions=len(module['code']),
        cases=rows, stock_firmware_used=False, camera_accessed=False,
        archived_native_probe_reproduced=False, install_ready=False)
    (args.out / 'smoke.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(module_bytes=report['module_bytes'], decoded_instructions=report['decoded_instructions'],
                         modeled_cases=len(rows), stock_firmware_used=False, camera_accessed=False)))


if __name__ == '__main__':
    main()
