"""Offline exact-image stock USB entry audit; no USB/device APIs.

Extracts pinned native windows and inventories dispatch/name tables. Camera
admission, session gates and handlers must be treated as separate layers.
"""
import argparse
import json
import struct
import subprocess
from pathlib import Path

from epl9_workspace_bridge import ROOT, MAIN, MAIN_SHA, BASE, sha
from epl9_recovery_audit import READER_SHA
from mn103_subset import parse_listing

WINDOWS = {
    'ptp-main-task': (0x60faf072, 0x60faf164),
    'ptp-support-task': (0x60faeee4, 0x60faf072),
    'ptp-api': (0x60faefa5, 0x60faf072),
    'ptp-open-api': (0x60faf23f, 0x60faf257),
    'usb-ptp-open-caller': (0x60faa2ce, 0x60faa89f),
    'usb-mode-commit': (0x60faa937, 0x60faab86),
    'ptp-setup': (0x60faf4dd, 0x60faf521),
    'diagnostic-dispatch': (0x60f51774, 0x60f51962),
    'none-dispatch': (0x60f535d8, 0x60f5473d),
    'in-dispatch': (0x60f5473d, 0x60f55674),
    'out-dispatch': (0x60f564b2, 0x60f56e54),
    'adjust-handlers': (0x60f519f1, 0x60f51ac8),
    'adjust-backends': (0x60f57596, 0x60f58216),
}
POINTERS = {'transport-marker': 0x626f5bca, 'diagnostic-gate': 0x626f3d04,
            'ptp-main-queue': 0x60421086}


def run(out, reader):
    if out.exists() or not out.resolve().is_relative_to((ROOT/'local').resolve()):
        raise ValueError('new ignored output directory required')
    image = MAIN.read_bytes()
    if sha(image) != MAIN_SHA or sha(reader.read_bytes()) != READER_SHA:
        raise ValueError('input or native reader identity differs')
    word = lambda a: struct.unpack_from('<I', image, a-BASE)[0]
    def string(a):
        at = a-BASE
        return image[at:image.index(0, at)].decode('ascii')
    out.mkdir()
    pointers = {}
    windows = dict(WINDOWS)
    for label, address in POINTERS.items():
        offsets = []; cursor = 0; needle = struct.pack('<I', address)
        while True:
            at = image.find(needle, cursor)
            if at < 0: break
            offsets.append(BASE+at); cursor = at+1
            if image[at-2] == 0xfc:
                windows[f'{label}-xref-{BASE+at:08x}'] = (BASE+at-2, BASE+at+40)
        pointers[label] = dict(address=hex(address), raw_references=[hex(a) for a in offsets])
    listings = {}
    for name, (start, end) in windows.items():
        listing = subprocess.check_output([str(reader.resolve()), str(MAIN.resolve()), hex(BASE),
                        hex(start-BASE), hex(end-BASE)], text=True)
        parse_listing(listing, image, BASE)
        p = out/(name+'.tsv'); p.write_text(listing, encoding='utf-8')
        listings[name] = dict(start=hex(start), end=hex(end), sha256=sha(p.read_bytes()))
    names = []
    for at in range(0x61278d2c, 0x61278f84, 8):
        opcode, pointer = word(at), word(at+4)
        if not BASE <= pointer < BASE+len(image): break
        names.append(dict(opcode=hex(opcode), name=string(pointer), record=hex(at)))
    dispatch = [dict(opcode=hex(word(at)+0x1001), target=hex(word(at+4)), record=hex(at))
                for at in range(0x612776d0, 0x612777d0, 8) if word(at)]
    report = dict(model='E-PL9 / IM008 / 1330', body='1.1 (owner report)', build='1101',
                  main_bytes=len(image), main_sha256=sha(image),
                  reader_bytes=reader.stat().st_size, reader_sha256=sha(reader.read_bytes()),
                  operation_names=names, dispatch_hash=dispatch, pointer_references=pointers,
                  listings=listings, source_sha256=sha(Path(__file__).read_bytes()),
                  exploratory_xrefs_are_not_a_complete_call_graph=True, camera_accessed=False)
    (out/'inventory.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(listings=len(listings), pointer_references=pointers,
                          dispatch_hash=dispatch, camera_accessed=False)))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--reader', type=Path, default=ROOT/'local/mn103-tooling/mn103-reader.exe')
    args = ap.parse_args()
    run(args.out, args.reader)
