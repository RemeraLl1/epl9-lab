"""Host-only source identity controls; no firmware or camera inputs."""
import hashlib
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from epl9_source_identity import verified_source
from epl9_osd_audit import DECODER_SHA, DECODER_LF_SHA, DECODER_COMMIT, load_decoder
from epl9_v3_package import (REFERENCE_SOURCE_SHA, REFERENCE_SOURCE_LF_SHA,
                             REFERENCE_COMMIT, independent_parser)

ROOT = Path(__file__).resolve().parents[1]


def sha(data):
    return hashlib.sha256(data).hexdigest()


class SourceIdentityTests(unittest.TestCase):
    def verify(self, raw, expected, legacy='historical'):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'source.py'
            path.write_bytes(raw)
            return verified_source(path, expected, legacy)

    def test_lf_crlf_same_canonical_distinct_raw(self):
        lf = b'x = 1\ny = 2\n'
        crlf = lf.replace(b'\n', b'\r\n')
        for raw, ending in [(lf, 'LF'), (crlf, 'CRLF')]:
            canonical, report = self.verify(raw, sha(lf), sha(crlf))
            self.assertEqual(canonical, lf)
            self.assertEqual(report['raw_sha256'], sha(raw))
            self.assertEqual(report['canonical_lf_sha256'], sha(lf))
            self.assertEqual(report['line_endings'], ending)
            self.assertEqual(report['legacy_raw_match'], raw == crlf)

    def test_mixed_and_bare_cr_rejected_even_if_hash_matches(self):
        for raw in [b'x = 1\r\ny = 2\n', b'x = 1\ry = 2\r', b'x = 1\r\r\n']:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                self.verify(raw, sha(raw.replace(b'\r\n', b'\n')))

    def test_non_line_ending_bytes_never_normalized(self):
        original = b'x = 1\ny = 2\n'
        for changed in [original.replace(b'1', b'9'), b'\xef\xbb\xbf'+original,
                        original.replace(b' = ', b'='), original[:-1],
                        original+b'\n', original.replace(b'1\n', b'1 \n')]:
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                self.verify(changed, sha(original))

    def test_no_newline_does_not_add_one(self):
        raw = b'x = 1'
        self.assertEqual(self.verify(raw, sha(raw))[0], raw)


class PinnedUpstreamTests(unittest.TestCase):
    def pinned(self, repo, commit, name):
        directory = ROOT / 'references' / repo
        if not (directory / '.git').exists():
            self.skipTest('optional ignored pinned upstream checkout not present')
        return subprocess.check_output(['git', '-C', str(directory), 'show', commit+':'+name])

    def test_both_pins_derive_from_exact_upstream_commits(self):
        cases = [('caduceus-ep7', DECODER_COMMIT, 'tools/osd_extract.py', DECODER_LF_SHA, DECODER_SHA),
                 ('oly_fw_analysis', REFERENCE_COMMIT, 'tools/oly_container.py',
                  REFERENCE_SOURCE_LF_SHA, REFERENCE_SOURCE_SHA)]
        for repo, commit, name, canonical_sha, legacy_sha in cases:
            with self.subTest(repo=repo):
                lf = self.pinned(repo, commit, name)
                self.assertNotIn(b'\r', lf)
                self.assertEqual(sha(lf), canonical_sha)
                self.assertEqual(sha(lf.replace(b'\n', b'\r\n')), legacy_sha)
                for source in (lf, lf.replace(b'\n', b'\r\n')):
                    with tempfile.TemporaryDirectory() as directory:
                        path = Path(directory)/'source.py'
                        path.write_bytes(source)
                        _, report = verified_source(path, canonical_sha, legacy_sha)
                        self.assertEqual(report['raw_sha256'], sha(source))

    def test_decoder_loads_verified_lf_and_crlf_snapshots(self):
        lf = self.pinned('caduceus-ep7', DECODER_COMMIT, 'tools/osd_extract.py')
        for source in (lf, lf.replace(b'\n', b'\r\n')):
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory)/'osd_extract.py'
                path.write_bytes(source)
                decoder = load_decoder(path)
                self.assertEqual(decoder._source_identity['raw_sha256'], sha(source))
                self.assertEqual(decoder.COMPONENT_ADDR, 0x421e0020)
                path.write_bytes(source+b'# changed\n')
                with self.assertRaises(ValueError):
                    load_decoder(path)

    def test_parser_loads_both_endings_and_preserves_commit_guard(self):
        lf = self.pinned('oly_fw_analysis', REFERENCE_COMMIT, 'tools/oly_container.py')
        for source in (lf, lf.replace(b'\n', b'\r\n')):
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                path = root/'references/oly_fw_analysis/tools/oly_container.py'
                path.parent.mkdir(parents=True)
                path.write_bytes(source)
                with patch('epl9_v3_package.ROOT', root), patch(
                        'epl9_v3_package.subprocess.check_output', return_value=REFERENCE_COMMIT+'\n'):
                    parser = independent_parser()
                    self.assertEqual(parser._source_identity['raw_sha256'], sha(source))
                    path.write_bytes(source+b'# changed\n')
                    with self.assertRaises(ValueError):
                        independent_parser()
                path.write_bytes(source)
                with patch('epl9_v3_package.ROOT', root), patch(
                        'epl9_v3_package.subprocess.check_output', return_value='wrong commit\n'):
                    with self.assertRaises(ValueError):
                        independent_parser()


if __name__ == '__main__':
    unittest.main()
