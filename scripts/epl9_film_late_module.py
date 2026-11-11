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
from epl9_color_extension import controls, assembly, matrix_assembly, KEYS
from epl9_wb_extension import controls as wb_controls, assembly as wb_assembly
from epl9_native_source_gate import extend_late_source

LATE_TEMPLATE = ROOT/'firmware_src/epl9_films_late.s.in'
PRIVATE_TEMPLATE = ROOT/'firmware_src/epl9_films_private_color.s.in'


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


def build_late_module(image,base=MODULE_BASE,diagnostic_rgb=False,rgb_document=None,color_document=None,wb_document=None,private_color=False,native_source_gate=False):
    require(type(native_source_gate) is bool,'native_source_gate must be explicit boolean')
    require(not (diagnostic_rgb and rgb_document is not None),'choose provided RGB tables or diagnostic RGB, not both')
    provided = rgb_tables(rgb_document) if rgb_document is not None else None
    module = build_module(image,base,diagnostic_rgb)
    constants = dict(module['constants'],GOLD_HEADER=0x00780101,PORTRA_HEADER=0x00780201,
                     CONTROL_MAGIC=0x46504c45)
    source = Template(LATE_TEMPLATE.read_text()).substitute({k:str(v) for k,v in constants.items()})
    if native_source_gate:
        source=extend_late_source(source)
    extended=controls(color_document) if color_document is not None else None
    if extended is not None:
        source=source.replace('color_restore:\n',assembly(extended,base)+'color_restore:\n')
        source+='\n'+matrix_assembly(extended)
    wb=wb_controls(wb_document) if wb_document is not None else None
    if wb is not None: source+='\n'+wb_assembly(wb,native_source_gate=native_source_gate)
    if private_color:
        source+='\n'+Template(PRIVATE_TEMPLATE.read_text()).substitute({k:str(v) for k,v in constants.items()})
    code,symbols,rows = assemble(source,base)
    require(len(code) <= 0x1000,'late code overlaps HSL data')
    data = bytearray(module['data'])
    data[:0x1000] = bytes(0x1000)
    data[:len(code)] = code
    if extended is not None:
        for key,offset in zip(KEYS,(0x1c00,0x2c00)):
            if extended[key]['six_axis'] is not None:
                struct.pack_into('<12h',data,offset,*extended[key]['six_axis'])
    if provided is not None:
        for prefix,key in (('GOLD','0x01010078'),('PORTRA','0x01020078')):
            for n,values in enumerate(provided[key]):
                at = constants[f'{prefix}_RGB{n}']-base
                data[at:at+512] = struct.pack('<256H',*values)
    rgb_sha = sha(json.dumps(rgb_document,sort_keys=True,separators=(',',':')).encode()) if provided is not None else None
    patches = []
    hook_specs = [
        (0x60752202,'881cf9140c','jmp',['film_route_gate'],b''),
        (0x6079d7f4,'cd34fbf01cf8923d','call',['film_gamma_hook','[d2,d3,a2,a3]','28'],b'\xcb'),
        (0x6079fb88,'f1d3f1ef53','jmp',['film_private_entry' if private_color else 'film_color_entry'],b''),
    ]
    if wb is not None:
        hook_specs.append((0x60761c9e,'fab4f002a000','jmp',['film_wb_entry'],b'\xcb') if native_source_gate else
                          (0x6074f352,'0008257e0e','jmp',['film_wb_entry'],b''))
    if extended is not None:
        hook_specs.append((0x6079c017,'cdc4feb00c','jmp',['film_matrix_hook'],b''))
    for at,before,op,args,suffix in hook_specs:
        raw = bytes.fromhex(before)
        require(image[at-BASE:at-BASE+len(raw)] == raw,'late hook source bytes changed')
        replacement = encode(op,args,at,symbols)+suffix
        require(len(replacement) == len(raw),'late hook length mismatch')
        patches.append(dict(address=at,before=before,after=replacement.hex()))
    return dict(module,data=bytes(data),source=source,symbols=symbols,rows=rows,
        code_bytes=len(code),constants=constants,patches=patches,template=LATE_TEMPLATE,color_controls=extended,wb_controls=wb,
        metadata=dict(generation='late-v2',preserves_original_art_keys=True,
            existing_owner_object_unchanged=True,extra_owner_allocation=False,
            legacy_commit_prepare_interfaces_used=False,extra_stack_bytes=2176 if private_color else 88,
            private_color_snapshot=private_color,
            private_template_sha256=sha(PRIVATE_TEMPLATE.read_bytes()) if private_color else None,
            temporary_color_key=11,request_fields_restored_on_return=True,
            rgb_data_source='provided' if provided is not None else 'diagnostic' if diagnostic_rgb else 'stock',
            rgb_document_canonical_sha256=rgb_sha,native_curve_channel_order_verified=False,
            color_controls_sha256=sha(json.dumps(color_document,sort_keys=True).encode()) if extended else None,
            wb_controls_sha256=sha(json.dumps(wb_document,sort_keys=True).encode()) if wb else None,
            early_gain_bias_enabled=wb is not None and not native_source_gate,physical_wb_channel_order_verified=False,
            native_wb_bias_implemented=wb is not None,install_ready=False,
            native_source_gate_policy='primary-art-base-variant-v1' if native_source_gate else 'legacy',
            gain_bias_stage='fresh request after source copy and optional selector callback' if native_source_gate and wb else 'early request constructor',
            gain_bias_hook_address='0x60761c9e' if native_source_gate and wb else '0x6074f352' if wb else None,
            finalized_request_stability_required=native_source_gate,
            arbitrary_mutator_callbacks_qualified=False,
            native_matrix_preserved=not extended or all(v['matrix_delta'] is None for v in extended.values()),
            calibration_matrix_replaced=False,six_axis_override_enabled=bool(extended and any(v['six_axis'] is not None for v in extended.values())),
            matrix_adjustment_before_owner_callback=extended is not None,
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
    ap.add_argument('--color-controls',type=Path)
    ap.add_argument('--wb-controls',type=Path)
    ap.add_argument('--native-source-gate',action='store_true',
        help='Opt in to source 0x0107/flags 3 and finalized-request gain placement; requires the qualified owner path')
    args = ap.parse_args()
    document = json.loads(args.rgb_tables.read_text(encoding='utf-8')) if args.rgb_tables else None
    color_document=json.loads(args.color_controls.read_text(encoding='utf-8')) if args.color_controls else None
    wb_document=json.loads(args.wb_controls.read_text(encoding='utf-8')) if args.wb_controls else None
    module = build_late_module(MAIN.read_bytes(),args.base,args.diagnostic_rgb,document,color_document,wb_document,native_source_gate=args.native_source_gate)
    _,report = emit_files(module,args.out)
    print(json.dumps({k:report[k] for k in ('code_bytes','module_sha256','preserves_original_art_keys','extra_owner_allocation')},indent=2))


if __name__ == '__main__':
    main()
