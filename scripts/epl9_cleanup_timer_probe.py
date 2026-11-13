"""64 bounded native cleanup/timer-dispatch controls; no camera or firmware writes."""
import argparse,sys,json,subprocess,hashlib
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--main',type=Path,required=True);p.add_argument('--aux',type=Path,required=True);p.add_argument('--out',type=Path,required=True);args=p.parse_args()
sys.path.insert(0,str(args.repo/'scripts'))
class Model:
 def __init__(self,name,fn):self.name=name;self.fn=fn
 def validate(self,m,mask,frame):pass
 def apply(self,m):return self.fn(m)
from epl9_video_deep_audit import AUX_BASE,AUX_SHA
from epl9_video_audit import BASE,MAIN_SHA,verified_input,checked_listing
from mn103_subset import Memory,Region,parse_listing
from mn103_calls import CallMachine
from mn103_tooling import verify_reader
reader=args.repo/'local/mn103-tooling/mn103-reader'; reader_sha=verify_reader(reader)
image=verified_input(args.main,26214336,MAIN_SHA)
aux=verified_input(args.aux,219104,AUX_SHA)
def decode(path,image,base,windows):
 code={}
 for a,b in windows:
  s=subprocess.check_output([str(reader.resolve()),str(path.resolve()),hex(base),hex(a-base),hex(b-base)],text=True)
  checked_listing(s,image,a,b,base=base);code.update(parse_listing(s,image,base))
 return code
code=decode(args.main,image,BASE,[(0x6076681c,0x607669c4),(0x6074ad9f,0x6074adbe)])
OBJ=0x2a000000;SP=0x1d010000;END=0x1e000000
rows=[]
for entry,countoff,flagoff,parts in [(0x6076681c,96,98,[8]),(0x607668d4,400,402,[8,92,176,260]),(0x6076692a,176,178,[8,92]),(0x60766988,180,182,[8,92])]:
 for refs in [0,1,2,65535]:
  for present in [False,True]:
   mem=Memory([Region(BASE,image,False,'OEM'),Region(SP-4096,bytearray(8192),True,'stack'),Region(OBJ,bytearray(1024),True,'object')]);mem.write(OBJ+countoff,refs,2);mem.write(OBJ+flagoff,1,1)
   for off in parts:mem.write(OBJ+off+64,0x12345678 if present else 0,4)
   events=[]
   def noop(m):return {}
   def release(m):events.append({'command':m.r['d0'],'part':m.r['a1']-OBJ});m.r['d0']=0;return {}
   def zero(m):
    for i in range(m.r['d1']):m.memory.write(m.r['a0']+i,m.r['d0']&255,1)
    return {}
   models={0x60766a77:Model('unresolved exclusion acquire',noop),0x60766a93:Model('unresolved exclusion release',noop),0x6073eab3:Model('unresolved command dispatcher',release),0x4700111e:Model('memset',zero)}
   m=CallMachine(code,mem,dict(sp=SP,a0=0x2b000000,a1=OBJ),models=models);res=m.run(m.enter(entry,END,0x30,12),stops=[END],limit=1000)
   assert res['status']=='stop',res
   assert len(events)==(len(parts) if present and refs<=1 else 0)
   assert mem.read(OBJ+flagoff,1)==(0 if refs<=1 else 1)
   assert mem.read(OBJ+countoff,2)==(refs-1 if refs>1 else refs)
   rows.append(dict(entry=hex(entry),refs=refs,present=present,release_commands=events,trace=[hex(x) for x in m.trace]))
code=decode(args.aux,aux,AUX_BASE,[(0x40009fbc,0x40009ff5)])
timers=[]
for status in range(16):
 for cb1 in [0,0x40017578]:
  events=[]
  mem=Memory([Region(0x800,bytearray(256),True,'callback table'),Region(SP-4096,bytearray(8192),True,'stack')]);mem.write(0x828,cb1,4);mem.write(0x82c,0x2b000000,4);mem.write(0x830,0x1234,4)
  def first(m):events.append('epoch_callback');assert m.r['a0']==0x1234;return {}
  def second(m):events.append('alternate_callback');return {}
  m=CallMachine(code,mem,dict(sp=SP,d0=0,d1=status),models={0x40017578:Model('epoch callback boundary',first),0x2b000000:Model('synthetic alternate callback',second)})
  out=m.run(m.enter(0x40009fbc,END,0xc0,12),stops=[END],limit=100);assert out['status']=='stop',out
  want=(['epoch_callback'] if status&4 and cb1 else [])+(['alternate_callback'] if status&2 else []);assert events==want
  timers.append(dict(status=status,primary_enabled=bool(cb1),callbacks=events,trace=[hex(x) for x in m.trace]))
code=decode(args.aux,aux,AUX_BASE,[(0x4000a90f,0x4000a951),(0x40009db7,0x40009dc4),(0x40009fbc,0x40009ff5)])
irq=[]
for status in range(16):
 mem=Memory([Region(0,bytearray(0x9000),True,'synthetic RAM and controller registers'),Region(SP-4096,bytearray(8192),True,'stack')]);mem.write(0x8a00,34*4,2);initial=0xff00|status|(status<<4);mem.write(0x8988,initial,2);mem.write(0xc78,0x40009db7,4);mem.write(0x828,0x40017578,4);mem.write(0x82c,0,4)
 seen=[]
 def cb(m):seen.append(mem.read(0x8988,2));return {}
 m=CallMachine(code,mem,dict(sp=SP),models={0x40017578:Model('epoch callback boundary',cb)})
 a=m.run(m.enter(0x4000a90f,END,0x80,8),stops=[0x4000a938],limit=100);assert a['status']=='stop'
 # Explicit host bridge skips PSW instruction; does NOT model interrupt masks.
 b=m.run(0x4000a93c,stops=[END],limit=100);assert b['status']=='stop',b
 want=initial&~(status<<4);assert mem.read(0x8988,2)==want;assert seen==([want] if status&4 else [])
 irq.append(dict(status=status,register_after=want,at_callback=seen,skipped_psw='0x4000a938',trace=[hex(x) for x in m.trace]))
result=dict(main_sha256=MAIN_SHA,aux_sha256=AUX_SHA,reader_sha256=reader_sha,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),cleanup=rows,timer_dispatch=timers,irq_timer_link=irq,camera_accessed=False,firmware_modified=False,limitations=['synthetic RAM states','cleanup lock and dispatcher explicitly modeled','timer callbacks modeled','no IRQ scheduling or hardware clock','no drain or atomic timestamp qualification'])
if args.out.exists():raise ValueError('use fresh output')
args.out.write_text(json.dumps(result,indent=2)+'\n');print('Passed 32 cleanup + 32 timer dispatch + 16 IRQ linkage controls')
