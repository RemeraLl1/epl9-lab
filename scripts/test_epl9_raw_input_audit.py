"""Bounds checks for expanded RAW input; no original media or firmware."""
import unittest

from epl9_job_probe import validate_bayer_source


class RawInputTests(unittest.TestCase):
    def test_expanded_source_accepts_bounded_readonly_backing(self):
        source=dict(width=64,height=2,stride=64,data=bytes(256))
        for fmt in (0x108,0x109):
            validate_bayer_source(source,64,2,fmt)

    def test_rejects_truncated_unaligned_and_mutable_backing(self):
        good=dict(width=64,height=2,stride=64,data=bytes(256))
        for change in (dict(data=bytes(255)),dict(stride=65,data=bytes(260)),
                       dict(data=bytearray(256)),dict(height=3473),dict(stride=4736)):
            with self.assertRaises(ValueError):
                validate_bayer_source(dict(good,**change),64,2,0x108)

    def test_raw_window_must_fit_and_packed_format_is_not_expanded(self):
        source=dict(width=64,height=2,stride=64,data=bytes(256))
        with self.assertRaises(ValueError): validate_bayer_source(source,65,2,0x108)
        with self.assertRaises(ValueError): validate_bayer_source(source,64,3,0x108)
        with self.assertRaises(ValueError): validate_bayer_source(source,64,2,0x107)


if __name__=='__main__':
    unittest.main()
