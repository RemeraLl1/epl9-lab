"""Native UI mode conversion through property setter to raw storage-write boundary.

Uses stock registries and converters. Stops before first raw mutation rather
than inventing storage side effects or notification success.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from epl9_embedded_art_inventory import BASE,MAIN_SHA
from mn103_subset import Memory,Region,parse_listing
from mn103_calls import CallMachine
from mn103_tooling import reader_provenance

SP=0x10012000
WINDOWS=((0x6069cc82,0x6069cccc),(0x6069ce1d,0x6069ce54),
 (0x6069d4eb,0x6069d55a),(0x6069d699,0x6069d6b8),(0x6069d798,0x6069d817),
 (0x606a5251,0x606a529a),(0x606a538c,0x606a53d6),(0x606a5580,0x606a55a3),
 (0x606a5932,0x606a59b3))


def probe(main,reader):
    image=main.read_bytes()
    if hashlib.sha256(image).hexdigest()!=MAIN_SHA:raise ValueError('wrong stock image')
    provenance=reader_provenance(reader);code={}
    for a,b in WINDOWS:
        s=subprocess.check_output([str(reader),str(main),hex(BASE),hex(a-BASE),hex(b-BASE)],text=True)
        code.update(parse_listing(s,image,BASE))
    rows=[]
    for ui_mode,expected in ((19,120),(18,119),(8,100)):
        m=CallMachine(code,Memory([Region(BASE,image),
            Region(SP-8192,bytearray(16384),True),
            Region(0x6261f3e8,bytearray(4096),True),
            Region(0x626213c4,bytearray(11000),True)]),dict(sp=SP))
        for start,stop in ((0x6069d798,0x6069d7ea),(0x606a5932,0x606a5986)):
            result=m.run(start,[stop])
            if result['status']!='stop':raise ValueError('registry builder failed')
        m.r.update(sp=SP,d0=0x6f,d1=ui_mode)
        before=len(m.trace)
        result=m.run(m.enter(0x6069cc82,0x10000000,0xe0,16),[0x6069ce3f])
        if (result['status']!='stop' or result['pc']!=0x6069ce3f or
                m.r['d0']!=0x6f or m.r['d1']!=expected or
                any(e['op']=='modeled_call' for e in m.events) or m.models):
            raise ValueError('unexpected setter conversion: '+str(result)+' '+str(m.r))
        rows.append(dict(ui_mode=ui_mode,raw_property='0x6f',raw_value=expected,
            native_instructions=len(m.trace)-before,stop_before_call='0x6069ce3f',raw_write_target='0x6069cbd9',
            modeled_calls=0))
    return dict(schema='epl9-art-base-mode-probe-v1',controls=rows,
        reader_provenance=provenance,stock_main_sha256=MAIN_SHA,
        native_setter_conversion_proven=True,raw_storage_write_executed=False,
        notification_lifecycle_executed=False,full_ui_capture_join_proven=False,
        install_ready=False)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--main',type=Path,required=True);p.add_argument('--reader',type=Path,required=True)
    a=p.parse_args();print(json.dumps(probe(a.main,a.reader),indent=2))
