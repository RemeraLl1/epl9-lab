"""Read-only sensor geometry and gyro-producer audit for exact E-PL9 1101.

No camera commands or patch output. Raw listings and extracted records are
written only after verification, into a new ignored local/ directory.
The CPU1-labelled component's analysis base is 0x40002800, not its container
address 0x40002820. Static addresses do not establish execution on the body.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess

from epl9_video_audit import (
    ROOT, BASE, MAIN_NAME, MAIN_SHA, STOCK_SHA, verified_input,
    checked_listing, local_output,
)

AUX_BASE = 0x40002800
AUX_NAME = '03_010e_40002820.decoded.bin'
AUX_SHA = '1c942d2fb6b8830f0195a0be7464880838ddf08c5f038bad626aed8e72789678'

MAIN_WINDOWS = {
    'sensor_mode_decision': (0x607031f0, 0x60703260),
    'sensor_mode_to_record': (0x6071d49d, 0x6071d50e),
    'sensor_record_selection': (0x60749150, 0x607491e9),
    'sensor_geometry_consumer': (0x60742499, 0x6074255d),
    'sensor_auxiliary_consumer': (0x6074255d, 0x607425a9),
    'sensor_mode_state_assignment': (0x60701b03, 0x60701b1c),
    'sensor_record_publication': (0x60706642, 0x6070665b),
    'diagnostic_dispatch': (0x60f517d8, 0x60f5180c),
    'stabilizer_read_packet': (0x60f5670a, 0x60f567a5),
    'stabilizer_selector_operation': (0x604eae31, 0x604eae7f),
    'stabilizer_driver_dispatch': (0x604eb6cf, 0x604eb8bf),
    'stabilizer_register_packet': (0x604ec536, 0x604ec5b8),
    'movie_time_conversion': (0x60ff8069, 0x60ff80c9),
}
AUX_WINDOWS = {
    'entry_base_evidence': (0x40002804, 0x4000281e),
    'command_read_dispatch': (0x400124ac, 0x40012508),
    'command_read_branch': (0x40012637, 0x40012640),
    'selector_read_request': (0x40013202, 0x400132c7),
    'selector_read_values': (0x400094a8, 0x4000955c),
    'selector_table_choice': (0x40015051, 0x4001506f),
    'gyro_adc_callback': (0x400114ab, 0x400114ce),
    'gyro_roll_init': (0x4001a1b1, 0x4001a257),
    'gyro_acquisition': (0x4001a2b5, 0x4001a397),
    'gyro_periodic_callback': (0x4001a0aa, 0x4001a10d),
    'gyro_timer_setup': (0x400172b4, 0x40017337),
    'timer_register_programming': (0x40009884, 0x400099b0),
}
MAIN_ANCHORS = {
    0x607031f1: 'inc4\ta1',
    0x607031f3: 'mov\t1,d2',
    0x607031f5: 'cmp\t0,d0',
    0x6070325b: 'mov\td2,d0',
    0x60701b03: 'call\t0x607031f0,[d2],32',
    0x60701b18: 'movbu\td0,(902,a0)',
    0x60706650: 'call\t0x6071d49d,[],16',
    0x60706659: 'movbu\td0,(a3)',
    0x6074917e: 'add\t1619781920,a0',
    0x6074249b: 'call\t0x607491bf,[],0',
    0x60742504: 'movhu\t(16,a0),d0',
    0x6074250a: 'movhu\t(18,a0),d0',
    0x60742560: 'call\t0x60749150,[],0',
    0x6074256f: 'movhu\t(10,a0),d0',
    0x60f517d8: 'add\t-4097,d2',
    0x60f517dc: 'mov\t1629976272,a1',
    0x604eae33: 'mov\t35,d0',
    0x604eae63: 'movhu\td0,(a1)',
    0x604eae71: 'mov\t162,d0',
    0x604eb8b1: 'asl\t4,d0',
    0x604eb8b6: 'add\t1616398372,a0',
    0x604ec560: 'movbu\t(d1,a0),d0',
    0x604ec595: 'movhu\td0,(d2,a0)',
    0x60ff80b9: 'mov\t600,d0',
    0x60ff80bd: 'mov\t90000,d0',
}
AUX_ANCHORS = {
    0x40002806: 'mov\t1073771500,a0',
    0x40002813: 'mov\t1073771490,a0',
    0x400124e1: 'mov\t1073851836,a3',
    0x40012638: 'call\t0x40013202,[d2,d3,a2,a3],64',
    0x4001321c: 'call\t0x40015051,[],0',
    0x40013292: 'call\t0x400094a8,[d2,d3,a2,a3],32',
    0x400094da: 'udfu01\t12,d0',
    0x400094fa: 'mov\t(a2),a1',
    0x40009512: 'movbu\t(a1),d0',
    0x40009516: 'movbu\t(1,a1),d0',
    0x4001505e: 'mov\t1073853568,a0',
    0x400114c7: 'call\t0x4001a34e,[d2,d3],8',
    0x4001a240: 'mov\t1073859012,a0',
    0x4001a2d4: 'mov\t234,d0',
    0x4001a2dd: 'call\t0x4001621d,[d2,d3,a2,a3],28',
    0x4001a2ea: 'call\t0x40016487,[d2,d3,a2,a3],32',
    0x4001a2fe: 'movbu\t(0x000061c2),d0',
    0x4001a301: 'movbu\t(0x000061c3),d1',
    0x4001a309: 'movhu\td0,(0x0000493e)',
    0x4001a34e: 'movhu\t(0x9c060048),d2',
    0x4001a368: 'movhu\td0,(0x0000493a)',
    0x4001a36d: 'movhu\t(0x9c060044),d2',
    0x4001a37f: 'movhu\td1,(0x0000493c)',
    0x4001a38c: 'cmp\t3,d0',
    0x4001a0ad: 'call\t0x4001a2b5,[d2,a2,a3],16',
    0x4001a0fa: 'mov\t1073848490,a0',
    0x4001a100: 'call\t0x400172d6,[],24',
    0x4001a105: 'call\t0x4001731d,[],4',
    0x400172b4: 'mov\t2,d0',
    0x400172f1: 'mov\t12500,d1',
    0x400172f4: 'movhu\td1,(8,sp)',
    0x40017300: 'call\t0x40009884,[d2,d3,a2,a3],20',
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def hash_target(image, base, table, slots, key):
    """Bounded linear probing used by the reviewed power-of-two dispatches."""
    if slots <= 0 or slots & (slots - 1):
        raise ValueError('hash size must be a positive power of two')
    for step in range(slots):
        slot = ((key & (slots - 1)) + step) & (slots - 1)
        off = table - base + slot * 8
        if off < 0 or off + 8 > len(image):
            raise ValueError('dispatch outside image')
        found, target = struct.unpack_from('<II', image, off)
        if found == key:
            return target
        if found == 0:
            break
    raise ValueError(f'no dispatch for {key:#x}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--reader', type=Path, default=ROOT / 'local/mn103-tooling/mn103-reader.exe')
    args = parser.parse_args()
    out = local_output(args.out)
    verified_input(ROOT / 'firmware/OLY_E_133_1101_0000_0000.BIN', 104552480, STOCK_SHA)
    decoded_dir = ROOT / 'local/epl9-1101-analysis/decoded'
    main_path, aux_path = decoded_dir / MAIN_NAME, decoded_dir / AUX_NAME
    image = verified_input(main_path, 26214336, MAIN_SHA)
    aux = verified_input(aux_path, 219104, AUX_SHA)
    records = [struct.unpack_from('<12H', image, 0x608bece4 - BASE + i*24) for i in range(35)]
    for index, dimensions in {0: (4608,3456), 4: (1536,1152), 5: (1728,1296),
                              14: (2304,1296), 21: (4080,2295)}.items():
        require(records[index][8:10] == dimensions, 'geometry row changed')
    gyro = []
    for selector, pointer in [(192, 0x493a), (193, 0x493c), (194, 0x493e)]:
        address = 0x4001b480 + selector*12
        row = struct.unpack_from('<III', aux, address - AUX_BASE)
        require(row == (pointer, 0x8200 | selector, 0), 'selector row changed')
        gyro.append(dict(selector=selector, row_address=hex(address),
                         ram=hex(pointer), descriptor=hex(row[1]), callback=0))
    dispatches = []
    for table, slots, key, target in [(0x612776d0,32,0x802a,0x60f5191d),
                                      (0x60584660,32,14,0x604e8b3b),
                                      (0x6057e508,16,9,0x604d7654)]:
        require(hash_target(image, BASE, table, slots, key) == target, 'dispatch changed')
        dispatches.append(dict(table=hex(table), key=hex(key), target=hex(target)))
    require(struct.unpack_from('<I', image, 0x61277a88-BASE+6*4)[0] == 0x60f5670a,
            'suboperation 10 branch changed')
    driver = struct.unpack_from('<4I', image, 0x60584824-BASE+35*16)
    require(driver == (0x20081,0x604ec536,0,0x604ec56f), 'driver record changed')
    require(hash_target(aux,AUX_BASE,0x4001adbc,64,0x81) == 0x40012637,
            'component command 0x81 dispatch changed')
    for address, expected in [(0x400073ec,b'task_drive_main\n'),
                              (0x400073e2,b'init_tsk\n'),
                              (0x4001c9c4,b'gyro rol read error!!')]:
        off = address - AUX_BASE
        require(aux[off:off+len(expected)+1] == expected+b'\0', 'component base/string mismatch')
    listings, count = {}, 0
    for path, data, base, windows, anchors in [
            (main_path,image,BASE,MAIN_WINDOWS,MAIN_ANCHORS),
            (aux_path,aux,AUX_BASE,AUX_WINDOWS,AUX_ANCHORS)]:
        decoded = {}
        for name,(start,stop) in windows.items():
            listing = subprocess.check_output([str(args.reader.resolve()),str(path.resolve()),
                                               hex(base),hex(start-base),hex(stop-base)],text=True)
            decoded.update(checked_listing(listing,data,start,stop,base=base))
            listings[name] = listing
        for address,expected in anchors.items():
            require(decoded.get(address) == expected,
                    f'anchor {address:#x}: expected {expected!r}, got {decoded.get(address)!r}')
        count += len(anchors)
    report = dict(model='Olympus PEN E-PL9', model_id='1330', displayed_version='1.1',
                  internal_main_build='1101', stock_sha256=STOCK_SHA,
                  inputs=[dict(name=MAIN_NAME,bytes=len(image),sha256=MAIN_SHA,base=hex(BASE)),
                          dict(name=AUX_NAME,bytes=len(aux),sha256=AUX_SHA,base=hex(AUX_BASE))],
                  reader_sha256=hashlib.sha256(args.reader.read_bytes()).hexdigest(),
                  geometry_table=hex(0x608bece4), geometry_records=records,
                  gyro_selectors=gyro, dispatches=dispatches, driver_operation35=driver,
                  checked_instruction_anchors=count, windows=len(listings),
                  full_field_60_verified=False, gyro_movie_logging_verified=False,
                  gyro_clock_frequency_verified=False, camera_commands_sent=False)
    out.mkdir(parents=True)
    for name,listing in listings.items():
        (out/(name+'.tsv')).write_text(listing,encoding='utf-8')
    (out/'audit.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(out=str(out),anchors=count,windows=len(listings),
                          geometry_records=len(records),gyro_selectors=len(gyro))))


if __name__ == '__main__':
    main()
