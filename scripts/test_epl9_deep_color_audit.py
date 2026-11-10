"""Synthetic safety/interpretation checks; no firmware or camera required."""
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from epl9_deep_color_audit import checked_image, checked_output, curve_summary, unchanged_outside, ROOT


class DeepColorAuditTests(unittest.TestCase):
    def test_wrong_image_rejected(self):
        with self.assertRaisesRegex(ValueError, 'exact E-PL9'):
            checked_image(b'wrong model')
        # Right size is insufficient: the SHA gate must also reject it.
        with self.assertRaisesRegex(ValueError, 'exact E-PL9'):
            checked_image(bytes(26214336))

    def test_output_must_be_new_and_local(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'local') as directory:
            with self.assertRaises(ValueError):
                checked_output(Path(directory))
            checked_output(Path(directory)/'new-result')
        with self.assertRaises(ValueError):
            checked_output(ROOT/'local'/'..'/'outside-audit-test')

    def test_wrong_image_cli_never_runs_reader_or_creates_output(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'local') as directory:
            source, output = Path(directory)/'wrong.bin', Path(directory)/'out'
            source.write_bytes(b'not firmware')
            with patch('sys.argv', ['audit', '--image', str(source), '--out', str(output)]), \
                    patch('epl9_deep_color_audit.subprocess.run') as reader:
                from epl9_deep_color_audit import main
                with self.assertRaises(ValueError):
                    main()
                reader.assert_not_called()
            self.assertFalse(output.exists())

    def test_curve_summary_and_nonmonotone_detection(self):
        values = list(range(0, 1024, 4))
        data = struct.pack('<256H', *values)
        result = curve_summary(data, 0, 1023)
        self.assertTrue(result['monotone'])
        self.assertEqual(result['samples']['128'], 512)
        values[128] = 1
        self.assertFalse(curve_summary(struct.pack('<256H', *values), 0, 1023)['monotone'])

    def test_curve_bounds_and_range(self):
        for offset in (-1, 2):
            with self.assertRaises(ValueError):
                curve_summary(bytes(512), offset, 1023)
        with self.assertRaises(ValueError):
            curve_summary(struct.pack('<H', 1024)+bytes(510), 0, 1023)

    def test_unrelated_byte_changes_are_detected(self):
        before, after = bytes(16), bytearray(16)
        after[4] = 1
        self.assertTrue(unchanged_outside(before, after, [(4, 8)]))
        after[8] = 1
        self.assertFalse(unchanged_outside(before, after, [(4, 8)]))
        self.assertFalse(unchanged_outside(before, after[:-1], [(4, 8)]))


if __name__ == '__main__':
    unittest.main()
