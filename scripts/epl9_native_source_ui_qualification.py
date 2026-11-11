"""Prepare and qualify only the native-source-v1 E133 offline UI replay.

Generated firmware overlays and frames must stay in ignored local directories.
This does not exercise TruePic or establish installation readiness.
"""
import argparse
import base64
import io
import json
import re
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image

from epl9_omemu_compare import compare
from epl9_omemu_overlay import overlay, OSD, OSD_SHA, ICON_SHA, RESOURCE_PREFIX, UPSTREAM
from epl9_workspace_bridge import ROOT, MAIN, MAIN_SHA, BASE, sha

CANDIDATE_SHA = '2d003930675b47774e9ed3535ee49c64f56ff519bd6f1a33ddafd1a8c688b9b7'
MODULE_SHA = '89803a465ae76a81ae6b10055f0b8ff67dc30a1f162785bd8ee4f97e1c70d6e3'
RUNNER_SHA = 'e58bd4039fb55ca1388dd287bc2139d0fa67d7015d369c8393429a7004a0a047'
NODE_SHA = '0adde40d1b7dfa57c8bc83cbc319758c3ec6ebba21363bb2fa752ea6b267ad1b'
STOCK_PREFIX_SHA = 'd777456e3c2e41db6a55458cb8ec37d1a6589391f8103b3ec38be7cae59aaa43'
ICON_PREFIX_SHA = 'e492fa2ca4aa5143f7c207db22f1e417d4d2838f53daee5353b5a2a28ed144bc'
MODULE_BASE, MODULE_BYTES = 0x604a1300, 15360
ICON_INVENTORY = [
    ('4387', 'G200', 0x158024, 1118), ('4388', 'P400', 0x15849c, 1140),
    ('4420', 'G200', 0x105cdb8, 1742), ('4421', 'P400', 0x105d4a0, 1748),
    ('4458', 'G200', 0x15eb24, 1118), ('4459', 'P400', 0x15ef9c, 1140),
    ('4556', 'G200', 0x106d508, 548), ('4557', 'P400', 0x106d744, 570),
    ('A076', 'G200', 0x48284c, 268), ('A077', 'P400', 0x482964, 272),
]
HOOK_INVENTORY = [(0x60752202, 5), (0x6079d7f4, 8), (0x6079fb88, 5), (0x60761c9e, 6)]
FILMS = ROOT/'local/cloud-reentry-native-source-20261111/run-v5/module'
ICONS = ROOT/'local/cloud-private-reconstructed-osd-20261110'
ADAPTER = ROOT/'scripts/epl9_native_source_ui_observer.mjs'
SITES = {'0x60752202', '0x6079d7f4', '0x6079fb88', '0x6074f352', '0x6079c017', '0x60761c9e'}
ACTIONS = ['s1', 'menu', 'right', 'down', 'ok'] + ['down']*27 + ['ok', 'menu', 'menu', 'ok', 'down', 'ok', 'menu', 'menu']
QUALIFIER_LOADED_SHA = sha(Path(__file__).read_bytes())


def record(path):
    path = Path(path)
    data = path.read_bytes()
    return dict(path=str(path.resolve()), bytes=len(data), sha256=sha(data))


def new_local(path):
    path = Path(path).resolve()
    if path.exists() or not path.is_relative_to((ROOT/'local').resolve()):
        raise ValueError('new ignored local output directory required')
    return path


def read_json_bytes(data):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('duplicate JSON key: '+key)
            result[key] = value
        return result
    return json.loads(data.decode('utf8'), object_pairs_hook=unique)


def component_inputs():
    paths = [MAIN, OSD, FILMS/'main-with-module-OFFLINE-ONLY.decoded.bin',
        FILMS/'epl9-films-native.bin', ICONS/'OSD-icons-OFFLINE-ONLY.decoded.bin']
    data = [p.read_bytes() for p in paths]
    if [sha(b) for b in data] != [MAIN_SHA, OSD_SHA, CANDIDATE_SHA, MODULE_SHA, ICON_SHA]:
        raise ValueError('wrong exact native-source-v1 component identity')
    main, stock_osd, candidate, module, icon_osd = data
    at = MODULE_BASE-BASE
    if (len(module) != MODULE_BYTES or candidate[at:at+MODULE_BYTES] != module or
            sha(stock_osd[:RESOURCE_PREFIX]) != STOCK_PREFIX_SHA or sha(icon_osd[:RESOURCE_PREFIX]) != ICON_PREFIX_SHA):
        raise ValueError('module placement or OSD prefix mismatch')
    return paths, data


def exact_overlay_rows(data):
    main, stock_osd, candidate, module, icon_osd = data
    icons = overlay(stock_osd, icon_osd,
        [(at, n, recipe+' icon '+id_) for id_, recipe, at, n in ICON_INVENTORY], 'resource')
    spans = [(MODULE_BASE-BASE, MODULE_BYTES, 'native-source-v1 film module')]
    spans += [(at-BASE, n, 'native-source-v1 hook '+hex(at)) for at, n in HOOK_INVENTORY]
    films = overlay(main, candidate, spans, 'main')
    return dict(icons=icons, main=films, combined=icons+films)


def overlay_manifest(data):
    main, stock_osd, candidate, module, icon_osd = data
    return dict(schema='epl9-native-source-v1-ui-overlays-v2', generation='native-source-v1',
        model='Olympus E-PL9', displayed_version='1.1 (owner report)', internal_build='1101',
        upstream_commit=UPSTREAM, main_bytes=len(main), stock_main_sha256=MAIN_SHA,
        candidate_main_sha256=CANDIDATE_SHA, module_sha256=MODULE_SHA,
        osd_bytes=len(stock_osd), stock_osd_sha256=OSD_SHA, candidate_osd_sha256=ICON_SHA,
        omemu_resource_prefix=RESOURCE_PREFIX, stock_prefix_sha256=STOCK_PREFIX_SHA,
        candidate_prefix_sha256=ICON_PREFIX_SHA, icon_patches=10, main_patches=5,
        firmware_container_created=False, camera_accessed=False, hardware_pixel_execution=False)


def replay_overlay(raw, expected_rows, stocks, expected_hashes):
    """Strictly parse and replay the exact declared inventory against stock guards."""
    doc = read_json_bytes(raw)
    if not isinstance(doc, dict) or set(doc) != {'patches'} or not isinstance(doc['patches'], list):
        raise ValueError('overlay must contain exactly the patches list')
    rows = doc['patches']
    rebuilt = {key: bytearray(value) for key, value in stocks.items()}
    ends = dict.fromkeys(stocks, 0)
    changed_bytes = 0
    for row in rows:
        if not isinstance(row, dict) or set(row) != {'block', 'offset', 'label', 'old', 'new'}:
            raise ValueError('unexpected overlay patch fields')
        key, at = row['block'], row['offset']
        if key not in stocks or type(at) is not int or not isinstance(row['label'], str):
            raise ValueError('invalid overlay block/offset/label')
        try:
            before, after = [base64.b64decode(row[k], validate=True) for k in ('old', 'new')]
        except (TypeError, ValueError) as exc:
            raise ValueError('invalid overlay base64') from exc
        if any(base64.b64encode(b).decode() != row[k] for b, k in ((before, 'old'), (after, 'new'))):
            raise ValueError('noncanonical overlay base64')
        limit = min(RESOURCE_PREFIX, len(stocks[key])) if key == 'resource' else len(stocks[key])
        if (not before or len(before) != len(after) or at < ends[key] or at+len(before) > limit):
            raise ValueError('overlay overlap/negative offset/length/bounds')
        if stocks[key][at:at+len(before)] != before:
            raise ValueError('overlay old-byte guard differs from stock')
        rebuilt[key][at:at+len(after)] = after
        ends[key] = at+len(before)
        changed_bytes += sum(a != b for a, b in zip(before, after))
    if rows != expected_rows:
        raise ValueError('overlay differs from exact native-source-v1 patch inventory')
    actual = {key: sha(bytes(value[:RESOURCE_PREFIX] if key == 'resource' else value)) for key, value in rebuilt.items()}
    if actual != expected_hashes:
        raise ValueError('replayed overlay does not reconstruct exact components')
    return dict(patches=len(rows), changed_bytes=changed_bytes,
        component_sha256=actual)


def validate_overlays(directory, data):
    expected_rows = exact_overlay_rows(data)
    expected_manifest = overlay_manifest(data)
    paths = [directory/(name+'.json') for name in ('icons', 'main', 'combined', 'manifest')]
    raw = {p.name: p.read_bytes() for p in paths}
    if read_json_bytes(raw['manifest.json']) != expected_manifest:
        raise ValueError('overlay manifest differs from exact component/inventory metadata')
    main, stock_osd, candidate, module, icon_osd = data
    results = {}
    for name in ('icons', 'main', 'combined'):
        expected = dict(main=CANDIDATE_SHA if name != 'icons' else MAIN_SHA,
            resource=ICON_PREFIX_SHA if name != 'main' else STOCK_PREFIX_SHA)
        results[name] = replay_overlay(raw[name+'.json'], expected_rows[name], dict(main=main, resource=stock_osd), expected)
    return paths, {p.resolve(): raw[p.name] for p in paths}, expected_manifest, results


def prepare(out):
    out = new_local(out)
    _, data = component_inputs()
    rows = exact_overlay_rows(data)
    result = overlay_manifest(data)
    out.mkdir(parents=True)
    for name, patches in rows.items():
        (out/(name+'.json')).write_text(json.dumps(dict(patches=patches), indent=2)+'\n')
    (out/'manifest.json').write_text(json.dumps(result, indent=2)+'\n')
    validate_overlays(out, data)
    return result


def verify_sessions(sessions, overlay_dir, overlay_manifest, adapter_sha, overlay_records, node_record):
    """Reject stale inputs, historical generations and missing runtime/frame binding."""
    if len(sessions) != 3:
        raise ValueError('expected exactly three UI sessions')
    for index, doc in enumerate(sessions):
        if (doc['upstream_commit'] != UPSTREAM or doc['runner_sha256'] != RUNNER_SHA or
                doc['node'] != 'v26.13.0' or doc['actions'] != ACTIONS or
                doc['stock_main_sha256'] != MAIN_SHA or
                doc['stock_resource_prefix_sha256'] != overlay_manifest['stock_prefix_sha256']):
            raise ValueError('UI runner/runtime/baseline/action identity mismatch')
        if doc.get('camera_accessed') is not False or doc.get('hardware_pixel_execution') is not False:
            raise ValueError('expected explicitly offline UI-only sessions')
        adapter = doc.get('runner_adapter', {})
        if (adapter.get('source_sha256') != adapter_sha or adapter.get('base_runner_sha256') != RUNNER_SHA or
                adapter.get('extra_observed_sites') != ['0x60761c9e'] or
                adapter.get('input_and_frame_binding_schema') != 'epl9-ui-input-frame-binding-v2' or
                adapter.get('cpu_or_firmware_modified') is not False):
            raise ValueError('missing or changed native-source-v1 passive observer')
        binding = doc.get('input_binding', {})
        name = None if index == 0 else ('icons' if index == 1 else 'combined')
        expected_files = [] if name is None else [overlay_records[(Path(overlay_dir)/(name+'.json')).resolve()]]
        if (binding.get('schema') != 'epl9-ui-input-frame-binding-v2' or
                binding.get('patch_files') != expected_files or binding.get('node_executable') != node_record):
            raise ValueError('session-time patch bytes or executable differ from current verified inputs')
        for frame in doc['frames']:
            hits = frame['film_site_hits']
            if set(hits) != SITES or any(v != 0 for v in hits.values()):
                raise ValueError('UI processing-site coverage differs or a processing site executed')
    if sessions[0]['patch'] is not None:
        raise ValueError('baseline is patched')
    for doc, name, count in [(sessions[1], 'icons', 10), (sessions[2], 'combined', 15)]:
        patch = doc['patch']
        if patch['applied'] != count or [Path(p).resolve() for p in patch['files']] != [(Path(overlay_dir)/(name+'.json')).resolve()]:
            raise ValueError('wrong overlay file/count')
        blocks = patch['blocks']
        if len({b['block'] for b in blocks}) != len(blocks):
            raise ValueError('duplicate actual component summary')
        hashes = {b['block']: b['sha256'] for b in blocks}
        expected = dict(resource=ICON_PREFIX_SHA)
        if name == 'combined':
            expected['main'] = CANDIDATE_SHA
        if hashes != expected:
            raise ValueError('actual emulated component bytes differ from native-source-v1 pins')
        expected_changed = 8002 if name == 'icons' else 23298
        if patch.get('bytes') != expected_changed:
            raise ValueError('actual overlay changed-byte count mismatch')
        for block in blocks:
            stock_sha = MAIN_SHA if block['block'] == 'main' else STOCK_PREFIX_SHA
            expected_name = 'blk00000000.OE.0100.bin' if block['block'] == 'main' else 'blk01900000.OE.0101.bin'
            expected_count = 5 if block['block'] == 'main' else 10
            if (block.get('stock_sha256') != stock_sha or block.get('name') != expected_name or
                    block.get('patches') != expected_count):
                raise ValueError('actual component stock guard hash mismatch')


def verify_png(path, frame):
    raw = path.read_bytes()
    if len(raw) != frame.get('png_bytes') or sha(raw) != frame.get('png_sha256'):
        raise ValueError('PNG bytes differ from replay-time frame binding: '+str(path))
    with Image.open(io.BytesIO(raw)) as image:
        if image.format != 'PNG' or image.size != (720, 480):
            raise ValueError('unexpected native UI PNG format/dimensions')
        rgb = np.asarray(image.convert('RGB'), dtype=np.uint8).tobytes()
    if sha(rgb) != frame.get('png_rgb_sha256'):
        raise ValueError('PNG pixels differ from replay-time native RGB bytes: '+str(path))
    return dict(path=str(path.resolve()), bytes=len(raw), sha256=sha(raw), native_rgb_sha256=sha(rgb))


def verify_frame_files(directory, doc):
    if len(doc['frames']) != 41:
        raise ValueError('expected exactly 41 bound frames')
    rows = []
    expected_names = []
    for index, (action, frame) in enumerate(zip(['start']+ACTIONS, doc['frames'])):
        name = f'{index:03d}-'+re.sub(r'[^a-zA-Z0-9_-]', '_', action)+'.png'
        if frame['action'] != action or frame['png'] != name or (frame['width'], frame['height']) != (720, 480):
            raise ValueError('bound frame action/name/dimension mismatch')
        path = directory/name
        if path.resolve().parent != directory.resolve() or path.is_symlink():
            raise ValueError('frame path is not a direct local PNG')
        rows.append(verify_png(path, frame))
        expected_names.append(name)
    if sorted(p.name for p in directory.glob('*.png')) != sorted(expected_names):
        raise ValueError('missing/extra PNG frame inventory')
    return rows


def verify_runtime_dependencies(sessions, upstream):
    """Bind every observed loaded upstream module to its pinned tracked Git blob."""
    import hashlib
    inventory = {}
    tree = subprocess.check_output(['git', 'ls-tree', '-rz', 'HEAD'], cwd=upstream)
    for item in tree.split(b'\0'):
        if not item:
            continue
        head, name = item.split(b'\t', 1)
        mode, kind, blob = head.decode().split()
        if kind == 'blob' and mode in ('100644', '100755'):
            inventory[name.decode()] = blob
    identities = []
    for doc in sessions:
        rows = doc.get('runtime_dependencies', [])
        if not rows:
            raise ValueError('missing replay-time runtime dependencies')
        by = {}
        for row in rows:
            if not isinstance(row, dict) or set(row) != {'path', 'bytes', 'sha256'}:
                raise ValueError('invalid runtime dependency record')
            path = Path(row['path'])
            if path in by or not path.is_absolute() or path.resolve() != path or not path.is_relative_to(upstream.resolve()):
                raise ValueError('duplicate or nonlocal runtime dependency')
            relative = path.relative_to(upstream.resolve()).as_posix()
            raw = path.read_bytes()
            blob = hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
            actual = dict(path=str(path), bytes=len(raw), sha256=sha(raw))
            if (relative not in inventory or blob != inventory[relative] or actual != row):
                raise ValueError('loaded runtime dependency differs from pinned tracked source: '+relative)
            by[path] = dict(**row, git_blob_sha1=blob)
        identities.append(by)
    if any(identity != identities[0] for identity in identities[1:]):
        raise ValueError('UI replays loaded different runtime dependencies')
    return [identities[0][p] for p in sorted(identities[0])]


def records_for_bytes(raw_by_path):
    return {p.resolve(): dict(path=str(p.resolve()), bytes=len(raw), sha256=sha(raw)) for p, raw in raw_by_path.items()}


def assert_unchanged(records):
    for path, expected in records.items():
        if record(path) != expected:
            raise ValueError('evidence input changed during qualification: '+str(path))


def qualify(out, overlays, stock, icons, candidate, node):
    out = new_local(out)
    if sha(Path(__file__).read_bytes()) != QUALIFIER_LOADED_SHA:
        raise ValueError('qualifier source differs from the loaded source')
    components, data = component_inputs()
    overlay_paths, overlay_raw, manifest, replay = validate_overlays(overlays, data)
    runner = ROOT/'scripts/epl9_omemu_ui.mjs'
    helper_pins = {
        runner: RUNNER_SHA,
        ROOT/'scripts/epl9_omemu_compare.py': '93994e765c5e575e33501c271033bfb781630024863145f7240eb721a51d6568',
        ROOT/'scripts/epl9_omemu_overlay.py': 'e47bdfdb69a4bc1e5bb2ad43344fe52f068111644774e10c18ed9f00f43644fb',
        ROOT/'scripts/epl9_workspace_bridge.py': '1034449d83ffb555eb0ab47da570d7e44b7f7ac46062c4abf136fc3506141825',
    }
    for path, expected in helper_pins.items():
        if sha(path.read_bytes()) != expected:
            raise ValueError('current pinned runner/helper source changed: '+str(path))
    node_record = record(node)
    if node_record['sha256'] != NODE_SHA:
        raise ValueError('expected official Linux x64 Node v26.13.0 executable')
    upstream = ROOT/'references/om-emu'
    if subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=upstream, text=True).strip() != UPSTREAM:
        raise ValueError('wrong upstream checkout')
    subprocess.run(['git', 'diff', '--exit-code', 'HEAD', '--'], cwd=upstream, check=True)
    dirs = [stock, icons, candidate]
    session_raw = {(d/'session.json').resolve(): (d/'session.json').read_bytes() for d in dirs}
    sessions = [read_json_bytes(session_raw[(d/'session.json').resolve()]) for d in dirs]
    overlay_records = records_for_bytes(overlay_raw)
    verify_sessions(sessions, overlays, manifest, sha(ADAPTER.read_bytes()), overlay_records, node_record)
    runtime = verify_runtime_dependencies(sessions, upstream)
    frames_before = [verify_frame_files(d, doc) for d, doc in zip(dirs, sessions)]
    snapshot = records_for_bytes(dict(zip(components, data)))
    snapshot.update(overlay_records)
    snapshot.update(records_for_bytes(session_raw))
    for path in [node, ADAPTER, Path(__file__), *helper_pins]:
        snapshot[path.resolve()] = record(path)
    for row in runtime:
        snapshot[Path(row['path'])] = {key: row[key] for key in ('path', 'bytes', 'sha256')}
    comparison = compare(*dirs, main_patch_count=5)
    frames_after = [verify_frame_files(d, doc) for d, doc in zip(dirs, sessions)]
    if frames_before != frames_after:
        raise ValueError('frame inputs changed during pixel comparison')
    assert_unchanged(snapshot)
    # Repeat independent parsing, stock guards and exact reconstruction after comparison.
    validate_overlays(overlays, data)
    subprocess.run(['git', 'diff', '--exit-code', 'HEAD', '--'], cwd=upstream, check=True)
    out.mkdir(parents=True)
    (out/'ui-comparison.json').write_text(json.dumps(comparison, indent=2)+'\n')
    (out/'frame-bindings.json').write_text(json.dumps(frames_before, indent=2)+'\n')
    result = dict(schema='epl9-native-source-v1-ui-qualification-v2', generation='native-source-v1',
        candidate_main_sha256=CANDIDATE_SHA, module_sha256=MODULE_SHA, candidate_osd_sha256=ICON_SHA,
        candidate_resource_prefix_sha256=ICON_PREFIX_SHA,
        upstream_commit=UPSTREAM, upstream_tracked_files_unchanged=True, runtime_dependencies=runtime,
        node=snapshot[node.resolve()], runner=snapshot[runner.resolve()], passive_observer=snapshot[ADAPTER.resolve()],
        source=snapshot[Path(__file__).resolve()], source_dependencies=[snapshot[p.resolve()] for p in helper_pins],
        comparison=record(out/'ui-comparison.json'), frame_bindings=record(out/'frame-bindings.json'),
        components=[snapshot[p.resolve()] for p in components], overlay_replay=replay,
        overlays=[snapshot[p.resolve()] for p in overlay_paths],
        sessions=[snapshot[(d/'session.json').resolve()] for d in dirs], frames_per_run=41, png_files_bound=123,
        session_time_patch_inputs_verified=True, current_overlays_replayed_before_and_after=True,
        evidence_inputs_unchanged_across_comparison=True, native_rgb_and_png_bytes_bound=True,
        gui_states_actions_and_diagnostics_equal=True, candidate_matches_icons_pixels=True,
        changes_confined_to_accepted_icon_regions=True, changed_frames=comparison['changed_frames'],
        observed_resources=comparison['observed_resources'], film_site_hits=comparison['combined_film_site_hits'],
        ui_qualified=True, hardware_pixel_execution=False, camera_accessed=False, install_ready=False,
        limitations=['Six of ten icon resources observed; four resources remain outside this route.',
            'ART-dial large-example compositor and E133 palette dump retain documented emulator gaps.',
            'Exact stock BMP_LUT diagnostic history is preserved, not claimed absent.',
            'Passive hook counters begin after Player.open_session; this route does not execute processing.',
            'No TruePic pixels, physical boot, installation, readback acquisition or restore was tested.'])
    assert_unchanged(snapshot)
    (out/'manifest.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('prepare'); p.add_argument('--out', type=Path, required=True)
    q = sub.add_parser('qualify')
    for key in ('out', 'overlays', 'stock', 'icons', 'candidate', 'node'):
        q.add_argument('--'+key, type=Path, required=True)
    args = vars(parser.parse_args()); command = args.pop('command')
    print(json.dumps((prepare if command == 'prepare' else qualify)(**args), indent=2))
