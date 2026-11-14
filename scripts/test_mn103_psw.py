import unittest
from mn103_subset import Machine,Memory,Fault

class PswSemantics(unittest.TestCase):
    def machine(self,raw,op,args,psw=0):
        return Machine({0x100:(bytes.fromhex(raw),op,args)},Memory([]),psw=psw)
    def step(self,m):return m.run(0x100,limit=1,single_step=True)
    def test_move_reads_all_bits(self):
        for i in range(4):
            m=self.machine('f2'+format(0xe4+i,'02x'),'mov',['psw',f'd{i}'],0x180f)
            self.step(m);self.assertEqual(m.r[f'd{i}'],0x180f);self.assertEqual(m.read_psw(),0x180f)
    def test_move_restores_flags(self):
        m=self.machine('f2f3','mov',['d0','psw']);m.r['d0']=0x804
        self.step(m);self.assertTrue(m.c);self.assertFalse(m.z);self.assertEqual(m.read_psw(),0x804)
    def test_and_mask_does_not_recompute_flags(self):
        m=self.machine('fafcfff7','and',['63487','psw'],0x800)
        self.step(m);self.assertEqual(m.read_psw(),0);self.assertFalse(m.z)
    def test_or_can_set_zero_flag(self):
        m=self.machine('fafd0108','or',['2049','psw'])
        self.step(m);self.assertEqual(m.read_psw(),0x801);self.assertTrue(m.condition('eq'))
    def test_arithmetic_preserves_control(self):
        m=self.machine('00','clr',['d0'],0x180e)
        self.step(m);self.assertEqual(m.read_psw(),0x1801)
    def test_disabled_and_bad_encoding_fail_closed(self):
        m=Machine({0x100:(bytes.fromhex('f2e4'),'mov',['psw','d0'])},Memory([]))
        with self.assertRaises(Fault):self.step(m)
        m=self.machine('f2e5','mov',['psw','d0'])
        with self.assertRaises(Fault):self.step(m)

if __name__=='__main__':unittest.main()
