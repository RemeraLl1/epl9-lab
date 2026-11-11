"""Firmware-free file workflow rehearsal with independently decoded SD code.

All generated recipes are artificial range/format controls, not Gold/Portra
exports or stock gamma replacements. Native calls execute only the standalone
authored loader, with explicit host file/task/pool services per logical slot.
The shared HLS manager, stock wrappers, image processing and shutdown do not run.
"""
import argparse
from dataclasses import replace
import json
from pathlib import Path
import struct
import zlib

from epl9_sd_bundle import stage, verify, rehearse, read_bundle, record_path, sha
from epl9_sd_recipes import (ROOT, MAIN, Slot, load_session, pack_recipe, read_json,
                            validate_author, require, FILE_BYTES)
from epl9_sd_loader import build
from epl9_sd_loader_probe import LoaderFixture, sample_recipe, CTX
from epl9_sd_processing_probe import decode
from epl9_wifi_prototype import span
from mn103_tooling import default_reader, reader_provenance

LOADER_SHA = 'ed4d4e9055d00393ad1eea267bd265abf4261c3a12fd1980cac7ad216f15d357'


def selected_bytes(fixture):
    return bytes(span(fixture.memory, fixture.memory.read(CTX+4,4), FILE_BYTES))


def run(out, reader):
    out = Path(out).resolve()
    require(not out.exists() and out.is_relative_to((ROOT/'local').resolve()), 'new ignored output required')
    provenance = reader_provenance(reader)
    names = ('epl9_sd_recipes.py','epl9_sd_bundle.py','epl9_sd_workflow_probe.py',
             'epl9_sd_loader.py','epl9_sd_loader_probe.py','epl9_sd_processing_probe.py',
             'mn103_emit.py','mn103_subset.py','mn103_calls.py')
    paths = [ROOT/'scripts'/name for name in names] + [ROOT/'firmware_src/epl9_sd_loader.s.in']
    fingerprints = {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in paths}
    example = validate_author(read_json(ROOT/'recipes/epl9-sd-example-v0.json'))
    module = build()
    require(sha(module['data']) == LOADER_SHA, 'standalone loader bytes changed')
    module['code_bytes'] = len(module['data'])
    out.mkdir(parents=True)
    decode(module, out/'native-loader', reader)
    base = sample_recipe()
    recipes = [replace(base,recipe_id=1,name='SYNTH Fallback 1'),
               replace(base,recipe_id=2,name='SYNTH Fallback 2'),
               replace(base,recipe_id=31,name='SYNTH Override A',contrast=2,tone=(-7,0,7),
                       wb_q10=(512,2048),hsl=((-1000,240,-100),)*12),
               replace(base,recipe_id=32,name='SYNTH Override B',contrast=-2,tone=(7,1,-7),
                       wb_q10=(2048,512),gamma=tuple(n*n*4095//(255*255) for n in range(256)))]
    inputs = out/'synthetic-inputs'
    inputs.mkdir()
    record_paths = []
    for i, recipe in enumerate(recipes):
        path = inputs/f'record-{i}.RCP'
        path.write_bytes(pack_recipe(recipe))
        record_paths.append(path)
    fallback1, fallback2, first, second = record_paths
    raw1, raw2 = first.read_bytes(), second.read_bytes()
    native_runs = []

    def native(fixture, case, slot):
        result = fixture.run()
        native_runs.append(dict(case=case,slot=slot,state=result['state'],
            selected=result['selected'],record_sha256=sha(selected_bytes(fixture)),
            owned_block=result['owned_block'],open_file=result['open_file'],
            error_code=result['error_code'],instructions=result['instructions'],
            stopped_at_declared_pending_reply=result['result'].get('status') == 'fault',
            service_counts=result['counts']))
        return result

    cases = []
    plans = (('defaults',{}),('only-first',{1:first}),('only-second',{2:second}),
             ('both',{1:first,2:second}),('swapped',{1:second,2:first}),
             ('same-record-both',{1:first,2:first}))
    for label, bindings in plans:
        directory = out/label
        stage(bindings,directory)
        verify(directory)
        host = rehearse(directory,fallback1,fallback2)
        _, records = read_bundle(directory)
        for slot in (1,2):
            fixture = LoaderFixture(module,records.get(slot),fallback=recipes[slot-1],slot=slot)
            result = native(fixture,label,slot)
            require((result['state'],result['selected']) ==
                    ((3,'sd') if slot in records else (2,'embedded')), 'native slot source differs')
            require(sha(selected_bytes(fixture)) == host['slots'][slot]['record_sha256'],
                    'host/native selected bytes differ')
            snapshot = selected_bytes(fixture)
            counts = dict(fixture.counts)
            # File contents change after a completed attempt; the live record
            # and missing-file fallback must remain frozen for this fixture.
            fixture.file_data = raw2 if slot == 1 else raw1
            native(fixture,label+'/later-file-change',slot)
            require(dict(fixture.counts) == counts and selected_bytes(fixture) == snapshot,
                    'completed native attempt reopened or changed its record')
        cases.append(dict(case=label,host=host,host_native_records_match=True,
                          completed_attempts_do_not_reload=True))

    malformed = bytearray(raw1)
    malformed[64] ^= 1
    wrong_model = bytearray(raw1)
    struct.pack_into('<H',wrong_model,8,1420)
    struct.pack_into('<I',wrong_model,16,0)
    struct.pack_into('<I',wrong_model,16,zlib.crc32(wrong_model))
    rejected = []
    for label, raw in (('bad-crc',bytes(malformed)),('oversized',raw1+b'x'),
                       ('wrong-model-resealed',bytes(wrong_model))):
        directory = out/label
        stage({1:first,2:second},directory)
        (directory/record_path(1)).write_bytes(raw)
        try:
            verify(directory)
        except ValueError:
            pass
        else:
            raise ValueError('changed bundle was accepted')
        selections = load_session((Slot('T1',recipes[0],1),Slot('T2',recipes[1],2)),directory)
        for slot, data in ((1,raw),(2,raw2)):
            fixture = LoaderFixture(module,data,fallback=recipes[slot-1],slot=slot)
            result = native(fixture,label,slot)
            require((result['state'],result['selected']) == ((2,'embedded') if slot == 1 else (3,'sd')),
                    'bad-neighbor native source differs')
            require(selected_bytes(fixture) == pack_recipe(selections[slot-1].recipe),
                    'bad-neighbor host/native record differs')
        rejected.append(dict(case=label,bundle_rejected=True,host_native_fallback_agrees=True,
                             valid_neighbor_preserved=True))

    boundaries = []
    for label, options, expected in (
            ('close-uncertain',dict(close_error=True),4),
            ('read-pending',dict(stall_read=True),1),
            ('sd-not-ready',dict(sd_status=0),0),
            ('allocation-failed',dict(fail_alloc=True),2)):
        fixture = LoaderFixture(module,raw1,fallback=recipes[0],**options)
        result = native(fixture,label,1)
        require(result['state'] == expected and result['selected'] == 'embedded', 'boundary state differs')
        if label in ('close-uncertain','read-pending'):
            require(fixture.owned and fixture.file_open and fixture.counts['free'] == 0,
                    'uncertain/pending resource was prematurely released')
        if label == 'sd-not-ready':
            require(fixture.counts['alloc'] == 0, 'not-ready attempt allocated')
        boundaries.append(dict(case=label,expected_state=expected,
            unresolved_resources_retained=label in ('close-uncertain','read-pending')))

    require(all(sha(p.read_bytes()) == fingerprints[str(p.relative_to(ROOT))] for p in paths),
            'workflow source changed during the run')
    report = dict(schema='epl9-sd-source-only-workflow-v1',reader=provenance,
        source_sha256=fingerprints,loader_sha256=LOADER_SHA,
        author_preflight=dict(recipe_id=example['recipe_id'],name=example['name'],
            author_controls_valid=True,gamma_compiled=False,record_exported=False),
        valid_bundle_cases=cases,rejected_bundle_cases=rejected,resource_boundaries=boundaries,
        native_invocations=len(native_runs),native_runs=native_runs,
        synthetic_records_only=True,all_scoped_checks_passed=True,
        records_compiled_from_stock=False,stock_main_available=MAIN.is_file(),
        native_standalone_loader_executed=True,
        per_slot_file_task_and_pool_services_modeled=True,
        shared_hls_manager_or_stock_file_wrappers_executed=False,
        shutdown_protocol_executed=False,pixels_produced=False,
        native_menu_slots_assigned=False,physical_sd_tested=False,
        camera_accessed=False,install_ready=False)
    (out/'validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(valid_bundles=len(cases),rejected_bundles=len(rejected),
        resource_boundaries=len(boundaries),native_invocations=len(native_runs),
        all_scoped_checks_passed=True,install_ready=False)))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reader',type=Path,default=default_reader())
    parser.add_argument('--out',type=Path,required=True)
    args = parser.parse_args()
    run(args.out,args.reader)
