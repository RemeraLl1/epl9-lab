import unittest
from epl9_icon_integration import replace_spans


class IconSpanTests(unittest.TestCase):
    def test_exact_reversible_replacement_preserves_unrelated_bytes(self):
        source=b'0123456789abcdef'
        changed=replace_spans(source,[(2,b'23',b'XY'),(10,b'ab',b'ZZ')])
        self.assertEqual(changed,b'01XY456789ZZcdef')
        self.assertEqual(replace_spans(changed,[(2,b'XY',b'23'),(10,b'ZZ',b'ab')]),source)

    def test_overlap_growth_mismatch_and_outside_rejected(self):
        for changes in ([(1,b'12',b'a')],[(1,b'12',b'abc')],[(1,b'ZZ',b'ab')],
                        [(1,b'12',b'ab'),(2,b'23',b'cd')],[(20,b'X',b'Y')]):
            with self.assertRaises(ValueError): replace_spans(b'012345',changes)
