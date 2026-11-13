"""Bounded native deferred-drain snapshots; no hardware or firmware writes.

This is NOT an atomic timestamp implementation. Interrupt masking and hardware
phase progression are deliberately not emulated. Observation points are injected.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from epl9_video_deep_audit import AUX_BASE, AUX_SHA
from epl9_video_audit import checked_listing
from mn103_subset import Machine, Memory, Region, parse_listing
from mn103_tooling import default_reader, verify_reader

WINDOWS = [(0x4001d385,0x4001d394),(0x4001e466,0x4001e48b),
           (0x4001d3f6,0x4001d437),(0x4000b797,0x4000b7a7)]
ANCHORS = {0x4001d38c:'movbu\td0,(0x000061f5)',
           0x4001d38f:'call\t0x4001e466,[d2,d3,a2,a3],24',
           0x4001e46d:'call\t0x4001d418,[],0',
           0x4001e476:'mov\td0,(0x0000620c)',
           0x4001e481:'movhu\td0,(0x00006210)',
           0x4001e486:'call\t0x4001d42c,[],0',
           0x4001d418:'mov\tpsw,d0',
           0x4001d428:'mov\td1,(a0)',
           0x4001d432:'mov\td0,psw',
           0x4000b797:'movhu\t(0x9c050010),d0'}

def probe(aux,reader):
    image=aux.read_bytes()
    if len(image)!=219104 or hashlib.sha256(image).hexdigest()!=AUX_SHA:
        raise ValueError('Exact private build1101 stabilizer component required')
    reader_sha=verify_reader(reader); code={}; decoded={}
    for start,end in WINDOWS:
        listing=subprocess.check_output([str(reader.resolve()),str(aux.resolve()),hex(AUX_BASE),hex(start-AUX_BASE),hex(end-AUX_BASE)],text=True)
        decoded.update(checked_listing(listing,image,start,end,base=AUX_BASE))
        code.update(parse_listing(listing,image,AUX_BASE))
    for pc,text in ANCHORS.items():
        if decoded.get(pc)!=text: raise ValueError(f'Changed instruction at {pc:#x}')
    def machine(epoch,pending):
        mem=Memory([Region(0x61e0,bytearray(128),True,'synthetic counter RAM')])
        mem.write(0x620c,epoch & 0xffffffff,4); mem.write(0x6210,epoch>>32,2)
        mem.write(0x61f5,pending,1)
        return Machine(code,mem)
    def snapshot(m,label):
        lo=m.memory.read(0x620c,4); hi=m.memory.read(0x6210,2); p=m.memory.read(0x61f5,1)
        return dict(label=label,low=lo,high=hi,pending=p,epoch=(hi<<32)|lo,epoch_plus_pending=((hi<<32)|lo)+p)
    def run(m,start,stop):
        r=m.run(start,stops=[stop],limit=40)
        if r['status']!='stop': raise AssertionError(r)
    rows=[]
    for epoch in (10,0xffffffff,0xffffffffffff):
        for pending in (1,2,255):
            m=machine(epoch,pending); states=[snapshot(m,'before drain')]
            run(m,0x4001d385,0x4001d38f)
            states.append(snapshot(m,'after pending decrement, before tick function'))
            # Explicit host bridge: not execution of the call/stack/PSW helpers.
            run(m,0x4001e472,0x4001e479)
            states.append(snapshot(m,'after low store, before possible high carry'))
            run(m,0x4001e479,0x4001e484)
            states.append(snapshot(m,'after counter arithmetic'))
            assert states[1]['epoch_plus_pending']==states[0]['epoch_plus_pending']-1
            assert states[-1]['epoch']==(epoch+1)%(1<<48)
            assert states[-1]['pending']==pending-1
            if epoch!=0xffffffffffff:
                assert states[-1]['epoch_plus_pending']==states[0]['epoch_plus_pending']
            rows.append(dict(initial_epoch=epoch,initial_pending=pending,observations=states,
                             trace=[hex(pc) for pc in m.trace]))
    # Host read protocols, NOT native getters or admissible camera schedules.
    ordinary=rows[0]['observations']; carry=rows[3]['observations']
    read_models=[
      dict(name='two identical complete reads during drain gap',
           first=ordinary[1],second=ordinary[1],stable=True,
           counter_total_preserved=False),
      dict(name='high-low-high during low-store carry gap',
           first_high=carry[2]['high'],low=carry[2]['low'],second_high=carry[2]['high'],
           stable_high=True,observed_epoch=carry[2]['epoch'],
           before_epoch=carry[0]['epoch'],after_epoch=carry[3]['epoch'])]
    assert read_models[1]['observed_epoch'] < read_models[1]['before_epoch']
    return dict(schema='epl9-gyro-snapshot-probe-v1',component_sha256=AUX_SHA,
                reader_sha256=reader_sha,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                native_cases=len(rows),windows=len(WINDOWS),anchors=len(ANCHORS),cases=rows,
                host_read_protocol_counterexamples=read_models,
                critical_section_static_facts={'tick_enter':'0x4001e46d -> 0x4001d418',
                 'tick_exit':'0x4001e486 -> 0x4001d42c',
                 'saved_psw_destination':'caller-provided a0',
                 'mask_semantics_and_reader_preemption_qualified':False},
                limitations=['each fragment independently entered; call boundary bridged explicitly',
                 'observations at every instruction are adversarial, not proved interrupt schedules',
                 'PSW helpers verified statically, not executed or modeled',
                 'atomicity of individual bus reads is not qualified',
                 'phase, pending hardware IRQ and absolute clock frequency not modeled',
                 'no measured camera race, timestamp algorithm, gyro sample or exposure join'],
                firmware_changed=False,camera_accessed=False)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--aux',type=Path,required=True); p.add_argument('--reader',type=Path,default=default_reader())
    p.add_argument('--out',type=Path,required=True); a=p.parse_args()
    if a.out.exists(): raise ValueError('New output required')
    result=probe(a.aux,a.reader); a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'report':str(a.out),'native_cases':result['native_cases']}))
if __name__=='__main__': main()
