"""Audit ART service dependencies; bounded component execution, no camera access."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess

from epl9_art_routing_probe import BASE, ROOT, MAIN_SHA, STOCK_SHA
from epl9_offline_prototype import machine, JOB, SP, OBJECT, TABLE, CONTEXT
from mn103_subset import Region, parse_listing

WINDOWS = {
    'ordinary_entry': (0x60751319, 0x60751577),
    'long_entries': (0x607518c5, 0x6075199d),
    'long_worker': (0x607638cf, 0x607639b9),
    'table_reference_count': (0x6074b4da, 0x6074b4f8),
    'wait_and_cleanup': (0x6074edd9, 0x6074eec9),
    'wait_core': (0x6074af9e, 0x6074b090),
    'service_dispatch': (0x6073eab3, 0x6073eaca),
    'kind14_request': (0x6074bae2, 0x6074bb0a),
    'postprocess': (0x60750c2e, 0x60750ee3),
    'owner_callback': (0x607cfe8d, 0x607cffc7),
    'owner_callback2': (0x609a836f, 0x609a84d1),
    'owner_callback3': (0x607d16c7, 0x607d173a),
    'owner_assignment': (0x607ce515, 0x607ce5ae),
}
ANCHORS = {
    0x6074b4df: 'movhu\t(a1),d0', 0x6074b4e1: 'inc\td0',
    0x6074b4e4: 'mov\t(15408,a0),a0', 0x6074b4f1: 'add\t-1,d0',
    0x6074edec: 'mov\t1000,d0', 0x6074edef: 'call\t0x6074b125,[d2,a2],12',
    0x6074ee04: 'mov\t(a2),d0', 0x6074ee05: 'call\t0x6074aef3,[d2,d3,a2],16',
    0x6074ee2f: 'mov\t22,d0', 0x6074eebe: 'call\t0x6074edd9,[d3,a2,a3],28',
    0x6073eac4: 'calls\t(a3)', 0x6076398a: 'mov\t31,d0',
    0x6074baf3: 'mov\t14,d0', 0x6074baf8: 'mov\ta3,(24,sp)',
    0x6074bafa: 'mov\td2,(28,sp)', 0x6074bafc: 'mov\td3,(32,sp)',
    0x60751557: 'call\t0x60761b6a,[d2,d3,a2,a3],16',
    0x60763943: 'call\t0x60761b6a,[d2,d3,a2,a3],16',
    0x60750ed4: 'call\t0x6076199b,[d2,d3,a2,a3],80',
    0x607ce53a: 'mov\t1618804365,d0',
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def exercise(image, code):
    results = []
    for initial in [0, 1, 7, 65534]:
        obj = bytearray(15432)
        struct.pack_into('<I', obj, 15408, TABLE)
        struct.pack_into('<H', obj, 15428, initial)
        before = bytes(obj)
        m = machine(image, code, [Region(OBJECT, obj, True)], {'a0': OBJECT})
        acquire = m.run(0x6074b4da)
        require(acquire['status'] == 'retf_boundary' and m.r['a0'] == TABLE, 'acquire result')
        expected = bytearray(before)
        struct.pack_into('<H', expected, 15428, initial + 1)
        require(obj == expected, 'acquire changed unrelated data')
        m = machine(image, code, [Region(OBJECT, obj, True)], {'a0': OBJECT})
        release = m.run(0x6074b4eb)
        require(release['status'] == 'retf_boundary' and obj == before, 'balanced release')
        results.append(dict(test='balanced_reference_count', initial=initial, acquire=acquire, release=release))
    for index, pending in [(0, 0), (1, 0), (1, OBJECT)]:
        job = bytearray(14552)
        struct.pack_into('<H', job, 10388, index)
        struct.pack_into('<I', job, 10068, pending)
        before = bytes(job)
        m = machine(image, code, [Region(JOB, job, True)], {'a0': JOB})
        result = m.run(0x6074ee9c)
        if pending:
            require(result['pc'] == 0x6074eebe and m.r['a0'] == OBJECT, 'pending completion boundary')
        else:
            require(result['status'] == 'ret_boundary' and m.r['d0'] == 0, 'empty completion result')
        require(bytes(job) == before, 'unexpected pre-call mutation')
        results.append(dict(test='previous_entry_completion_boundary', index=index, pending=pending, result=result))
    # Begin after the diagnostic logging call; this is not the whole callback.
    for owner_status in [0, 1]:
        context = bytearray(256)
        context[195] = owner_status
        m = machine(image, code, [Region(CONTEXT, context)], {'a2': CONTEXT})
        m.memory.write(SP + 20, 31, 1)
        m.memory.write(SP + 12, CONTEXT + 195, 4)
        result = m.run(0x607cfee9)
        require(result['pc'] == 0x607cffc4 and result['status'] == 'ret_boundary'
                and m.r['d0'] == owner_status, 'event 31 did not return owner state')
        results.append(dict(test='owner_event31_after_logging', owner_status=owner_status, result=result))
    for callback in [0, 0x607cfe8d]:
        job = bytearray(16)
        struct.pack_into('<II', job, 4, callback, CONTEXT)
        m = machine(image, code, [Region(JOB, job)], {'a0': JOB+4, 'a1': SP+4, 'd0': 31})
        result = m.run(0x6073eab3)
        if callback:
            require(result['status'] == 'calls_boundary' and m.r['a3'] == callback
                    and m.r['a0'] == SP+4 and m.r['a1'] == CONTEXT and m.r['d0'] == 31,
                    'owner callback arguments')
        else:
            require(result['status'] == 'ret_boundary' and m.r['d0'] == 1, 'absent callback result')
        results.append(dict(test='callback_dispatch_boundary', callback=callback, result=result))
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', type=Path, default=ROOT/'local/epl9-1101-analysis/decoded/00_0100_406e0020.decoded.bin')
    parser.add_argument('--reader', type=Path, default=ROOT/'local/mn103-tooling/mn103-reader.exe')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    require(not args.out.exists() and args.out.resolve().is_relative_to((ROOT/'local').resolve()),
            'output must be a new ignored local directory')
    image = args.image.read_bytes()
    require(len(image) == 26214336 and hashlib.sha256(image).hexdigest() == MAIN_SHA, 'wrong E-PL9 main')
    code, text, listings = {}, {}, {}
    for name, (start, stop) in WINDOWS.items():
        listing = subprocess.check_output([str(args.reader.resolve()), str(args.image.resolve()),
                    hex(BASE), hex(start-BASE), hex(stop-BASE)], text=True)
        code.update(parse_listing(listing, image, BASE))
        for line in listing.splitlines():
            address, _, instruction = line.split('\t', 2)
            text[int(address, 16)] = instruction.rstrip()
        listings[name] = listing
    for address, expected in ANCHORS.items():
        require(text.get(address) == expected, f'instruction mismatch at {address:#x}')
    event31_row = 0x6090b550 + (31-2)*4
    event31_target = struct.unpack_from('<I', image, event31_row-BASE)[0]
    require(event31_target == 0x607cffc0, 'event 31 target mismatch')
    cases = exercise(image, code)
    args.out.mkdir(parents=True)
    for name, listing in listings.items():
        (args.out/f'{name}.tsv').write_text(listing, encoding='utf-8')
    report = dict(model='E-PL9', owner_displayed_version='1.1', downloaded_main_build='1101',
                  stock_bytes=104552480, stock_sha256=STOCK_SHA,
                  stock_note='Identity from initial audit; only decoded main read here.',
                  main_bytes=len(image), main_sha256=MAIN_SHA, analysis_base=hex(BASE),
                  reader_sha256=hashlib.sha256(args.reader.read_bytes()).hexdigest(),
                  script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  subset_sha256=hashlib.sha256((ROOT/'scripts/mn103_subset.py').read_bytes()).hexdigest(),
                  windows={n: [hex(a), hex(b)] for n, (a,b) in WINDOWS.items()},
                  checked_instructions={hex(a): i for a,i in ANCHORS.items()},
                  event31=dict(row=hex(event31_row), target=hex(event31_target)), cases=cases,
                  camera_accessed=False, firmware_modified=False,
                  limits=['CALL/RET boundaries remain; no integrated processing or hardware execution.',
                          'No proof all callers use this owner callback; callbacks can be supplied by callers.',
                          'No pixel transfer, wait completion, real buffer lifetime or preview/capture validation.'])
    (args.out/'audit.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(out=str(args.out), instruction_checks=len(ANCHORS), component_cases=len(cases),
                          event31=report['event31']), indent=2))


if __name__ == '__main__':
    main()
