"""Read-only, exact-input-gated E-PL9 Wi-Fi firmware audit.

Writes evidence only to a new directory under ignored local/. No camera access.
The address mapping is the established main-component analysis mapping, not a
claim about every component's runtime address. GNU listings need manual review.
"""

from mn103_tooling import default_reader, verify_reader
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
BASE = 0x60400020
STOCK_SHA = 'aefab05396c43ecba0551b94a5d31f7e52350c18d6f4bf1d02d75761108e6028'
COMPONENTS = {
    '00_0100_406e0020.decoded.bin': (26214336, '8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267'),
    '01_0101_421e0020.decoded.bin': (26214336, 'ee9a9c3ad1974dd212483ca7d012e51ae23083ce0119589a3b42996aa13ccf1e'),
    '02_0106_43ae0020.decoded.bin': (38797248, 'abd9d3f3e8598b3844b9b8d2c06d07ef49d5dbdb4cf00ca5dcaf096dcca659b8'),
    '03_010e_40002820.decoded.bin': (219104, '1c942d2fb6b8830f0195a0be7464880838ddf08c5f038bad626aed8e72789678'),
    '04_0102_468e0020.decoded.bin': (13107136, 'a0d6a08e79f8a1c731959695ada1f26d52ea1e1c0fc9f234618f795ced061c0f'),
}
WINDOWS = {
    'mime_and_http_headers': (0x60f2debe, 0x60f2e577),
    'http_workers': (0x60f2eeb7, 0x60f2fb4c),
    'http_request_and_file': (0x60f2fb4c, 0x60f31042),
    'http_socket_helpers': (0x60f31048, 0x60f31879),
}
ARM_START, ARM_SIZE, ARM_BASE = 0x1ad4fe0, 0x42000, 0x10000
ARM_SHA = '11f9fe5b597248fc6cc3748d604d4108a316f59cc4381a4af4cff4d5f7452506'
ARM_WINDOWS = {
    'arm_startup': (0x10000, 0x100b8),
    'arm_tcp_socket_send': (0x12bcc, 0x12cf4),
    'arm_bsd_send': (0x12e54, 0x12f1c),
    'arm_socket_buffers': (0x13d8c, 0x13ea4),
    'arm_tcp_queue': (0x1e9a8, 0x1ec1c),
    'arm_buffer_binding': (0x1f138, 0x1f150),
    'arm_isc_send_handler': (0x2667c, 0x266e0),
    'arm_isc_dispatch': (0x268a4, 0x26b08),
}
# Reviewed instruction anchors in this exact image. These are structural checks,
# not timings, emulation results or a certification of the selected mapping.
MN_ANCHORS = {
    0x60f2efe2: 'mov\t16384,d0',
    0x60f2f006: 'cmp\t4,d3',
    0x60f2f111: 'mov\t1,d1',
    0x60f2f13a: 'mov\t2,d1',
    0x60f2f163: 'mov\t3,d1',
    0x60f308c2: 'call\t0x60f30b8c,[d2,d3,a2,a3],96',
    0x60f30931: 'call\t0x60f316b3,[a2],72',
    0x60f30c6d: 'mov\t16384,d1',
    0x60f30c73: 'mov\t16384,d2',
    0x60f30c81: 'call\t0x609ce357,[d2,d3,a2,a3],24',
    0x60f30c97: 'call\t0x60f30d40,[d2,d3,a2,a3],20',
    0x60f30ca5: 'bra\t0x60f30c47',
    0x60f30d4d: 'call\t0x60f31542,[d2,d3,a2,a3],84',
    0x60f30d65: 'sub\td0,d2',
    0x60f30d67: 'add\td0,a2',
    0x60f30d6b: 'bne\t0x60f30d49',
    0x60f313ba: 'call\t0x604314e5,[d2,d3,a2,a3],28',
    0x60f313d8: 'call\t0x604313e9,[d2,d3,a2,a3],24',
    0x60f31549: 'mov\t6,d1',
    0x60f31571: 'call\t0x60f31364,[d2,d3,a2,a3],48',
}
ARM_ANCHORS = {
    0x12c20: ('ldr', 'r8, [r6, #0x64]'),
    0x12c48: ('bl', '#0x1e9a8'),
    0x13e10: ('mov', 'r1, #0x8000'),
    0x1ea1c: ('rsb', 'r3, r3, r2'),
    0x1ea24: ('ble', '#0x1ea80'),
    0x1ea38: ('bl', '#0x35c9c'),
    0x1f140: ('str', 'r2, [r0, #0xc4]'),
    0x26690: ('bl', '#0x2bb28'),
    0x2669c: ('bl', '#0x12e54'),
    0x266a4: ('str', 'r0, [r4, #0x20]'),
    0x266bc: ('bl', '#0x1024c'),
    0x268ec: ('bl', '#0x10250'),
    0x26a78: ('movw', 'r3, #0x667c'),
    0x26a7c: ('movt', 'r3, #2'),
    0x26ad8: ('movw', 'r1, #0x6e48'),
    0x26ae0: ('movt', 'r1, #4'),
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def offsets(data, needle):
    result, pos = [], 0
    while (pos := data.find(needle, pos)) >= 0:
        result.append(pos)
        pos += 1
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--reader', type=Path, default=default_reader())
    parser.add_argument('--no-disassembly', action='store_true')
    parser.add_argument('--arm-package-dir', type=Path,
                        help='optional isolated Capstone 5.0.6 directory; see Wi-Fi report')
    args = parser.parse_args()
    out = args.out.resolve()
    if out.exists() or not out.is_relative_to((ROOT/'local').resolve()):
        raise ValueError('output must be a new directory under ignored local/')
    stock = ROOT/'firmware/OLY_E_133_1101_0000_0000.BIN'
    data = stock.read_bytes()
    if len(data) != 104552480 or sha(data) != STOCK_SHA:
        raise ValueError('wrong E-PL9 stock container')
    inventory, images = [], {}
    for name, (size, digest) in COMPONENTS.items():
        path = ROOT/'local/epl9-1101-analysis/decoded'/name
        image = path.read_bytes()
        if len(image) != size or sha(image) != digest:
            raise ValueError(f'wrong decoded E-PL9 component: {name}')
        images[name] = image
        inventory.append(dict(name=name, bytes=size, sha256=digest))
    image = images[next(iter(COMPONENTS))]
    common = images['02_0106_43ae0020.decoded.bin']
    # Nested resource directory row 9, then row 1. Container addresses only.
    if struct.unpack_from('<II', common, 9*16) != (0x455b4000, 0x400000):
        raise ValueError('common resource row 9 changed')
    if struct.unpack_from('<II', common, 0x1ad4000+16) != (0x455b5000, ARM_SIZE):
        raise ValueError('ARM resource descriptor changed')
    arm = common[ARM_START:ARM_START+ARM_SIZE]
    if sha(arm) != ARM_SHA:
        raise ValueError('ARM module identity mismatch')
    xml_offset = image.index(b'<?xml version="1.0" encoding="Shift-JIS"?>', 0xe5c000)
    xml = image[xml_offset:image.index(b'\0', xml_offset)]
    xml_root = ET.fromstring(xml.decode('shift_jis'))
    command_names = [node.attrib['name'] for node in xml_root.findall('cgi')]
    if xml_root.findtext('version').strip() != '4.00' or len(command_names) != 37:
        raise ValueError('unexpected command-list shape')
    # Literal occurrences are evidence leads, not automatic semantic xrefs.
    strings = []
    for match in re.finditer(rb'[\x20-\x7e]{4,}', image):
        text = match.group().decode('ascii')
        if re.search(r'(?i)(http|do_file|content-length|content-range|range:|accept-ranges|send_buff|tcp.*window|sndbuf)', text):
            offset = match.start()
            strings.append(dict(offset=hex(offset), address=hex(BASE+offset), text=text,
                                literal_occurrences=[hex(BASE+p) for p in offsets(image, struct.pack('<I', BASE+offset))]))
    listings = {}
    checked = {}
    if not args.no_disassembly:
        for name, (start, stop) in WINDOWS.items():
            verify_reader(args.reader)
            listings[name] = subprocess.check_output(
                [str(args.reader.resolve()), str((ROOT/'local/epl9-1101-analysis/decoded'/next(iter(COMPONENTS))).resolve()),
                 hex(BASE), hex(start-BASE), hex(stop-BASE)], text=True)
        decoded = {}
        for listing in listings.values():
            for line in listing.splitlines():
                address, raw, instruction = line.split('\t', 2)
                address = int(address, 16)
                raw = bytes.fromhex(raw)
                if image[address-BASE:address-BASE+len(raw)] != raw:
                    raise ValueError('reader bytes disagree with firmware')
                decoded[address] = instruction.rstrip()
        for address, expected in MN_ANCHORS.items():
            if decoded.get(address) != expected:
                raise ValueError(f'MN103 instruction mismatch at {address:#x}')
            checked[hex(address)] = expected
    arm_checked = {}
    if args.arm_package_dir:
        sys.path.insert(0, str(args.arm_package_dir.resolve()))
        import capstone
        if capstone.__version__ != '5.0.6':
            raise ValueError('expected isolated Capstone 5.0.6')
        md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_ARM)
        md.skipdata = True  # Dispatch tables/data are not executable instructions.
        decoded = {}
        for name, (start, stop) in ARM_WINDOWS.items():
            rows = []
            for ins in md.disasm(arm[start-ARM_BASE:stop-ARM_BASE], start):
                decoded[ins.address] = (ins.mnemonic, ins.op_str)
                rows.append(f'{ins.address:08x}\t{ins.bytes.hex()}\t{ins.mnemonic}\t{ins.op_str}')
            listings[name] = '\n'.join(rows)+'\n'
        for address, expected in ARM_ANCHORS.items():
            if decoded.get(address) != expected:
                raise ValueError(f'ARM instruction mismatch at {address:#x}')
            arm_checked[hex(address)] = expected
    # Case 6 of the ARM 16-case absolute dispatch table selects the send thunk.
    if struct.unpack_from('<I', arm, 0x269a4-ARM_BASE+5*4)[0] != 0x26a78:
        raise ValueError('ARM send dispatch target mismatch')
    out.mkdir(parents=True)
    for name, listing in listings.items():
        (out/f'{name}.tsv').write_text(listing, encoding='utf-8')
    (out/'stock-commandlist.xml').write_bytes(xml)
    report = dict(model='Olympus PEN E-PL9', owner_displayed_version='1.1', downloaded_main_build='1101',
                  installed_image_dumped=False, stock_bytes=len(data), stock_sha256=sha(data),
                  components=inventory, main_analysis_base=hex(BASE), strings=strings,
                  windows={n: [hex(a), hex(b)] for n, (a,b) in WINDOWS.items()},
                  checked_instructions=checked, arm_checked_instructions=arm_checked,
                  command_list=dict(file_offset=hex(xml_offset), bytes=len(xml), sha256=sha(xml),
                                    api_version='4.00', command_names=command_names),
                  arm_module=dict(component='0x0106', file_offset=hex(ARM_START), bytes=ARM_SIZE,
                                  sha256=ARM_SHA, analysis_base=hex(ARM_BASE),
                                  mapping_evidence='absolute dispatch table and paired MOVW/MOVT references to diagnostic strings',
                                  windows={n: [hex(a), hex(b)] for n, (a,b) in ARM_WINDOWS.items()},
                                  capstone_version='5.0.6' if args.arm_package_dir else None),
                  range_header_literals={s: offsets(image, s.encode()) for s in
                                         ['Range:', 'Content-Range:', 'Accept-Ranges:', '206 Partial Content']},
                  reader_sha256=verify_reader(args.reader) if listings else None,
                  script_sha256=sha(Path(__file__).read_bytes()), camera_accessed=False, firmware_modified=False)
    (out/'audit.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(out=str(out), verified_components=len(inventory), strings=len(strings),
                          windows=len(listings), mn103_checks=len(checked), arm_checks=len(arm_checked),
                          api_version='4.00', cgi_commands=len(command_names)), indent=2))


if __name__ == '__main__':
    main()
