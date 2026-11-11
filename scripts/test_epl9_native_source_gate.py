"""Synthetic instruction contracts; real-BIN path evidence is a separate probe."""
import struct
import unittest

from epl9_native_source_gate import SOURCE_PAIRS, assembly, qualified, extend_late_source
from epl9_wb_extension import assembly as wb_assembly, adjusted
from epl9_offline_prototype import header
from mn103_emit import assemble
from mn103_subset import Machine, Memory, Region

BASE, REQUEST, SP = 0x68000000, 0x11000000, 0x10010000
GAINS = {'0x01010078': (1106, 901), '0x01020078': (1060, 963)}


def code(source):
    data, symbols, rows = assemble(source, BASE)
    return {pc: (data[pc-BASE:pc-BASE+length], op,
                 [hex(symbols[arg]) if arg in symbols else arg for arg in args])
            for pc, op, args, length in rows}, symbols


class NativeSourceGateTests(unittest.TestCase):
    def test_exact_source_pairs_reject_unknown_flags_formats_and_booleans(self):
        self.assertEqual(SOURCE_PAIRS, ((0x100, 0), (0x200, 0), (0x107, 3)))
        for fmt, flags in SOURCE_PAIRS:
            self.assertTrue(qualified(fmt, flags))
        for pair in ((0x107, 0), (0x107, 7), (0x108, 3), (0x200, 3),
                     (0x107, 0x83), (True, 0), (0x100, False)):
            self.assertFalse(qualified(*pair))

    def test_inline_source_gate_preserves_native_d0_result_and_recipe_key(self):
        for register in ('a1', 'a3'):
            source = assembly('test', register, 28, 48, 'yes', 'no')
            source += 'yes:\n jmp 0x1e000000\nno:\n jmp 0x1e000004\n'
            instructions, _ = code(source)
            for fmt, flags in (*SOURCE_PAIRS, (0x107, 7), (0x108, 0), (0x100, 3)):
                request = bytearray(64)
                struct.pack_into('<H', request, 28, fmt)
                request[48] = flags
                m = Machine(instructions, Memory([Region(REQUEST, request)]),
                            {register: REQUEST, 'd0': 0x12345678})
                result = m.run(BASE, (0x1e000000, 0x1e000004))
                self.assertEqual(result['pc'], 0x1e000000 if qualified(fmt, flags) else 0x1e000004)
                self.assertEqual(m.r['d0'], 0x12345678)

    def test_finalized_wb_reads_final_fields_and_replays_displaced_state(self):
        instructions, symbols = code(wb_assembly(GAINS, native_source_gate=True))
        records = ((1024,)*4, (65535,)*4, (2048,1536,0,1024))
        for key, factors in GAINS.items():
            for fmt, flags, selector, kind, accepted in (
                (0x100,0,0,0x200,True), (0x200,0,0,0x1000,True),
                (0x107,3,0,0x1000,True), (0x107,7,0,0x1000,False),
                (0x108,0,0,0x1000,False), (0x107,3,0x900,0x1000,False),
                (0x107,3,0,0x107,False), (0x107,0x83,0,0x1000,False)):
                for gains in records:
                    with self.subTest(key=key, fmt=fmt, flags=flags, selector=selector, gains=gains):
                        request = bytearray([0xa5])*1876
                        header = 0x00780101 if key=='0x01010078' else 0x00780201
                        struct.pack_into('<I', request, 8, header)
                        struct.pack_into('<H', request, 14, kind)
                        struct.pack_into('<H', request, 28, fmt)
                        request[48] = flags
                        struct.pack_into('<H', request, 1832, selector)
                        struct.pack_into('<4H', request, 1568, *gains)
                        before = bytes(request)
                        stack = bytearray(1024)
                        struct.pack_into('<I', stack, 52, REQUEST)
                        struct.pack_into('<I', stack, 752, 0x11223344)
                        preserved = dict(a0=0x10002000,a2=0x22334455,a3=0x33445566,
                                         d2=0x44556677,d3=0x55667788,mdr=0x66778899,mdrq=0x778899aa,sp=SP)
                        m = Machine(instructions, Memory([Region(REQUEST,request,True),
                            Region(SP,stack)]), preserved)
                        result = m.run(symbols['film_wb_entry'], (0x60761ca4,))
                        self.assertEqual(result['pc'], 0x60761ca4)
                        expected = bytearray(before)
                        struct.pack_into('<4H',expected,1568,*adjusted(gains,factors) if accepted else gains)
                        self.assertEqual(request, expected)
                        self.assertEqual(m.r['d0'], 0x11223344)
                        self.assertEqual(m.r['d1'], 0)
                        for name, value in preserved.items():
                            self.assertEqual(m.r[name], value, name)
                        self.assertFalse(m.z)

    def test_template_mismatch_is_rejected_and_no_implicit_scope_expansion(self):
        with self.assertRaisesRegex(ValueError, 'reviewed late template'):
            extend_late_source('unreviewed source')

    def test_finalized_wb_leaves_other_mode_keys_unchanged(self):
        instructions, symbols = code(wb_assembly(GAINS, native_source_gate=True))
        for key in (1, 11, 0x01030078):
            request = bytearray(1876)
            request[8:12] = header(key)
            struct.pack_into('<H', request, 14, 0x1000)
            struct.pack_into('<H', request, 28, 0x107)
            request[48] = 3
            struct.pack_into('<4H', request, 1568, 1024, 1024, 1024, 1024)
            before = bytes(request)
            stack = bytearray(1024)
            struct.pack_into('<I', stack, 52, REQUEST)
            m = Machine(instructions, Memory([Region(REQUEST,request,True),Region(SP,stack)]), {'sp':SP})
            self.assertEqual(m.run(symbols['film_wb_entry'], (0x60761ca4,))['pc'], 0x60761ca4)
            self.assertEqual(request, before)
            self.assertTrue(m.z)  # Replayed CMP 0 for the displaced zero option.


if __name__ == '__main__':
    unittest.main()
