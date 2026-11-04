import copy
import json
from pathlib import Path
import struct
import unittest

from epl9_tonal_drafts import (definitions, remap_curve, scale_wb, validate_curve,
                               validate_knots, wb_entries, tone_entries)
from epl9_workspace_bridge import Epl9Orf
from test_epl9_workspace_bridge import synthetic_orf


def wb_fixture():
    data = synthetic_orf()
    struct.pack_into('<H', data, 1088, 4)
    for i, tag in enumerate((0x100, 0x101)):
        where = 1400+8*i
        struct.pack_into('<HHII', data, 1088+2+12*(2+i), tag, 3, 4, where-1024)
        struct.pack_into('<4H', data, where, 496, 496, 256, 256)
    return data


class CurveTests(unittest.TestCase):
    def test_identity_remap_preserves_a_nonlinear_stock_gamma_exactly(self):
        curve = [(i*i*4095+32512)//65025 for i in range(256)]
        self.assertEqual(remap_curve(curve, [[0, 0], [4095, 4095]]), curve)

    def test_composition_uses_stock_output_code_instead_of_knot_index(self):
        stock = [0]*128+[1024]*64+[4095]*64
        remapped = remap_curve(stock, [[0, 0], [2048, 1024], [4095, 4095]])
        self.assertEqual((remapped[0], remapped[128], remapped[255]), (0, 512, 4095))

    def test_knots_cannot_fold_repeat_inputs_or_leave_range(self):
        for knots in ([[0, 0], [0, 10], [4095, 4095]], [[0, 10], [4095, 0]],
                      [[0, 0], [4095, 4096]], [[True, 0], [4095, 4095]], [[1, 0], [4095, 4095]]):
            with self.assertRaises(ValueError):
                validate_knots(knots)
        with self.assertRaises(ValueError):
            validate_curve([0]*255+[4096])


class WhiteBalanceTests(unittest.TestCase):
    def test_relative_rb_scales_preserve_both_green_references(self):
        self.assertEqual(scale_wb((496, 496, 256, 256), 1080, 880), (536, 436, 256, 256))
        self.assertEqual(scale_wb((496, 496, 256, 256), 1035, 940), (513, 466, 256, 256))

    def test_zero_overflow_and_out_of_range_gain_are_rejected(self):
        for vector, r, b in [((0, 496, 256, 256), 1000, 1000),
                             ((65535, 496, 256, 256), 1080, 880),
                             ((496, 496, 256, 256), 1200, 1000),
                             ((496, 496, 256, 256), True, 1000)]:
            with self.assertRaises(ValueError):
                scale_wb(vector, r, b)

    def test_existing_two_wb_spans_are_qualified(self):
        entries, values = wb_entries(Epl9Orf(bytes(wb_fixture())))
        self.assertEqual([e['offset'] for e in entries], [1400, 1408])
        self.assertEqual(values, (496, 496, 256, 256))

    def test_wb_alias_or_metadata_raw_overlap_is_rejected(self):
        for target in (1400, 2100, 200000):
            data = wb_fixture()
            struct.pack_into('<I', data, 1088+2+12*3+8, target-1024)
            struct.pack_into('<4H', data, target, 496, 496, 256, 256)
            with self.assertRaises(ValueError):
                wb_entries(Epl9Orf(bytes(data)))


class TonalRecipeTests(unittest.TestCase):
    def test_v2_stock_tone_bounds_and_slot_bindings(self):
        path = Path(__file__).resolve().parents[1]/'recipes/epl9-film-drafts-v2.json'
        document = json.loads(path.read_text())
        rows = definitions(document)
        self.assertEqual(rows[1]['tone_level']['shadows'], 3)
        for field, value in [('picture_mode_contrast', 3), ('picture_mode_contrast', True)]:
            changed = copy.deepcopy(document)
            changed['recipes'][0][field] = value
            with self.assertRaises(ValueError):
                definitions(changed)
        document['recipes'][0]['tone_level']['highlights'] = -8
        with self.assertRaises(ValueError):
            definitions(document)

    def test_tone_entries_require_original_natural_bounds_and_axis_ids(self):
        data = wb_fixture()
        struct.pack_into('<H', data, 1036, 2)
        struct.pack_into('<HHII', data, 1036+2+12, 0x2020, 13, 1, 128)
        struct.pack_into('<H', data, 1152, 3)
        for i, row in enumerate([(0x520, 3, 2, 0x00020002),
                                  (0x523, 8, 3, 1480-1024),
                                  (0x52e, 8, 28, 1490-1024)]):
            struct.pack_into('<HHII', data, 1152+2+12*i, *row)
        struct.pack_into('<3h', data, 1480, 0, -2, 2)
        struct.pack_into('<28h', data, 1490, -31999, 0, -7, 7, -31998, 0, -7, 7,
                         -31997, 0, -7, 7, *([0]*16))
        contrast, tone = tone_entries(Epl9Orf(bytes(data)))
        self.assertEqual((contrast['offset'], tone['offset']), (1480, 1490))
        struct.pack_into('<h', data, 1490, -31998)
        with self.assertRaises(ValueError):
            tone_entries(Epl9Orf(bytes(data)))

    def test_real_definitions_keep_distinct_accepted_slots(self):
        document = json.loads((Path(__file__).resolve().parents[1]/'recipes/epl9-film-drafts-v1.json').read_text())
        recipes = definitions(document)
        self.assertEqual({r['watercolor_key'] for r in recipes}, {'0x01010078', '0x01020078'})
        self.assertNotEqual(recipes[0]['tone_knots'], recipes[1]['tone_knots'])
        altered = copy.deepcopy(document)
        altered['recipes'][1]['watercolor_key'] = recipes[0]['watercolor_key']
        with self.assertRaises(ValueError):
            definitions(altered)


if __name__ == '__main__':
    unittest.main()
