"""Native producer override matrix; operation IDs are deliberately not named as camera modes."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from epl9_art_header_probe import BASE,MAIN_SHA,STACK,OWNER,CONFIG,OUTPUT,FORMATTER,PRODUCER
from mn103_subset import Memory,Region,parse_listing
from mn103_calls import CallMachine
from mn103_tooling import reader_provenance
END=0x10000000
WINDOWS=((FORMATTER,0x60743845),(PRODUCER,0x607d27b0),
         (0x607cace8,0x607cad29),(0x607cb011,0x607cb027),(0x607cb0be,0x607cb0c6),
         (0x607d4e65,0x607d4ece),(0x607ca446,0x607ca469))

def probe(main,reader):
    image=main.read_bytes()
    if hashlib.sha256(image).hexdigest()!=MAIN_SHA:raise ValueError('wrong stock image')
    provenance=reader_provenance(reader);code={}
    for start,end in WINDOWS:
        listing=subprocess.check_output([str(reader),str(main),hex(BASE),hex(start-BASE),hex(end-BASE)],text=True)
        code.update(parse_listing(listing,image,BASE))
    def run(mode,operation=0x1003,submode=0,field272=0,config23680=0,writer=None,writer_input=0):
        m=CallMachine(code,Memory([Region(BASE,image),Region(STACK-8192,bytearray(16384),True),
            Region(OWNER,bytearray(512),True),Region(CONFIG,bytearray(24000),True),
            Region(OUTPUT,bytearray(8),True)]),dict(sp=STACK,a0=OWNER,a1=OUTPUT))
        for address,value,size in ((OWNER+152,CONFIG,4),(OWNER+72,operation,2),
              (OWNER+86,submode,2),(OWNER+272,field272,2),(CONFIG+22955,mode,1),
              (CONFIG+23688,2,1),(CONFIG+23680,config23680,1)):
            m.memory.write(address,value,size)
        if writer=='config22828':
            m.memory.write(CONFIG+22828,writer_input,2)
            m.memory.write(STACK+8,OWNER,4);m.memory.write(STACK+12,OWNER+72,4)
            m.r.update(sp=STACK,a3=CONFIG,d3=1)
            result=m.run(0x607cace8,[0x607cad29])
            if result['status']!='stop':raise ValueError(str(result))
            field272=3 if writer_input==2 else 1
        elif writer=='selector':
            m.memory.write(STACK+12,OWNER,4);m.r.update(sp=STACK,d2=writer_input)
            result=m.run(0x607cb011,[0x607cb021,0x607cb0c6])
            if result['status']!='stop':raise ValueError(str(result))
            field272=3 if writer_input==0 else 1
        if writer and m.memory.read(OWNER+272,2)!=field272:raise ValueError('writer differs')
        m.r.update(sp=STACK,a0=OWNER,a1=OUTPUT)
        result=m.run(m.enter(PRODUCER,END,0xf0,32),[END])
        if result['status']!='stop' or result['pc']!=END:raise ValueError(str(result))
        actual=bytes(m.memory.read(OUTPUT+i,1) for i in range(4))
        # Independently specified predicates; native jump-table classification
        # is also checked against this bounded stock domain.
        expected=bytes((1,2,mode,0))
        if operation in (0x2001,0x2006) and submode==2:expected=bytes((0,0,2,0))
        if operation==0x2001 and config23680==14:expected=bytes((2,0,12,0))
        if field272==3:
            if mode!=112:expected=bytes((0,0,2,0))
            elif config23680==14:expected=bytes((2,0,12,0))
        if actual!=expected:raise ValueError('unexpected override: '+actual.hex())
        return dict(raw_mode=mode,operation=hex(operation),submode=submode,owner272=field272,
            config23680=config23680,header=actual.hex(),writer=writer,writer_input=writer_input,
            classifier_executed=any(e.get('target')==0x607ca446 for e in m.events),
            helper_executed=any(e.get('target')==0x607d4e65 for e in m.events),
            native_instructions=len(m.trace))
    rows=[run(mode,field272=flag) for mode in range(100,125) for flag in (0,3)]
    rows += [run(mode,op,2,flag,14) for mode in (112,120) for op in (0x1003,0x2001,0x2006) for flag in (0,3)]
    rows += [run(120,writer=w,writer_input=v) for w,values in (('config22828',(0,2)),('selector',(0,1))) for v in values]
    table=struct.unpack_from('<25I',image,0x609095a8-BASE)
    classes={0x607ca45c:1,0x607ca460:2,0x607ca464:0}
    classification=[dict(raw_mode=100+i,value=classes[target]) for i,target in enumerate(table)]
    return dict(schema='epl9-art-override-probe-v2',reader_provenance=provenance,
        controls=rows,controls_passed=len(rows),stock_classifier=classification,
        physical_operation_mode_names_known=False,preview_capture_parity_proven=False,
        actual_video_tested=False,install_ready=False)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--main',type=Path,required=True);p.add_argument('--reader',type=Path,required=True)
    a=p.parse_args();print(json.dumps(probe(a.main,a.reader),indent=2))
