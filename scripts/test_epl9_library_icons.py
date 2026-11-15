import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from epl9_film_icons import artwork, encode_rle
from epl9_library_icons import CATALOG, build, load_catalog
from epl9_osd_audit import load_decoder


class LibraryIconTests(unittest.TestCase):
    def test_roster_and_replacements(self):
        rows=load_catalog()['recipes']
        self.assertEqual(rows[9]['id'],'neon-city')
        self.assertEqual(rows[16]['id'],'astra')
        self.assertTrue(rows[16]['group_requires_review'])
        self.assertEqual(rows[6]['id'],'vision3-500t')
        self.assertEqual(rows[25]['id'],'lomo-cn800')

    def test_frozen_pair_pixels_unchanged(self):
        for badge,sha in [('G200','a17f62606fec9aa9c6e2bd945a9e7289788007f85a17a9c972c9fb957d6ff044'),
                          ('P400','3022dc645bf99fe328669b0dc3d12a8ce25157593ff5f5b6e6c75f2392d9bf8b')]:
            self.assertEqual(hashlib.sha256(artwork(badge)).hexdigest(),sha)

    def test_all31_independent_decoder_roundtrip_both_formats_and_sizes(self):
        decoder=load_decoder()
        seen=set()
        for row in load_catalog()['recipes']:
            self.assertNotIn(artwork(row['badge']),seen)
            seen.add(artwork(row['badge']))
            for w,h in [(44,32),(22,16),(88,64)]:
                for mode,ink in [(1,3),(11,103)]:
                    pixels=bytes(ink if v else 0 for v in artwork(row['badge'],w,h))
                    payload=encode_rle(pixels,w,h,mode)
                    decoded,dw,dh,dm,used=decoder.decode_rle(payload,w,h)
                    self.assertEqual((decoded,dw,dh,dm),(pixels,w,h,mode))
                    self.assertLessEqual(used,len(payload))

    def test_build_no_firmware_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'assets'
            report=build(CATALOG,out)
            self.assertFalse(report['install_ready'])
            self.assertFalse(report['firmware_modified'])
            self.assertEqual(len(list(out.glob('*.svg'))),31)
            self.assertEqual(len(list(out.iterdir())),33)
            with self.assertRaises(ValueError): build(CATALOG,out)

    def test_catalog_rejects_duplicate_badge_reorder_and_native_assignment(self):
        for change in ['badge','order','native']:
            data=json.loads(CATALOG.read_text())
            if change=='badge': data['recipes'][2]['badge']='G200'
            if change=='order': data['recipes'].reverse()
            if change=='native': data['recipes'][2]['native_art_id']='0x801'
            with tempfile.TemporaryDirectory() as td:
                path=Path(td)/'bad.json'; path.write_text(json.dumps(data))
                with self.assertRaises(ValueError): load_catalog(path)

if __name__=='__main__': unittest.main()
