"""Input-free regressions for authored ART hook gates and WB arithmetic.

The instruction map uses assembler rows, not an independent GNU decode. These
tests exercise synthetic control flow only: no stock firmware, native callers,
v3 recipe data, ISP pixels, update package or camera execution is supplied.
"""
import struct
from string import Template
import unittest

from epl9_film_module import OFFSETS, ROOT
from epl9_offline_prototype import header
from epl9_wb_extension import adjusted, assembly as wb_assembly
from mn103_emit import assemble
from mn103_subset import Machine, Memory, Region


BASE = 0x68000000
REQUEST, CONTEXT, OUTPUT, SP = 0x20000000, 0x20100000, 0x20200000, 0x20300000
KEYS = (0x01010078, 0x01020078)
KINDS = (0x40, 0x100, 0x200, 0x1000)
REJECTED_KINDS = (0, 0x41, 0x101, 0x201, 0x300, 0x1001, 0x1040, 0x1100, 0x1200, 0xffff)


def instruction_map(source):
    data, symbols, rows = assemble(source, BASE)
    code = {at: (data[at-BASE:at-BASE+length], op,
                 [str(symbols[arg]) if arg in symbols else arg for arg in args])
            for at, op, args, length in rows}
    return code, symbols, rows


def late_source():
    # Fixture constants only. No recipe is loaded, selected or retuned here.
    constants = {name: BASE+offset for name, offset in OFFSETS.items()}
    constants.update(GOLD_KEY=KEYS[0], PORTRA_KEY=KEYS[1],
                     GOLD_HEADER=0x00780101, PORTRA_HEADER=0x00780201,
                     COLOR_HEADER=0x000b0000, CONTROL_MAGIC=0x46504c45)
    for name in ('GOLD', 'PORTRA'):
        constants.update({name+'_'+field: 0 for field in ('CONTRAST', 'HIGHLIGHTS', 'SHADOWS')})
    return Template((ROOT/'firmware_src/epl9_films_late.s.in').read_text()).substitute(constants)


def fixture(code, key=KEYS[0], kind=0x1000):
    request, context, output, stack = bytearray(1876), bytearray(80), bytearray(5200), bytearray(512)
    request[8:12] = header(key)
    struct.pack_into('<H', request, 14, kind)
    struct.pack_into('<H', request, 28, 0x200)
    struct.pack_into('<I', context, 4, REQUEST)
    struct.pack_into('<I', context, 12, OUTPUT)
    struct.pack_into('<I', context, 52, key)
    regions = [Region(at, data, True) for at, data in
               ((REQUEST, request), (CONTEXT, context), (OUTPUT, output), (SP, stack))]
    machine = Machine(code, Memory(regions), dict(a0=CONTEXT, a2=REQUEST, a3=REQUEST, sp=SP))
    return machine


def snapshot(machine):
    return [bytes(region.data) for region in machine.memory.regions]


class ArtHookGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.code, cls.symbols, rows = instruction_map(late_source())
        # Begin after the original gamma call, which requires exact firmware.
        gamma_call = next(i for i, (_, op, args, _) in enumerate(rows)
                          if op == 'call' and args[0] == '0x6079d328')
        cls.gamma_start = rows[gamma_call+1][0]

    def color_gate(self, key=KEYS[0], kind=0x1000, changes=()):
        machine = fixture(self.code, key, kind)
        for address, value, size in changes:
            machine.memory.write(address, value, size)
        before = snapshot(machine)
        stops = [self.symbols[name] for name in ('color_save', 'film_color_original')]
        result = machine.run(self.symbols['film_color_entry'], stops)
        self.assertEqual(snapshot(machine), before)
        return machine, result['pc']

    def gamma_gate(self, key=KEYS[0], kind=0x1000, changes=()):
        machine = fixture(self.code, key, kind)
        for address, value in ((REQUEST+8, 0x000b0000), (CONTEXT+52, 11),
                               (SP+28, 0x6079d7fb), (SP+72, CONTEXT),
                               (SP+288, self.symbols['color_after_native_call']),
                               (REQUEST+1512, SP+352), (SP+364, key),
                               (SP+368, 0x46504c45)):
            machine.memory.write(address, value, 4)
        for address, value, size in changes:
            machine.memory.write(address, value, size)
        before = snapshot(machine)
        stops = [self.symbols[name] for name in ('gamma_gold', 'gamma_portra', 'gamma_done')]
        result = machine.run(self.gamma_start, stops)
        self.assertEqual(snapshot(machine), before)
        return result['pc']

    def test_color_accepts_only_exact_supported_kinds_for_both_slots(self):
        for key in KEYS:
            for kind in KINDS+REJECTED_KINDS:
                with self.subTest(key=hex(key), kind=hex(kind)):
                    machine, pc = self.color_gate(key, kind)
                    accepted = kind in KINDS
                    self.assertEqual(pc, self.symbols['color_save' if accepted else 'film_color_original'])
                    if accepted:
                        self.assertEqual(machine.r['d1'], KEYS.index(key)+1)

    def test_color_requires_coherent_identity_layout_variant_and_selector(self):
        for key in KEYS:
            mutations = [(CONTEXT+52, 11, 4), (CONTEXT+52, 0x01030078, 4),
                         (REQUEST+8, int.from_bytes(header(KEYS[1-KEYS.index(key)]), 'little'), 4),
                         (REQUEST+28, 0x1000, 2), (REQUEST+48, 1, 1), (REQUEST+1832, 1, 2)]
            for change in mutations:
                with self.subTest(key=hex(key), change=change):
                    _, pc = self.color_gate(key, changes=[change])
                    self.assertEqual(pc, self.symbols['film_color_original'])
            _, pc = self.color_gate(key, changes=[(REQUEST+28, 0x100, 2)])
            self.assertEqual(pc, self.symbols['color_save'])

    def test_gamma_accepts_only_exact_supported_kinds_for_both_slots(self):
        for key, label in zip(KEYS, ('gamma_gold', 'gamma_portra')):
            for kind in KINDS+REJECTED_KINDS:
                with self.subTest(key=hex(key), kind=hex(kind)):
                    self.assertEqual(self.gamma_gate(key, kind),
                                     self.symbols[label if kind in KINDS else 'gamma_done'])

    def test_gamma_rejects_mismatched_caller_and_control_record(self):
        changes = [(SP+28, 0x6079d7fa, 4), (SP+72, 0, 4), (CONTEXT+4, REQUEST+4, 4),
                   (CONTEXT+52, KEYS[0], 4), (REQUEST+8, 0, 4),
                   (SP+288, self.symbols['color_after_native_call']+1, 4),
                   (REQUEST+1512, SP+356, 4), (SP+368, 0, 4),
                   (SP+364, 0x01030078, 4), (REQUEST+28, 0x1000, 2),
                   (REQUEST+48, 1, 1), (REQUEST+1832, 1, 2)]
        for key in KEYS:
            for change in changes:
                with self.subTest(key=hex(key), change=change):
                    self.assertEqual(self.gamma_gate(key, changes=[change]), self.symbols['gamma_done'])

    def test_gamma_rejected_kind_never_reads_unqualified_stack_record(self):
        for kind in REJECTED_KINDS:
            machine = fixture(self.code, kind=kind)
            # No stack/context memory exists: early rejection must not touch it.
            machine.memory = Memory([machine.memory.regions[0]])
            result = machine.run(self.gamma_start, [self.symbols['gamma_done']])
            self.assertEqual(result['pc'], self.symbols['gamma_done'])


class WbHookGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gains = {str_key: values for str_key, values in
                     (('0x01010078', (1106, 901)), ('0x01020078', (900, 1120)))}
        cls.code, cls.symbols, _ = instruction_map(wb_assembly(cls.gains))

    def run_hook(self, key, kind, values):
        machine = fixture(self.code, key, kind)
        machine.r.update(a0=0x1234, a3=0x5678, d3=0x9abc, mdr=0xdef0, mdrq=0x1357)
        for i, value in enumerate(values):
            machine.memory.write(REQUEST+1568+2*i, value, 2)
        before = snapshot(machine)
        registers = dict(machine.r)
        result = machine.run(self.symbols['film_wb_entry'], [0x6074f357])
        self.assertEqual(result['pc'], 0x6074f357)
        for name in ('a0', 'a2', 'a3', 'd3', 'sp', 'mdr', 'mdrq'):
            self.assertEqual(machine.r[name], registers[name], name)
        self.assertEqual((machine.r['d0'], machine.r['d2'], machine.r['a1']), (0, 0, 3710))
        expected = bytearray(before[0])
        gains = self.gains.get(f'0x{key:08x}')
        if gains is not None and kind in KINDS:
            struct.pack_into('<4H', expected, 1568, *adjusted(values, gains))
        self.assertEqual(snapshot(machine), [bytes(expected), *before[1:]])

    def test_wb_exact_kind_and_key_grid_preserves_other_request_bytes(self):
        for key in (*KEYS, 11, 0x01030078, 0x02010078):
            for kind in KINDS+REJECTED_KINDS:
                with self.subTest(key=hex(key), kind=hex(kind)):
                    self.run_hook(key, kind, (2048, 1536, 1024, 1056))

    def test_wb_zero_inputs_and_saturation_match_integer_oracle(self):
        for key in KEYS:
            for values in ((65535,)*4, (1,)*4, (0, 1, 1, 1), (1, 0, 1, 1),
                           (1, 1, 0, 1), (1, 1, 1, 0)):
                with self.subTest(key=hex(key), values=values):
                    self.run_hook(key, 0x1000, values)


if __name__ == '__main__':
    unittest.main()
