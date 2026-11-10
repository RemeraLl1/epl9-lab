"""Bounded E-PL9 diagnostic initialization/teardown with explicit service models.

No device access. Synthetic queue replies, allocations and event results are
fault-injection fixtures, not a working diagnostic session or lens emulator.
"""
import argparse
import json
import struct
from pathlib import Path

from epl9_workspace_bridge import ROOT, MAIN, MAIN_SHA, BASE, sha
from epl9_recovery_audit import Boundary
from mn103_subset import Memory, Region, parse_listing
from mn103_calls import CallMachine

SP, HEAP, END = 0x18008000, 0x19000000, 0x1a000000
PENDING, READY = 0x626155a0, 0xa2ae44d8
LISTINGS = ROOT / 'local/epl9-v3-diagnostic-init-20261107'


class Model(Boundary):
    def __init__(self, name, abi, action):
        super().__init__(name, [abi])
        self.action = action

    def apply(self, m):
        return self.action(m)


def checked(condition, message):
    if not condition:
        raise ValueError(message)


def run(out, directory=LISTINGS):
    checked(not out.exists() and out.resolve().is_relative_to((ROOT/'local').resolve()),
            'new ignored output required')
    image = MAIN.read_bytes()
    checked(sha(image) == MAIN_SHA, 'stock main identity differs')
    paths = [directory/(n+'.tsv') for n in
             ('init', 'teardown', 'reset', 'ready', 'callback-wait', 'lens-main', 'init-callback')]
    code = {}
    for p in paths:
        incoming = parse_listing(p.read_text(encoding='utf-8-sig'), image, BASE)
        checked(all(code[a] == incoming[a] for a in code.keys() & incoming.keys()),
                'inconsistent native listing overlap')
        code.update(incoming)
    half = lambda a: struct.unpack_from('<H', image, a-BASE)[0]
    checked((half(0x60421030), half(0x60420fc6)) == (101, 48), 'queue identities differ')
    for at, name, ident in ((0x61786256, b'TAKE_FUNC_CP_POST', 101),
                            (0x61785cf4, b'LENS_EXEC', 48)):
        checked(image[at-BASE:at-BASE+24].rstrip(b'\0') == name and half(at+24) == ident,
                'queue name record differs')
    rows = []

    def make(ready=1, reply_mask=1, reply_status=0, send_status=0,
             event_status=0, callback_status=0):
        mem = Memory([Region(BASE, image), Region(SP-32768, bytearray(65536), True),
                      Region(HEAP, bytearray(4096), True),
                      Region(0x62615580, bytearray(128), True),
                      Region(0x62618550, bytearray(8), True),
                      Region(0x625a4000, bytearray(4096), True),
                      Region(READY, bytearray(4), True)])
        mem.write(READY, ready, 4)
        state = dict(allocations={}, frees=[], sends=[], replies=[], schedules=[], waits=[], logs=[])

        def allocate(m):
            size = m.r['d0']
            checked(size in (8, 16), 'undeclared allocation')
            address = HEAP + 64*len(state['allocations'])
            state['allocations'][address] = size
            m.r['a0'] = address
            return dict(address=hex(address), bytes=size, allocation_modeled=True)

        def free(m):
            address = m.r['a0']
            checked(address in state['allocations'] and address not in state['frees'],
                    'unowned or duplicate synthetic free')
            state['frees'].append(address)
            return dict(address=hex(address), free_modeled=True)

        def send(m):
            checked((m.r['d0'], m.r['d1'], m.r['a1']) == (48, 16, 0xffffffff),
                    'unexpected service send')
            packet = [mem.read(m.r['a0']+i, 4) for i in range(0, 16, 4)]
            checked(packet[0] == 101 and packet[3] in state['allocations'], 'packet ownership differs')
            row = dict(queue=48, words=packet, injected_wrapper_result=send_status,
                       queue_io_executed=False)
            state['sends'].append(row)
            m.r['d0'] = send_status & 0xffffffff
            return row

        def receive(m):
            checked((m.r['d0'], m.r['d1'], m.r['a1']) == (101, 12, 0xffffffff),
                    'unexpected service receive')
            checked(not state['replies'], 'fixture supplies only one reply')
            for offset, value in ((0, reply_status), (4, reply_mask), (8, HEAP)):
                mem.write(m.r['a0']+offset, value, 4)
            row = dict(queue=101, status=reply_status, mask=reply_mask, reply_modeled=True)
            state['replies'].append(row)
            m.r['d0'] = 0
            return row

        def schedule(m):
            record = m.r['a0']
            checked(state['allocations'].get(record) == 8 and
                    (mem.read(record, 4), mem.read(record+4, 4)) == (0x605f99da, 0),
                    'callback record differs')
            row = dict(record=hex(record), callback='0x605f99da', scheduler_executed=False)
            state['schedules'].append(row)
            m.r['d0'] = 0
            return row

        def wait(m):
            # This is deliberately the still-pending callback cleanup path.
            # No scheduler completion, callback free or real event is invented.
            checked(m.r['d1'] == 1 and m.r['a1'] == 1 and
                    mem.read(m.r['sp']+36+4, 4) == 0xffffffff, 'event wait ABI differs')
            mem.write(0x626155a8, callback_status, 2)
            m.r['d0'] = event_status & 0xffffffff
            row = dict(kernel_result=event_status, injected_callback_status=callback_status,
                       callback_executed=False, kernel_wait_executed=False)
            state['waits'].append(row)
            return row

        def log(m):
            state['logs'].append(m.r['d0'])
            return dict(code=m.r['d0'], logging_suppressed=True)

        models = {
            0x60402373: Model('synthetic-owned-allocation', (0, 4), allocate),
            0x604023b2: Model('synthetic-owned-free', (0, 4), free),
            0x605f9d7c: Model('unexecuted-queue-send-wrapper', (0xc0, 44), send),
            0x605f9e3c: Model('synthetic-service-reply', (0xc0, 44), receive),
            0x60451dd9: Model('unexecuted-callback-registration', (0, 4), schedule),
            0x60431138: Model('injected-event-result', (0xf0, 36), wait),
            0x605fa0a3: Model('unexecuted-error-log', (0x80, 8), log),
        }
        return CallMachine(code, mem, dict(sp=SP, d0=0), models=models), state

    for ready in (0, 1):
        for send_status in (0, -1):
            m, s = make(ready=ready, send_status=send_status)
            stop = 0x605f97c5 if not ready else 0x605f984b
            r = m.run(m.enter(0x605f96c0, END, 0xf0, 60), [stop])
            checked(r.get('pc') == stop and m.memory.read(PENDING, 4) == 1 and
                    s['sends'][0]['words'][1:3] == [1, 1], 'native init prefix differs')
            checked(not s['frees'] and not s['replies'], 'premature completion')
            rows.append(dict(kind='open-prefix', ready=ready, send_wrapper_result=send_status,
                             stop=hex(stop), pending=1, command=1, completion_mask=1,
                             awaits='readiness-delay' if not ready else 'queue-reply'))

    for closing in (False, True):
        entry, frame, receive_pc = ((0x6067d641, 56, 0x6067d788) if closing else
                                    (0x605f96c0, 60, 0x605f984b))
        expected = 0x20 if closing else 1
        wrong = 1 if closing else 0x20
        m, s = make(reply_mask=wrong)
        r = m.run(m.enter(entry, END, 0xf0, frame), [receive_pc])
        checked(r.get('pc') == receive_pc, 'missing receive stop')
        # Consume exactly one synthetic reply, then stop at the next receive.
        first_after = receive_pc + len(code[receive_pc][0])
        r = m.run(receive_pc, [first_after])
        checked(r.get('pc') == first_after, 'receive fixture failed')
        r = m.run(first_after, [receive_pc, END])
        checked(r.get('pc') == receive_pc and m.memory.read(PENDING, 4) == expected
                and not s['frees'], 'wrong completion mask completed work')
        rows.append(dict(kind='close-wrong-mask' if closing else 'open-wrong-mask',
                         supplied=wrong, pending=expected, remains_waiting=True))

    for status in (0, 0x310d):
        m, s = make(reply_mask=0x20, reply_status=status)
        r = m.run(m.enter(0x6067d641, END, 0xf0, 56), [END])
        checked(r.get('pc') == END and m.r['sp'] == SP and m.r['d0'] == status and
                m.memory.read(PENDING, 4) == 0 and len(s['frees']) == 1 and
                s['sends'][0]['words'][1:3] == [0x20, 2], 'teardown return/ownership differs')
        rows.append(dict(kind='close-reply', injected_status=status, native_return=status,
                         command=2, completion_mask=0x20, all_fixture_allocations_freed=True))

    m, s = make()
    m.memory.write(0x6261558e, 1, 1)
    r = m.run(m.enter(0x6067d641, END, 0xf0, 56), [0x6067d64f])
    checked(r.get('pc') == 0x6067d64f and m.r['d0'] == 5 and not s['sends'],
            'active teardown prefix differs')
    rows.append(dict(kind='close-active-flag', stop='0x6067d64f', next_call='0x605f931e', argument=5))

    for reply_status, event_status, callback_status in ((0, 0, 0), (0, 0, 0x310d),
                                                       (0, -2, 0), (0x310d, 0, 0)):
        m, s = make(reply_status=reply_status, event_status=event_status, callback_status=callback_status)
        r = m.run(m.enter(0x605f96c0, END, 0xf0, 60), [0x6091ace8])
        wait_result = 0x4b06 if event_status == -2 else callback_status
        checked(r.get('pc') == 0x6091ace8 and m.r['d0'] == wait_result, 'wait result mapping differs')
        r = m.run(0x6091ace8, [END])
        checked(r.get('pc') == END and m.r['sp'] == SP and m.r['d0'] == reply_status and
                len(s['allocations']) == len(s['frees']) == 2 and s['logs'] == [0x38b4] and
                m.memory.read(0x6261558c, 1) == m.memory.read(0x6261558d, 1) == 1 and
                m.memory.read(0x6261558f, 1) == 0, 'init pending-callback cleanup differs')
        rows.append(dict(kind='open-pending-callback-cleanup', reply_status=reply_status,
                         kernel_event_result=event_status, callback_status=callback_status,
                         native_wait_result=wait_result, native_initializer_return=m.r['d0'],
                         logged_error=0x38b4, all_fixture_allocations_freed=True,
                         wait_error_not_propagated=bool(wait_result), terminal_flags_8c_8d_set=True))

    # Lens gate and inner dispatch are separate native fragments. Do not imply
    # execution of the unmodeled intermediate asynchronous lens job.
    for command, state, no_op in ((1, 1, True), (2, 0, True), (1, 0, False), (2, 1, False)):
        m, _ = make()
        m.memory.write(HEAP+8, command, 2)
        m.memory.write(0x625a405c, state, 2)
        m.r['a0'] = HEAP
        r = m.run(m.enter(0x605cec9b, END, 0x30, 20), [END, 0x605cecd7])
        checked(r.get('pc') == (END if no_op else 0x605cecd7), 'lens state gate differs')
        rows.append(dict(kind='lens-state-gate', command=command, initial_state=state,
                         native_no_op=no_op, stops_before_property_query=not no_op))
    for command, stop, target in ((1, 0x605cee57, 0x605cef22), (2, 0x605cee66, 0x605cf0c9)):
        m, _ = make()
        m.memory.write(HEAP+8, command, 2)
        m.r['a0'] = HEAP
        r = m.run(m.enter(0x605cee49, END, 0, 4), [stop])
        checked(r.get('pc') == stop and int(code[stop][2][0], 0) == target, 'lens dispatch differs')
        rows.append(dict(kind='lens-inner-dispatch', command=command,
                         selected_handler=hex(target), handler_executed=False))

    for command, final_state in ((1, 1), (2, 0)):
        m, _ = make()
        m.memory.write(HEAP+8, command, 2)
        m.memory.write(0x625a405c, 1-final_state, 2)
        m.r['a2'] = HEAP+8
        r = m.run(m.enter(0x605ced41, END, 0x30, 20), [END])
        checked(r.get('pc') == END and m.r['sp'] == SP and m.r['d0'] == 0 and
                m.memory.read(0x625a405c, 2) == final_state, 'lens post-wait state differs')
        rows.append(dict(kind='lens-post-wait-fragment', command=command, final_state=final_state,
                         prior_wait_and_handler_not_executed=True))

    result = dict(model='E-PL9 / IM008 / 1330', displayed_version='1.1 (owner report)', build='1101',
                  main_bytes=len(image), main_sha256=sha(image), cases=rows,
                  listing_sha256={str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in paths},
                  source_sha256=sha(Path(__file__).read_bytes()),
                  all_heap_queue_event_scheduler_services_modeled=True,
                  missing_callback_cleanup_is_not_successful_session=True,
                  downstream_lens_side_effects_qualified=False, physical_transport_qualified=False,
                  camera_accessed=False, firmware_modified=False, install_ready=False)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows), open_lens_command=1, close_lens_command=2,
                          wait_error_propagated=False, camera_accessed=False)))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--listings', type=Path, default=LISTINGS)
    args = ap.parse_args()
    run(args.out, args.listings)
