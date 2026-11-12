"""Offline bridge from a validated E9B1 snapshot to native descriptor layout.

Executes authored MN103 materialization, not a camera loader or hook. All
addresses are synthetic, and the caller owns validation, lifetime and memory.
"""
import struct
from epl9_recipe_banks import Bank, MAX_RECIPES, unpack_bank, pack_bank
from epl9_sd_recipes import pack_recipe, require
from epl9_sd_processing import TEMPLATE, RECORD, STRIDE, MAGIC, pointer
from epl9_sd_loader import assemble
from mn103_subset import Memory, Region
from mn103_calls import CallMachine

MODULE = 0x6b000000
ARENA = 0x18000000
RAW = 0x19000000
STACK = 0x1a000000
STOP = 0x12345678
ROM = 0x608ee360
GUARD = bytes([0xa5])*16


def build():
    # Reuse the existing independently exercised descriptor writer, replacing
    # only its two-slot getter with an explicit caller-owned record pointer.
    source = TEMPLATE.read_text().split('sd_materialize:\n', 1)[1].split('# Default descriptors', 1)[0]
    source = 'sd_materialize:\n' + source
    source = source.replace(' call $GET,[d2,d3,a2,a3],24', ' mov a1,a0')
    source = source.replace('$RECORD_PTR', pointer('a1', 'a3', RECORD)).replace('$MAGIC', str(MAGIC))
    require('$' not in source, 'unresolved materializer input')
    raw, symbols, rows = assemble(source, MODULE)
    code = {pc:(raw[pc-MODULE:pc-MODULE+n], op,
                [hex(symbols[a]) if a in symbols else a for a in args])
            for pc,op,args,n in rows}
    return dict(data=raw, source=source, symbols=symbols, rows=rows, code=code)


def materialize_snapshot(bank, rom_table, *, code=None):
    """Return an offline immutable arena, preserving logical order, not ART IDs.

    There is deliberately no global registry, native allocator, SD operation,
    camera address assignment or implicit lifetime/publication claim.
    """
    require(isinstance(bank, Bank), 'validated Bank required')
    bank = unpack_bank(pack_bank(bank))
    require(type(rom_table) is bytes and len(rom_table)==3028, 'exact 3028-byte HSL template required')
    module = build()
    count = len(bank.recipes)
    records = b''.join(pack_recipe(r) for r in bank.recipes)
    destination = bytearray(GUARD + bytes(count*STRIDE) + GUARD)
    memory = Memory([Region(ARENA-16, destination, True, 'host-owned arena with guards'),
                     Region(RAW, records, False, 'validated immutable bank records'),
                     Region(ROM, rom_table, False, 'provided HSL template'),
                     Region(STACK, bytearray(4096), True, 'synthetic stack')])
    for index in range(count):
        m = CallMachine(code if code is not None else module['code'], memory,
                        dict(sp=STACK+4000, a0=ARENA+index*STRIDE,
                             a1=RAW+index*660, d0=index+1))
        sp=m.r['sp']
        saved={r:m.r[r] for r in m.saved(0xf0)}
        result=m.run(m.enter(module['symbols']['sd_materialize'], STOP, 0xf0,24), [STOP], limit=30000)
        require(result.get('pc')==STOP and m.r['sp']==sp and all(m.r[k]==v for k,v in saved.items()),
                'native materializer did not return with ABI preserved')
    require(destination[:16]==GUARD and destination[-16:]==GUARD, 'arena guards changed')
    return bytes(destination[16:-16])


def footprint(count):
    require(type(count) is int and 1<=count<=MAX_RECIPES, 'requires 1..31 records')
    return dict(records=count, serialized_bank_bytes=24+count*660,
                expanded_descriptors_bytes=count*STRIDE,
                both_retained_bytes=24+count*(660+STRIDE),
                camera_allocation_proven=False)


def main():
    import argparse
    import hashlib
    import json
    import subprocess
    from pathlib import Path
    from dataclasses import replace
    from mn103_tooling import verify_reader
    from mn103_subset import parse_listing
    from epl9_workspace_bridge import MAIN_SHA, BASE
    from epl9_sd_loader_probe import sample_recipe
    from epl9_sd_processing import descriptor
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--main',type=Path,required=True)
    parser.add_argument('--reader',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    image=args.main.read_bytes()
    require(hashlib.sha256(image).hexdigest()==MAIN_SHA,'wrong E-PL9 main')
    reader_sha=verify_reader(args.reader)
    args.out.mkdir(parents=True,exist_ok=False)
    module=build()
    module_path=args.out/'authored-materializer.bin'
    module_path.write_bytes(module['data'])
    listing=subprocess.check_output([str(args.reader),str(module_path),hex(MODULE),'0',hex(len(module['data']))],text=True)
    code=parse_listing(listing,module['data'],MODULE)
    require(set(code)==set(module['code']), 'GNU instruction boundaries differ')
    # GNU-decoded instructions, not assembler rows, drive this run.
    records=tuple(replace(sample_recipe(),recipe_id=100+i,name=f'Synthetic {i}',
                         contrast=i%5-2,tone=(i%15-7,0,7-i%15),
                         hsl=((i*10-150,i-15,15-i),)*12,
                         wb_q10=(512+i*32,2048-i*32)) for i in range(31))
    bank=Bank(7,records)
    arena=materialize_snapshot(bank,image[ROM-BASE:ROM-BASE+3028],code=code)
    checks=[]
    for i,record in enumerate(records):
        want=descriptor(image,pack_recipe(record),ARENA+i*STRIDE,i+1,RAW+i*660)
        got=arena[i*STRIDE:(i+1)*STRIDE]
        require(got==want,'native materialization differs from host oracle')
        checks.append(dict(ordinal=i+1,recipe_id=record.recipe_id,bytes_compared=len(got),sha256=hashlib.sha256(got).hexdigest()))
    report=dict(schema='epl9-native-bank-materializer-experiment-v1',main_sha256=MAIN_SHA,
                reader_sha256=reader_sha,module_sha256=hashlib.sha256(module['data']).hexdigest(),
                module_bytes=len(module['data']),native_instruction_count=len(code),
                cases=checks,footprint=footprint(31),
                camera_accessed=False,firmware_changed=False,art_ids_assigned=False,
                real_recipe_parameters=False,real_allocator_verified=False,
                sd_or_delete_hooks_installed=False,install_ready=False)
    (args.out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='cases'},indent=2))


if __name__=='__main__':main()
