"""Trace matrix notification and request restoration before event 4/hardware start."""
import argparse,json,struct,subprocess
from pathlib import Path
from epl9_workspace_bridge import ROOT,BASE,MAIN,sha
from epl9_film_late_probe import prepare_probe
from epl9_wb_math_probe import extend
from epl9_float_contract import models
from epl9_job_probe import experiment
from epl9_deployment_probe import Observe
from mn103_subset import Memory,Region,Machine,parse_listing


class Lifecycle(Observe):
    def __call__(self,m):
        super().__call__(m)
        self.sequence=[];self.pending={};self.restored=[]
        enter,read=m.enter,m.read
        def snapshot(address):
            region,offset=m.memory.region(address,4)
            return bytes(region.data[offset:offset+1876])
        def traced_enter(target,return_pc,mask=0,frame=0):
            index=len(m.trace)
            if target==0x6079fb88:
                request=m.memory.read(m.r['a0']+4,4)
                self.color_output=m.memory.read(m.r['a0']+12,4)
                self.pending[return_pc]=(request,snapshot(request))
                self.sequence.append(dict(event='color_entry',instruction=index))
            elif target==0x6073eab3:
                self.sequence.append(dict(event='owner_callback',code=m.r['d0']&255,instruction=index,
                    return_pc=hex(return_pc),argument=hex(m.r['a1']),owner_descriptor=hex(m.r['a0']),
                    callback=hex(m.memory.read(m.r['a0'],4)),owner_context=hex(m.memory.read(m.r['a0']+4,4)),
                    during_color=bool(self.pending)))
            elif target==0x6079bf86:
                self.sequence.append(dict(event='matrix_packer',instruction=index,return_pc=hex(return_pc),
                    destination=hex(m.r['a0']),output_offset=m.r['a0']-getattr(self,'color_output',0),
                    key=hex(m.r['d0'])))
            elif target in (0x607a17b7,0x607a1841,0x6074edd9,0x6073f74f):
                self.sequence.append(dict(event=hex(target),instruction=index))
            return enter(target,return_pc,mask,frame)
        def traced_read(operand,size=4):
            pc=m.trace[-1] if m.trace else -1
            if pc in self.pending:
                address,before=self.pending.pop(pc)
                same=snapshot(address)==before
                if not same:raise ValueError('connected request not restored at color return')
                self.restored.append(dict(request=hex(address),bytes=1876))
                self.sequence.append(dict(event='color_return_restored',instruction=len(m.trace)))
            return read(operand,size)
        m.enter,m.read=traced_enter,traced_read
        leaves=models()
        if leaves.keys()&m.code.keys():raise ValueError('scalar model shadows native code')
        m.models.update(leaves)
        m.memory=Memory([*m.memory.regions,Region(0xa2a7da44,bytearray(4),True)])


def task31(image):
    row=struct.unpack_from('<7I',image,0x60418cc4-BASE+31*28)
    if row[0]!=31 or row[3]!=0x607ce1b5 or row[5]!=14080:raise ValueError('task 31 descriptor changed')
    anchors={0x607ce1b5:'cff0',0x607ce1b7:'fafe9cfe',0x607ce31c:'cdd700b014',
             0x607ce460:'cd010c303c',0x607cf0e0:'cdcef4b01c',
             0x607ce63f:'ddac00f8fff020'}
    for at,raw in anchors.items():
        if image[at-BASE:at-BASE+len(bytes.fromhex(raw))]!=bytes.fromhex(raw):raise ValueError('task stack anchor mismatch')
    return dict(task=31,entry=hex(row[3]),declared_stack=row[5],saved_register_bytes=16,local_bytes=356,
                intermediate_call_frame_bytes=[20,60,28],prefix_before_executor_bytes=480,
                executor_call_frame_bytes=32,executor_frame_already_in_measurement=True,
                path='607ce31c -> 607ce460 -> 607cf0e0 -> 607ce63f; conditional branch',
                task_runtime_and_interrupt_headroom_verified=False)


def owner_matrix_tails(image):
    # Selected post-gate tails only: logging, state lookup and readiness gates
    # are not modeled as unconditional success.
    values=(126,2,0,0,129,-1,1,0,127)
    coeff=struct.pack('<9h',*values);rows=[]
    for start,end,slot,a2 in ((0x607d0acf,0x607d0b22,8,0x1d000000),
                               (0x609a83c5,0x609a841e,4,0x1c000000)):
        listing=subprocess.check_output([str(ROOT/'local/mn103-tooling/mn103-reader.exe'),str(MAIN),
            hex(BASE),hex(start-BASE),hex(end-BASE)],text=True)
        code=parse_listing(listing,image,BASE)
        data=bytearray([0xa5])*4200;stack=bytearray(512);sp=0x1e000100
        struct.pack_into('<I',stack,256+slot,0x1c000000 if slot==8 else 0x1d000000)
        m=Machine(code,Memory([Region(BASE,image),Region(0x1c000000,coeff),
            Region(0x1d000000,data,True),Region(0x1e000000,stack,True)]),dict(sp=sp,a2=a2))
        result=m.run(start,[end]);expected=bytearray([0xa5])*4200
        struct.pack_into('<9H',expected,4114,*[(2*v)&65535 for v in values])
        if result.get('pc')!=end or data!=expected:raise ValueError('native owner matrix-copy tail differs')
        rows.append(dict(entry=hex(start),stop=hex(end),matrix_words=9,destination_offset=4114,
                         native_scale=2,other_bytes_unchanged=True,full_callback_executed=False))
    return rows


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--color-controls',type=Path)
    args=ap.parse_args()
    wb=json.loads((ROOT/'recipes/epl9-native-wb-trial-v1.json').read_text())
    color=json.loads(args.color_controls.read_text()) if args.color_controls else None
    image,patched,_,code,module,manifest=prepare_probe(args.out,wb_document=wb,base=0x604a1300,
                                                    color_document=color,diagnostic_rgb=True)
    extend(image,code);rows=[]
    for key in (0x01010078,0x01020078):
        for kind in (0x200,0x100,0x40):
            observer=Lifecycle(module['base'])
            opts=dict(provide_slot=True,input_format=0x100) if kind==0x40 else {}
            report=experiment(patched,code,key,kind,0,native_module=module,gain_fixture=(1024,)*4,
                              machine_observer=observer,**opts)
            if not observer.restored or observer.pending:raise ValueError('no complete observed color return')
            sequence=observer.sequence
            returned=max(x['instruction'] for x in sequence if x['event']=='color_return_restored')
            hardware=[x['instruction'] for x in sequence if x['event']=='0x6073f74f']
            notify=[x['instruction'] for x in sequence if x['event']=='owner_callback' and x['code']==4]
            if not hardware or min(hardware)<=returned or not notify or min(notify)<=returned:
                raise ValueError('hardware/notification ordering violated')
            if report['output_changed'] or report['event_bits_signalled']:raise ValueError('fabricated pixels/completion')
            notified=[e['coefficients_preserved'] for e in report['events'] if e.get('event')==2 and 'coefficients_preserved' in e]
            if not notified or any(v!=report['native_film']['matrix_words'] for v in notified):
                raise ValueError('owner and ISP matrix mismatch')
            rows.append(dict(key=hex(key),kind=hex(kind),stack=observer.result(),sequence=sequence,
                             restored=observer.restored,owner_matrix_matches_isp=True,hardware_started_after_restoration=True))
    task=task31(image)
    task['scoped_configuration_stack_bound']=max(x['stack']['observed_stack_depth'] for x in rows)+task['prefix_before_executor_bytes']
    report=dict(main_sha256=sha(image),module=manifest,cases=rows,task31=task,owner_matrix_tails=owner_matrix_tails(image),
        owner_event2_inside_temporary_configuration=True,
        same_job_concurrent_entry_excluded=False,isp_irq_and_scheduling_verified=False,install_ready=False)
    (args.out/'lifecycle.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows),whole_request_restoration=True,task31=task),indent=2))


if __name__=='__main__':main()
