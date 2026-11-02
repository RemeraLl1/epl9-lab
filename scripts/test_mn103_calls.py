"""Synthetic ABI tests against explicit GNU stack conventions."""
import unittest
from mn103_calls import CallMachine
from mn103_subset import Memory, Region, Fault, operands


def make(rows, regs=None):
    code = {pc: (bytes.fromhex(raw), op, operands(args)) for pc, raw, op, args in rows}
    return CallMachine(code, Memory([Region(0x8000, bytearray(0x1000), True)]),
                       {'sp': 0x8800, **(regs or {})})


class CallTests(unittest.TestCase):
    def test_nested_call_ret_restores_saved_registers_and_sp(self):
        m = make([(0x1000, 'cd0010f020', 'call', '0x2000,[d2,d3,a2,a3],32'),
                  (0x2000, 'cd00100004', 'call', '0x3000,[],4'),
                  (0x2005, 'dff020', 'ret', '[d2,d3,a2,a3],32'),
                  (0x3000, '8a09', 'mov', '9,d2'), (0x3002, 'df0004', 'ret', '[],4')],
                 {'d2': 22, 'd3': 33, 'a2': 42, 'a3': 43})
        m.run(0x1000, [0x1005])
        self.assertEqual(m.r['sp'], 0x8800)
        self.assertEqual([m.r[r] for r in ('d2','d3','a2','a3')], [22,33,42,43])
        self.assertEqual(m.memory.read(0x87fc, 4), 22)
        self.assertEqual(m.memory.read(0x87e0, 4), 0x2005)

    def test_indirect_calls_movm_and_retf(self):
        m = make([(0x1000, 'f0f1', 'calls', '(a1)'),
                  (0x2000, 'cfa0', 'movm', '[d2,a2],(sp)'),
                  (0x2002, '8a09', 'mov', '9,d2'),
                  (0x2004, 'dea008', 'retf', '[d2,a2],8')], {'a1': 0x2000, 'd2': 22, 'a2': 42})
        m.run(0x1000, [0x1002])
        self.assertEqual((m.r['sp'], m.r['d2'], m.r['a2']), (0x8800, 22, 42))

    def test_retf_uses_mdr_not_stack_return(self):
        m = make([(0x1000, 'de0000', 'retf', '[],0')], {'mdr': 0x2000})
        m.memory.write(0x8800, 0x3000, 4)
        self.assertEqual(m.run(0x1000, [0x2000])['pc'], 0x2000)

    def test_movm_pop_reverse_order(self):
        m = make([(0x1000,'cff0','movm','[d2,d3,a2,a3],(sp)'),
                  (0x1002,'cef0','movm','(sp),[d2,d3,a2,a3]')],
                 {'d2': 2, 'd3': 3, 'a2': 12, 'a3': 13})
        m.run(0x1000, [0x1002])
        self.assertEqual(m.r['sp'], 0x87f0)
        m.r.update(d2=0,d3=0,a2=0,a3=0)
        m.run(0x1002,[0x1004])
        self.assertEqual([m.r[r] for r in ('d2','d3','a2','a3','sp')], [2,3,12,13,0x8800])

    def test_missing_callee_does_not_fake_success_or_change_stack(self):
        m = make([(0x1000,'cd0010f020','call','0x2000,[d2,d3,a2,a3],32')])
        before = bytes(m.memory.regions[0].data)
        self.assertEqual(m.run(0x1000)['status'], 'external_call')
        self.assertEqual(m.r['sp'], 0x8800)
        self.assertEqual(bytes(m.memory.regions[0].data), before)

    def test_unsupported_mask_and_bad_stack_rejected(self):
        m = make([(0x1000,'cf08','movm','[other],(sp)')])
        with self.assertRaises(Fault):
            m.run(0x1000)
        m = make([(0x1000,'df0000','ret','[],0')], {'sp': 0x100})
        with self.assertRaises(Fault):
            m.run(0x1000)


if __name__ == '__main__':
    unittest.main()
