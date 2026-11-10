"""Synthetic checks for component-address and bounded dispatch verification."""
import struct
import unittest

from epl9_video_deep_audit import hash_target
from epl9_video_audit import checked_listing


class DeepAuditTests(unittest.TestCase):
    def test_auxiliary_base_is_not_container_address(self):
        listing = '40002804\t8006\tmov\t6,d0\n'
        image = b'\0'*4+b'\x80\x06'
        self.assertEqual(checked_listing(listing,image,0x40002804,0x40002806,
                                        base=0x40002800)[0x40002804], 'mov\t6,d0')
        with self.assertRaises(ValueError):
            checked_listing(listing,image,0x40002804,0x40002806,base=0x40002820)

    def test_hash_collision_wrap_and_empty(self):
        table = struct.pack('<8I',7,0xabc,0,0,0,0,3,0xdef)
        self.assertEqual(hash_target(table,0,0,4,7),0xabc)
        with self.assertRaises(ValueError):
            hash_target(table,0,0,4,11)

    def test_full_hash_table_is_bounded_and_checks_extent(self):
        table = struct.pack('<8I',4,1,1,2,2,3,3,4)
        with self.assertRaises(ValueError):
            hash_target(table,0,0,4,8)
        with self.assertRaises(ValueError):
            hash_target(table,0,4,4,7)
        with self.assertRaises(ValueError):
            hash_target(table,0,0,3,1)


if __name__ == '__main__':
    unittest.main()
