"""Native capture-ring copy bounds; synthetic RAM only, no diagnostic session."""
import argparse
import json
import struct
from pathlib import Path
from epl9_workspace_bridge import ROOT, MAIN, MAIN_SHA, BASE, sha
from mn103_subset import Memory, Region, parse_listing
from mn103_calls import CallMachine


def run(out):
    if out.exists() or not out.resolve().is_relative_to((ROOT/'local').resolve()):
        raise ValueError('new ignored report required')
    image = MAIN.read_bytes()
    if sha(image) != MAIN_SHA:
        raise ValueError('stock main changed')
    listing = ROOT/'local/epl9-bounded-read-20261110/capture-copy.tsv'
    code = parse_listing(listing.read_text(encoding='utf-8-sig'), image, BASE)
    ring, dest, length, sp, end = 0x18000000, 0x18100000, 0x18200000, 0x19008000, 0x1a000000
    data = bytes(i % 251 for i in range(16384))
    rows = []
    for read, write, capacity in ((0, 0, 1), (0, 1, 2), (0, 2048, 2049),
                                   (16000, 100, 485), (0, 16383, 16384), (0, 2048, 64)):
        count = (write-read) % 16384
        backing = bytearray(b'\xa5'*16400)
        mem = Memory([Region(BASE, image), Region(ring, data), Region(dest, backing, True),
                      Region(length, bytearray(4), True), Region(sp-32768, bytearray(65536), True),
                      Region(0x6238a92c, struct.pack('<I', ring)),
                      Region(0xa2ae2448, bytearray(struct.pack('<HH', read, write)), True)])
        m = CallMachine(code, mem, dict(sp=sp, a0=dest, a1=length))
        r = m.run(m.enter(0x604d5208, end, 0xe0, 12), [end], limit=500000)
        expected = bytes(data[(read+i) % 16384] for i in range(count))+b'\0'
        if (r.get('pc') != end or m.r['sp'] != sp or backing[:count+1] != expected or
                mem.read(length, 2) != count or mem.read(0xa2ae2448, 2) != write):
            raise ValueError('native capture copy differs')
        rows.append(dict(read_cursor=read, write_cursor=write, bytes_copied=count,
                         terminator_bytes=1, declared_destination_capacity=capacity,
                         native_writes_past_declared_capacity=count+1 > capacity,
                         read_cursor_consumed=True, instructions=len(m.trace)))
    result = dict(model='E-PL9 / IM008 / 1330', build='1101', main_bytes=len(image),
                  main_sha256=sha(image), cases=rows, source_sha256=sha(Path(__file__).read_bytes()),
                  listing_sha256=sha(listing.read_bytes()),
                  response_capacity_not_an_argument=True, safe_outer_capacity_qualified=False,
                  concurrent_ring_publisher_qualified=False, physical_transport_qualified=False,
                  camera_accessed=False)
    out.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows), demonstrated_capacity_overrun=1, camera_accessed=False)))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    run(ap.parse_args().out)
