"""Full-size local controls for the two-component readback comparator."""
import argparse
import json
from pathlib import Path
from epl9_workspace_bridge import ROOT, sha
from epl9_component_readback import references, compare, package_files, GENERATIONS


def run(out,generation='frozen-v3'):
    if out.exists() or not out.resolve().is_relative_to((ROOT/'local').resolve()):
        raise ValueError('new ignored report directory required')
    private = generation=='private-color-v3'
    packages = ROOT/('local/epl9-v3-private-packages-20261107' if private else 'local/epl9-v3-packages-20261107')
    refs = references(packages,generation)
    files = package_files(generation)
    native_path=ROOT/('local/epl9-v3-private-package-native-20261107/validation.json' if private else
        'local/epl9-v3-package-native-final-20261107/validation.json')
    native = json.loads(native_path.read_text())
    if native['package_manifest_sha256']!=sha((packages/'manifest.json').read_bytes()):
        raise ValueError('native validation used a different package manifest')
    # Compare the envelopes with independently recorded native writer-boundary
    # hashes, not merely the decoder's own payload hash.
    for label, (name, _) in files.items():
        row = next(r for r in native['cases'] if r['file'] == name and r['mode'] == 0
                   and not r.get('negative_control'))
        for request in row['backend_requests']:
            kind = {'0x100': 'main', '0x101': 'osd'}[request['kind']]
            if sha(refs[label][kind]) != request['decoded_envelope_sha256']:
                raise ValueError('reference differs from native writer boundary')
    cases = []

    def check(name, target, main, osd, want, repeated=None):
        samples = {'main': (main, main), 'osd': (osd, osd)}
        if repeated is not None:
            samples['main'] = (main, repeated)
        report = compare(samples, refs, target)
        if report['both_component_bytes_match'] != want:
            raise ValueError('unexpected full-size comparison: '+name)
        cases.append(dict(control=name, **report))

    for target in files:
        check('exact-'+target, target, refs[target]['main'], refs[target]['osd'], True)
        for main, osd in [('stock', 'v3'), ('v3', 'stock')]:
            check('mixed-'+main+'-'+osd, target, refs[main]['main'], refs[osd]['osd'], False)
    main, osd = refs['v3']['main'], refs['v3']['osd']
    for label, at in [('header', 0), ('body', 32+0xa12e0), ('trailer', len(main)-1)]:
        bad = bytearray(main)
        bad[at] ^= 1
        check('corrupt-'+label, 'v3', bytes(bad), osd, False)
    bad = bytearray(main)
    bad[100] ^= 1
    check('unstable-repeat', 'v3', main, osd, False, bytes(bad))
    check('body-only-wrong-layout', 'v3', main[32:-32], osd, False)
    check('truncated', 'v3', main[:-1], osd, False)
    check('swapped-components', 'v3', osd, main, False)
    encoded = (packages/files['v3'][0]).read_bytes()
    check('encoded-package-is-not-readback', 'v3', encoded[:len(main)], encoded[len(main):], False)
    if private:
        old=references(ROOT/'local/epl9-v3-packages-20261107')
        check('old-v3-main-is-not-private-color', 'v3', old['v3']['main'],osd,False)
        reverse=compare({'main':(main,main),'osd':(osd,osd)},old,'v3')
        if reverse['both_component_bytes_match']:
            raise ValueError('new candidate incorrectly accepted as frozen generation')
        cases.append(dict(control='private-color-is-not-old-v3',**reverse))
    out.mkdir()
    report = dict(generation=generation,controls=cases, native_boundary_reference_match=True,
        package_manifest_sha256=sha((packages/'manifest.json').read_bytes()),
        native_report_sha256=sha(native_path.read_bytes()),
        source_sha256={name: sha((ROOT/'scripts'/name).read_bytes()) for name in
                       ('epl9_readback_probe.py', 'epl9_component_readback.py')},
        source_kind='synthetic local data, not camera acquisition',
        camera_accessed=False, physical_write_or_restore_verified=False)
    (out/'readback-controls.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(full_size_controls=len(cases), native_boundary_reference_match=True,
        camera_accessed=False)))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--generation',choices=GENERATIONS,default='frozen-v3')
    args=ap.parse_args()
    run(args.out,args.generation)
