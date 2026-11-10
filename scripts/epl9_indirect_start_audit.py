"""Bounded E-PL9 indirect task-start provenance. No camera/media/network.

Explicit task IDs/current-task replies are fixtures, not physical OK selection.
Kernel activation, allocation, transport and diagnostic boundaries are declared.
"""
import argparse
import json
from pathlib import Path
import struct

from epl9_ok_entry_audit import (ROOT, BASE, MAIN_NAME, MAIN_SHA, STOCK_SHA,
    READER_SHA, sha, u32, transfers, pointer_candidates, verified_input, local_output)
from epl9_boot_recovery_audit import task_records
from mn103_subset import Memory, Region, Fault, parse_listing
from mn103_calls import CallMachine

WINDOWS = {
    'queue_producer': (0x60433b2f, 0x60433b5f),
    'queue_consumer': (0x60433ca9, 0x60433db0),
    'start_wrapper': (0x604318bb, 0x604318ff),
    'stop_wrapper': (0x604318ff, 0x604319b2),
    'cpu1_sender': (0x60438c39, 0x60438c4f),
    'cpu2_sender': (0x60438fe3, 0x60438ff9),
    'cpu1_start_slice': (0x604389bf, 0x60438a05),
    'cpu2_start_slice': (0x60438d74, 0x60438dba),
    'existing_thread_factory': (0x60db9f77, 0x60db9fa7),
    'existing_thread_constructor': (0x60db9b9d, 0x60db9bb4),
    'thread_start': (0x60db9d0a, 0x60db9d2f),
    'current_thread_slice': (0x60dbb3d3, 0x60dbb3ed),
    'factory_and_current_getters': (0x60db93a5, 0x60db93ce),
    'object_allocator_wrapper': (0x60dba072, 0x60dba07c),
    'task_slot_allocator': (0x60414e95, 0x60414f87),
}
STACK, SP, RETURN = 0x18000000, 0x18008000, 0x1a000000
PACKET, OBJECT, RESULT = 0x19000000, 0x19001000, 0x19002000


def load_code(image, out):
    import subprocess
    from epl9_video_audit import checked_listing
    reader = ROOT/'local/mn103-tooling/mn103-reader.exe'
    if sha(reader.read_bytes()) != READER_SHA:
        raise ValueError('unqualified reader')
    code = {}
    for name, (lo, hi) in WINDOWS.items():
        s = subprocess.check_output([str(reader.resolve()),
            str((ROOT/'local/epl9-1101-analysis/decoded'/MAIN_NAME).resolve()),
            hex(BASE), hex(lo-BASE), hex(hi-BASE)], text=True)
        checked_listing(s, image, lo, hi)
        parsed = parse_listing(s, image, BASE)
        if any(code[a] != parsed[a] for a in code.keys() & parsed.keys()):
            raise ValueError('conflicting instruction boundaries')
        code.update(parsed)
        (out/(name+'.tsv')).write_text(s, encoding='utf8')
    return code


class Boundary:
    def __init__(self, name, abi, value=0):
        self.name, self.abi, self.value = name, abi, value

    def validate(self, m, mask, frame):
        if (mask, frame) != self.abi:
            raise Fault(f'undeclared {self.name} ABI {mask:#x}/{frame}')

    def apply(self, m):
        detail = {'explicit_model': True}
        if self.name == 'packet-allocation':
            m.r['a0'] = self.value
            detail['declared_pointer'] = hex(self.value)
        elif self.name == 'transport-trap':
            assert m.r['a0'] == PACKET
            detail.update(task_argument=m.r['d0'], operation=m.memory.read(PACKET,4),
                          source_cpu=m.memory.read(PACKET+12,4),
                          task_field=m.memory.read(PACKET+20,4), transport_executed=False)
        elif self.name == 'activation-trap':
            detail.update(requested_task=m.r['d0'], scheduled=False)
        elif self.name == 'current-task-query':
            m.memory.write(m.r['a0'], self.value, 2)
            detail['supplied_current_task'] = self.value
        elif self.name == 'object-allocation':
            assert m.r['d0'] == 28
            m.r['a0'] = OBJECT
            detail.update(requested_bytes=28, declared_pointer=hex(OBJECT))
        elif self.name == 'packet-release':
            assert m.r['a0'] == PACKET
        m.r['d0'] = 0
        return detail


def memory(image, extra=()):
    return Memory([Region(BASE, image, False, 'exact main'),
                   Region(STACK, bytearray(0x10000), True, 'synthetic stack'), *extra])


def diagnostic_models():
    return {a:Boundary('diagnostic-suppressed', (0x80,8)) for a in (0x604335ef,0x604335fd)}


def queue_cases(image, code):
    rows = []
    for cpu, task, available in ((0,1,True),(0,89,True),(1,89,True),(2,89,True),(0,89,False)):
        models = {0x60434318:Boundary('packet-allocation',(0xf0,24),PACKET if available else 0),
                  0x60433e02:Boundary('transport-trap',(0xf0,36)),
                  0x60434371:Boundary('packet-release',(0x20,8))}
        mem = memory(image, [Region(0x8050,struct.pack('<I',cpu),False,'declared source CPU'),
                             Region(PACKET,bytearray(64),True,'declared packet')])
        m = CallMachine(code,mem,{'sp':SP,'d0':task},models=models)
        m.enter(0x60433b2f,RETURN,0xe0,16)
        stop = m.run(0x60433b2f,stops={RETURN})
        assert stop.get('pc') == RETURN and m.r['sp'] == SP
        sent = [e for e in m.events if e.get('model') == 'transport-trap']
        assert len(sent) == int(available)
        assert m.r['d0'] == (0 if available else 255)
        row = dict(source_cpu_fixture=cpu,task_argument_fixture=task,available_packet=available,
                   producer_result=m.r['d0'],producer_events=m.events)
        if available:
            assert sent[0]['operation'] == 9 and sent[0]['task_field'] == task
            raw = bytes(mem.read(PACKET+i,1) for i in range(64))
            n = CallMachine(code,memory(image,[Region(PACKET,bytearray(raw),True,'producer packet')]),
                            {'sp':SP,'a0':PACKET},models={
                0x60410727:Boundary('activation-trap',(0xe0,16)),
                0x6043436e:Boundary('completion-notification-suppressed',(0,0))})
            n.enter(0x60433ca9,RETURN,0xb0,24)
            end = n.run(0x60433ca9,stops={0x60433d8d,0x60433d9b,0x60433da5})
            assert end.get('status') == 'stop'
            starts = [e for e in n.events if e.get('model') == 'activation-trap']
            assert [e['requested_task'] for e in starts] == [task]
            assert n.memory.read(PACKET+8,4) == 0 and n.memory.read(PACKET+48,4) == 5
            row.update(consumer_events=n.events,consumer_stop=end,
                       note='packet handoff between isolated fragments; no cross-CPU scheduler; stop before interrupt write')
        rows.append(row)
    return rows


def mailbox_cases(image, code):
    rows = []
    for sender, consumer, stop_at, address in (
            (0x60438c39,0x604389bf,0x60438a05,0x8ff00060),
            (0x60438fe3,0x60438d74,0x60438dba,0x8ff00088)):
        for command in (0x10001,0x10002):
            mem = memory(image,[Region(address,bytearray(12),True,'declared mailbox')])
            m = CallMachine(code,mem,{'sp':SP,'d0':command,'d1':89})
            m.enter(sender,RETURN,0x80,4)
            end = m.run(sender,stops={RETURN})
            assert end.get('pc') == RETURN and m.r['sp'] == SP
            assert [mem.read(address+4*i,4) for i in range(3)] == [command,89,0]
            models = diagnostic_models() | {
                0x60410727:Boundary('activation-trap',(0xe0,16)),
                0x60448f89:Boundary('critical-section-entry',(0x80,8)),
                0x60448fd2:Boundary('critical-section-exit',(0x80,8))}
            m = CallMachine(code,mem,{'sp':SP},models=models)
            end = m.run(consumer,stops={stop_at})
            assert end.get('pc') == stop_at
            starts = [e for e in m.events if e.get('model') == 'activation-trap']
            assert [e['requested_task'] for e in starts] == ([89] if command==0x10001 else [])
            if command == 0x10001:
                assert mem.read(address,4) == 0 and mem.read(address+8,4) == 1
            rows.append(dict(sender=hex(sender),consumer=hex(consumer),
                             command_fixture=hex(command),task_fixture=89,events=m.events,
                             physical_mailbox_used=False,
                             note='10002 stops before later command dispatch; this case tests only the start branch'))
    return rows


def object_cases(image, code):
    rows = []
    initial_vtable = u32(image,0x60632210)
    assert initial_vtable == 0x60ef1a64
    for current in (1,89):
        models = {0x604117be:Boundary('current-task-query',(0x20,4),current),
                  0x60402373:Boundary('object-allocation',(0,4))}
        mem = memory(image,[Region(0x6239cf50,struct.pack('<I',initial_vtable),False,'stock factory initializer'),
                             Region(OBJECT,bytearray(28),True,'declared object allocation')])
        m = CallMachine(code,mem,{'sp':SP},models=models)
        end = m.run(0x60dbb3d3,stops={0x60dbb3ed})
        assert end.get('pc') == 0x60dbb3ed and m.r['sp'] == SP
        assert mem.read(OBJECT,4) == 0x60ef19d0 and mem.read(OBJECT+4,2) == current
        assert mem.read(OBJECT+8,4) == mem.read(OBJECT+12,4) == 1
        assert not any(e.get('model') == 'activation-trap' for e in m.events)
        rows.append(dict(current_task_fixture=current,wrapped_id=mem.read(OBJECT+4,2),
                         events=m.events,task_activation=False,
                         note='current=89 presupposes SD is already the current task'))
    for ident in (89,0xffff):
        raw = bytearray(28);struct.pack_into('<IH',raw,0,0x60ef19d0,ident)
        models = diagnostic_models() | {0x60410727:Boundary('activation-trap',(0xe0,16))}
        m = CallMachine(code,memory(image,[Region(OBJECT,raw,True,'declared existing-ID object')]),
                        {'sp':SP,'a0':OBJECT},models=models)
        m.enter(0x60db9d0a,RETURN)
        end = m.run(0x60db9d0a,stops={RETURN})
        assert end.get('pc') == RETURN and m.r['sp'] == SP
        starts = [e for e in m.events if e.get('model') == 'activation-trap']
        assert [e['requested_task'] for e in starts] == ([89] if ident==89 else [])
        rows.append(dict(stored_id_fixture=hex(ident),events=m.events,
                         note='explicit method call on a supplied object; not a discovered OK caller'))
    return rows


def allocator_cases(image, code):
    cfg=0x6042143c;table=u32(image,cfg+204)
    pointers=struct.unpack_from('<255I',image,table-BASE)
    rows=[]
    for mode,requested,want in (('stock-occupied',0,144),('cleared-89-control',0,89),
                                ('explicit-89',89,-18),('all-occupied',0,-34)):
        tcb=[]
        ids={r['id']&0xfff:r['id'] for r in task_records(image)}
        if mode=='cleared-89-control':ids.pop(89)
        if mode=='all-occupied':ids={i:i for i in range(1,256)}
        for ident,pointer in enumerate(pointers,1):
            raw=bytearray(120);struct.pack_into('<H',raw,16,ids.get(ident,0))
            tcb.append(Region(pointer,raw,True,'declared task occupancy'))
        mem=memory(image,[Region(0x8050,bytes(4),False,'CPU zero'),
            Region(0x8ff00004,struct.pack('<I',cfg),False,'stock context'),
            Region(u32(image,cfg+56),bytearray(struct.pack('<HH',1,len(ids))),True,'declared cursor/count'),
            Region(RESULT,bytearray(4),True,'selected TCB output'),*tcb])
        m=CallMachine(code,mem,{'sp':SP,'d0':requested,'a0':RESULT})
        m.enter(0x60414e95,RETURN,0xf0,24)
        end=m.run(0x60414e95,stops={RETURN},limit=10000)
        assert end.get('pc')==RETURN and m.r['sp']==SP
        value=m.r['d0'] if m.r['d0']<0x80000000 else m.r['d0']-0x100000000
        assert value==want,(mode,value)
        rows.append(dict(occupancy_fixture=mode,requested_id=requested,result=value,
                         instructions=len(m.trace),task_activation=False))
    return rows


def contracts(image,code):
    expected={0x60433b2f:['0x604318c7'],0x60438c39:['0x60431919'],0x60438fe3:['0x6043193c']}
    refs={}
    for target,sites in expected.items():
        found=transfers(image,{target})
        assert [r['site'] for r in found]==sites and pointer_candidates(image,target)==[]
        refs[hex(target)]=found
    for a in (0x60431912,0x60431935):
        _,op,args=code[a];assert (op,args)==('mov',['65538','d0'])
    assert u32(image,0x60ef1a88)==0x60db9f77 and u32(image,0x60ef1a90)==0x60db93b1
    assert u32(image,0x60ef19fc)==0x60db9d0a
    return dict(producer_candidates=refs,physical_OK_producer_found=False,
                current_thread_factory_supplies_existing_id=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True)
    args=p.parse_args()
    if not __debug__:p.error('assertions required')
    out=local_output(args.out)
    image=verified_input(ROOT/'local/epl9-1101-analysis/decoded'/MAIN_NAME,26214336,MAIN_SHA)
    stock=verified_input(ROOT/'firmware/OLY_E_133_1101_0000_0000.BIN',104552480,STOCK_SHA)
    out.mkdir();code=load_code(image,out)
    queue=queue_cases(image,code);mailbox=mailbox_cases(image,code)
    objects=object_cases(image,code);allocation=allocator_cases(image,code)
    static=contracts(image,code)
    report=dict(model='Olympus PEN E-PL9',model_bytes='1330',
        displayed_version='1.1 (owner report)',downloaded_main_build='1101',
        stock_bytes=len(stock),stock_sha256=STOCK_SHA,main_bytes=len(image),main_sha256=MAIN_SHA,
        reader_sha256=READER_SHA,source_sha256=sha(Path(__file__).read_bytes()),
        dependencies={n:sha((ROOT/'scripts'/n).read_bytes()) for n in (
            'mn103_subset.py','mn103_calls.py','epl9_ok_entry_audit.py','epl9_boot_recovery_audit.py',
            'epl9_video_audit.py','epl9_color_audit.py')},
        queue_cases=queue,mailbox_cases=mailbox,object_cases=objects,allocator_cases=allocation,
        static_contracts=static,camera_accessed=False,media_accessed=False,network_accessed=False,
        firmware_modified=False,physical_OK_to_SD_proven=False,
        reference_revision='539fcf1fa9eda5fdef8ede4deeab94a4691d94c3')
    (out/'results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(queue_cases=len(queue),mailbox_cases=len(mailbox),object_cases=len(objects),
        allocator_cases=len(allocation),physical_OK_to_SD_proven=False,camera_accessed=False),indent=2))


if __name__=='__main__':main()
