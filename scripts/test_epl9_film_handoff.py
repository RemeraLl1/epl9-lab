import struct
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from epl9_film_handoff import (BUNDLE_BASE, RGB_RETURN, checked_output,
                              inject_gamma, matrix_oracle)
from epl9_offline_prototype import STACK
from mn103_calls import CallMachine
from mn103_subset import Memory, Region


def fixture(writable=False):
    stack = bytearray(4096)
    frame = STACK+256
    pointers = tuple(BUNDLE_BASE+n*512 for n in range(3))
    data = b''.join(struct.pack('<256H', *(i*16+n for i in range(256))) for n in range(3))
    struct.pack_into('<I', stack, 256+220, 0x6079fbcd)
    struct.pack_into('<3I', stack, 256+68, *([0x608c37e4]*3))
    m = CallMachine({}, Memory([Region(STACK, stack, True), Region(BUNDLE_BASE, data, writable)]),
                    dict(sp=frame, d0=77, a0=123))
    bundle = dict(key=0x01010078, pointers=pointers, native_shared_gamma=0x608c37e4)
    return m, bundle, stack


class GammaHandoffTests(unittest.TestCase):
    def test_three_results_change_only_declared_stack_slots_and_no_registers(self):
        m, bundle, stack = fixture()
        before, regs = bytes(stack), dict(m.r)
        self.assertTrue(inject_gamma(m, RGB_RETURN, bundle['key'], bundle))
        expected = bytearray(before)
        struct.pack_into('<3I', expected, 256+68, *bundle['pointers'])
        self.assertEqual(stack, expected)
        self.assertEqual(m.r, regs)

    def test_non_target_identity_does_not_touch_memory_or_require_hook_context(self):
        for key in (1, 11, 0x01030078, 0x01010079):
            m, bundle, stack = fixture()
            before, regs = bytes(stack), dict(m.r)
            self.assertFalse(inject_gamma(m, 0, key, bundle))
            self.assertEqual(stack, before)
            self.assertEqual(m.r, regs)

    def test_wrong_boundary_binding_and_native_caller_are_rejected(self):
        m, bundle, stack = fixture()
        for pc, key in ((0, bundle['key']), (RGB_RETURN, 0x01020078)):
            with self.assertRaises(ValueError):
                inject_gamma(m, pc, key, bundle)
        struct.pack_into('<I', stack, 256+220, 0)
        with self.assertRaises(ValueError):
            inject_gamma(m, RGB_RETURN, bundle['key'], bundle)

    def test_unexpected_stock_selection_is_rejected(self):
        m, bundle, stack = fixture()
        struct.pack_into('<I', stack, 256+68, 0)
        with self.assertRaises(ValueError):
            inject_gamma(m, RGB_RETURN, bundle['key'], bundle)

    def test_writable_overlapping_and_short_curve_storage_rejected_before_writes(self):
        for mode in ('writable', 'overlap', 'short'):
            m, bundle, stack = fixture(mode == 'writable')
            if mode == 'overlap':
                bundle['pointers'] = (BUNDLE_BASE, BUNDLE_BASE+2, BUNDLE_BASE+1024)
            if mode == 'short':
                bundle['pointers'] = (BUNDLE_BASE, BUNDLE_BASE+512, BUNDLE_BASE+1026)
            before = bytes(stack)
            with self.assertRaises(ValueError):
                inject_gamma(m, RGB_RETURN, bundle['key'], bundle)
            self.assertEqual(stack, before)


class MatrixOracleTests(unittest.TestCase):
    def test_parity_constraints_and_normalized_rows_preserve_equal_inputs(self):
        result = matrix_oracle((128, 3, -1, 3, 128, 2, 0, -3, 128))
        self.assertEqual(result, (127, 2, -1, 2, 124, 2, 0, -4, 132))
        self.assertEqual([sum(result[n:n+3]) for n in (0, 3, 6)], [128]*3)

    def test_unbounded_or_nonnumeric_matrix_is_rejected(self):
        for matrix in ((0,)*8, (0,)*8+(1000,), (0,)*8+(True,)):
            with self.assertRaises(ValueError):
                matrix_oracle(matrix)

    def test_output_must_be_new_and_ignored(self):
        with TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                checked_output(Path(folder))
        with self.assertRaises(ValueError):
            checked_output(Path(__file__).resolve().parents[1]/'public-output')


if __name__ == '__main__':
    unittest.main()
