"""Synthetic lifecycle tests plus explicitly local, exact-stock native tests."""
from collections import Counter
import struct
import unittest

from epl9_wifi_prototype import (
    BLOCK, ROOT, Fault, Evidence, NativeReader, NativeIsc, IscContext, Resources,
    Ticket, Model, wire_request, transfer, OUTPUT, REQUEST, SCRATCH, span,
)


class IscPrototypeTests(unittest.TestCase):
    def test_persistent_resources_and_completion_boundary(self):
        resources = Resources()
        context = IscContext(resources, 0)
        source = bytearray(b'first')
        ticket = context.begin(0, source)
        self.assertIs(context.source, source)
        self.assertEqual(context.output, b'')  # A publish is not a completion.
        with self.assertRaises(Fault):
            context.begin(0, bytearray(b'next'))
        with self.assertRaises(Fault):
            context.close()
        context.complete(ticket, len(source))
        ticket2 = context.begin(0, bytearray(b'next'))
        with self.assertRaises(Fault):
            context.complete(ticket, 4)  # Old HOST ticket, not a wire-generation check.
        context.complete(ticket2, 4)
        self.assertEqual(context.output, b'firstnext')
        self.assertEqual(resources.counts, Counter(queue_creates=1, slot_creates=2))
        context.close()
        self.assertFalse(resources.live)
        self.assertEqual(resources.counts, Counter(queue_creates=1, queue_deletes=1,
                                                  slot_creates=2, slot_deletes=2))

    def test_partial_construction_rolls_back(self):
        for step in (1, 2, 3):
            with self.subTest(step=step):
                resources = Resources(fail_step=step)
                with self.assertRaises(Fault):
                    IscContext(resources, 0)
                self.assertFalse(resources.live)
                for kind in ('queue', 'slot'):
                    self.assertEqual(resources.counts[kind+'_creates'], resources.counts[kind+'_deletes'])

    def test_four_workers_have_disjoint_resources_and_requests(self):
        resources = Resources()
        contexts = [IscContext(resources, owner) for owner in range(4)]
        self.assertEqual(len({c.queue for c in contexts}), 4)
        self.assertEqual(len({c.request for c in contexts}), 4)
        with self.assertRaises(Fault):
            IscContext(resources, 0)
        tickets = [c.begin(i, bytearray([i])*10) for i, c in enumerate(contexts)]
        for i, c in enumerate(contexts):
            with self.assertRaises(Fault):
                c.complete(tickets[(i+1) % 4], 10)
            c.complete(tickets[i], 10)
            self.assertEqual(c.output, bytes([i])*10)
            c.close()
        self.assertFalse(resources.live)

    def test_source_cannot_change_during_wait(self):
        context = IscContext(Resources(), 0)
        source = bytearray(b'123')
        ticket = context.begin(0, source)
        source[1] = ord('x')
        with self.assertRaises(Fault):
            context.complete(ticket, 3)
        self.assertEqual(context.state, 'pending')
        source[1] = ord('2')
        context.complete(ticket, 3)
        context.close()

    def test_ambiguous_timeout_quarantines_until_actual_completion(self):
        context = IscContext(Resources(), 0)
        ticket = context.begin(0, bytearray(b'old'))
        context.ambiguous_timeout()
        self.assertEqual(context.state, 'quarantined')
        with self.assertRaises(Fault):
            context.begin(0, bytearray(b'new'))
        with self.assertRaises(Fault):
            context.close()
        with self.assertRaises(Fault):
            context.publication_rejected(ticket)
        context.complete(ticket, 3)
        self.assertEqual(context.output, b'old')
        context.close()

    def test_proven_prepublication_rejection_and_error_completion(self):
        context = IscContext(Resources(), 0)
        ticket = context.begin(0, bytearray(b'a'))
        context.publication_rejected(ticket)
        self.assertFalse(context.output)
        ticket = context.begin(0, bytearray(b'b'))
        context.complete(ticket, 0, status=1)
        self.assertFalse(context.output)
        context.close()

    def test_short_send_remainder_waits_separately(self):
        context = IscContext(Resources(), 0)
        source = bytearray(bytes(range(200)))
        offset = 0
        for accepted in (17, 0, 100, 83):
            ticket = context.begin(0, source, offset)
            offset += context.complete(ticket, accepted)
        self.assertEqual(offset, len(source))
        self.assertEqual(context.output, source)
        self.assertEqual(context.counts['completion_waits'], 4)
        context.close()

    def test_invalid_owner_results_and_double_close(self):
        context = IscContext(Resources(), 0)
        for owner in (1, -1):
            with self.assertRaises(Fault):
                context.begin(owner, bytearray(b'a'))
        with self.assertRaises(Fault):
            context.begin(0, bytearray(BLOCK+1))
        ticket = context.begin(0, bytearray(b'a'))
        for returned, status in ((2, 0), (-1, 0), (1, 1)):
            with self.assertRaises(Fault):
                context.complete(ticket, returned, status)
        context.complete(ticket, 1)
        with self.assertRaises(Fault):
            context.complete(ticket, 1)
        context.close()
        with self.assertRaises(Fault):
            context.close()

    def test_wire_format_and_no_invented_generation_guarantee(self):
        context = IscContext(Resources(), 0)
        ticket = context.begin(0, bytearray(b'a'))
        first = context.wire
        fields = struct.unpack('<16I', first)
        self.assertEqual(fields[:9], (6, context.queue, REQUEST, 0, 9, OUTPUT & 0x5fffffff, 1, 0, 0))
        context.complete(ticket, 1)
        second = context.begin(0, bytearray(b'a'))
        self.assertNotEqual(ticket, second)
        # Honest negative control: the real wire format cannot tell them apart.
        self.assertEqual(first, context.wire)
        context.complete(second, 1)
        context.close()
        for source, length in ((0, 10), (0xbfffffff, 2), (OUTPUT, BLOCK+1)):
            with self.assertRaises(Fault):
                wire_request(1, REQUEST, 9, source, length)

    def test_model_abi_rejection(self):
        model = Model('test service', 0xf0, 28, lambda m: {})
        with self.assertRaises(Fault):
            model.validate(None, 0, 28)


@unittest.skipUnless((ROOT/'local/wifi-limits-20261102-v6/main_file_read_backend.tsv').exists(),
                     'requires ignored exact-stock image/listing fixtures')
class NativePrototypeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence = Evidence(ROOT/'local/wifi-limits-20261102-v6')
        cls.data = bytes(range(251))*140

    def test_actual_mode_parser(self):
        self.assertEqual(self.evidence.mode_flags('r')[0], 1)
        self.assertEqual(self.evidence.mode_flags('rd')[0], 17)
        with self.assertRaises(Fault):
            self.evidence.mode_flags('rde')

    def test_native_boundary_matrix_144_cases(self):
        for mode in ('r', 'rd'):
            for position in (0, 1, 127, 511, 512, 513, len(self.data)-1, len(self.data)):
                for count in (0, 1, 7, 511, 512, 513, 1024, 16383, BLOCK):
                    with self.subTest(mode=mode, position=position, count=count):
                        reader = NativeReader(self.evidence, self.data, mode)
                        result = reader.read(count, position)
                        self.assertEqual(result, self.data[position:position+count])
                        self.assertEqual(reader.position, position+len(result))

    def test_direct_route_removes_only_bounce_not_control_allocations(self):
        readers = [NativeReader(self.evidence, self.data, mode) for mode in ('r', 'rd')]
        self.assertEqual(readers[0].read(BLOCK), readers[1].read(BLOCK))
        ordinary, direct = [r.counts for r in readers]
        self.assertEqual((ordinary['bounce_allocations'], ordinary['memcpy_bytes']), (1, BLOCK))
        self.assertEqual((direct['bounce_allocations'], direct['memcpy_bytes']), (0, 0))
        for counts in (ordinary, direct):
            self.assertEqual((counts['control_allocations'], counts['control_frees']), (1, 1))

    def test_local_end_to_end_variants(self):
        cases = [transfer(self.evidence, self.data, mode, reuse)
                 for mode, reuse in [('r', False), ('rd', False), ('rd', True)]]
        self.assertEqual(len({case['sha256'] for case in cases}), 1)
        self.assertEqual(cases[0]['resources']['queue_creates'], 3)
        self.assertEqual(cases[2]['resources']['queue_creates'], 1)
        self.assertEqual(cases[2]['isc']['completion_waits'], 3)

    def test_native_short_reads_and_nonzero_error_status(self):
        for mode in ('r', 'rd'):
            error = NativeReader(self.evidence, self.data, mode, {0: (1, 0)})
            self.assertEqual(error.read(BLOCK), b'')
            self.assertEqual(error.position, 0)
        direct = NativeReader(self.evidence, self.data, 'rd', {0: (0, 1)})
        self.assertEqual(direct.read(BLOCK), self.data[:512])
        self.assertEqual(direct.position, 512)
        self.assertEqual(direct.read(BLOCK), self.data[512:512+BLOCK])
        buffered = NativeReader(self.evidence, self.data, 'r', {0: (0, 1)})
        self.assertEqual(buffered.read(BLOCK), self.data[:BLOCK])
        self.assertEqual(buffered.counts['sector_calls'], 2)

    def test_error_after_partial_head_preserves_actual_length(self):
        reader = NativeReader(self.evidence, self.data, 'rd', {1: (1, 0)})
        self.assertEqual(reader.read(1024, position=1), self.data[1:512])
        self.assertEqual(reader.position, 512)

    def test_successful_zero_sector_tail_exposes_native_assumption(self):
        # This tests a model-injected contract violation, NOT an observed SD bug.
        reader = NativeReader(self.evidence, self.data, 'rd', {1: (0, 0)})
        result = reader.read(513)
        self.assertEqual(len(result), 513)
        self.assertNotEqual(result, self.data[:513])
        self.assertEqual(result[-1], 0xcd)  # Stale scratch byte copied as success.

    def test_zero_progress_buffered_service_stops_at_instruction_limit(self):
        faults = {i: (0, 0) for i in range(1000)}
        reader = NativeReader(self.evidence, self.data, 'r', faults)
        with self.assertRaisesRegex(Fault, 'instruction limit'):
            reader.read(BLOCK)

    def test_physical_exhaustion_is_not_an_automatic_success(self):
        for mode in ('r', 'rd'):
            reader = NativeReader(self.evidence, self.data, mode, fail_alloc=True)
            with self.assertRaises(Fault):
                reader.read(BLOCK)

    def test_block_limit_and_declared_file_position(self):
        reader = NativeReader(self.evidence, self.data, 'rd')
        with self.assertRaises(Fault):
            reader.read(BLOCK+1)
        with self.assertRaises(Fault):
            reader.read(1, len(self.data)+1)

    def test_native_isc_helper_two_balanced_calls(self):
        native = NativeIsc(self.evidence)
        for length in (BLOCK, 7):
            self.assertEqual(native.send(length), wire_request(7, REQUEST, 9, OUTPUT, length))
        for name in ('queue_creates', 'queue_deletes', 'publishes', 'completion_waits'):
            self.assertEqual(native.counts[name], 2)
        self.assertEqual(native.counts['slot_allocations'], 4)
        self.assertEqual(native.counts['slot_frees'], 4)


if __name__ == '__main__':
    unittest.main()
