"""Enter the native executor again at a live v3 configuration checkpoint.

The second execution uses a cloned RAM/model snapshot: it cannot alter the
outer experiment. This tests actual job dispatch, not direct COLOR recursion.
No scheduler, hardware, or pixel completion is fabricated.
"""
import argparse
import copy
import json
from pathlib import Path

from epl9_workspace_bridge import ROOT, sha
from epl9_film_late_probe import prepare_probe
from epl9_job_probe import experiment, JOB, STACK, RETURN
from epl9_lifecycle_probe import Lifecycle
from epl9_wb_math_probe import extend
from epl9_v3_package import CANDIDATE_HASHES
from mn103_subset import Memory, Region, Fault
from mn103_calls import CallMachine


class Reentry(Lifecycle):
    def __init__(self, module):
        super().__init__(module['base'])
        self.module = module
        self.reentries = []

    def __call__(self, m):
        super().__call__(m)
        enter = m.enter

        def inspect(target, return_pc, mask=0, frame=0):
            if target == self.module['symbols']['film_color_original']:
                memory = Memory([Region(r.address, bytearray(r.data), r.writable, r.name)
                                 for r in m.memory.regions])
                child = CallMachine(m.code, memory,
                    dict(sp=STACK+8192, d0=JOB, d1=memory.read(JOB+10390,2)),
                    models=copy.deepcopy(m.models))
                start = child.enter(0x6074e6eb, RETURN, 0xf0, 32)
                try:
                    result = child.run(start, [RETURN,0x6074e765,0x6079fb88,0x6073f74f], limit=500000)
                except Fault as error:
                    result = dict(status='fault', error=str(error))
                self.reentries.append(dict(cursor=memory.read(JOB+10388,2),
                    original_cursor=m.memory.read(JOB+10388,2),
                    job_error_before=m.memory.read(JOB+10392,2),
                    job_error_after=memory.read(JOB+10392,2),
                    result=result, return_value=hex(child.r['d0']),
                    entered_color=result.get('pc')==0x6079fb88,
                    duplicate_work_dispatch=result.get('pc')==0x6074e765,
                    selected_work_callback=hex(child.r['a1']) if result.get('pc')==0x6074e765 else None,
                    hardware_start_boundary=result.get('pc')==0x6073f74f,
                    modeled_calls=[dict(target=hex(e['target']), model=e['model'])
                        for e in child.events if e['op']=='modeled_call'],
                    trace_tail=[hex(p) for p in child.trace[-20:]],
                    instructions=len(child.trace), memory_snapshot_isolated=True))
            return enter(target, return_pc, mask, frame)
        m.enter = inspect


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',type=Path,required=True)
    args = ap.parse_args()
    rgb=json.loads((ROOT/'local/epl9-native-film-curves-v3-20261107/native-rgb-tables.json').read_text())
    wb=json.loads((ROOT/'recipes/epl9-native-wb-trial-v1.json').read_text())
    image,patched,_,code,module,manifest=prepare_probe(args.out,base=0x604a1300,
        rgb_document=rgb,wb_document=wb)
    if sha(patched)!=CANDIDATE_HASHES[0x100]:
        raise ValueError('frozen v3 identity changed')
    extend(image,code)
    rows=[]
    for key in (0x01010078,0x01020078):
        for kind in (0x200,0x100,0x40):
            observer=Reentry(module)
            options=dict(provide_slot=True,input_format=0x100) if kind==0x40 else {}
            result=experiment(patched,code,key,kind,0,native_module=module,
                machine_observer=observer,gain_fixture=(1024,)*4,**options)
            if not observer.reentries or not observer.restored or observer.pending:
                raise ValueError('outer execution did not reach/restore the checkpoint')
            if result['output_changed'] or result['event_bits_signalled']:
                raise ValueError('fabricated pixels/completion')
            rows.append(dict(key=hex(key),kind=hex(kind),reentries=observer.reentries,
                outer_executor=result['executor'],outer_request_restored=True))
            if any(r['result'].get('pc')!=0x6074e765 or
                   r['original_cursor']!=r['cursor'] for r in observer.reentries):
                raise ValueError('native duplicate-dispatch control differed')
            print(json.dumps(dict(key=hex(key),kind=hex(kind),duplicate_dispatch=True)),flush=True)
    report=dict(main_sha256=sha(image),candidate_main_sha256=sha(patched),cases=rows,
        source_sha256=sha(Path(__file__).read_bytes()),
        scheduler_or_camera_executed=False,install_ready=False)
    (args.out/'job-reentry.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':
    main()
