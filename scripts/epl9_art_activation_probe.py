"""Native activation dataflow slices, with explicit getter-return boundaries.

Not an end-to-end property mutation. No external functions are stubbed. Each
slice declares its input state and stops before the next getter/setter call.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from epl9_embedded_art_inventory import BASE,MAIN_SHA
from mn103_subset import Memory,Region,parse_listing
from mn103_calls import CallMachine
from mn103_tooling import reader_provenance

SP=0x10012000
OUT=0x20000000
WINDOWS=((0x606a1aeb,0x606a1af6),(0x606a3901,0x606a391b),
 (0x606a3d0b,0x606a3d31),(0x606a3ee3,0x606a3eea),
 (0x606a3fa3,0x606a3fb0),(0x6069e295,0x6069e2ad),(0x6069d798,0x6069d817))


def probe(main,reader):
    image=main.read_bytes()
    if hashlib.sha256(image).hexdigest()!=MAIN_SHA:raise ValueError('wrong stock image')
    provenance=reader_provenance(reader)
    code={}
    for a,b in WINDOWS:
        s=subprocess.check_output([str(reader),str(main),hex(BASE),hex(a-BASE),hex(b-BASE)],text=True)
        code.update(parse_listing(s,image,BASE))
    def machine(**regs):
        return CallMachine(code,Memory([Region(BASE,image),
            Region(SP-8192,bytearray(16384),True),Region(OUT,bytearray(128),True),Region(0x6261f3e8,bytearray(4096),True,'declared registry RAM')]),
            dict(sp=SP,**regs))
    def run(m,a,b,expect):
        before=len(m.trace)
        result=m.run(a,[b])
        if result['status']!='stop' or result['pc']!=b or m.events or m.models:
            raise ValueError('unexpected slice execution: '+str(result))
        if any(m.r[k]!=v for k,v in expect.items()):raise ValueError('register mismatch')
        return len(m.trace)-before
    registry=machine()
    registry_instructions=run(registry,0x6069d798,0x6069d7ea,{})
    registry.r['d0']=0x1d4
    run(registry,0x6069d7ed,0x6069d814,dict(a0=0x60816c88))
    callback=registry.memory.read(registry.r['a0']+24,4)
    if callback!=0x606a1ae1:raise ValueError('callback registration differs')
    rows=[]
    for variant in (1,2):
        counts=[]
        # Callback checks declared return value of current UI-mode getter.
        m=machine(d0=19);counts.append(run(m,0x606a1aeb,0x606a1af1,dict(d0=0,d1=19)))
        # Real jump table selects the Watercolor branch, then its property getter.
        m=machine(d0=0,d2=19,a3=0)
        counts.append(run(m,0x606a3901,0x606a3d12,dict(a0=0x1d4,d0=0,d1=1)))
        # Declared getter return, not an emulated storage read.
        m=machine(d0=variant,a3=0)
        stop=0x606a3d24 if variant==2 else 0x606a3d2e
        counts.append(run(m,0x606a3d17,stop,dict(a0=0x371 if variant==2 else 0x1d3)))
        if m.memory.read(SP+4,4)!=variant:raise ValueError('variant not retained')
        m.memory.write(SP+64,OUT,4)
        counts.append(run(m,0x606a3ee3,0x606a3eea,dict(d0=variant,a0=OUT)))
        if m.memory.read(OUT+32,4)!=variant:raise ValueError('output variant differs')
        # Caller output begins at its SP+4: output+32 is caller SP+36.
        m=machine(d2=0);m.memory.write(SP+36,variant,4)
        counts.append(run(m,0x606a3fa3,0x606a3fab,dict(a0=0x16a,a1=variant,d0=0,d1=2)))
        # Execute setter dispatcher to its native indirect-call boundary.
        counts.append(run(m,0x6069e295,0x6069e2ab,dict(d0=0x16a,d1=variant,a2=0x6069cc7d)))
        rows.append(dict(variant=variant,source_property='0x1d4',destination_property='0x16a',
            native_setter_target='0x6069cc7d',slice_instructions=counts,
            getter_return_supplied=True,storage_read_executed=False,storage_write_executed=False))
    m=machine(d0=18)
    run(m,0x606a1aeb,0x606a1af6,dict(d1=18))
    return dict(schema='epl9-art-activation-slices-v1',controls=rows,
        non_watercolor_callback_skips_activation=True,reader_provenance=provenance,
        registry_builder_executed=True,registry_build_instructions=registry_instructions,
        watercolor_descriptor='0x60816c88',watercolor_callback=hex(callback),
        runtime_startup_invocation_proven=False,ui_base_to_processing_mode_proven=False,
        end_to_end_mutation_proven=False,install_ready=False)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--main',type=Path,required=True);p.add_argument('--reader',type=Path,required=True)
    a=p.parse_args();print(json.dumps(probe(a.main,a.reader),indent=2))
