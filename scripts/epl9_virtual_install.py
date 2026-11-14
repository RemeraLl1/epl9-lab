"""Native E-PL9 updater -> persistent logical flash -> independent reopen/readback.

No camera, USB, card, network or physical memory API. Real updater, selector and
program/readback-wrapper instructions execute in the existing bounded MN103
interpreter. Only program/read storage leaves are explicit software models.
Every scenario enters main-resident updater directly, not from hardware reset.
Private component files stay under ignored local/. They are not releases.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import struct
import subprocess
from dataclasses import asdict

from epl9_recovery_audit import (ROOT, BASE, BUFFER, STACK, SP, RESULT, RETURN,
    WINDOWS, STATIC_WINDOWS, Boundary, MAIN_NAME, MAIN_SHA, sha, inspect_package,
    decoded_payload, load_code, fixture)
from epl9_video_audit import checked_listing
from epl9_v3_package import sum32
from epl9_package_native_probe import LoopMachine, span
from epl9_virtual_flash import VirtualFlashStore, FaultPlan
from mn103_calls import CallMachine
from mn103_subset import Memory, Region, Fault, parse_listing
from mn103_tooling import default_reader, verify_reader

GENERATION = 'native-source-v1'
DEFAULT_PACKAGES = ROOT/'local/cloud-native-source-package-20261111/package-final'
CANDIDATE_NAME = 'Gold-Portra-v3-native-source-candidate.bin'
RESTORE_NAME = 'Stock-1101-main-osd-restore.bin'
CANDIDATE_SHA = '10ac83e9beb9dd1bfd12aa6a021135706875d6ea245e58e20ec07fb917229421'
RESTORE_SHA = '10a7b949d1509ce627cb3c098c0a01a8ae5758fb2ce84b6c887e34b46e349387'
CANDIDATE_MAIN_SHA = '2d003930675b47774e9ed3535ee49c64f56ff519bd6f1a33ddafd1a8c688b9b7'
SIZES = {'main': 26214400, 'osd': 26214400}
BASES = {'main': 0x406e0000, 'osd': 0x421e0000}
KINDS = {'main': 0x100, 'osd': 0x101}
LOWER_SUM, LOWER_SUM_END = 0x6043a110, 0x6043a116
LOWER_WINDOWS = ('write_selector', 'access_mode', 'program_readback_wrapper')


def write_json(path, document):
    path = Path(path)
    with path.open('x', encoding='utf-8') as out:
        json.dump(document, out, indent=2)
        out.write('\n')
    return sha(path.read_bytes())


def decode_pair(raw):
    rows = inspect_package(raw)
    if [r['kind'] for r in rows] != ['0x100', '0x101']:
        raise ValueError('requires exactly main then OSD')
    result = {}
    for name, row in zip(('main', 'osd'), rows):
        at, size = int(row['offset'], 16), row['package_bytes']
        if size != SIZES[name] or int(row['destination'], 16) != BASES[name]:
            raise ValueError('unexpected component extent/destination')
        block = raw[at:at+size]
        result[name] = block[:32]+decoded_payload(block[32:-32])+block[-32:]
    return result


def component_name(address, length):
    if address == 0x806e0000:
        address = 0x406e0000
    found = [name for name, base in BASES.items() if address == base and length == SIZES[name]]
    if len(found) != 1:
        raise Fault('storage leaf outside declared whole-component layout')
    return found[0]


def build_code(image, directory=None):
    reader = default_reader()
    code = load_code(image, directory, reader)
    image_path = ROOT/'local/epl9-1101-analysis/decoded'/MAIN_NAME
    for name in LOWER_WINDOWS:
        start, end = STATIC_WINDOWS[name]
        listing = subprocess.check_output([str(reader), str(image_path), hex(BASE), hex(start-BASE), hex(end-BASE)], text=True)
        checked_listing(listing, image, start, end)
        code.update(parse_listing(listing, image, BASE))
        if directory:
            (directory/(name+'.tsv')).write_text(listing, encoding='utf-8')
    # Preserve the exact extra accelerated window, not an inferred loop.
    expected = bytes.fromhex('7652e7f102d9')
    if image[LOWER_SUM-BASE:LOWER_SUM_END-BASE] != expected:
        raise ValueError('native lower checksum loop changed')
    return code


class PowerLoss(RuntimeError):
    """A modeled loss of execution, deliberately not a native return code."""


class NativeInstallMachine(LoopMachine):
    def __init__(self, *args, accelerate_lower=True, **kwargs):
        super().__init__(*args, **kwargs)
        self.accelerate_lower = accelerate_lower

    def run(self, start, stops=(), limit=300000):
        if not self.accelerate_lower:
            return super().run(start, stops, limit)
        pc, beginning, stops = start, len(self.trace), set(stops)
        while True:
            remaining = limit-(len(self.trace)-beginning)
            if remaining <= 0:
                raise Fault('native installation instruction limit')
            result = super().run(pc, stops | {LOWER_SUM}, remaining)
            pc = result.get('pc')
            if pc in stops or pc != LOWER_SUM:
                return result
            count = self.r['d2']
            if self.loop != LOWER_SUM or not 1 <= count <= self.package_size//4:
                raise Fault('invalid lower checksum loop extent')
            n = count-1
            if n:
                region, at = span(self, self.r['a2'], n*4)
                before = bytes(region.data[at:at+n*4])
                self.r['d3'] = (self.r['d3']+sum32(before)) & 0xffffffff
                self.r['a2'] += n*4
                self.r['d2'] = 1
                self.events.append(dict(op='bulk_lower_readback_checksum', loop=hex(pc),
                    bytes=n*4, accelerated_iterations=n, input_sha256=sha(before),
                    final_iteration_native=True))
            final = CallMachine.run(self, pc, {LOWER_SUM_END}, 100)
            if final.get('pc') != LOWER_SUM_END:
                raise Fault('native lower checksum final iteration failed')
            pc = LOWER_SUM_END


def crosscheck_lower_checksum(code):
    """Compare the new readback-loop acceleration with exact step execution."""
    rows = []
    for size in (16, 32, 80, 256, 4096):
        for damaged in (False, True):
            data = bytearray((i*17+3)&255 for i in range(size))
            if damaged:
                data[size//2] ^= 0x51
            states = []
            instructions = []
            for accelerated in (False, True):
                memory = Memory([Region(BUFFER, bytearray(data), False, 'checksum fixture')])
                cpu = NativeInstallMachine(code, memory, dict(d2=size, a2=BUFFER),
                    accelerate_lower=accelerated)
                cpu.package_size = size
                stop = cpu.run(0x6043a109, {LOWER_SUM_END}, 300000)
                if stop.get('pc') != LOWER_SUM_END:
                    raise Fault('checksum crosscheck did not finish')
                states.append((dict(cpu.r), (cpu.n, cpu.z, cpu.c, cpu.v), cpu.loop,
                    bytes(memory.regions[0].data)))
                instructions.append(len(cpu.trace))
            if states[0] != states[1] or states[1][0]['d3'] != sum32(data):
                raise Fault('lower checksum acceleration differs from step execution')
            rows.append(dict(bytes=size, damaged=damaged, full_register_flags_memory_equal=True,
                step_instructions=instructions[0], accelerated_instructions=instructions[1]))
    return rows


class StoreHandle:
    def __init__(self, store):
        self.store, self.reopens = store, 0

    def reopen(self):
        path = self.store.path
        self.store.close(checkpoint=False)
        self.store = VirtualFlashStore.open(path)
        self.reopens += 1


class ProgramLeaf:
    name = 'persistent-logical-program-leaf'

    def __init__(self, handle, events, target=None, plan=None):
        self.handle, self.events, self.target, self.plan = handle, events, target, plan

    def validate(self, cpu, mask, frame):
        if (mask, frame) != (0xf0, 24):
            raise Fault('unexpected native program leaf ABI')

    def apply(self, cpu):
        address, source, length = cpu.r['a0'], cpu.r['a1'], cpu.r['d0']
        name = component_name(address, length)
        region, at = span(cpu, source, length)
        data = bytes(region.data[at:at+length])
        if data[:4] != b'OE\x13\x30' or struct.unpack_from('<H', data, 20)[0] != KINDS[name]:
            raise Fault('native program data does not match destination component')
        fault = self.plan if name == self.target else None
        result = self.handle.store.program_component(name, data, fault)
        self.handle.reopen()
        event = dict(result, native_operation='program', native_entry='0x60439f38',
            native_destination=hex(address), source=hex(source), bytes=length,
            requested_envelope_sha256=sha(data), requested_payload_sha256=sha(data[32:-32]),
            checksum=sum32(data), persistent_reopen=True)
        self.events.append(event)
        if not result['returned']:
            raise PowerLoss('modeled power loss during '+name+' '+result['stage'])
        cpu.r['d0'] = result['return_code']
        return dict(component=name, bytes=length, return_code=result['return_code'],
                    persistent_reopen=True, requested_envelope_sha256=sha(data))


class ReadLeaf:
    name = 'persistent-logical-readback-leaf'

    def __init__(self, handle, events, error_target=None):
        self.handle, self.events, self.error_target = handle, events, error_target

    def validate(self, cpu, mask, frame):
        if (mask, frame) != (0xf0, 32):
            raise Fault('unexpected native readback leaf ABI')

    def apply(self, cpu):
        address, destination, length = cpu.r['a0'], cpu.r['a1'], cpu.r['d1']
        name = component_name(address, length)
        self.handle.reopen()
        if name == self.error_target:
            cpu.r['d0'] = 0x3102
            self.events.append(dict(stage='readback', component=name, native_entry='0x604014c6',
                bytes=length, return_code=0x3102, copied=False, persistent_reopen=True))
        else:
            data = self.handle.store.read_component(name)
            region, at = span(cpu, destination, length, True)
            region.data[at:at+length] = data
            cpu.r['d0'] = 0
            self.events.append(dict(stage='readback', component=name, native_entry='0x604014c6',
                bytes=length, return_code=0, copied=True, persistent_reopen=True,
                envelope_sha256=sha(data), payload_sha256=sha(data[32:-32]), checksum=sum32(data)))
        return dict(component=name, bytes=length, return_code=cpu.r['d0'], persistent_reopen=True)


def execute(image, code, package, handle, *, mode=0, fault_target=None, fault_plan=None,
            readback_error_target=None, accelerate_lower=True):
    if any(image[pc-BASE:pc-BASE+len(op[0])] != op[0] for pc, op in code.items()):
        raise Fault('loaded native instructions differ from executing image')
    operations = []
    models = {
        0x60401fcc: Boundary('diagnostic', [(0x30, 28)]),
        0x6040227a: Boundary('diagnostic-number', [(0xa0, 40)]),
        0x605c99f4: Boundary('progress-notification', [(0xf0, 72)]),
        0x605c9b0f: Boundary('error-notification', [(0xf0, 64)]),
        0x60439f38: ProgramLeaf(handle, operations, fault_target, fault_plan),
        0x604014c6: ReadLeaf(handle, operations, readback_error_target),
    }
    regions = [Region(BASE, image, False, 'executing main'),
        Region(BUFFER-16, bytearray(b'\xa5'*16+package+b'\xa5'*16), True, 'guarded package'),
        Region(STACK, bytearray(0x10000), True, 'caller stack'),
        Region(RESULT, bytearray(16), True, 'caller result'),
        Region(0x61f01098, bytearray(2), True, 'native flash-access-mode')]
    cpu = NativeInstallMachine(code, Memory(regions), dict(sp=SP, d0=len(package), d1=mode,
        a0=BUFFER, a1=RESULT), models=models, accelerate_lower=accelerate_lower)
    cpu.package_size = len(package)
    cpu.enter(0x6100440a, RETURN, 0xf0, 16)
    interrupted = False
    try:
        stop = cpu.run(0x6100440a, {RETURN}, 300000)
        if stop.get('pc') != RETURN or cpu.r['sp'] != SP:
            raise Fault('native updater did not return: '+str(stop))
    except PowerLoss as exc:
        interrupted = True
        stop = dict(status='modeled_power_loss', detail=str(exc))
    if regions[1].data[:16]+regions[1].data[-16:] != b'\xa5'*32:
        raise Fault('package guards changed')
    after = bytes(regions[1].data[16:-16])
    report = dict(schema='epl9-native-persistent-updater-v1', mode=mode,
        input_bytes=len(package), input_sha256=sha(package), output_sha256=sha(after),
        executing_main_sha256=sha(image), entry='0x6100440a',
        returned=not interrupted, return_value=None if interrupted else hex(cpu.r['d0']),
        stop=stop, instructions_executed=len(cpu.trace), operations=operations,
        native_events=cpu.events, package_guards_intact=True,
        stack_balanced=None if interrupted else True, persistent_reopens=handle.reopens,
        real_native_layers=['updater', 'write selector', 'program/readback wrapper', 'readback checksum'],
        modeled_leaves=['program 0x60439f38', 'read 0x604014c6'],
        diagnostics_and_notifications_suppressed=True, usb_sd_transport_modeled=False,
        reset_boot_proven=False, physical_writes=False, camera_accessed=False, install_ready=False)
    state = (dict(cpu.r), (cpu.n, cpu.z, cpu.c, cpu.v), cpu.loop,
             tuple(bytes(r.data) for r in regions[1:]),
             [e for e in cpu.events if e.get('op') not in ('bulk_loop', 'bulk_lower_readback_checksum')])
    return report, after, state


def snapshot(handle):
    handle.reopen()
    return {name: handle.store.read_component(name) for name in ('main', 'osd')}


def scenario(out, name, target, package_path, image, code, initial, expected, *,
             fault_target=None, fault_plan=None, readback_error_target=None, mode=0,
             input_snapshot=None, corrupted_input=None, source_snapshot=None):
    directory = out/name
    directory.mkdir()
    store = VirtualFlashStore.create(directory/'flash', initial)
    handle = StoreHandle(store)
    source_names = ('epl9_virtual_install.py', 'epl9_virtual_flash.py', 'epl9_package_native_probe.py',
        'epl9_recovery_audit.py', 'epl9_video_audit.py', 'epl9_v3_package.py',
        'mn103_calls.py', 'mn103_subset.py', 'mn103_tooling.py')
    provenance = dict(source_root=str(ROOT), reader_sha256=verify_reader(default_reader()),
        source_sha256={n: sha((ROOT/'scripts'/n).read_bytes()) for n in source_names},
        native_instruction_sha256=sha(json.dumps({hex(pc): op[0].hex() for pc, op in code.items()}, sort_keys=True).encode()))
    if source_snapshot is not None and provenance['source_sha256'] != source_snapshot:
        raise ValueError('producer source changed between suite scenarios')
    raw = package_path.read_bytes()
    if corrupted_input is not None:
        damaged = bytearray(raw)
        damaged[corrupted_input] ^= 1
        raw = bytes(damaged)
    report, _, _ = execute(image, code, raw, handle, mode=mode, fault_target=fault_target,
        fault_plan=fault_plan, readback_error_target=readback_error_target)
    if provenance['source_sha256'] != {n: sha((ROOT/'scripts'/n).read_bytes()) for n in source_names}:
        raise ValueError('producer source changed during execution')
    if provenance['reader_sha256'] != sha(default_reader().read_bytes()):
        raise ValueError('reader changed during execution')
    actual = snapshot(handle)
    matches = {n: actual[n] == expected[n] for n in expected}
    operations_good = all(op.get('return_code') == 0 and not op.get('corruption_injected') for op in report['operations'])
    program_order = [op['component'] for op in report['operations'] if op.get('native_entry') == '0x60439f38']
    verified = (mode in (0, 1) and report['returned'] and report['return_value'] == '0x0'
        and operations_good and program_order == ['osd', 'main'] and all(matches.values())
        and len([op for op in report['operations'] if op.get('native_entry') == '0x604014c6']) == 2)
    report.update(scenario=name, target=target, generation=GENERATION, execution_provenance=provenance,
        actual_components_match_target=matches, virtual_install_verified=verified,
        expected_target_payload_sha256={n: sha(data[32:-32]) for n, data in expected.items()},
        input_snapshot=input_snapshot,
        fault_target=fault_target, fault_plan=None if fault_plan is None else asdict(fault_plan),
        readback_error_target=readback_error_target,
        source_package_file_sha256=sha(package_path.read_bytes()),
        source_package_intentionally_corrupted=corrupted_input is not None)
    report_sha = write_json(directory/'native-updater.json', report)
    handle.store.close(checkpoint=False)
    manifest_path = directory/'flash/manifest.json'
    components = [dict(name=n, kind=hex(KINDS[n]), file='flash/'+n+'.flash.bin', bytes=len(data),
        payload_bytes=len(data)-64, layout='decoded-envelope-v1', logical_destination=hex(BASES[n]),
        envelope_sha256=sha(data), payload_sha256=sha(data[32:-32]),
        target_payload_sha256=sha(expected[n][32:-32]), target_matches=matches[n])
        for n, data in actual.items()]
    document = dict(schema='epl9-virtual-install-components-v1', generation=GENERATION,
        model='Olympus PEN E-PL9', model_bytes='1330', scenario=name, target=target,
        status='verified-virtual-only' if verified else ('interrupted-virtual-only' if not report['returned'] else 'unverified-virtual-only'),
        virtual_install_verified=verified, camera_accessed=False, physical_writes=False,
        reset_boot_proven=False, install_ready=False,
        native_report=dict(file='native-updater.json', sha256=report_sha),
        source_package=dict(file=str(package_path.resolve()), bytes=package_path.stat().st_size,
                            sha256=sha(package_path.read_bytes())),
        flash_manifest=dict(file='flash/manifest.json', sha256=sha(manifest_path.read_bytes())),
        components=components)
    manifest_sha = write_json(directory/'result-components.json', document)
    print(json.dumps(dict(scenario=name, returned=report['returned'], result=report['return_value'],
        persisted_target_matches=matches, virtual_install_verified=verified)), flush=True)
    return dict(scenario=name, target=target, returned=report['returned'], return_value=report['return_value'],
        virtual_install_verified=verified, actual_components_match_target=matches,
        components_manifest=str(directory/'result-components.json'), manifest_sha256=manifest_sha,
        native_report_sha256=report_sha), actual


def run(out, packages=DEFAULT_PACKAGES):
    out = out.resolve()
    if out.exists() or not out.is_relative_to((ROOT/'local').resolve()):
        raise ValueError('new ignored local output directory required')
    out.mkdir()
    stock_main = (ROOT/'local/epl9-1101-analysis/decoded'/MAIN_NAME).read_bytes()
    if sha(stock_main) != MAIN_SHA:
        raise ValueError('wrong stock main')
    cp, rp = packages/CANDIDATE_NAME, packages/RESTORE_NAME
    if sha(cp.read_bytes()) != CANDIDATE_SHA or sha(rp.read_bytes()) != RESTORE_SHA:
        raise ValueError('requires exact native-source candidate and stock return')
    candidate, stock = decode_pair(cp.read_bytes()), decode_pair(rp.read_bytes())
    candidate_main = candidate['main'][32:-32]
    if sha(candidate_main) != CANDIDATE_MAIN_SHA:
        raise ValueError('wrong decoded candidate')
    source_snapshot = {n: sha((ROOT/'scripts'/n).read_bytes()) for n in (
        'epl9_virtual_install.py', 'epl9_virtual_flash.py', 'epl9_package_native_probe.py',
        'epl9_recovery_audit.py', 'epl9_video_audit.py', 'epl9_v3_package.py',
        'mn103_calls.py', 'mn103_subset.py', 'mn103_tooling.py')}
    def run_scenario(*args, **kwargs):
        return scenario(*args, **kwargs, source_snapshot=source_snapshot)
    listing_dir = out/'native-listings'
    listing_dir.mkdir()
    code = build_code(stock_main, listing_dir)
    lower_crosschecks = crosscheck_lower_checksum(code)
    write_json(out/'lower-checksum-crosschecks.json', lower_crosschecks)
    cases = []
    item, written_candidate = run_scenario(out, 'install-candidate', 'candidate', cp, stock_main, code, stock, candidate)
    assert item['virtual_install_verified']
    cases.append(item)
    parent = dict(scenario=item['scenario'], manifest_sha256=item['manifest_sha256'])
    item, _ = run_scenario(out, 'restore-stock', 'stock', rp, candidate_main, code, written_candidate, stock, input_snapshot=parent)
    assert item['virtual_install_verified']
    cases.append(item)
    for name, target, plan, read_error in [
        ('erase-error-osd', 'osd', FaultPlan('erase_error', block_index=0), None),
        ('program-error-osd', 'osd', FaultPlan('program_error', page_index=17), None),
        ('program-error-main', 'main', FaultPlan('program_error', page_index=200), None),
        ('readback-mismatch-main', 'main', FaultPlan('readback_mismatch', page_index=200), None),
        ('readback-error-main', None, None, 'main'),
        ('power-loss-osd', 'osd', FaultPlan('power_loss', page_index=17, partial_bytes=512), None),
        ('power-loss-main', 'main', FaultPlan('power_loss', page_index=200, partial_bytes=512), None),
    ]:
        item, actual = run_scenario(out, name, 'candidate', cp, stock_main, code, stock, candidate,
            fault_target=target, fault_plan=plan, readback_error_target=read_error)
        assert not item['virtual_install_verified']
        cases.append(item)
        if name == 'power-loss-main':
            retry, _ = run_scenario(out, 'restore-after-modeled-interruption', 'stock', rp, candidate_main,
                code, actual, stock, input_snapshot=dict(scenario=name, manifest_sha256=item['manifest_sha256'],
                assumption='synthetic explicit entry with intact executing main; no reset/recovery proof'))
            assert retry['virtual_install_verified']
            cases.append(retry)
    for name, offset in [('corrupt-main-input', 48), ('corrupt-osd-input', SIZES['main']+48)]:
        item, _ = run_scenario(out, name, 'candidate', cp, stock_main, code, stock, candidate, corrupted_input=offset)
        assert not item['virtual_install_verified'] and item['return_value'] == '0x3211'
        cases.append(item)
    item, _ = run_scenario(out, 'check-only-no-write', 'stock', cp, stock_main, code, stock, stock, mode=2)
    assert not item['virtual_install_verified'] and all(item['actual_components_match_target'].values())
    cases.append(item)
    summary = dict(schema='epl9-virtual-updater-suite-v1', generation=GENERATION,
        candidate_package_sha256=CANDIDATE_SHA, stock_return_sha256=RESTORE_SHA, cases=cases,
        lower_checksum_crosschecks=lower_crosschecks,
        native_execution='Real updater, selector, program/readback wrapper and checksum; storage leaves are explicit logical models',
        physical_writes=False, camera_accessed=False, reset_boot_proven=False, install_ready=False,
        reader_sha256=verify_reader(default_reader()),
        source_sha256={n: sha((ROOT/'scripts'/n).read_bytes()) for n in ('epl9_virtual_install.py',
            'epl9_virtual_flash.py', 'epl9_package_native_probe.py', 'mn103_calls.py', 'mn103_subset.py')},
        limitations=['Logical flash geometry and failures are models, not measured physical chip behavior.',
            'No USB/SD update transport or hardware reset entry is executed.',
            'Subsequent OM-Emu UI replay is a separate harness launch, not a physical reboot.',
            'Native success may hide storage errors; independent persisted-byte comparison is required.'])
    write_json(out/'summary.json', summary)
    print(json.dumps(dict(out=str(out), scenarios=len(cases), physical_writes=False, install_ready=False)), flush=True)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--packages', type=Path, default=DEFAULT_PACKAGES)
    args = ap.parse_args()
    run(args.out, args.packages)
