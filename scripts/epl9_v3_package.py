"""Build frozen E-PL9 v3/stock two-component update files, entirely offline.

No media/card naming, camera interface, settings changes or physical writes.
Container validity is distinct from installation readiness and recovery ability.
"""
import argparse
from array import array
import base64
import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import sys

from epl9_recovery_audit import inspect_package, decoded_payload, ORDER, WINDOWS, STATIC_WINDOWS
from epl9_workspace_bridge import ROOT, BASE, MAIN_SHA, sha
from epl9_color_audit import STOCK_SHA

STOCK = ROOT/'firmware/OLY_E_133_1101_0000_0000.BIN'
INTEGRATION = ROOT/'local/epl9-v3-integration-20261107/manifest.json'
OVERLAY = ROOT/'local/epl9-v3-combined-overlay-20261107/combined.json'
CANDIDATE_HASHES = {0x100: '501707d09a0eb648e46196752b7ece17cd5368f6d54dbabce7c73e9806f65686',
                    0x101: '50141904c211fd16bc4c26b35cd52955f96a9e611ca062d84fe0169eeda21b3b'}
PRIVATE_CANDIDATE_HASHES = {**CANDIDATE_HASHES,
    0x100: '72cc1e48e6b42ab02b9911bdb841fe2c5b0cb34f2c08893f6b78be8a6871beee'}
GENERATIONS = ('frozen-v3', 'private-color-v3')
REFERENCE_COMMIT = '539fcf1fa9eda5fdef8ede4deeab94a4691d94c3'
REFERENCE_SOURCE_SHA = '2b72243f7af4735f5e341ce8f04ec4527dcf40ccfcf9ae3741efe7146657dce2'
KINDS = (0x100, 0x101)
INVERT = bytes(x ^ 255 for x in range(256))


def sum32(data):
    if not data or len(data) % 4:
        raise ValueError('checksum requires nonempty whole words')
    words = array('I')
    if words.itemsize != 4:
        raise ValueError('host unsigned int must be 32 bits')
    words.frombytes(data)
    if sys.byteorder != 'little':
        words.byteswap()
    return sum(words) & 0xffffffff


def encode_payload(plain):
    if not plain or len(plain) % 16:
        raise ValueError('payload must be nonempty and 16-byte aligned')
    encoded = bytearray(len(plain))
    for i, j in enumerate(ORDER):
        encoded[j::16] = plain[i::16].translate(INVERT)
    return bytes(encoded)


def component(raw, row):
    at, size = int(row['offset'], 16), row['package_bytes']
    return raw[at:at+size]


def replace_component(template, plain):
    rows = inspect_package(template)
    if len(rows) != 1 or int(rows[0]['kind'], 16) not in KINDS:
        raise ValueError('requires one main or OSD component')
    if len(plain) != rows[0]['payload_bytes']:
        raise ValueError('replacement size changed')
    header, trailer = template[:32], bytearray(template[-32:])
    trailer[28:] = bytes(4)
    struct.pack_into('<I', trailer, 28, (-sum32(header+plain+trailer)) & 0xffffffff)
    result = header+encode_payload(plain)+trailer
    verified, = inspect_package(result)
    if verified['decoded_sha256'] != sha(plain):
        raise ValueError('encoded payload does not decode to intended bytes')
    if result[:32] != template[:32] or result[-32:-4] != template[-32:-4]:
        raise ValueError('component identity metadata changed')
    return result


def pair(stock, replacements):
    if set(replacements) != set(KINDS):
        raise ValueError('both and only main/OSD replacements are required')
    rows = inspect_package(stock)
    selected = [r for r in rows if int(r['kind'], 16) in KINDS]
    if [int(r['kind'], 16) for r in selected] != list(KINDS):
        raise ValueError('expected unique main then OSD in stock order')
    restore = b''.join(component(stock, row) for row in selected)
    candidate = b''.join(replace_component(component(stock, row), replacements[int(row['kind'], 16)])
                         for row in selected)
    if len(candidate) != len(restore):
        raise ValueError('candidate/restore size mismatch')
    return candidate, restore


def independent_parser():
    repo = ROOT/'references/oly_fw_analysis'
    commit = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
    path = repo/'tools/oly_container.py'
    if commit != REFERENCE_COMMIT or sha(path.read_bytes()) != REFERENCE_SOURCE_SHA:
        raise ValueError('independent container implementation changed')
    spec = importlib.util.spec_from_file_location('epl9_pinned_container', path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def verify_overlay(originals, replacements, overlay_path=OVERLAY):
    patches = json.loads(overlay_path.read_text())['patches']
    rebuilt = {kind: bytearray(data) for kind, data in originals.items()}
    ends = {kind: 0 for kind in KINDS}
    changed = []
    for patch in sorted(patches, key=lambda p: (p['block'], p['offset'])):
        kind = {'main': 0x100, 'resource': 0x101}[patch['block']]
        at = patch['offset']
        before, after = (base64.b64decode(patch[k], validate=True) for k in ('old', 'new'))
        if (not before or len(before) != len(after) or at < ends[kind] or
                originals[kind][at:at+len(before)] != before):
            raise ValueError('invalid overlay boundary or original-byte guard')
        rebuilt[kind][at:at+len(after)] = after
        ends[kind] = at+len(after)
        changed.append(dict(kind=hex(kind), offset=hex(at), bytes=len(before),
            changed_bytes=sum(a != b for a, b in zip(before, after)), label=patch['label'],
            before_sha256=sha(before), after_sha256=sha(after)))
    if len(patches) != 15 or any(bytes(rebuilt[k]) != replacements[k] for k in KINDS):
        raise ValueError('candidate differs from the selected fifteen-span overlay')
    return changed


def generation_inputs(generation):
    if generation == 'frozen-v3':
        return INTEGRATION, OVERLAY, CANDIDATE_HASHES, 'Gold-Portra-v3-candidate.bin'
    if generation == 'private-color-v3':
        return (ROOT/'local/epl9-v3-private-integration-20261107/manifest.json',
            ROOT/'local/epl9-v3-private-overlay-20261107/combined.json',
            PRIVATE_CANDIDATE_HASHES, 'Gold-Portra-v3-private-color-candidate.bin')
    raise ValueError('unknown integration generation')


def build(out, generation='frozen-v3'):
    out = out.resolve()
    if out.exists() or not out.is_relative_to((ROOT/'local').resolve()):
        raise ValueError('new ignored local output directory required')
    integration, overlay_path, expected_hashes, candidate_name = generation_inputs(generation)
    frozen = json.loads(integration.read_text())
    for row in frozen['evidence'].values():
        if sha(Path(row['path']).read_bytes()) != row['sha256']:
            raise ValueError('frozen integration evidence changed')
    stock = STOCK.read_bytes()
    if len(stock) != 104552480 or sha(stock) != STOCK_SHA:
        raise ValueError('wrong stock E-PL9 1101 input')
    stock_rows = inspect_package(stock)
    if [int(r['kind'], 16) for r in stock_rows] != [0x100, 0x101, 0x106, 0x10e, 0x102]:
        raise ValueError('unexpected stock component inventory/order')
    replacements = {int(row['kind'], 16): Path(row['path']).read_bytes()
                    for row in frozen['candidate_components']}
    if {k: sha(v) for k, v in replacements.items()} != expected_hashes:
        raise ValueError('requires the exact selected v3 candidate')
    originals = {int(row['kind'], 16): decoded_payload(component(stock, row)[32:-32])
                 for row in stock_rows if int(row['kind'], 16) in KINDS}
    if sha(originals[0x100]) != MAIN_SHA:
        raise ValueError('decoded stock main differs')
    spans = verify_overlay(originals, replacements, overlay_path)
    # All existing recipe files are read-only and pinned in the output report.
    recipe_paths = [ROOT/f'recipes/epl9-film-drafts-v{v}.json' for v in (0, 1, 2)]
    recipe_paths += [ROOT/'recipes/epl9-native-wb-trial-v1.json',
                     ROOT/'local/epl9-native-film-curves-v3-20261107/native-rgb-tables.json']
    recipes = {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in recipe_paths}
    if generation == 'private-color-v3':
        previous = json.loads((ROOT/'local/epl9-v3-packages-20261107/manifest.json').read_text())
        if recipes != previous['recipe_sha256']:
            raise ValueError('private COLOR packaging must preserve all frozen recipe inputs')
    protected = WINDOWS | STATIC_WINDOWS | {'early_startup': (0x60400020, 0x60400280),
                                            'task_descriptors': (0x60418cc4, 0x60419c68)}
    protected_rows = []
    for name, (start, end) in protected.items():
        a, b = start-BASE, end-BASE
        if originals[0x100][a:b] != replacements[0x100][a:b]:
            raise ValueError('audited updater/startup dependency modified: '+name)
        protected_rows.append(dict(name=name, start=hex(start), end=hex(end),
                                   bytes=end-start, sha256=sha(originals[0x100][a:b])))
    candidate, restore = pair(stock, replacements)
    ref = independent_parser()
    source_blocks = ref.parse(stock)
    if ref.reconstruct(source_blocks) != stock:
        raise ValueError('independent full stock roundtrip failed')
    reports = []
    for label, data, expected in [(candidate_name, candidate, replacements),
                                   ('Stock-1101-main-osd-restore.bin', restore, originals)]:
        blocks = ref.parse(data)
        if [b.kind for b in blocks] != list(KINDS) or ref.reconstruct(blocks) != data:
            raise ValueError('independent selected-package roundtrip failed')
        for block in blocks:
            source = next(b for b in source_blocks if b.kind == block.kind)
            if (block.payload != expected[block.kind] or block.header != source.header or
                    block.trailer[:28] != source.trailer[:28]):
                raise ValueError('independent payload or metadata mismatch')
        reports.append(dict(file=label, bytes=len(data), sha256=sha(data),
                            components=inspect_package(data), independent_roundtrip=True))
    if any(recipe != sha((ROOT/name).read_bytes()) for name, recipe in recipes.items()):
        raise ValueError('recipe changed during packaging')
    out.mkdir()
    for row, data in zip(reports, (candidate, restore)):
        with (out/row['file']).open('xb') as stream:
            stream.write(data)
        if sha((out/row['file']).read_bytes()) != row['sha256']:
            raise ValueError('written file hash mismatch')
    report = dict(schema='epl9-v3-package-pair-v1', generation=generation, model='E-PL9', model_bytes='1330',
        displayed_body_version='1.1 (owner report)', downloaded_main_build='1101',
        stock_file=str(STOCK), stock_bytes=len(stock), stock_sha256=sha(stock),
        integration_manifest_sha256=sha(integration.read_bytes()),
        overlay_sha256=sha(overlay_path.read_bytes()),
        source_sha256=sha(Path(__file__).read_bytes()), files=reports,
        recipe_sha256=recipes, declared_decoded_changes=spans,
        preserved_updater_startup_ranges=protected_rows,
        excluded_stock_components=[r for r in stock_rows if int(r['kind'], 16) not in KINDS],
        independent_reference=dict(url='https://github.com/fishcu/oly_fw_analysis',
            commit=REFERENCE_COMMIT, source_sha256=REFERENCE_SOURCE_SHA),
        metadata_and_lengths_preserved=True, restore_exact_stock_component_bytes=True,
        selective_package=True, camera_accessed=False, media_written=False,
        physical_restore_verified=False, install_ready=False,
        status='Encoded two-component pair; host checks passed; native full-size checks separate')
    (out/'manifest.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    (out/'SHA256SUMS.txt').write_text(''.join(f"{r['sha256']}  {r['file']}\n" for r in reports), encoding='ascii')
    print(json.dumps(dict(out=str(out), files=[{k:r[k] for k in ('file','bytes','sha256')} for r in reports],
                         host_checks_passed=True, install_ready=False), indent=2))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--generation', choices=GENERATIONS, default='frozen-v3')
    args = ap.parse_args()
    build(args.out, args.generation)
