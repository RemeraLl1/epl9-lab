from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from epl9_film_module import ROOT, build_module, emit_files


class ModuleGuards(unittest.TestCase):
    def test_unknown_firmware_rejected_before_reading_recipe_data(self):
        for data in (b'',b'E-PL9',b'\x00'*1024):
            with self.assertRaisesRegex(ValueError,'exact E-PL9'):
                build_module(data)

    def test_public_output_and_overwrite_rejected_before_tool_invocation(self):
        for path in (ROOT/'firmware_src',ROOT/'native-module-public'):
            with self.assertRaisesRegex(ValueError,'ignored local'):
                emit_files({},path)

    def test_wrong_reader_rejected_without_creating_partial_output(self):
        with TemporaryDirectory(dir=ROOT/'local') as temp:
            root = Path(temp)
            reader = root/'reader.exe'
            reader.write_bytes(b'unqualified')
            out = root/'output'
            with self.assertRaisesRegex(ValueError,'inspected GNU reader'):
                emit_files({},out,reader=reader)
            self.assertFalse(out.exists())


if __name__ == '__main__':
    unittest.main()
