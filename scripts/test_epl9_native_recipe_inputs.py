"""Synthetic input/emission checks, not final recipes or exact-image execution."""
from copy import deepcopy
from dataclasses import FrozenInstanceError
import hashlib
import json
from pathlib import Path
import struct
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from epl9_film_module import BASE, OFFSETS, ROOT, build_module, emit_files
from epl9_film_late_module import build_late_module
import epl9_film_late_module
import epl9_film_late_probe
from epl9_native_recipe_inputs import KEYS, NAMES, NativeRecipeInputs, SCHEMA
from mn103_subset import Machine, Memory, Region


def document():
    # Deliberately synthetic neutral/marker values. These are not the owner's
    # unavailable photographic v3 definitions and must never become an input file.
    return dict(schema=SCHEMA, model='Olympus E-PL9', build='1101', recipe_revision='v3',
        source_definition_sha256=hashlib.sha256(b'SYNTHETIC UNIT TEST ONLY').hexdigest(), recipes=[
            dict(name=name, watercolor_key=key, native_hsl=[[0, 0, 0] for _ in range(12)],
                picture_mode_contrast=0, tone_level=dict(highlights=0, midtones=mid, shadows=0),
                native_rgb_curves='stock', native_wb_gain_q10='stock', matrix_delta=None, six_axis=None)
            for name, key, mid in zip(NAMES, KEYS, (-3, 5))])


def inputs(value):
    raw = json.dumps(value).encode()
    return NativeRecipeInputs(raw, hashlib.sha256(raw).hexdigest())


def instruction_map(module):
    base, data, symbols = module['base'], module['data'], module['symbols']
    return {at: (data[at-base:at-base+length], op,
        [str(symbols[a]) if a in symbols else a for a in args]) for at, op, args, length in module['rows']}


class InputContractTests(unittest.TestCase):
    def test_hash_duplicate_fields_revision_and_native_fields_are_required(self):
        raw = json.dumps(document()).encode()
        with self.assertRaisesRegex(ValueError, 'SHA-256 mismatch'):
            NativeRecipeInputs(raw, '0'*64)
        duplicated = raw.replace(b'"recipe_revision": "v3"', b'"recipe_revision":"v2","recipe_revision":"v3"')
        with self.assertRaisesRegex(ValueError, 'duplicate JSON field'):
            NativeRecipeInputs(duplicated, hashlib.sha256(duplicated).hexdigest())
        for field in document():
            value = document()
            del value[field]
            with self.subTest(missing=field), self.assertRaises(ValueError):
                inputs(value)
        for field in document()['recipes'][0]:
            value = document()
            del value['recipes'][0][field]
            with self.subTest(missing_recipe_field=field), self.assertRaises(ValueError):
                inputs(value)
        for field, wrong in (('recipe_revision', 'v2'), ('model', 'PEN-F'), ('build', '1102'),
                             ('source_definition_sha256', 'unidentified')):
            value = document()
            value[field] = wrong
            with self.subTest(field=field), self.assertRaises(ValueError):
                inputs(value)

    def test_bound_bytes_are_immutable_and_parsed_views_do_not_change_them(self):
        value = inputs(document())
        with self.assertRaises(FrozenInstanceError):
            value.raw = b'changed'
        _, decoded = value.decoded()
        decoded['rows'][0]['native_hsl'][0][0] = 999
        self.assertEqual(value.decoded()[1]['rows'][0]['native_hsl'][0][0], 0)
        self.assertFalse(value.binding()['historical_draft_fallback_used'])
        self.assertFalse(value.binding()['owner_acceptance_independently_verified'])

    def test_reordering_is_keyed_and_wrong_or_duplicate_recipe_binding_is_rejected(self):
        value = document()
        value['recipes'].reverse()
        self.assertEqual([r['watercolor_key'] for r in inputs(value).decoded()[1]['rows']], list(KEYS))
        for field, wrong in (('name', NAMES[1]), ('watercolor_key', KEYS[1]),
                             ('watercolor_key', '0x01030078')):
            value = document()
            value['recipes'][0][field] = wrong
            with self.subTest(field=field, wrong=wrong), self.assertRaises(ValueError):
                inputs(value)

    def test_ranges_shapes_and_native_order_are_not_inferred(self):
        for field, wrong in (
            ('native_hsl', [[0, 0, 0]]*11), ('native_hsl', [[1001, 0, 0]]*12),
            ('native_hsl', [[True, 0, 0]]*12), ('picture_mode_contrast', 3),
            ('tone_level', dict(highlights=0, shadows=0, midtones=True)),
            ('tone_level', dict(highlights=0, shadows=0, midtones=-8)),
            ('native_rgb_curves', None), ('native_rgb_curves', [[0]*256]*2),
            ('native_rgb_curves', [[0]*255+[4096]]*3),
            ('native_wb_gain_q10', [1080]), ('native_wb_gain_q10', [511, 1024]),
            ('native_wb_gain_q10', dict(red_gain_permille=1080, blue_gain_permille=880)),
            ('matrix_delta', [1]*9), ('six_axis', [0]*11)):
            value = document()
            value['recipes'][0][field] = wrong
            with self.subTest(field=field, wrong=str(wrong)[:50]), self.assertRaises(ValueError):
                inputs(value)

    def test_diagnostic_or_separate_overrides_cannot_mix_with_pinned_inputs(self):
        for options in (dict(diagnostic_rgb=True), dict(rgb_document={}),
                        dict(color_document={}), dict(wb_document={})):
            with self.subTest(options=options), self.assertRaisesRegex(ValueError, 'cannot mix'):
                build_late_module(b'', recipe_inputs=inputs(document()), **options)
        with self.assertRaisesRegex(ValueError, 'exact E-PL9'):
            build_late_module(b'', recipe_inputs=inputs(document()))

    def test_incomplete_early_builder_cannot_emit_a_full_bundle_claim(self):
        with self.assertRaisesRegex(ValueError, 'refusing partial'):
            emit_files(dict(recipe_binding=inputs(document()).binding()), ROOT/'local/not-created-native-input-test')

    def test_emitter_and_probe_cli_require_the_input_and_hash_pair_before_file_reads(self):
        for entry in (epl9_film_late_module.main, epl9_film_late_probe.main):
            for options in (['--recipe-inputs','not-a-real-input.json'], ['--recipe-inputs-sha256','0'*64]):
                with self.subTest(entry=entry.__module__, options=options), patch.object(sys, 'argv',
                        ['test','--out',str(ROOT/'local/not-created-cli-test'),*options]):
                    with self.assertRaisesRegex(ValueError, 'must be supplied together'):
                        entry()


class SyntheticEmissionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        image = bytearray(26214336)
        for address, raw in ((0x60752202, '881cf9140c'), (0x6079d7f4, 'cd34fbf01cf8923d'),
                (0x6079fb88, 'f1d3f1ef53'), (0x6074f352, '0008257e0e'), (0x6079c017, 'cdc4feb00c')):
            image[address-BASE:address-BASE+len(bytes.fromhex(raw))] = bytes.fromhex(raw)
        struct.pack_into('<256H', image, 0x608c37e4-BASE, *range(0, 4096, 16))
        cls.image = bytes(image)
        cls.image_sha = hashlib.sha256(cls.image).hexdigest()

    def build(self, value=None, **options):
        # Only this test's image-identity constant changes. The production
        # source keeps its exact vendor-main hash; no bypass reaches the CLI.
        with patch('epl9_film_module.MAIN_SHA', self.image_sha):
            return build_late_module(self.image, recipe_inputs=inputs(value) if value is not None else None, **options)

    def test_all_explicit_data_reaches_emitted_hsl_rgb_six_axis_and_native_controls(self):
        value = document()
        row = value['recipes'][0]
        row['native_hsl'][3] = [123, -45, 6]
        row['native_rgb_curves'] = [[n*15 for n in range(256)]]*3
        row['native_wb_gain_q10'] = [1111, 999]
        row['matrix_delta'] = [1, -1, 0, 0, 0, 0, 0, 0, 0]
        row['six_axis'] = list(range(12))
        module = self.build(value)
        self.assertEqual(struct.unpack_from('<3h', module['data'], OFFSETS['GOLD_HSL']+3*28+12), (123, -45, 6))
        for slot in range(3):
            self.assertEqual(struct.unpack_from('<256H', module['data'], OFFSETS[f'GOLD_RGB{slot}']), tuple(row['native_rgb_curves'][slot]))
            self.assertEqual(struct.unpack_from('<256H', module['data'], OFFSETS[f'PORTRA_RGB{slot}']), tuple(range(0,4096,16)))
        self.assertEqual(struct.unpack_from('<12h', module['data'], 0x1c00), tuple(range(12)))
        self.assertEqual(module['wb_controls'][KEYS[0]], (1111, 999))
        self.assertEqual(module['wb_controls'][KEYS[1]], (1024, 1024))
        self.assertEqual(module['color_controls'][KEYS[0]]['matrix_delta'], tuple(row['matrix_delta']))
        self.assertEqual(len(module['patches']), 5)
        self.assertTrue(module['native_recipe_inputs_complete'])
        self.assertEqual(module['definitions'], {'native_recipe_inputs': inputs(value).expected_sha256})
        self.assertFalse(module['metadata']['install_ready'])
        self.assertLessEqual(module['code_bytes'], 0x1000)

    def test_explicit_inputs_never_read_historical_recipe_files(self):
        original = Path.read_text
        def read(path, *args, **kwargs):
            if path.parent == ROOT/'recipes':
                raise AssertionError('historical numerical fallback read')
            return original(path, *args, **kwargs)
        with patch.object(Path, 'read_text', read):
            module = self.build(document())
        self.assertEqual(module['recipes'][0]['tone_level']['midtones'], -3)

    def test_historical_default_code_and_data_are_identical_to_explicit_same_number_control(self):
        value = document()
        hsl = json.loads((ROOT/'recipes/epl9-film-drafts-v0.json').read_text())['recipes']
        tone = json.loads((ROOT/'recipes/epl9-film-drafts-v2.json').read_text())['recipes']
        for row, h, t in zip(value['recipes'], hsl, tone):
            row['native_hsl'] = h['native_hsl']
            row['picture_mode_contrast'], row['tone_level'] = t['picture_mode_contrast'], t['tone_level']
        # Historical numbers are used ONLY to check compatibility. The neutral
        # test binding is not a recovered or accepted photographic v3 recipe.
        old, same = self.build(), self.build(value)
        self.assertEqual(old['source'], same['source'])
        self.assertEqual(old['data'], same['data'])
        self.assertEqual(old['patches'], same['patches'])
        self.assertIsNone(old['recipe_binding'])
        # Fixed outputs independently generated by the original builders from
        # PR #1 head 318d7b4 on this exact synthetic image fixture. This checks
        # the pre-change result, not just two paths through the new builder.
        self.assertEqual(hashlib.sha256(old['source'].encode()).hexdigest(),
            '3499a3cbc3c17ce319c89dfbfc91044f0f435c31a191443df747be642b05746e')
        self.assertEqual(hashlib.sha256(old['data']).hexdigest(),
            'afdcdc1131501b25cbeaebda34d26afa709503e6ebbd16a1bd1c6ff676c0bea2')
        patch_bytes = json.dumps(old['patches'],sort_keys=True,separators=(',',':')).encode()
        self.assertEqual(hashlib.sha256(patch_bytes).hexdigest(),
            '89e66f05dc98cb7af60e1fbde3d2ed032d74c066dd0f3d71aac2aa3aaad87968')

    def test_portra_only_overrides_and_six_distinct_curves_do_not_cross_slots(self):
        value = document()
        for row, base in zip(value['recipes'], (0, 100)):
            row['native_rgb_curves'] = [[base+slot+n*14 for n in range(256)] for slot in range(3)]
        value['recipes'][1]['native_hsl'][11] = [-456, 78, -9]
        value['recipes'][1]['native_wb_gain_q10'] = [999, 1111]
        value['recipes'][1]['six_axis'] = list(range(-6, 6))
        module = self.build(value)
        for prefix, row in zip(('GOLD', 'PORTRA'), value['recipes']):
            for slot in range(3):
                self.assertEqual(struct.unpack_from('<256H', module['data'], OFFSETS[f'{prefix}_RGB{slot}']),
                    tuple(row['native_rgb_curves'][slot]))
        self.assertEqual(struct.unpack_from('<3h', module['data'], OFFSETS['GOLD_HSL']+11*28+12), (0, 0, 0))
        self.assertEqual(struct.unpack_from('<3h', module['data'], OFFSETS['PORTRA_HSL']+11*28+12), (-456, 78, -9))
        self.assertEqual(struct.unpack_from('<12h', module['data'], 0x2c00), tuple(range(-6, 6)))
        self.assertEqual(module['wb_controls'][KEYS[0]], (1024, 1024))
        self.assertEqual(module['wb_controls'][KEYS[1]], (999, 1111))

    def test_equal_nondefault_midtones_have_no_selection_branch(self):
        value = document()
        for row in value['recipes']:
            row['tone_level']['midtones'] = -4
        module = self.build(value)
        self.assertNotIn('color_midtone_bias_gold', module['symbols'])
        self.assertIn(' movhu (6,a1),d0\n exth d0\n add -4,d0\n', module['source'])

    def test_manifest_records_bound_and_emitted_hashes_without_camera_claim(self):
        value = document()
        module = self.build(value)
        # Mocked reader output checks manifest plumbing only. It does not
        # substitute for the real pinned GNU disassembly required in production.
        listing = '\n'.join(f'{at:x}\t{raw.hex()}\t{op}\t'+','.join(args)
            for at, (raw, op, args) in instruction_map(module).items())
        with TemporaryDirectory(dir=ROOT/'local') as temp:
            root = Path(temp)
            reader = root/'mock-reader'
            reader.write_bytes(b'SYNTHETIC MOCK READER')
            with patch('epl9_film_module.READER_SHA',hashlib.sha256(reader.read_bytes()).hexdigest()), \
                    patch('epl9_film_module.subprocess.check_output',return_value=listing):
                _, report = emit_files(module,root/'out',reader=reader)
            saved = json.loads((root/'out/manifest.json').read_text())
        self.assertEqual(saved,report)
        self.assertEqual(saved['recipe_binding']['input_sha256'],inputs(value).expected_sha256)
        self.assertTrue(saved['native_recipe_inputs_complete'])
        for prefix, key in zip(('GOLD','PORTRA'),KEYS):
            offset = OFFSETS[prefix+'_HSL']
            self.assertEqual(saved['recipe_binding']['emitted_tables'][key]['hsl_sha256'],
                hashlib.sha256(module['data'][offset:offset+3028]).hexdigest())
        for field in ('install_ready','camera_accessed','firmware_container_created'):
            self.assertFalse(saved[field])

    def test_internal_early_layer_also_selects_both_explicit_midtone_biases(self):
        value = document()
        with patch('epl9_film_module.MAIN_SHA',self.image_sha):
            module = build_module(self.image,recipe_inputs=inputs(value))
        for index, row in enumerate(value['recipes'],1):
            controls, request = bytearray(10), bytearray(1876)
            at, req = 0x20000000, 0x20001000
            machine = Machine(instruction_map(module), Memory([Region(at, controls, True),
                Region(req, request, True)]),dict(a1=at,a3=req,d2=index))
            result = machine.run(module['symbols']['controls_bias'])
            self.assertEqual(result['status'],'ret_boundary')
            self.assertEqual(struct.unpack_from('<5h',controls),(0,0,0,row['tone_level']['midtones'],0))

    def test_both_native_midtone_biases_execute_with_clamping_and_other_controls(self):
        value = document()
        value['recipes'][0]['tone_level'].update(highlights=2, shadows=-2)
        value['recipes'][1]['tone_level'].update(highlights=-4, shadows=3)
        module = self.build(value)
        for index, row in enumerate(value['recipes'], 1):
            for user in (-7, -1, 0, 3, 7):
                stack, request = bytearray(128), bytearray(1876)
                struct.pack_into('<I', stack, 44, int(row['watercolor_key'], 16))
                struct.pack_into('<5h', stack, 64, 4, -3, user, user, user)
                sp, req, context = 0x20000000, 0x20001000, 0x20002000
                machine = Machine(instruction_map(module), Memory([Region(sp, stack, True),
                    Region(req, request, True)]), dict(sp=sp, a1=sp+64, a2=req, a3=context, d3=index))
                result = machine.run(module['symbols']['color_controls_bias'])
                self.assertEqual(result['status'], 'call_boundary')
                expected = tuple(max(-7, min(7, user+row['tone_level'][field]))
                    for field in ('highlights', 'midtones', 'shadows'))
                self.assertEqual(struct.unpack_from('<5h', stack, 64), (4, -3, *expected))
                self.assertEqual(machine.r['sp'], sp)
                self.assertEqual(struct.unpack_from('<I', request, 1512)[0], sp+64)


if __name__ == '__main__':
    unittest.main()
