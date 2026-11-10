"""Offline OpenGate/gyro evidence for exact E-PL9 1.1/build 1101.

No camera interface, firmware mutation or patch generation. All derived bytes
and listings stay in a new directory under ignored local/. Literal matches are
leads, not semantic references. Reviewed instructions are static evidence only.
"""

from mn103_tooling import default_reader, verify_reader
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess

from epl9_color_audit import MAIN_SHA, STOCK_SHA, occurrences

ROOT = Path(__file__).resolve().parents[1]
BASE = 0x60400020
MAIN_NAME = '00_0100_406e0020.decoded.bin'
WINDOWS = {
    'geometry_selection': (0x605652eb, 0x6056546a),
    'sensor_record_selection': (0x60749150, 0x607491e9),
    'encoder_video_parameter_dump': (0x607bd6ac, 0x607bd73b),
    'encoder_progressive_parameters': (0x6169f340, 0x6169f482),
    'gyro_csv_caller': (0x60f5be89, 0x60f5beda),
    'gyro_csv': (0x60f798d3, 0x60f799fc),
    'gyro_read_write_wrappers': (0x60fa6aab, 0x60fa6af0),
    'gyro_request_builder': (0x60fa6916, 0x60fa6975),
    'gyro_diagnostic_transport': (0x60fa7870, 0x60fa7922),
    'gyro_file_helpers': (0x60fa4577, 0x60fa46c7),
    'gyro_wait_wrapper': (0x60fa7cc0, 0x60fa7cca),
}
ANCHORS = {
    0x6056532d: 'mov\t1616666200,a2',
    0x6056534b: 'cmp\t1920,d0',
    0x60565354: 'cmp\t1080,d0',
    0x60565411: 'mov\t1616666200,a2',
    0x60749173: 'cmp\t35,d1',
    0x6074917e: 'add\t1619781920,a0',
    0x607bd6b9: 'mov\t96,a2',
    0x607bd6fb: 'mov\t(16,a2),d1',
    0x607bd70b: 'mov\t(20,a2),d1',
    0x607bd71b: 'mov\t(24,a2),d1',
    0x607bd72b: 'mov\t(28,a2),d1',
    0x6169f368: 'cmp\t2160,d0',
    0x6169f395: 'cmp\t1920,d0',
    0x6169f418: 'cmp\t1280,d0',
    0x6169f456: 'mov\t(a0),d1',
    0x6169f457: 'mov\t(4,a0),d0',
    0x6169f45a: 'mov\td1,(a2)',
    0x6169f45b: 'mov\td0,(4,a2)',
    0x60f5beb2: 'call\t0x60f798d3,[d2,d3,a2],64',
    0x60f798f6: 'mov\t150,d0',
    0x60f798fb: 'call\t0x60fa6ad9,[],16',
    0x60f7990a: 'mov\t1000,d0',
    0x60f79914: 'mov\t1630540630,a0',
    0x60f79930: 'mov\tsp,a0',
    0x60f79931: 'add\t40,a0',
    0x60f79933: 'clr\td0',
    0x60f79934: 'mov\t12,d1',
    0x60f79936: 'call\t0x4700111e,[d2,a2],8',
    0x60f7994c: 'mov\t192,d0',
    0x60f79950: 'call\t0x60fa6aab,[],16',
    0x60f79962: 'movhu\td0,(40,sp)',
    0x60f79965: 'mov\t193,d0',
    0x60f79968: 'call\t0x60fa6aab,[],16',
    0x60f79977: 'movhu\td0,(42,sp)',
    0x60f7997a: 'mov\t194,d0',
    0x60f7997d: 'call\t0x60fa6aab,[],16',
    0x60f7998b: 'movhu\td0,(44,sp)',
    0x60f7998e: 'mov\t2,d0',
    0x60f79990: 'call\t0x60fa7cc0,[],4',
    0x60f799b7: 'movhu\t(46,sp),d0',
    0x60f799bd: 'movhu\t(48,sp),d0',
    0x60f799c3: 'movhu\t(50,sp),d0',
    0x60f799d6: 'mov\t150,d0',
    0x60f799d9: 'clr\td1',
    0x60fa6ab4: 'mov\t10,d0',
    0x60fa6ab9: 'call\t0x60fa6916,[d2,d3,a2,a3],52',
    0x60fa6ae1: 'mov\t9,d0',
    0x60fa6951: 'call\t0x60fa7870,[d2,d3,a2,a3],72',
    0x60fa695f: 'mov\t(20,sp),d1',
    0x60fa6966: 'mov\t(24,sp),d1',
    0x60fa78d5: 'mov\t36907,d0',
    0x60fa78e1: 'call\t0x60fa71a8,[d2,d3,a2,a3],24',
    0x60fa7cc0: 'call\t0x60f5ac3f,[],4',
}
STRINGS = {
    0x1fddea: b'         :         : 0x06:CAM_SENSOR_MODE_MOVIE_FULL(--fps)\n',
    0x50632b: b'[AVM_API] ulHsize           : ',
    0xf01336: b'GYRO_DBG.csv',
    0xf01343: b'cnt,Yaw,Pitch,Roll,X,Y,Z\r\n',
    0xf0135e: b'%d,%d,%d,%d,%d,%d,%d\r\n',
    0xe78cc5: b'MODEL_ORIENTED_DATA_IN',
    0xe79bb4: b'MDO_CONT_STAB',
}


def verified_input(path, size, digest):
    data = path.read_bytes()
    if len(data) != size or hashlib.sha256(data).hexdigest() != digest:
        raise ValueError(f'wrong exact E-PL9 input: {path.name}')
    return data


def checked_listing(listing, image, start, stop, *, base=BASE):
    """Reject holes, wrong bytes, duplicate addresses and truncated windows."""
    decoded = {}
    cursor = start
    for line in listing.splitlines():
        address, raw, instruction = line.split('\t', 2)
        address = int(address, 16)
        raw = bytes.fromhex(raw)
        off = address - base
        if (address != cursor or address >= stop or not raw
                or off < 0 or off + len(raw) > len(image)
                or image[off:off + len(raw)] != raw):
            raise ValueError(f'invalid listing at {address:#x}')
        decoded[address] = instruction.rstrip()
        cursor += len(raw)
    if cursor < stop:
        raise ValueError('incomplete listing')
    return decoded


def local_output(path):
    out = path.resolve()
    if out.exists() or not out.is_relative_to((ROOT / 'local').resolve()):
        raise ValueError('output must be a new directory under ignored local/')
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--reader', type=Path, default=default_reader())
    args = parser.parse_args()
    out = local_output(args.out)
    stock = verified_input(ROOT / 'firmware/OLY_E_133_1101_0000_0000.BIN', 104552480, STOCK_SHA)
    image_path = ROOT / 'local/epl9-1101-analysis/decoded' / MAIN_NAME
    data = verified_input(image_path, 26214336, MAIN_SHA)
    leads = []
    for offset, expected in STRINGS.items():
        if data[offset:offset + len(expected) + 1] != expected + b'\0':
            raise ValueError(f'string mismatch at {offset:#x}')
        leads.append(dict(file_offset=hex(offset), address=hex(BASE + offset),
                          text=expected.decode('ascii'), literal_occurrences=[
                              hex(BASE + p) for p in occurrences(data, struct.pack('<I', BASE + offset))]))
    tables = {}
    for address, expected in [(0x605c5dc8, (864, 648, 432)),
                              (0x605c5e10, (720, 540, 360)),
                              (0x605c5e58, (1440, 1080, 720)),
                              (0x605c5ea0, (1152, 864, 576))]:
        rows = [struct.unpack_from('<HHH', data, address - BASE + i * 6) for i in range(12)]
        if rows != [expected] * 12:
            raise ValueError('geometry triple table mismatch')
        tables[hex(address)] = rows
    # This pair is data in a dimension map; it is NOT a proven recording mode.
    if struct.unpack_from('<III', data, 0xaece34) != (1, 1920, 1440):
        raise ValueError('dimension-map row mismatch')
    if struct.unpack_from('<II', data, 0xe78f18) != (0x61278ce5, 0x902b):
        raise ValueError('diagnostic request-name association mismatch')
    if struct.unpack_from('<II', data, 0xe79cd0) != (10, 0x61279bd4):
        raise ValueError('stabilizer operation-name association mismatch')
    listings, decoded = {}, {}
    for name, (start, stop) in WINDOWS.items():
        verify_reader(args.reader)
        listing = subprocess.check_output([str(args.reader.resolve()), str(image_path.resolve()),
                                           hex(BASE), hex(start - BASE), hex(stop - BASE)], text=True)
        decoded.update(checked_listing(listing, data, start, stop))
        listings[name] = listing
    for address, expected in ANCHORS.items():
        if decoded.get(address) != expected:
            raise ValueError(f'instruction anchor mismatch at {address:#x}')
    report = dict(
        model='Olympus PEN E-PL9', model_id='1330', displayed_version='1.1', internal_main_build='1101',
        stock_bytes=len(stock), stock_sha256=STOCK_SHA, decoded_main_bytes=len(data), decoded_main_sha256=MAIN_SHA,
        analysis_base=hex(BASE), reader_sha256=verify_reader(args.reader),
        target=dict(width=1920, height=1440, fps=60, pixel_aspect='1:1', full_sensor_field_required=True,
                    full_field_readout_verified=False, recording_verified=False),
        arithmetic_only=dict(output_pixels_per_second=1920*1440*60,
                             h264_macroblocks_per_frame=120*90,
                             h264_macroblocks_per_second=120*90*60,
                             tightly_packed_8bit_yuv420_bytes_per_frame=1920*1440*3//2),
        string_leads=leads, geometry_triples_unknown_semantics=tables,
        dimension_map_row=dict(file_offset='0xaece34', values=[1, 1920, 1440], recording_binding_verified=False),
        checked_instructions={hex(a): s for a, s in ANCHORS.items()},
        windows={k: dict(start_address=hex(a), stop_address_exclusive=hex(b)) for k, (a, b) in WINDOWS.items()},
        gyro=dict(diagnostic_csv='cnt,Yaw,Pitch,Roll,X,Y,Z', timestamp_column=False,
                  read_selectors=[192, 193, 194], state_selector=150,
                  diagnostic_request='0x902b MODEL_ORIENTED_DATA_IN',
                  diagnostic_suboperation='10 MDO_CONT_STAB',
                  raw_units_verified=False, sample_rate_verified=False, video_clock_binding_verified=False,
                  note='Visible local buffer writes fill only Yaw/Pitch/Roll; X/Y/Z have no observed producer. '
                       'External callees were not executed. Do not assume accelerometer support.'),
        camera_accessed=False, firmware_modified=False, installable_patch=False,
        limits=['Static decoded windows only; no emulator or whole-image control-flow proof.',
                'No proof that named generic sensor modes work on this body.',
                'No live sensor, ISP, encoder, gyro or filesystem tests.'])
    out.mkdir(parents=True)
    for name, listing in listings.items():
        (out / f'{name}.tsv').write_text(listing, encoding='utf-8')
    (out / 'audit.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(output=str(out), checked_instructions=len(ANCHORS), windows=len(WINDOWS),
                          camera_accessed=False, firmware_modified=False), indent=2))


if __name__ == '__main__':
    main()
