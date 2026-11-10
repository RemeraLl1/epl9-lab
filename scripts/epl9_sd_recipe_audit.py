"""Read-only E-PL9 SD recipe source audit; emits no patch or camera commands."""

from mn103_tooling import default_reader, verify_reader
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess

from epl9_workspace_bridge import ROOT, BASE, MAIN, MAIN_SHA
from epl9_color_audit import STOCK_SHA
from epl9_osd_audit import load_decoder, verified_bytes, OSD_SHA
from mn103_subset import parse_listing

WINDOWS = {
    'file_wrappers': (0x609ce1c8, 0x609ce98c),
    'file_open_route': (0x609cf2ed, 0x609cf72e),
    'file_classifier': (0x609dba49, 0x609dbb10),
    'file_position': (0x609de2b1, 0x609de3ae),
    'service_rpc': (0x60434a21, 0x60434c30),
    'heap': (0x60402373, 0x60402822),
    'color_consumer': (0x6079e50e, 0x6079e6a0),
    'gamma_setter': (0x6079d7a0, 0x6079d7da),
}
ANCHORS = {
    0x609ce1c9: ('call', ['0x609cf2ed', '[d2,d3,a2,a3]', '44']),
    0x609ce1e9: ('call', ['0x609dd327', '[d2,d3,a2,a3]', '32']),
    0x609ce377: ('call', ['0x609ddff6', '[d2,d3,a2,a3]', '20']),
    0x609ce3fd: ('call', ['0x609de2b1', '[a2]', '8']),
    0x609ce46b: ('call', ['0x609de2e4', '[d2,d3,a2]', '16']),
    0x609cf310: ('call', ['0x609dcdbc', '[d2,d3,a2,a3]', '96']),
    0x609cf329: ('movhu', ['(0x60420faa)', 'd0']),
    0x609cf32f: ('mov', ['65537', 'd1']),
    0x609cf336: ('call', ['0x60434a21', '[d2,d3,a2,a3]', '68']),
    0x609dba49: ('mov', ['(0x00008050)', 'd0']),
    0x609dba52: ('call', ['0x604117be', '[a2]', '4']),
    0x609dba5c: ('movhu', ['(0x60420ba4)', 'd1']),
    0x609dba67: ('call', ['0x609b176c', '[d2,d3]', '12']),
    0x609de2dd: ('mov', ['(308,a2)', 'd0']),
    0x609de305: ('cmp', ['2', 'd3']),
    0x609de309: ('cmp', ['0', 'd3']),
    0x609de30d: ('cmp', ['1', 'd3']),
    0x609de328: ('mov', ['268', 'a1']),
    0x609de331: ('mov', ['d2', '(308,a2)']),
    0x609de376: ('mov', ['268', 'a1']),
    0x60434a88: ('call', ['0x604314e5', '[d2,d3,a2,a3]', '28']),
    0x60434a9c: ('mov', ['-1', 'd1']),
    0x60434a9e: ('call', ['0x604313e9', '[d2,d3,a2,a3]', '24']),
    0x60402381: ('cmp', ['2048', 'd0']),
    0x6040238f: ('cmp', ['16384', 'd0']),
    0x6040241d: ('cmp', ['2048', 'd0']),
    0x6040242b: ('cmp', ['16384', 'd0']),
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def label_run(image, start, end, strings):
    rows = []
    for address in range(start, end, 12):
        value, kind, ident, text = struct.unpack_from('<IHHI', image, address-BASE)
        if (not value or kind != 4 or not 0 < ident < len(strings)
                or not BASE <= text < BASE+len(image) or image[text-BASE] != 0):
            raise ValueError('unexpected label-run shape')
        rows.append(dict(address=hex(address), value=hex(value), string_id=ident, text=strings[ident]))
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--listings', type=Path, help='reuse byte-checked GNU listings instead of launching the reader')
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    if args.out.exists() or not args.out.resolve().is_relative_to((ROOT/'local').resolve()):
        ap.error('output must be a new ignored local directory')
    stock = verified_bytes(ROOT/'firmware/OLY_E_133_1101_0000_0000.BIN', STOCK_SHA, 104552480)
    image = verified_bytes(MAIN, MAIN_SHA, 26214336)
    osd_path = MAIN.parent/'01_0101_421e0020.decoded.bin'
    osd_data = verified_bytes(osd_path, OSD_SHA, 26214336)
    reader = default_reader()
    verify_reader(reader)
    code, listings = {}, {}
    for name, (start, end) in WINDOWS.items():
        listing = ((args.listings/(name+'.tsv')).read_text(encoding='utf-8') if args.listings else
            subprocess.check_output([str(reader), str(MAIN), hex(BASE), hex(start-BASE), hex(end-BASE)], text=True))
        parsed = parse_listing(listing, image, BASE)
        if start not in parsed or any(not start <= pc < end for pc in parsed):
            raise ValueError('listing window mismatch')
        code.update(parsed)
        listings[name] = listing
    for pc, expected in ANCHORS.items():
        if code.get(pc, (None, None, None))[1:] != expected:
            raise ValueError(f'anchor mismatch at {pc:#x}')
    decoder = load_decoder()
    _, strings = decoder.OSD(osd_path, MAIN).strings(8)
    labels = [label_run(image, 0x61572340, 0x6157264c, strings),
              label_run(image, 0x61572da8, 0x61572f7c, strings)]
    paths = [dict(address=hex(BASE+m.start()), text=m.group()[:-1].decode('ascii'))
             for m in re.finditer(rb'C:\\[ -~]{1,92}\x00', image)]
    report = dict(model='Olympus E-PL9', displayed_version='1.1 (owner report)', downloaded_main_build=1101,
        inputs=[dict(name='stock package', bytes=len(stock), sha256=digest(stock)),
                dict(name='decoded main', bytes=len(image), sha256=digest(image)),
                dict(name='decoded OSD', bytes=len(osd_data), sha256=digest(osd_data))],
        reader_sha256=verify_reader(reader), script_sha256=digest(Path(__file__).read_bytes()),
        checked_instruction_anchors=len(ANCHORS),
        listings={k:dict(start=hex(WINDOWS[k][0]), end=hex(WINDOWS[k][1]),
                         sha256=digest(v.encode())) for k,v in listings.items()},
        file_api=dict(open='0x609ce1c8', close='0x609ce1d1', read='0x609ce357',
                      tell='0x609ce3e5', seek='0x609ce44f',
                      seek_origins=dict(current=0, end=1, absolute=2),
                      context_classifier='0x609dba49', synchronous_rpc='0x60434a21',
                      warning='API roles/origins are static control/data-flow findings; no full file operation executed'),
        matched_label_runs=labels, stock_c_drive_paths=paths,
        label_count_note='These are contiguous label records, including aliases; not visible or free slot counts',
        context_note='Classifier reads CPU/task state; ordinary task route uses synchronous file-service RPC and an indefinite reply wait',
        camera_accessed=False, firmware_modified=False, firmware_container_created=False,
        native_execution_performed=False, physical_sd_and_new_trigger_qualified=False)
    args.out.mkdir(parents=True)
    for name, listing in listings.items():
        (args.out/(name+'.tsv')).write_text(listing, encoding='utf-8')
    (args.out/'audit.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(anchors=len(ANCHORS), label_records=[len(x) for x in labels],
                         path_literals=len(paths), camera_accessed=False)))


if __name__ == '__main__':
    main()
