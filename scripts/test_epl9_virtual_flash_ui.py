"""Focused fail-closed controls for persisted native-write -> UI source binding."""
import copy
from contextlib import ExitStack
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

import epl9_virtual_flash_ui as bridge


def result_document():
    return dict(schema=bridge.SCHEMA, generation='native-source-v1', model='Olympus PEN E-PL9',
        model_bytes='1330', scenario='install-candidate', target='candidate', status='verified-virtual-only',
        virtual_install_verified=True, camera_accessed=False, physical_writes=False,
        reset_boot_proven=False, install_ready=False, native_report={}, source_package={}, flash_manifest={},
        components=[dict(name=name, kind=bridge.KINDS[name], file=f'flash/{name}.flash.bin',
            bytes=bridge.ENVELOPE_BYTES, payload_bytes=bridge.PAYLOAD_BYTES, layout='decoded-envelope-v1',
            logical_destination=bridge.DESTINATIONS[name], envelope_sha256='envelope',
            payload_sha256=bridge.PAYLOAD_HASHES['candidate'][name],
            target_payload_sha256=bridge.PAYLOAD_HASHES['candidate'][name], target_matches=True)
            for name in bridge.COMPONENTS])


class ResultSchemaTests(unittest.TestCase):
    def setUp(self):
        self.doc = result_document()

    def verify(self):
        bridge.validate_result_header(self.doc, 'install-candidate')

    def test_exact_header(self):
        self.verify()

    def test_specimen_incomplete_and_ambiguous_success_rejected(self):
        for key, value in [('status', 'schema-only-not-an-execution-result'), ('status', 'unverified-virtual-only'),
                ('virtual_install_verified', False), ('install_ready', True), ('physical_writes', True)]:
            with self.subTest(key=key, value=value):
                self.doc = result_document(); self.doc[key] = value
                with self.assertRaises(ValueError): self.verify()

    def test_mixed_historical_wrong_destination_and_extra_components_rejected(self):
        for key, value in [('payload_sha256', bridge.ui.MAIN_SHA), ('kind', '0x101'),
                ('logical_destination', '0x806e0000'), ('file', '../main.flash.bin'), ('bytes', True)]:
            with self.subTest(key=key):
                self.doc = result_document(); self.doc['components'][0][key] = value
                with self.assertRaises(ValueError): self.verify()
        self.doc = result_document(); self.doc['components'].reverse()
        with self.assertRaises(ValueError): self.verify()
        self.doc = result_document(); self.doc['components'].append(self.doc['components'][0])
        with self.assertRaises(ValueError): self.verify()

    def test_unknown_fields_and_generation_fail_closed(self):
        self.doc['future_field'] = True
        with self.assertRaises(ValueError): self.verify()
        self.doc = result_document(); self.doc['generation'] = 'private-color-v3'
        with self.assertRaises(ValueError): self.verify()


class PathAndEnvelopeTests(unittest.TestCase):
    def test_missing_traversal_and_symlink_paths_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); (root/'data').write_bytes(b'ok')
            (root/'alias').symlink_to(root/'data')
            self.assertEqual(bridge.direct_file(root, 'data'), root/'data')
            for name in ('../data', '/etc/passwd', 'missing', 'alias', './data', 'dir/../data'):
                with self.subTest(name=name), self.assertRaises(ValueError):
                    bridge.direct_file(root, name)

    def envelope(self):
        header = bytearray(32); header[:4] = b'OE\x13\x30'
        struct.pack_into('<II', header, 8, 0x406e0000, 16)
        struct.pack_into('<H', header, 20, 0x100)
        payload = bytes(range(16)); trailer = bytearray(header)
        total = sum(struct.unpack('<20I', header+payload+trailer))
        struct.pack_into('<I', trailer, 28, (-total) & 0xffffffff)
        return bytes(header+payload+trailer)

    def verify(self, data, expected):
        row = dict(envelope_sha256=bridge.ui.sha(data), payload_sha256=bridge.ui.sha(data[32:-32]),
            logical_destination='0x406e0000', kind='0x100')
        with patch.object(bridge, 'ENVELOPE_BYTES', 80), patch.object(bridge, 'PAYLOAD_BYTES', 16):
            return bridge.validate_envelope(data, row, expected)

    def test_whole_envelope_and_payload_body_are_bound(self):
        data = self.envelope()
        self.assertEqual(self.verify(data, data), bytes(range(16)))
        changed = bytearray(data); changed[32] ^= 1
        with self.assertRaisesRegex(ValueError, 'decoded source package'):
            self.verify(bytes(changed), data)

    def test_metadata_trailer_and_checksum_changes_are_rejected(self):
        for at in (2, 8, 12, 20, 32, 79):
            with self.subTest(at=at):
                changed = bytearray(self.envelope()); changed[at] ^= 1
                with self.assertRaises(ValueError): self.verify(bytes(changed), bytes(changed))


class NativeOperationTests(unittest.TestCase):
    def setUp(self):
        self.doc = result_document()
        self.envelopes = dict(main=b'new-main', osd=b'new-osd')
        self.initial = dict(main=b'old-main', osd=b'old-osd')
        self.native = dict(schema='epl9-native-persistent-updater-v1', generation='native-source-v1',
            scenario='install-candidate', target='candidate', mode=0, returned=True, return_value='0x0',
            input_bytes=2*bridge.ENVELOPE_BYTES, input_sha256=bridge.PACKAGE_HASHES['candidate'],
            output_sha256=bridge.ui.sha(self.envelopes['main']+self.envelopes['osd']),
            source_package_file_sha256=bridge.PACKAGE_HASHES['candidate'], source_package_intentionally_corrupted=False,
            entry='0x6100440a', executing_main_sha256=bridge.ui.MAIN_SHA, physical_writes=False,
            camera_accessed=False, reset_boot_proven=False, install_ready=False, usb_sd_transport_modeled=False,
            virtual_install_verified=True, package_guards_intact=True, stack_balanced=True,
            actual_components_match_target=dict.fromkeys(bridge.COMPONENTS, True),
            expected_target_payload_sha256=bridge.PAYLOAD_HASHES['candidate'], fault_target=None,
            fault_plan=None, readback_error_target=None, persistent_reopens=4,
            real_native_layers=['updater', 'write selector', 'program/readback wrapper', 'readback checksum'],
            modeled_leaves=['program 0x60439f38', 'read 0x604014c6'], operations=[])
        for name in ('osd', 'main'):
            envelope_sha = bridge.ui.sha(self.envelopes[name])
            base = dict(component=name, return_code=0, bytes=bridge.ENVELOPE_BYTES, persistent_reopen=True, checksum=0)
            self.native['operations'].append(dict(base, native_entry='0x60439f38', status='success', returned=True,
                fault=None, stage='complete', offset=bridge.ENVELOPE_BYTES, native_operation='program',
                native_destination='0x806e0000' if name == 'main' else '0x421e0000',
                requested_envelope_sha256=envelope_sha, expected_sha256=envelope_sha, actual_sha256=envelope_sha,
                before_sha256=bridge.ui.sha(self.initial[name]), requested_payload_sha256=bridge.PAYLOAD_HASHES['candidate'][name],
                programmed_bytes=bridge.ENVELOPE_BYTES, erased_blocks=200, programmed_pages=12800))
            self.native['operations'].append(dict(base, native_entry='0x604014c6', stage='readback', copied=True,
                envelope_sha256=envelope_sha, payload_sha256=bridge.PAYLOAD_HASHES['candidate'][name]))

    def verify(self):
        bridge.validate_native_operations(self.native, self.doc, self.envelopes, self.initial)

    def test_full_program_and_independent_readback_chain_accepts(self):
        self.verify()

    def test_final_zero_cannot_hide_program_readback_or_copy_fault(self):
        for index, key, value in [(0, 'return_code', 0x3101), (0, 'corruption_injected', True),
                (1, 'copied', False), (1, 'envelope_sha256', 'stale'), (2, 'before_sha256', 'wrong-initial'),
                (3, 'persistent_reopen', False)]:
            with self.subTest(index=index, key=key):
                before = copy.deepcopy(self.native)
                self.native['operations'][index][key] = value
                with self.assertRaises(ValueError): self.verify()
                self.native = before

    def test_missing_duplicated_and_reordered_native_operations_rejected(self):
        original = copy.deepcopy(self.native['operations'])
        for ops in (original[:2], original+original[:1], list(reversed(original))):
            with self.subTest(count=len(ops)), self.assertRaises(ValueError):
                self.native['operations'] = ops; self.verify()

    def test_trap_only_old_or_wrong_executing_main_rejected(self):
        self.native['executing_main_sha256'] = bridge.ui.CANDIDATE_SHA
        with self.assertRaisesRegex(ValueError, 'execution/input'): self.verify()


class FlashInitializationTests(unittest.TestCase):
    def setUp(self):
        self.doc = result_document()
        self.initial = dict(main=b'original-main', osd=b'original-osd')
        self.flash = dict(schema='epl9-logical-flash-v1',
            layout={'main': dict(base=0x406e0000, aliases=[0x806e0000], size=bridge.ENVELOPE_BYTES),
                'osd': dict(base=0x421e0000, aliases=[], size=bridge.ENVELOPE_BYTES)},
            geometry=dict(page_size=2048, erase_block_size=131072, basis='logical assumptions; not proven chip geometry'),
            envelope=dict(header_bytes=32, trailer_bytes=32), persistence='test', hardware_qualified=False,
            components={name: dict(size=bridge.ENVELOPE_BYTES, sha256='envelope',
                original_sha256=bridge.ui.sha(self.initial[name])) for name in bridge.COMPONENTS},
            last_result=dict(component='main', status='success', fault=None, return_code=0,
                returned=True, stage='complete', programmed_bytes=bridge.ENVELOPE_BYTES, actual_sha256='envelope'))

    def verify(self):
        core = {k: v for k, v in self.flash.items() if k != 'manifest_sha256'}
        self.flash['manifest_sha256'] = bridge.ui.sha(json.dumps(core, sort_keys=True, separators=(',', ':')).encode())
        bridge.validate_flash_manifest(self.flash, self.doc, self.initial)

    def test_initial_and_result_envelopes_accept(self):
        self.verify()

    def test_rebound_initial_snapshot_rejected_even_with_recomputed_manifest_hash(self):
        self.flash['components']['osd']['original_sha256'] = 'stale-previous-run'
        with self.assertRaisesRegex(ValueError, 'initial snapshot'): self.verify()

    def test_fault_state_and_unsupported_geometry_rejected(self):
        self.flash['last_result']['fault'] = dict(kind='program_error')
        with self.assertRaisesRegex(ValueError, 'incomplete/faulted'): self.verify()
        self.flash['last_result']['fault'] = None
        self.flash['geometry']['page_size'] = 4096
        with self.assertRaisesRegex(ValueError, 'geometry'): self.verify()


class RestoredSessionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.overlay = Path(self.tmp.name)/'restore.json'; self.overlay.write_text('{"patches":[]}')
        self.node = Path(self.tmp.name)/'node'; self.node.write_bytes(b'node')
        frame = dict(action='menu', gui='0x1', state='screen', sha256='stock-frame',
            png_rgb_sha256='stock-rgb', engine_errors=[], engine_errors_total=0,
            unexpected_engine_errors=[], film_site_hits=dict.fromkeys(bridge.ui.SITES, 0),
            labels=[], inline_targets=[], target_draws=[], palette=None)
        self.stock = dict(frames=[copy.deepcopy(frame) for _ in range(41)])
        self.restored = dict(model='E133', error=None, patch=dict(files=[str(self.overlay.resolve())],
            applied=15, bytes=0, blocks=[
                dict(block='main', sha256=bridge.ui.MAIN_SHA, stock_sha256=bridge.ui.MAIN_SHA,
                    name='blk00000000.OE.0100.bin', patches=5),
                dict(block='resource', sha256=bridge.ui.STOCK_PREFIX_SHA, stock_sha256=bridge.ui.STOCK_PREFIX_SHA,
                    name='blk01900000.OE.0101.bin', patches=10)]),
            input_binding=dict(patch_files=[bridge.ui.record(self.overlay)], node_executable=bridge.ui.record(self.node)),
            frames=copy.deepcopy(self.stock['frames']))

    def verify(self):
        return bridge.validate_restored_session(self.restored, self.stock, self.overlay, self.node)

    def test_exact_stock_return_accepts_and_does_not_mutate_session(self):
        before = copy.deepcopy(self.restored)
        self.assertIsNone(self.verify()['patch'])
        self.assertEqual(self.restored, before)

    def test_stock_looking_frames_without_actual_restore_overlay_binding_rejected(self):
        self.restored['input_binding']['patch_files'][0]['sha256'] = 'different-overlay'
        with self.assertRaisesRegex(ValueError, 'session-time'): self.verify()

    def test_different_pixels_or_diagnostics_rejected(self):
        self.restored['frames'][12]['png_rgb_sha256'] = 'candidate-image'
        with self.assertRaisesRegex(ValueError, 'frame 12'): self.verify()


class QualificationMutationTests(unittest.TestCase):
    def mutation_control(self, kind):
        """Exercise qualify(), including both former late snapshot acceptance holes."""
        with tempfile.TemporaryDirectory() as tmp, ExitStack() as stack:
            root = Path(tmp)
            dirs = [root/name for name in ('stock', 'icons', 'candidate', 'restored')]
            for directory in dirs:
                directory.mkdir()
                (directory/'session.json').write_text(json.dumps(dict(frames=[dict(png_rgb_sha256='a'*64)])))
            overlays = root/'overlays'; overlays.mkdir()
            files = {}
            for name in ('main', 'osd', 'node', 'adapter', 'candidate-result', 'restore-result', 'module'):
                files[name] = root/name; files[name].write_bytes(name.encode())
            source_copy = root/'bridge-source.py'
            source_copy.write_bytes(Path(bridge.__file__).read_bytes())
            stack.enter_context(patch.object(bridge, '__file__', str(source_copy)))
            (overlays/'bridge-manifest.json').write_text(json.dumps(dict(
                candidate_result=bridge.ui.record(files['candidate-result']),
                restore_result=bridge.ui.record(files['restore-result']), source_files=[])))

            def mutate_after_parse(sessions, upstream):
                self.assertEqual(len(sessions), 4)
                if kind == 'session':
                    session = dirs[3]/'session.json'
                    changed = json.loads(session.read_text())
                    changed['frames'][0]['png_rgb_sha256'] = '0'*64
                    session.write_text(json.dumps(changed))
                return [bridge.ui.record(files['module'])]*120

            consumed = []
            def consume(*args):
                if kind == 'source' and not consumed:
                    source_copy.write_bytes(source_copy.read_bytes()+b'\n# drift after entry hash check\n')
                consumed.append(True)
                return {}, {}, {}

            def original_qualifier(out, *args):
                out.mkdir(parents=True)
                (out/'manifest.json').write_text('{}')
                return dict(ui_qualified=True, limitations=[])

            for attribute, value in [('MAIN', files['main']), ('OSD', files['osd']), ('ADAPTER', files['adapter'])]:
                stack.enter_context(patch.object(bridge.ui, attribute, value))
            stack.enter_context(patch.object(bridge.ui, 'new_local', side_effect=lambda p: p))
            stack.enter_context(patch.object(bridge, 'consume_result', side_effect=consume))
            stack.enter_context(patch.object(bridge, 'overlay_contents', return_value=([], {})))
            stack.enter_context(patch.object(bridge, 'helper_snapshot', return_value={}))
            stack.enter_context(patch.object(bridge, 'validate_restored_session', return_value={}))
            stack.enter_context(patch.object(bridge.ui, 'validate_overlays', return_value=([], {}, {}, {})))
            stack.enter_context(patch.object(bridge.ui, 'verify_sessions'))
            stack.enter_context(patch.object(bridge.ui, 'verify_runtime_dependencies', side_effect=mutate_after_parse))
            stack.enter_context(patch.object(bridge.ui, 'verify_frame_files', return_value=[]))
            stack.enter_context(patch.object(bridge.ui, 'qualify', side_effect=original_qualifier))
            target = 'restored/session.json' if kind == 'session' else 'bridge-source.py'
            with self.assertRaisesRegex(ValueError, 'changed during qualification.*'+target):
                bridge.qualify(root/'qualification', overlays, *dirs, files['node'],
                    files['candidate-result'], files['restore-result'])

    def test_session_mutation_during_runtime_check_is_rejected(self):
        self.mutation_control('session')

    def test_source_mutation_after_entry_check_is_rejected(self):
        self.mutation_control('source')


if __name__ == '__main__':
    unittest.main()
