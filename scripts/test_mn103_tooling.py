"""Source-only qualification guards. No compiler, firmware or camera needed."""
import copy
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import mn103_tooling as tooling
from mn103_reader import build_reader as builder


class ToolingTests(unittest.TestCase):
    def setUp(self):
        (tooling.ROOT / 'local').mkdir(exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=tooling.ROOT / 'local', prefix='reader-guard-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.reader = self.root / 'mn103-reader'
        self.reader.write_bytes(b'not-an-executable')
        self.source = self.root / 'upstream'
        vectors = self.source / 'gas/testsuite/gas/mn10300/am33-2.d'
        vectors.parent.mkdir(parents=True)
        vectors.write_bytes(b'synthetic vector identity only; never executed')
        self.manifest = dict(commit='pinned-fixture', files=[])
        self.validation = dict(upstream_opcode_vectors_passed=tooling.VECTOR_COUNT,
            fixture_bytes=tooling.VECTOR_BYTES, negative_cases_passed=tooling.NEGATIVE_CASES,
            vectors_sha256=tooling.digest(vectors), camera_accessed=False)
        (self.root / 'validation').mkdir()
        (self.root / 'validation/validation.json').write_text(json.dumps(self.validation))
        self.receipt = dict(schema=tooling.BUILD_SCHEMA, platform=sys.platform,
            machine=platform.machine(), reader_filename=self.reader.name,
            reader_bytes=self.reader.stat().st_size, reader_sha256=tooling.digest(self.reader),
            source_directory=str(self.source), upstream_commit=self.manifest['commit'], upstream_files=[],
            adapter_sources=tooling.source_fingerprints(), validation=self.validation,
            validation_sha256=tooling.digest(self.root / 'validation/validation.json'),
            compiler=dict(path='/fixture/compiler', sha256='0'*64, version='fixture compiler'))
        tooling._validated.clear()

    def save(self):
        (self.root / 'build.json').write_text(json.dumps(self.receipt))

    def test_default_is_host_specific_not_a_path_search(self):
        with patch.object(tooling.sys, 'platform', 'linux'):
            self.assertEqual(tooling.default_reader(), tooling.ROOT / 'local/mn103-tooling/mn103-reader')
        with patch.object(tooling.sys, 'platform', 'win32'):
            self.assertEqual(tooling.default_reader().name, 'mn103-reader.exe')

    def test_legacy_constant_keeps_historical_identity(self):
        with patch.object(tooling, 'digest', return_value=tooling.LEGACY_READER_SHA):
            result = tooling.reader_provenance(self.reader)
        self.assertEqual(result['kind'], 'legacy-windows-pinned')
        self.assertEqual(result['reader_sha256'], tooling.LEGACY_READER_SHA)

    def test_unknown_binary_without_receipt_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'inspected GNU reader'):
            tooling.verify_reader(self.reader)

    def test_receipt_cannot_replace_live_independent_validation(self):
        self.save()
        with patch.object(tooling, 'checked_upstream', return_value=self.manifest), \
                patch.object(tooling.subprocess, 'run', side_effect=subprocess.CalledProcessError(2, ['fixture'])) as run:
            with self.assertRaisesRegex(ValueError, 'inspected GNU reader'):
                tooling.verify_reader(self.reader)
            run.assert_called_once()
        self.assertFalse(tooling._validated)

    def test_changed_binary_is_rejected_before_execution(self):
        self.save()
        self.reader.write_bytes(b'changed executable')
        with patch.object(tooling.subprocess, 'run') as run:
            with self.assertRaisesRegex(ValueError, 'binary/host'):
                tooling.verify_reader(self.reader)
            run.assert_not_called()

    def test_host_filename_sources_and_schema_mismatches_fail_closed(self):
        for field, value in [('platform', 'foreign-host'), ('machine', 'foreign-cpu'),
                ('reader_filename', 'other-reader'), ('schema', 'unqualified'),
                ('adapter_sources', {}), ('reader_bytes', 0)]:
            with self.subTest(field=field):
                original = self.receipt[field]
                self.receipt[field] = value
                self.save()
                with patch.object(tooling.subprocess, 'run') as run:
                    with self.assertRaisesRegex(ValueError, 'binary/host'):
                        tooling.verify_reader(self.reader)
                    run.assert_not_called()
                self.receipt[field] = original

    def test_changed_validation_file_is_rejected(self):
        self.save()
        (self.root / 'validation/validation.json').write_text('{}')
        with patch.object(tooling, 'checked_upstream', return_value=self.manifest), \
                patch.object(tooling.subprocess, 'run') as run:
            with self.assertRaisesRegex(ValueError, 'validation receipt changed'):
                tooling.verify_reader(self.reader)
            run.assert_not_called()

    def test_wrong_upstream_commit_is_rejected(self):
        self.receipt['upstream_commit'] = 'changed'
        self.save()
        with patch.object(tooling, 'checked_upstream', return_value=self.manifest):
            with self.assertRaisesRegex(ValueError, 'different upstream'):
                tooling.verify_reader(self.reader)

    def test_compiler_identity_is_required(self):
        for value in ({}, dict(path='cc', sha256='wrong', version='cc'), 'not-a-record'):
            with self.subTest(value=value):
                self.receipt['compiler'] = value
                self.save()
                with self.assertRaisesRegex(ValueError, 'compiler provenance'):
                    tooling.verify_reader(self.reader)

    def test_validation_requires_exact_inventory_and_all_negative_controls(self):
        for field, value in [('upstream_opcode_vectors_passed', 1293), ('fixture_bytes', 5693),
                ('negative_cases_passed', tooling.NEGATIVE_CASES[:-1]), ('vectors_sha256', '0'*64),
                ('camera_accessed', True)]:
            with self.subTest(field=field):
                report = copy.deepcopy(self.validation)
                report[field] = value
                with self.assertRaisesRegex(ValueError, 'incomplete GNU reader'):
                    tooling.checked_validation(report, self.validation['vectors_sha256'])

    def test_upstream_bytes_and_size_are_pinned(self):
        here = self.root / 'tooling'
        here.mkdir()
        source = self.root / 'source'
        source.mkdir()
        data = source / 'source.c'
        data.write_bytes(b'pinned source\n')
        manifest = dict(commit='fixture', files=[dict(path='source.c', bytes=data.stat().st_size,
            sha256=hashlib.sha256(data.read_bytes()).hexdigest())])
        (here / 'upstream.json').write_text(json.dumps(manifest))
        with patch.object(tooling, 'HERE', here):
            self.assertEqual(tooling.checked_upstream(source), manifest)
            data.write_bytes(b'changed bytes\n')
            with self.assertRaisesRegex(ValueError, 'changed upstream'):
                tooling.checked_upstream(source)
            data.unlink()
            with self.assertRaisesRegex(ValueError, 'changed upstream'):
                tooling.checked_upstream(source)


class BuildInputRaceTests(unittest.TestCase):
    """Mock compilation only to check that changed inputs never get a receipt."""
    def setUp(self):
        (tooling.ROOT / 'local').mkdir(exist_ok=True)

    def test_adapter_or_upstream_change_during_build_rejects_receipt(self):
        for changed in ('adapter', 'upstream'):
            with self.subTest(changed=changed), tempfile.TemporaryDirectory(dir=tooling.ROOT / 'local') as tmp:
                root = Path(tmp)
                source = root / 'source'
                vectors = source / 'gas/testsuite/gas/mn10300/am33-2.d'
                vectors.parent.mkdir(parents=True)
                vectors.write_bytes(b'synthetic identity; compiler and validation are mocked')
                out = root / 'out'
                compiler = root / 'fixture-compiler'
                compiler.write_bytes(b'not executed')
                manifest = dict(commit='fixture', files=[])
                validation = dict(upstream_opcode_vectors_passed=tooling.VECTOR_COUNT,
                    fixture_bytes=tooling.VECTOR_BYTES, negative_cases_passed=tooling.NEGATIVE_CASES,
                    vectors_sha256=tooling.digest(vectors), camera_accessed=False)

                def fake_run(command, **kwargs):
                    out.mkdir(exist_ok=True)
                    (out / 'mn103-reader').write_bytes(b'not executed')
                    (out / 'validation').mkdir(exist_ok=True)
                    (out / 'validation/validation.json').write_text(json.dumps(validation))

                upstream = [manifest, ValueError('changed upstream during build')] if changed == 'upstream' else [manifest]
                before = {'adapter': '0'*64}
                after = {'adapter': '1'*64} if changed == 'adapter' else before
                with patch.object(builder.sys, 'platform', 'linux'), \
                        patch.object(builder.sys, 'argv', ['build', '--source', str(source),
                            '--compiler', str(compiler), '--out', str(out)]), \
                        patch.object(builder, 'checked_upstream', side_effect=upstream), \
                        patch.object(builder, 'source_fingerprints', side_effect=[before, after]), \
                        patch.object(builder.subprocess, 'run', side_effect=fake_run), \
                        patch.object(builder.subprocess, 'check_output', return_value='fixture compiler'):
                    with self.assertRaisesRegex(ValueError, 'changed.*build'):
                        builder.main()
                self.assertFalse((out / 'build.json').exists())


if __name__ == '__main__':
    unittest.main()
