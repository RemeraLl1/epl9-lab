import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from epl9_native_source_package import (GENERATION, CANDIDATE_NAME, MAIN_HASH, OSD_HASH,
    MODULE_BASE, MODULE_BYTES, BASE, DEFAULTS, EXPECTED_HOOKS, overlay_spans,
    PRIVATE_ARCHIVE_INPUTS, verify_protected, pinned, save_archive, module_main, build)
from epl9_v3_package import generation_inputs, CANDIDATE_HASHES, PRIVATE_CANDIDATE_HASHES
from epl9_workspace_bridge import sha


class NativeSourcePackageTests(unittest.TestCase):
    def setUp(self):
        self.originals = {0x100:bytes(range(128)),0x101:bytes(range(128,256))}
        self.patches = [dict(kind=0x100,offset=7,before=self.originals[0x100][7:10],
            after=b'abc',label='main'),dict(kind=0x101,offset=40,
            before=self.originals[0x101][40:42],after=b'XY',label='icon')]
        self.replacements = {k:bytearray(v) for k,v in self.originals.items()}
        for patch in self.patches:
            self.replacements[patch['kind']][patch['offset']:patch['offset']+len(patch['after'])] = patch['after']
        self.replacements = {k:bytes(v) for k,v in self.replacements.items()}

    def test_generation_is_separate_and_old_defaults_still_reject_new_generation(self):
        self.assertEqual(GENERATION,'native-source-v1')
        self.assertNotIn(MAIN_HASH,(CANDIDATE_HASHES[0x100],PRIVATE_CANDIDATE_HASHES[0x100]))
        self.assertEqual(OSD_HASH,CANDIDATE_HASHES[0x101])
        self.assertNotEqual(CANDIDATE_NAME,generation_inputs('frozen-v3')[3])
        self.assertNotEqual(CANDIDATE_NAME,generation_inputs('private-color-v3')[3])
        with self.assertRaises(ValueError):
            generation_inputs(GENERATION)
        for wrong in ('frozen-v3','private-color-v3','native-source-v2'):
            with self.assertRaisesRegex(ValueError,'generation'):
                build(Path('/tmp/not-created-native-source'),generation=wrong)

    def test_exact_overlay_has_exhaustive_byte_guards_and_addresses(self):
        rows = overlay_spans(self.originals,self.replacements,list(reversed(self.patches)))
        self.assertEqual([r['kind'] for r in rows],['0x100','0x101'])
        self.assertEqual(rows[0]['address'],hex(BASE+7))
        self.assertEqual(rows[0]['end'],'0xa')
        self.assertEqual(rows[0]['before_sha256'],sha(self.patches[0]['before']))
        self.assertEqual(sum(r['changed_bytes'] for r in rows),5)
        self.assertIn('old',rows[0])
        self.assertIn('new',rows[0])

    def test_overlay_rejects_undeclared_change(self):
        changed = dict(self.replacements)
        changed[0x100] = changed[0x100][:-1]+b'!'
        with self.assertRaisesRegex(ValueError,'outside declared'):
            overlay_spans(self.originals,changed,self.patches)

    def test_overlay_rejects_missing_or_extra_components_and_resizing(self):
        for originals,replacements in (({0x100:b'a'},{0x100:b'b'}),
                (self.originals,{**self.replacements,0x102:b'a'}),
                (self.originals,{**self.replacements,0x101:b'a'})):
            with self.assertRaises(ValueError):
                overlay_spans(originals,replacements,self.patches)

    def test_overlay_rejects_overlap_negative_out_of_bounds_and_wrong_old_guard(self):
        for changed in (dict(self.patches[0],offset=-1),
                dict(self.patches[0],offset=127),
                dict(self.patches[0],before=b'bad'),
                dict(self.patches[0],before=b'',after=b''),
                dict(self.patches[0],after=b'long'),
                dict(self.patches[0],kind=0x102)):
            with self.assertRaises(ValueError):
                overlay_spans(self.originals,self.replacements,[changed])
        with self.assertRaisesRegex(ValueError,'boundary'):
            overlay_spans(self.originals,self.replacements,self.patches+[self.patches[0]])

    def test_overlay_rejects_unchanged_spans(self):
        patch = dict(self.patches[0],after=self.patches[0]['before'])
        with self.assertRaisesRegex(ValueError,'does not change'):
            overlay_spans(self.originals,self.originals,[patch])

    def test_protected_spans_require_exact_original_bytes(self):
        original,replacement = self.originals[0x100],self.replacements[0x100]
        ranges = {'unchanged':(BASE+20,BASE+24)}
        rows = verify_protected(original,replacement,ranges)
        self.assertEqual(rows[0]['sha256'],sha(original[20:24]))
        with self.assertRaisesRegex(ValueError,'dependency modified'):
            verify_protected(original,replacement,{'changed':(BASE,BASE+12)})
        for span in ((BASE-1,BASE+4),(BASE+1,BASE+200),(BASE+4,BASE+4)):
            with self.assertRaisesRegex(ValueError,'outside main'):
                verify_protected(original,replacement,{'bad':span})

    def test_pinned_inputs_reject_changed_bytes_and_size(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'input'
            path.write_bytes(b'pin me')
            self.assertEqual(pinned(path,sha(b'pin me'),6),b'pin me')
            with self.assertRaisesRegex(ValueError,'identity mismatch'):
                pinned(path,sha(b'pin me'),8)
            path.write_bytes(b'PIN ME')
            with self.assertRaisesRegex(ValueError,'identity mismatch'):
                pinned(path,sha(b'pin me'))

    def test_reproduction_archive_deterministic_and_readable_without_vendor_sources(self):
        sources = {'scripts/example.py':b'print("offline")\n','recipes/example.json':b'{}\n'}
        private = {name:json.dumps({'private-test-input':key}).encode()
                   for key,name in PRIVATE_ARCHIVE_INPUTS.items()}
        with tempfile.TemporaryDirectory() as folder:
            a,b = Path(folder)/'a.zip',Path(folder)/'b.zip'
            save_archive(a,sources,private)
            save_archive(b,sources,private)
            self.assertEqual(a.read_bytes(),b.read_bytes())
            with zipfile.ZipFile(a) as archive:
                self.assertEqual(set(archive.namelist()),set(sources)|{'private-inputs/'+n for n in private})
                for name,data in private.items():
                    self.assertEqual(archive.read('private-inputs/'+name),data)
            with self.assertRaises(FileExistsError):
                save_archive(a,sources,private)

    def test_reproduction_archive_rejects_missing_metadata_or_firmware_inputs(self):
        private = {name:b'private source metadata' for name in PRIVATE_ARCHIVE_INPUTS.values()}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'forbidden.zip'
            for changed in ({'native-rgb-tables.json':b'{}'},
                    {**private,'firmware.bin':b'not allowed'},
                    {**private,'decoded-overlay.json':b'not source'},
                    {**private,'native-source-module.s':'not bytes'}):
                with self.assertRaisesRegex(ValueError,'source archive requires exact'):
                    save_archive(path,{},changed)
                self.assertFalse(path.exists())

    def test_native_source_keeps_new_gain_site_not_old_constructor(self):
        hooks = {p[0] for p in EXPECTED_HOOKS}
        self.assertEqual(len(hooks),4)
        self.assertIn(0x60761c9e,hooks)
        self.assertNotIn(0x6074f352,hooks)
        self.assertEqual(DEFAULTS['module'].parent,DEFAULTS['main'].parent)

    def test_module_main_requires_exact_stock_padding_and_hook_guard(self):
        at = MODULE_BASE-BASE
        original = bytes(at)+b'\xff'*MODULE_BYTES+bytes(64)
        module = dict(data=b'X'*MODULE_BYTES,patches=[])
        result = module_main(original,module)
        self.assertEqual(result[at:at+MODULE_BYTES],module['data'])
        self.assertEqual(len(result),len(original))
        with self.assertRaisesRegex(ValueError,'padding'):
            module_main(result,module)
        module['patches'] = [dict(address=BASE,before='01',after='02')]
        with self.assertRaisesRegex(ValueError,'hook guard'):
            module_main(original,module)


if __name__ == '__main__':
    unittest.main()
