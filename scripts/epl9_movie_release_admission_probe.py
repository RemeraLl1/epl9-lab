"""Native movie resource lookup/release admission, NOT a drain simulation.
Private stock decoded main plus audited GNU reader required. No OEM output.
"""
import argparse, hashlib, json, subprocess
from pathlib import Path
from mn103_subset import Memory, Region, parse_listing
from mn103_calls import CallMachine
BASE=0x60400020
SHA='8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267'
WINDOWS=[(0x607c3f6a,0x607c3fc8),(0x607c4504,0x607c4547),(0x607c461c,0x607c4644),(0x607c441a,0x607c4463)]
def main():
 p=argparse.ArgumentParser();p.add_argument('--main',type=Path,required=True);p.add_argument('--reader',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 b=a.main.read_bytes();assert hashlib.sha256(b).hexdigest()==SHA;code={}
 for start,end in WINDOWS:
  listing=subprocess.check_output([str(a.reader.resolve()),str(a.main.resolve()),hex(BASE),hex(start-BASE),hex(end-BASE)],text=True)
  cursor=start
  for line in listing.splitlines():
   pc,raw,_=line.split('\t',2);pc=int(pc,16);raw=bytes.fromhex(raw)
   assert pc==cursor and b[pc-BASE:pc-BASE+len(raw)]==raw;cursor+=len(raw)
  assert cursor>=end
  code.update(parse_listing(listing,b,BASE))
 rows=[]
 for label,address,active,next_node,count,tag in [
 ('live address',0x21000000,1,True,2,10),
 ('same address different unrelated field',0x21000000,1,True,2,99),
 ('inactive address',0x21000000,0,True,2,10),
 ('unknown address',0x22000000,1,True,2,10),
 ('empty list',0x21000000,1,False,2,10),
 ('matching address status two',0x21000000,2,True,2,10)]:
  pool=0x11002000;node=0x11003000;sentinel=pool+20
  m=Memory([Region(BASE,b),Region(0x11000000,bytearray(0x6000),True)])
  m.write(pool+16,count,2);m.write(sentinel+4,node if next_node else 0,4)
  m.write(node+4,sentinel,4);m.write(node+8,sentinel,4);m.write(node+24,0x21000000,4)
  m.write(node+28,tag,2);m.write(node+30,1,2);m.write(node+32,active,2)
  c=CallMachine(code,m,dict(sp=0x11001000,a2=pool,d3=address,d2=0))
  # Entry is explicitly after lock acquisition; no lock/kernel behavior modeled.
  result=c.run(0x607c3f6a,[0x607c3fbf],limit=500)
  admitted=label in ('live address','same address different unrelated field','matching address status two')
  if admitted:
   assert result['status']=='external_call' and result['target']==0x4700111e,result
   assert m.read(node+32,2)==0
  else:
   assert result['status']=='stop',result
   assert c.r['d3']==3,(label,c.r['d3'])
  rows.append(dict(label=label,result=result,release_admitted=admitted,record_active_after=m.read(node+32,2),status_register=c.r['d3'],trace=[hex(pc) for pc in c.trace]))
 assert rows[0]['trace']==rows[1]['trace']
 a.out.write_text(json.dumps(dict(schema='epl9-native-release-admission-v1',cases=rows,main_sha256=SHA,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),entry_after_lock=True,lock_executed=False,kernel_call_executed=False,full_release_executed=False,upstream_quiescence_proven=False,camera_accessed=False,firmware_modified=False),indent=2)+'\n')
 print('PASS',len(rows),'native admission cases; stopped at genuine kernel boundary')
if __name__=='__main__':main()
