"""Execute bounded stock ART-header producer with declared capture configuration.

No UI-to-configuration mapping, TruePic output, full job lifecycle, firmware
installation, or preview parity is proved. Proprietary bytes stay local.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from epl9_embedded_art_inventory import BASE, MAIN_SHA
from mn103_subset import Memory, Region, parse_listing
from mn103_calls import CallMachine
from mn103_tooling import reader_provenance

FORMATTER = 0x60743621
PRODUCER = 0x607d26a0
STOP = 0x607d2756
STACK, OWNER, CONFIG, OUTPUT = 0x10012000, 0x20000000, 0x21000000, 0x22000000
WINDOWS = ((FORMATTER,0x60743845),(PRODUCER,STOP))


def load_code(main, reader):
    image=main.read_bytes()
    if hashlib.sha256(image).hexdigest()!=MAIN_SHA:
        raise ValueError('requires exact stock E-PL9 1101 decoded main')
    provenance=reader_provenance(reader)
    code={}
    for start,end in WINDOWS:
        listing=subprocess.check_output([str(reader),str(main),hex(BASE),
            hex(start-BASE),hex(end-BASE)],text=True)
        code.update(parse_listing(listing,image,BASE))
    return code,provenance


def execute(code,mode,variant,operation=0x1003,submode=0):
    if not 100 <= mode <= 255 or not 0 <= variant <= 255:
        raise ValueError('bounded ART input domain required')
    m=CallMachine(code,Memory([
        Region(STACK-8192,bytearray(16384),True,'declared stack'),
        Region(OWNER,bytearray(512),True,'declared owner'),
        Region(CONFIG,bytearray(24000),True,'declared configuration'),
        Region(OUTPUT,bytearray(8),True,'header destination')]),
        dict(sp=STACK,a0=OWNER,a1=OUTPUT))
    m.memory.write(OWNER+152,CONFIG,4)
    m.memory.write(OWNER+72,operation,2)
    m.memory.write(OWNER+86,submode,2)
    m.memory.write(CONFIG+22955,mode,1)
    m.memory.write(CONFIG+23688,variant,1)
    result=m.run(PRODUCER,[STOP])
    if result['status']!='stop' or result['pc']!=STOP:
        raise ValueError('unexpected native stop: '+str(result))
    calls=[e for e in m.events if e['op']=='call']
    if len(calls)!=1 or calls[0]['target']!=FORMATTER or m.models:
        raise ValueError('unexpected calls or software model')
    actual=bytes(m.memory.read(OUTPUT+i,1) for i in range(4))
    overridden=operation in (0x2001,0x2006) and submode==2
    effective_variant=variant or 1
    expected=bytes((0,0,2,0)) if overridden else bytes((1,effective_variant,mode,0))
    if actual!=expected:
        raise ValueError('ART header branch differs')
    group,kind=actual[:2];identifier=int.from_bytes(actual[2:],'little')
    return dict(mode=mode,variant=variant,operation=hex(operation),submode=submode,
        header=actual.hex(),processing_key=hex((group<<24)|(kind<<16)|identifier),
        conditional_override=overridden,native_instructions=len(m.trace),
        native_formatter_calls=len(calls),modeled_calls=0,
        stop_before_instruction=hex(STOP))


def probe(code):
    rows=[execute(code,mode,variant) for mode in (100,120,255) for variant in (0,1,2,3)]
    rows += [execute(code,120,variant,op,submode)
             for variant in (1,2) for op in (0x2001,0x2006) for submode in (0,2)]
    return dict(schema='epl9-art-header-probe-v1',stock_main_sha256=MAIN_SHA,
        controls=rows,controls_passed=len(rows),ui_to_configuration_proven=False,
        full_producer_executed=False,preview_capture_parity_proven=False,
        hardware_rendering_tested=False,install_ready=False,
        scope='Native bounded producer+formatter; synthetic declared configuration only')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--main',type=Path,required=True)
    p.add_argument('--reader',type=Path,required=True)
    a=p.parse_args();code,provenance=load_code(a.main,a.reader)
    result=probe(code);result['reader_provenance']=provenance
    print(json.dumps(result,indent=2))

if __name__=='__main__': main()
