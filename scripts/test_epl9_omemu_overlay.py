"""Safety boundaries for packaging existing components as emulator overlays."""
import base64
import unittest
from epl9_omemu_overlay import overlay


class OverlayTests(unittest.TestCase):
    def test_unsorted_spans_reconstruct_only_declared_changes(self):
        old = b'0123456789'
        new = b'0ab3456XY9'
        rows = overlay(old, new, [(7, 2, 'B'), (1, 2, 'A')], 'resource')
        rebuilt = bytearray(old)
        for row in rows:
            at = row['offset']
            before, after = (base64.b64decode(row[k]) for k in ('old', 'new'))
            self.assertEqual(bytes(rebuilt[at:at+len(before)]), before)
            rebuilt[at:at+len(after)] = after
        self.assertEqual(rebuilt, new)
        self.assertEqual([r['offset'] for r in rows], [1, 7])

    def test_rejects_unlisted_change(self):
        with self.assertRaisesRegex(ValueError, 'undeclared'):
            overlay(b'012345', b'0X234Y', [(1, 1, 'only X')], 'main')

    def test_rejects_overlap_even_if_overlapping_bytes_agree(self):
        with self.assertRaisesRegex(ValueError, 'overlapping'):
            overlay(b'012345', b'01XX45', [(2, 2, 'A'), (3, 1, 'B')], 'main')

    def test_rejects_invalid_bounds_and_size(self):
        for at, size in [(-1, 1), (0, 0), (2, -1), (5, 2)]:
            with self.subTest(at=at, size=size), self.assertRaises(ValueError):
                overlay(b'012345', b'012345', [(at, size, 'bad')], 'resource')
        with self.assertRaisesRegex(ValueError, 'size'):
            overlay(b'0', b'00', [], 'main')


if __name__ == '__main__':
    unittest.main()
