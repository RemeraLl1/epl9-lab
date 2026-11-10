"""Firmware-free differential checks for the experimental SD record validator.

GNU independently decodes the standalone and placed-state validators. Both
execute against the same generated corpus and the host codec. This does not
exercise stock file services, session shutdown, physical SD or camera menus.
All generated data and reports stay below a new ignored local/ directory.
"""
import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import random
import struct
import zlib

from epl9_workspace_bridge import ROOT
from epl9_sd_loader import build as build_loader, assemble
from epl9_sd_loader_probe import sample_recipe
from epl9_sd_state import build as build_state
from epl9_sd_placement import STATE_BASE, relocate_constants
from epl9_sd_processing_probe import decode
from epl9_sd_recipes import Recipe, FILE_BYTES, pack_recipe, unpack_recipe
from mn103_tooling import default_reader, reader_provenance
from mn103_subset import Memory, Region
from mn103_calls import CallMachine

INPUT, STACK, STOP = 0x18000000, 0x19000000, 0x1a000000
GUARD = b'\xa5'*16
LIMIT = 200000
SHUTDOWN_FILES = (
    'docs/epl9-sd-session-shutdown.md', 'scripts/epl9_sd_session.py',
    'firmware_src/epl9_sd_session.s.in', 'scripts/epl9_sd_session_probe.py',
    'scripts/test_epl9_sd_session.py',
)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def reseal(raw, offset, fmt, value):
    data = bytearray(raw)
    struct.pack_into('<'+fmt, data, offset, value)
    struct.pack_into('<I', data, 16, 0)
    struct.pack_into('<I', data, 16, zlib.crc32(data))
    return bytes(data)


def corpus():
    """Yield explicitly valid/invalid records; no manufacturer data is used."""
    base = sample_recipe()
    raw = pack_recipe(base)
    yield 'valid/base', raw, True
    for name in ('A', 'A'*31, ' ~'):
        yield 'valid/name/'+name, pack_recipe(replace(base, name=name)), True
    for ident in (1, 0x80000000, 0xffffffff):
        yield f'valid/id/{ident}', pack_recipe(replace(base, recipe_id=ident)), True
    for n in (0, 4095):
        yield f'valid/constant-gamma/{n}', pack_recipe(replace(base, gamma=(n,)*256)), True
    for row in range(12):
        for component, limit in enumerate((1000, 240, 100)):
            offset = 64+row*6+component*2
            for sign in (-1, 1):
                yield f'valid/hsl/{offset}/{sign}', reseal(raw, offset, 'h', sign*limit), True
                yield f'invalid/hsl/{offset}/{sign}', reseal(raw, offset, 'h', sign*(limit+1)), False
    for offset, limit in ((136, 2), (138, 7), (140, 7), (142, 7)):
        for sign in (-1, 1):
            yield f'valid/tone/{offset}/{sign}', reseal(raw, offset, 'h', sign*limit), True
            yield f'invalid/tone/{offset}/{sign}', reseal(raw, offset, 'h', sign*(limit+1)), False
    for offset in (144, 146):
        for value in (512, 2048):
            yield f'valid/wb/{offset}/{value}', reseal(raw, offset, 'H', value), True
        for value in (0, 511, 2049, 65535):
            yield f'invalid/wb/{offset}/{value}', reseal(raw, offset, 'H', value), False
    # A separate PRNG leaves global test state alone; the corpus is reproducible.
    rng = random.Random(0xe91101)
    for i in range(16):
        recipe = Recipe(rng.randrange(1, 2**32), f'Synthetic {i}',
            tuple(tuple(rng.randint(-n, n) for n in (1000, 240, 100)) for _ in range(12)),
            rng.randint(-2, 2), tuple(rng.randint(-7, 7) for _ in range(3)),
            tuple(rng.randint(512, 2048) for _ in range(2)),
            tuple(sorted(rng.randint(0, 4095) for _ in range(256))))
        yield f'valid/random/{i}', pack_recipe(recipe), True
    for offset in range(FILE_BYTES):
        data = bytearray(raw)
        data[offset] ^= 1
        yield f'invalid/crc/{offset}', bytes(data), False
    for offset, fmt, value in ((0, 'I', 0), (4, 'H', 1), (6, 'H', 63),
            (8, 'H', 1420), (10, 'H', 1100), (12, 'I', 659),
            (20, 'I', 0), (24, 'I', 2), (28, 'I', 1)):
        yield f'invalid/header/{offset}', reseal(raw, offset, fmt, value), False
    for offset in range(32, 64):
        yield f'invalid/name/{offset}', reseal(raw, offset, 'B', 64), False
    yield 'invalid/empty-name', reseal(raw, 32, 'B', 0), False
    for index in range(256):
        yield f'invalid/gamma-range/{index}', reseal(raw, 148+index*2, 'H', 4096), False
    for index in (1, 128, 255):
        source = reseal(raw, 148, 'H', 16) if index == 1 else raw
        value = 0 if index == 1 else (index-1)*16-1
        yield f'invalid/gamma-order/{index}', reseal(source, 148+index*2, 'H', value), False


def host_accepts(raw):
    try:
        unpack_recipe(raw)
        return True
    except ValueError:
        return False


def relocated_state(defaults):
    """Use the placed builder's state relocation without a fake stock image."""
    original = build_state(defaults)
    constants = {k: STATE_BASE+v-original['base'] for k, v in original['constants'].items()}
    source = relocate_constants(original['source'],
        dict(zip(original['constants'].values(), constants.values())))
    code, symbols, rows = assemble(source, STATE_BASE)
    if len(code) > 4096:
        raise ValueError('relocated state code overlaps data')
    data = bytearray(original['data'])
    data[:4096] = bytes(4096)
    data[:len(code)] = code
    return dict(original, source=source, data=bytes(data), symbols=symbols, rows=rows,
        code_bytes=len(code), base=STATE_BASE, constants=constants)


def native_accepts(module, raw):
    if type(raw) is not bytes or len(raw) != FILE_BYTES:
        raise ValueError('fixed-size validator requires exactly 660 bytes')
    record = bytearray(GUARD+raw+GUARD)
    stack = bytearray(GUARD+bytes(4096)+GUARD)
    top = STACK+2048
    saved = dict(d2=0x22222222, d3=0x33333333, a2=0x44444444, a3=0x55555555)
    memory = Memory([
        Region(module['base'], module['data'], False, 'GNU-decoded authored module'),
        Region(INPUT-16, record, False, 'read-only bounded recipe'),
        Region(STACK-16, stack, True, 'guarded stack'),
    ])
    machine = CallMachine(module['code'], memory, dict(sp=top, a0=INPUT, **saved))
    result = machine.run(machine.enter(module['symbols']['sd_validate'], STOP, 0xf0, 24),
                         [STOP], limit=LIMIT)
    if (result.get('pc') != STOP or machine.r['sp'] != top or
            any(machine.r[k] != v for k, v in saved.items()) or
            record != GUARD+raw+GUARD or stack[:16] != GUARD or stack[-16:] != GUARD or
            any(e['op'] == 'call' for e in machine.events)):
        raise ValueError('validator violated return/register/input/guard/no-call contract')
    if machine.r['d0'] not in (0, 1):
        raise ValueError('unexpected validator result')
    return machine.r['d0'] == 0, len(machine.trace)


def run(out, reader):
    out = Path(out).resolve()
    if out.exists() or not out.is_relative_to((ROOT/'local').resolve()):
        raise ValueError('use a new ignored local output directory')
    provenance = reader_provenance(reader)
    sources = sorted(set((ROOT/'scripts').glob('*.py')) |
                     set((ROOT/'firmware_src').glob('*.s.in')))
    fingerprints = {str(p.relative_to(ROOT)): digest(p.read_bytes()) for p in sources}
    cases = list(corpus())
    if len({name for name, _, _ in cases}) != len(cases):
        raise ValueError('duplicate corpus case')
    for name, raw, expected in cases:
        if host_accepts(raw) != expected:
            raise ValueError('host codec disagrees with authored expectation: '+name)
    defaults = [pack_recipe(sample_recipe())]*2
    loader = build_loader()
    loader['code_bytes'] = len(loader['data'])
    modules = dict(standalone=loader, placed_state=relocated_state(defaults))
    out.mkdir(parents=True)
    for name, module in modules.items():
        decode(module, out/name, reader)
    rows, maxima = [], {name: 0 for name in modules}
    for i, (name, raw, expected) in enumerate(cases):
        instructions = {}
        for implementation, module in modules.items():
            accepted, count = native_accepts(module, raw)
            if accepted != expected:
                raise ValueError(f'host/native disagreement: {implementation} {name}')
            instructions[implementation] = count
            maxima[implementation] = max(maxima[implementation], count)
        rows.append(dict(case=name, record_sha256=digest(raw), accepted=expected,
                         native_instructions=instructions))
        if (i+1) % 100 == 0:
            print(f'Checked {i+1}/{len(cases)} records against both GNU-decoded validators', flush=True)
    if any(digest(p.read_bytes()) != fingerprints[str(p.relative_to(ROOT))] for p in sources):
        raise ValueError('research source changed during probe')
    report = dict(schema='epl9-sd-source-only-validator-v1',
        model=1330, downloaded_build=1101, reader=provenance,
        source_sha256=fingerprints, corpus_sha256=digest(b''.join(
            name.encode()+b'\0'+raw+bytes([expected]) for name, raw, expected in cases)),
        record_cases=len(rows), accepted_cases=sum(x['accepted'] for x in rows),
        rejected_cases=sum(not x['accepted'] for x in rows),
        native_executions=len(rows)*len(modules), instruction_limit=LIMIT,
        max_native_instructions=maxima,
        modules={name: dict(base=hex(m['base']), bytes=len(m['data']),
            code_bytes=m['code_bytes'], sha256=digest(m['data']),
            decoded_instructions=len(m['code'])) for name, m in modules.items()},
        cases=rows,
        shutdown_transfer={p: (dict(present=True, sha256=digest((ROOT/p).read_bytes()))
                                if (ROOT/p).is_file() else dict(present=False))
                           for p in SHUTDOWN_FILES},
        source_only_validation_passed=True, archived_exact_stock_probes_reproduced=False,
        stock_firmware_used=False, full_session_shutdown_qualified=False,
        native_file_service_executed=False, physical_sd_tested=False,
        native_menu_slots_assigned=False, camera_accessed=False, install_ready=False)
    path = out/'validation.json'
    path.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k: report[k] for k in ('record_cases', 'accepted_cases', 'rejected_cases',
        'native_executions', 'source_only_validation_passed', 'stock_firmware_used', 'install_ready')}))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reader', type=Path, default=default_reader())
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    run(args.out, args.reader)
