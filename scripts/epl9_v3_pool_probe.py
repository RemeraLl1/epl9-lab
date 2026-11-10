"""Native deallocation classifiers versus the placed module's address aliases.

This excludes seven classified pool intervals, not every runtime memory writer.
Stops before any deallocation, logging, kernel or hardware operation.
"""
import argparse
import json
import struct
from pathlib import Path
from epl9_workspace_bridge import ROOT, MAIN, MAIN_SHA, BASE, sha
from epl9_placement import CANDIDATE, MODULE_SIZE
from mn103_subset import Machine, Memory, parse_listing

# Entry, accepted branch, rejected branch, validated interval and pool ID.
POOLS = [
    (0x604023b2,0x604023fa,0x60402401,0x61f01fc0,0x61faffc0,0x10001),
    (0x604023b2,0x604023fa,0x60402401,0x62267000,0x6237f800,0x10002),
    (0x604023b2,0x604023fa,0x60402401,0x61fb8540,0x621ba540,0x10004),
    (0x6040244e,0x60402496,0x6040249d,0xa1faffc0,0xa1fb8540,0x20001),
    (0x6040244e,0x60402496,0x6040249d,0xa237f800,0xa238a540,0x20002),
    (0x6040244e,0x60402496,0x6040249d,0xa21ba540,0xa2267000,0x20004),
    (0x604024ce,0x604024e6,0x604024ed,0xa2bc0500,0xa2bc5000,0x40001),
]


def run(out, listing):
    if out.exists() or not out.resolve().is_relative_to((ROOT/'local').resolve()):
        raise ValueError('new ignored report required')
    image = MAIN.read_bytes()
    if sha(image) != MAIN_SHA:
        raise ValueError('stock identity differs')
    code = parse_listing(listing.read_text(encoding='utf-8-sig'), image, BASE)
    memory = Memory([])

    def classify(address, entry, yes, no):
        m = Machine(code, memory, dict(a0=address))
        result = m.run(entry, [yes, no])
        if result.get('pc') not in (yes, no):
            raise ValueError('classifier reached undeclared operation')
        return result['pc'] == yes, m.r['d0']

    positive = []
    for entry, yes, no, start, end, ident in POOLS:
        for address in (start, end-1):
            valid, selected = classify(address, entry, yes, no)
            if not valid or selected != ident:
                raise ValueError('native pool boundary differs')
            positive.append(dict(address=hex(address), pool_id=hex(ident)))
    aliases = [CANDIDATE, (CANDIDATE & 0x3fffffff)|0x80000000]
    rejected = 0
    for start in aliases:
        for address in range(start, start+MODULE_SIZE, 4):
            for entry, yes, no in sorted({r[:3] for r in POOLS}):
                valid, _ = classify(address, entry, yes, no)
                if valid:
                    raise ValueError('placed module accepted as pool storage')
                rejected += 1
    table = []
    for at in range(0x60405f10, 0x60405f80, 16):
        start, block, count, marker = struct.unpack_from('<4I', image, at-BASE)
        pool, = [r for r in POOLS if r[3] == start]
        if pool[4]-start != (block+64)*count:
            raise ValueError('ROM table differs from classified interval')
        lo, hi = start & 0x3fffffff, pool[4] & 0x3fffffff
        mod = CANDIDATE & 0x3fffffff
        if lo < mod+MODULE_SIZE and mod < hi:
            raise ValueError('pool aliases overlap module')
        table.append(dict(table=hex(at), start=hex(start), end=hex(pool[4]),
            block_bytes=block, block_count=count, marker=hex(marker), pool_id=hex(pool[5])))
    report = dict(main_sha256=sha(image), listing_sha256=sha(listing.read_bytes()),
        source_sha256=sha(Path(__file__).read_bytes()), pool_intervals=table,
        native_boundary_controls=positive, module_word_addresses_rejected=rejected,
        aliases=[hex(a) for a in aliases], classified_pool_overlap=False,
        module_bytes=MODULE_SIZE, all_runtime_writers_excluded=False,
        runtime_pool_metadata_measured=False, cache_execution_verified=False,
        deallocation_or_hardware_executed=False, install_ready=False)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(pool_intervals=7, boundary_controls=len(positive),
        rejected_word_checks=rejected, classified_pool_overlap=False)))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--listing', type=Path, required=True)
    args = ap.parse_args()
    run(args.out, args.listing)
