"""Run native math bodies with explicitly inferred, finite scalar-float leaves."""
import argparse,json,subprocess
from decimal import Decimal,localcontext
from fractions import Fraction
from pathlib import Path
from epl9_film_late_probe import prepare_probe
from epl9_workspace_bridge import ROOT,MAIN,BASE
from epl9_job_probe import experiment
from epl9_deployment_probe import Observe
from epl9_float_contract import models,pack,unpack
from mn103_subset import parse_listing,Memory,Region
from mn103_calls import CallMachine


def extend(image,code):
    reader=ROOT/'local/mn103-tooling/mn103-reader.exe'
    text=subprocess.check_output([str(reader),str(MAIN),hex(BASE),hex(0x604b83c1-BASE),hex(0x604b8900-BASE)],text=True)
    code.update(parse_listing(text,image,BASE))


def power_checks(image,code):
    rows=[]
    for i in range(-64,65):
        exponent=Fraction(i,16)
        sp=0x1f004000;end=0x1e000000
        m=CallMachine(code,Memory([Region(BASE,image),Region(sp-8192,bytearray(16384),True),
            Region(0xa2a7da44,bytearray(4),True)]),dict(sp=sp,d0=pack(Fraction(2)),d1=pack(exponent)),models=models())
        result=m.run(m.enter(0x604b860e,end,0xf0,36),[end])
        if result.get('pc')!=end or m.r['sp']!=sp:raise ValueError('native power failed')
        with localcontext() as ctx:
            ctx.prec=80
            exact=(Decimal(2).ln()*Decimal(i)/Decimal(16)).exp()
            expected=pack(Fraction(exact))
        ulps=abs(m.r['d0']-expected)
        if ulps>3:raise ValueError(f'native power discrepancy: exponent={exponent}, ulps={ulps}')
        rows.append(dict(exponent=str(exponent),output=hex(m.r['d0']),oracle=hex(expected),ulps=ulps))
    return rows


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--base',type=lambda s:int(s,0),default=0x68000000)
    ap.add_argument('--color-controls',type=Path)
    args=ap.parse_args()
    wb=json.loads((ROOT/'recipes/epl9-native-wb-trial-v1.json').read_text())
    color=json.loads(args.color_controls.read_text()) if args.color_controls else None
    image,patched,original_code,code,module,manifest=prepare_probe(args.out,wb_document=wb,color_document=color,
                                                               base=args.base,diagnostic_rgb=True)
    extend(image,code)
    powers=power_checks(image,code)
    rows=[]
    for key in (0x01010078,0x01020078):
        for kind in (0x200,0x100,0x40):
            for selector in (0,2):
                for gains in ((2048,1536,1024,1056),(1024,)*4,(640,480,640,480)):
                    meter=Observe(module['base'])
                    def attach(m):
                        meter(m)
                        leaves=models()
                        if leaves.keys()&m.code.keys():raise ValueError('float model shadows native code')
                        m.models.update(leaves)
                        m.memory=Memory([*m.memory.regions,Region(0xa2a7da44,bytearray(4),True,'math errno')])
                    options=dict(provide_slot=True,input_format=0x100) if kind==0x40 else {}
                    r=experiment(patched,code,key,kind,selector,native_module=module,gain_fixture=gains,machine_observer=attach,**options)
                    expected="0x6073eafa mov ['d0', '(0x9880014c)']: unmapped access at 0x9880014c, size 4"
                    if r['executor'].get('error')!=expected or not r['native_film']['recipe_applied']:
                        raise ValueError('math-supported job did not reach the declared TruePic boundary: '+str(r['executor']))
                    if r['native_film']['request_header']!=('01017800' if key==0x01010078 else '01027800'):
                        raise ValueError('native request identity not restored')
                    rows.append(dict(key=hex(key),kind=hex(kind),selector=selector,gains=gains,executor=r['executor'],film=r['native_film'],
                        stack=meter.result(),float_calls=[e for e in r['events'] if e.get('model')=='inferred-finite-binary32-contract']))
    report=dict(module=manifest,cases=rows,power_checks=powers,inferred_float_contract=True,hardware_float_verified=False)
    (args.out/'math-contract.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows),power_checks=len(powers),max_power_ulps=max(r['ulps'] for r in powers),
        max_observed_stack=max(r['stack']['observed_stack_depth'] for r in rows),hardware_float_verified=False),indent=2))


if __name__=='__main__':main()
