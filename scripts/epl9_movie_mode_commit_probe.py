"""Exact E-PL9 mode commit to ART source-selection fragments. No camera writes.
Synthetic ring/flag inputs. Not a movie start, frame, encoder or pixel test.
"""
import argparse, hashlib, json, subprocess
from pathlib import Path
from mn103_subset import Memory, Region, parse_listing
from mn103_calls import CallMachine
from mn103_tooling import default_reader, verify_reader
from epl9_video_audit import BASE, checked_listing
SHA='8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267'
WINDOWS=[(0x60724502,0x6072450d),(0x607273d0,0x607273ec),(0x606ff32c,0x606ff394),(0x6070ded0,0x6070dfa7),(0x6070665b,0x60706689)]
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--main',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
 image=a.main.read_bytes();assert hashlib.sha256(image).hexdigest()==SHA
 reader=default_reader();verify_reader(reader);code={}
 for start,end in WINDOWS:
  listing=subprocess.check_output([str(reader),str(a.main),hex(BASE),hex(start-BASE),hex(end-BASE)],text=True)
  checked_listing(listing,image,start,end);code.update(parse_listing(listing,image,BASE))
 sp=0x11001000; flags=0x11003000; modeptr=0xa2af2acc; ring=0xa2aed68c
 def memory():return Memory([Region(BASE,image),Region(sp-2048,bytearray(4096),True),Region(flags,bytearray(64),True),Region(0xa2aed600,bytearray(0x7000),True)])
 gates=[]
 for bits in (0,1,2,3,0x800,0x801,0x802,0x803):
  m=memory();m.write(flags,bits,4);c=CallMachine(code,m,dict(sp=sp,a2=flags));r=c.run(0x60724502,[0x60724508,0x6072450d]);assert r['status']=='stop';called=r['pc']==0x60724508;assert called==bool(bits&1)
  gates.append(dict(flags=bits,commit_selected=called,trace=[hex(p) for p in c.trace]))
 rows=[]
 for s0,s1 in ((0,1),(1,0),(2,2)):
  for newmode in (0,3,4):
   for inhibit in (0,1,255):
    m=memory();m.write(0xa2aed63e,s0,2);m.write(0xa2aed640,s1,2)
    state=ring+s0*1020;source=ring+s1*1020;m.write(state+576,inhibit,1);m.write(state+912+19,newmode,1);m.write(modeptr,2,1)
    c=CallMachine(code,m,dict(sp=sp));r=c.run(0x607273d0,[0x607273ec]);assert r['status']=='stop',r
    got=m.read(modeptr,1);assert got==(newmode if inhibit==0 else 2)
    # Feed actual committed global mode into the previously qualified selector.
    m.write(sp+24,modeptr,4);m.write(sp+32,1,4);m.write(sp+12,source,4)
    select=CallMachine(code,m,dict(sp=sp));r2=select.run(0x6070665b,[0x60706689]);assert r2['status']=='stop'
    offset=select.r['a1']-source;assert offset==(296 if got==3 else 290)
    rows.append(dict(selector0_slot=s0,selector1_slot=s1,mode_from_state0=newmode,inhibit=inhibit,old_mode=2,committed_mode=got,selected_property_offset=offset,commit_trace=[hex(p) for p in c.trace],selector_trace=[hex(p) for p in select.trace]))
 report=dict(schema='epl9-movie-mode-commit-v1',main_sha256=SHA,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),native_windows=[[hex(s),hex(e)] for s,e in WINDOWS],gates=gates,cases=rows,synthetic_inputs=True,host_mode_commit=False,external_calls_modeled=False,full_caller_executed=False,movie_start_binding_verified=False,encoder_executed=False,firmware_modified=False)
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(report,indent=2)+'\n');print('PASS',len(gates),'bit gates and',len(rows),'native commits/selectors')
if __name__=='__main__':main()
