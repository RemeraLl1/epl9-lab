"""Synthetic trace tests. No network, camera or capture-driver access."""
import unittest

from epl9_wifi_trace import analyze_stream, merged_ranges, CAMERA


def packet(seq, size, timestamp, flags='0x18', retry='', src=CAMERA, payload=''):
    return {'ip.src': src, 'ip.dst': 'pc' if src == CAMERA else CAMERA,
            'tcp.seq': str(seq), 'tcp.len': str(size), 'frame.time_epoch': str(timestamp),
            'tcp.flags': flags, 'tcp.analysis.retransmission': retry, 'tcp.payload': payload}


def request():
    return packet(1, 80, 0, src='pc', payload=b'GET /DCIM/100OLYMP/PB020002.MOV HTTP/1.1\r\n'.hex())


class TraceTests(unittest.TestCase):
    def test_adjacent_and_overlapping_ranges(self):
        self.assertEqual(merged_ranges([(10, 20), (1, 10), (5, 12), (30, 35)]), [[1, 20], [30, 35]])

    def test_fin_retry_is_not_repeated_file_data(self):
        rows = [request(), packet(1, 8105416+94, .1),
                packet(8105416+95, 0, .2, '0x11'), packet(8105416+95, 0, .3, '0x11', '1')]
        result = analyze_stream(rows)
        self.assertEqual(result['data_retry_frames'], 0)
        self.assertEqual(result['control_only_retry_frames'], 1)
        self.assertTrue(result['response_capture_complete'])
        self.assertEqual(result['inferred_header_bytes'], 94)

    def test_data_retry_does_not_inflate_unique_response(self):
        rows = [request(), packet(1, 8105416+94, .1), packet(1, 8105416+94, .2, retry='1'),
                packet(8105416+95, 0, .3, '0x11')]
        result = analyze_stream(rows)
        self.assertEqual(result['data_retry_frames'], 1)
        self.assertEqual(result['captured_unique_response_bytes'], 8105416+94)
        self.assertEqual(result['duplicate_captured_payload_bytes'], 8105416+94)

    def test_capture_cut_is_not_an_http_transfer_failure(self):
        result = analyze_stream([request(), packet(1, 50000, .1)])
        self.assertFalse(result['response_capture_complete'])
        self.assertIsNone(result['inferred_header_bytes'])
        self.assertEqual(result['after_16k_boundary_gap_ms']['n'], 0)

    def test_boundary_uses_body_offset_not_header_offset(self):
        rows = [request(), packet(1, 94, .01), packet(95, 16384, .02),
                packet(16479, 8105416-16384, .025), packet(8105416+95, 0, .1, '0x11')]
        result = analyze_stream(rows)
        self.assertEqual(result['after_16k_boundary_gap_ms']['n'], 1)
        self.assertAlmostEqual(result['after_16k_boundary_gap_ms']['median'], 5)

    def test_missing_sequence_range_rejects_header_inference(self):
        rows = [request(), packet(1, 100, .1), packet(201, 8105416, .2), packet(8105617, 0, .3, '0x11')]
        result = analyze_stream(rows)
        self.assertFalse(result['response_capture_complete'])
        self.assertIsNone(result['inferred_header_bytes'])


if __name__ == '__main__':
    unittest.main()
