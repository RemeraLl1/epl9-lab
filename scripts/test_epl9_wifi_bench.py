"""Synthetic transfer-integrity tests: in-memory transport, no camera/socket."""
import http.client
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import time
import unittest
from unittest.mock import patch

from epl9_wifi_bench import classify, fetch, FILES, MEDIA, METADATA, ROOT, USER_AGENT, validate_target, run


BODY = b''.join(hashlib.sha256(n.to_bytes(4, 'little')).digest() for n in range(8192))
PATH = '/DCIM/100OLYMP/PB020002.MOV'


class FakeResponse:
    def __init__(self, body=BODY, status=200, headers=None, fail_after=None):
        self.body, self.status, self.position = body, status, 0
        self.headers = headers if headers is not None else {'Content-Length': str(len(body))}
        self.fail_after = fail_after

    def getheaders(self):
        return self.headers.items()

    def read1(self, size):
        if self.fail_after is not None and self.position >= self.fail_after:
            raise http.client.IncompleteRead(b'')
        # Short reads must not be mistaken for EOF.
        end = min(len(self.body), self.position+min(size, 7777))
        data = self.body[self.position:end]
        self.position = end
        return data


class FakeConnection:
    def __init__(self, response):
        self.response, self.sock, self.closed = response, None, False
        self.requested = None

    def connect(self):
        pass

    def request(self, *args, **kwargs):
        self.requested = args, kwargs

    def getresponse(self):
        return self.response

    def close(self):
        self.closed = True


class TransferTests(unittest.TestCase):
    def fetch_fake(self, response, **kwargs):
        conn = FakeConnection(response)
        with patch.dict(MEDIA, {PATH: len(BODY)}):
            report, body = fetch('unused.invalid', 80, PATH,
                                 connection_factory=lambda *a, **k: conn, **kwargs)
        self.assertTrue(conn.closed)
        self.assertEqual(conn.requested[0], ('GET', PATH))
        self.assertEqual(conn.requested[1]['headers']['User-Agent'], USER_AGENT)
        return report, body

    def test_short_reads_assemble_complete_original(self):
        report, body = self.fetch_fake(FakeResponse())
        result = classify(report['status'], report['headers'], body,
                          expected_size=len(BODY), complete=report['complete'], reference=BODY)
        self.assertTrue(result['valid'])
        self.assertEqual(body, BODY)
        self.assertEqual(report['read_events'][-1][2], len(BODY))
        self.assertGreater(len(report['read_events']), 2)

    def test_corruption_same_size_is_rejected(self):
        body = BODY[:-1]+b'x'
        result = classify(200, {}, body, expected_size=len(BODY), reference=BODY)
        self.assertIn('reference_hash_mismatch', result['issues'])

    def test_truncated_original_is_rejected(self):
        report, body = self.fetch_fake(FakeResponse(BODY[:1000], headers={'Content-Length': str(len(BODY))}))
        result = classify(200, report['headers'], body, expected_size=len(BODY), complete=report['complete'])
        self.assertIn('original_size_mismatch', result['issues'])
        self.assertIn('content_length_mismatch', result['issues'])

    def test_error_after_partial_body_preserves_evidence(self):
        report, body = self.fetch_fake(FakeResponse(fail_after=7777))
        self.assertEqual(body, BODY[:7777])
        self.assertFalse(report['complete'])
        self.assertIn('IncompleteRead', report['error'])

    def test_ignored_range_is_bounded_and_rejected(self):
        report, body = self.fetch_fake(FakeResponse(), byte_range=(65536, 131071))
        self.assertEqual(len(body), 65537)
        self.assertFalse(report['complete'])
        result = classify(200, report['headers'], body, expected_size=len(BODY),
                          byte_range=(65536, 131071), reference=BODY, complete=report['complete'])
        self.assertIn('range_ignored', result['issues'])

    def test_actual_nonzero_range(self):
        interval = (65536, 131071)
        part = BODY[interval[0]:interval[1]+1]
        headers = {'Content-Length': str(len(part)), 'Content-Range': f'bytes 65536-131071/{len(BODY)}'}
        report, body = self.fetch_fake(FakeResponse(part, 206, headers), byte_range=interval)
        self.assertTrue(classify(206, headers, body, expected_size=len(BODY), byte_range=interval,
                                 reference=BODY, complete=report['complete'])['valid'])

    def test_wrong_range_offsets_rejected_even_if_length_matches(self):
        result = classify(206, {'Content-Range': f'bytes 0-65535/{len(BODY)}'}, BODY[:65536],
                          expected_size=len(BODY), byte_range=(65536, 131071), reference=BODY)
        self.assertIn('content_range_mismatch', result['issues'])

    def test_wrong_total_in_range_rejected(self):
        result = classify(206, {'Content-Range': 'bytes 0-65535/999999'}, BODY[:65536],
                          expected_size=len(BODY), byte_range=(0, 65535), reference=BODY)
        self.assertIn('content_range_mismatch', result['issues'])

    def test_correct_range_header_with_wrong_body_rejected(self):
        result = classify(206, {'Content-Range': f'bytes 65536-131071/{len(BODY)}'}, BODY[:65536],
                          expected_size=len(BODY), byte_range=(65536, 131071), reference=BODY)
        self.assertIn('range_reference_mismatch', result['issues'])

    def test_encoding_and_bad_length_rejected(self):
        result = classify(200, {'Content-Length': 'bad', 'Content-Encoding': 'gzip'}, BODY)
        self.assertIn('invalid_content_length', result['issues'])
        self.assertIn('unexpected_content_encoding', result['issues'])

    def test_metadata_has_a_hard_cap(self):
        conn = FakeConnection(FakeResponse(b'x'*(2*1024*1024)))
        report, body = fetch('unused.invalid', 80, METADATA[0], connection_factory=lambda *a, **k: conn)
        self.assertEqual(len(body), 1024*1024+1)
        self.assertFalse(report['complete'])

    def test_vendor_writes_and_arbitrary_paths_rejected(self):
        for path in ['/set_camprop.cgi?x=y', '/exec_pwoff.cgi', '/switch_cammode.cgi',
                     '/DCIM/../settings', PATH+'?x=1', 'http://example.com/']:
            with self.subTest(path=path), self.assertRaises(ValueError):
                validate_target(path)

    def test_invalid_range_rejected_before_connection(self):
        for interval in [(-1, 1), (5, 4), (0, MEDIA[PATH])]:
            with self.subTest(interval=interval), self.assertRaises(ValueError):
                fetch('unused.invalid', 80, PATH, byte_range=interval)

    def test_full_manifest_workflow_without_camera(self):
        def synthetic_fetch(host, port, path, **kwargs):
            self.assertEqual(host, '192.168.0.10')
            if path in METADATA:
                data, status, headers = b'<synthetic/>', 200, {}
            else:
                data, status, headers = BODY, 200, {}
                if kwargs.get('byte_range'):
                    first, last = kwargs['byte_range']
                    data, status = BODY[first:last+1], 206
                    headers['Content-Range'] = f'bytes {first}-{last}/{len(BODY)}'
            headers['Content-Length'] = str(len(data))
            start = time.perf_counter()
            return dict(path=path, status=status, headers=headers, complete=True, error=None,
                        bytes=len(data), elapsed_s=0.5, mib_s=len(data)/1048576/0.5,
                        started_perf_s=start, finished_perf_s=start+0.5), data

        with tempfile.TemporaryDirectory(prefix='wifi-test-', dir=ROOT/'local') as folder:
            out = Path(folder)/'measurements'
            with patch.dict(FILES, {name: len(BODY) for name in FILES}), \
                    patch('epl9_wifi_bench.fetch', side_effect=synthetic_fetch):
                run(SimpleNamespace(out=out, original_root=None, repeats=2, parallel=2,
                                    range_probe=True, read_size=65536))
            report = json.loads((out/'measurements.json').read_text())
            self.assertEqual(len(report['metadata']), 4)
            self.assertEqual(len(report['trials']), 16)
            self.assertEqual(len(report['parallel_groups']), 2)
            self.assertEqual(report['owner_hash_text_length'], 42)
            self.assertTrue(all(r['valid'] for r in report['trials']))
            self.assertTrue(all(not r['verified_against_card_reader'] for r in report['trials']))
            self.assertTrue(all(r['all_sha256_equal'] for r in report['serial_summary'].values()))
            self.assertIn('paired_wall_speedup', report['parallel_groups'][0])


if __name__ == '__main__':
    unittest.main()
