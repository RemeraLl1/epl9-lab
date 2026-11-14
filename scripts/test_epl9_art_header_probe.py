import tempfile
from pathlib import Path
import unittest
from epl9_art_header_probe import execute,load_code


class HeaderProbeContract(unittest.TestCase):
    def test_mode_bounds(self):
        for mode in (-1,0,99,256):
            with self.assertRaises(ValueError): execute({},mode,1)
    def test_variant_bounds(self):
        for variant in (-1,256):
            with self.assertRaises(ValueError): execute({},120,variant)
    def test_missing_native_code_not_success(self):
        with self.assertRaisesRegex(ValueError,'unexpected native stop'):
            execute({},120,1)
    def test_wrong_stock_rejected_before_reader(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'main.bin';p.write_bytes(b'not OEM')
            with self.assertRaisesRegex(ValueError,'exact stock'):
                load_code(p,Path(directory)/'absent-reader')

if __name__=='__main__': unittest.main()
