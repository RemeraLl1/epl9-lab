"""Offline exact-E-PL9 read-dispatch and maintenance-gate audit; no device IO."""
import argparse, hashlib, json, subprocess, sys
from pathlib import Path
BASE=0x60400020
SHA='8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267'
WINDOWS=[(0x6043ae0d,0x6043aeed),(0x604009bf,0x60400ae0),(0x604007b0,0x604008a7),(0x604a0f03,0x604a0f8b),(0x60439e72,0x60439f08),(0x60400abd,0x60400acd)]

def main():
 p=argparse.ArgumentParser();p.add_argument('--main',required=True);p.add_argument('--reader',required=True);p.add_argument('--engine-dir',required=True);p.add_argument('--out',required=True);a=p.parse_args()
 sys.path.insert(0,a.engine_dir)
 from mn103_subset import Memory,Region,parse_listing
 from mn103_calls import CallMachine
 data=Path(a.main).read_bytes()
 if hashlib.sha256(data).hexdigest()!=SHA:raise ValueError('wrong E-PL9 main')
 code={}
 for start,end in WINDOWS:
  listing=subprocess.check_output([str(Path(a.reader).resolve()),str(Path(a.main).resolve()),hex(BASE),hex(start-BASE),hex(end-BASE)],text=True)
  code.update(parse_listing(listing,data,BASE))
 anchors={
  0x6043aea7:('call','0x604a0f03'),
  0x60439e7a:('call','0x604014c6'),
  0x60400a4a:('mov','(0x98d01194)'),
  0x60400a50:('and','15'),
  0x60400a53:('mov','d2'),
  0x60400ac8:('call','0x604007b0'),
  0x60400813:('call','0x60400c60'),
  0x60400826:('call','0x60401066'),
  0x60400838:('call','0x60400e55'),
  0x6040086a:('call','0x60401066'),
  0x6040087f:('call','0x60400e55'),
  0x6040088e:('call','0x60400e55'),
  0x6040089d:('call','0x60400e55')}
 for address,(op,arg0) in anchors.items():
  assert code[address][1]==op and code[address][2][0]==arg0,hex(address)
 # Keep maintenance a real external stop, not an accidentally executed callee.
 code={k:v for k,v in code.items() if not 0x604007b0<=k<0x604008a7}
 class Diagnostic:
  name='diagnostic-only model'
  def validate(self,m,mask,frame):
   if (mask,frame) not in [(0xa0,40),(0xf0,36)]:raise ValueError('diagnostic ABI')
  def apply(self,m):return {'no_device_io':True}
 def cpu(registers):
  return CallMachine(code,Memory([Region(BASE,data),Region(0x70000000,bytearray(0x4000),True)]),dict(sp=0x70002000,**registers),models={0x6040227a:Diagnostic(),0x6040205d:Diagnostic()})
 modes=[]
 for mode in [0x101,0x102,0x103,0x104,0x105,0x106,0x107]:
  m=cpu(dict(d0=2048,d1=mode,a0=0x411fb000,a1=0xa0f1b000))
  m.enter(0x604a0f03,0x70003000,0xc0,12)
  stop=m.run(0x604a0f03,stops={0x70003000},limit=200)
  regs={k:hex(m.r[k]) for k in ['d0','d1','a0','a1']}
  if mode in [0x101,0x103]:
   assert stop['status']=='external_call' and stop['target']==0x604014c6
   assert m.r['d1']==2048 and m.r['a0']==0x411fb000 and m.r['a1']==0xa0f1b000
  else:
   assert stop['pc']==0x70003000
   assert m.r['d0']==(0x3109 if mode==0x107 else 0)
  modes.append(dict(mode=hex(mode),stop=stop,registers=regs,events=m.events))
 gates=[]
 for status in range(16):
  m=cpu(dict(a3=0x1234));m.memory.write(m.r['sp']+16,status,4)
  stop=m.run(0x60400abd,stops={0x60400acd},limit=20)
  maintenance=stop.get('target')==0x604007b0
  assert maintenance==(status>13)
  if maintenance:assert m.r['d0']==0x1234>>6
  gates.append(dict(status_nibble=status,maintenance=maintenance,stop=stop))
 report=dict(main_sha256=SHA,reader_sha256=hashlib.sha256(Path(a.reader).read_bytes()).hexdigest(),source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),static_anchor_count=len(anchors),mode_cases=modes,maintenance_gate_cases=gates,limits=['Synthetic register/stack fixtures, not full native boot or hardware','Maintenance callee not executed; it is an explicit external stop','Diagnostics explicitly modeled; no storage success injected','No camera, transport, read, write, or installation performed'],read_only_qualified=False,install_ready=False)
 Path(a.out).write_text(json.dumps(report,indent=2)+'\n')
 print('PASS: 7 read-dispatch controls; 16 native maintenance-gate controls')
if __name__=='__main__':main()
