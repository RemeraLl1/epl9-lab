"""Stage and rehearse two experimental SD-file bindings under ignored local/.

Uses already compiled, validated 660-byte records; no firmware, curve fitting,
physical SD preparation, shutdown implementation or native menu assignment.
"""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile

from epl9_sd_recipes import (ROOT, MODEL, BUILD, ABI, FILE_BYTES, CARD_DIRECTORY,
    Slot, load_session, pack_recipe, unpack_recipe, read_json, require)

SCHEMA = 'epl9-sd-local-bundle-v1'
QUALIFICATION = dict(native_menu_slots_assigned=False, physical_sd_tested=False,
                     full_session_shutdown_qualified=False, install_ready=False)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def record_path(index):
    return f'{CARD_DIRECTORY}/SLOT{index:02}.RCP'


def read_record(path):
    with Path(path).open('rb') as handle:
        raw = handle.read(FILE_BYTES+1)
    return raw, unpack_recipe(raw)


def metadata(index, raw, recipe):
    return dict(path=record_path(index), bytes=FILE_BYTES, sha256=sha(raw),
                recipe_id=recipe.recipe_id, name=recipe.name)


def stage(bindings, out):
    require(type(bindings) is dict and
            all(type(i) is int and i in (1, 2) for i in bindings),
            'bind only logical test slots 1/2')
    # Snapshot and validate every source before creating any output.
    records = {i: read_record(path) for i, path in sorted(bindings.items())}
    out = Path(out)
    require(not out.exists() and not out.is_symlink() and
            out.resolve().is_relative_to((ROOT/'local').resolve()),
            'use a new output directory under ignored local/; no physical card writes')
    manifest = dict(schema=SCHEMA, model=MODEL, build=BUILD, processing_abi=ABI,
        record_bytes=FILE_BYTES,
        slots={str(i): metadata(i, raw, recipe) for i, (raw, recipe) in records.items()},
        qualification=dict(QUALIFICATION))
    out.mkdir(parents=True)
    (out/CARD_DIRECTORY).mkdir()
    for i, (raw, _) in records.items():
        with (out/record_path(i)).open('xb') as handle:
            handle.write(raw)
    with (out/'manifest.json').open('x', encoding='utf-8') as handle:
        handle.write(json.dumps(manifest, indent=2)+'\n')
    return manifest


def read_bundle(bundle):
    bundle = Path(bundle)
    require(bundle.is_dir() and not bundle.is_symlink(), 'bundle must be an ordinary directory')
    entries = list(bundle.rglob('*'))
    require(not any(p.is_symlink() for p in entries), 'bundle cannot contain symlinks')
    manifest = read_json(bundle/'manifest.json')
    fields = {'schema','model','build','processing_abi','record_bytes','slots','qualification'}
    require(type(manifest) is dict and set(manifest) == fields and manifest['schema'] == SCHEMA,
            'unsupported bundle schema/fields')
    for field, expected in (('model',MODEL),('build',BUILD),('processing_abi',ABI),('record_bytes',FILE_BYTES)):
        require(type(manifest[field]) is int and manifest[field] == expected, 'incompatible bundle '+field)
    qualifications = manifest['qualification']
    require(type(qualifications) is dict and set(qualifications) == set(QUALIFICATION) and
            all(value is False for value in qualifications.values()), 'bundle must retain unqualified camera status')
    slots = manifest['slots']
    require(type(slots) is dict and set(slots) <= {'1','2'}, 'invalid logical bundle slots')
    expected_entries = {'manifest.json',CARD_DIRECTORY} | {record_path(int(i)) for i in slots}
    require({p.relative_to(bundle).as_posix() for p in entries} == expected_entries,
            'missing or unexpected bundle files')
    records = {}
    for label, info in slots.items():
        index = int(label)
        require(type(info) is dict and set(info) == {'path','bytes','sha256','recipe_id','name'},
                'unsupported slot metadata')
        require(type(info['bytes']) is int and type(info['recipe_id']) is int and
                info['path'] == record_path(index), 'invalid slot binding/metadata')
        raw, recipe = read_record(bundle/record_path(index))
        require(info == metadata(index, raw, recipe), 'slot record differs from manifest')
        records[index] = raw
    return manifest, records


def verify(bundle):
    return read_bundle(bundle)[0]


def rehearse(bundle, fallback1, fallback2):
    """Resolve an immutable private copy; never reread inputs during selection."""
    manifest, records = read_bundle(bundle)
    fallbacks = [read_record(path) for path in (fallback1, fallback2)]
    slots = (Slot('built-in-reference', fallbacks[0][1]),
             Slot('T1', fallbacks[0][1], 1), Slot('T2', fallbacks[1][1], 2))
    (ROOT/'local').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='sd-rehearsal-', dir=ROOT/'local') as directory:
        root = Path(directory)
        (root/CARD_DIRECTORY).mkdir()
        for index, raw in records.items():
            (root/record_path(index)).write_bytes(raw)
        selected = load_session(slots, root)
    rows = [dict(slot=s.slot_id, source=s.source, status=s.status,
        recipe_id=s.recipe.recipe_id, name=s.recipe.name, record_sha256=sha(pack_recipe(s.recipe)))
        for s in selected]
    require(selected[0].recipe == fallbacks[0][1] and selected[0].source == 'embedded',
            'host built-in reference changed')
    for i in (1, 2):
        expected = records.get(i, fallbacks[i-1][0])
        require(rows[i]['record_sha256'] == sha(expected), 'host slot resolution differs from snapshot')
    return dict(schema='epl9-sd-host-rehearsal-v1',
        canonical_manifest_sha256=sha(json.dumps(manifest, sort_keys=True, separators=(',',':')).encode()),
        fallback_sha256=[sha(raw) for raw, _ in fallbacks], slots=rows,
        input_snapshot_used=True, host_resolution_passed=True,
        fallback_library_selected=False, native_task_or_file_service_executed=False,
        camera_accessed=False, **QUALIFICATION)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    prepare = commands.add_parser('stage', help='stage verified precompiled records into new local files')
    prepare.add_argument('--slot1', type=Path)
    prepare.add_argument('--slot2', type=Path)
    prepare.add_argument('--defaults-only', action='store_true', help='explicitly stage no override files')
    prepare.add_argument('--out', type=Path, required=True)
    check = commands.add_parser('verify', help='check the staged names, hashes and record contents')
    check.add_argument('bundle', type=Path)
    model = commands.add_parser('rehearse', help='resolve two slots with explicitly supplied research defaults')
    model.add_argument('bundle', type=Path)
    model.add_argument('--fallback1', type=Path, required=True)
    model.add_argument('--fallback2', type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == 'stage':
            bindings = {i: p for i, p in ((1,args.slot1),(2,args.slot2)) if p is not None}
            require(bool(bindings) != args.defaults_only,
                    'choose --slot1/--slot2 or --defaults-only')
            result = stage(bindings, args.out)
        elif args.command == 'verify':
            result = verify(args.bundle)
        else:
            result = rehearse(args.bundle, args.fallback1, args.fallback2)
    except (OSError,ValueError) as error:
        parser.error(str(error))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
