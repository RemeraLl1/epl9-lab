import unittest
from fractions import Fraction
from epl9_float_contract import pack,unpack
from mn103_subset import Fault


class FloatContractTests(unittest.TestCase):
    def test_known_bits_and_round_to_even_ties(self):
        for value,bits in ((Fraction(1),0x3f800000),(Fraction(-2),0xc0000000),
                           (Fraction(3,2),0x3fc00000),(Fraction(1,2),0x3f000000)):
            self.assertEqual(pack(value),bits);self.assertEqual(unpack(bits),value)
        self.assertEqual(pack(Fraction(1)+Fraction(1,1<<24)),0x3f800000)
        self.assertEqual(pack(Fraction(1)+Fraction(3,1<<24)),0x3f800002)

    def test_unsupported_float_domains_do_not_silently_pass(self):
        for bits in (1,0x7f800000,0x7fc00000,0xff800000):
            with self.assertRaises(Fault):unpack(bits)
        for value in (Fraction(2)**128,Fraction(2)**-127):
            with self.assertRaises(Fault):pack(value)
