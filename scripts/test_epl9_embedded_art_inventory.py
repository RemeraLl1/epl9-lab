import struct
import unittest
from epl9_embedded_art_inventory import BASE, KEY_BASE, read_table, inventory

class InventoryTest(unittest.TestCase):
    def test_empty_slots_are_not_modes(self):
        image=struct.pack('<IIII',0,0,0x11,0x607521db)
        self.assertEqual(read_table(image,BASE,2),[dict(slot=1,key='0x1010078',target='0x607521db')])

    def test_normalized_variant_is_preserved(self):
        image=struct.pack('<IIII',0x11,7,0x10011,7)
        self.assertEqual([r['key'] for r in read_table(image,BASE,2)],['0x1010078','0x1020078'])

    def test_wrong_input_rejected(self):
        with self.assertRaises(ValueError): inventory(b'not firmware')

    def test_truncated_table_rejected(self):
        with self.assertRaises(struct.error): read_table(bytes(7),BASE,1)

if __name__=='__main__': unittest.main()
