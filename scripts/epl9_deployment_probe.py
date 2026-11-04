"""Measure offline stack/request accesses and enumerate unqualified placement candidates."""
import argparse
import json
import re
import struct
from pathlib import Path
from epl9_film_late_probe import prepare_probe
from epl9_job_probe import experiment, JOB, SP
from epl9_workspace_bridge import BASE, ROOT, sha

# Exact 1101 section endpoints resolved by native 604229df / rows 60405f94.
# These cover the post-entry section loader, not an identified pre-main map.
SECTIONS=((0x604b7800,0x60601000),(0x6066f800,0x6092c800),
          (0x60942200,0x6096d000),(0x60973a00,0x60abc000),
          (0x60acc800,0x60efe000),(0x60f1b000,0x61630000),
          (0x6164b000,0x61738000),(0x61741000,0x61741000),
          (0x61745000,0x617b9000))


def placement_coverage(start,size):
    covered=[i+1 for i,(a,b) in enumerate(SECTIONS) if a<=start and start+size<=b]
    return dict(stock_section_covers_module=covered,
                pre_main_mapping_unknown=start<SECTIONS[0][0],
                post_entry_loader_covers_module=bool(covered))


class Registers(dict):
    def __init__(self,values):
        super().__init__(values)
        self.minimum_sp=values['sp']
    def __setitem__(self,key,value):
        super().__setitem__(key,value)
        if key=='sp': self.minimum_sp=min(self.minimum_sp,value)
    def update(self,*args,**kwargs):
        for k,v in dict(*args,**kwargs).items(): self[k]=v


class Observe:
    def __init__(self,base=0x68000000):self.module_base=base
    def __call__(self,m):
        self.m=m
        self.reads=[]
        self.writes=[]
        self.request_addresses=set()
        self.locks_at_writes=set()
        m.r=Registers(m.r)
        read,write=m.read,m.write
        def observed_read(operand,size=4):
            address=m.address(operand) if operand.startswith('(') else -1
            if JOB+10440+1568 <= address < JOB+10440+1576:
                self.reads.append((m.trace[-1] if m.trace else 0,address-(JOB+10440),size))
            return read(operand,size)
        def observed_write(operand,value,size=4):
            address=m.address(operand) if operand.startswith('(') else -1
            if m.trace and self.module_base<=m.trace[-1]<self.module_base+0x1000 and address-m.r['a2'] in (8,1512,1524,1795):
                self.request_addresses.add(m.r['a2'])
                self.writes.append((m.trace[-1],address-m.r['a2'],size))
                self.locks_at_writes.add(tuple(bool(getattr(m.models.get(k),'held',False)) for k in (0x607a17b7,0x607a1841)))
            return write(operand,value,size)
        m.read,m.write=observed_read,observed_write
    def result(self):
        return dict(observed_stack_depth=SP-self.m.r.minimum_sp,minimum_sp=hex(self.m.r.minimum_sp),
            actual_hook_request_addresses=[hex(v) for v in sorted(self.request_addresses)],
            wb_reads=[dict(pc=hex(p),offset=o,size=s) for p,o,s in sorted(set(self.reads))],
            isp_lock_states_at_hook_writes=sorted(self.locks_at_writes),
            hook_request_writes=[dict(pc=hex(p),offset=o,size=s) for p,o,s in sorted(set(self.writes))])


def padding_candidates(image):
    result=[]
    for match in re.finditer(b'\xff{16384,}',image):
        aligned=(BASE+match.start()+255)&~255
        if aligned+0x3c00>BASE+match.end():continue
        needle=struct.pack('<I',aligned)
        literals=[hex(BASE+m.start()) for m in re.finditer(re.escape(needle),image)]
        result.append(dict(start=hex(aligned),padding_end=hex(BASE+match.end()),
            available=BASE+match.end()-aligned,exact_start_literals=literals,
            **placement_coverage(aligned,0x3c00),
            executable_mapping_verified=False,computed_references_excluded=False,
            loader_preservation_verified=False,approved=False))
    return sorted(result,key=lambda r:r['available'],reverse=True)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--color-controls',type=Path)
    ap.add_argument('--wb-controls',type=Path)
    ap.add_argument('--base',type=lambda s:int(s,0),default=0x68000000)
    args=ap.parse_args()
    document=json.loads(args.color_controls.read_text()) if args.color_controls else None
    wb=json.loads(args.wb_controls.read_text()) if args.wb_controls else None
    image,patched,original_code,code,module,manifest=prepare_probe(args.out,color_document=document,wb_document=wb,base=args.base)
    cases=[]
    for key in (0x01010078,0x01020078):
        for kind in (0x200,0x100,0x40):
            options=dict(provide_slot=True,input_format=0x100) if kind==0x40 else {}
            if wb is not None: options['gain_fixture']=(2048,1536,1024,1056)
            observed=[]
            for mode in ('historical_color','native_film'):
                meter=Observe(module['base'])
                report=experiment(patched if mode=='native_film' else image,
                    code if mode=='native_film' else original_code,key,kind,0,
                    native_module=module if mode=='native_film' else None,machine_observer=meter,**options)
                if mode=='native_film' and not meter.writes:
                    raise ValueError('observer did not see native hook writes; audit invalid')
                observed.append(dict(mode=mode,**meter.result(),stop=report['executor'].get('error')))
            cases.append(dict(key=hex(key),kind=hex(kind),runs=observed,
                measured_additional_stack=observed[1]['observed_stack_depth']-observed[0]['observed_stack_depth']))
    report=dict(main_sha256=sha(image),module=manifest,stack_cases=cases,
        padding_candidates=padding_candidates(image),
        synchronization=dict(job_submission_request_offset=10440,hook_request_identity_traced=True,
            temporary_request_writes=True,shared_owner_readonly=True,
            same_request_concurrent_access_excluded=False,lock_coverage_verified=False),
        camera_stack_size_and_headroom_verified=False,install_ready=False)
    (args.out/'deployment-audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(cases=len(cases),stack=[(r['key'],r['kind'],r['measured_additional_stack'],r['runs'][1]['observed_stack_depth']) for r in cases],
        wb_reads=cases[0]['runs'][1]['wb_reads'],padding=report['padding_candidates'][:2]),indent=2))


if __name__=='__main__':main()
