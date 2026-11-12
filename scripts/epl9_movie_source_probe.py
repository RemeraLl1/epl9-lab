"""Read-only native source-selection audit; requires a private exact decoded main.
No OEM bytes, camera interface, or firmware writes. Synthetic states, not recording.
"""
import argparse, hashlib, json, subprocess
from pathlib import Path
from mn103_subset import Memory, Region, parse_listing
from mn103_calls import CallMachine
from mn103_tooling import default_reader, verify_reader
from epl9_video_audit import BASE, checked_listing


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--main',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args(); image=a.main.read_bytes()
    digest=hashlib.sha256(image).hexdigest()
    assert digest=='8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267'
    reader=default_reader();verify_reader(reader);code={}
    windows=[(0x6070665b,0x60706689),(0x607082d7,0x60708390),
             (0x6071e85c,0x6071e89a),(0x60743621,0x60743846)]
    for start,end in windows:
        listing=subprocess.check_output([str(reader),str(a.main),hex(BASE),hex(start-BASE),hex(end-BASE)],text=True)
        checked_listing(listing,image,start,end)
        code.update(parse_listing(listing,image,BASE))
    rows=[]
    for mode in range(5):
      for index in (0,1,2):
       sp=0x11001000;state=0x11003000;modeptr=0x11004000;wire=0x11005000
       mem=Memory([Region(BASE,image),Region(sp-1024,bytearray(2048),True),Region(state,bytearray(1024),True),Region(modeptr,bytearray(32),True),Region(wire,bytearray(64),True)])
       mem.write(sp+24,modeptr,4);mem.write(sp+32,index,4);mem.write(sp+12,state,4);mem.write(modeptr,mode,1)
       mem.write(state+291,120,1);mem.write(state+292,1,1)
       mem.write(state+297,120,1);mem.write(state+298,2,1)
       machine=CallMachine(code,mem,dict(sp=sp,d2=wire))
       result=machine.run(0x6070665b,[0x60706689]);assert result['status']=='stop'
       selected=machine.r['a1']-state
       assert selected==(296 if mode==3 and index==1 else 290)
       # Supply the selector outputs to the following bounded mapper fragment.
       # Skip external getter, explicitly model its output as zero.
       mem.write(sp+8,state,4);mem.write(sp+12,state+selected,4);mem.write(sp+4,wire+8,4)
       mem.write(sp+21,0,1)
       mapper=CallMachine(code,mem,dict(sp=sp,d3=0))
       result=mapper.run(0x607082d7,[0x60708390]);assert result['status']=='stop'
       header=mem.read(wire+8,4)
       assert header==(0x780201 if selected==296 else 0x780101)
       rows.append(dict(mode=mode,index=index,property_offset=selected,header=hex(header),selector_trace=[hex(pc) for pc in machine.trace],mapper_trace=[hex(pc) for pc in mapper.trace]))
    overrides=[]
    for label,fields in [('override274',{274:1}),('override817',{817:143}),('exception896',{274:1,804:1,896:4,172:1})]:
        for offset in (274,804,896,172,817):mem.write(state+offset,0,4 if offset in (896,172) else 1)
        for offset,value in fields.items():mem.write(state+offset,value,4 if offset in (896,172) else 1)
        mem.write(sp+8,state,4);mem.write(sp+12,state+290,4);mem.write(sp+4,wire+8,4)
        mem.write(wire+8,0,4);mem.write(sp+21,0,1)
        machine=CallMachine(code,mem,dict(sp=sp,d3=0));result=machine.run(0x607082d7,[0x60708390]);assert result['status']=='stop'
        header=mem.read(wire+8,4)
        expected={'override274':0x20000,'override817':0xc0002,'exception896':0x780101}[label]
        assert header==expected,(label,hex(header))
        overrides.append(dict(label=label,fields=fields,header=hex(header)))
    report=dict(schema='epl9-movie-source-selection-v1',override_cases=overrides,main_sha256=digest,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),cases=rows,
      mode_object_address='0xa2af2acc',state_selector=1,state_index_address='0xa2aed640',state_base='0xa2aed68c',state_stride=1020,
      producer_call_sites=['0x6070dde1','0x60724d23','0x60724d39'],
      external_getter_output_synthetic=True,synthetic_state=True,movie_start_binding_verified=False,encoder_executed=False,firmware_modified=False)
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(report,indent=2)+'\n')
    print('PASS',len(rows),'source-selection and normal mapper cases')
if __name__=='__main__':main()
