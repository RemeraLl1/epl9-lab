import unittest
import copy
from types import SimpleNamespace
from unittest.mock import patch

import epl9_native_source_deployment_probe as probe
from epl9_load_sequence_probe import STORAGE_BASE
from mn103_subset import Memory, Region, Fault


class NativeSourceBindingTests(unittest.TestCase):
    def document(self, generation=probe.GENERATION):
        return dict(generation=generation, files=[dict(file=probe.CANDIDATE_NAME),
                                                dict(file=probe.RESTORE_NAME)])

    def test_only_explicit_native_source_generation_is_accepted(self):
        probe.checked_manifest(self.document())
        for generation in (None, '', 'frozen-v3', 'private-color-v3', 'native-source-v2'):
            with self.subTest(generation=generation), self.assertRaisesRegex(ValueError, 'exactly native-source-v1'):
                probe.checked_manifest(self.document(generation))
        missing = self.document(); del missing['generation']
        with self.assertRaises(ValueError): probe.checked_manifest(missing)

    def test_candidate_and_restore_names_and_order_are_bound(self):
        for names in ((probe.RESTORE_NAME, probe.CANDIDATE_NAME), (probe.CANDIDATE_NAME,),
                (probe.CANDIDATE_NAME, probe.RESTORE_NAME, 'extra.bin'),
                ('Gold-Portra-v3-private-color-candidate.bin', probe.RESTORE_NAME)):
            document = self.document(); document['files'] = [dict(file=name) for name in names]
            with self.subTest(names=names), self.assertRaises(ValueError): probe.checked_manifest(document)

    def test_incorrect_stock_main_is_rejected_before_manifest_is_used(self):
        with self.assertRaisesRegex(ValueError, 'wrong stock main'):
            probe.checked_candidate(b'wrong', b'wrong', b'wrong', {})

    def test_protected_windows_require_exact_bytes_and_complete_source(self):
        stock = b'0123456789abcdef'
        windows = dict(sample=(probe.BASE+2, probe.BASE+10))
        with patch.object(probe, 'WINDOWS', windows), patch.object(probe, 'STATIC_WINDOWS', {}), \
                patch.object(probe, 'LOAD_WINDOWS', {}):
            rows = probe.protected_windows(stock, stock)
            self.assertEqual(rows[0]['sha256'], probe.sha(b'23456789'))
            self.assertTrue(rows[0]['matches_stock'])
            for candidate in (b'012X456789abcdef', b'01234'):
                with self.assertRaises(ValueError): probe.protected_windows(stock, candidate)
            with self.assertRaises(ValueError): probe.protected_windows(stock[:5], stock[:5])

    def test_corrected_generation_pins_are_distinct_from_historical_mains(self):
        self.assertNotIn(probe.NATIVE_MAIN_SHA, (probe.MAIN_SHA,
            '501707d09a0eb648e46196752b7ece17cd5368f6d54dbabce7c73e9806f65686',
            '72cc1e48e6b42ab02b9911bdb841fe2c5b0cb34f2c08893f6b78be8a6871beee'))
        self.assertEqual(len(probe.HOOKS), 4)
        self.assertEqual(len({address for address, _, _ in probe.HOOKS}), 4)
        self.assertIn(0x60761c9e, {address for address, _, _ in probe.HOOKS})
        self.assertNotIn(0x6074f352, {address for address, _, _ in probe.HOOKS})


class EarlyNegativeOracleTests(unittest.TestCase):
    def expected_exceptions(self):
        return [kind(reason) for _, _, kind, reason in probe.EARLY_NEGATIVES]

    def test_each_negative_requires_its_exact_type_and_reason(self):
        with patch.object(probe, 'early_control', side_effect=self.expected_exceptions()) as run:
            rows = probe.early_negative_controls(b'candidate', {})
        self.assertTrue(all(row['exact_failure_reason_matched'] for row in rows))
        self.assertEqual([call.kwargs for call in run.call_args_list],
                         [options for _, options, _, _ in probe.EARLY_NEGATIVES])

    def test_unrelated_fault_at_any_negative_is_not_accepted(self):
        for index in range(len(probe.EARLY_NEGATIVES)):
            for kind in (ValueError, Fault):
                exceptions = self.expected_exceptions()
                exceptions[index] = kind('unrelated native decode or ABI fault')
                with self.subTest(index=index, kind=kind), \
                        patch.object(probe, 'early_control', side_effect=exceptions), \
                        self.assertRaisesRegex(ValueError, 'unrelated reason'):
                    probe.early_negative_controls(b'candidate', {})

    def test_expected_reason_with_wrong_exception_type_is_not_accepted(self):
        exceptions = self.expected_exceptions()
        exceptions[0] = Fault(str(exceptions[0]))
        with patch.object(probe, 'early_control', side_effect=exceptions), \
                self.assertRaisesRegex(ValueError, 'unrelated reason'):
            probe.early_negative_controls(b'candidate', {})

    def test_successful_negative_is_not_accepted(self):
        with patch.object(probe, 'early_control', return_value={}), \
                self.assertRaisesRegex(ValueError, 'negative was accepted'):
            probe.early_negative_controls(b'candidate', {})


class CandidateReconstructionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        length = max(address-probe.BASE+len(bytes.fromhex(after))
                     for address, _, after in probe.HOOKS)+32
        stock = bytearray(b'\x11'*length)
        stock[probe.CANDIDATE-probe.BASE:probe.CANDIDATE-probe.BASE+probe.MODULE_SIZE] = b'\xff'*probe.MODULE_SIZE
        for address, before, _ in probe.HOOKS:
            at = address-probe.BASE
            stock[at:at+len(bytes.fromhex(before))] = bytes.fromhex(before)
        cls.stock = bytes(stock)
        cls.module = bytes(i % 253 for i in range(probe.MODULE_SIZE))
        candidate = bytearray(stock)
        candidate[probe.CANDIDATE-probe.BASE:probe.CANDIDATE-probe.BASE+probe.MODULE_SIZE] = cls.module
        for address, _, after in probe.HOOKS:
            at = address-probe.BASE
            candidate[at:at+len(bytes.fromhex(after))] = bytes.fromhex(after)
        cls.candidate = bytes(candidate)
        cls.manifest = dict(main_sha256=probe.sha(cls.stock), module_base=hex(probe.CANDIDATE),
            module_bytes=probe.MODULE_SIZE, module_sha256=probe.sha(cls.module),
            candidate_patches=[dict(address=hex(a), before=b, after=c) for a,b,c in probe.HOOKS])

    def check(self, *, candidate=None, manifest=None, stock=None):
        candidate = self.candidate if candidate is None else candidate
        manifest = self.manifest if manifest is None else manifest
        stock = self.stock if stock is None else stock
        # Synthetic unit fixture identities are patched only inside the test.
        # The production CLI has no hash override or permissive generation path.
        with patch.object(probe, 'MAIN_SHA', probe.sha(stock)), \
                patch.object(probe, 'NATIVE_MAIN_SHA', probe.sha(candidate)), \
                patch.object(probe, 'MODULE_SHA', probe.sha(self.module)):
            probe.checked_candidate(stock, candidate, self.module, manifest)

    def test_declared_exact_module_and_four_hooks_reconstruct_candidate(self):
        self.check()

    def test_missing_duplicate_or_mutated_hook_manifest_is_rejected(self):
        for change in ('missing', 'duplicate', 'mutated'):
            manifest = copy.deepcopy(self.manifest)
            if change == 'missing': manifest['candidate_patches'].pop()
            elif change == 'duplicate': manifest['candidate_patches'].append(manifest['candidate_patches'][0])
            else: manifest['candidate_patches'][0]['after'] = '00'*5
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, 'four exact'):
                self.check(manifest=manifest)

    def test_hash_matching_undeclared_change_still_fails_reconstruction(self):
        candidate = bytearray(self.candidate); candidate[-1] ^= 1
        with self.assertRaisesRegex(ValueError, 'undeclared'):
            self.check(candidate=bytes(candidate))

    def test_nonpadding_module_source_is_rejected(self):
        stock = bytearray(self.stock); stock[probe.CANDIDATE-probe.BASE] = 0
        manifest = copy.deepcopy(self.manifest); manifest['main_sha256'] = probe.sha(stock)
        with self.assertRaisesRegex(ValueError, 'stock padding'):
            self.check(stock=bytes(stock), manifest=manifest)


class LocalSectionBoundaryTests(unittest.TestCase):
    def fixture(self, *, short_destination=False, short_source=False):
        source = bytes(i % 251 for i in range(8192))
        start = probe.BASE+2048
        destination = 0xa0400820
        source_address = (STORAGE_BASE+2048 & 0x3fffffff) | 0x80000000
        data = bytearray(b'\xa5'*16+b'\xcd'*(2047 if short_destination else 2048)+b'\xa5'*16)
        if short_source: source = source[:4095]
        reader = probe.LocalSectionRead(source, start, start+2048, source_address, destination, data)
        machine = SimpleNamespace(r=dict(a0=destination, a1=source_address, d0=2048, d1=257),
            memory=Memory([Region(destination-16, data, True)]))
        return reader, machine, data, source

    def test_native_section_contract_copies_exact_local_bytes_and_preserves_guards(self):
        reader, machine, data, source = self.fixture()
        reader.validate(machine, 0xf0, 20)
        result = reader.apply(machine)
        self.assertEqual(data[16:-16], source[2048:4096])
        self.assertEqual(data[:16]+data[-16:], b'\xa5'*32)
        self.assertEqual(result['loaded_sha256'], probe.sha(source[2048:4096]))
        self.assertFalse(result['physical_read'])
        self.assertEqual(machine.r['d0'], 0)

    def test_unexpected_abi_or_request_stops_before_writes(self):
        reader, machine, data, _ = self.fixture()
        before = bytes(data)
        for mask, frame in ((0,20), (0xf0,24)):
            with self.assertRaises(Fault): reader.validate(machine,mask,frame)
        for register in ('a0', 'a1', 'd0', 'd1'):
            original = machine.r[register]; machine.r[register] += 1
            with self.assertRaises(Fault): reader.apply(machine)
            machine.r[register] = original
            self.assertEqual(data, before)

    def test_short_source_is_rejected_before_writes(self):
        reader, machine, data, _ = self.fixture(short_source=True)
        before = bytes(data)
        with self.assertRaisesRegex(Fault, 'source outside'): reader.apply(machine)
        self.assertEqual(data, before)

    def test_short_destination_is_rejected_before_writes(self):
        # Remove the last payload byte AND the trailing guard, so mapped memory
        # cannot hide a short payload by supplying guard bytes to the model.
        reader, machine, data, _ = self.fixture(short_destination=True)
        region = machine.memory.regions[0]
        region.data = data[:-16]
        before = bytes(region.data)
        with self.assertRaisesRegex(Fault, 'destination truncated'): reader.apply(machine)
        self.assertEqual(region.data, before)

    def test_wrong_source_alias_mapping_is_rejected(self):
        reader, machine, data, _ = self.fixture()
        reader.start += 4; reader.end += 4
        before = bytes(data)
        with self.assertRaisesRegex(Fault, 'source outside'): reader.apply(machine)
        self.assertEqual(data, before)


if __name__ == '__main__':
    unittest.main()
