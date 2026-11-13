"""Actual config FIFO fragments, synthetic RAM; no camera or movie scheduling."""
import argparse,hashlib,json,subprocess
from pathlib import Path
from mn103_subset import Memory,Region,parse_listing
from mn103_calls import CallMachine
BASE=0x60400020
SHA='8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267'
def checked_listing(listing,image,start,stop):
 cursor=start
 for line in listing.splitlines():
  address,raw,_=line.split('\t',2);address=int(address,16);raw=bytes.fromhex(raw);off=address-BASE
  if address!=cursor or address>=stop or not raw or off<0 or image[off:off+len(raw)]!=raw:raise ValueError('invalid listing')
  cursor+=len(raw)
 if cursor<stop:raise ValueError('incomplete listing')
def main():
 p=argparse.ArgumentParser();p.add_argument('--main',type=Path,required=True);p.add_argument('--reader',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();b=a.main.read_bytes();assert hashlib.sha256(b).hexdigest()==SHA
 code={}
 for s,e in [(0x6070302e,0x607030be),(0x60700737,0x6070075a)]:
  t=subprocess.check_output([str(a.reader),str(a.main),hex(BASE),hex(s-BASE),hex(e-BASE)],text=True);checked_listing(t,b,s,e);code.update(parse_listing(t,b,BASE))
 rows=[];sp=0x11001000;src=0x11002000;dst=0x11003000;queue=0x62419a2c;wi=0x62419d8c;ri=wi+1;stop=0x12345678
 def mem():return Memory([Region(BASE,b),Region(0x11000000,bytearray(0x5000),True),Region(0x62419000,bytearray(0x2000),True)])
 for index in range(8):
  m=mem();m.write(wi,index,1);m.write(ri,index,1)
  for x in range(108):m.write(src+x,(x*13+index)&255,1)
  c=CallMachine(code,m,dict(sp=sp,a0=src));r=c.run(c.enter(0x6070302e,stop,0,4),[stop]);assert r['status']=='stop',r
  assert m.read(wi,1)==(index+1)&7
  for x in range(108):assert m.read(queue+index*108+x,1)==m.read(src+x,1)
  d=CallMachine(code,m,dict(sp=sp,a0=dst));q=d.run(d.enter(0x60700737,stop,0,4),[stop]);assert q['status']=='stop',q
  assert m.read(ri,1)==(index+1)&7
  for x in range(108):assert m.read(dst+x,1)==m.read(src+x,1)
  rows.append(dict(index=index,next_index=m.read(wi,1),bytes_equal=108,enqueue_trace=[hex(x) for x in c.trace],dequeue_trace=[hex(x) for x in d.trace]))
 # Error paths deliberately stop at external logging; do not fabricate logger.
 errors=[]
 for kind,w,r in [('full',0,1),('empty',0,0)]:
  m=mem();m.write(wi,w,1);m.write(ri,r,1)
  for x in range(108):m.write(src+x,0xA5,1);m.write(queue+x,0x5A,1)
  c=CallMachine(code,m,dict(sp=sp,a0=src if kind=='full' else dst));entry=0x6070302e if kind=='full' else 0x60700737;out=c.run(c.enter(entry,stop,0,4),[stop]);assert out['status']=='external_call' and out['target']==0x60440132,out
  assert m.read(wi,1)==w and m.read(ri,1)==r
  # Actual copy happens before full/empty test.
  assert m.read(queue if kind=='full' else dst,1)==(0xA5 if kind=='full' else 0x5A)
  errors.append(dict(kind=kind,result=out,index_unchanged=True,copy_before_check=True,trace=[hex(x) for x in c.trace]))
 a.out.write_text(json.dumps(dict(schema='epl9-native-config-fifo-v1',main_sha256=SHA,cases=rows,boundaries=errors,synthetic_ram=True,movie_scheduling_executed=False,firmware_modified=False),indent=2)+'\n');print('PASS 8 FIFO wrap transfers + 2 boundary stops')
if __name__=='__main__':main()
