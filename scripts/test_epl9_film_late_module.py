"""Data-input contracts; native execution is covered by the pinned-image probe."""
from copy import deepcopy
import unittest

from epl9_film_late_module import rgb_tables, build_late_module


def document():
    return dict(schema='epl9-native-rgb-tables-v1',recipes=[
        dict(watercolor_key=k,curves=[[n*16 for n in range(256)] for _ in range(3)])
        for k in ('0x01010078','0x01020078')])


class NativeRgbInputTests(unittest.TestCase):
    def test_two_slots_three_curves_are_copied_and_endpoint_offsets_allowed(self):
        source = document()
        source['recipes'][0]['curves'][0] = [128+n*14 for n in range(256)]
        tables = rgb_tables(source)
        self.assertEqual(tables['0x01010078'][0][0],128)
        self.assertEqual(tables['0x01020078'][2][-1],4080)
        source['recipes'][0]['curves'][0][0] = 0
        self.assertEqual(tables['0x01010078'][0][0],128)

    def test_unexpected_fields_slots_duplicates_and_shapes_are_rejected(self):
        source = document()
        candidates = [None,{},dict(source,ignored=True),dict(source,schema='other'),
                      dict(source,recipes=source['recipes'][:1])]
        for field,value in (('watercolor_key','0x01030078'),('watercolor_key',0x01010078),
                            ('curves',[[0]*256]*2),('curves',[None]*3),('extra',1)):
            changed = deepcopy(source)
            changed['recipes'][0][field] = value
            candidates.append(changed)
        duplicate = deepcopy(source)
        duplicate['recipes'][1]['watercolor_key'] = duplicate['recipes'][0]['watercolor_key']
        candidates.append(duplicate)
        for candidate in candidates:
            with self.subTest(candidate=str(candidate)[:80]):
                with self.assertRaises(ValueError): rgb_tables(candidate)

    def test_folded_short_and_out_of_range_values_cannot_reach_binary_packing(self):
        for values in ([0]*255,[0]*257,[0]*255+[4096],[-1]+[0]*255,
                       [0]*255+[True],[0]*255+[1.5],[1,0]+[16]*254):
            source = document()
            source['recipes'][1]['curves'][2] = values
            with self.assertRaises(ValueError): rgb_tables(source)

    def test_diagnostic_and_supplied_tables_are_mutually_exclusive(self):
        with self.assertRaisesRegex(ValueError,'not both'):
            build_late_module(b'',diagnostic_rgb=True,rgb_document=document())


if __name__ == '__main__':
    unittest.main()
