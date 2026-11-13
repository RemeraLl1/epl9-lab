"""Native promotion copy and conditional event-invocation gate, separately executed."""
import argparse,hashlib,json,subprocess
from pathlib import Path
from mn103_subset import Memory,Region,parse_listing
from mn103_calls import CallMachine
BASE=0x60400020
SHA='8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267'
def main():
 p=argparse.ArgumentParser();p.add_argument('--main',type=Path,required=True);p.add_argument('--reader',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();b=a.main.read_bytes();assert hashlib.sha256(b).hexdigest()==SHA;code={}
 for s,e in [(0x60720c86,0x60720c9b),(0x60720d37,0x60720d7b)]:
  t=subprocess.check_output([str(a.reader),str(a.main),hex(BASE),hex(s-BASE),hex(e-BASE)],text=True);parsed=parse_listing(t,b,BASE);assert min(parsed)==s and max(parsed)+len(parsed[max(parsed)][0])==e;code.update(parsed)
 sp=0x11001000;state=0x11002000;pair=0x11004000
 def mem():return Memory([Region(BASE,b),Region(0x11000000,bytearray(0x6000),True),Region(0x62419000,bytearray(0x2000),True)])
 m=mem()
 for x in range(108):m.write(pair+108+x,(x*17+3)&255,1)
 c=CallMachine(code,m,dict(sp=sp,a0=state,a1=pair));r=c.run(0x60720c86,[0x60720c9b]);assert r['status']=='stop'
 assert all(m.read(pair+x,1)==m.read(pair+108+x,1) for x in range(108))
 promotion=dict(bytes_equal=108,trace=[hex(x) for x in c.trace]);rows=[]
 for active in (0,1):
  for flag in (0,0x4000):
   for submode in (1,7):
    for latch in (0,1):
     m=mem();m.write(sp+4,state,4);m.write(sp+12,pair+108,4);m.write(state+640,active,1);m.write(state+16,flag,4);m.write(pair+108+18,submode,1);m.write(0x62419de4,latch,2)
     c=CallMachine(code,m,dict(sp=sp));r=c.run(0x60720d37,[0x60720d74,0x60720d7b,0x60720d99]);assert r['status']=='stop',r
     eligible=not active or bool(flag&0x4000)
     reset=eligible and (not active or submode==7)
     expected=eligible and (reset or latch==0)
     assert (r['pc']==0x60720d74)==expected
     assert m.read(0x62419de4,2)==(0 if reset else latch)
     rows.append(dict(active=active,flag=flag,submode=submode,latch=latch,event_dispatch_selected=expected,latch_after=m.read(0x62419de4,2),stop=hex(r['pc']),trace=[hex(x) for x in c.trace]))
 a.out.write_text(json.dumps(dict(schema='epl9-event-promotion-guards-v1',main_sha256=SHA,promotion=promotion,cases=rows,fragments_separately_executed=True,intervening_helpers_executed=False,full_cycle_executed=False,firmware_modified=False),indent=2)+'\n');print('PASS 1 promotion +',len(rows),'event invocation guards')
if __name__=='__main__':main()
