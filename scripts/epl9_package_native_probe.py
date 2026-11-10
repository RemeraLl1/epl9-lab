"""Full-size E-PL9 package checks with native outer control flow and guarded writes.

Three byte-pinned repetitive loops are accelerated, then their final iteration
runs natively. Small cases compare the entire register/flag/RAM state against
unaccelerated execution. No unconditional validation-success model is used.
The flash entry is a RAM-only trap; no device or storage API is invoked.
"""

from mn103_tooling import default_reader, verify_reader
import argparse
import json
from pathlib import Path
import struct

from epl9_recovery_audit import ROOT, BASE, BUFFER, STACK, SP, RESULT, RETURN, Boundary, fixture, load_code, inspect_package, decoded_payload, sha, MAIN_NAME, MAIN_SHA, ORDER
from epl9_v3_package import sum32, INVERT, generation_inputs, component
from mn103_subset import Region, Memory, Fault
from mn103_calls import CallMachine

# Exact decoded loop ranges are validated against live disassembly of the pinned main.
LOOPS = {0x6100397e: (0x610039e7, 'permute16'),
         0x610039ef: (0x610039f9, 'invert32'),
         0x604d54c5: (0x604d54cd, 'sum32')}


def span(m, address, size, writable=False):
    if size <= 0 or address % 4 or size % 4 or not BUFFER <= address < address+size <= BUFFER+m.package_size:
        raise Fault('bulk access outside bounded aligned package bytes')
    for region in m.memory.regions:
        if region.address <= address and address+size <= region.address+len(region.data):
            if writable and not region.writable:
                raise Fault('bulk write to read-only region')
            return region, address-region.address
    raise Fault('bulk range is unmapped')


class LoopMachine(CallMachine):
    def run(self, start, stops=(), limit=300000):
        pc, beginning = start, len(self.trace)
        stops = set(stops)
        while True:
            used = len(self.trace)-beginning
            if used >= limit:
                raise Fault('outer native instruction limit')
            result = super().run(pc, stops=stops | set(LOOPS), limit=limit-used)
            pc = result.get('pc')
            if pc in stops or pc not in LOOPS:
                return result
            end, name = LOOPS[pc]
            count = self.memory.read(self.r['sp'], 4) if name == 'permute16' else self.r['d0']
            if not 1 <= count <= m_max_iterations(self.package_size, name):
                raise Fault('invalid counted loop extent')
            if self.loop != pc:
                raise Fault('unexpected native loop-buffer address')
            n = count-1  # Native final iteration preserves exact flags/registers/stack effects.
            if n:
                address = self.r['a1'] if name == 'permute16' else self.r['a0']
                length = n*(16 if name == 'permute16' else 4)
                region, at = span(self, address, length, name != 'sum32')
                before = bytes(region.data[at:at+length])
                if name == 'permute16':
                    after = bytearray(length)
                    for i, j in enumerate(ORDER):
                        after[i::16] = before[j::16]
                    region.data[at:at+length] = after
                    self.r['a1'] += length
                    self.memory.write(self.r['sp'], 1, 4)
                elif name == 'invert32':
                    region.data[at:at+length] = before.translate(INVERT)
                    self.r['a0'] += length
                    self.r['d0'] = 1
                else:
                    self.r['d2'] = (self.r['d2']+sum32(before)) & 0xffffffff
                    self.r['a0'] += length
                    self.r['d0'] = 1
                self.events.append(dict(op='bulk_loop', loop=hex(pc), name=name,
                    iterations_accelerated=n, bytes=length, input_sha256=sha(before),
                    final_iteration_native=True))
            result = super().run(pc, stops=stops | {end}, limit=1000)
            if result.get('pc') != end:
                raise Fault('native final loop iteration failed: '+str(result))
            pc = end


def m_max_iterations(size, name):
    return size//(16 if name == 'permute16' else 4)


def translated_address(address):
    """Measured 60445069 mapping; OSD 421e0000 stays unchanged, main maps to 806e0000."""
    if 0x40000000 <= address < 0x41000000 or 0x60000000 <= address < 0x80000000:
        return (address & 0x3fffffff) | 0x80000000
    return address


def expected_requests(rows):
    by_kind = {row['kind']: row for row in rows}
    if set(by_kind) != {'0x100', '0x101'} or len(rows) != 2:
        raise ValueError('this native probe qualifies exactly main and OSD')
    # Native selection writes resources before main, irrespective of container order.
    return [by_kind[k] for k in ('0x101', '0x100')]


class FlashTrap(Boundary):
    def apply(self, m):
        source, length = m.r['a1'], m.r['d0']
        region, at = span(m, source, length)
        raw = bytes(region.data[at:at+length])
        kind = struct.unpack_from('<H', raw, 20)[0]
        result = (self.backend_result.get(kind, 0) if isinstance(self.backend_result, dict)
                  else self.backend_result)
        detail = dict(destination=hex(m.r['a0']), source=hex(source), bytes=length,
            mode=m.r['d1'], kind=hex(kind),
            decoded_envelope_sha256=sha(raw), decoded_payload_sha256=sha(raw[32:-32]),
            checksum=sum32(raw), injected_result=result, physical_write=False)
        m.r['d0'] = result
        return detail


def execute(image, code, package, *, fast=True, mode=0, backend_result=0):
    if not package or mode not in (0, 1, 2):
        raise ValueError('invalid package/mode')
    models = {0x60401fcc: Boundary('diagnostic', [(0x30, 28)]),
        0x6040227a: Boundary('diagnostic-number', [(0xa0, 40)]),
        0x605c99f4: Boundary('progress-notification', [(0xf0, 72)]),
        0x605c9b0f: Boundary('error-notification', [(0xf0, 64)]),
        0x604a0f8b: FlashTrap('flash-request-trap', [(0xf0, 36)], backend_result)}
    regions = [Region(BASE, image, False, 'executing main'),
        Region(BUFFER-16, bytearray(b'\xa5'*16+package+b'\xa5'*16), True, 'guarded package'),
        Region(STACK, bytearray(0x10000), True, 'caller stack'),
        Region(RESULT, bytearray(16), True, 'caller result')]
    m = (LoopMachine if fast else CallMachine)(code, Memory(regions),
        dict(sp=SP, d0=len(package), d1=mode, a0=BUFFER, a1=RESULT), models=models)
    m.package_size = len(package)
    m.enter(0x6100440a, RETURN, 0xf0, 16)
    stop = m.run(0x6100440a, stops={RETURN}, limit=300000)
    if stop.get('pc') != RETURN or m.r['sp'] != SP:
        raise Fault('native updater did not return: '+str(stop))
    if regions[1].data[:16]+regions[1].data[-16:] != b'\xa5'*32:
        raise Fault('native updater escaped package guards')
    after = bytes(regions[1].data[16:-16])
    report = dict(mode=mode, input_bytes=len(package), input_sha256=sha(package),
        output_sha256=sha(after), return_value=hex(m.r['d0']), instructions_executed=len(m.trace),
        backend_requests=[e for e in m.events if e.get('model') == 'flash-request-trap'],
        accelerated_loops=[e for e in m.events if e.get('op') == 'bulk_loop'],
        package_guards_intact=True, stack_balanced=True, physical_writes=False)
    state = (dict(m.r), (m.n, m.z, m.c, m.v), m.loop,
             tuple(bytes(r.data) for r in regions[1:]),
             [e for e in m.events if e.get('op') != 'bulk_loop'])
    return report, after, state


def crosscheck_loops(image, code):
    rows = []
    for size in (16, 32, 80, 256, 4096):
        for damaged in (False, True):
            package = bytearray(fixture(size=size))
            if damaged:
                package[32+size//2] ^= 0x51
            native = execute(image, code, bytes(package), fast=False)
            accelerated = execute(image, code, bytes(package))
            if native[2] != accelerated[2] or native[1] != accelerated[1]:
                raise ValueError(f'bulk/native state mismatch: {size}, damaged={damaged}')
            rows.append(dict(payload_bytes=size, damaged=damaged,
                return_value=native[0]['return_value'], native_instructions=native[0]['instructions_executed'],
                accelerated_instructions=accelerated[0]['instructions_executed'],
                registers_flags_loop_stack_result_package_events_equal=True))
    return rows


def run(out, packages):
    out = out.resolve()
    if out.exists() or not out.is_relative_to((ROOT/'local').resolve()):
        raise ValueError('new ignored output directory required')
    image = (ROOT/'local/epl9-1101-analysis/decoded'/MAIN_NAME).read_bytes()
    if sha(image) != MAIN_SHA:
        raise ValueError('wrong stock main')
    package_manifest = json.loads((packages/'manifest.json').read_text())
    out.mkdir()
    reader = default_reader()
    code = load_code(image, out, reader)
    checks = crosscheck_loops(image, code)
    (out/'loop-crosschecks.json').write_text(json.dumps(checks, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(native_bulk_crosschecks=len(checks))), flush=True)
    generation = package_manifest.get('generation', 'frozen-v3')
    _, _, hashes, candidate_name = generation_inputs(generation)
    if [r['file'] for r in package_manifest['files']] != [candidate_name, 'Stock-1101-main-osd-restore.bin']:
        raise ValueError('requires exactly the selected candidate and stock return pair')
    candidate_bytes = (packages/candidate_name).read_bytes()
    candidate_item = package_manifest['files'][0]
    if len(candidate_bytes) != candidate_item['bytes'] or sha(candidate_bytes) != candidate_item['sha256']:
        raise ValueError('candidate file identity changed')
    candidate_rows = inspect_package(candidate_bytes)
    if {int(r['kind'],16):r['decoded_sha256'] for r in candidate_rows} != hashes or len(candidate_rows)!=2:
        raise ValueError('wrong executing candidate components')
    candidate_main = decoded_payload(component(candidate_bytes,candidate_rows[0])[32:-32])
    # The loaded native validator instructions must also be unchanged in candidate main.
    if any(candidate_main[pc-BASE:pc-BASE+len(op[0])] != op[0] for pc, op in code.items()):
        raise ValueError('candidate changes a native validator instruction')
    results = []
    for item in package_manifest['files']:
        raw = (packages/item['file']).read_bytes()
        if len(raw) != item['bytes'] or sha(raw) != item['sha256']:
            raise ValueError('package file identity changed')
        rows = inspect_package(raw)
        write_rows = expected_requests(rows)
        executing = image if 'candidate' in item['file'] else candidate_main
        for mode in (0, 2):
            observed, decoded, _ = execute(executing, code, raw, mode=mode)
            if observed['return_value'] != '0x0':
                raise ValueError('native full-size validation failed: '+str(observed))
            expected = b''.join(raw[int(row['offset'],16):int(row['offset'],16)+32] +
                decoded_payload(raw[int(row['offset'],16)+32:int(row['offset'],16)+row['package_bytes']-32]) +
                raw[int(row['offset'],16)+row['package_bytes']-32:int(row['offset'],16)+row['package_bytes']]
                for row in rows)
            if decoded != expected:
                raise ValueError('full-size native decoding differs from host')
            requests = observed['backend_requests']
            if len(requests) != (2 if mode == 0 else 0):
                raise ValueError('unexpected write-request count')
            for request, row in zip(requests, write_rows):
                if (request['kind'] != row['kind'] or request['bytes'] != row['package_bytes'] or
                        request['decoded_payload_sha256'] != row['decoded_sha256'] or request['checksum'] != 0 or
                        int(request['destination'],16) != translated_address(int(row['destination'],16))):
                    raise ValueError('native write request differs from intended component')
            results.append(dict(file=item['file'], executing_main_sha256=sha(executing), **observed))
            print(json.dumps(dict(file=item['file'], mode=mode, result=observed['return_value'],
                                  trapped_requests=len(requests))), flush=True)
            if mode == 2:
                committed, _, _ = execute(executing, code, decoded, mode=1)
                if committed['return_value'] != '0x0' or len(committed['backend_requests']) != 2:
                    raise ValueError('check/commit sequence failed')
                if [(x['destination'],x['bytes'],x['decoded_payload_sha256']) for x in committed['backend_requests']] != [
                    (hex(translated_address(int(r['destination'],16))),r['package_bytes'],r['decoded_sha256']) for r in write_rows]:
                    raise ValueError('commit target/payload mismatch')
                results.append(dict(file=item['file'], executing_main_sha256=sha(executing), **committed))
        for label, offset in [('corrupt-first', 48), ('corrupt-second', int(rows[1]['offset'],16)+48)]:
            damaged = bytearray(raw)
            damaged[offset] ^= 1
            negative, _, _ = execute(executing, code, bytes(damaged))
            if negative['return_value'] != '0x3211' or negative['backend_requests']:
                raise ValueError('corruption did not reject the entire package before writes')
            results.append(dict(file=item['file'], negative_control=label, **negative))
        for label, injected, expected_return in (
                ('both-writes-report-error', 0x3105, '0x3105'),
                ('osd-error-main-success', {0x101: 0x3105}, '0x0'),
                ('osd-success-main-error', {0x100: 0x3105}, '0x3105')):
            failure, _, _ = execute(executing, code, raw, backend_result=injected)
            if (failure['return_value'] != expected_return or
                    [r['kind'] for r in failure['backend_requests']] != ['0x101', '0x100']):
                raise ValueError('native multi-component error propagation differs from observed contract')
            results.append(dict(file=item['file'], negative_control=label,
                continued_after_osd_failure=label != 'osd-success-main-error',
                earlier_component_error_masked=label == 'osd-error-main-success', **failure))
    report = dict(schema='epl9-full-size-native-package-probe-v1', generation=generation,
        candidate_main_from_exact_package=True, candidate_main_sha256=sha(candidate_main),
        package_manifest_sha256=sha((packages/'manifest.json').read_bytes()),
        source_sha256=sha(Path(__file__).read_bytes()), reader_sha256=verify_reader(reader),
        loop_windows={hex(a):dict(end=hex(b),name=n,sha256=sha(image[a-BASE:b-BASE])) for a,(b,n) in LOOPS.items()},
        native_loop_crosschecks=checks, cases=results,
        scope='Native outer validator/selection control flow; three crosschecked bulk loops; writes trapped',
        native_write_order=['0x101', '0x100'],
        earlier_component_write_error_can_be_masked=True,
        accelerated=True, camera_accessed=False, physical_writes=False, physical_restore_verified=False,
        lower_writer_executed=False, install_ready=False)
    (out/'validation.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(out=str(out), full_size_cases=len(results), physical_writes=False)), flush=True)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--packages', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    run(args.out, args.packages)
