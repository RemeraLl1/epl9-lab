"""Audit native logical-component read selection/error propagation offline.

The actual NAND read is trapped; no USB, shell, filesystem or camera client is
provided. A zero return from a stub is deliberately distinguished from a read.
"""
import argparse
import json
import struct
from pathlib import Path
from epl9_workspace_bridge import ROOT, MAIN, MAIN_SHA, BASE, sha
from epl9_component_readback import ADDRESSES, SIZE
from epl9_recovery_audit import Boundary
from mn103_subset import Memory, Region, parse_listing, Machine
from mn103_calls import CallMachine

SP, BUFFER, END = 0x18008000, 0x19000000, 0x1a000000


class ReadBoundary(Boundary):
    def apply(self,m):
        self.calls.append(dict(source=hex(m.r['a0']),destination=hex(m.r['a1']),
            bytes=m.r['d1'],d0=m.r['d0'],
            extra0=m.memory.read(m.r['sp']+36,4),
            extra1=m.memory.read(m.r['sp']+40,4),
            injected_result=hex(self.backend_result),storage_executed=False))
        m.r['d0']=self.backend_result
        return self.calls[-1]


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--listings',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args()
    if args.out.exists() or not args.out.resolve().is_relative_to((ROOT/'local').resolve()):
        raise ValueError('new ignored output report required')
    image=MAIN.read_bytes()
    if sha(image)!=MAIN_SHA:raise ValueError('stock identity mismatch')
    code={};hashes={}
    for name in ('logical-read-selector.tsv','read-wrapper.tsv','fmem-parser.tsv'):
        path=args.listings/name
        code.update(parse_listing(path.read_text(encoding='utf-8-sig'),image,BASE))
        hashes[name]=sha(path.read_bytes())
    rows=[]
    for kind,source in ADDRESSES.items():
        for mode in (0x101,0x103):
            for length in (16384,SIZE):
                for status in (0,0x3102,0x310d):
                    read=ReadBoundary('unexecuted-logical-storage-read',[(0xf0,32)],status)
                    read.calls=[]
                    mem=Memory([Region(BASE,image),Region(SP-32768,bytearray(65536),True)])
                    m=CallMachine(code,mem,dict(sp=SP,a0=source,a1=BUFFER,d0=length,d1=mode),
                        models={0x604014c6:read,
                            0x6040227a:Boundary('diagnostic-only',[(0xa0,40)])})
                    result=m.run(m.enter(0x604a0f03,END,0xc0,12),[END])
                    expected=0 if status==0 else 0x310d if status==0x310d else 0x3105
                    if result.get('pc')!=END or m.r['sp']!=SP or m.r['d0']!=expected or len(read.calls)!=1:
                        raise ValueError('native logical read status/stack differs')
                    call=read.calls[0]
                    if (int(call['source'],0)!=source or int(call['destination'],0)!=BUFFER or
                        call['bytes']!=length or call['d0']!=0 or call['extra0']!=0 or
                        call['extra1']!={0x101:1,0x103:4}[mode]):
                        raise ValueError('native read arguments differ')
                    rows.append(dict(component=kind,mode=hex(mode),return_value=hex(m.r['d0']),**call))
    stubs=[]
    for mode in (0x102,0x104,0x105,0x106):
        mem=Memory([Region(BASE,image),Region(SP-32768,bytearray(65536),True)])
        m=CallMachine(code,mem,dict(sp=SP,a0=0x100,a1=BUFFER,d0=16384,d1=mode),
            models={0x6040227a:Boundary('diagnostic-only',[(0xa0,40)])})
        r=m.run(m.enter(0x604a0f03,END,0xc0,12),[END])
        if r.get('pc')!=END or m.r['d0']!=0 or any(e.get('target')==0x604014c6 for e in m.events):
            raise ValueError('expected non-reading success stub differs')
        stubs.append(dict(mode=hex(mode),return_value=0,read_requested=False))
    cli=[]
    # Original CLI obtains destination from a global, with no allocation in
    # this read branch. Zero/stale values must not be treated as owned buffers.
    for destination in (0,BUFFER,BUFFER+2048):
        mem=Memory([Region(BASE,image),Region(SP-32768,bytearray(65536),True),
                    Region(0x61f01124,struct.pack('<I',destination))])
        for at,value in ((56,ADDRESSES['main']),(60,16384),(64,0x101)):
            mem.write(SP+at,value,4)
        m=Machine(code,mem,dict(sp=SP))
        r=m.run(0x6043b3b9,[0x6043b3c5])
        if r.get('pc')!=0x6043b3c5 or m.r['a0']!=destination:
            raise ValueError('fmem read destination propagation differs')
        cli.append(dict(destination=hex(destination),forwarded_without_buffer_validation=True,
            called_storage=False))
    plan=[dict(component=kind,logical_start=hex(start),bytes=SIZE,
        logical_end_exclusive=hex(start+SIZE),chunk_bytes=16384,chunks_per_pass=SIZE//16384,
        passes=2,address_domain='logical storage, not CPU load address or raw NAND offset')
        for kind,start in ADDRESSES.items()]
    report=dict(main_sha256=sha(image),listing_sha256=hashes,
        source_sha256=sha(Path(__file__).read_bytes()),native_read_boundary_cases=rows,
        success_without_read_controls=stubs,cli_destination_controls=cli,
        proposed_acquisition_extent=plan,
        working_selector_front_identified=True,physical_transport_qualified=False,
        diagnostic_session_setup_qualified=False,owned_cli_buffer_qualified=False,
        read_maintenance_program_erase_excluded=False,
        installed_component_bytes_obtained=False,physical_restore_verified=False)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(read_boundary_cases=len(rows),non_reading_success_modes=len(stubs),
        cli_controls=len(cli),physical_transport_qualified=False)))


if __name__=='__main__':
    main()
