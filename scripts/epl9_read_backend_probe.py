"""Native read-wrapper status propagation, with all storage calls trapped.

Extends the selector-only audit through 604014c6. Never acquires pixel/flash
bytes or treats a model return as proof of a physical successful read.
"""
import argparse
import json
import struct
from pathlib import Path
from epl9_workspace_bridge import ROOT, MAIN, MAIN_SHA, BASE, sha
from epl9_component_readback import ADDRESSES, SIZE
from epl9_recovery_audit import Boundary
from mn103_subset import Memory, Region, parse_listing
from mn103_calls import CallMachine

SP, BUFFER, END = 0x18008000, 0x19000000, 0x1a000000


class LeafRead(Boundary):
    def __init__(self,name,status):
        super().__init__(name,[(0xf0,44)],status)
        self.calls=[]

    def apply(self,m):
        row=dict(source=hex(m.r['d1']),destination=hex(m.r['d0']),bytes=m.r['a0'],
            injected_result=self.backend_result,storage_executed=False,bytes_supplied=False)
        self.calls.append(row)
        m.r['d0']=self.backend_result
        return row


def run(out):
    if out.exists() or not out.resolve().is_relative_to((ROOT/'local').resolve()):
        raise ValueError('new ignored output path required')
    image=MAIN.read_bytes()
    if sha(image)!=MAIN_SHA:raise ValueError('stock main identity differs')
    listings=[ROOT/'local/epl9-v3-readback-route-20261107'/n for n in
        ('logical-read-selector.tsv','read-wrapper.tsv')]
    listings += [ROOT/'local/epl9-v3-readback-service-20261107/read-full.tsv']
    code={}
    for p in listings:code.update(parse_listing(p.read_text(encoding='utf-8-sig'),image,BASE))
    rows=[]
    for component,source in ADDRESSES.items():
        for mode in (0x101,0x103):
            for length in (16384,SIZE):
                for status in (0,1,0x310d):
                    page=LeafRead('unexecuted-page-read',status)
                    bulk=LeafRead('unexecuted-bulk-read',status)
                    mem=Memory([Region(BASE,image),Region(SP-32768,bytearray(65536),True),
                        Region(0x61f01120,bytes(4)),
                        Region(0xa2abc57c,struct.pack('<I',100))])
                    models={0x604009bf:page,0x60400d2f:bulk,
                        0x604016cc:Boundary('unexecuted-read-entry-helper',[(0,4)]),
                        0x604016f5:Boundary('unexecuted-read-exit-helper',[(0,4)]),
                        0x60401e69:Boundary('synthetic-clock-zero',[(0,4)]),
                        0x6040227a:Boundary('diagnostic-suppressed',[(0xa0,40)])}
                    m=CallMachine(code,mem,dict(sp=SP,a0=source,a1=BUFFER,d0=length,d1=mode),models=models)
                    r=m.run(m.enter(0x604a0f03,END,0xc0,12),[END])
                    calls=[dict(target=hex(e['target']),source=e['source'],destination=e['destination'],
                        bytes=e['bytes'],injected_result=e['injected_result']) for e in m.events
                        if e.get('target') in (0x604009bf,0x60400d2f)]
                    if r.get('pc')!=END or m.r['sp']!=SP or m.r['d0']!=0:
                        raise ValueError('native read wrapper return/stack differs: '+str(r))
                    if (sum(c['bytes'] for c in calls)!=length or
                        [c['target'] for c in calls]!=([hex(0x604009bf)] if length==16384 else
                            [hex(0x60400d2f),hex(0x604009bf)])):
                        raise ValueError('native aligned leaf calls differ')
                    cursor=source;dest=BUFFER
                    for c in calls:
                        if int(c['source'],0)!=cursor or int(c['destination'],0)!=dest:
                            raise ValueError('native read ranges are not contiguous')
                        cursor+=c['bytes'];dest+=c['bytes']
                    if not {0x604016bf,0x604016c0}.issubset(m.trace):
                        raise ValueError('unconditional native success return not executed')
                    rows.append(dict(component=component,mode=hex(mode),bytes=length,
                        injected_leaf_result=hex(status),outer_result=hex(m.r['d0']),
                        leaf_calls=calls,instructions=len(m.trace),stack_balanced=True,
                        leaf_error_masked=status!=0,storage_executed=False,read_bytes_obtained=False))
    for row in rows:
        other=next(r for r in rows if r['component']==row['component'] and r['bytes']==row['bytes'] and
            r['injected_leaf_result']==row['injected_leaf_result'] and r['mode']!=row['mode'])
        if row['leaf_calls']!=other['leaf_calls']:
            raise ValueError('selector flags selected different physical read calls')
    result=dict(model='E-PL9 / IM008 / 1330',displayed_body_version='1.1 (owner report)',
        downloaded_main_build='1101',main_bytes=len(image),main_sha256=sha(image),cases=rows,
        listing_sha256={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in listings},
        source_sha256=sha(Path(__file__).read_bytes()),
        flags_1_and_4_same_tested_leaf_calls=True,leaf_errors_overwritten_by_native_zero=True,
        ordinary_reader_reached_with_both_flags=True,read_maintenance_excluded=False,
        storage_and_setup_helpers_modeled=True,physical_transport_qualified=False,
        read_bytes_obtained=False,camera_accessed=False,install_ready=False)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows),masked_leaf_errors=sum(r['leaf_error_masked'] for r in rows),
        both_flags_same_calls=True,camera_accessed=False)))


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',type=Path,required=True)
    run(ap.parse_args().out)
