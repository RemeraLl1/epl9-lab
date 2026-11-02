"""Synthetic rejection tests for the pinned parser and E-PL9 input guard."""
import tempfile
from pathlib import Path
import unittest

from epl9_osd_audit import load_decoder, verified_bytes, check_labels


class OSDTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.decoder = load_decoder()

    def test_valid_short_stream(self):
        # Two pixels, palette index 4, one 12-bit run token (mode 11).
        pixels, w, h, mode, _ = self.decoder.decode_rle(bytes.fromhex('0010000b4100'), 2, 1)
        self.assertEqual((pixels, w, h, mode), (b'\x04\x04', 2, 1, 11))

    def test_bad_streams(self):
        for stream in ('0010000b', '0010000b4200', '001000ff4100',
                       '0010000b4100000000000010', '0010000b410001'):
            with self.subTest(stream=stream), self.assertRaises(ValueError):
                self.decoder.decode_rle(bytes.fromhex(stream), 2, 1)

    def test_dimension_mismatch(self):
        with self.assertRaises(ValueError):
            self.decoder.decode_rle(bytes.fromhex('0010000b4100'), 3, 1)

    def test_identity_guard(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'not-firmware'
            path.write_bytes(b'wrong')
            with self.assertRaises(ValueError):
                verified_bytes(path, '0' * 64, 5)
            with self.assertRaises(ValueError):
                load_decoder(path)

    def test_label_mismatch(self):
        with self.assertRaises(ValueError):
            check_labels(bytes(32))


if __name__ == '__main__':
    unittest.main()
