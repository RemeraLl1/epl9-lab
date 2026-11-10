"""Synthetic guards for the boot audit; no firmware or hardware is needed."""
import struct
import unittest

from epl9_boot_recovery_audit import BASE, expected_address, task_records


def table_fixture():
    image = bytearray(0x1a000)
    for slot in range(143):
        ident = 0x808a if slot == 0 else slot if slot < 138 else slot+1
        struct.pack_into('<7I', image, 0x60418cc4-BASE+28*slot,
                         ident, 2 if slot == 1 else 0, 0, BASE+0x400, 55, 2048, 0)
    return image


class TaskTableGuards(unittest.TestCase):
    def test_special_row_and_skipped_ID_are_preserved(self):
        rows = task_records(table_fixture())
        self.assertEqual(len(rows), 143)
        self.assertEqual(rows[0]['id'], 0x808a)
        self.assertEqual(rows[138]['id'], 139)
        self.assertEqual(rows[-1]['id'], 143)

    def test_premature_sentinel_is_rejected(self):
        image = table_fixture()
        image[0x60418cc4-BASE+28*50:0x60418cc4-BASE+28*51] = bytes(28)
        with self.assertRaises(ValueError):
            task_records(image)

    def test_duplicate_ID_is_rejected(self):
        image = table_fixture()
        struct.pack_into('<I', image, 0x60418cc4-BASE+28*90, 89)
        with self.assertRaises(ValueError):
            task_records(image)

    def test_entry_outside_image_is_rejected(self):
        image = table_fixture()
        struct.pack_into('<I', image, 0x60418cc4-BASE+28*89+12, 0x10000000)
        with self.assertRaises(ValueError):
            task_records(image)

    def test_missing_sentinel_is_rejected(self):
        image = table_fixture()
        struct.pack_into('<7I', image, 0x60418cc4-BASE+28*143, 10, 0, 0, BASE+0x400, 1, 2048, 0)
        with self.assertRaises(ValueError):
            task_records(image)

    def test_address_domains_have_boundaries(self):
        # Crossing 41000000 must not blindly create an 81xxxxxx address.
        cases = {0x3fffffff: 0x3fffffff, 0x40000000: 0x80000000,
                 0x40ffffff: 0x80ffffff, 0x41000000: 0x41000000,
                 0x411fb000: 0x411fb000, 0x60000000: 0xa0000000,
                 0x7fffffff: 0xbfffffff, 0x80000000: 0x80000000}
        for value, want in cases.items():
            with self.subTest(address=hex(value)):
                self.assertEqual(expected_address(value), want)


if __name__ == '__main__':
    unittest.main()
