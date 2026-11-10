"""Frozen v3 configuration interleaving with shared module and distinct RAM.

No scheduler, IRQ or ISP emulation. Same-context overlap is a negative control,
not a claim that the camera actually schedules such an overlap.
"""
import argparse
import json
import struct
from pathlib import Path

from epl9_workspace_bridge import ROOT, BASE, sha
from epl9_film_late_probe import prepare_probe, frame_inputs, AUX
from epl9_integrated_probe import native, RETURN
from epl9_film_module_probe import USER_CONTROLS
from epl9_offline_prototype import REQUEST, CONTEXT, OUTPUT, OBJECT, SP
from epl9_deployment_probe import Registers
from epl9_v3_package import CANDIDATE_HASHES
from mn103_subset import Memory, Region
from mn103_calls import CallMachine


def build_frame(original, original_code, patched, code, shared, key, fmt, offset):
    request, obj = frame_inputs(original, original_code, key, fmt, 0, (0,)*5, True)
    for at in (1484, 1512, 1524):
        value = struct.unpack_from('<I', request, at)[0]
        if value:
            struct.pack_into('<I', request, at, value+offset)
    context = bytearray(128)
    for at, value in ((4, REQUEST+offset), (12, OUTPUT+offset), (52, key), (60, 0x10000002)):
        struct.pack_into('<I', context, at, value)
    blobs = [(REQUEST, request), (CONTEXT, context), (OUTPUT, bytearray(5200)),
             (AUX, bytearray(6000)), (OBJECT, bytearray(obj)),
             (USER_CONTROLS, bytearray(10))]
    m = native(patched, code, [], {})
    stack = next(r for r in m.memory.regions if r.name == 'stack')
    regions = [Region(BASE, shared, True, 'shared main'),
        Region(stack.address+offset, stack.data, True, 'private stack')]
    guarded = []
    for address, blob in blobs:
        data = bytearray(b'\xa5'*16)+blob+bytearray(b'\x5a'*16)
        region = Region(address+offset-16, data, True, hex(address))
        regions.append(region)
        guarded.append((address+offset, data, bytes(blob)))
    m.memory = Memory(regions)
    m.r = Registers(dict(m.r, sp=SP+offset, a0=CONTEXT+offset))
    return dict(m=m, initial_sp=SP+offset, guarded=guarded, offset=offset,
                pc=m.enter(0x6079fb88, RETURN, 0xf0, 40))


def execute(frame, stops=()):
    r = frame['m'].run(frame['pc'], [RETURN, *stops])
    if r.get('status') != 'stop':
        raise ValueError('unexpected native boundary: '+str(r))
    frame['pc'] = r['pc']


def snapshot(frame):
    m, off = frame['m'], frame['offset']
    if frame['pc'] != RETURN or m.r['sp'] != frame['initial_sp']:
        raise ValueError('configuration did not return with balanced stack')
    state = {}
    for address, data, before in frame['guarded']:
        if data[:16] != b'\xa5'*16 or data[-16:] != b'\x5a'*16:
            raise ValueError('buffer boundary overwritten')
        actual = bytes(data[16:-16])
        if address-off not in (OUTPUT, AUX) and actual != before:
            raise ValueError('private request/context/owner/control was not restored')
        state[address-off] = actual
    for at in (2596, 2600, 2604, 2608):
        pointer = struct.unpack_from('<I', state[OUTPUT], at)[0]
        stack = next(r for r in m.memory.regions if r.name == 'private stack')
        if stack.address <= pointer < stack.address+len(stack.data):
            raise ValueError('output retained a temporary stack pointer')
    return state, m.r['d0']


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    rgb = json.loads((ROOT/'local/epl9-native-film-curves-v3-20261107/native-rgb-tables.json').read_text())
    wb = json.loads((ROOT/'recipes/epl9-native-wb-trial-v1.json').read_text())
    original, patched, original_code, code, module, manifest = prepare_probe(
        args.out, base=0x604a1300, rgb_document=rgb, wb_document=wb)
    if sha(patched) != CANDIDATE_HASHES[0x100]:
        raise ValueError('rebuilt binary differs from frozen v3')
    shared = bytearray(patched)
    keys = (0x01010078, 0x01020078)
    rows, overlaps = [], []
    for fmt in (0x200, 0x100, 0x40, 0x1000):
        for first, second in ((keys[0], keys[1]), (keys[1], keys[0])):
            frames, references = [], []
            for i, key in enumerate((first, second)):
                off = i*0x04000000
                ref = build_frame(original, original_code, patched, code, shared, key, fmt, off)
                execute(ref)
                references.append(snapshot(ref))
                frames.append(build_frame(original, original_code, patched, code, shared, key, fmt, off))
            # Both native frames are paused while their own request is temporary.
            # Distinct request/output/cache/owner/stack, exactly one shared main.
            for symbol in ('color_native_call', 'color_after_native_call', 'color_restore'):
                for frame in frames:
                    execute(frame, [module['symbols'][symbol]])
                    if frame['pc'] != module['symbols'][symbol]:
                        raise ValueError('interleave checkpoint not reached')
            for frame, expected in zip(reversed(frames), reversed(references)):
                execute(frame)
                if snapshot(frame) != expected:
                    raise ValueError('interleaving changed native configuration')
            if shared != patched:
                raise ValueError('executed path wrote shared code/tables')
            rows.append(dict(first=hex(first), second=hex(second), kind=hex(fmt),
                whole_request_context_owner_restored=True, configuration_matches_isolated=True,
                shared_main_unchanged=True, buffer_guards_intact=True,
                temporary_output_pointers=False,
                peak_frame_stack=[f['initial_sp']-f['m'].r.minimum_sp for f in frames]))
    for key in keys:
        # Deliberately overlap the SAME request with another CPU context/stack.
        # This documents the required caller exclusion instead of assuming it.
        isolated = build_frame(original, original_code, patched, code, shared, key, 0x1000, 0)
        execute(isolated)
        isolated_output = snapshot(isolated)[0][OUTPUT]
        outer = build_frame(original, original_code, patched, code, shared, key, 0x1000, 0)
        execute(outer, [module['symbols']['color_native_call']])
        stack = Region(0x1f000000, bytearray(8192), True, 'negative control stack')
        child = CallMachine(code, Memory([*outer['m'].memory.regions, stack]),
                            dict(sp=0x1f001000, a0=CONTEXT))
        child.r = Registers(child.r)
        entered = child.enter(0x6079fb88, RETURN, 0xf0, 40)
        result = child.run(entered, [RETURN])
        if result.get('pc') != RETURN:
            raise ValueError('same-context negative control stopped unexpectedly')
        gated = module['symbols']['color_bias'] in child.trace
        if gated:
            raise ValueError('expected temporary identity to suppress inner recipe selection')
        output_region = next(data for address, data, _ in outer['guarded'] if address == OUTPUT)
        differing = sum(a != b for a, b in zip(output_region[16:-16], isolated_output))
        if not differing:
            raise ValueError('negative control unexpectedly matches complete isolated configuration')
        overlaps.append(dict(key=hex(key), inner_color_bias_entered=gated,
            inner_post_hsl_entered=module['symbols']['color_post_hsl'] in child.trace,
            inner_gamma_hook_entered=module['symbols']['film_gamma_hook'] in child.trace,
            configuration_bytes_differing_from_isolated=differing,
            temporary_context_key=hex(outer['m'].memory.read(CONTEXT+52, 4)),
            exclusion_required=True, camera_overlap_observed=False))
        execute(outer)
        snapshot(outer)
    if shared != patched:
        raise ValueError('shared image modified')
    report = dict(main_sha256=sha(original), candidate_main_sha256=sha(patched),
        module_sha256=manifest['module_sha256'], cases=rows, same_context_negative_controls=overlaps,
        source_sha256=sha(Path(__file__).read_bytes()),
        no_shared_mutable_recipe_state_in_tested_paths=True,
        same_job_concurrent_entry_excluded=False, irq_scheduling_verified=False,
        runtime_module_ownership_verified=False, full_pixel_cycle=False, install_ready=False)
    (args.out/'concurrency.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows), negative_controls=len(overlaps),
        candidate_main_sha256=sha(patched), same_job_exclusion_required=True), indent=2))


if __name__ == '__main__':
    main()
