"""Read-only native source-return identity probe; synthetic lifecycle bridge only.

No camera, MMIO, firmware patches or actual stop/restart scheduling.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from epl9_video_audit import BASE, MAIN_SHA, verified_input, checked_listing
from epl9_video_geometry_audit import WINDOWS, probe_repacked_fhd_pool
from mn103_subset import Machine, Memory, Region, parse_listing
from mn103_tooling import default_reader, verify_reader

SELECT = ['resource_object_allocate','resource_slot_acquire','resource_slot_query_entry',
          'resource_free_count','source_pool_slot_state','source_pool_virtual_address',
          'resource_object_release','resource_slot_release']

def probe(main,reader):
 image=verified_input(main,26214336,MAIN_SHA);reader_sha=verify_reader(reader)
 windows={k:WINDOWS[k] for k in SELECT};windows['full_source_return']=(0x607116c6,0x60711724);windows['source_mode_init']=(0x60710c74,0x60710c94)
 code={};decoded={}
 for start,end in windows.values():
  listing=subprocess.check_output([str(reader.resolve()),str(main.resolve()),hex(BASE),hex(start-BASE),hex(end-BASE)],text=True)
  decoded.update(checked_listing(listing,image,start,end));code.update(parse_listing(listing,image,BASE))
 anchors={0x607116c8:'mov\t(0xa2af3c80),d1',0x607116e3:'mov\t(4,a1),d3',
          0x607116e6:'cmp\td0,d3',0x60711703:'mov\td0,(8,a1)',0x60711715:'add\t-1,d0'}
 for pc,text in anchors.items():
  if decoded.get(pc)!=text:raise ValueError(f'anchor mismatch {pc:#x}')
 init_rows=[]
 for value in (0,1,0x10001):
  mem=Memory([Region(0xa2af3c60,bytearray(36),True,'synthetic source mode')])
  m=Machine(code,mem,dict(d1=value));r=m.run(0x60710c74,stops=[0x60710c94])
  assert r['status']=='stop' and mem.read(0xa2af3c80,4)==(value&0xffff)
  init_rows.append(dict(input_d1=value,stored_mode=mem.read(0xa2af3c80,4)))
 pool=probe_repacked_fhd_pool(code)
 address=int(pool['native_addresses'][0],16)
 # Allocation/release/reallocate above is native. The transfer into source
 # records below is an explicit HOST bridge, not the firmware producer path.
 def returned(label,callback=address,gate=0,refs=1,selected=8,duplicate=False):
  table=0xa2af3ac8
  mem=Memory([Region(table,bytearray(108),True,'synthetic source records'),
              Region(0xa2af3c64,bytearray(32),True,'synthetic refs, selection, return gate')])
  for i in range(9):
   mem.write(table+12*i+4,address+0x1000000+i*0x1000,4)
   mem.write(table+12*i+8,2,4);mem.write(0xa2af3c64+i,refs,1)
  mem.write(table+4,address,4)
  if duplicate:mem.write(table+12+4,address,4)
  mem.write(0xa2af3c6d,selected,1);mem.write(0xa2af3c80,gate,4)
  m=Machine(code,mem,dict(d0=callback,d1=0xdeadbeef))
  result=m.run(0x607116c6,stops=[0x60711724],limit=500)
  if result['status']!='stop':raise AssertionError(result)
  return dict(label=label,callback_address=hex(callback),return_gate=gate,initial_refs=refs,selected=selected,
   final_refs=[mem.read(0xa2af3c64+i,1) for i in range(9)],
   final_flags=[mem.read(table+12*i+8,4) for i in range(9)],trace=[hex(pc) for pc in m.trace])
 rows=[returned('current generation callback'),returned('hypothetical old generation callback after reuse'),
       returned('global gate nonzero',gate=1),returned('unmatched address',callback=address-4096),
       returned('two references',refs=2),returned('retained selected slot',selected=0),
       returned('two records same address',duplicate=True)]
 assert rows[0]['final_refs'][0]==rows[1]['final_refs'][0]==0
 assert rows[0]['final_flags'][0]==rows[1]['final_flags'][0]==1
 assert rows[0]['trace']==rows[1]['trace']
 for row in rows[2:4]:assert row['final_refs']==[1]*9 and row['final_flags']==[2]*9
 assert rows[4]['final_refs'][0]==1 and rows[4]['final_flags'][0]==2
 assert rows[5]['final_refs'][0]==0 and rows[5]['final_flags'][0]==2
 assert rows[6]['final_refs'][:2]==[0,1]
 return dict(schema='epl9-source-reuse-probe-v1',main_sha256=MAIN_SHA,reader_sha256=reader_sha,
  source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),windows=len(windows),anchors=len(anchors),
  native_repacked_pool=pool,source_mode_initialization=init_rows,source_return_cases=rows,
  distinction='native leaves linked through explicitly synthetic host record setup, not integrated firmware lifecycle',
  result='This callback fragment matches source address, not a generation token; a hypothetical stale same-address return is locally indistinguishable.',
  limitations=['upstream delivery/queue admission not modeled','global condition initialized from caller argument; full writer census/lifecycle not proven',
   'hardware and DMA completion unverified','late callback on camera not observed','six-slot movie sufficiency unverified'],
  camera_accessed=False,firmware_modified=False)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--main',type=Path,required=True);p.add_argument('--reader',type=Path,default=default_reader());p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 if a.out.exists():raise ValueError('Choose new output')
 result=probe(a.main,a.reader);a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'report':str(a.out),'return_cases':7}))
if __name__=='__main__':main()
