"""Execute three stock event-2 owners, including native readiness and logging gates.

All owner/RTOS/registry state is declared synthetic data. No callback or logger
is modeled as a successful return. Enabled output logging and invalid handles
remain explicit stops. This is not a camera concurrency or pixel test.
"""
import argparse
import json
import struct
import subprocess
from pathlib import Path

from epl9_workspace_bridge import ROOT, MAIN, MAIN_SHA, BASE, sha
from epl9_film_late_probe import prepare_probe
from epl9_job_probe import experiment, OWNER_CALLBACK
from epl9_lifecycle_probe import Lifecycle
from epl9_wb_math_probe import extend
from mn103_calls import CallMachine
from mn103_subset import Memory, Region, parse_listing, Fault

CONTEXT, STATE, OBJECT, COEFFICIENTS = 0x2c000000, 0x2c001000, 0x2c002000, 0x2c004000
TASK_ROOT, TASK_FLAGS, TASK_LINK, TASK_RECORD = 0x2c005000, 0x2c006000, 0x2c007000, 0x2c008000
SP, END = 0x1d004000, 0x1e000000
CALLBACKS = {'primary': 0x607cfe8d, 'primary_wrapper': 0x607d16c7, 'secondary': 0x609a836f}
WINDOWS = {
    'primary': (0x607cfe8d, 0x607cffc7),
    'primary_matrix': (0x607d0aa7, 0x607d0b25),
    'primary_wrapper': (0x607d16c7, 0x607d173a),
    'primary_log': (0x607cc266, 0x607cc524),
    'current_task': (0x604117be, 0x60411802),
    'secondary': (0x609a836f, 0x609a84e7),
    'secondary_lookup': (0x609a9390, 0x609a93fe),
    'secondary_registry': (0x6068758f, 0x606875d5),
    'secondary_log': (0x609a5e9f, 0x609a608e),
}


def load_owners(image, out):
    if sha(image) != MAIN_SHA:
        raise ValueError('exact E-PL9 1101 main required')
    code = {}
    for name, (start, end) in WINDOWS.items():
        listing = subprocess.check_output([str(ROOT/'local/mn103-tooling/mn103-reader.exe'),
            str(MAIN), hex(BASE), hex(start-BASE), hex(end-BASE)], text=True)
        (out/(name+'.tsv')).write_text(listing)
        code.update(parse_listing(listing, image, BASE))
    if struct.unpack_from('<I', image, 0x6090b550-BASE)[0] != 0x607cff1b:
        raise ValueError('primary event-2 dispatch changed')
    return code


def fixture(*, ready=1, phase=16, cancelled=0, handle=1, registry_active=True,
            primary_log_mask=0, secondary_output=False):
    context = bytearray(512)
    struct.pack_into('<II', context, 0, STATE, STATE)
    struct.pack_into('<I', context, 24, phase)
    struct.pack_into('<I', context, 152, OBJECT)
    context[195] = ready
    # Secondary owner has a different context layout; patched by its caller.
    obj = bytearray([0xa5])*4200
    root, flags, link, record = bytearray(100), bytearray(2), bytearray(4), bytearray(18)
    struct.pack_into('<I', root, 28, TASK_FLAGS)
    struct.pack_into('<I', root, 96, TASK_LINK)
    struct.pack_into('<I', link, 0, TASK_RECORD)
    struct.pack_into('<H', record, 16, 31)
    registry = bytearray(26*24)
    struct.pack_into('<H', registry, 24, 4 if registry_active else 0)
    struct.pack_into('<I', registry, 24+12, OBJECT)
    secondary_log = bytearray(28)
    struct.pack_into('<I', secondary_log, 0, 4)
    struct.pack_into('<H', secondary_log, 10, int(secondary_output))
    struct.pack_into('<H', secondary_log, 24, 2 if secondary_output else 0)
    ring = bytearray(1208)
    regions = [Region(CONTEXT, context, True, 'declared owner context'),
        Region(STATE, struct.pack('<I', cancelled), False, 'declared cancellation state'),
        Region(OBJECT, obj, True, 'declared native owner object'),
        Region(0x8050, bytes(4), False, 'declared processor index zero'),
        Region(0x8ff00004, struct.pack('<I', TASK_ROOT), False, 'declared current task root'),
        Region(TASK_ROOT, root), Region(TASK_FLAGS, flags), Region(TASK_LINK, link), Region(TASK_RECORD, record),
        Region(0x6266a878, struct.pack('<H', primary_log_mask), False, 'declared primary log mask'),
        Region(0x62688280, secondary_log, False, 'declared secondary output logging flags'),
        Region(0x6261cf14, registry, False, 'declared handle registry'),
        Region(0xa2a5df00, ring, True, 'native secondary diagnostic ring')]
    return dict(regions=regions, context=context, object=obj, ring=ring, handle=handle, ready=ready)


def select_owner(state, name):
    if name == 'secondary':
        struct.pack_into('<I', state['context'], 4, state['handle'])
        state['context'][8] = state['ready']


def expected_object(values, changed):
    result = bytearray([0xa5])*4200
    if changed:
        struct.pack_into('<9H', result, 4114, *[(2*v)&65535 for v in values])
    return result


def isolated_cases(image, code):
    rows = []
    values = (126, 2, 0, 0, 129, -1, 1, 0, 127)
    coeff = struct.pack('<9h', *values)
    for name, entry in CALLBACKS.items():
        for ready in (0, 1):
            for phase in (15, 16):
                for cancelled in (0, 1):
                    state = fixture(ready=ready, phase=phase, cancelled=cancelled)
                    select_owner(state, name)
                    m = CallMachine(code, Memory([Region(BASE, image), *state['regions'],
                        Region(COEFFICIENTS, coeff), Region(SP-8192, bytearray(16384), True)]),
                        dict(sp=SP, a0=COEFFICIENTS, a1=CONTEXT, d0=2))
                    result = m.run(m.enter(entry, END), [END])
                    if result.get('pc') != END or m.r['sp'] != SP or any(e['op']=='modeled_call' for e in m.events):
                        raise ValueError(f'native owner did not return without models: {name}: {result}')
                    changed = name == 'secondary' or ready == 1 and phase == 16
                    if state['object'] != expected_object(values, changed):
                        raise ValueError('native owner readiness/copy behavior differs')
                    expected_return = (0 if cancelled else ready) if name == 'secondary' else ready
                    if m.r['d0'] != expected_return:
                        raise ValueError('owner cancellation/result behavior differs')
                    rows.append(dict(owner=name, ready=ready, phase=phase, cancelled=cancelled,
                        matrix_saved=changed, result=m.r['d0'], instructions=len(m.trace),
                        modeled_calls=0, native_log_ring_changed=any(state['ring']),
                        call_targets=sorted({hex(e['target']) for e in m.events if e['op'] in ('call','calls')})))
    # Invalid handles/output logging must not silently become successful calls.
    for name, options, boundary in (
        ('secondary_invalid_handle', dict(handle=0), 0x605f9d64),
        ('secondary_inactive_handle', dict(registry_active=False), 0x605f9d64),
        ('secondary_output_enabled', dict(secondary_output=True), 0x609a608e),
    ):
        state = fixture(**options); select_owner(state, 'secondary')
        m = CallMachine(code, Memory([Region(BASE, image), *state['regions'],
            Region(COEFFICIENTS, coeff), Region(SP-8192, bytearray(16384), True)]),
            dict(sp=SP, a0=COEFFICIENTS, a1=CONTEXT, d0=2))
        result = m.run(m.enter(CALLBACKS['secondary'], END), [END])
        # Handle zero is rejected by the callback itself before state lookup.
        if options.get('handle') == 0:
            if result.get('pc') != END or state['object'] != expected_object(values, False):
                raise ValueError('zero owner handle was not skipped')
        elif result.get('status') != 'external_call' or result.get('target') != boundary:
            raise ValueError(f'undeclared owner state did not stop at expected boundary: {name}: {result}')
        rows.append(dict(negative_control=name, outcome=result))
    return rows


class NativeEvent2:
    """Host owner adapter: other events retain their existing declared contract."""
    name = 'native-owner-event2-adapter'

    def __init__(self, previous, owner, state):
        self.previous, self.owner, self.state = previous, owner, state
        self.calls = []

    def validate(self, m, mask, frame):
        self.previous.validate(m, mask, frame)

    def apply(self, m):
        if m.r['d0'] & 255 != 2:
            return self.previous.apply(m)
        arg, sp = m.r['a0'], m.r['sp']
        values = [m.memory.read(arg+2*i, 2) for i in range(9)]
        return_pc = m.memory.read(sp, 4)
        m.r['a1'] = CONTEXT  # Explicit synthetic adapter binding, not a patch.
        start, events = len(m.trace), len(m.events)
        result = m.run(CALLBACKS[self.owner], [return_pc])
        if (result.get('pc') != return_pc or m.r['sp'] != sp or
                any(e['op']=='modeled_call' for e in m.events[events:])):
            raise Fault('native owner callback did not return without modeled calls: '+str(result))
        if self.state['object'] != expected_object(values, True):
            raise Fault('native owner did not save notified matrix')
        if [m.memory.read(arg+2*i, 2) for i in range(9)] != values:
            raise Fault('native owner changed supplied matrix')
        if any(pc in (0x6074e6eb, 0x6079fb88) for pc in m.trace[start:]):
            raise Fault('owner reentered executor/color configuration')
        self.calls.append(dict(instructions=len(m.trace)-start, native_callback=hex(CALLBACKS[self.owner]),
            coefficients=values, modeled_calls_inside_callback=0, executor_or_color_reentered=False,
            call_targets=sorted({hex(e['target']) for e in m.events[events:] if e['op'] in ('call','calls')})))
        return dict(event=2, coefficients_preserved=values, native_owner=self.owner,
                    synthetic_context_binding=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--color-controls', type=Path, required=True)
    args = ap.parse_args()
    color = json.loads(args.color_controls.read_text())
    wb = json.loads((ROOT/'recipes/epl9-native-wb-trial-v1.json').read_text())
    image, patched, _, code, module, manifest = prepare_probe(args.out, base=0x604a1300,
        color_document=color, wb_document=wb, diagnostic_rgb=True)
    owner_code = load_owners(image, args.out)
    isolated = isolated_cases(image, owner_code)
    code.update(owner_code)
    extend(image, code)
    rows = []
    for name in CALLBACKS:
        for key in (0x01010078, 0x01020078):
            for kind in (0x200, 0x100, 0x40):
                state = fixture(); select_owner(state, name)
                observer = Lifecycle(module['base'])
                adapters = []
                def attach(m):
                    observer(m)
                    if m.memory.read(0x8050, 4) != 0:
                        raise ValueError('connected fixture requires processor index zero')
                    m.memory = Memory([*m.memory.regions, *[r for r in state['regions'] if r.address != 0x8050]])
                    adapter = NativeEvent2(m.models[OWNER_CALLBACK], name, state)
                    m.models[OWNER_CALLBACK] = adapter; adapters.append(adapter)
                opts = dict(provide_slot=True, input_format=0x100) if kind == 0x40 else {}
                r = experiment(patched, code, key, kind, 0, native_module=module,
                    gain_fixture=(1024,)*4, machine_observer=attach, **opts)
                calls = adapters[0].calls
                if not calls or any(c['coefficients'] != r['native_film']['matrix_words'] for c in calls):
                    raise ValueError('native owner / ISP matrix mismatch')
                if not observer.restored or observer.pending or r['output_changed'] or r['event_bits_signalled']:
                    raise ValueError('restoration failed or fabricated pixels/completion')
                expected = "0x6073eafa mov ['d0', '(0x9880014c)']: unmapped access at 0x9880014c, size 4"
                if r['executor'].get('error') != expected:
                    raise ValueError('unexpected connected boundary: '+str(r['executor']))
                rows.append(dict(owner=name, key=hex(key), kind=hex(kind), calls=calls,
                    native_owner_matrix_matches_isp=True, stack=observer.result(), restored=observer.restored,
                    boundary=r['executor']))
    report = dict(main_sha256=sha(image), module=manifest, isolated=isolated, connected=rows,
        declared_state='valid current task and registry; external log output disabled; native secondary ring active',
        camera_state_measured=False, same_job_reentry_excluded=False, irq_scheduling_verified=False,
        full_pixel_cycle_passed=False, install_ready=False,
        sources={p:sha((ROOT/'scripts'/p).read_bytes()) for p in
            ('epl9_owner_callback_probe.py','epl9_lifecycle_probe.py','epl9_film_late_probe.py',
             'epl9_job_probe.py','epl9_deployment_probe.py','epl9_float_contract.py','epl9_wb_math_probe.py',
             'mn103_calls.py','mn103_subset.py')})
    (args.out/'owners.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(isolated=len(isolated), connected=len(rows),
        max_stack=max(r['stack']['observed_stack_depth'] for r in rows), native_owners=list(CALLBACKS)), indent=2))


if __name__ == '__main__':
    main()
