import struct
import unittest
from epl9_art_property_inventory import BASE,TABLE,COUNT,backing_slot,audit

class PropertyInventory(unittest.TestCase):
    def test_indexed_halfwords_not_whole_word(self):
        image=bytearray(TABLE-BASE+4*COUNT)
        struct.pack_into('<HH',image,TABLE-BASE+4*0x1d4,0x44c1,8)
        self.assertEqual(backing_slot(image,0x1d4),dict(property_id='0x1d4',storage_id='0x44c1',element_index=8))
    def test_bounds(self):
        for p in (-1,COUNT):
            with self.assertRaises(ValueError):backing_slot(b'',p)
    def test_truncated(self):
        with self.assertRaises(ValueError):backing_slot(b'',0x1d4)
    def test_exact_stock_required(self):
        with self.assertRaises(ValueError):audit(b'not OEM')

if __name__=='__main__':unittest.main()
