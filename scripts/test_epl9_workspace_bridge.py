import struct
import unittest
import copy
import json
from pathlib import Path

from epl9_workspace_bridge import (Epl9Orf, P_SIZE, T_SIZE, decode_cmio,
                                    replace_span, verify_copy, validate_recipes)


def synthetic_orf():
    data = bytearray(200128)
    data[:8] = b'IIRO'+struct.pack('<I', 8)

    def ifd(at, entries):
        struct.pack_into('<H', data, at, len(entries))
        for i, row in enumerate(entries):
            struct.pack_into('<HHII', data, at+2+12*i, *row)

    ifd(8, [(0x110, 2, 17, 512), (0x8769, 4, 1, 128),
            (0x111, 4, 1, 200000), (0x117, 4, 1, 128)])
    data[512:529] = b'E-PL9           \0'
    ifd(128, [(0x927c, 7, 96, 1024)])
    data[1024:1036] = b'OLYMPUS\0II\x03\0'
    ifd(1036, [(0x2040, 13, 1, 64)])
    ifd(1088, [(0x635, 7, P_SIZE, 1024), (0x636, 7, T_SIZE, 20000)])
    for at in (2048, 21024):
        data[at:at+8] = b'CMIO\x01\x00\x13\xdc'
    data[200000:] = bytes(range(128))
    return data


class OrfBoundsTests(unittest.TestCase):
    def test_native_metadata_and_raw_spans_remain_separate(self):
        layout = Epl9Orf(bytes(synthetic_orf()))
        self.assertEqual(layout.strips, ((200000, 128),))
        self.assertEqual((layout.p['offset'], layout.t['offset']), (2048, 21024))

    def test_other_model_and_cmio_revision_are_rejected(self):
        for at, replacement in ((512, b'PEN-F'), (2054, b'\x11')):
            data = synthetic_orf()
            data[at:at+len(replacement)] = replacement
            with self.assertRaises(ValueError):
                Epl9Orf(bytes(data))

    def test_truncated_pointer_and_duplicate_tag_are_rejected(self):
        for data in (synthetic_orf()[:-10], synthetic_orf()):
            if len(data) == 200128:
                struct.pack_into('<H', data, 1088+2+12, 0x635)
            with self.assertRaises(ValueError):
                Epl9Orf(bytes(data))

    def test_raw_overlap_with_metadata_is_rejected(self):
        data = synthetic_orf()
        struct.pack_into('<I', data, 8+2+2*12+8, 2048)
        with self.assertRaisesRegex(ValueError, 'overlaps RAW'):
            Epl9Orf(bytes(data))


class EncodedSpanTests(unittest.TestCase):
    def test_patch_recovers_exact_plain_span_including_both_boundaries(self):
        key = tuple((i*7919+0x12345678) & 0xffffffff for i in range(63))
        encoded = bytearray(b'CMIO\x01\x00\x13\xdc'+bytes(range(256))*3)
        before = decode_cmio(encoded, key)
        replacement = bytes(range(99))
        replace_span(encoded, 211, before[211:310], replacement)
        self.assertEqual(decode_cmio(encoded, key), before[:211]+replacement+before[310:])

    def test_missing_end_boundary_corrupts_following_plaintext(self):
        key = tuple(range(63))
        encoded = bytearray(b'CMIO\x01\x00\x13\xdc'+b'\0'*80)
        before = decode_cmio(encoded, key)
        encoded[20] ^= 0x71  # Deliberately omit C[21], unlike a valid span edit.
        after = decode_cmio(encoded, key)
        self.assertNotEqual(after[21:], before[21:])

    def test_span_cannot_change_header_length_or_run_past_block(self):
        for at, old, new in ((7, b'a', b'b'), (10, b'a', b'bc'), (19, b'a', b'b')):
            with self.assertRaises(ValueError):
                replace_span(bytearray(20), at, old, new)

    def test_allowed_metadata_cannot_authorize_a_raw_change(self):
        original = bytes(range(100))
        changed = bytearray(original)
        changed[40] ^= 1
        with self.assertRaisesRegex(ValueError, 'RAW samples'):
            verify_copy(original, changed, [(40, 1)], [(32, 32)])
        with self.assertRaisesRegex(ValueError, 'unrelated'):
            verify_copy(original, changed, [(50, 1)], [(80, 20)])
        with self.assertRaisesRegex(ValueError, 'length'):
            verify_copy(original, changed[:-1], [], [])


class RecipeContractTests(unittest.TestCase):
    def setUp(self):
        path = Path(__file__).resolve().parents[1]/'recipes/epl9-film-drafts-v0.json'
        self.document = json.loads(path.read_text(encoding='utf-8'))

    def test_checked_in_drafts_preserve_two_distinct_accepted_slots(self):
        rows = validate_recipes(self.document)
        self.assertEqual({r['watercolor_key'] for r in rows}, {'0x01010078', '0x01020078'})
        self.assertNotEqual(rows[0]['native_hsl'], rows[1]['native_hsl'])

    def test_duplicate_identity_or_swapped_mode_is_rejected(self):
        for field in ('name', 'watercolor_key'):
            document = copy.deepcopy(self.document)
            document['recipes'][1][field] = document['recipes'][0][field]
            with self.assertRaises(ValueError):
                validate_recipes(document)

    def test_overflow_bool_and_missing_record_are_rejected(self):
        for value in (32768, -32769, True, 0.5):
            document = copy.deepcopy(self.document)
            document['recipes'][0]['native_hsl'][0][0] = value
            with self.assertRaises(ValueError):
                validate_recipes(document)
        self.document['recipes'][0]['native_hsl'].pop()
        with self.assertRaises(ValueError):
            validate_recipes(self.document)


if __name__ == '__main__':
    unittest.main()
