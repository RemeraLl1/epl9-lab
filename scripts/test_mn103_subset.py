"""Arithmetic/boundary tests with synthetic instructions, no camera or firmware."""
import random
import unittest

from mn103_subset import Fault, Machine, Memory, Region, MASK, parse_listing, signed


def mini(rows, registers=None, regions=()):
    image = b''.join(bytes.fromhex(raw) for raw, text in rows)
    at, listing = 0x2000, []
    for raw, text in rows:
        listing.append(f'{at:x}\t{raw}\t{text}')
        at += len(bytes.fromhex(raw))
    code = parse_listing('\n'.join(listing), image, 0x2000)
    return Machine(code, Memory(list(regions)), registers), at


class SubsetTests(unittest.TestCase):
    def test_add_sub_compare_flags_against_integer_arithmetic(self):
        rng = random.Random(1330)
        vectors = [(0, 0), (MASK, 1), (0x7fffffff, 1), (0x80000000, MASK)]
        vectors += [(rng.randrange(1 << 32), rng.randrange(1 << 32)) for _ in range(200)]
        for right, left in vectors:
            for op, raw in [('add', 'e4'), ('sub', 'f104'), ('cmp', 'a4')]:
                m, end = mini([(raw, op+'\td1,d0')], {'d0': right, 'd1': left})
                m.run(0x2000, [end])
                expected = right + left if op == 'add' else right - left
                signed_result = signed(right) + signed(left) if op == 'add' else signed(right) - signed(left)
                self.assertEqual(m.r['d0'], right if op == 'cmp' else expected & MASK)
                self.assertEqual(m.c, expected > MASK if op == 'add' else expected < 0)
                self.assertEqual(m.v, not -(1 << 31) <= signed_result < 1 << 31)
                self.assertEqual(m.z, (expected & MASK) == 0)
                self.assertEqual(m.n, signed(expected) < 0)

    def test_moves_and_extensions_preserve_comparison(self):
        m, end = mini([('a4', 'cmp\td1,d0'), ('50', 'inc4\ta0'),
                       ('10', 'extb\td0'), ('f1d1', 'mov\ta0,d1')],
                      {'d0': 255, 'd1': 255, 'a0': 100})
        m.run(0x2000, [end])
        self.assertTrue(m.z)
        self.assertEqual(m.r['a0'], 104)
        self.assertEqual(m.r['d0'], MASK)

    def test_loop_and_address_increment_keep_flags(self):
        m, end = mini([('db', 'setlb'), ('40', 'inc\td0'), ('50', 'inc4\ta0'),
                       ('a003', 'cmp\t3,d0'), ('d9', 'lne')])
        m.run(0x2000, [end])
        self.assertEqual(m.r['d0'], 3)
        self.assertEqual(m.r['a0'], 12)

    def test_gnu_shift_flags(self):
        m, end = mini([('f8c008', 'asl\t8,d0')], {'d0': 0x10000001})
        m.c = m.v = True
        m.run(0x2000, [end])
        self.assertTrue(m.c and m.v)
        m, end = mini([('f8c808', 'asr\t8,d0')], {'d0': 0x80000001})
        m.v = True
        m.run(0x2000, [end])
        self.assertEqual(m.r['d0'], 0xff800000)
        self.assertTrue(m.c and m.v)

    def test_multiply_and_signed_divide(self):
        for left, right in [(-7000, 7), (0x7fffffff, 3), (-2147483648, -1), (-3, -7)]:
            m, end = mini([('f604', 'udf00\td1,d0')], {'d0': right, 'd1': left})
            m.run(0x2000, [end])
            self.assertEqual(m.r['d0'], (left*right) & MASK)
            self.assertEqual(m.r['mdrq'], (left*right >> 32) & MASK)
        m, end = mini([('f2d0', 'ext\td0'), ('f264', 'div\td1,d0')], {'d0': -17, 'd1': 5})
        m.run(0x2000, [end])
        self.assertEqual(signed(m.r['d0']), -3)
        self.assertEqual(signed(m.r['mdr']), -2)

    def test_memory_bounds_and_readonly(self):
        for address, writable in [(0x1000, False), (0x1001, True), (0x9000, True)]:
            m, _ = mini([('60', 'mov\td0,(a0)')], {'a0': address},
                        [Region(0x1000, bytearray(4), writable)])
            with self.assertRaises(Fault):
                m.run(0x2000)
        m, _ = mini([('70', 'mov\t(a0),d0')], {'a0': 0x1001},
                    [Region(0x1000, bytearray(8))])
        with self.assertRaisesRegex(Fault, 'unaligned'):
            m.run(0x2000)

    def test_unsigned_divide_64bit_inputs_and_flags(self):
        for dividend, divisor in [(0,3),(17,5),(0x100000000,3),
                                  (0x7fffffffffffffff,0xffffffff),(0xfffffffe00000000,0xffffffff)]:
            m,end=mini([('f274','divu\td1,d0')],
                       {'d0':dividend & MASK,'mdr':dividend >> 32,'d1':divisor})
            m.c=m.v=True
            m.run(0x2000,[end])
            q,r=divmod(dividend,divisor)
            self.assertEqual((m.r['d0'],m.r['mdr']),(q,r))
            self.assertEqual((m.z,m.n,m.c,m.v),(q==0,bool(q & 0x80000000),False,False))
        for high,divisor in [(0,0),(1,1)]:
            m,_=mini([('f274','divu\td1,d0')],{'d0':17,'mdr':high,'d1':divisor})
            before=dict(m.r)
            with self.assertRaises(Fault):
                m.run(0x2000)
            self.assertEqual(m.r,before)

    def test_unsigned_register_product_and_not(self):
        for left,right in [(0,0xffffffff),(0xffffffff,0xffffffff),(0x80000000,3),(17,23)]:
            m,end=mini([('f614','udf01\td1,d0')],{'d0':right,'d1':left})
            m.c=m.v=True
            m.run(0x2000,[end])
            product=left*right
            self.assertEqual((m.r['d0'],m.r['mdrq']),(product & MASK,product >> 32))
            self.assertEqual((m.z,m.n,m.c,m.v),
                             ((product & MASK)==0,bool(product & 0x80000000),False,False))
        for value in (0,MASK,0x7fffffff,0x80000000):
            m,end=mini([('f230','not\td0')],{'d0':value})
            m.c=m.v=True
            m.run(0x2000,[end])
            expected=value ^ MASK
            self.assertEqual(m.r['d0'],expected)
            self.assertEqual((m.z,m.n,m.c,m.v),(expected==0,bool(expected & 0x80000000),False,False))

    def test_little_endian_and_signed_load(self):
        region = Region(0x1000, bytearray(b'\xfe\xff\x34\x12'))
        m, end = mini([('70', 'mov\t(a0),d0')], {'a0': 0x1000}, [region])
        m.run(0x2000, [end])
        self.assertEqual(m.r['d0'], 0x1234fffe)

    def test_unknown_unmapped_and_loop_limit_stop(self):
        for rows, limit in [([('ff', 'unknown')], 20), ([('ca00', 'bra\t0x2000')], 5),
                             ([('cc0000', 'jmp\t0x9000')], 20)]:
            m, _ = mini(rows)
            with self.assertRaises(Fault):
                m.run(0x2000, limit=limit)

    def test_call_and_return_are_boundaries(self):
        for raw, op in [('cd00000000', 'call\t0x1234,[],0'), ('df0000', 'ret\t[],0')]:
            m, _ = mini([(raw, op)], {'sp': 0x9000})
            self.assertTrue(m.run(0x2000)['status'].endswith('_boundary'))
            self.assertEqual(m.r['sp'], 0x9000)

    def test_listing_bytes_and_ambiguous_multiply_rejected(self):
        with self.assertRaises(ValueError):
            parse_listing('2000\tff\tnop', b'\x00', 0x2000)
        m, _ = mini([('f914ff', 'udfu01\t255,d0')])
        with self.assertRaises(Fault):
            m.run(0x2000)


if __name__ == '__main__':
    unittest.main()
