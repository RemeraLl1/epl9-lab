"""Join the exact private-COLOR v3 native/load/UI evidence before packaging."""
import argparse
import json
from pathlib import Path
from epl9_workspace_bridge import ROOT, sha
from epl9_v3_package import PRIVATE_CANDIDATE_HASHES, INTEGRATION
from epl9_omemu_compare import compare

SEAL = ROOT/'local/epl9-v3-private-readback-seal-20261107/manifest.json'
SEAL_SHA = '3277f55368d804df04358163b5c4d2f56c5531e09a9abc42305a357707cf624f'


def record(path):
    raw = path.read_bytes()
    return dict(path=str(path.resolve()), bytes=len(raw), sha256=sha(raw))


def build(out):
    if out.exists() or not out.resolve().is_relative_to((ROOT/'local').resolve()):
        raise ValueError('new ignored output directory required')
    if sha(SEAL.read_bytes()) != SEAL_SHA:
        raise ValueError('private-COLOR evidence seal changed')
    seal = json.loads(SEAL.read_text())
    for row in seal['reports'] + seal['frozen_inputs'] + [seal['candidate'], seal['module']]:
        if sha((ROOT/row['path']).read_bytes()) != row['sha256']:
            raise ValueError('sealed input/report changed: '+row['path'])
    frame_dir = ROOT/'local/epl9-v3-private-color-v2-20261107'
    owner_dir = ROOT/'local/epl9-v3-private-owner-20261107'
    load_dir = ROOT/'local/epl9-v3-private-load-20261107'
    overlay_dir = ROOT/'local/epl9-v3-private-overlay-20261107'
    ui_dir = ROOT/'local/epl9-v3-private-ui-20261107'
    stock_ui = ROOT/'local/epl9-omemu-stock-final-20261107'
    icons_ui = ROOT/'local/epl9-omemu-icons-final-20261107'
    frames = json.loads((frame_dir/'private-color.json').read_text())
    load = json.loads((load_dir/'load-sequence.json').read_text())
    overlay = json.loads((overlay_dir/'manifest.json').read_text())
    main = frame_dir/'private/main-with-module-OFFLINE-ONLY.decoded.bin'
    osd = ROOT/'local/epl9-embedded-icons-rowbounded-20261107/OSD-icons-OFFLINE-ONLY.decoded.bin'
    owner_main = owner_dir/'main-with-module-OFFLINE-ONLY.decoded.bin'
    expected = PRIVATE_CANDIDATE_HASHES[0x100]
    if not (sha(main.read_bytes()) == sha(owner_main.read_bytes()) ==
            frames['candidate_main_sha256'] == load['candidate_sha256'] ==
            overlay['candidate_main_sha256'] == expected):
        raise ValueError('native, owner, load and UI main identities differ')
    if sha(osd.read_bytes()) != PRIVATE_CANDIDATE_HASHES[0x101] or overlay['candidate_osd_sha256'] != PRIVATE_CANDIDATE_HASHES[0x101]:
        raise ValueError('icon OSD changed')
    if not all(load[k] for k in ('loaded_bytes_match','module_bytes_match',
            'destination_guards_intact','known_startup_intervals_nonoverlapping')):
        raise ValueError('load validation did not pass')
    sessions = [json.loads((d/'session.json').read_text()) for d in (stock_ui,icons_ui,ui_dir)]
    for field in ('runner_sha256','upstream_commit','node'):
        if len({s[field] for s in sessions}) != 1:
            raise ValueError('UI runner/runtime identities differ: '+field)
    comparison = compare(stock_ui,icons_ui,ui_dir,main_patch_count=5)
    patch = sessions[2]['patch']
    # Pin the actual input overlay as well as the replay result.
    overlay_input = overlay_dir/'combined.json'
    if [Path(p).resolve() for p in patch['files']] != [overlay_input.resolve()]:
        raise ValueError('UI run does not identify the selected overlay file')
    ui_hashes = {b['block']:b['sha256'] for b in patch['blocks']}
    if ui_hashes != dict(main=expected,resource=overlay['candidate_prefix_sha256']):
        raise ValueError('UI executed component bytes differ from the selected candidate')
    out.mkdir()
    comparison_path = out/'ui-comparison.json'
    comparison_path.write_text(json.dumps(comparison,indent=2)+'\n')
    previous = json.loads(INTEGRATION.read_text())
    evidence = dict(frame_validation=frame_dir/'private-color.json',
        owner_binding=owner_dir/'binding.json', load_sequence=load_dir/'load-sequence.json',
        combined_overlay=overlay_dir/'manifest.json', overlay_input=overlay_input,
        ui_comparison=comparison_path, private_seal=SEAL,
        ui_session=ui_dir/'session.json')
    report = dict(schema='epl9-v3-integration-evidence-v1', generation='private-color-v3',
        model='E-PL9 / IM008 / 1330', displayed_body_version='1.1 (owner report)', downloaded_build='1101',
        candidate_components=[dict(kind=hex(k),**record(p)) for k,p in ((0x100,main),(0x101,osd))],
        restore_components=previous['restore_components'], evidence={k:record(p) for k,p in evidence.items()},
        recipe_sha256=json.loads((ROOT/'local/epl9-v3-packages-20261107/manifest.json').read_text())['recipe_sha256'],
        source_sha256=sha(Path(__file__).read_bytes()),
        same_main_across_native_owner_load_ui=True, shared_recipe_tables_unchanged=True,
        ui_frames=41, changed_frames=comparison['changed_frames'],
        camera_accessed=False, install_ready=False,
        status='Private-COLOR v3 native/load/UI checks joined; encoded package qualification remains separate')
    (out/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(main_sha256=expected,ui_frames=41,changed_frames=comparison['changed_frames'],
        gui_states_equal=comparison['gui_states_equal'],combined_matches_icons_pixels=True,install_ready=False)))


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',type=Path,required=True)
    build(ap.parse_args().out)
