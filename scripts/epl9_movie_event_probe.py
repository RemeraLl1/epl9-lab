"""Bounded E-PL9 pending-event -> ART mode initializer. Private stock input required.
Not full movie start, ring commit, encoder, camera frame or hardware evidence.
"""
import argparse, hashlib, json, subprocess
from pathlib import Path
from mn103_subset import Memory, Region, parse_listing
from mn103_calls import CallMachine
BASE=0x60400020
SHA='8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267'
WINDOWS=[(0x6071759d,0x60717642),(0x6071798b,0x6071799f),(0x607179b2,0x607179c6),(0x6070c9c2,0x6070ca0c)]
def checked_listing(listing,image,start,stop):
 cursor=start
 for line in listing.splitlines():
  address,raw,_=line.split('\t',2);address=int(address,16);raw=bytes.fromhex(raw);off=address-BASE
  if address!=cursor or address>=stop or not raw or off<0 or image[off:off+len(raw)]!=raw:raise ValueError('invalid listing')
  cursor+=len(raw)
 if cursor<stop:raise ValueError('incomplete listing')
def main():
 p=argparse.ArgumentParser();p.add_argument('--main',type=Path,required=True);p.add_argument('--reader',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 b=a.main.read_bytes();assert hashlib.sha256(b).hexdigest()==SHA;code={}
 for s,e in WINDOWS:
  t=subprocess.check_output([str(a.reader),str(a.main),hex(BASE),hex(s-BASE),hex(e-BASE)],text=True)
  checked_listing(t,b,s,e);code.update(parse_listing(t,b,BASE))
 rows=[]
 for event in (0x1600,0x1601,0x16ff,0x1500,0x1301,0x1400,0):
  for auxiliary in (0,1,2):
   for oldmode in (0,1,2,3,4,9):
    sp=0x11001000;obj=0x11003000;src=0x11004000
    m=Memory([Region(BASE,b),Region(0x11000000,bytearray(0x6000),True),Region(0x62419000,bytearray(0x2000),True),Region(0xa2af2000,bytearray(0x2000),True)])
    m.write(sp+4,obj,4);m.write(sp+12,src,4);m.write(0x62419d9c,event,4);m.write(0x62419da0,auxiliary,4);m.write(obj+19,oldmode,1)
    c=CallMachine(code,m,dict(sp=sp,a2=0));r=c.run(0x6071759d,[0x6070ca0c,0x6071765f,0x60717618,0x60717623,0x60717631])
    assert r['status']=='stop',r
    blocked=auxiliary==1 and oldmode in (1,2,3,4)
    expected=event>>8==22 and not blocked
    assert (0x60717606 in c.trace)==expected
    assert m.read(obj+19,1)==(3 if expected else oldmode)
    assert m.read(0x62419d9c,4)==0 and m.read(0x62419da0,4)==0
    if expected:
     assert m.read(obj+18,1)==1 and m.read(obj+23,1)==1 and m.read(obj+22,1)==0
    if blocked:assert m.read(obj+18,1)==7
    rows.append(dict(old_mode=oldmode,auxiliary_overrode=blocked,event=hex(event),auxiliary_event=auxiliary,initializer_selected=expected,mode=m.read(obj+19,1),submode=m.read(obj+18,1),stop_pc=hex(r['pc']),trace=[hex(x) for x in c.trace],native_calls=c.events))
 traces=[]
 for row in rows:
  trace=row.pop('trace');row.pop('native_calls')
  if trace not in traces:traces.append(trace)
  row['trace_id']=traces.index(trace)
 report=dict(traces=traces,schema='epl9-movie-event-mode-v1',main_sha256=SHA,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),cases=rows,synthetic_pending_events=True,external_calls_modeled=False,whole_dispatcher_executed=False,producer_to_ring_binding_verified=False,movie_start_binding_verified=False,encoder_executed=False,firmware_modified=False)
 a.out.write_text(json.dumps(report,indent=2)+'\n');print('PASS',len(rows),'native pending-event cases')
if __name__=='__main__':main()
