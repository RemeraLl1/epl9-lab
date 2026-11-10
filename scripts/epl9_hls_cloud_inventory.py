"""Read-only stock-only HLS evidence inventory, independent of SD shutdown code.

Requires the exact downloaded E-PL9 build 1101 main. Does not require frozen
v3 packages, fallback recipe exports or the missing session-shutdown sources.
Raw CALL/root matches remain candidates. No task-stop or user-list completeness
claim is inferred from an address, a destructor or a successful decode.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from epl9_workspace_bridge import ROOT, MAIN, MAIN_SHA, BASE
from epl9_sd_state_audit import WINDOWS as STATE_WINDOWS, raw_call_candidates
from epl9_sd_load_trigger_audit import WINDOWS as TRIGGER_WINDOWS
from mn103_subset import parse_listing
from mn103_tooling import default_reader, reader_provenance


MAIN_BYTES = 26214336
ROOT_ADDRESS = 0x6239790c
TARGETS = {
    'manager_constructor': 0x60ae187f,
    'destructor_prefix': 0x60ae1910,
    'manager_getter': 0x60ae1a4d,
    'task_creation_adapter': 0x60ae1bb2,
    'task_entry': 0x60ae1c12,
    'event_get_adapter': 0x60ae2073,
}
WINDOWS = {name: STATE_WINDOWS[name] for name in
    ('manager_ctor', 'manager_getter', 'manager_vectors', 'task_create_manager', 'root_users')}
WINDOWS.update({name: TRIGGER_WINDOWS[name] for name in ('hls_init', 'hls_get', 'event_get')})


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require_exact_main(data):
    if len(data) != MAIN_BYTES or sha(data) != MAIN_SHA:
        raise ValueError('requires the byte-exact downloaded E-PL9 1101 main')


def literal_candidates(data, value):
    needle = value.to_bytes(4, 'little')
    result, at = [], data.find(needle)
    while at >= 0:
        result.append(hex(BASE+at))
        at = data.find(needle, at+1)
    return result


def save_evidence(image, out, reader, provenance):
    """Decode already-recorded windows; collect candidates without classifying users."""
    require_exact_main(image)
    if not out.is_dir():
        raise ValueError('private output directory is missing')
    windows = {}
    for name, (start, end) in WINDOWS.items():
        listing = subprocess.check_output([str(reader.resolve()), str(out/'stock-main-input.bin'),
            hex(BASE), hex(start-BASE), hex(end-BASE)], text=True)
        # The caller places a private, exact input snapshot only during decoding.
        parsed = parse_listing(listing, image, BASE)
        if start not in parsed or any(not start <= pc < end for pc in parsed):
            raise ValueError('GNU decoder escaped the recorded window: '+name)
        path = out/(name+'.tsv')
        path.write_text(listing, encoding='utf-8')
        windows[name] = dict(start=hex(start), end=hex(end), instructions=len(parsed),
            listing_sha256=sha(path.read_bytes()), whole_function_or_loop_proven=False)
    report = dict(schema='epl9-hls-stock-only-cloud-inventory-v1', model=1330,
        displayed_version='1.1 (owner report)', downloaded_build=1101,
        stock_main_bytes=len(image), stock_main_sha256=sha(image), reader=provenance,
        windows=windows, root_address=hex(ROOT_ADDRESS),
        raw_root_literal_candidates=literal_candidates(image, ROOT_ADDRESS),
        raw_call_candidates={name: dict(target=hex(target),
            sites=raw_call_candidates(image, target)) for name, target in TARGETS.items()},
        candidate_warning='byte-pattern matches can lie inside data or other instructions; '
                          'they are not independently established callers or users',
        source_sha256={name: sha((ROOT/name).read_bytes()) for name in (
            'scripts/epl9_hls_cloud_inventory.py', 'scripts/epl9_sd_state_audit.py',
            'scripts/epl9_sd_load_trigger_audit.py', 'scripts/mn103_subset.py')},
        missing_shutdown_code_used=False, frozen_v3_artifacts_required=False,
        full_hls_loop_covered=False, task_stop_acknowledgement_proven=False,
        five_vector_users_complete=False, cached_or_inflight_users_drained=False,
        local_chat_stop_confirmed=False, camera_accessed=False, install_ready=False)
    (out/'inventory.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    return report


def run(main, out, reader):
    # Fail before creating output or qualifying a decoder when input is absent/wrong.
    with main.open('rb') as handle:
        image = handle.read(MAIN_BYTES+1)
    require_exact_main(image)
    if out.exists() or not out.resolve().is_relative_to((ROOT/'local').resolve()):
        raise ValueError('use a new ignored local output directory')
    provenance = reader_provenance(reader)
    # Decode a private snapshot so a concurrently replaced source cannot produce
    # listings whose bytes differ from the verified image. Always remove it.
    out.mkdir(parents=True)
    snapshot = out/'stock-main-input.bin'
    try:
        with snapshot.open('xb') as handle:
            handle.write(image)
        report = save_evidence(image, out, reader, provenance)
    finally:
        snapshot.unlink(missing_ok=True)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--main', type=Path, default=MAIN)
    parser.add_argument('--reader', type=Path, default=default_reader())
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = run(args.main, args.out, args.reader)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(dict(windows=len(result['windows']),
        task_stop_acknowledgement_proven=False, five_vector_users_complete=False)))
