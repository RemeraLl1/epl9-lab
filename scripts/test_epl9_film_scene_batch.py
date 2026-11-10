import struct
import unittest

import numpy as np

from epl9_film_scene_batch import natural_copy, detailed_comparison
from test_epl9_tonal_drafts import wb_fixture


def scene_fixture():
    data = wb_fixture()
    struct.pack_into('<H', data, 1036, 2)
    struct.pack_into('<HHII', data, 1036+2+12, 0x2020, 13, 1, 128)
    struct.pack_into('<H', data, 1152, 6)
    entries = [(0x520, 3, 2, 0x00020004), (0x521, 8, 3, 1480-1024),
               (0x523, 8, 3, 1490-1024), (0x524, 8, 3, 1500-1024),
               (0x525, 3, 1, 0), (0x526, 3, 1, 0)]
    for index, row in enumerate(entries):
        struct.pack_into('<HHII', data, 1152+2+12*index, *row)
    for at in (1480, 1490, 1500):
        struct.pack_into('<3h', data, at, 0, -2, 2)
    return data


class SceneBatchTests(unittest.TestCase):
    def test_mode_normalization_changes_only_qualified_halfword(self):
        original = bytes(scene_fixture())
        result, mode = natural_copy(original)
        self.assertEqual(mode, [4, 2])
        expected = bytearray(original)
        struct.pack_into('<H', expected, 1152+2+8, 2)
        self.assertEqual(result, expected)

    def test_non_neutral_settings_and_unknown_modes_are_rejected(self):
        for at, value in ((1152+2+8, 19), (1480, 1), (1490, 1), (1500, -1),
                          (1152+2+12*4+8, 1)):
            data = scene_fixture()
            struct.pack_into('<h', data, at, value)
            with self.assertRaises(ValueError):
                natural_copy(bytes(data))

    def test_clipping_counts_only_new_channel_endpoints_and_empty_bands_are_null(self):
        before = np.array([[[0, 4, 255], [6, 128, 250]]], dtype=np.uint8)
        after = np.array([[[0, 0, 255], [0, 129, 255]]], dtype=np.uint8)
        meta = dict(file='test.tif', icc_sha256='same')
        result = detailed_comparison(before, after, meta, meta)
        self.assertEqual(result['new_zero_channels'], 2)
        self.assertEqual(result['new_full_scale_channels'], 1)
        self.assertEqual(result['different_pixels'], 2)
        self.assertEqual(sum(b['pixels'] for b in result['bands']), 2)
        self.assertIsNone(result['bands'][-1]['mean_after'])
        with self.assertRaisesRegex(ValueError, 'ICC'):
            detailed_comparison(before, after, meta, dict(meta, icc_sha256='other'))


if __name__ == '__main__':
    unittest.main()
