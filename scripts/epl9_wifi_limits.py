"""Exact-stock, read-only audit of E-PL9 block sizing and ISC/TCP waits.

No firmware patch is created. Synthetic instruction bytes are decoder fixtures,
not an update input. Outputs must be new directories under ignored local/.
"""

from mn103_tooling import default_reader, verify_reader
import argparse
import json
from pathlib import Path
import struct
import subprocess
import sys

from epl9_wifi_firmware import ROOT, BASE, STOCK_SHA, COMPONENTS, ARM_START, ARM_SIZE, ARM_BASE, ARM_SHA, sha

MAIN_WINDOWS = {
    'http_all': (0x60f28c2d, 0x60f31879),
    'heap_wrappers': (0x60402373, 0x60402822),
    'reply_queue_create': (0x60410269, 0x60410401),
    'reply_queue_delete': (0x60410fc9, 0x60411073),
    'queue_wrappers': (0x6043129f, 0x60431761),
    'shared_address': (0x60439cf3, 0x60439d50),
    'file_read': (0x609ce357, 0x609ce550),
    'file_open': (0x609ce1c8, 0x609ce357),
    'file_open_route': (0x609cf2ed, 0x609cf600),
    'file_open_core': (0x609dcdbc, 0x609dd327),
    'existing_rd_consumer': (0x609d9e7d, 0x609d9ed0),
    'file_sector_read': (0x609dd646, 0x609dd931),
    'isc_send': (0x616f8b52, 0x616f8b84),
    'isc_os_service': (0x616f9c1a, 0x616f9d20),
    'isc_transport': (0x616f90ea, 0x616f94d0),
    'file_read_backend': (0x609ddff6, 0x609de2b1),
}
ARM_WINDOWS = {
    'bsd_accept': (0x12998, 0x12bcc),
    'bsd_send': (0x12bcc, 0x12f1c),
    'socket_defaults': (0x13d8c, 0x14110),
    'socket_options': (0x13b9c, 0x13d44),
    'tcp_limit': (0x1d334, 0x1d388),
    'tcp_space_signal': (0x1d264, 0x1d334),
    'tcp_accept_binding': (0x1dbf0, 0x1ddc0),
    'tcp_ack_queue_release': (0x20a58, 0x20bd0),
    'tcp_queue': (0x1e9a8, 0x1ec1c),
    'tcp_init': (0x1f138, 0x1f280),
    'tcp_schedule': (0x1f6b8, 0x1f734),
    'isc_send': (0x2667c, 0x266e0),
    'shared_cache': (0x2bb28, 0x2bb44),
    'queue_wait': (0x35c9c, 0x35dd0),
}

MN_CHECKS = {
    0x6040238f: 'cmp\t16384,d0',
    0x6040242b: 'cmp\t16384,d0',
    0x6040242f: 'bhi\t0x6040243e',
    0x60402431: 'mov\t131076,d0',
    0x60402449: 'mov\t0,a0',
    0x60402480: 'cmp\t-1575246528,d0',
    0x60402488: 'cmp\t-1574539264,d0',
    0x604024ab: 'cmp\t128,d0',
    0x604024b1: 'mov\t262145,d0',
    0x60402756: 'mov\t16384,d1',
    0x60402763: 'add\t64,d1',
    0x60439cf4: 'cmp\t-1610612736,d2',
    0x60439cfc: 'cmp\t-1073741825,d2',
    0x60439d14: 'and\t1610612735,d0',
    0x60f2efe2: 'mov\t16384,d0',
    0x60f2efe5: 'call\t0x6040240f,[],4',
    0x60f30c6d: 'mov\t16384,d1',
    0x60f30c73: 'mov\t16384,d2',
    0x60f30c81: 'call\t0x609ce357,[d2,d3,a2,a3],24',
    0x60f30c97: 'call\t0x60f30d40,[d2,d3,a2,a3],20',
    0x60f30beb: 'mov\t1629903948,a1',
    0x60f30bf1: 'call\t0x609ce1c8,[],4',
    0x60f31191: 'mov\t3,d1',
    0x60f31198: 'mov\t64,a1',
    0x60f311a2: 'call\t0x6043129f,[d2],12',
    0x60f311d4: 'mov\t4,d0',
    0x60f311d7: 'mov\t64,d1',
    0x60f31204: 'call\t0x47001012,[d2,d3,a2,a3],28',
    0x60f31211: 'mov\t12,d0',
    0x60f31370: 'call\t0x60f31258,[d2,d3],28',
    0x60f31378: 'mov\t16,d0',
    0x60f3137a: 'call\t0x60f312fa,[d2,d3,a2],16',
    0x60f3137f: 'mov\t12,d0',
    0x60f31382: 'call\t0x60f312fa,[d2,d3,a2],16',
    0x60f313b8: 'mov\t-1,d1',
    0x60f313ba: 'call\t0x604314e5,[d2,d3,a2,a3],28',
    0x60f313d4: 'mov\t-1,d1',
    0x60f313d8: 'call\t0x604313e9,[d2,d3,a2,a3],24',
    0x60f313f5: 'call\t0x60f31330,[d2,a2,a3],16',
    0x60f313fc: 'call\t0x60f31330,[d2,a2,a3],16',
    0x60f31405: 'call\t0x60f312a5,[d2,d3,a2,a3],20',
    0x60f31561: 'mov\td3,(8,a2)',
    0x609de032: 'btst\t16,d1',
    0x609de039: 'call\t0x609de148,[d2,d3,a2,a3],60',
    0x609de042: 'call\t0x609de04f,[d2,d3,a2,a3],64',
    0x609de0a7: 'mov\t16384,d0',
    0x609de0aa: 'call\t0x6040240f,[],4',
    0x609de0c5: 'mov\t32,d0',
    0x609de113: 'call\t0x47001012,[d2,d3,a2,a3],28',
    0x609de135: 'call\t0x6040244e,[],4',
    0x609dcea4: 'or\t16,d2',
    0x609dcfe9: 'mov\td0,(a0)',
    0x609de22e: 'cmp\t0,d2',
    0x609de23d: 'add\td3,a1',
    0x609de242: 'call\t0x609dd646,[d2,d3,a2,a3],56',
    0x609de274: 'call\t0x609dd646,[d2,d3,a2,a3],56',
    0x609de287: 'call\t0x47001012,[d2,d3,a2,a3],28',
}
ARM_CHECKS = {
    0x12c20: ('ldr', 'r8, [r6, #0x64]'),
    0x12c40: ('strle', 'r4, [sp, #0x14]'),
    0x12c44: ('strgt', 'r8, [sp, #0x14]'),
    0x12c48: ('bl', '#0x1e9a8'),
    0x13bd4: ('bne', '#0x13ca0'),
    0x13c2c: ('sub', 'r1, r2, #0x1000'),
    0x13c30: ('sub', 'r1, r1, #5'),
    0x13c38: ('bhi', '#0x13ca0'),
    0x13ca0: ('mvn', 'r0, #0x8d'),
    0x13e10: ('mov', 'r1, #0x8000'),
    0x13e1c: ('add', 'r2, r2, #0x8000'),
    0x13e24: ('cmp', 'r2, #0x50000'),
    0x13e94: ('bl', '#0x1f138'),
    0x13eb0: ('cmp', 'r0, #2'),
    0x13eb4: ('movne', 'r5, #0x14'),
    0x13ebc: ('movne', 'r4, #0xa'),
    0x13f20: ('movw', 'ip, #0xea60'),
    0x13f68: ('str', 'ip, [r5, #0x40]'),
    0x14078: ('moveq', 'r4, #6'),
    0x1d2c4: ('rsb', 'r2, r2, r1'),
    0x1d2cc: ('ble', '#0x1d2e8'),
    0x1d2d4: ('bl', '#0x31ae4'),
    0x1dc4c: ('bl', '#0x13ea4'),
    0x1dc7c: ('bl', '#0x13e48'),
    0x1ea1c: ('rsb', 'r3, r3, r2'),
    0x1ea24: ('ble', '#0x1ea80'),
    0x1ea38: ('bl', '#0x35c9c'),
    0x1eb04: ('str', 'r5, [r4, #0xc0]'),
    0x1eb0c: ('bl', '#0x1d264'),
    0x1f140: ('str', 'r2, [r0, #0xc4]'),
    0x20b2c: ('str', 'r3, [r4, #0xc0]'),
    0x20bb0: ('bl', '#0x31ae4'),
    0x26690: ('bl', '#0x2bb28'),
    0x2669c: ('bl', '#0x12e54'),
    0x266bc: ('bl', '#0x1024c'),
    0x2bb28: ('and', 'r3, r0, #0x7f'),
    0x2bb38: ('bicne', 'r1, r1, #0x7f'),
    0x2bb3c: ('addne', 'r1, r1, #0x80'),
}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--reader', type=Path, default=default_reader())
    p.add_argument('--arm-package-dir', type=Path, default=ROOT/'local/wifi-python')
    args = p.parse_args()
    out = args.out.resolve()
    if out.exists() or not out.is_relative_to((ROOT/'local').resolve()):
        raise ValueError('output must be a new directory under ignored local/')
    stock = (ROOT/'firmware/OLY_E_133_1101_0000_0000.BIN').read_bytes()
    if len(stock) != 104552480 or sha(stock) != STOCK_SHA:
        raise ValueError('wrong E-PL9 stock')
    images, identities = {}, []
    for name in ['00_0100_406e0020.decoded.bin', '02_0106_43ae0020.decoded.bin']:
        path = ROOT/'local/epl9-1101-analysis/decoded'/name
        data = path.read_bytes()
        size, digest = COMPONENTS[name]
        if len(data) != size or sha(data) != digest:
            raise ValueError('wrong decoded component')
        images[name] = data
        identities.append(dict(name=name, bytes=size, sha256=digest))
    image_path = ROOT/'local/epl9-1101-analysis/decoded/00_0100_406e0020.decoded.bin'
    image = images[image_path.name]
    arm = images['02_0106_43ae0020.decoded.bin'][ARM_START:ARM_START+ARM_SIZE]
    if sha(arm) != ARM_SHA:
        raise ValueError('wrong embedded ARM module')
    listings = {}
    for name, (start, stop) in MAIN_WINDOWS.items():
        verify_reader(args.reader)
        listings['main_'+name] = subprocess.check_output(
            [str(args.reader.resolve()), str(image_path), hex(BASE), hex(start-BASE), hex(stop-BASE)], text=True)
    decoded = {}
    for listing in listings.values():
        for line in listing.splitlines():
            address, raw, instruction = line.split('\t', 2)
            address, raw = int(address, 16), bytes.fromhex(raw)
            if image[address-BASE:address-BASE+len(raw)] != raw:
                raise ValueError('MN103 listing bytes do not match stock')
            decoded[address] = instruction.rstrip()
    for address, expected in MN_CHECKS.items():
        if decoded.get(address) != expected:
            raise ValueError(f'MN103 anchor mismatch at {address:#x}: {decoded.get(address)!r}')
    sys.path.insert(0, str(args.arm_package_dir.resolve()))
    import capstone
    if capstone.__version__ != '5.0.6':
        raise ValueError('expected Capstone 5.0.6')
    md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_ARM)
    md.skipdata = True
    arm_decoded = {}
    for name, (start, stop) in ARM_WINDOWS.items():
        rows = []
        for i in md.disasm(arm[start-ARM_BASE:stop-ARM_BASE], start):
            arm_decoded[i.address] = (i.mnemonic, i.op_str)
            rows.append(f'{i.address:08x}\t{i.bytes.hex()}\t{i.mnemonic}\t{i.op_str}')
        listings['arm_'+name] = '\n'.join(rows)+'\n'
    for address, expected in ARM_CHECKS.items():
        if arm_decoded.get(address) != expected:
            raise ValueError(f'ARM anchor mismatch at {address:#x}')
    pool_row = struct.unpack_from('<4I', image, 0x60405f50-BASE)
    if pool_row != (0xa21ba540, 16384, 43, 0xdeb40000):
        raise ValueError('physical pool descriptor mismatch')
    if 43*(16384+64) != 0xa2267000-0xa21ba540:
        raise ValueError('pool stride/extent mismatch')
    if image[0x61265c4c-BASE:0x61265c4c-BASE+2] != b'r\0':
        raise ValueError('HTTP original mode changed')
    if image[0x60a8ba0c-BASE:0x60a8ba0c-BASE+3] != b'rd\0':
        raise ValueError('existing rd mode literal changed')
    if struct.unpack_from('<II', image, 0x60a8c2c4-BASE) != (ord('d')-42, 0x609dcea1):
        raise ValueError('d mode parser binding changed')
    direct_read_shapes = []
    for name, size in [('PB020001.ORF', 14692005), ('PB020001.JPG', 3249056), ('PB020002.MOV', 8105416)]:
        full, tail = divmod(size, 16384)
        direct_read_shapes.append(dict(file=name, bytes=size, full_16k_reads=full,
                                       tail_bytes=tail, tail_whole_sectors=tail//512,
                                       tail_partial_bytes=tail%512,
                                       body_send_requests_minimum=full+bool(tail),
                                       note='arithmetic for aligned sequential reads; not camera execution'))
    out.mkdir(parents=True)
    # Demonstrate the SIGNED immediate at all three block-size sites without
    # touching a single firmware byte. Each independent synthetic instruction
    # is followed by retf, so instruction length/boundary is checked too.
    fixture = b''.join(bytes([op])+struct.pack('<H', value)+b'\xde\x00\x00'
                       for value in [16384, 24576, 32767, 32768, 49152, 65535]
                       for op in [0x2c, 0x2d, 0x2e])
    fixture_path = out/'synthetic-signed-immediates.dat'
    fixture_path.write_bytes(fixture)
    verify_reader(args.reader)
    listings['synthetic_signed_immediates'] = subprocess.check_output(
        [str(args.reader.resolve()), str(fixture_path), '0x1000', '0', hex(len(fixture))], text=True)
    fixture_rows = [line.split('\t', 2) for line in listings['synthetic_signed_immediates'].splitlines()]
    if len(fixture_rows) != 36:
        raise ValueError('unexpected synthetic instruction count')
    for n, value in enumerate([16384, 24576, 32767, 32768, 49152, 65535]):
        signed = value if value < 32768 else value-65536
        for reg in range(3):
            row = (n*3+reg)*2
            if fixture_rows[row][2].rstrip() != f'mov\t{signed},d{reg}' or \
                    fixture_rows[row+1][2].rstrip() != 'retf\t[],0':
                raise ValueError('signed-immediate fixture mismatch')
    for name, listing in listings.items():
        (out/f'{name}.tsv').write_text(listing, encoding='utf-8')
    report = dict(model='Olympus PEN E-PL9', owner_displayed_version='1.1', downloaded_main_build='1101',
                  stock_bytes=len(stock), stock_sha256=sha(stock), installed_image_dumped=False,
                  components_read=identities, arm_module_bytes=len(arm), arm_module_sha256=sha(arm),
                  main_base=hex(BASE), arm_base=hex(ARM_BASE),
                  main_windows={k: [hex(a), hex(b)] for k, (a,b) in MAIN_WINDOWS.items()},
                  arm_windows={k: [hex(a), hex(b)] for k, (a,b) in ARM_WINDOWS.items()},
                  script_sha256=sha(Path(__file__).read_bytes()), reader_sha256=verify_reader(args.reader),
                  checked_mn103={hex(a): s for a, s in MN_CHECKS.items()},
                  checked_arm={hex(a): s for a, s in ARM_CHECKS.items()},
                  synthetic_instruction_cases=18,
                  direct_read_shapes=direct_read_shapes,
                  physical_pool=dict(descriptor=hex(0x60405f50), start=hex(pool_row[0]),
                                     block_bytes=pool_row[1], blocks=pool_row[2], slot_stride=16384+64,
                                     pointer_range_end=hex(0xa2267000), free_blocks_observed=False),
                  firmware_modified=False, patch_created=False, camera_accessed=False)
    (out/'audit.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(out=str(out), windows=len(listings), mn103_checks=len(MN_CHECKS),
                          arm_checks=len(ARM_CHECKS), synthetic_instruction_cases=18,
                          physical_pool=report['physical_pool'], firmware_modified=False), indent=2))


if __name__ == '__main__':
    main()
