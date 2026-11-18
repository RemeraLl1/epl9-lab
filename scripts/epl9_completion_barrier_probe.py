"""Bounded native command-ack and processing-cleanup replay; no hardware drain claim."""
import argparse, hashlib, json, subprocess
from pathlib import Path
from epl9_video_audit import BASE, MAIN_SHA, verified_input, checked_listing
from mn103_tooling import default_reader, verify_reader
from mn103_subset import Memory, Region, parse_listing
from mn103_calls import CallMachine

SP=0x1d010000
END=0x1e000000
OBJ=0x2a000000
OUT=OBJ+128
class Model:
 def __init__(self,name,fn):self.name=name;self.fn=fn
 def validate(self,m,mask,frame):pass
 def apply(self,m):return self.fn(m)

def probe(main,reader):
 image=verified_input(main,26214336,MAIN_SHA); rs=verify_reader(reader)
 windows={'ack':(0x60718e02,0x60718f40),'queue_wrapper':(0x6071771c,0x60717760),'cleanup':(0x6074ea4f,0x6074eac5),'outer':(0x60707429,0x60707450),'cleanup_wrapper':(0x6071c52f,0x6071c554)}
 code={};decoded={}
 for a,b in windows.values():
  listing=subprocess.check_output([str(reader.resolve()),str(main.resolve()),hex(BASE),hex(a-BASE),hex(b-BASE)],text=True)
  decoded.update(checked_listing(listing,image,a,b));code.update(parse_listing(listing,image,BASE))
 anchors={0x60718e14:'bne\t0x60718e19',0x60718e16:'jmp\t0x60718f0b',0x60718ed8:'cmp\td1,d0',0x60718ede:'beq\t0x60718ef9',0x6074eac1:'clr\td0'}
 for pc,expected in anchors.items():
  if decoded.get(pc)!=expected:raise ValueError(f'anchor {pc:x}: {decoded.get(pc)!r} vs {expected!r}')
 def fixture():
  return Memory([Region(BASE,image,False,'exact OEM main read only'),Region(SP-4096,bytearray(8192),True,'synthetic stack'),Region(OBJ,bytearray(512),True,'synthetic ack/object storage')])
 def execute(mem,regs,start,mask,frame,models):
  m=CallMachine(code,mem,dict(sp=SP,**regs),models=models)
  r=m.run(m.enter(start,END,mask,frame),stops=[END],limit=4000)
  assert r['status']=='stop',r
  return m
 def memset(m):
  addr=m.r['a0'];n=m.r['d1'];v=m.r['d0']&255
  for i in range(n):m.memory.write(addr+i,v,1)
  return dict(address=hex(addr),count=n)
 def noop(m):return {}
 cases=[]
 for label,allocated,kernel,opcode,status in [('ack5',True,0,5,0),('ack6',True,0,6,0),('wrong_opcode',True,0,6,0),('remote_error',True,0,5,17),('queue_timeout',True,0xfffffffe,5,0),('queue_error',True,1,5,0),('allocation_null',False,0,5,0)]:
  mem=fixture();mem.write(OUT,0xaaaaaaaa,4)
  expected=6 if label=='ack6' else 5
  def alloc(m):m.r['a0']=OBJ if allocated else 0;return dict(result=hex(m.r['a0']))
  def queue(m):
   # Actual 6071771c wrapper supplies a 16-byte kernel descriptor in a0.
   dest=m.memory.read(m.r['a0'],4)
   if kernel==0:
    m.memory.write(dest,status,2);m.memory.write(dest+4,opcode,4);m.memory.write(dest+8,0,4)
   m.r['d0']=kernel
   return dict(injected_kernel_result=kernel,reply_opcode=opcode,reply_status=status)
  models={0x6040240f:Model('declared allocator outcome',alloc),0x4700111e:Model('bounded memset',memset),0x604313e9:Model('injected kernel receive; NOT real queue',queue),0x606fac98:Model('diagnostic notification only',noop),0x6040244e:Model('declared free; no native allocator',noop),0x60440132:Model('diagnostic log only',noop)}
  m=execute(mem,dict(d0=expected,a0=OUT),0x60718e02,0xf0,84,models)
  actual=m.r['d0'];want=0 if label in ('ack5','ack6','allocation_null') else (0x9d10 if label=='queue_timeout' else 0x9d09 if label=='queue_error' else 0xff12)
  assert actual==want,(label,actual,want)
  if label=='allocation_null':
   assert not any(e.get('target')==0x604313e9 for e in m.events), 'null allocation must not receive'
  cases.append(dict(label=label,return_code=actual,output_status=mem.read(OUT,4),native_trace=[hex(x) for x in m.trace],modeled_events=m.events))
 cleanup=[]
 for kind,slots,error in [(2,[12,16,20,24],0),(3,[12,16,20,24],0),(0,[12,16,20,24],0),(2,[],0),(2,[12,16,20,24],0x1234),(3,[12,16,20,24],0x1234)]:
  mem=fixture();mem.write(OBJ+2,kind,2)
  for off in slots:mem.write(OBJ+off,0x2b000000+off,4)
  def unresolved(m):
   m.r['d0']=error
   return dict(injected_register_d0=error,semantic_meaning='unknown ABI; not asserted as real service error')
  models={x:Model('unresolved cleanup service boundary',unresolved) for x in (0x6076681c,0x60766988,0x6076692a,0x607668d4,0x604023b2)}
  m=execute(mem,dict(d0=OBJ),0x6074ea4f,0x20,8,models)
  calls=[x['target'] for x in m.events if x['op']=='modeled_call']
  expected=[0x6076681c,0x60766988,0x6076692a,0x607668d4,0x604023b2] if kind==2 and slots else [0x607668d4,0x604023b2] if kind==3 else [0x604023b2]
  assert calls==expected and m.r['d0']==0,(kind,calls)
  cleanup.append(dict(object_kind=kind,nonzero_offsets=slots,injected_service_d0=error,service_calls=[hex(x) for x in calls],return_code=m.r['d0'],native_trace=[hex(x) for x in m.trace]))
 return dict(schema='epl9-completion-barrier-v1',main_sha256=MAIN_SHA,reader_sha256=rs,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),windows=windows,ack_cases=cases,cleanup_cases=cleanup,limitations=['kernel receive outcomes injected; no live message ordering','cleanup service bodies unresolved; no DMA drain proven','synthetic caller/object state, no real stop/restart','null allocator case is a local code observation, not camera failure evidence'],firmware_modified=False,camera_accessed=False)
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--main',type=Path,required=True);p.add_argument('--reader',type=Path,default=default_reader());p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 if a.out.exists():raise ValueError('Use a fresh output')
 r=probe(a.main,a.reader);a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(r,indent=2)+'\n');print('Passed 7 ack + 6 cleanup controls')
if __name__=='__main__':main()
