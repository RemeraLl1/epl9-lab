"""Synthetic guards for the stock-only inventory; no firmware fixtures."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import epl9_hls_cloud_inventory as audit


class InventoryTests(unittest.TestCase):
    def setUp(self):
        base = audit.ROOT/'local/test-temp'
        base.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='hls-inventory-', dir=base)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.main = self.root/'synthetic-input.bin'
        self.main.write_bytes(b'\0'*4)
        self.out = self.root/'result'
        self.reader = self.root/'mock-reader'

    def test_raw_calls_are_candidates_including_unaligned_patterns(self):
        data = bytearray(40)
        target = audit.BASE+32
        for at, opcode, width in ((1, 0xcd, 2), (9, 0xdd, 4)):
            data[at:at+width+3] = bytes([opcode])+(target-audit.BASE-at).to_bytes(width, 'little', signed=True)+b'\xf0\x18'
        self.assertEqual(audit.raw_call_candidates(data, target), [hex(audit.BASE+1), hex(audit.BASE+9)])
        # A pattern inside an arbitrary byte array remains only a candidate;
        # this API supplies no instruction-boundary or user identity proof.
        self.assertEqual(audit.raw_call_candidates(b'\xcd\x20', target), [])

    def test_root_matches_preserve_raw_offsets_without_user_claims(self):
        value = audit.ROOT_ADDRESS.to_bytes(4, 'little')
        self.assertEqual(audit.literal_candidates(b'x'+value+b'x'+value, audit.ROOT_ADDRESS),
                         [hex(audit.BASE+1), hex(audit.BASE+6)])

    def test_missing_or_wrong_input_never_creates_output_or_runs_decoder(self):
        with patch.object(audit, 'reader_provenance') as reader:
            with self.assertRaises(FileNotFoundError):
                audit.run(self.root/'missing.bin', self.out, self.reader)
            with self.assertRaises(ValueError):
                audit.run(self.main, self.out, self.reader)
            with patch.object(audit, 'MAIN_BYTES', 4):
                with self.assertRaises(ValueError):
                    audit.run(self.main, self.out, self.reader)
            self.assertFalse(self.out.exists())
            reader.assert_not_called()

    def synthetic_run(self, decode):
        with patch.object(audit, 'MAIN_BYTES', 4), patch.object(audit, 'MAIN_SHA', audit.sha(b'\0'*4)), \
             patch.object(audit, 'WINDOWS', {'synthetic': (audit.BASE, audit.BASE+1)}), \
             patch.object(audit, 'reader_provenance', return_value={'synthetic_decoder_fixture': True}), \
             patch.object(audit.subprocess, 'check_output', side_effect=decode):
            return audit.run(self.main, self.out, self.reader)

    def test_input_snapshot_and_conservative_report(self):
        def decode(command, **options):
            snapshot = Path(command[1])
            self.assertEqual(snapshot.read_bytes(), b'\0'*4)
            self.assertNotEqual(snapshot, self.main)
            return f'{audit.BASE:08x}\t00\tnop\n'
        report = self.synthetic_run(decode)
        self.assertEqual(report['windows']['synthetic']['instructions'], 1)
        for flag in ('full_hls_loop_covered', 'task_stop_acknowledgement_proven',
                     'five_vector_users_complete', 'cached_or_inflight_users_drained',
                     'local_chat_stop_confirmed', 'camera_accessed', 'install_ready'):
            self.assertIs(report[flag], False)
        self.assertFalse((self.out/'stock-main-input.bin').exists())
        self.assertTrue((self.out/'inventory.json').is_file())

    def test_decoder_failure_removes_private_snapshot_and_leaves_no_success_report(self):
        def decode(command, **options):
            raise ValueError('declared decoder failure')
        with self.assertRaisesRegex(ValueError, 'declared decoder failure'):
            self.synthetic_run(decode)
        self.assertFalse((self.out/'stock-main-input.bin').exists())
        self.assertFalse((self.out/'inventory.json').exists())

    def test_altered_listing_is_rejected_without_leaving_firmware_or_success_report(self):
        def decode(command, **options):
            return f'{audit.BASE:08x}\tff\tnop\n'
        with self.assertRaisesRegex(ValueError, 'listing bytes do not match'):
            self.synthetic_run(decode)
        self.assertFalse((self.out/'stock-main-input.bin').exists())
        self.assertFalse((self.out/'inventory.json').exists())


if __name__ == '__main__':
    unittest.main()
