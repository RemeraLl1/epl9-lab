"""Record wider coefficient inputs, including unresolved native software paths."""
import argparse
import json
from pathlib import Path
from epl9_film_late_probe import prepare_probe
from epl9_job_probe import experiment


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--wb-controls',type=Path,required=True)
    args=ap.parse_args()
    document=json.loads(args.wb_controls.read_text())
    image,patched,original_code,code,module,manifest=prepare_probe(args.out,wb_document=document)
    cases=[]
    for key in (0x01010078,0x01020078):
        for gains in ((2048,1536,1024,1056),(1024,1024,1024,1024),(640,480,640,480)):
            r=experiment(patched,code,key,0x200,0,native_module=module,gain_fixture=gains)
            stop=r['executor']
            cases.append(dict(key=hex(key),synthetic_input=gains,native_film=r.get('native_film'),
                status=stop['status'],stop=stop,hardware_pixels=False))
    report=dict(module=manifest,cases=cases,
                unrestricted_coefficient_domain_validated=False,install_ready=False)
    (args.out/'wb-dependencies.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps([dict(key=r['key'],input=r['synthetic_input'],status=r['status'],
        target=hex(r['stop']['target']) if 'target' in r['stop'] else r['stop'].get('error')) for r in cases],indent=2))


if __name__=='__main__':main()
