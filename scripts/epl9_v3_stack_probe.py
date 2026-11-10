"""Measure native call-frame fragments on the identified task-31 branch."""
import argparse
import json
from pathlib import Path
from epl9_workspace_bridge import ROOT, MAIN, MAIN_SHA, BASE, sha
from epl9_lifecycle_probe import task31
from mn103_subset import Memory, Region, parse_listing
from mn103_calls import CallMachine


def run(out, listings):
    if out.exists() or not out.resolve().is_relative_to((ROOT/'local').resolve()):
        raise ValueError('new ignored report required')
    image = MAIN.read_bytes()
    if sha(image) != MAIN_SHA:
        raise ValueError('stock identity differs')
    code, hashes = {}, {}
    for name in ('task31.tsv', 'process-parent.tsv', 'job-control.tsv'):
        path = listings/name
        code.update(parse_listing(path.read_text(encoding='utf-8-sig'), image, BASE))
        hashes[name] = sha(path.read_bytes())
    sp = 0x20008000
    m = CallMachine(code, Memory([Region(BASE, image),
        Region(0x20000000, bytearray(65536), True)]), dict(sp=sp))
    rows = []
    # Explicit fragments, not an emulated task scheduler or a fabricated path
    # through the intervening conditionals/diagnostic/resource calls.
    for start, stop in ((0x607ce1b5,0x607ce1bb),(0x607ce31c,0x607ce3f3),
                       (0x607ce460,0x607cf061),(0x607cf0e0,0x607ce5ae),
                       (0x607ce63f,0x6074e6eb)):
        before = m.r['sp']
        result = m.run(start, [stop])
        if result.get('pc') != stop:
            raise ValueError('stack fragment stopped unexpectedly: '+str(result))
        rows.append(dict(start=hex(start), stop=hex(stop), allocated_bytes=before-m.r['sp']))
    if [r['allocated_bytes'] for r in rows] != [372,20,60,28,32]:
        raise ValueError('native stack chain differs')
    binding = ROOT/'local/epl9-v3-owner-binding-20261107/binding.json'
    report = json.loads(binding.read_text())
    depth = max(r['stack']['observed_stack_depth'] for r in report['cases'])
    task = task31(image)
    task.update(fragment_measurements=rows,
        connected_job_observed_peak=depth,
        scoped_configuration_bytes=depth+sp-m.r['sp']-32,
        historical_prefix_392_corrected=True,
        scheduler_and_irq_budget_measured=False)
    result = dict(main_sha256=sha(image), input_binding_sha256=sha(binding.read_bytes()),
        listings_sha256=hashes, source_sha256=sha(Path(__file__).read_bytes()), task31=task,
        full_task_path_executed=False, all_callers_audited=False, install_ready=False)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(task, indent=2))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--listings', type=Path, required=True)
    args = ap.parse_args()
    run(args.out, args.listings)
