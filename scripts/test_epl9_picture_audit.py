import struct
import unittest
from epl9_picture_audit import jpeg_end, directory, BASE


class PictureTests(unittest.TestCase):
    def test_embedded_thumbnail_eoi_is_not_main_eoi(self):
        blob = b'\xff\xd8\xff\xe1\x00\x06\xff\xd8\xff\xd9\xff\xda\x00\x02abc\xff\x00z\xff\xd0x\xff\xd9'
        self.assertEqual(jpeg_end(blob+b'padding'), len(blob))

    def test_multiple_scans(self):
        blob = b'\xff\xd8\xff\xda\x00\x02abc\xff\xc4\x00\x02\xff\xda\x00\x02xyz\xff\xd9'
        self.assertEqual(jpeg_end(blob), len(blob))

    def test_truncated_and_invalid_jpeg_rejected(self):
        for blob in (b'', b'\xff\xd8', b'\xff\xd8\xff\xe1\x00\x10x', b'\xff\xd8x\xff\xd9'):
            with self.assertRaises(ValueError):
                jpeg_end(blob)

    def test_zero_size_slots_and_bounds(self):
        blob = struct.pack('<4I', BASE+32, 4, 0, 0)+struct.pack('<4I', BASE+36, 0, 0, 0)+b'\xff\xd8\xff\xd9'
        slots, rows = directory(blob)
        self.assertEqual((slots, len(rows), rows[0][0]), (2, 1, 0))
        with self.assertRaises(ValueError):
            directory(blob[:-1])


if __name__ == '__main__':
    unittest.main()
