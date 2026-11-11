"""Synthetic rejection controls for exact native-source-v1 UI identities."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

from epl9_native_source_ui_qualification import (
    verify_sessions, ACTIONS, SITES, UPSTREAM, RUNNER_SHA, MAIN_SHA, CANDIDATE_SHA,
    STOCK_PREFIX_SHA, ICON_PREFIX_SHA, replay_overlay, verify_png, assert_unchanged,
    record, sha, verify_runtime_dependencies,
)


class NativeSourceUiTests(unittest.TestCase):
    def setUp(self):
        self.overlays = Path('/tmp/native-source-ui-overlays')
        self.manifest = dict(stock_prefix_sha256=STOCK_PREFIX_SHA, candidate_prefix_sha256=ICON_PREFIX_SHA)
        self.adapter_sha = 'passive-observer'
        self.node = dict(path='/tmp/node', bytes=1, sha256='node-executable')
        self.overlay_records = {
            (self.overlays/(name+'.json')).resolve(): dict(path=str(self.overlays/(name+'.json')), bytes=10, sha256=name+'-overlay')
            for name in ('icons', 'combined')}
        baseline = dict(upstream_commit=UPSTREAM, runner_sha256=RUNNER_SHA, node='v26.13.0',
            stock_main_sha256=MAIN_SHA, stock_resource_prefix_sha256=STOCK_PREFIX_SHA, actions=ACTIONS,
            camera_accessed=False, hardware_pixel_execution=False,
            runner_adapter=dict(source_sha256=self.adapter_sha, base_runner_sha256=RUNNER_SHA,
                extra_observed_sites=['0x60761c9e'], input_and_frame_binding_schema='epl9-ui-input-frame-binding-v2', cpu_or_firmware_modified=False),
            input_binding=dict(schema='epl9-ui-input-frame-binding-v2', patch_files=[], node_executable=self.node),
            patch=None, frames=[dict(film_site_hits=dict.fromkeys(SITES, 0))])
        self.sessions = [copy.deepcopy(baseline) for _ in range(3)]
        for index, name, count in [(1, 'icons', 10), (2, 'combined', 15)]:
            blocks = [dict(block='resource', sha256=ICON_PREFIX_SHA, stock_sha256=STOCK_PREFIX_SHA, patches=10, name='blk01900000.OE.0101.bin')]
            if index == 2:
                blocks.insert(0, dict(block='main', sha256=CANDIDATE_SHA, stock_sha256=MAIN_SHA, patches=5, name='blk00000000.OE.0100.bin'))
            self.sessions[index]['patch'] = dict(files=[str(self.overlays/(name+'.json'))], applied=count, blocks=blocks, bytes=8002 if index == 1 else 23298)
            self.sessions[index]['input_binding']['patch_files'] = [self.overlay_records[(self.overlays/(name+'.json')).resolve()]]

    def verify(self):
        verify_sessions(self.sessions, self.overlays, self.manifest, self.adapter_sha, self.overlay_records, self.node)

    def test_exact_identity_accepts(self):
        self.verify()

    def test_historical_main_is_not_native_source(self):
        self.sessions[2]['patch']['blocks'][0]['sha256'] = 'historical-private-color-v3'
        with self.assertRaisesRegex(ValueError, 'actual emulated component'):
            self.verify()

    def test_runtime_or_runner_or_upstream_substitution_rejected(self):
        for key, value in [('node', 'v24.22.1'), ('runner_sha256', 'other'), ('upstream_commit', 'other')]:
            original = self.sessions[1][key]
            self.sessions[1][key] = value
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'identity'):
                self.verify()
            self.sessions[1][key] = original

    def test_changed_action_route_rejected(self):
        self.sessions[2]['actions'] = ['mode:ART']*40
        with self.assertRaisesRegex(ValueError, 'identity'):
            self.verify()

    def test_missing_relocated_wb_observer_rejected(self):
        self.sessions[2]['frames'][0]['film_site_hits'].pop('0x60761c9e')
        with self.assertRaisesRegex(ValueError, 'coverage'):
            self.verify()

    def test_processing_hit_cannot_be_called_ui_only(self):
        self.sessions[2]['frames'][0]['film_site_hits']['0x60761c9e'] = 1
        with self.assertRaisesRegex(ValueError, 'processing site executed'):
            self.verify()

    def test_missing_or_changed_adapter_rejected(self):
        self.sessions[0]['runner_adapter']['source_sha256'] = 'other'
        with self.assertRaisesRegex(ValueError, 'passive observer'):
            self.verify()

    def test_overlay_file_and_count_rejected(self):
        for key, value in [('files', ['/tmp/historical-combined.json']), ('applied', 16)]:
            original = self.sessions[2]['patch'][key]
            self.sessions[2]['patch'][key] = value
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'overlay file/count'):
                self.verify()
            self.sessions[2]['patch'][key] = original

    def test_resource_prefix_substitution_rejected(self):
        self.sessions[1]['patch']['blocks'][0]['sha256'] = 'other-resource'
        with self.assertRaisesRegex(ValueError, 'actual emulated component'):
            self.verify()

    def test_ui_only_scope_must_be_explicit(self):
        self.sessions[2]['hardware_pixel_execution'] = True
        with self.assertRaisesRegex(ValueError, 'offline UI-only'):
            self.verify()

    def test_session_patch_hash_must_match_current_overlay(self):
        self.sessions[2]['input_binding']['patch_files'][0] = dict(self.sessions[2]['input_binding']['patch_files'][0], sha256='substituted')
        with self.assertRaisesRegex(ValueError, 'session-time patch bytes'):
            self.verify()

    def test_duplicate_component_summary_rejected(self):
        self.sessions[2]['patch']['blocks'].append(copy.deepcopy(self.sessions[2]['patch']['blocks'][0]))
        with self.assertRaisesRegex(ValueError, 'duplicate actual component'):
            self.verify()

    def test_component_guard_and_count_metadata_rejected(self):
        self.sessions[2]['patch']['blocks'][0]['patches'] = 4
        with self.assertRaisesRegex(ValueError, 'stock guard hash'):
            self.verify()

    def test_changed_byte_count_metadata_rejected(self):
        self.sessions[2]['patch']['bytes'] = 0
        with self.assertRaisesRegex(ValueError, 'changed-byte count'):
            self.verify()


class OverlayBindingTests(unittest.TestCase):
    def setUp(self):
        self.stock = dict(main=b'0123456789', resource=b'abcdef')
        self.rows = [dict(block='main', offset=2, label='hook', old='MjM=', new='WFk=')]
        self.expected = dict(main=sha(b'01XY456789'), resource=sha(b'abcdef'))

    def run_overlay(self, rows=None, raw=None):
        raw = raw if raw is not None else json.dumps(dict(patches=self.rows if rows is None else rows)).encode()
        return replay_overlay(raw, self.rows, self.stock, self.expected)

    def test_exact_overlay_replays(self):
        self.assertEqual(self.run_overlay()['changed_bytes'], 2)

    def test_invalid_substituted_overlay_bytes_rejected(self):
        with self.assertRaises(ValueError):
            self.run_overlay(raw=b'not even valid overlay JSON\n')

    def test_duplicate_json_key_rejected(self):
        with self.assertRaisesRegex(ValueError, 'duplicate JSON'):
            self.run_overlay(raw=b'{"patches":[],"patches":[]}')

    def test_missing_extra_duplicate_and_split_inventory_rejected(self):
        alternatives = [[], self.rows*2, self.rows+[dict(block='resource', offset=0, label='noop', old='YQ==', new='YQ==')],
            [dict(block='main', offset=2, label='hook', old='Mg==', new='WA=='), dict(block='main', offset=3, label='hook', old='Mw==', new='WQ==')]]
        for rows in alternatives:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                self.run_overlay(rows=rows)

    def test_old_guard_bounds_offsets_block_and_base64_rejected(self):
        for update in [dict(old='MDA='), dict(offset=-1), dict(offset=9), dict(offset=True), dict(block='other'), dict(old='@@')]:
            with self.subTest(update=update), self.assertRaises(ValueError):
                self.run_overlay(rows=[dict(self.rows[0], **update)])


class PngBindingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)/'frame.png'
        Image.new('RGB', (720, 480), (1, 2, 3)).save(self.path)
        raw = self.path.read_bytes()
        self.frame = dict(png_bytes=len(raw), png_sha256=sha(raw), png_rgb_sha256=sha(bytes([1, 2, 3])*(720*480)))

    def test_replay_bound_png_accepts(self):
        self.assertEqual(verify_png(self.path, self.frame)['sha256'], self.frame['png_sha256'])

    def test_modified_png_bytes_rejected(self):
        self.path.write_bytes(self.path.read_bytes()+b'extra')
        with self.assertRaisesRegex(ValueError, 'PNG bytes differ'):
            verify_png(self.path, self.frame)

    def test_rgb_binding_rejects_changed_native_pixels(self):
        self.frame['png_rgb_sha256'] = 'not-native-rgb'
        with self.assertRaisesRegex(ValueError, 'native RGB'):
            verify_png(self.path, self.frame)

    def test_mutation_between_checks_rejected(self):
        snapshot = {self.path.resolve(): record(self.path)}
        self.path.write_bytes(b'replaced after comparison')
        with self.assertRaisesRegex(ValueError, 'changed during qualification'):
            assert_unchanged(snapshot)


class RuntimeBindingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.path = self.root/'module.mjs'
        self.raw = b'export const value = 1;\n'
        self.path.write_bytes(self.raw)
        blob = hashlib.sha1(b'blob '+str(len(self.raw)).encode()+b'\0'+self.raw).hexdigest()
        self.tree = b'100644 blob '+blob.encode()+b'\tmodule.mjs\0'
        self.sessions = [dict(runtime_dependencies=[record(self.path)]) for _ in range(3)]

    def verify(self):
        with patch('epl9_native_source_ui_qualification.subprocess.check_output', return_value=self.tree):
            return verify_runtime_dependencies(self.sessions, self.root)

    def test_loaded_source_matches_pinned_blob(self):
        self.assertEqual(len(self.verify()), 1)

    def test_empty_dependency_coverage_rejected(self):
        self.sessions[0]['runtime_dependencies'] = []
        with self.assertRaisesRegex(ValueError, 'missing replay-time'):
            self.verify()

    def test_duplicate_dependency_rejected(self):
        self.sessions[0]['runtime_dependencies'] *= 2
        with self.assertRaisesRegex(ValueError, 'duplicate or nonlocal'):
            self.verify()

    def test_changed_current_runtime_source_rejected(self):
        self.path.write_bytes(b'export const value = 2;\n')
        with self.assertRaisesRegex(ValueError, 'pinned tracked source'):
            self.verify()

    def test_untracked_runtime_source_rejected(self):
        self.tree = b''
        with self.assertRaisesRegex(ValueError, 'pinned tracked source'):
            self.verify()


if __name__ == '__main__':
    unittest.main()
