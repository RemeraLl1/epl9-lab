"""Emit original E-PL9 native film glue; never assemble a flashable container.

Placement is synthetic. Owner allocation/call-site binding is an explicit
remaining integration requirement. Default RGB contents stay stock.
"""
import argparse
import json
from pathlib import Path
import struct
import subprocess
from string import Template

from epl9_workspace_bridge import ROOT, BASE, MAIN, MAIN_SHA, COLOR_ROM, sha, validate_recipes
from epl9_tonal_drafts import definitions, READER_SHA, remap_curve
from mn103_emit import assemble, encode
from mn103_subset import parse_listing

MODULE_BASE = 0x68000000  # Synthetic, not an approved camera address.
TEMPLATE = ROOT/'firmware_src/epl9_films.s.in'
OFFSETS = dict(GOLD_HSL=0x1000, PORTRA_HSL=0x2000,
    GOLD_RGB0=0x3000, GOLD_RGB1=0x3200, GOLD_RGB2=0x3400,
    PORTRA_RGB0=0x3600, PORTRA_RGB1=0x3800, PORTRA_RGB2=0x3a00)


def require(ok, message):
    if not ok:
        raise ValueError(message)


def build_module(image, base=MODULE_BASE, diagnostic_rgb=False):
    require(len(image) == 26214336 and sha(image) == MAIN_SHA, 'requires exact E-PL9 build 1101')
    require(type(base) is int and base % 4 == 0 and 0 <= base <= 0xffffffff-0x3c00,
            'module address is out of range or unaligned')
    require(base+0x3c00 <= BASE or base >= BASE+len(image), 'offline module cannot overlap the stock mapping')
    hsl_path, tone_path = ROOT/'recipes/epl9-film-drafts-v0.json', ROOT/'recipes/epl9-film-drafts-v2.json'
    hsl = validate_recipes(json.loads(hsl_path.read_text()))
    tone = definitions(json.loads(tone_path.read_text()))
    require([r['watercolor_key'] for r in hsl] == [r['watercolor_key'] for r in tone], 'recipe order mismatch')
    constants = {name: base+at for name, at in OFFSETS.items()}
    constants.update(GOLD_KEY=0x01010078, PORTRA_KEY=0x01020078, COLOR_HEADER=0x000b0000)
    for prefix, row in zip(('GOLD','PORTRA'), tone):
        constants.update({prefix+'_CONTRAST': row['picture_mode_contrast'],
            prefix+'_HIGHLIGHTS': row['tone_level']['highlights'], prefix+'_SHADOWS': row['tone_level']['shadows']})
        require(row['tone_level']['midtones'] == 1, 'assembly midtone bias requires review')
    source = Template(TEMPLATE.read_text(encoding='utf-8')).substitute({k: str(v) for k,v in constants.items()})
    code, symbols, rows = assemble(source, base)
    require(len(code) <= 0x1000, 'code overlaps first HSL table')
    data = bytearray(0x3c00)
    data[:len(code)] = code
    stock = struct.unpack_from('<256H', image, 0x608c37e4-BASE)
    for index, (prefix, recipe) in enumerate(zip(('GOLD','PORTRA'), hsl)):
        table = bytearray(image[COLOR_ROM-BASE:COLOR_ROM-BASE+3028])
        for n, triplet in enumerate(recipe['native_hsl']):
            struct.pack_into('<3h', table, n*28+12, *triplet)
        at = OFFSETS[prefix+'_HSL']
        data[at:at+3028] = table
        for slot, delta in enumerate(((24,0,-32) if index == 0 else (-16,8,20))):
            values = remap_curve(stock, [[0,0],[1024,1024+delta],[3072,3072-delta//2],[4095,4095]]) if diagnostic_rgb else stock
            at = OFFSETS[f'{prefix}_RGB{slot}']
            data[at:at+512] = struct.pack('<256H', *values)
    patches = []
    for address, before, op, args, suffix in (
        (0x60752202, '881cf9140c', 'jmp', ['film_route_gate'], b''),
        (0x6079d7f4, 'cd34fbf01cf8923d', 'call', ['film_gamma_hook','[d2,d3,a2,a3]','28'], b'\xcb'),
    ):
        expected = bytes.fromhex(before)
        require(image[address-BASE:address-BASE+len(expected)] == expected, 'patch input bytes changed')
        after = encode(op,args,address,symbols)+suffix
        require(len(after) == len(expected), 'patch span size mismatch')
        patches.append(dict(address=address, before=before, after=after.hex()))
    return dict(data=bytes(data), source=source, symbols=symbols, constants=constants,
        code_bytes=len(code), rows=rows, patches=patches, base=base,
        diagnostic_rgb=diagnostic_rgb, recipes=tone,
        definitions={p.name:sha(p.read_bytes()) for p in (hsl_path,tone_path)})


def emit_files(module, out, reader=None):
    require(not out.exists() and out.resolve().is_relative_to((ROOT/'local').resolve()),
            'output must be a new ignored local directory')
    reader = reader or ROOT/'local/mn103-tooling/mn103-reader.exe'
    require(sha(reader.read_bytes()) == READER_SHA, 'requires inspected GNU reader')
    out.mkdir()
    binary = out/'epl9-films-native.bin'
    binary.write_bytes(module['data'])
    (out/'epl9-films-native.s').write_text(module['source'],encoding='utf-8')
    listing = subprocess.check_output([str(reader.resolve()),str(binary.resolve()),hex(module['base']),
        '0',hex(module['code_bytes'])],text=True)
    code = parse_listing(listing,module['data'],module['base'])
    # Verify every emitted instruction's boundary, mnemonic and operand meaning.
    require(set(code) == {r[0] for r in module['rows']}, 'GNU instruction boundaries disagree with emitter')
    for at,op,args,length in module['rows']:
        raw,decoded,operands = code[at]
        require(len(raw) == length and decoded == op, f'GNU mnemonic mismatch at {at:#x}: {decoded} != {op}')
        for authored,observed in zip(args,operands):
            if authored in module['symbols']:
                require(int(observed,0) == module['symbols'][authored], 'GNU branch target mismatch')
            elif authored.startswith('('):
                from mn103_emit import memory
                require(memory(authored) == memory(observed), 'GNU memory operand mismatch')
            elif authored.startswith('[') or authored[0] in 'das' and not authored[0].isdigit():
                require(authored == observed, f'GNU register mismatch: {authored} != {observed}')
            else:
                require(int(authored,0) & 0xffffffff == int(observed,0) & 0xffffffff, 'GNU immediate mismatch')
        require(len(args) == len(operands), 'GNU operand count mismatch')
    (out/'native-listing.tsv').write_text(listing,encoding='utf-8')
    report = dict(model='Olympus E-PL9', displayed_version='1.1 (owner report)', downloaded_build='1101',
        main_bytes=26214336, main_sha256=MAIN_SHA, reader_sha256=READER_SHA,
        module_base=hex(module['base']), placement='synthetic; camera placement unqualified',
        module_bytes=len(module['data']), code_bytes=module['code_bytes'],
        module_sha256=sha(module['data']), source_sha256=sha(module['source'].encode()),
        template_sha256=sha(module.get('template',TEMPLATE).read_bytes()), definitions=module['definitions'],
        symbols={k:hex(v) for k,v in module['symbols'].items()},
        candidate_patches=[dict(address=hex(p['address']),before=p['before'],after=p['after']) for p in module['patches']],
        owner_call_sites_bound=False, firmware_container_created=False, camera_accessed=False,
        owner_synchronization_and_buffer_lifetime_external=True,
        diagnostic_rgb=module['diagnostic_rgb'], native_wb_bias_implemented=False,
        native_matrix_preserved=True, film_calibrated=False,
        note='Experimental native glue using v2 HSL/tone direction. Stock RGB by default; no camera proof.')
    report.update(module.get('metadata',{}))
    (out/'manifest.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return code, report


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--image',type=Path,default=MAIN)
    ap.add_argument('--base',type=lambda s:int(s,0),default=MODULE_BASE)
    ap.add_argument('--diagnostic-rgb',action='store_true')
    ap.add_argument('--out',type=Path,required=True)
    args = ap.parse_args()
    module = build_module(args.image.read_bytes(),args.base,args.diagnostic_rgb)
    _, report = emit_files(module,args.out)
    print(json.dumps({k:report[k] for k in ('module_bytes','code_bytes','module_sha256','owner_call_sites_bound')},indent=2))


if __name__ == '__main__':
    main()
