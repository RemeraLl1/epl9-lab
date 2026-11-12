"""Read-only bounded gyro timer/epoch probe; no device I/O or firmware output.

Actual MN103 fragments run on synthetic RAM states. Critical sections, IRQs,
physical clocks, sample conversions and scheduler execution are not emulated.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from epl9_video_deep_audit import AUX_BASE, AUX_SHA
from epl9_video_audit import checked_listing
from mn103_subset import Machine, Memory, Region, parse_listing
from mn103_tooling import default_reader, verify_reader

WINDOWS = {
 'timer0_setup': (0x4001753b,0x40017583),
 'enqueue_tick': (0x4001cef8,0x4001cf2e),
 'irq_drain': (0x4001d361,0x4001d3ed),
 'reset_tick': (0x4001d53a,0x4001d544),
 'reset_pending': (0x4001d5b6,0x4001d5bd),
 'tick_counter_prefix': (0x4001e466,0x4001e48b),
 'phase_difference': (0x4000b7f5,0x4000b808),
}
ANCHORS = {
 0x40017545:'mov\t50000,d0',
 0x40017551:'mov\t1073837432,d0',
 0x4001757b:'call\t0x4001cf1f,[],12',
 0x4001cf26:'call\t0x4001cef8,[],4',
 0x4001cf0f:'movbu\t(0x000061f5),d0',
 0x4001cf13:'movbu\td0,(0x000061f5)',
 0x4001d38f:'call\t0x4001e466,[d2,d3,a2,a3],24',
 0x4001e472:'mov\t(0x0000620c),d0',
 0x4001e476:'mov\td0,(0x0000620c)',
 0x4001e481:'movhu\td0,(0x00006210)',
 0x4001d53b:'movhu\td0,(0x00006210)',
 0x4001d53e:'mov\td0,(0x0000620c)',
 0x4000b7fc:'mov\t50000,d0',
}

def probe(aux,reader):
 image=aux.read_bytes()
 if len(image)!=219104 or hashlib.sha256(image).hexdigest()!=AUX_SHA:
  raise ValueError('Exact E-PL9 build1101 stabilizer component required')
 reader_sha=verify_reader(reader); code={}; decoded={}
 for start,end in WINDOWS.values():
  listing=subprocess.check_output([str(reader.resolve()),str(aux.resolve()),hex(AUX_BASE),hex(start-AUX_BASE),hex(end-AUX_BASE)],text=True)
  decoded.update(checked_listing(listing,image,start,end,base=AUX_BASE)); code.update(parse_listing(listing,image,AUX_BASE))
 for pc,expected in ANCHORS.items():
  if decoded.get(pc)!=expected: raise ValueError(f'Instruction anchor mismatch at {pc:#x}')
 def machine(low=0,high=0,pending=0,flags=(0,1),regs=None):
  ram=bytearray(128);mem=Memory([Region(0x61e0,ram,True,'declared component RAM')])
  mem.write(0x620c,low,4);mem.write(0x6210,high,2);mem.write(0x61f5,pending,1)
  mem.write(0x6209,flags[0],1);mem.write(0x6208,flags[1],1)
  return Machine(code,mem,regs)
 def run(m,start,stops):
  result=m.run(start,stops=stops,limit=100)
  if result['status']!='stop': raise AssertionError(result)
  return result
 rows=[]
 for low,high in ((0,0),(0xfffffffe,3),(0xffffffff,3),(0xffffffff,0xffff)):
  m=machine(low,high);run(m,0x4001e472,[0x4001e484])
  after=(m.memory.read(0x6210,2)<<32)|m.memory.read(0x620c,4)
  assert after==(((high<<32)|low)+1)%(1<<48)
  rows.append(dict(before=(high<<32)|low,after=after,trace=[hex(x) for x in m.trace]))
 enqueue=[]
 for flags in ((0,0),(0,1),(1,0),(1,1)):
  m=machine(flags=flags);r=run(m,0x4001cef8,[0x4001cf0a,0x4001cf1c])
  enqueue.append(dict(flags_6209_6208=list(flags),admitted=r['pc']==0x4001cf0a,return_value=None if r['pc']==0x4001cf0a else m.r['d0'],trace=[hex(x) for x in m.trace]))
 assert [r['admitted'] for r in enqueue]==[False,True,False,False]
 pending=[]
 for n in (0,1,254,255):
  m=machine(pending=n);run(m,0x4001cf0f,[0x4001cf16]);after=m.memory.read(0x61f5,1)
  assert after==(n+1)%256
  pending.append(dict(before=n,after=after,overflow_loses_pending_count=n==255,trace=[hex(x) for x in m.trace]))
 drain=[]
 for n in (0,1,255):
  m=machine(pending=n);r=run(m,0x4001d385,[0x4001d38f,0x4001d3a0]);after=m.memory.read(0x61f5,1)
  assert after==max(n-1,0)
  drain.append(dict(before=n,after=after,will_call_tick_counter=r['pc']==0x4001d38f,trace=[hex(x) for x in m.trace]))
 phase=[]
 for old,new in ((100,120),(49990,10),(100,100)):
  m=machine(regs={'d0':old,'d1':new});run(m,0x4000b7f5,[0x4000b805]);delta=m.r['d0']
  assert delta==(new-old)%50000
  phase.append(dict(old=old,new=new,native_delta=delta,trace=[hex(x) for x in m.trace]))
 # Algebraic examples, NOT native execution: same phase read with a delayed
 # pending software tick cannot establish a long acquisition timestamp.
 snapshot_examples=[dict(label='no wrap',epoch=10,pending=0,phase=49999),
                    dict(label='wrap before deferred drain',epoch=10,pending=1,phase=0),
                    dict(label='after deferred drain',epoch=11,pending=0,phase=0)]
 for row in snapshot_examples: row['naive_epoch_times_50000_plus_phase']=row['epoch']*50000+row['phase']
 assert snapshot_examples[1]['naive_epoch_times_50000_plus_phase']<snapshot_examples[0]['naive_epoch_times_50000_plus_phase']
 return dict(schema='epl9-gyro-deferred-epoch-probe-v1',component_sha256=AUX_SHA,reader_sha256=reader_sha,
  source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),native_windows=len(WINDOWS),native_anchors=len(ANCHORS),
  tick_counter_rows=rows,enqueue_gates=enqueue,pending_increment_rows=pending,pending_drain_rows=drain,phase_difference_rows=phase,
  host_algebraic_snapshot_examples=snapshot_examples,
  limitations=['native fragments independently entered on synthetic RAM','critical sections and IRQ execution not modeled','counter units and hardware clock parent unverified','pending overflow case is synthetic, not measured camera loss','no gyro sample, exposure or cross-clock join','phase/comparator inclusive endpoint remains unqualified'],
  camera_accessed=False,firmware_changed=False,gyro_log_generated=False)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--aux',type=Path,required=True);p.add_argument('--reader',type=Path,default=default_reader());p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 if a.out.exists():raise ValueError('Choose new output')
 result=probe(a.aux,a.reader);a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'report':str(a.out),'native_cases':18,'component_sha256':AUX_SHA}))
if __name__=='__main__':main()
