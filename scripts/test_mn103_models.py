"""Check software model effects, atomic range rejection and strict opt-in."""
import unittest
from mn103_calls import CallMachine
from mn103_models import FillModel, OneBlockPool
from mn103_subset import Memory, Region, Fault, operands


def machine(model, args, regs=None):
    raw, operands_text = args
    code = {0x1000: (bytes.fromhex(raw), 'call', operands(operands_text))}
    return CallMachine(code, Memory([Region(0x8000, bytearray(4096), True),
         Region(0x10000, bytearray([0xa5])*16384, True)]),
         {'sp': 0x8800, **(regs or {})}, models={0x2000: model})


FILL = ('cd0010a008', '0x2000,[d2,a2],8')
POOL = ('cd0010e010', '0x2000,[d2,d3,a2],16')


class ModelTests(unittest.TestCase):
    def test_fill_effects_canaries_saved_registers_and_stack(self):
        m = machine(FillModel(), FILL, {'a0': 0x10003, 'd0': 0x1f2, 'd1': 9, 'd2': 29, 'a2': 71})
        m.run(0x1000, [0x1005])
        self.assertEqual(m.memory.regions[1].data[:13], b'\xa5'*3+b'\xf2'*9+b'\xa5')
        self.assertEqual([m.r[k] for k in ('sp','d2','a2','a0','d1')], [0x8800,29,71,0x1000c,0])
        self.assertEqual(m.events[0]['op'], 'modeled_call')

    def test_fill_rejects_bad_range_before_any_mutation(self):
        for start, size in [(0x13fff,2),(0xffffffff,2),(0x87ff,4)]:
            m = machine(FillModel(), FILL, {'a0': start,'d1': size})
            before = [bytes(r.data) for r in m.memory.regions]
            with self.assertRaises(Fault):
                m.run(0x1000)
            self.assertEqual(before, [bytes(r.data) for r in m.memory.regions])
            self.assertEqual(m.r['sp'], 0x8800)

    def test_zero_length_fill_does_not_dereference_pointer(self):
        m = machine(FillModel(), FILL, {'a0': 0xffffffff, 'd1': 0})
        m.run(0x1000, [0x1005])
        self.assertEqual(m.r['a0'], 0xffffffff)

    def test_allocator_success_failure_and_exhaustion(self):
        for fail in (False, True):
            m = machine(OneBlockPool(0x10000, fail), POOL, {'d0': 0x10004})
            m.run(0x1000, [0x1005])
            self.assertEqual(m.r['a0'], 0 if fail else 0x10000)
            self.assertEqual(m.memory.regions[1].data, b'\xa5'*16384)
            with self.assertRaises(Fault):
                m.run(0x1000)

    def test_model_rejects_wrong_abi_or_pool(self):
        for model, args, regs in [(FillModel(),POOL,{}),
                                  (OneBlockPool(0x10000),POOL,{'d0':0x10002})]:
            m = machine(model,args,regs)
            with self.assertRaises(Fault):
                m.run(0x1000)
            self.assertEqual(m.r['sp'], 0x8800)


if __name__ == '__main__':
    unittest.main()
