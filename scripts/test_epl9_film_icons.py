"""Encoder boundary vectors against hand-derived token layout."""
import unittest
from epl9_film_icons import encode_rle


class IconEncoderTests(unittest.TestCase):
    def test_mode11_splits_run_at_sixteen(self):
        # Header 17x1; white index 4, runs 16 and 1: 0x04f, 0x040.
        self.assertEqual(encode_rle(bytes([4])*17,17,1), bytes.fromhex('0000010b4f0004'))

    def test_mode11_groups_five_tokens_with_four_padding_bits(self):
        pixels = bytes([1,2,3,4,5,6])
        expected = bytes.fromhex('0050000b') + int('050040030020010',16).to_bytes(8,'little') + b'\x60\x00'
        self.assertEqual(encode_rle(pixels,6,1),expected)

    def test_inline_two_bit_levels_and_four_pixel_runs(self):
        self.assertEqual(encode_rle(bytes([3])*5,5,1,1),bytes.fromhex('00400001cf'))

    def test_mode11_identical_pixels_on_two_rows_remain_two_runs(self):
        # Two 3-pixel rows: tokens 0x042, 0x042, never one 6-pixel run.
        self.assertEqual(encode_rle(bytes([4])*6,3,2),bytes.fromhex('0120000b422004'))

    def test_inline_identical_pixels_on_two_rows_remain_two_runs(self):
        # Colour 3, run 3 -> nibble 0xE twice; row width is below run limit 4.
        self.assertEqual(encode_rle(bytes([3])*6,3,2,1),bytes.fromhex('01200001ee'))

    def test_rejects_incompatible_dimensions_and_palette(self):
        for pixels,w,h,mode in [(b'',0,1,11),(b'\0',2,1,11),(b'\x04',1,1,1)]:
            with self.assertRaises(ValueError):
                encode_rle(pixels,w,h,mode)


if __name__ == '__main__':
    unittest.main()
