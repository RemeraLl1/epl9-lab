"""Native owner parameter production and constructor-to-matrix binding.

Property values and buffers are explicit host inputs. Events 2, 13 and 21
execute stock code with the context copied by the stock constructor. Resource
events retain bounded host contracts; no camera/pixel claim.
"""
import argparse
import json
import struct
import subprocess
from pathlib import Path

from epl9_workspace_bridge import ROOT, MAIN, BASE, sha
from epl9_film_late_probe import prepare_probe
from epl9_job_probe import experiment, OWNER_CALLBACK, OWNER_CONTEXT, JOB, RETURN
from epl9_owner_callback_probe import fixture, load_owners, CALLBACKS, CONTEXT, OBJECT, SP, END
from epl9_lifecycle_probe import Lifecycle
from epl9_wb_math_probe import extend
from epl9_deployment_probe import Registers
from epl9_wb_extension import adjusted
from mn103_subset import Memory, Region, parse_listing, Fault
from mn103_calls import CallMachine

PROPERTIES, PARAMETERS = 0x2e000000, 0x2d000000
FACTORIES = {'primary': (0x607ce515,0xf0,24), 'primary_wrapper': (0x607d0b25,0x30,16)}
WINDOWS = {'primary_params':(0x607ce515,0x607ce5ae),
    'wrapper_params':(0x607d0b25,0x607d0b8d),
    'selectors':(0x607d25a7,0x607d2873), 'option':(0x607d5505,0x607d5520),
    'header':(0x60743621,0x60743846)}


def load_factories(image,out):
    code={}
    for name,(a,b) in WINDOWS.items():
        listing=subprocess.check_output([str(ROOT/'local/mn103-tooling/mn103-reader.exe'),
            str(MAIN),hex(BASE),hex(a-BASE),hex(b-BASE)],text=True)
        (out/(name+'.tsv')).write_text(listing)
        code.update(parse_listing(listing,image,BASE))
    return code


def create_parameters(image,code,name,variant,*,cancelled=0):
    state=fixture(cancelled=cancelled)
    obj=state['object'];obj.extend(bytes([0xa5])*(0x7000-len(obj)))
    for region in state['regions']:
        if region.address==OBJECT:region.address=PROPERTIES
    struct.pack_into('<I',state['context'],152,PROPERTIES)
    struct.pack_into('<H',state['context'],72,0x1003)
    state['context'][164]=1
    struct.pack_into('<H',state['context'],272,0)
    obj[22955]=120
    struct.pack_into('<H',obj,22926,0)
    for offset,value in ((23680,0),(23688,variant),(23689,0),(22956,0),(22957,0),(23703,0)):
        obj[offset]=value
    params=bytearray(32)
    m=CallMachine(code,Memory([Region(BASE,image),*state['regions'],Region(PARAMETERS,params,True),
        Region(SP-8192,bytearray(16384),True)]),dict(sp=SP,a0=CONTEXT,a1=PARAMETERS))
    target,mask,frame=FACTORIES[name]
    before=bytes(obj)
    r=m.run(m.enter(target,END,mask,frame),[END])
    if r.get('pc')!=END or m.r['sp']!=SP or any(e['op']=='modeled_call' for e in m.events):
        raise ValueError('native parameter producer failed: '+str(r))
    if struct.unpack_from('<2I',params)!=(CALLBACKS[name],CONTEXT):
        raise ValueError('native callback/context binding differs')
    if params[8:12]!=bytes((1,variant,120,0)) or struct.unpack_from('<H',params,16)[0]!=0x1000:
        raise ValueError('native ART header/kind differs')
    if obj!=before:raise ValueError('parameter producer changed owner property storage')
    return bytes(params),state,dict(producer=hex(target),callback=hex(CALLBACKS[name]),
        context=hex(CONTEXT),parameters=params.hex(),instructions=len(m.trace),modeled_calls=0,
        declared_fields={'operation':0x1003,'art':120,'art_variant':variant,'dimension_selector':1})


def control_cases(image,code):
    """Native control returns, including cancellation's persistent ready clear."""
    rows=[]
    for name in FACTORIES:
        for event in (13,21,31):
            for ready in (0,1):
                for cancelled in (0,1):
                    state=fixture(ready=ready,cancelled=cancelled)
                    context_before=bytes(state['context']);object_before=bytes(state['object'])
                    m=CallMachine(code,Memory([Region(BASE,image),*state['regions'],
                        Region(SP-8192,bytearray(16384),True)]),
                        dict(sp=SP,d0=event,a0=0,a1=CONTEXT))
                    r=m.run(m.enter(CALLBACKS[name],END),[END])
                    expected=bytearray(context_before)
                    if event==13 and cancelled:expected[195]=0
                    if (r.get('pc')!=END or m.r['sp']!=SP or
                            any(e['op']=='modeled_call' for e in m.events) or
                            m.r['d0']!=expected[195] or state['context']!=expected or
                            state['object']!=object_before):
                        raise ValueError('native control return/state differs: '+str(r))
                    rows.append(dict(owner=name,event=event,ready=ready,cancelled=cancelled,
                        result=m.r['d0'],ready_after=state['context'][195],
                        instructions=len(m.trace),modeled_calls=0))
    return rows


class BoundOwner:
    name='native-bound-controls-and-matrix-with-declared-resources'
    def __init__(self,previous,native_code,entry,state):
        self.previous,self.code,self.entry,self.state=previous,native_code,entry,state
        self.calls=[]

    def validate(self,m,mask,frame):
        if m.r['a1']!=CONTEXT:raise Fault('constructor-bound context changed')
        original=m.r['a1'];m.r['a1']=OWNER_CONTEXT
        try:self.previous.validate(m,mask,frame)
        finally:m.r['a1']=original

    def apply(self,m):
        event=m.r['d0']&255
        if event not in (2,13,21):
            original=m.r['a1'];m.r['a1']=OWNER_CONTEXT
            try:detail=self.previous.apply(m)
            finally:m.r['a1']=original
            return dict(detail,declared_resource_adapter=True)
        arg,sp=m.r['a0'],m.r['sp']
        values=[m.memory.read(arg+2*i,2) for i in range(9)] if event==2 else None
        return_pc=m.memory.read(sp,4)
        before=bytes(self.state['object']);context_before=bytes(self.state['context'])
        cancelled=m.memory.read(m.memory.read(CONTEXT+4,4),4)
        # Separate instruction map avoids shadowing native code with a model.
        # RAM and actual registers/context are the same at this explicit boundary.
        child=CallMachine(self.code,m.memory,dict(m.r))
        child.r=Registers(child.r)
        for flag in ('n','z','c','v'):setattr(child,flag,getattr(m,flag))
        r=child.run(self.entry,[return_pc])
        if r.get('pc')!=return_pc or child.r['sp']!=sp or any(e['op']=='modeled_call' for e in child.events):
            raise Fault('native bound owner did not return: '+str(r))
        expected=bytearray(before)
        if event==2:struct.pack_into('<9H',expected,4114,*[(2*v)&65535 for v in values])
        if self.state['object']!=expected:raise Fault('bound owner matrix copy differs')
        expected_context=bytearray(context_before)
        if event==13 and cancelled==1:expected_context[195]=0
        if self.state['context']!=expected_context or child.r['d0']!=expected_context[195]:
            raise Fault('bound owner control state/return differs')
        if any(pc in (0x6074e6eb,0x6079fb88) for pc in child.trace):raise Fault('bound owner reentered processing')
        m.r.minimum_sp=min(m.r.minimum_sp,child.r.minimum_sp)
        m.r.update(child.r)
        for flag in ('n','z','c','v'):setattr(m,flag,getattr(child,flag))
        m.trace.extend(child.trace);m.events.extend(child.events)
        self.calls.append(dict(event=event,callback=hex(self.entry),context=hex(CONTEXT),matrix=values,
            instructions=len(child.trace),modeled_calls=0,context_rewritten=False,returned=child.r['d0']))
        detail=dict(event=event,context_rewritten=False,returned=child.r['d0'])
        if event==2:detail['coefficients_preserved']=values
        return detail


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--color-controls',type=Path)
    ap.add_argument('--rgb-tables',type=Path,
        help='Use the supplied recipe curves instead of diagnostic RGB markers')
    ap.add_argument('--private-color',action='store_true',
        help='Opt in to private stack copies of COLOR request/context')
    args=ap.parse_args()
    if args.color_controls is None and args.rgb_tables is None:
        ap.error('provide diagnostic color controls or actual recipe RGB tables')
    color=json.loads(args.color_controls.read_text()) if args.color_controls else None
    rgb=json.loads(args.rgb_tables.read_text()) if args.rgb_tables else None
    wb=json.loads((ROOT/'recipes/epl9-native-wb-trial-v1.json').read_text())
    image,patched,_,code,module,manifest=prepare_probe(args.out,base=0x604a1300,
        color_document=color,wb_document=wb,rgb_document=rgb,diagnostic_rgb=rgb is None,
        private_color=args.private_color)
    owner_code=load_owners(image,args.out)
    controls=control_cases(image,owner_code)
    producer_code={**owner_code,**load_factories(image,args.out)}
    extend(image,code)
    rows=[];cancellations=[]
    for name in FACTORIES:
        for variant in (1,2):
            params,state,producer=create_parameters(image,producer_code,name,variant)
            observer=Lifecycle(module['base']);adapters=[]
            def attach(m):
                observer(m)
                m.memory=Memory([*m.memory.regions,*[r for r in state['regions'] if r.address!=0x8050]])
                adapter=BoundOwner(m.models[OWNER_CALLBACK],owner_code,CALLBACKS[name],state)
                if CALLBACKS[name] in m.code:raise ValueError('native bound owner model would shadow code')
                m.models[CALLBACKS[name]]=adapter;adapters.append(adapter)
            # The outer engine has an explicit function boundary here. Native
            # controls and event 2 use the child map with the same RAM/context.
            outer_code={a:v for a,v in code.items() if a!=CALLBACKS[name]}
            report=experiment(patched,outer_code,0x01000078+(variant<<16),0x1000,0,
                parameter_fixture=params,native_module=module,input_format=0x200,gain_fixture=(1024,)*4,
                machine_observer=attach)
            film=report.get('native_film',{})
            wanted="0x6073eafa mov ['d0', '(0x9880014c)']: unmapped access at 0x9880014c, size 4"
            if report.get('executor',{}).get('error')!=wanted or not film.get('recipe_applied'):
                raise ValueError('native-produced job must apply recipe and reach TruePic boundary: '+str(film))
            key=f'0x{0x01000078+(variant<<16):08x}'
            if tuple(film['request_gain_record'])!=adjusted((1024,)*4,module['wb_controls'][key]):
                raise ValueError('native-produced job skipped WB bias')
            matrix_calls=[c for c in adapters[0].calls if c['event']==2]
            if (not matrix_calls or any(c['matrix']!=film['matrix_words'] for c in matrix_calls) or
                    not {13,21} <= {c['event'] for c in adapters[0].calls} or
                    not observer.restored or observer.pending or report['output_changed'] or report['event_bits_signalled']):
                raise ValueError('native binding/restoration/matrix contract failed')
            binding=tuple(observer.m.memory.read(JOB+n,4) for n in (4,8))
            if binding!=(CALLBACKS[name],CONTEXT):raise ValueError('constructor owner binding changed')
            row=dict(owner=name,variant=variant,producer=producer,
                constructor=report.get('constructor'),start=report.get('start'),executor=report.get('executor'),
                entries=report.get('entries'),film=report.get('native_film'),calls=adapters[0].calls,
                restored=observer.restored,stack=observer.result(),
                owner_binding=[hex(v) for v in binding])
            rows.append(row)
            (args.out/'binding-progress.json').write_text(json.dumps(rows,indent=2)+'\n')
            print(json.dumps(dict(owner=name,variant=variant,recipe_applied=film['recipe_applied'],
                request_kind=film['request_fields']['14'],native_matrix_callbacks=len(matrix_calls)),indent=2))
            params,state,producer=create_parameters(image,producer_code,name,variant,cancelled=1)
            observer=Lifecycle(module['base']);adapters=[]
            negative=experiment(patched,outer_code,0x01000078+(variant<<16),0x1000,0,
                parameter_fixture=params,native_module=module,input_format=0x200,gain_fixture=(1024,)*4,
                machine_observer=attach,destroy_job=True)
            (args.out/f'cancel-{name}-{variant}.json').write_text(json.dumps(dict(
                experiment=negative,calls=adapters[0].calls,ready_after=state['context'][195]),indent=2)+'\n')
            if (negative.get('executor',{}).get('pc')!=RETURN or
                    negative['executor']['registers']['d0']!='0x9e01' or
                    negative['cancelled']!=1 or state['context'][195]!=0 or
                    negative['worklist_calls'] or negative['processor_entered'] or
                    negative['output_changed'] or negative['cpu_source_reads'] or
                    negative['event_bits_signalled'] or not negative['pending_record_zero'] or
                    negative['pool_live_after_destructor'] or
                    negative['destructor'].get('pc')!=RETURN or
                    [(c['event'],c['returned']) for c in adapters[0].calls]!=[(13,0)]):
                raise ValueError('native owner cancellation did not stop and release the job')
            cancellations.append(dict(owner=name,variant=variant,executor=negative['executor'],
                destructor=negative['destructor'],native_calls=adapters[0].calls,
                worklist_calls=negative['worklist_calls'],pending_record_zero=True,pool_live=[],
                output_changed=False,source_reads=0,ready_after=state['context'][195]))
    sources=('epl9_owner_binding_probe.py','epl9_owner_callback_probe.py','epl9_job_probe.py',
        'epl9_lifecycle_probe.py','epl9_film_handoff.py','epl9_wb_math_probe.py','epl9_float_contract.py')
    report=dict(main_sha256=sha(image),module=manifest,cases=rows,control_cases=controls,
        native_cancellation_cases=cancellations,
        source_sha256={name:sha((ROOT/'scripts'/name).read_bytes()) for name in sources},
        camera_state_measured=False,full_pixel_cycle_passed=False,install_ready=False)
    (args.out/'binding.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
