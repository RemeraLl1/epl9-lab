"""Bind reopened virtual updater writes to fresh, private E133 UI replays.

This consumes decoded logical component files, not a physical NAND boot. The
unchanged upstream E133 NAND input is null; software/HLE models remain in use.
No camera, card, USB, device interface, ISP output or recovery claim is involved.
"""
from __future__ import annotations

import argparse
from array import array
import copy
import json
from pathlib import Path
import struct
import subprocess
import sys

import epl9_native_source_ui_qualification as ui
from epl9_recovery_audit import decoded_payload, inspect_package, WINDOWS, STATIC_WINDOWS
from epl9_video_audit import checked_listing
from mn103_subset import parse_listing

ROOT = ui.ROOT
ENVELOPE_BYTES, PAYLOAD_BYTES = 26214400, 26214336
COMPONENTS = ('main', 'osd')
KINDS = dict(main='0x100', osd='0x101')
DESTINATIONS = dict(main='0x406e0000', osd='0x421e0000')
PAYLOAD_HASHES = {
    'candidate': dict(main=ui.CANDIDATE_SHA, osd=ui.ICON_SHA),
    'stock': dict(main=ui.MAIN_SHA, osd=ui.OSD_SHA),
}
PACKAGE_HASHES = {
    'candidate': '10ac83e9beb9dd1bfd12aa6a021135706875d6ea245e58e20ec07fb917229421',
    'stock': '10a7b949d1509ce627cb3c098c0a01a8ae5758fb2ce84b6c887e34b46e349387',
}
SCENARIOS = {'install-candidate': 'candidate', 'restore-stock': 'stock'}
PRODUCER_SOURCES = ('epl9_virtual_install.py', 'epl9_virtual_flash.py', 'epl9_package_native_probe.py',
    'epl9_recovery_audit.py', 'epl9_video_audit.py', 'epl9_v3_package.py',
    'mn103_calls.py', 'mn103_subset.py', 'mn103_tooling.py')
READER_SHA = '013c0af69148cc34b74e2a8a46c4efba808c7575a19cd1c08b4f2ab3867712d5'
BRIDGE_HELPER_PINS = {
    'epl9_native_source_ui_qualification.py': '7edfd7b4941c8411066029a963324769b17aa2f54b7880f9ece990e1e5539d7a',
    'epl9_recovery_audit.py': '13a0da9819d00acb218077f67e6dca130c5cc513ae5da8828ac5e9a367a23a88',
    'epl9_video_audit.py': '2c326a9eec477c6b0068c86e1db62104d3f881e89c4aae0e2b75564b5ab5e15c',
    'mn103_subset.py': '478667b95d5ea7ea4a1964b769d7eb8f4ccd6ea32bf5f4fbc7ed3c335eec979f',
}
SCHEMA = 'epl9-virtual-install-components-v1'
RESULT_KEYS = {'schema', 'generation', 'model', 'model_bytes', 'scenario', 'target',
    'status', 'virtual_install_verified', 'camera_accessed', 'physical_writes',
    'reset_boot_proven', 'install_ready', 'native_report', 'source_package', 'flash_manifest', 'components'}
COMPONENT_KEYS = {'name', 'kind', 'file', 'bytes', 'payload_bytes', 'layout',
    'logical_destination', 'envelope_sha256', 'payload_sha256', 'target_payload_sha256', 'target_matches'}
LOADED_SHA = ui.sha(Path(__file__).read_bytes())


def require(condition, message):
    if not condition:
        raise ValueError(message)


def fields(value, expected, label):
    require(isinstance(value, dict) and set(value) == set(expected), 'unexpected '+label+' fields')


def direct_file(root, name):
    """Require normalized relative paths, no symlink in any path component."""
    require(isinstance(name, str), 'file path must be a string')
    relative = Path(name)
    require(not relative.is_absolute() and relative.as_posix() == name and
        name not in ('', '.') and not any(p in ('..', '.') for p in relative.parts), 'unsafe relative evidence path')
    root = root.resolve()
    path = root/relative
    current = root
    for part in relative.parts:
        current /= part
        require(not current.is_symlink(), 'symlink evidence is not allowed')
    require(path.resolve().is_relative_to(root) and path.is_file(), 'missing/out-of-bounds evidence file')
    return path


def checked_json(root, item, expected_name=None):
    fields(item, {'file', 'sha256'}, 'JSON reference')
    if expected_name is not None:
        require(item['file'] == expected_name, 'unexpected evidence filename')
    path = direct_file(root, item['file'])
    raw = path.read_bytes()
    require(ui.sha(raw) == item['sha256'], 'referenced JSON checksum mismatch')
    return path, ui.read_json_bytes(raw), raw


def validate_result_header(doc, scenario):
    fields(doc, RESULT_KEYS, 'result-components')
    require(scenario in SCENARIOS and doc['scenario'] == scenario and doc['target'] == SCENARIOS[scenario],
        'scenario/target identity mismatch')
    require(doc['schema'] == SCHEMA and doc['generation'] == 'native-source-v1' and
        doc['model'] == 'Olympus PEN E-PL9' and doc['model_bytes'] == '1330', 'wrong result generation/model/schema')
    require(doc['status'] == 'verified-virtual-only' and doc['virtual_install_verified'] is True,
        'result is not a verified virtual installation')
    require(all(doc[key] is False for key in ('camera_accessed', 'physical_writes', 'reset_boot_proven', 'install_ready')),
        'virtual-only boundaries must be explicit')
    require(isinstance(doc['components'], list) and len(doc['components']) == 2, 'requires exactly two components')
    for name, row in zip(COMPONENTS, doc['components']):
        fields(row, COMPONENT_KEYS, 'component')
        require(row['name'] == name and row['kind'] == KINDS[name] and
            row['logical_destination'] == DESTINATIONS[name] and row['file'] == f'flash/{name}.flash.bin' and
            type(row['bytes']) is int and row['bytes'] == ENVELOPE_BYTES and
            type(row['payload_bytes']) is int and row['payload_bytes'] == PAYLOAD_BYTES and
            row['layout'] == 'decoded-envelope-v1', 'wrong component inventory/layout/target')
        expected = PAYLOAD_HASHES[doc['target']][name]
        require(row['target_matches'] is True and row['target_payload_sha256'] == expected and
            row['payload_sha256'] == expected, 'mixed, missing or non-target payload')


def package_envelopes(data, target):
    require(len(data) == 2*ENVELOPE_BYTES and ui.sha(data) == PACKAGE_HASHES[target], 'wrong source package bytes')
    rows = inspect_package(data)
    require([row['kind'] for row in rows] == list(KINDS.values()) and
        [row['decoded_sha256'] for row in rows] == list(PAYLOAD_HASHES[target].values()), 'source package component identity mismatch')
    result = {}
    for index, name in enumerate(COMPONENTS):
        raw = data[index*ENVELOPE_BYTES:(index+1)*ENVELOPE_BYTES]
        result[name] = raw[:32]+decoded_payload(raw[32:-32])+raw[-32:]
    return result


def validate_envelope(raw, row, expected):
    require(len(raw) == ENVELOPE_BYTES and ui.sha(raw) == row['envelope_sha256'], 'persisted envelope size/hash mismatch')
    require(raw == expected, 'persisted bytes do not equal decoded source package envelope')
    require(raw[:4] == b'OE\x13\x30' and raw[:28] == raw[-32:-4] and raw[28:32] == bytes(4) and
        struct.unpack_from('<I', raw, 12)[0] == PAYLOAD_BYTES and
        hex(struct.unpack_from('<I', raw, 8)[0]) == row['logical_destination'] and
        hex(struct.unpack_from('<H', raw, 20)[0]) == row['kind'], 'decoded envelope metadata mismatch')
    words = array('I'); words.frombytes(raw)
    if sys.byteorder != 'little':
        words.byteswap()
    require(sum(words) & 0xffffffff == 0, 'decoded envelope checksum mismatch')
    body = raw[32:-32]
    require(len(body) == PAYLOAD_BYTES and ui.sha(body) == row['payload_sha256'], 'persisted payload checksum mismatch')
    return body


def validate_flash_manifest(flash, doc, initial):
    fields(flash, {'schema', 'layout', 'geometry', 'envelope', 'persistence',
        'hardware_qualified', 'components', 'last_result', 'manifest_sha256'}, 'flash manifest')
    core = {k: v for k, v in flash.items() if k != 'manifest_sha256'}
    canonical = json.dumps(core, sort_keys=True, separators=(',', ':')).encode()
    require(ui.sha(canonical) == flash['manifest_sha256'], 'flash manifest canonical checksum mismatch')
    require(flash['schema'] == 'epl9-logical-flash-v1' and flash['hardware_qualified'] is False and
        flash['envelope'] == dict(header_bytes=32, trailer_bytes=32), 'flash manifest scope/layout mismatch')
    require(flash['layout'] == {
        'main': dict(base=0x406e0000, aliases=[0x806e0000], size=ENVELOPE_BYTES),
        'osd': dict(base=0x421e0000, aliases=[], size=ENVELOPE_BYTES)}, 'flash logical address map changed')
    require(flash['geometry'] == dict(page_size=2048, erase_block_size=131072,
        basis='logical assumptions; not proven chip geometry'), 'unsupported virtual geometry')
    require(set(flash['components']) == set(COMPONENTS), 'flash component inventory changed')
    for row in doc['components']:
        item = flash['components'][row['name']]
        fields(item, {'size', 'sha256', 'original_sha256'}, 'flash component')
        require(item['size'] == row['bytes'] and item['sha256'] == row['envelope_sha256'] and
            item['original_sha256'] == ui.sha(initial[row['name']]), 'flash manifest differs from result or initial snapshot')
    last = flash['last_result']
    require(isinstance(last, dict) and last.get('component') == 'main' and last.get('status') == 'success' and
        last.get('fault') is None and last.get('return_code') == 0 and last.get('returned') is True and
        last.get('stage') == 'complete' and last.get('programmed_bytes') == ENVELOPE_BYTES and
        last.get('actual_sha256') == doc['components'][0]['envelope_sha256'], 'flash last write is incomplete/faulted')


def validate_native_operations(native, doc, envelopes, initial):
    """Validate the producer's executed request/readback provenance, not final 0 alone."""
    require(native.get('schema') == 'epl9-native-persistent-updater-v1' and
        native.get('generation') == 'native-source-v1' and native.get('scenario') == doc['scenario'] and
        native.get('target') == doc['target'], 'native report scenario/schema mismatch')
    require(type(native.get('mode')) is int and native['mode'] == 0 and native.get('returned') is True and native.get('return_value') == '0x0' and
        native.get('input_bytes') == 2*ENVELOPE_BYTES and native.get('input_sha256') == PACKAGE_HASHES[doc['target']] and
        native.get('output_sha256') == ui.sha(envelopes['main']+envelopes['osd']) and
        native.get('source_package_file_sha256') == PACKAGE_HASHES[doc['target']] and
        native.get('source_package_intentionally_corrupted') is False and native.get('entry') == '0x6100440a' and
        native.get('executing_main_sha256') == (ui.MAIN_SHA if doc['target'] == 'candidate' else ui.CANDIDATE_SHA),
        'native updater execution/input identity mismatch')
    require(all(native.get(key) is False for key in ('physical_writes', 'camera_accessed', 'reset_boot_proven',
        'install_ready', 'usb_sd_transport_modeled')) and native.get('virtual_install_verified') is True and
        native.get('package_guards_intact') is True and native.get('stack_balanced') is True and
        native.get('actual_components_match_target') == dict.fromkeys(COMPONENTS, True) and
        native.get('expected_target_payload_sha256') == PAYLOAD_HASHES[doc['target']],
        'native report lacks verified virtual-only provenance')
    require(all(native.get(key) is None for key in ('fault_target', 'fault_plan', 'readback_error_target')),
        'faulted native result cannot feed UI qualification')
    require(native.get('real_native_layers') == ['updater', 'write selector', 'program/readback wrapper', 'readback checksum'] and
        native.get('modeled_leaves') == ['program 0x60439f38', 'read 0x604014c6'], 'native layer/model boundary changed')
    operations = native.get('operations', [])
    require([(op.get('component'), op.get('native_entry')) for op in operations] == [
        ('osd', '0x60439f38'), ('osd', '0x604014c6'), ('main', '0x60439f38'), ('main', '0x604014c6')],
        'native program/readback operations missing, mixed or out of order')
    for op in operations:
        name = op['component']; envelope_sha = ui.sha(envelopes[name])
        require(op.get('return_code') == 0 and op.get('bytes') == ENVELOPE_BYTES and
            op.get('persistent_reopen') is True and op.get('checksum') == 0, 'native operation did not complete/checksum/reopen')
        if op['native_entry'] == '0x60439f38':
            destination = '0x806e0000' if name == 'main' else DESTINATIONS[name]
            require(op.get('status') == 'success' and op.get('returned') is True and op.get('fault') is None and
                op.get('stage') == 'complete' and op.get('offset') == ENVELOPE_BYTES and
                op.get('native_operation') == 'program' and op.get('native_destination') == destination and
                op.get('requested_envelope_sha256') == envelope_sha and op.get('expected_sha256') == envelope_sha and
                op.get('actual_sha256') == envelope_sha and op.get('before_sha256') == ui.sha(initial[name]) and
                op.get('requested_payload_sha256') == PAYLOAD_HASHES[doc['target']][name] and
                op.get('programmed_bytes') == ENVELOPE_BYTES and op.get('erased_blocks') == 200 and
                op.get('programmed_pages') == 12800 and not op.get('corruption_injected'), 'native program provenance differs from persisted target')
        else:
            require(op.get('stage') == 'readback' and op.get('copied') is True and
                op.get('envelope_sha256') == envelope_sha and op.get('payload_sha256') == PAYLOAD_HASHES[doc['target']][name],
                'native independent persisted readback differs from target')
    require(type(native.get('persistent_reopens')) is int and native['persistent_reopens'] >= 4,
        'native persistence was not independently reopened')


def validate_native_report(native, doc, envelopes, initial, root, snapshot):
    validate_native_operations(native, doc, envelopes, initial)
    if doc['scenario'] == 'install-candidate':
        require(native.get('input_snapshot') is None, 'candidate unexpectedly depends on another store')
    else:
        parent = direct_file(root.parent, 'install-candidate/result-components.json')
        parent_raw = parent.read_bytes()
        require(native.get('input_snapshot') == dict(scenario='install-candidate', manifest_sha256=ui.sha(parent_raw)),
            'restored input snapshot does not bind actual installation result')
        snapshot.update(ui.records_for_bytes({parent: parent_raw}))
    # Require execution-time receipt; a suite summary recorded after execution is
    # insufficient to bind the source actually used by these native runs.
    provenance = native.get('execution_provenance', {})
    fields(provenance, {'source_root', 'reader_sha256', 'source_sha256', 'native_instruction_sha256'}, 'execution provenance')
    source_root = Path(provenance['source_root'])
    require(source_root.is_absolute() and source_root.resolve() == source_root and
        root.is_relative_to(source_root/'local'), 'producer source root differs from local evidence root')
    require(isinstance(provenance['source_sha256'], dict) and
        set(provenance['source_sha256']) == set(PRODUCER_SOURCES), 'producer source provenance inventory changed')
    for name, expected in provenance['source_sha256'].items():
        file = direct_file(source_root/'scripts', name)
        actual = ui.record(file)
        require(actual['sha256'] == expected, 'producer source differs from execution-time receipt: '+name)
        snapshot[file.resolve()] = actual
    reader = direct_file(source_root/'local/mn103-tooling', 'mn103-reader')
    reader_record = ui.record(reader)
    require(provenance['reader_sha256'] == READER_SHA == reader_record['sha256'], 'native reader executable differs from pinned execution receipt')
    snapshot[reader.resolve()] = reader_record
    code = {}
    image = initial['main'][32:-32]
    windows = WINDOWS | {k: STATIC_WINDOWS[k] for k in ('write_selector', 'access_mode', 'program_readback_wrapper')}
    for name, (start, end) in windows.items():
        file = direct_file(root.parent/'native-listings', name+'.tsv')
        raw = file.read_bytes(); text = raw.decode('utf8')
        checked_listing(text, image, start, end)
        native_code = parse_listing(text, image, ui.BASE)
        require(all(image[pc-ui.BASE:pc-ui.BASE+len(op[0])] == op[0] for pc, op in native_code.items()),
            'listed instruction bytes differ from executing image')
        require(all(code[pc] == native_code[pc] for pc in code.keys() & native_code.keys()), 'conflicting native instruction listings')
        code.update(native_code)
        snapshot.update(ui.records_for_bytes({file: raw}))
    instruction_hash = ui.sha(json.dumps({hex(pc): op[0].hex() for pc, op in code.items()}, sort_keys=True).encode())
    require(instruction_hash == provenance['native_instruction_sha256'], 'executed native instruction inventory hash mismatch')


def consume_result(path, scenario):
    path = Path(path).absolute()
    require(path.name == 'result-components.json' and not path.is_symlink() and path.resolve() == path,
        'expected a direct result-components.json path')
    root = path.parent
    raw = path.read_bytes(); doc = ui.read_json_bytes(raw)
    validate_result_header(doc, scenario)
    snapshot = ui.records_for_bytes({path: raw})
    native_path, native, native_raw = checked_json(root, doc['native_report'], 'native-updater.json')
    flash_path, flash, flash_raw = checked_json(root, doc['flash_manifest'], 'flash/manifest.json')
    snapshot.update(ui.records_for_bytes({native_path: native_raw, flash_path: flash_raw}))
    source = doc['source_package']
    fields(source, {'file', 'bytes', 'sha256'}, 'source package')
    source_path = Path(source['file'])
    require(source_path.is_absolute() and source_path.resolve() == source_path and not source_path.is_symlink() and
        source['bytes'] == 2*ENVELOPE_BYTES and source['sha256'] == PACKAGE_HASHES[doc['target']], 'source package identity/path mismatch')
    source_raw = source_path.read_bytes()
    envelopes = package_envelopes(source_raw, doc['target'])
    snapshot.update(ui.records_for_bytes({source_path: source_raw}))
    other_target = 'stock' if doc['target'] == 'candidate' else 'candidate'
    other_name = 'Stock-1101-main-osd-restore.bin' if other_target == 'stock' else 'Gold-Portra-v3-native-source-candidate.bin'
    other_path = direct_file(source_path.parent, other_name)
    other_raw = other_path.read_bytes()
    initial = package_envelopes(other_raw, other_target)
    snapshot.update(ui.records_for_bytes({other_path: other_raw}))
    validate_flash_manifest(flash, doc, initial)
    payloads = {}
    for row in doc['components']:
        file = direct_file(root, row['file']); data = file.read_bytes()
        payloads[row['name']] = validate_envelope(data, row, envelopes[row['name']])
        snapshot.update(ui.records_for_bytes({file: data}))
    validate_native_report(native, doc, envelopes, initial, root, snapshot)
    ui.assert_unchanged(snapshot)
    return doc, payloads, snapshot


def bridge_data(candidate, restored):
    stock_main, stock_osd = ui.MAIN.read_bytes(), ui.OSD.read_bytes()
    require(restored == dict(main=stock_main, osd=stock_osd), 'restored full payloads differ from pinned stock loader baseline')
    require(ui.sha(stock_main) == ui.MAIN_SHA and ui.sha(stock_osd) == ui.OSD_SHA, 'stock source identity changed')
    at = ui.MODULE_BASE-ui.BASE
    module = candidate['main'][at:at+ui.MODULE_BYTES]
    require(ui.sha(module) == ui.MODULE_SHA, 'virtual-written native-source module differs')
    return [stock_main, stock_osd, candidate['main'], module, candidate['osd']]


def overlay_contents(candidate, restored):
    data = bridge_data(candidate, restored)
    rows = ui.exact_overlay_rows(data)
    stock_main, stock_osd = data[:2]
    restore_rows = ui.exact_overlay_rows([stock_main, stock_osd, restored['main'], b'', restored['osd']])['combined']
    contents = {name+'.json': dict(patches=value) for name, value in rows.items()}
    contents['manifest.json'] = ui.overlay_manifest(data)
    contents['restore.json'] = dict(patches=restore_rows)
    return data, contents


def prepare(out, candidate_result, restore_result):
    out = ui.new_local(out)
    helper_snapshot()
    candidate_doc, candidate, candidate_snapshot = consume_result(candidate_result, 'install-candidate')
    restore_doc, restored, restore_snapshot = consume_result(restore_result, 'restore-stock')
    data, contents = overlay_contents(candidate, restored)
    out.mkdir(parents=True)
    for name, value in contents.items():
        (out/name).write_text(json.dumps(value, indent=2)+'\n')
    ui.validate_overlays(out, data)
    ui.replay_overlay((out/'restore.json').read_bytes(), contents['restore.json']['patches'],
        dict(main=data[0], resource=data[1]), dict(main=ui.MAIN_SHA, resource=ui.STOCK_PREFIX_SHA))
    snapshot = candidate_snapshot | restore_snapshot
    ui.assert_unchanged(snapshot)
    report = dict(schema='epl9-virtual-flash-ui-overlays-v1', source=ui.record(Path(__file__)),
        candidate_result=ui.record(candidate_result), restore_result=ui.record(restore_result),
        source_files=list(snapshot.values()), overlays=[ui.record(out/name) for name in contents],
        overlay_source='reopened persisted decoded envelopes; payload = file bytes[32:-32]',
        restored_stock_overlay_noop_spans=15, reconstructed_full_payloads_match_persisted=True,
        camera_accessed=False, physical_writes=False, hardware_pixel_execution=False, install_ready=False)
    (out/'bridge-manifest.json').write_text(json.dumps(report, indent=2)+'\n')
    return report


def helper_snapshot():
    records = {}
    for name, expected in BRIDGE_HELPER_PINS.items():
        file = ROOT/'scripts'/name
        actual = ui.record(file)
        require(actual['sha256'] == expected, 'bridge helper source changed: '+name)
        records[file.resolve()] = actual
    return records


def validate_restored_session(restored, baseline, overlay, node):
    require(restored['model'] == 'E133' and restored['error'] is None and not restored.get('close_error'), 'restored replay did not complete')
    patch = restored.get('patch')
    require(isinstance(patch, dict) and patch.get('files') == [str(overlay.resolve())] and
        patch.get('applied') == 15 and patch.get('bytes') == 0, 'wrong restored-stock overlay binding/count')
    expected = {
        'main': (ui.MAIN_SHA, 'blk00000000.OE.0100.bin', 5),
        'resource': (ui.STOCK_PREFIX_SHA, 'blk01900000.OE.0101.bin', 10)}
    blocks = patch.get('blocks', [])
    require(len(blocks) == 2 and {row['block'] for row in blocks} == set(expected), 'restored component inventory changed')
    for row in blocks:
        sha, name, count = expected[row['block']]
        require(row.get('sha256') == sha and row.get('stock_sha256') == sha and row.get('name') == name and
            row.get('patches') == count, 'restored component hash/source/count mismatch')
    binding = restored.get('input_binding', {})
    require(binding.get('patch_files') == [ui.record(overlay)] and binding.get('node_executable') == ui.record(node),
        'restored session-time overlay/executable bytes changed')
    normalized = copy.deepcopy(restored)
    normalized['patch'] = None
    normalized['input_binding']['patch_files'] = []
    require(len(restored['frames']) == len(baseline['frames']) == 41, 'restored frame inventory mismatch')
    keys = ['action', 'gui', 'state', 'sha256', 'png_rgb_sha256', 'engine_errors', 'engine_errors_total',
        'unexpected_engine_errors', 'film_site_hits', 'labels', 'inline_targets', 'target_draws', 'palette']
    for index, (a, b) in enumerate(zip(baseline['frames'], restored['frames'])):
        require(all(a.get(key) == b.get(key) for key in keys), f'restored stock differs from baseline at frame {index}')
    return normalized


def qualify(out, overlays, stock, icons, candidate, restored, node, candidate_result, restore_result):
    out = ui.new_local(out)
    source_path = Path(__file__).resolve()
    source_raw = source_path.read_bytes()
    source_record = ui.records_for_bytes({source_path: source_raw})[source_path]
    require(source_record['sha256'] == LOADED_SHA, 'bridge source changed after import')
    _, written, c_snapshot = consume_result(candidate_result, 'install-candidate')
    _, returned, r_snapshot = consume_result(restore_result, 'restore-stock')
    data, contents = overlay_contents(written, returned)
    snapshot = c_snapshot | r_snapshot | helper_snapshot() | {source_path: source_record}
    for name, expected in contents.items():
        file = direct_file(overlays, name)
        raw = file.read_bytes()
        require(ui.read_json_bytes(raw) == expected, 'overlay is not derived from current persisted flash bytes')
        snapshot.update(ui.records_for_bytes({file: raw}))
    for file in (ui.MAIN, ui.OSD):
        snapshot[file.resolve()] = ui.record(file)
    bridge_path = overlays/'bridge-manifest.json'
    bridge_raw = bridge_path.read_bytes()
    bridge = ui.read_json_bytes(bridge_raw)
    require(bridge.get('candidate_result') == ui.record(candidate_result) and bridge.get('restore_result') == ui.record(restore_result) and
        bridge.get('source_files') == list((c_snapshot | r_snapshot).values()), 'prepared bridge provenance differs from current producer files')
    snapshot.update(ui.records_for_bytes({bridge_path: bridge_raw}))
    dirs = [stock, icons, candidate, restored]
    session_raw = {(d/'session.json').resolve(): (d/'session.json').read_bytes() for d in dirs}
    snapshot.update(ui.records_for_bytes(session_raw))
    docs = [ui.read_json_bytes(session_raw[(d/'session.json').resolve()]) for d in dirs]
    normalized_restore = validate_restored_session(docs[3], docs[0], overlays/'restore.json', node)
    _, overlay_raw, manifest, _ = ui.validate_overlays(overlays, data)
    ui.verify_sessions([normalized_restore, docs[1], docs[2]], overlays, manifest,
        ui.sha(ui.ADAPTER.read_bytes()), ui.records_for_bytes(overlay_raw), ui.record(node))
    upstream = (ROOT/'references/om-emu').resolve()
    runtime = ui.verify_runtime_dependencies(docs, upstream)
    frames_before = [ui.verify_frame_files(d, doc) for d, doc in zip(dirs, docs)]
    require(len(runtime) == 120, 'expected exact 120 loaded pinned upstream modules')
    for row in runtime:
        snapshot[Path(row['path'])] = {key: row[key] for key in ('path', 'bytes', 'sha256')}
    for file in (node, ui.ADAPTER):
        snapshot[file.resolve()] = ui.record(file)
    # The original, unchanged qualifier independently checks all first-three-run
    # stock guards, exact generation, 123 PNG/RGBs, dependencies and icon regions.
    old = ui.qualify(out/'candidate-qualification', overlays, stock, icons, candidate, node)
    frames_after = [ui.verify_frame_files(d, doc) for d, doc in zip(dirs, docs)]
    require(frames_before == frames_after, 'frames changed during bridge qualification')
    ui.assert_unchanged(snapshot)
    consume_result(candidate_result, 'install-candidate')
    consume_result(restore_result, 'restore-stock')
    report = dict(schema='epl9-virtual-flash-ui-qualification-v1', generation='native-source-v1',
        model='Olympus PEN E-PL9', model_bytes='1330', source=source_record,
        candidate_result=ui.record(candidate_result), restore_result=ui.record(restore_result),
        source_files=list(snapshot.values()), existing_qualification=ui.record(out/'candidate-qualification/manifest.json'),
        sessions=[snapshot[(d/'session.json').resolve()] for d in dirs], frames_per_run=41, png_files_bound=164,
        loaded_pinned_modules_per_run=len(runtime), restored_matches_stock_frames=41,
        candidate_ui_qualified=old['ui_qualified'], stock_return_ui_qualified=True,
        persisted_inputs_bound_before_and_after=True, restored_overlay_noop_spans=15,
        overlay_source='actual persisted flash component bytes[32:-32], with complete source-envelope equivalence',
        camera_accessed=False, physical_writes=False, hardware_pixel_execution=False, reset_boot_proven=False,
        recovery_proven=False, install_ready=False,
        limitations=old['limitations']+[
            'Fresh UI sessions are normal loader sessions, not a full reset/boot-chain execution.',
            'Patched main/resource arrays derive from logical component files; unchanged upstream E133 loadNand() returns null, not a full NAND image.',
            'The persistent logical store is not a full NAND/OOB/controller, bad-block, cache/DMA, ISP or power-loss model.',
            'Zero post-bring-up processing counters establish UI-only coverage, never rendering or recipe execution.',
            'Stock-looking restored frames do not prove physical restoration or recovery after a failed boot.'])
    (out/'frame-bindings.json').write_text(json.dumps(frames_after, indent=2)+'\n')
    report['frame_bindings'] = ui.record(out/'frame-bindings.json')
    ui.assert_unchanged(snapshot)
    (out/'manifest.json').write_text(json.dumps(report, indent=2)+'\n')
    return report


def run(out, candidate_result, restore_result, node):
    out = ui.new_local(out)
    require(ui.record(node)['sha256'] == ui.NODE_SHA, 'wrong official pinned Node executable')
    # Preparing consumes real completed result manifests. Specimens/faulted writes
    # are rejected before any session or screenshot is created.
    prepare(out/'overlays', candidate_result, restore_result)
    snapshot = helper_snapshot()
    for result, scenario in [(candidate_result, 'install-candidate'), (restore_result, 'restore-stock')]:
        _, _, records = consume_result(result, scenario); snapshot.update(records)
    for name, patch in [('stock', '-'), ('icons', str(out/'overlays/icons.json')),
            ('candidate', str(out/'overlays/combined.json')), ('restored', str(out/'overlays/restore.json'))]:
        ui.assert_unchanged(snapshot)
        command = [str(node), '--max-old-space-size=6144', '--import', str(ui.ADAPTER),
            str(ROOT/'scripts/epl9_omemu_ui.mjs'), str(out/name), patch, *ui.ACTIONS]
        with (out/(name+'-replay.log')).open('x') as log:
            subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
    return qualify(out/'qualification', out/'overlays', *(out/name for name in ('stock', 'icons', 'candidate', 'restored')),
        node, candidate_result, restore_result)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for command in ('prepare', 'run', 'qualify'):
        p = sub.add_parser(command)
        for key in ('out', 'candidate-result', 'restore-result'):
            p.add_argument('--'+key, type=Path, required=True)
        if command in ('run', 'qualify'):
            p.add_argument('--node', type=Path, required=True)
        if command == 'qualify':
            for key in ('overlays', 'stock', 'icons', 'candidate', 'restored'):
                p.add_argument('--'+key, type=Path, required=True)
    args = vars(parser.parse_args()); command = args.pop('command')
    print(json.dumps(globals()[command](**args), indent=2))
