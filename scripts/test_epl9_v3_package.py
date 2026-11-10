import unittest

from epl9_recovery_audit import decoded_payload, fixture, inspect_package
from epl9_v3_package import encode_payload, pair, replace_component, sum32, generation_inputs


class PackageTests(unittest.TestCase):
    def test_generations_keep_recipe_osd_identity_but_never_alias_main_or_package_name(self):
        old = generation_inputs('frozen-v3')
        new = generation_inputs('private-color-v3')
        self.assertNotEqual(old[0],new[0])
        self.assertNotEqual(old[1],new[1])
        self.assertNotEqual(old[2][0x100],new[2][0x100])
        self.assertEqual(old[2][0x101],new[2][0x101])
        self.assertNotEqual(old[3],new[3])
        with self.assertRaises(ValueError):generation_inputs('unqualified')

    def test_encode_inverse_and_unchanged_component_reproduce_exact_bytes(self):
        for size in (16, 80, 256, 4096):
            raw = fixture(size=size)
            plain = decoded_payload(raw[32:-32])
            self.assertEqual(encode_payload(plain), raw[32:-32])
            self.assertEqual(replace_component(raw, plain), raw)

    def test_replacement_repairs_checksum_preserving_all_other_envelope_fields(self):
        raw = fixture(size=256)
        plain = bytearray(decoded_payload(raw[32:-32]))
        plain[0] ^= 255
        plain[-1] ^= 0x5a
        changed = replace_component(raw, bytes(plain))
        self.assertEqual(changed[:32], raw[:32])
        self.assertEqual(changed[-32:-4], raw[-32:-4])
        self.assertEqual(decoded_payload(changed[32:-32]), plain)
        self.assertEqual(sum32(changed[:32]+plain+changed[-32:]), 0)
        self.assertNotEqual(changed[-4:], raw[-4:])

    def test_pair_covers_both_changed_components_and_restore_is_exact_stock(self):
        main, osd, pictures = fixture(), fixture(kind=0x101), fixture(kind=0x102)
        originals = {0x100: decoded_payload(main[32:-32]), 0x101: decoded_payload(osd[32:-32])}
        replacements = {k: bytes(x ^ 0x5a for x in v) for k, v in originals.items()}
        candidate, restore = pair(main+osd+pictures, replacements)
        self.assertEqual(restore, main+osd)
        self.assertEqual([r['kind'] for r in inspect_package(candidate)], ['0x100', '0x101'])
        self.assertEqual(len(candidate), len(restore))
        self.assertNotEqual(candidate, restore)

    def test_missing_extra_duplicate_or_wrong_order_components_are_rejected(self):
        main, osd = fixture(), fixture(kind=0x101)
        plain = decoded_payload(main[32:-32])
        for replacements in ({0x100: plain}, {0x100: plain, 0x101: plain, 0x102: plain}):
            with self.assertRaises(ValueError):
                pair(main+osd, replacements)
        for raw in (main, osd+main, main+main+osd):
            with self.assertRaises(ValueError):
                pair(raw, {0x100: plain, 0x101: plain})

    def test_size_changes_and_unsupported_target_are_rejected(self):
        for template, plain in ((fixture(), bytes(240)), (fixture(kind=0x102), bytes(256))):
            with self.assertRaises(ValueError):
                replace_component(template, plain)
        for data in (b'', b'abc'):
            with self.assertRaises(ValueError):
                encode_payload(data)
            with self.assertRaises(ValueError):
                sum32(data)

    def test_checksum_valid_does_not_accept_metadata_corruption(self):
        raw = bytearray(fixture())
        raw[-12] ^= 1
        with self.assertRaisesRegex(ValueError, 'header/trailer'):
            replace_component(bytes(raw), bytes(256))


if __name__ == '__main__':
    unittest.main()
