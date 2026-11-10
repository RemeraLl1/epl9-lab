"""Synthetic safety checks; these do not exercise camera video or gyro hardware."""
import hashlib
from pathlib import Path
import tempfile
import unittest

from epl9_video_audit import BASE, ROOT, checked_listing, local_output, verified_input


class VideoAuditSafetyTests(unittest.TestCase):
    def test_identity_rejects_same_length_corruption_and_truncation(self):
        scratch = (ROOT / 'local/tmp').resolve()
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as folder:
            self.assertTrue(Path(folder).resolve().is_relative_to(scratch))
            path = Path(folder) / 'synthetic.bin'
            original = b'\x80\x01\xdf\x00\x04'
            digest = hashlib.sha256(original).hexdigest()
            path.write_bytes(original)
            self.assertEqual(verified_input(path, len(original), digest), original)
            for wrong in (original[:-1], b'\x81' + original[1:]):
                path.write_bytes(wrong)
                with self.assertRaises(ValueError):
                    verified_input(path, len(original), digest)

    def test_listing_covers_exact_bytes_and_last_instruction(self):
        listing = f'{BASE:x}\t8001\tmov\t1,d0\n{BASE+2:x}\tdf0004\tret\t[],4\n'
        decoded = checked_listing(listing, bytes.fromhex('8001df0004'), BASE, BASE + 4)
        self.assertEqual(decoded[BASE + 2], 'ret\t[],4')

    def test_listing_rejects_wrong_bytes_holes_duplicates_and_incomplete(self):
        image = bytes.fromhex('8001df0004')
        for listing in (f'{BASE:x}\t8002\tmov\t2,d0\n',
                        f'{BASE+2:x}\tdf0004\tret\t[],4\n',
                        f'{BASE:x}\t8001\tmov\t1,d0\n{BASE:x}\t8001\tmov\t1,d0\n',
                        f'{BASE:x}\t8001\tmov\t1,d0\n',
                        f'{BASE:x}\t8001df000400\tdata\n'):
            with self.subTest(listing=listing), self.assertRaises(ValueError):
                checked_listing(listing, image, BASE, BASE + 5)

    def test_output_rejects_existing_and_nonlocal_destinations(self):
        for path in (ROOT / 'local', ROOT / 'scripts/new-video-evidence',
                     ROOT / 'local/../firmware/new-video-evidence'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                local_output(path)


if __name__ == '__main__':
    unittest.main()
