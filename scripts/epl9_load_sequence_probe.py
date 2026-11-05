"""Native early-read chunk planning with explicit successful local storage bytes.

No NAND/DMA hardware is emulated. This tests the real alignment/chunk arithmetic
and known startup destination intervals, not runtime memory ownership.
"""
import argparse
import json
import struct
import subprocess
from pathlib import Path
from epl9_workspace_bridge import ROOT, MAIN, MAIN_SHA, BASE, sha
from epl9_placement import CANDIDATE, MODULE_SIZE, EARLY_START, EARLY_END
from epl9_deployment_probe import SECTIONS
from epl9_tonal_drafts import READER_SHA
from mn103_subset import Machine, Memory, Region, parse_listing, Fault
from mn103_calls import CallMachine

STORAGE_BASE, DESTINATION, STACK = 0x406e0020, 0xa0410000, 0x10000000


def cached(address):
    return (address & 0x3fffffff) | 0x60000000


def overlaps(start, end):
    return start < CANDIDATE+MODULE_SIZE and CANDIDATE < end


class LocalStorageRead:
    name = 'declared-local-storage-read'

    def __init__(self, image, destination, length):
        self.image, self.destination, self.length = image, destination, length
        self.calls = []

    def validate(self, m, mask, frame):
        if (mask, frame) != (0xf0, 44):
            raise Fault('unexpected early-read leaf ABI')

    def apply(self, m):
        dest, source, size = m.r['d0'], m.r['d1'], m.r['a0']
        at = source-STORAGE_BASE
        if (size <= 0 or source % 2048 or size % 2048 or
                not 0 <= at < at+size <= len(self.image) or
                not self.destination <= dest < dest+size <= self.destination+self.length):
            raise Fault('local storage read outside declared aligned bounds')
        region, offset = m.memory.region(dest, 4, write=True)
        if offset+size > len(region.data):
            raise Fault('local storage destination truncated')
        region.data[offset:offset+size] = self.image[at:at+size]
        row = dict(source=hex(source), destination=hex(dest), bytes=size, physical_read=False)
        self.calls.append(row)
        m.r['d0'] = 0
        return row


def audit(image, candidate, code):
    length = EARLY_END-EARLY_START
    data = bytearray([0xa5])*16 + bytearray([0xcd])*length + bytearray([0xa5])*16
    stack = bytearray(4096); sp = STACK+2048
    struct.pack_into('<I', stack, 2048+8, 0x406f0000)
    read = LocalStorageRead(candidate, DESTINATION, length)
    m = CallMachine(code, Memory([Region(BASE, image), Region(STACK, stack, True),
        Region(DESTINATION-16, data, True)]), dict(sp=sp, a2=DESTINATION, d2=length),
        models={0x604009bf:read, 0x60400d2f:read})
    result = m.run(0x60401561, [0x6040168b])
    if result.get('pc') != 0x6040168b or m.r['sp'] != sp:
        raise ValueError('native aligned-read planning failed: '+str(result))
    expected = candidate[EARLY_START-BASE:EARLY_END-BASE]
    if data[16:-16] != expected or data[:16]+data[-16:] != b'\xa5'*32:
        raise ValueError('native chunk reads missed/overwrote declared load bytes')
    selected = data[16+CANDIDATE-EARLY_START:16+CANDIDATE-EARLY_START+MODULE_SIZE]
    if selected != candidate[CANDIDATE-BASE:CANDIDATE-BASE+MODULE_SIZE]:
        raise ValueError('placed module did not survive native read chunks')
    # Execute argument-building fragments before each actual storage call.
    globals_ = bytearray(20)
    memory = Memory([Region(BASE, image), Region(STACK, bytearray(4096), True),
                     Region(0x6257d800, globals_, True)])
    intervals = []
    for start, stop in ((0x60400174,0x604001cb),(0x604001d0,0x604001f0),
            (0x604001f5,0x60400215),(0x6040021a,0x6040023a),
            (0x6040023f,0x6040025f),(0x60400264,0x6040027b)):
        machine = Machine(code, memory, dict(sp=sp))
        r = machine.run(start, [stop])
        if r.get('pc') != stop:
            raise ValueError('startup load argument fragment failed')
        lo = cached(machine.r['a1']); hi = lo+machine.r['d1']
        intervals.append(dict(call=hex(stop), source=hex(machine.r['a0']),
            destination=hex(machine.r['a1']), cached_start=hex(lo), cached_end=hex(hi),
            bytes=machine.r['d1'], intersects_module=overlaps(lo,hi)))
    if not intervals[0]['intersects_module'] or any(r['intersects_module'] for r in intervals[1:]):
        raise ValueError('unexpected competing early load destination')
    initializations = []
    for start, stop in ((0x6040004d,0x60400059),(0x60400068,0x60400074)):
        machine = Machine(code, memory, dict(sp=sp))
        r = machine.run(start, [stop])
        if r.get('pc') != stop:
            raise ValueError('startup initialization argument fragment failed')
        lo,hi = cached(machine.r['d0']),cached(machine.r['d1'])
        if overlaps(lo,hi):
            raise ValueError('startup initialization intersects module')
        initializations.append(dict(call=hex(stop), cached_start=hex(lo), cached_end=hex(hi)))
    if any(overlaps(a,b) for a,b in SECTIONS):
        raise ValueError('known later section load overlaps module')
    return dict(native_chunk_calls=read.calls, loaded_bytes_match=True, destination_guards_intact=True,
        module_bytes_match=True, startup_loads=intervals, startup_initialization_arguments=initializations,
        known_later_section_intervals=[[hex(a),hex(b)] for a,b in SECTIONS],
        known_startup_intervals_nonoverlapping=True, all_runtime_writers_excluded=False,
        physical_storage_and_cache_verified=False, install_ready=False)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--candidate-main', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    if args.out.exists() or not args.out.resolve().is_relative_to((ROOT/'local').resolve()):
        raise ValueError('new ignored output directory required')
    image, candidate = MAIN.read_bytes(), args.candidate_main.read_bytes()
    manifest = json.loads((args.candidate_main.parent/'manifest.json').read_text())
    module = (args.candidate_main.parent/'epl9-films-native.bin').read_bytes()
    if (sha(image) != MAIN_SHA or len(candidate) != len(image) or
            manifest['main_sha256'] != MAIN_SHA or int(manifest['module_base'],0) != CANDIDATE or
            len(module) != MODULE_SIZE or sha(module) != manifest['module_sha256']):
        raise ValueError('exact candidate/main identity required')
    expected = bytearray(image)
    expected[CANDIDATE-BASE:CANDIDATE-BASE+MODULE_SIZE] = module
    for patch in manifest['candidate_patches']:
        at = int(patch['address'],0)-BASE
        before,after = bytes.fromhex(patch['before']),bytes.fromhex(patch['after'])
        if len(before) != len(after) or expected[at:at+len(before)] != before:
            raise ValueError('hook source identity mismatch')
        expected[at:at+len(after)] = after
    if candidate != expected:
        raise ValueError('candidate contains undeclared changes')
    args.out.mkdir()
    code = {}
    reader = ROOT/'local/mn103-tooling/mn103-reader.exe'
    if sha(reader.read_bytes()) != READER_SHA:
        raise ValueError('pinned reader required')
    for name,a,b in (('startup',0x60400020,0x60400280),('chunks',0x60401561,0x6040168b)):
        listing = subprocess.check_output([str(reader),
            str(MAIN),hex(BASE),hex(a-BASE),hex(b-BASE)],text=True)
        (args.out/(name+'.tsv')).write_text(listing)
        code.update(parse_listing(listing,image,BASE))
    report = dict(main_sha256=sha(image), candidate_sha256=sha(candidate), **audit(image,candidate,code))
    report['source_sha256'] = sha(Path(__file__).read_bytes())
    report['reader_sha256'] = READER_SHA
    report['section_evidence_source_sha256'] = sha((ROOT/'scripts/epl9_deployment_probe.py').read_bytes())
    (args.out/'load-sequence.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    main()
