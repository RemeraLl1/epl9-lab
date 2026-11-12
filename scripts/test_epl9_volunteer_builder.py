"""Small failure controls; opt-in exact-stock integration, no camera access."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import epl9_volunteer_builder as b


class BuilderControls(unittest.TestCase):
    def test_bad_identity(self):
        with self.assertRaises(ValueError):
            b.identified(b'bad',b.STOCK_SHA)

    def test_wrong_size_before_read(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'wrong.bin';p.write_bytes(b'OE\x14\x20')
            with self.assertRaisesRegex(ValueError,'exact'):
                b.load_stock(p)

    def test_missing_input(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                b.load_stock(Path(d)/'missing.bin')

    def test_stock_or_patch_cannot_bypass_sha(self):
        with self.assertRaisesRegex(ValueError,'stock identity'):
            b.build_bytes(b'not stock')

    def test_icon_inventory(self):
        with self.assertRaises(ValueError):
            b.make_icons(bytes(100),[])

    def test_icon_bounds(self):
        rows=json.loads(b.LAYOUT.read_text())
        rows[0]['offset']=-1
        with self.assertRaisesRegex(ValueError,'icon span'):
            b.make_icons(bytes(18000000),rows)

    def test_icon_original_guard(self):
        rows=json.loads(b.LAYOUT.read_text())
        with self.assertRaisesRegex(ValueError,'original icon identity'):
            b.make_icons(bytes(18000000),rows)

    def test_outside_output_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,'under this checkout'):
                b.write_outputs(Path(d)/'out',{'x.bin':b'a'}, {})

    def test_existing_output_preserved(self):
        with tempfile.TemporaryDirectory() as d,patch.object(b,'ROOT',Path(d)):
            out=Path(d)/'local/out';out.mkdir(parents=True)
            marker=out/'keep';marker.write_bytes(b'unchanged')
            with self.assertRaisesRegex(ValueError,'already exists'):
                b.write_outputs(out,{'x.bin':b'a'}, {})
            self.assertEqual(marker.read_bytes(),b'unchanged')

    def test_readback_and_completion_receipt(self):
        with tempfile.TemporaryDirectory() as d,patch.object(b,'ROOT',Path(d)):
            out=Path(d)/'local/out'
            b.write_outputs(out,{'x.bin':b'abc'}, {'install_ready':False})
            self.assertEqual((out/'x.bin').read_bytes(),b'abc')
            receipt=json.loads((out/'manifest.json').read_text())
            self.assertTrue(receipt['output_readback_verified'])
            self.assertFalse(receipt['install_ready'])

    def test_partial_write_has_no_completion_receipt(self):
        with tempfile.TemporaryDirectory() as d,patch.object(b,'ROOT',Path(d)):
            out=Path(d)/'local/out'
            # Force independent readback failure after successful file write.
            with patch.object(b,'identified',side_effect=ValueError('bad disk bytes')):
                with self.assertRaises(ValueError):
                    b.write_outputs(out,{'x.bin':b'abc'}, {})
            self.assertTrue((out/'x.bin').exists())
            self.assertFalse((out/'manifest.json').exists())


@unittest.skipUnless(os.getenv('EPL9_STOCK_BIN'),'set EPL9_STOCK_BIN for exact private input')
class ExactStockBuild(unittest.TestCase):
    def test_frozen_pair_from_original_only(self):
        path=Path(os.environ['EPL9_STOCK_BIN'])
        stock=b.load_stock(path)
        files,receipt=b.build_bytes(stock)
        self.assertEqual(b.sha(files[b.CANDIDATE_NAME]),b.CANDIDATE_HASH)
        self.assertEqual(b.sha(files[b.RESTORE_NAME]),b.RESTORE_HASH)
        self.assertEqual(b.sha(path.read_bytes()),b.STOCK_SHA)
        self.assertFalse(receipt['install_ready'])
        self.assertFalse(receipt['camera_accessed'])
        self.assertEqual(receipt['derived_rgb_sha256'],b.RGB_HASH)


if __name__=='__main__': unittest.main()
