"""Late color hook with preserved ART keys and original native owner objects."""
import argparse
from pathlib import Path
import json
import struct
from string import Template

from epl9_film_module import build_module, emit_files, require, MODULE_BASE
from epl9_workspace_bridge import ROOT, BASE, MAIN, sha
from epl9_tonal_drafts import validate_curve
from mn103_emit import assemble, encode

LATE_TEMPLATE = ROOT/'firmware_src/epl9_films_late.s.in'


def rgb_tables(document):
    """Strict two-slot input; slot order is native, not a proven physical R/G/B order."""
    require(type(document) is dict and set(document) == {'schema','recipes'} and
        document['schema'] == 'epl9-native-rgb-tables-v1','unsupported native RGB table schema/fields')
    rows = document['recipes']
    require(type(rows) is list and len(rows) == 2,'requires exactly the two accepted Watercolor slots')
    result = {}
    for row in rows:
        require(type(row) is dict and set(row) == {'watercolor_key','curves'},'unexpected native RGB recipe fields')
        key,curves = row['watercolor_key'],row['curves']
        require(type(key) is str and key in ('0x01010078','0x01020078') and key not in result,
                'unqualified or duplicate Watercolor binding')
        require(type(curves) is list and len(curves) == 3 and all(type(v) is list for v in curves),
                'requires three native-order curve arrays per recipe')
        for values in curves:
            validate_curve(values)
        result[key] = tuple(tuple(v) for v in curves)
    return result


def build_late_module(image,base=MODULE_BASE,diagnostic_rgb=False,rgb_document=None):
    require(not (diagnostic_rgb and rgb_document is not None),'choose provided RGB tables or diagnostic RGB, not both')
    provided = rgb_tables(rgb_document) if rgb_document is not None else None
    module = build_module(image,base,diagnostic_rgb)
    constants = dict(module['constants'],GOLD_HEADER=0x00780101,PORTRA_HEADER=0x00780201,
                     CONTROL_MAGIC=0x46504c45)
    source = Template(LATE_TEMPLATE.read_text()).substitute({k:str(v) for k,v in constants.items()})
    code,symbols,rows = assemble(source,base)
    require(len(code) <= 0x1000,'late code overlaps HSL data')
    data = bytearray(module['data'])
    data[:0x1000] = bytes(0x1000)
    data[:len(code)] = code
    if provided is not None:
        for prefix,key in (('GOLD','0x01010078'),('PORTRA','0x01020078')):
            for n,values in enumerate(provided[key]):
                at = constants[f'{prefix}_RGB{n}']-base
                data[at:at+512] = struct.pack('<256H',*values)
    rgb_sha = sha(json.dumps(rgb_document,sort_keys=True,separators=(',',':')).encode()) if provided is not None else None
    patches = []
    for at,before,op,args,suffix in (
        (0x60752202,'881cf9140c','jmp',['film_route_gate'],b''),
        (0x6079d7f4,'cd34fbf01cf8923d','call',['film_gamma_hook','[d2,d3,a2,a3]','28'],b'\xcb'),
        (0x6079fb88,'f1d3f1ef53','jmp',['film_color_entry'],b''),
    ):
        raw = bytes.fromhex(before)
        require(image[at-BASE:at-BASE+len(raw)] == raw,'late hook source bytes changed')
        replacement = encode(op,args,at,symbols)+suffix
        require(len(replacement) == len(raw),'late hook length mismatch')
        patches.append(dict(address=at,before=before,after=replacement.hex()))
    return dict(module,data=bytes(data),source=source,symbols=symbols,rows=rows,
        code_bytes=len(code),constants=constants,patches=patches,template=LATE_TEMPLATE,
        metadata=dict(generation='late-v2',preserves_original_art_keys=True,
            existing_owner_object_unchanged=True,extra_owner_allocation=False,
            legacy_commit_prepare_interfaces_used=False,extra_stack_bytes=88,
            temporary_color_key=11,request_fields_restored_on_return=True,
            rgb_data_source='provided' if provided is not None else 'diagnostic' if diagnostic_rgb else 'stock',
            rgb_document_canonical_sha256=rgb_sha,native_curve_channel_order_verified=False,
            owner_call_sites_bound=False,
            owner_binding_strategy='No new owner call; use the existing selected request object',
            owner_synchronization_and_buffer_lifetime_external=True,
            note='Late synchronous configuration hook; synthetic placement, no camera/pixel validation.'))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--base',type=lambda x:int(x,0),default=MODULE_BASE)
    ap.add_argument('--diagnostic-rgb',action='store_true')
    ap.add_argument('--rgb-tables',type=Path,help='Two recipes, three 256-entry native-order curves each')
    args = ap.parse_args()
    document = json.loads(args.rgb_tables.read_text(encoding='utf-8')) if args.rgb_tables else None
    module = build_late_module(MAIN.read_bytes(),args.base,args.diagnostic_rgb,document)
    _,report = emit_files(module,args.out)
    print(json.dumps({k:report[k] for k in ('code_bytes','module_sha256','preserves_original_art_keys','extra_owner_allocation')},indent=2))


if __name__ == '__main__':
    main()
