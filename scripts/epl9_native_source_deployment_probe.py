"""Strict native-source-v1 local load/package qualification, never camera access.

Reuses the existing byte-checked native interpreter and crosschecked bulk loops.
Storage reads copy only declared local bytes; flash requests stop at the existing
RAM-only trap. These boundaries do not establish hardware or recovery success.
The historical frozen/private generation selectors and defaults are unchanged.
"""

import argparse
import json
from pathlib import Path
import struct
import subprocess

from epl9_workspace_bridge import ROOT, BASE, MAIN, MAIN_SHA, sha
from epl9_placement import CANDIDATE, MODULE_SIZE, EARLY_START, EARLY_END
from epl9_load_sequence_probe import LocalStorageRead, STORAGE_BASE, DESTINATION, STACK, audit
from epl9_deployment_probe import SECTIONS
from epl9_recovery_audit import (WINDOWS, STATIC_WINDOWS, inspect_package,
    decoded_payload, load_code)
from epl9_package_native_probe import (LOOPS, crosscheck_loops, execute,
    expected_requests, translated_address)
from epl9_boot_recovery_audit import (section_endpoint, Boundary, SECTION_FLAGS,
    STACK as SECTION_STACK, SP as SECTION_SP, RETURN as SECTION_RETURN)
from epl9_video_audit import checked_listing
from mn103_tooling import default_reader, verify_reader
from mn103_subset import Memory, Region, Fault, parse_listing
from mn103_calls import CallMachine

GENERATION = 'native-source-v1'
CANDIDATE_NAME = 'Gold-Portra-v3-native-source-candidate.bin'
RESTORE_NAME = 'Stock-1101-main-osd-restore.bin'
NATIVE_MAIN_SHA = '2d003930675b47774e9ed3535ee49c64f56ff519bd6f1a33ddafd1a8c688b9b7'
MODULE_SHA = '89803a465ae76a81ae6b10055f0b8ff67dc30a1f162785bd8ee4f97e1c70d6e3'
OSD_SHA = '50141904c211fd16bc4c26b35cd52955f96a9e611ca062d84fe0169eeda21b3b'
STOCK_OSD_SHA = 'ee9a9c3ad1974dd212483ca7d012e51ae23083ce0119589a3b42996aa13ccf1e'
CANDIDATE_SHA = '10ac83e9beb9dd1bfd12aa6a021135706875d6ea245e58e20ec07fb917229421'
RESTORE_SHA = '10a7b949d1509ce627cb3c098c0a01a8ae5758fb2ce84b6c887e34b46e349387'
MODULE_DIRECTORY = ROOT/'local/cloud-reentry-native-source-20261111/run-v5/module'
HOOKS = (
    (0x60752202, '881cf9140c', 'dcfef0d4ff'),
    (0x6079d7f4, 'cd34fbf01cf8923d', 'dd6d3ed0fff01ccb'),
    (0x6079fb88, 'f1d3f1ef53', 'dc7e1ed0ff'),
    (0x60761c9e, 'fab4f002a000', 'dc37fbd3ffcb'),
)
LOAD_WINDOWS = {
    'early_startup': (0x60400020, 0x60400280),
    'early_chunk_planner': (0x60401561, 0x6040168b),
    'task_descriptors': (0x60418cc4, 0x60419c68),
    'section_endpoint_and_reader': (0x604229df, 0x60422ac1),
    'section_descriptors': (0x60405f94, 0x60406000),
}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def checked_manifest(document):
    require(document.get('generation') == GENERATION, 'requires exactly native-source-v1')
    require([row['file'] for row in document['files']] == [CANDIDATE_NAME, RESTORE_NAME],
            'requires exactly the native-source candidate and stock-return pair')


def checked_candidate(stock, candidate, module, manifest):
    require(sha(stock) == MAIN_SHA, 'wrong stock main')
    require(len(candidate) == len(stock) and sha(candidate) == NATIVE_MAIN_SHA,
            'wrong corrected native-source main')
    require(len(module) == MODULE_SIZE and sha(module) == MODULE_SHA,
            'wrong corrected native-source module')
    require(manifest['main_sha256'] == MAIN_SHA and
            int(manifest['module_base'], 0) == CANDIDATE and
            manifest['module_bytes'] == MODULE_SIZE and manifest['module_sha256'] == MODULE_SHA,
            'wrong module provenance')
    patches = tuple((int(p['address'], 0), p['before'], p['after'])
                    for p in manifest['candidate_patches'])
    require(patches == HOOKS, 'requires all four exact native-source hooks')
    expected = bytearray(stock)
    require(expected[CANDIDATE-BASE:CANDIDATE-BASE+MODULE_SIZE] == b'\xff'*MODULE_SIZE,
            'module source is not exact reviewed stock padding')
    expected[CANDIDATE-BASE:CANDIDATE-BASE+MODULE_SIZE] = module
    for address, before, after in HOOKS:
        at = address-BASE
        before, after = bytes.fromhex(before), bytes.fromhex(after)
        require(len(before) == len(after) and expected[at:at+len(before)] == before,
                'hook source changed')
        expected[at:at+len(after)] = after
    require(candidate == expected, 'candidate contains undeclared decoded main changes')


def protected_windows(stock, candidate):
    rows = []
    for name, (start, end) in (WINDOWS | STATIC_WINDOWS | LOAD_WINDOWS).items():
        source = stock[start-BASE:end-BASE]
        require(len(source) == end-start and source == candidate[start-BASE:end-BASE],
                'protected native source window changed: '+name)
        rows.append(dict(name=name, start=hex(start), end=hex(end), bytes=end-start,
                         sha256=sha(source), matches_stock=True))
    return rows


def checked_pair(packages):
    manifest_bytes = (packages/'manifest.json').read_bytes()
    document = json.loads(manifest_bytes)
    checked_manifest(document)
    pair = []
    for index, item in enumerate(document['files']):
        raw = (packages/item['file']).read_bytes()
        require(len(raw) == item['bytes'] == 52428800 and sha(raw) == item['sha256'],
                'package file identity changed')
        rows = inspect_package(raw)
        require(item.get('components') == rows, 'package manifest component metadata differs from actual file')
        expected = {0x100: NATIVE_MAIN_SHA, 0x101: OSD_SHA} if index == 0 else {
            0x100: MAIN_SHA, 0x101: STOCK_OSD_SHA}
        require([r['kind'] for r in rows] == ['0x100', '0x101'] and
                {int(r['kind'], 16): r['decoded_sha256'] for r in rows} == expected,
                'wrong generation or component identity')
        require(all(r['package_bytes'] == 26214400 for r in rows), 'wrong component size')
        require(sha(raw) == (CANDIDATE_SHA if index == 0 else RESTORE_SHA),
                'requires exact generation-specific encoded package')
        pair.append((item, raw, rows))
    main_row = pair[0][2][0]
    at = int(main_row['offset'], 16)
    candidate = decoded_payload(pair[0][1][at+32:at+main_row['package_bytes']-32])
    require(sha(candidate) == NATIVE_MAIN_SHA, 'executing main must come from exact candidate package')
    return document, manifest_bytes, pair, candidate


def decode_load_code(stock, out, reader):
    code = {}
    # Descriptor data is intentionally not passed through the disassembler.
    for name in ('early_startup', 'early_chunk_planner', 'section_endpoint_and_reader'):
        start, end = LOAD_WINDOWS[name]
        listing = subprocess.check_output([str(reader.resolve()), str(MAIN.resolve()),
            hex(BASE), hex(start-BASE), hex(end-BASE)], text=True)
        checked_listing(listing, stock, start, end)
        code.update(parse_listing(listing, stock, BASE))
        (out/(name+'.tsv')).write_text(listing, encoding='utf-8')
    # Native section read arguments use this translator before the trapped read.
    start, end = WINDOWS['address_translation']
    listing = subprocess.check_output([str(reader.resolve()), str(MAIN.resolve()),
        hex(BASE), hex(start-BASE), hex(end-BASE)], text=True)
    checked_listing(listing, stock, start, end)
    code.update(parse_listing(listing, stock, BASE))
    (out/'load_address_translation.tsv').write_text(listing, encoding='utf-8')
    return code


def early_control(candidate, code, *, drop_last=False, truncate_source=False,
                  truncate_destination=False):
    """Run actual early planner; missing/short local bytes must be rejected."""
    length = EARLY_END-EARLY_START
    data = bytearray(b'\xa5'*16+b'\xcd'*length+b'\xa5'*16)
    stack = bytearray(4096)
    struct.pack_into('<I', stack, 2056, 0x406f0000)
    class Read(LocalStorageRead):
        def apply(self, m):
            if drop_last and m.r['d1'] == 0x40780000:
                self.calls.append(dict(deliberately_dropped=True, source=hex(m.r['d1']),
                                       bytes=m.r['a0'], physical_read=False))
                m.r['d0'] = 0
                return self.calls[-1]
            try:
                return super().apply(m)
            except Fault as exc:
                exc.native_checkpoint = dict(stage='local-storage-read-boundary',
                    native_callsite=hex(m.trace[-1]), source=hex(m.r['d1']),
                    destination=hex(m.r['d0']), bytes=m.r['a0'])
                raise
    source = candidate[:EARLY_END-BASE-1] if truncate_source else candidate
    read = Read(source, DESTINATION, length)
    # Short destination is a distinct mapped-memory failure, not a claimed read error.
    backing = data[:-17] if truncate_destination else data
    m = CallMachine(code, Memory([Region(BASE, candidate), Region(STACK, stack, True),
        Region(DESTINATION-16, backing, True)]),
        dict(sp=STACK+2048, a2=DESTINATION, d2=length),
        models={0x604009bf: read, 0x60400d2f: read})
    stop = m.run(0x60401561, [0x6040168b])
    require(stop.get('pc') == 0x6040168b and m.r['sp'] == STACK+2048,
            'early native planner did not return: '+str(stop))
    if data[16:-16] != candidate[EARLY_START-BASE:EARLY_END-BASE]:
        exc = ValueError('native early bytes missing or read omitted')
        exc.native_checkpoint = dict(stage='after-native-planner-return',
            pc=hex(stop['pc']), native_chunk_calls=read.calls, stack_balanced=True)
        raise exc
    require(data[:16]+data[-16:] == b'\xa5'*32, 'early destination guards changed')
    loaded_module = bytes(data[16+CANDIDATE-EARLY_START:16+CANDIDATE-EARLY_START+MODULE_SIZE])
    require(sha(loaded_module) == MODULE_SHA, 'loaded module identity differs')
    return dict(native_chunk_calls=read.calls, bytes=length,
        loaded_module_sha256=sha(loaded_module), module_bytes=MODULE_SIZE, module_exact_bytes=True,
        loaded_sha256=sha(data[16:-16]), exact_bytes=True, guards_intact=True,
        executing_main_sha256=sha(candidate), local_storage_completion_modeled=True,
        physical_read=False)


EARLY_NEGATIVES = (
    ('dropped-last-read', dict(drop_last=True), ValueError,
     'native early bytes missing or read omitted'),
    ('truncated-source', dict(truncate_source=True), Fault,
     'local storage read outside declared aligned bounds'),
    ('truncated-destination', dict(truncate_destination=True), Fault,
     'local storage destination truncated'),
)


def early_negative_controls(candidate, code):
    """Reject unrelated emulator/setup failures instead of counting them as evidence."""
    rows = []
    for label, options, expected_type, expected_reason in EARLY_NEGATIVES:
        try:
            early_control(candidate, code, **options)
        except (ValueError, Fault) as exc:
            if type(exc) is not expected_type or str(exc) != expected_reason:
                raise ValueError('early negative '+label+' failed for an unrelated reason: '+
                                 type(exc).__name__+': '+str(exc)) from exc
            rows.append(dict(control=label, rejected=True, reason=str(exc),
                expected_reason=expected_reason, exact_failure_reason_matched=True,
                exception_type=type(exc).__name__,
                native_checkpoint=getattr(exc, 'native_checkpoint', None)))
        else:
            raise ValueError('early load negative was accepted: '+label)
    return rows


class LocalSectionRead:
    name = 'declared-local-section-read'

    def __init__(self, candidate, start, end, source, destination, backing):
        self.candidate, self.start, self.end = candidate, start, end
        self.source, self.destination, self.backing = source, destination, backing
        self.calls = []

    def validate(self, m, mask, frame):
        if (mask, frame) != (0xf0, 20):
            raise Fault('unexpected section-read ABI')

    def apply(self, m):
        size = self.end-self.start
        if (m.r['a0'], m.r['a1'], m.r['d0'], m.r['d1']) != (
                self.destination, self.source, size, 257):
            raise Fault('native section request differs from exact descriptor')
        # Map the declared source alias back to this local decoded main only.
        at = (self.source & 0x3fffffff)-(STORAGE_BASE & 0x3fffffff)
        if at != self.start-BASE or not 0 <= at <= at+size <= len(self.candidate):
            raise Fault('section source outside exact local candidate')
        if size:
            region, offset = m.memory.region(self.destination, 4, write=True)
            if offset+size > len(region.data):
                raise Fault('section destination truncated')
            region.data[offset:offset+size] = self.candidate[at:at+size]
        row = dict(source=hex(self.source), destination=hex(self.destination), bytes=size,
                   loaded_sha256=sha(self.candidate[at:at+size]), physical_read=False)
        self.calls.append(row)
        m.r['d0'] = 0
        return row


def hook_loads(candidate, code):
    endpoints = {ident: section_endpoint(candidate, code, ident) for ident in range(1, 10)}
    executable = {pc: op for pc, op in code.items() if not 0x604229df <= pc < 0x60422a3c}
    rows = []
    for ident in range(1, 10):
        start, source, destination = struct.unpack_from('<3I', candidate,
            0x60405f94-BASE+(ident-1)*12)
        end = endpoints[ident]
        require((start, end) == SECTIONS[ident-1], 'native section endpoints changed')
        hits = [(address, bytes.fromhex(after)) for address, _, after in HOOKS
                if start <= address and address+len(bytes.fromhex(after)) <= end]
        if not hits:
            continue
        source, destination = translated_address(source), translated_address(destination)
        backing = bytearray(b'\xa5'*16+b'\xcd'*(end-start)+b'\xa5'*16)
        read = LocalSectionRead(candidate, start, end, source, destination, backing)
        memory = Memory([Region(BASE, candidate, False, 'exact candidate ROM'),
            Region(SECTION_STACK, bytearray(0x10000), True, 'caller stack'),
            Region(SECTION_FLAGS, bytearray(4), True, 'declared section flags'),
            Region(destination-16, backing, True, 'guarded local section')])
        models = {0x604229df: Boundary('endpoint-RETS-bridge', (0, 0), endpoints),
            0x6043ae0d: read, 0x604022d4: Boundary('diagnostic-suppressed', (0xa0, 40)),
            0x6056838a: Boundary('section-7-extra-init-suppressed', (0xa0, 12))}
        m = CallMachine(executable, memory, dict(sp=SECTION_SP, d0=ident), models=models)
        m.enter(0x60422a3c, SECTION_RETURN, 0xf0, 24)
        stop = m.run(0x60422a3c, [SECTION_RETURN], limit=1000)
        require(stop.get('pc') == SECTION_RETURN and m.r['sp'] == SECTION_SP,
                'native section load did not return: '+str(stop))
        require(len(read.calls) == 1 and m.r['d0'] == 1 << (ident-1) and
                memory.read(SECTION_FLAGS, 4) == 1 << (ident-1), 'native section result mismatch: '+str((len(read.calls), hex(m.r['d0']), hex(memory.read(SECTION_FLAGS, 4)))))
        require(backing[16:-16] == candidate[start-BASE:end-BASE] and
                backing[:16]+backing[-16:] == b'\xa5'*32, 'section bytes/guards differ')
        hooks = []
        for address, expected in hits:
            at = address-start+16
            require(backing[at:at+len(expected)] == expected, 'hook was not loaded')
            hooks.append(dict(address=hex(address), bytes=len(expected), sha256=sha(expected),
                              exact_bytes=True))
        rows.append(dict(section=ident, start=hex(start), end=hex(end), request=read.calls[0],
            hooks=hooks, native_return_value=hex(m.r['d0']), loaded_flag_set=True,
            native_endpoint_instructions_executed=True,
            endpoint_return_uses_explicit_rets_bridge=True, guards_intact=True, stack_balanced=True))
    require(sum(len(row['hooks']) for row in rows) == len(HOOKS), 'not all four hooks covered')
    return dict(sections=rows, hook_count=len(HOOKS),
        all_native_endpoints=[dict(section=i, start=hex(SECTIONS[i-1][0]), end=hex(endpoints[i]))
                              for i in range(1, 10)],
        local_storage_completion_modeled=True, physical_storage_or_cache_verified=False,
        full_boot_executed=False)


def native_packages(stock, candidate, pair, code):
    require(all(candidate[pc-BASE:pc-BASE+len(op[0])] == op[0] for pc, op in code.items()),
            'candidate changes a loaded validator instruction')
    checks = crosscheck_loops(stock, code)
    results = []
    for index, (item, raw, rows) in enumerate(pair):
        executing = stock if index == 0 else candidate
        write_rows = expected_requests(rows)
        decoded_expected = b''.join(raw[int(r['offset'],16):int(r['offset'],16)+32] +
            decoded_payload(raw[int(r['offset'],16)+32:int(r['offset'],16)+r['package_bytes']-32]) +
            raw[int(r['offset'],16)+r['package_bytes']-32:int(r['offset'],16)+r['package_bytes']]
            for r in rows)
        checked_decoded = None
        for mode in (0, 2, 1):
            observed, decoded, _ = execute(executing, code,
                checked_decoded if mode == 1 else raw, mode=mode)
            if mode == 2:
                checked_decoded = decoded
            require(observed['return_value'] == '0x0' and decoded == decoded_expected,
                    'native full-size validator differs from exact host decode')
            requests = observed['backend_requests']
            require(len(requests) == (0 if mode == 2 else 2), 'unexpected flash trap count')
            for request, row in zip(requests, write_rows):
                require(request['kind'] == row['kind'] and request['bytes'] == row['package_bytes'] and
                    request['decoded_payload_sha256'] == row['decoded_sha256'] and
                    request['checksum'] == 0 and int(request['destination'],16) ==
                    translated_address(int(row['destination'],16)), 'wrong trapped write request')
            results.append(dict(file=item['file'], executing_main_sha256=sha(executing), **observed))
        for label, offset in [('corrupt-first', 48), ('corrupt-second', int(rows[1]['offset'],16)+48)]:
            damaged = bytearray(raw); damaged[offset] ^= 1
            negative, _, _ = execute(executing, code, bytes(damaged))
            require(negative['return_value'] == '0x3211' and not negative['backend_requests'],
                    'corruption not rejected before write trap')
            results.append(dict(file=item['file'], executing_main_sha256=sha(executing),
                                negative_control=label, **negative))
        for label, injected, expected in (
                ('both-writes-report-error', 0x3105, '0x3105'),
                ('osd-error-main-success', {0x101: 0x3105}, '0x0'),
                ('osd-success-main-error', {0x100: 0x3105}, '0x3105')):
            observed, _, _ = execute(executing, code, raw, backend_result=injected)
            require(observed['return_value'] == expected and
                [r['kind'] for r in observed['backend_requests']] == ['0x101','0x100'],
                'native multi-component error behavior changed')
            results.append(dict(file=item['file'], executing_main_sha256=sha(executing),
                negative_control=label, earlier_component_error_masked=label == 'osd-error-main-success',
                **observed))
        print(json.dumps(dict(file=item['file'], full_size_cases=8,
            executing_main_sha256=sha(executing), physical_writes=False)), flush=True)
    return dict(schema='epl9-native-source-package-validation-v1', generation=GENERATION,
        candidate_main_from_exact_package=True, candidate_main_sha256=sha(candidate),
        native_loop_crosschecks=checks, cases=results, native_write_order=['0x101','0x100'],
        loop_windows={hex(a): dict(end=hex(b), name=n, sha256=sha(stock[a-BASE:b-BASE]))
                      for a, (b,n) in LOOPS.items()},
        earlier_component_write_error_can_be_masked=True, accelerated=True,
        lower_writer_executed=False, physical_writes=False, physical_restore_verified=False,
        camera_accessed=False, install_ready=False)


def run(packages, out):
    out = out.resolve()
    require(not out.exists() and out.is_relative_to((ROOT/'local').resolve()),
            'new ignored output directory required')
    document, manifest_bytes, pair, candidate = checked_pair(packages)
    stock = MAIN.read_bytes()
    module = (MODULE_DIRECTORY/'epl9-films-native.bin').read_bytes()
    module_manifest_bytes = (MODULE_DIRECTORY/'manifest.json').read_bytes()
    checked_candidate(stock, candidate, module, json.loads(module_manifest_bytes))
    protected = protected_windows(stock, candidate)
    out.mkdir()
    reader = default_reader()
    reader_sha = verify_reader(reader)
    load = decode_load_code(stock, out, reader)
    # Existing full startup/initialization overlap audit, using this exact main.
    startup = audit(candidate, candidate, load)
    early = early_control(candidate, load)
    negatives = early_negative_controls(candidate, load)
    sections = hook_loads(candidate, load)
    loader = dict(schema='epl9-native-source-load-sequence-v1', generation=GENERATION,
        candidate_sha256=sha(candidate), module_sha256=sha(module), module_bytes=MODULE_SIZE,
        module_base=hex(CANDIDATE), early=early, startup=startup, hook_loads=sections,
        negative_controls=negatives, protected_source_windows=protected,
        full_boot_executed=False, all_runtime_writers_excluded=False,
        camera_accessed=False, physical_storage_and_cache_verified=False, install_ready=False)
    (out/'load-sequence.json').write_text(json.dumps(loader, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(load_bytes=early['bytes'], native_read_chunks=len(early['native_chunk_calls']),
        module_sha256=MODULE_SHA, hook_count=sections['hook_count'], negative_controls=len(negatives))), flush=True)
    code = load_code(stock, out, reader)
    validator = native_packages(stock, candidate, pair, code)
    common = dict(package_manifest_sha256=sha(manifest_bytes), reader_sha256=reader_sha,
        module_manifest_sha256=sha(module_manifest_bytes), source_sha256=sha(Path(__file__).read_bytes()),
        dependencies={name: sha((ROOT/'scripts'/name).read_bytes()) for name in (
            'epl9_package_native_probe.py', 'epl9_load_sequence_probe.py',
            'epl9_recovery_audit.py', 'epl9_boot_recovery_audit.py',
            'epl9_deployment_probe.py', 'epl9_v3_package.py', 'epl9_workspace_bridge.py',
            'epl9_placement.py', 'epl9_video_audit.py',
            'mn103_calls.py', 'mn103_subset.py', 'mn103_tooling.py')})
    loader.update(common)
    validator.update(common)
    (out/'load-sequence.json').write_text(json.dumps(loader, indent=2)+'\n', encoding='utf-8')
    (out/'validation.json').write_text(json.dumps(validator, indent=2)+'\n', encoding='utf-8')
    report = dict(schema='epl9-native-source-deployment-v1', generation=GENERATION,
        **common, candidate_main_from_exact_package=True, candidate_main_sha256=sha(candidate),
        files=document['files'], reports={name: sha((out/name).read_bytes())
            for name in ('load-sequence.json','validation.json')},
        native_bulk_crosschecks=len(validator['native_loop_crosschecks']),
        full_size_native_cases=len(validator['cases']), protected_source_windows=len(protected),
        exact_hooks_loaded=sections['hook_count'], camera_accessed=False, physical_writes=False,
        physical_restore_verified=False, install_ready=False)
    (out/'manifest.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(out=str(out), full_size_cases=len(validator['cases']), install_ready=False)), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packages', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    run(args.packages, args.out)
