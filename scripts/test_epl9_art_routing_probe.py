"""Synthetic checks for the offline lookup; no firmware or camera required."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from epl9_art_routing_probe import ROOT, lookup, mode_key


class RoutingModelTests(unittest.TestCase):
    def test_header_byte_order_and_variants(self):
        self.assertEqual(mode_key(bytes([1, 1, 0x78, 0])), 0x01010078)
        self.assertEqual(mode_key(bytes([1, 2, 0x78, 0])), 0x01020078)
        self.assertEqual(mode_key(bytes([0, 0, 11, 0])), 11)
        self.assertEqual(mode_key(bytes([1, 3, 0x34, 0x12])), 0x01031234)
        with self.assertRaises(ValueError):
            mode_key(b'\x01\x01\x78')

    def test_variant_collision_is_not_collapsed(self):
        rows = [(0, 0)] * 32
        rows[17] = (0x11, 0x1000)
        rows[18] = (0x10011, 0x2000)
        self.assertEqual(lookup(rows, 0x01010078)['target'], 0x1000)
        second = lookup(rows, 0x01020078)
        self.assertEqual(second['target'], 0x2000)
        self.assertEqual(second['visited'], [17, 18])

    def test_wraparound_and_absent(self):
        rows = [(0x10011, 0x2000), (0x21, 0x3000), (0x31, 0x4000), (0x41, 0x5000)]
        self.assertEqual(lookup(rows, 0x01020078)['visited'], [1, 2, 3, 0])
        rows[3] = (0, 0)
        self.assertEqual(lookup(rows, 0x01020078)['status'], 'absent')

    def test_guarded_range_and_corrupt_table(self):
        self.assertEqual(lookup([(0, 0)] * 16, 11)['status'], 'outside_key_range')
        with self.assertRaises(ValueError):
            lookup([(1, 0)] * 16, 0x01010078)
        with self.assertRaises(ValueError):
            lookup([(0, 0)] * 3, 0x01010078)

    def test_wrong_image_rejected_before_reader_or_output(self):
        (ROOT / 'local').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / 'local') as directory:
            directory = Path(directory)
            image = directory / 'synthetic.bin'
            image.write_bytes(b'synthetic, not firmware')
            output = directory / 'rejected'
            result = subprocess.run([sys.executable, str(ROOT / 'scripts/epl9_art_routing_probe.py'),
                                     '--image', str(image), '--reader', str(directory / 'missing.exe'),
                                     '--out', str(output)], text=True, capture_output=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn('requires exact decoded E-PL9', result.stderr)
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
