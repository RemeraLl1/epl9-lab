from pathlib import Path
import tempfile
import unittest

import numpy as np
from PIL import Image, TiffImagePlugin

from epl9_workspace_pixels import compare, load_tiff, pixel_metrics


class WorkspacePixelTests(unittest.TestCase):
    def test_metadata_change_is_not_a_pixel_change(self):
        with tempfile.TemporaryDirectory() as directory:
            loaded = []
            for name, software in [('a.tif', 'export A'), ('b.tif', 'export B')]:
                path = Path(directory)/name
                tags = TiffImagePlugin.ImageFileDirectory_v2()
                tags[305] = software
                Image.new('RGB', (3, 2), (90, 70, 40)).save(
                    path, tiffinfo=tags, icc_profile=b'same synthetic test profile')
                loaded.append(load_tiff(path))
            a, am = loaded[0]
            b, bm = loaded[1]
            self.assertNotEqual(am['file_sha256'], bm['file_sha256'])
            self.assertTrue(compare(a, b, am, bm)['pixel_identical'])

    def test_pixel_and_channel_range_changes_are_measured_without_uint8_wrap(self):
        before = np.array([[[255, 0, 0], [80, 80, 80]]], dtype=np.uint8)
        after = np.array([[[85, 85, 85], [80, 80, 80]]], dtype=np.uint8)
        result = compare(before, after, dict(file='a', icc_sha256='same'),
                         dict(file='b', icc_sha256='same'))
        self.assertEqual(result['different_pixels'], 1)
        self.assertEqual(result['different_fraction'], 0.5)
        self.assertEqual(result['maximum_abs_difference'], 170)
        self.assertEqual(pixel_metrics(after)['mean_channel_range'], 0)

    def test_different_geometry_or_profile_is_rejected(self):
        a = np.zeros((2, 3, 3), dtype=np.uint8)
        with self.assertRaisesRegex(ValueError, 'geometry'):
            compare(a, a[:1], {}, {})
        with self.assertRaisesRegex(ValueError, 'ICC'):
            compare(a, a, dict(icc_sha256='a'), dict(icc_sha256='b'))

    def test_missing_profile_and_non_rgb_file_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            for mode in ('RGB', 'L'):
                path = Path(directory)/(mode+'.tif')
                Image.new(mode, (3, 2)).save(path)
                with self.assertRaises(ValueError):
                    load_tiff(path)


if __name__ == '__main__':
    unittest.main()
