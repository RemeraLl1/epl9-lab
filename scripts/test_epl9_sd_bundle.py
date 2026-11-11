"""Host recipe authoring and staging contracts; no firmware or camera inputs."""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from epl9_sd_bundle import stage, verify, rehearse, read_record, record_path
from epl9_sd_loader_probe import sample_recipe
from epl9_sd_recipes import ROOT, validate_author, compile_author, pack_recipe, read_json


class AuthorTests(unittest.TestCase):
    def setUp(self):
        self.document = json.loads((ROOT/'recipes/epl9-sd-example-v0.json').read_text())

    def test_valid_author_does_not_need_or_compile_a_gamma(self):
        controls = validate_author(self.document)
        self.assertEqual(controls['tone'], (0,0,0))
        self.assertNotIn('gamma', controls)
        with self.assertRaisesRegex(ValueError, 'exact E-PL9'):
            compile_author(self.document, b'')

    def test_malformed_controls_are_rejected_before_compilation(self):
        changes = ({'recipe_id':True}, {'name':'@BAD@'}, {'contrast':False},
            {'native_hsl':[[0,0,0]]*11}, {'native_hsl':[0]*12},
            {'wb_q10':[511,1024]}, {'tone':{'highlights':0,'midtones':0}},
            {'gamma_knots':[[0,0],[0,4095]]}, {'gamma_knots':[[0,0],[4095,False]]})
        for change in changes:
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_author(dict(self.document, **change))

    def test_parameter_normalization_does_not_retain_mutable_author_lists(self):
        document = deepcopy(self.document)
        controls = validate_author(document)
        document['native_hsl'][0][0] = 1000
        document['wb_q10'][0] = 2048
        self.assertEqual(controls['hsl'][0], (0,0,0))
        self.assertEqual(controls['wb_q10'], (1024,1024))

    def test_validation_cli_succeeds_without_private_main(self):
        result = subprocess.run([sys.executable,str(ROOT/'scripts/epl9_sd_recipes.py'),
            'validate-author',str(ROOT/'recipes/epl9-sd-example-v0.json')],
            check=True,capture_output=True,text=True)
        report = json.loads(result.stdout)
        self.assertTrue(report['author_controls_valid'])
        self.assertFalse(report['gamma_compiled'] or report['record_exported'])


class BundleTests(unittest.TestCase):
    def setUp(self):
        base = ROOT/'local/test-temp'
        base.mkdir(parents=True,exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='sd-bundle-',dir=base)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.first = self.root/'first.RCP'
        self.second = self.root/'second.RCP'
        self.first.write_bytes(pack_recipe(sample_recipe()))
        self.second.write_bytes(pack_recipe(replace(sample_recipe(),recipe_id=2,name='Second')))
        self.out = self.root/'bundle'

    def test_defaults_one_override_both_and_swapped_files(self):
        for i, bindings in enumerate(({}, {1:self.first}, {2:self.first},
                                     {1:self.second,2:self.first}, {1:self.first,2:self.first})):
            path = self.root/f'bundle-{i}'
            manifest = stage(bindings,path)
            self.assertEqual(verify(path),manifest)
            report = rehearse(path,self.first,self.second)
            self.assertTrue(report['host_resolution_passed'])
            self.assertEqual(report['slots'][0]['source'],'embedded')
            self.assertEqual([r['source'] for r in report['slots'][1:]],
                             ['sd' if n in bindings else 'embedded' for n in (1,2)])
            self.assertFalse(report['fallback_library_selected'] or report['install_ready'])

    def test_sources_are_snapshotted_before_staging(self):
        original = self.first.read_bytes()
        stage({1:self.first},self.out)
        self.first.write_bytes(self.second.read_bytes())
        self.assertEqual((self.out/record_path(1)).read_bytes(),original)
        verify(self.out)

    def test_invalid_neighbor_prevents_any_output(self):
        self.second.write_bytes(b'invalid')
        with self.assertRaises(ValueError):
            stage({1:self.first,2:self.second},self.out)
        self.assertFalse(self.out.exists())

    def test_unassigned_slots_and_existing_or_external_output_rejected(self):
        for bindings in ({3:self.first}, {True:self.first}):
            with self.assertRaises(ValueError):
                stage(bindings,self.out)
        stage({1:self.first},self.out)
        original = (self.out/'manifest.json').read_bytes()
        with self.assertRaises(ValueError):
            stage({2:self.second},self.out)
        self.assertEqual((self.out/'manifest.json').read_bytes(),original)
        with self.assertRaises(ValueError):
            stage({1:self.first},ROOT/'not-an-authorized-card-target')

    def test_changed_record_or_missing_or_extra_file_rejected(self):
        for i, mutation in enumerate(('changed','missing','extra')):
            path = self.root/f'mutation-{i}'
            stage({1:self.first},path)
            if mutation == 'changed':
                (path/record_path(1)).write_bytes(self.second.read_bytes())
            elif mutation == 'missing':
                (path/record_path(1)).unlink()
            else:
                (path/'EPL9MOD/SLOT03.RCP').write_bytes(self.first.read_bytes())
            with self.assertRaises(ValueError):
                verify(path)

    def test_manifest_cannot_retarget_paths_or_claim_camera_readiness(self):
        for i, change in enumerate(('path','qualification','boolean-id','unknown-field')):
            path = self.root/f'manifest-{i}'
            manifest = stage({1:self.first},path)
            if change == 'path':manifest['slots']['1']['path']='../SLOT02.RCP'
            elif change == 'qualification':manifest['qualification']['install_ready']=True
            elif change == 'boolean-id':manifest['slots']['1']['recipe_id']=True
            else:manifest['extra']='unrecognized'
            (path/'manifest.json').write_text(json.dumps(manifest))
            with self.assertRaises(ValueError):verify(path)

    def test_symlinked_bundle_record_is_rejected(self):
        stage({1:self.first},self.out)
        path = self.out/record_path(1)
        path.unlink()
        path.symlink_to(self.first)
        with self.assertRaises(ValueError):verify(self.out)

    def test_oversized_records_and_ambiguous_json_are_rejected(self):
        self.first.write_bytes(self.first.read_bytes()+b'x')
        with self.assertRaises(ValueError):read_record(self.first)
        path = self.root/'duplicate.json'
        for text in ('{"x":1,"x":2}', '{"x":NaN}', '{"x":Infinity}'):
            path.write_text(text)
            with self.assertRaises(ValueError):read_json(path)
        path.write_bytes(b' '*65537)
        with self.assertRaises(ValueError):read_json(path)


if __name__ == '__main__':
    unittest.main()
