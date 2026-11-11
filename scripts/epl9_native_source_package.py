"""Build the separate native-source-v1 main+OSD pair, entirely offline.

This does not replace frozen/private-COLOR v3 evidence, perform native updater
qualification, access a camera, prepare a card, or establish install readiness.
All emitted firmware and private reconstruction evidence must stay in local/.
"""
import argparse
import base64
import json
from pathlib import Path
import subprocess
import zipfile

from epl9_film_late_module import build_late_module
from epl9_recovery_audit import inspect_package, decoded_payload, WINDOWS, STATIC_WINDOWS
from epl9_v3_package import (component, pair, independent_parser, KINDS,
    CANDIDATE_HASHES, PRIVATE_CANDIDATE_HASHES)
from epl9_workspace_bridge import ROOT, BASE, MAIN_SHA, sha
from epl9_color_audit import STOCK_SHA

GENERATION = 'native-source-v1'
MAIN_BYTES = 26214336
PAIR_BYTES = 52428800
MODULE_BASE = 0x604a1300
MODULE_BYTES = 0x3c00
MAIN_HASH = '2d003930675b47774e9ed3535ee49c64f56ff519bd6f1a33ddafd1a8c688b9b7'
MODULE_HASH = '89803a465ae76a81ae6b10055f0b8ff67dc30a1f162785bd8ee4f97e1c70d6e3'
OSD_HASH = '50141904c211fd16bc4c26b35cd52955f96a9e611ca062d84fe0169eeda21b3b'
STOCK_OSD_HASH = 'ee9a9c3ad1974dd212483ca7d012e51ae23083ce0119589a3b42996aa13ccf1e'
RESTORE_HASH = '10a7b949d1509ce627cb3c098c0a01a8ae5758fb2ce84b6c887e34b46e349387'
MODULE_MANIFEST_HASH = '101e5fb13d6a1c89f6115e5528d0c0c2a510330e063eec800e23ef799386db83'
OSD_MANIFEST_HASH = 'ea0d27c20b648dfd4393bcce27824b125b75237f0a118def7620378395380102'
RGB_HASH = '915f5cfd5d89d78a01b36b386bcab4e874ffc664b7de8017c9f0f9cf92c6a1cb'
RECIPE_HASHES = {
    'recipes/epl9-film-drafts-v0.json': '13947acdc18e87ea8756872b23dbb92564e59775c27eec3fb8525ee97555ce59',
    'recipes/epl9-film-drafts-v1.json': '048d795d6687619da6d5929bf7f1e0a76700a01e06af3b6da5b516fddfce4285',
    'recipes/epl9-film-drafts-v2.json': '8227e85ee818bb063cc6c0262b5b99d8883153981bc1de09a017231c08b29073',
    'recipes/epl9-native-wb-trial-v1.json': '64308eb17d67f6608cf5efa8e6dc234b4d48fd6d0f40b86600f7adad2fe8ea0a',
}
MODULE_DIR = ROOT/'local/cloud-reentry-native-source-20261111/run-v5/module'
OSD_DIR = ROOT/'local/cloud-private-reconstructed-osd-20261110'
DEFAULTS = dict(
    stock=ROOT/'firmware/OLY_E_133_1101_0000_0000.BIN',
    stock_main=ROOT/'local/epl9-1101-analysis/decoded/00_0100_406e0020.decoded.bin',
    main=MODULE_DIR/'main-with-module-OFFLINE-ONLY.decoded.bin',
    module=MODULE_DIR/'epl9-films-native.bin',
    module_manifest=MODULE_DIR/'manifest.json',
    module_source=MODULE_DIR/'epl9-films-native.s',
    osd=OSD_DIR/'OSD-icons-OFFLINE-ONLY.decoded.bin',
    osd_manifest=OSD_DIR/'manifest.json',
    rgb_tables=ROOT/'local/cloud-private-reconstructed-v3-20261110/native-rgb-tables.json')
CANDIDATE_NAME = 'Gold-Portra-v3-native-source-candidate.bin'
RESTORE_NAME = 'Stock-1101-main-osd-restore.bin'
EXPECTED_HOOKS = (
    (0x60752202, '881cf9140c', 'dcfef0d4ff'),
    (0x6079d7f4, 'cd34fbf01cf8923d', 'dd6d3ed0fff01ccb'),
    (0x6079fb88, 'f1d3f1ef53', 'dc7e1ed0ff'),
    (0x60761c9e, 'fab4f002a000', 'dc37fbd3ffcb'),
)
ICON_IDS = {'4387','4388','4420','4421','4458','4459','4556','4557','A076','A077'}
PRIVATE_ARCHIVE_INPUTS = {
    'rgb_tables': 'native-rgb-tables.json',
    'module_manifest': 'native-source-module-manifest.json',
    'osd_manifest': 'v3-icon-osd-manifest.json',
    'module_source': 'native-source-module.s',
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def pinned(path, expected, size=None):
    path = Path(path)
    data = path.read_bytes()
    require(sha(data) == expected and (size is None or len(data) == size),
            'input identity mismatch: '+str(path))
    return data


def overlay_spans(originals, replacements, patches):
    """Require exact old-byte guards and exhaustive, disjoint decoded changes."""
    require(set(originals) == set(replacements) == set(KINDS), 'requires both decoded components')
    require(all(len(originals[k]) == len(replacements[k]) for k in KINDS),
            'decoded component resized')
    rebuilt = {k: bytearray(v) for k, v in originals.items()}
    ends = {k: 0 for k in KINDS}
    rows = []
    for patch in sorted(patches, key=lambda p: (p['kind'], p['offset'])):
        kind, at = patch['kind'], patch['offset']
        before, after = patch['before'], patch['after']
        require(kind in KINDS and type(at) is int and at >= ends[kind] and
                before and len(before) == len(after) and
                at+len(before) <= len(originals[kind]) and
                originals[kind][at:at+len(before)] == before,
                'invalid overlay boundary or original-byte guard')
        require(before != after, 'overlay span does not change any bytes')
        rebuilt[kind][at:at+len(after)] = after
        ends[kind] = at+len(after)
        row = dict(kind=hex(kind), offset=hex(at), end=hex(at+len(before)),
            bytes=len(before), changed_bytes=sum(a != b for a,b in zip(before,after)),
            label=patch['label'], before_sha256=sha(before), after_sha256=sha(after),
            old=base64.b64encode(before).decode('ascii'),
            new=base64.b64encode(after).decode('ascii'))
        if kind == 0x100:
            row.update(address=hex(BASE+at), address_end=hex(BASE+at+len(before)))
        rows.append(row)
    require(all(bytes(rebuilt[k]) == replacements[k] for k in KINDS),
            'candidate has decoded changes outside declared overlay')
    return rows


def verify_protected(original, replacement, ranges=None):
    protected = ranges if ranges is not None else WINDOWS | STATIC_WINDOWS | {
        'early_startup': (0x60400020, 0x60400280),
        'task_descriptors': (0x60418cc4, 0x60419c68)}
    rows = []
    for name,(start,end) in protected.items():
        a,b = start-BASE,end-BASE
        require(0 <= a < b <= len(original) and len(original) == len(replacement),
                'protected range outside main: '+name)
        require(original[a:b] == replacement[a:b],
                'audited updater/startup dependency modified: '+name)
        rows.append(dict(name=name,start=hex(start),end=hex(end),bytes=end-start,
                         sha256=sha(original[a:b])))
    return rows


def module_main(original, module):
    output = bytearray(original)
    at = MODULE_BASE-BASE
    require(original[at:at+len(module['data'])] == b'\xff'*MODULE_BYTES,
            'module slot is not exact stock padding')
    output[at:at+len(module['data'])] = module['data']
    for patch in module['patches']:
        at = patch['address']-BASE
        before,after = bytes.fromhex(patch['before']),bytes.fromhex(patch['after'])
        require(original[at:at+len(before)] == before and len(before) == len(after),
                'module reproduction hook guard failed')
        output[at:at+len(after)] = after
    return bytes(output)


def reproduce(original, rgb, expected_main, expected_module, module_source):
    """Reassemble all three generations; old defaults and every table stay fixed."""
    wb = json.loads(pinned(ROOT/'recipes/epl9-native-wb-trial-v1.json',
                           RECIPE_HASHES['recipes/epl9-native-wb-trial-v1.json']))
    options = dict(base=MODULE_BASE,rgb_document=rgb,wb_document=wb)
    modules = [build_late_module(original,**options),
               build_late_module(original,**options,private_color=True),
               build_late_module(original,**options,private_color=True,native_source_gate=True)]
    identities = [('frozen-v3',CANDIDATE_HASHES[0x100],
                   '18f17217c96d0ef7b6cd767f9738825ed9913a0df32435358237304f3f6a73a9'),
                  ('private-color-v3',PRIVATE_CANDIDATE_HASHES[0x100],
                   '8878c9c99d6ba28d996a86201ca0d4aef3ec6f0e37bac2af2140889025b6c685'),
                  (GENERATION,MAIN_HASH,MODULE_HASH)]
    reports = []
    for built,(generation,main_hash,module_hash) in zip(modules,identities):
        rebuilt = module_main(original,built)
        require(sha(rebuilt) == main_hash and sha(built['data']) == module_hash,
                'source reproduction failed for '+generation)
        require(built['data'][4096:] == expected_module[4096:],
                'numerical table bytes changed between generations')
        reports.append(dict(generation=generation,main_sha256=main_hash,
            module_sha256=module_hash,code_bytes=built['code_bytes'],
            numerical_tables_sha256=sha(built['data'][4096:]),reproduced_from_source=True))
    new = modules[-1]
    require(module_main(original,new) == expected_main and new['data'] == expected_module and
            new['source'].encode('utf-8') == module_source,
            'retained native-source bytes or authored source differ from reproduction')
    hooks = tuple((p['address'],p['before'],p['after']) for p in new['patches'])
    require(hooks == EXPECTED_HOOKS, 'native-source hook inventory changed')
    return reports


def validate_pair(data, stock, expected, ref):
    """Both strict implementations must agree, preserving original envelopes."""
    rows = inspect_package(data)
    require([int(r['kind'],16) for r in rows] == list(KINDS),
            'selected package must contain exactly main then OSD')
    blocks = ref.parse(data)
    require([b.kind for b in blocks] == list(KINDS) and ref.reconstruct(blocks) == data,
            'independent selected-package roundtrip failed')
    originals = {b.kind:b for b in ref.parse(stock)}
    for block in blocks:
        source = originals[block.kind]
        require(block.payload == expected[block.kind] and block.header == source.header and
                block.trailer[:28] == source.trailer[:28],
                'independent payload or original envelope metadata mismatch')
    return rows


def source_snapshot():
    """Capture project sources, never vendor reference checkouts or firmware."""
    tracked = subprocess.check_output(['git','-C',str(ROOT),'ls-files','-z',
        'scripts','firmware_src','recipes','AGENTS.md','docs/epl9-native-source-gates.md',
        'docs/epl9-v3-package-validation.md','docs/epl9-v3-private-deployment.md',
        'docs/epl9-native-source-v1-package.md']).decode().split('\0')
    names = set(filter(None,tracked)) | {
        'scripts/epl9_native_source_package.py','scripts/test_epl9_native_source_package.py'}
    require(all(not Path(n).is_absolute() and '..' not in Path(n).parts and
                (ROOT/n).is_file() for n in names), 'invalid project source snapshot')
    return {name:(ROOT/name).read_bytes() for name in sorted(names)}


def save_archive(path, sources, private_inputs):
    require(set(private_inputs) == set(PRIVATE_ARCHIVE_INPUTS.values()) and
            all(type(data) is bytes for data in private_inputs.values()),
            'source archive requires exact RGB, reconstruction metadata and authored source inputs')
    private_files = {'private-inputs/'+name:data for name,data in private_inputs.items()}
    require(not sources.keys() & private_files.keys(), 'source archive path collision')
    files = {**sources,**private_files}
    with zipfile.ZipFile(path,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for name,data in sorted(files.items()):
            info = zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0))
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info,data,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
    with zipfile.ZipFile(path) as archive:
        require(archive.testzip() is None and set(archive.namelist()) == set(files) and
                all(archive.read(n) == d for n,d in files.items()),
                'source archive readback mismatch')


def build(out, generation=GENERATION, **paths):
    require(generation == GENERATION, 'unknown native-source package generation')
    require(set(paths) <= set(DEFAULTS), 'unknown input path')
    paths = {k:Path(paths.get(k,v)).resolve() for k,v in DEFAULTS.items()}
    out = Path(out).resolve()
    require(not out.exists() and out.is_relative_to((ROOT/'local').resolve()),
            'new ignored local output directory required')
    ignored = subprocess.run(['git','-C',str(ROOT),'check-ignore','-q','--',str(out)])
    require(ignored.returncode == 0, 'output must remain Git-ignored')
    sources = source_snapshot()
    recipes = {name:sha(pinned(ROOT/name,digest)) for name,digest in RECIPE_HASHES.items()}
    raw = {}
    for name,digest,size in (
        ('stock',STOCK_SHA,104552480),('stock_main',MAIN_SHA,MAIN_BYTES),
        ('main',MAIN_HASH,MAIN_BYTES),('module',MODULE_HASH,MODULE_BYTES),
        ('osd',OSD_HASH,MAIN_BYTES),('rgb_tables',RGB_HASH,None),
        ('module_manifest',MODULE_MANIFEST_HASH,None),('osd_manifest',OSD_MANIFEST_HASH,None)):
        raw[name] = pinned(paths[name],digest,size)
    module_manifest = json.loads(raw['module_manifest'])
    icon_manifest = json.loads(raw['osd_manifest'])
    raw['module_source'] = pinned(paths['module_source'],module_manifest['source_sha256'])
    require(module_manifest['module_base'] == hex(MODULE_BASE) and
            module_manifest['module_bytes'] == MODULE_BYTES and
            module_manifest['native_source_gate_policy'] == 'primary-art-base-variant-v1',
            'retained native-source module evidence differs')
    stock_rows = inspect_package(raw['stock'])
    require([int(r['kind'],16) for r in stock_rows] == [0x100,0x101,0x106,0x10e,0x102],
            'unexpected stock component inventory/order')
    originals = {int(row['kind'],16):decoded_payload(component(raw['stock'],row)[32:-32])
                 for row in stock_rows if int(row['kind'],16) in KINDS}
    require(originals[0x100] == raw['stock_main'] and sha(originals[0x101]) == STOCK_OSD_HASH,
            'decoded stock components differ')
    replacements = {0x100:raw['main'],0x101:raw['osd']}
    reproduced = reproduce(originals[0x100],json.loads(raw['rgb_tables']),
                           raw['main'],raw['module'],raw['module_source'])
    at = MODULE_BASE-BASE
    patches = [dict(kind=0x100,offset=at,before=originals[0x100][at:at+MODULE_BYTES],
                    after=raw['module'],label='native-source private module')]
    declared_hooks = tuple((int(p['address'],16),p['before'],p['after'])
                           for p in module_manifest['candidate_patches'])
    require(declared_hooks == EXPECTED_HOOKS, 'module hook manifest differs')
    for address,before,after in EXPECTED_HOOKS:
        patches.append(dict(kind=0x100,offset=address-BASE,before=bytes.fromhex(before),
                            after=bytes.fromhex(after),label='native hook '+hex(address)))
    changes = icon_manifest['changes']
    require(len(changes) == 10 and {r['id'] for r in changes} == ICON_IDS,
            'OSD evidence must contain exactly the ten existing film badges')
    for row in changes:
        at,size = int(row['offset'],16),row['bytes']
        before,after = originals[0x101][at:at+size],raw['osd'][at:at+size]
        require(len(before) == size and sha(before) == row['before_sha256'] and
                sha(after) == row['after_sha256'], 'OSD evidence byte guard differs')
        patches.append(dict(kind=0x101,offset=at,before=before,after=after,
                            label='existing v3 film badge '+row['id']))
    spans = overlay_spans(originals,replacements,patches)
    require(len(spans) == 15, 'native-source package requires fifteen declared spans')
    protected = verify_protected(originals[0x100],raw['main'])
    candidate,restore = pair(raw['stock'],replacements)
    require(len(candidate) == len(restore) == PAIR_BYTES and sha(restore) == RESTORE_HASH,
            'stock restore is not the exact unchanged two-component file')
    ref = independent_parser()
    require(ref.reconstruct(ref.parse(raw['stock'])) == raw['stock'],
            'independent full stock roundtrip failed')
    reports = []
    for name,data,expected in ((CANDIDATE_NAME,candidate,replacements),
                                (RESTORE_NAME,restore,originals)):
        rows = validate_pair(data,raw['stock'],expected,ref)
        reports.append(dict(file=name,bytes=len(data),sha256=sha(data),components=rows,
                            independent_roundtrip=True))
    require(all((ROOT/name).read_bytes() == data for name,data in sources.items()),
            'project source changed during packaging')
    require(all(paths[k].read_bytes() == data for k,data in raw.items()),
            'private input changed during packaging')
    overlay = dict(schema='epl9-native-source-decoded-overlay-v1',generation=GENERATION,
        scope='new evidence, not a recreated historical integration manifest',patches=spans,
        original_sha256={hex(k):sha(v) for k,v in originals.items()},
        replacement_sha256={hex(k):sha(v) for k,v in replacements.items()})
    out.mkdir(parents=True)
    for report,data in zip(reports,(candidate,restore)):
        with (out/report['file']).open('xb') as stream:
            stream.write(data)
        require(sha((out/report['file']).read_bytes()) == report['sha256'],
                'written package hash mismatch')
    (out/'decoded-overlay.json').write_text(json.dumps(overlay,indent=2)+'\n',encoding='utf-8')
    (out/'native-source-module.s').write_bytes(raw['module_source'])
    archive = out/'private-source-reproduction.zip'
    private_sources = {name:raw[key] for key,name in PRIVATE_ARCHIVE_INPUTS.items()}
    save_archive(archive,sources,private_sources)
    evidence = {name:dict(path=str(paths[name]),bytes=len(data),sha256=sha(data))
                for name,data in raw.items()}
    candidate_components = [dict(kind=hex(kind),path=str(paths[key]),bytes=len(raw[key]),sha256=sha(raw[key]))
                            for kind,key in ((0x100,'main'),(0x101,'osd'))]
    limitations = ['Native full-size validator and early-load qualification are separate evidence.',
        'Whole UI/owner/runtime/IRQ and code-slot/cache/DMA lifetime remain unqualified.',
        'Same-job exclusion remains required; private COLOR copies are not a lock.',
        'Independent camera acquisition/readback, entry/recovery and physical restoration remain unqualified.',
        'TruePic output pixels and hardware completion have not been tested.']
    report = dict(schema='epl9-native-source-package-pair-v1',generation=GENERATION,
        model='E-PL9',model_bytes='1330',displayed_body_version='1.1 (owner report)',
        downloaded_main_build='1101',stock_file=str(paths['stock']),stock_bytes=len(raw['stock']),
        stock_sha256=STOCK_SHA,files=reports,candidate_components=candidate_components,
        evidence=evidence,recipe_sha256=recipes,native_rgb_tables_sha256=RGB_HASH,
        source_reproduction=reproduced,numerical_tables_unchanged_from_both_v3_generations=True,
        declared_decoded_changes=[{k:v for k,v in r.items() if k not in ('old','new')} for r in spans],
        decoded_overlay_file='decoded-overlay.json',
        decoded_overlay_sha256=sha((out/'decoded-overlay.json').read_bytes()),
        changed_decoded_bytes=sum(r['changed_bytes'] for r in spans),
        preserved_updater_startup_ranges=protected,
        excluded_stock_components=[r for r in stock_rows if int(r['kind'],16) not in KINDS],
        independent_reference=dict(url='https://github.com/fishcu/oly_fw_analysis',
            commit=ref.__dict__.get('REFERENCE_COMMIT',
                '539fcf1fa9eda5fdef8ede4deeab94a4691d94c3'),**ref._source_identity),
        source_preservation=dict(file=archive.name,sha256=sha(archive.read_bytes()),
            bytes=archive.stat().st_size,project_source_sha256={n:sha(d) for n,d in sources.items()},
            private_inputs={'private-inputs/'+name:dict(evidence_key=key,
                bytes=len(raw[key]),sha256=sha(raw[key])) for key,name in PRIVATE_ARCHIVE_INPUTS.items()},
            includes_private_rgb_input=True,includes_upstream_source=False,
            includes_required_reconstruction_metadata=True,includes_firmware_bytes=False,
            git_head=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()),
        metadata_and_lengths_preserved=True,restore_exact_stock_component_bytes=True,
        selective_package=True,host_checks_passed=True,native_validation_status='pending separate evidence',
        early_load_status='pending separate evidence',ui_session_status='pending separate evidence',
        historical_evidence_resealed=False,frozen_private_defaults_unchanged=True,
        private_only=True,camera_accessed=False,media_written=False,physical_writes=False,
        physical_restore_verified=False,install_ready=False,limitations=limitations,
        status='New offline encoded pair; strict host checks and source reproduction passed only')
    (out/'manifest.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    qualification = dict(schema='epl9-native-source-package-qualification-v1',generation=GENERATION,
        package_manifest_sha256=sha((out/'manifest.json').read_bytes()),host_checks_passed=True,
        source_reproduction_passed=True,native_full_size='pending',early_load='pending',ui_session='pending',
        install_ready=False,physical_restore_verified=False,limitations=limitations)
    (out/'qualification.json').write_text(json.dumps(qualification,indent=2)+'\n',encoding='utf-8')
    (out/'SHA256SUMS.txt').write_text(''.join(f"{r['sha256']}  {r['file']}\n" for r in reports),encoding='ascii')
    (out/'README.txt').write_text(
        'Private offline native-source-v1 research pair. NOT INSTALL READY.\n'
        'No camera, card, flash or physical restoration was accessed or verified.\n'
        'Candidate: Gold/Portra v3 tables unchanged; exact corrected native-source main and existing v3 icon OSD.\n'
        'Return: exact original encoded stock main and OSD; not a device-specific backup or proven recovery.\n'
        'Native validation, early load and UI evidence must be qualified separately for this generation.\n'
        'All other runtime, same-job, cache/DMA, entry/readback and physical recovery limits remain.\n'
        'Source archive preserves exact RGB JSON, both pinned reconstruction manifests and authored module assembly.\n'
        'Source archive excludes external projects, firmware BIN/decoded bytes and decoded overlay vendor bytes.\n'
        'Stock update, decoded stock main, corrected main/module and existing v3 icon OSD remain separately required private inputs.\n'
        'After extraction, --rgb-tables, --module-manifest, --osd-manifest and --module-source can select private-inputs/ files.\n'
        'Reproduce with python scripts/epl9_native_source_package.py --generation native-source-v1 '
        '--out local/NEW-DIRECTORY; use --help for explicit input paths.\n'
        'Do not substitute this main/package into frozen-v3 or private-color-v3 references.\n',encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--generation',choices=(GENERATION,),default=GENERATION)
    for name,path in DEFAULTS.items():
        parser.add_argument('--'+name.replace('_','-'),type=Path,default=path)
    args = vars(parser.parse_args())
    report = build(**args)
    print(json.dumps(dict(generation=report['generation'],files=[
        {k:r[k] for k in ('file','bytes','sha256')} for r in report['files']],
        host_checks_passed=True,source_reproduction_passed=True,install_ready=False),indent=2))


if __name__ == '__main__':
    main()
