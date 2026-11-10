"""Host package guards for the offline-only E-PL9 recovery audit."""
import struct
import unittest

from epl9_recovery_audit import fixture,inspect_package


class RecoveryGuards(unittest.TestCase):
    def test_valid_component_identity(self):
        row,=inspect_package(fixture())
        self.assertEqual((row['model'],row['header_build'],row['kind'],row['package_bytes']),
                         ('1330','1101','0x100',320))

    def test_wrong_camera_rejected(self):
        with self.assertRaises(ValueError):inspect_package(fixture(model=0x1220))

    def test_corrupt_payload_rejected(self):
        raw=bytearray(fixture());raw[40]^=1
        with self.assertRaisesRegex(ValueError,'checksum'):inspect_package(raw)

    def test_truncated_later_component_rejected(self):
        raw=fixture()+fixture(kind=0x101)[:-1]
        with self.assertRaises(ValueError):inspect_package(raw)

    def test_duplicate_main_rejected_by_host(self):
        with self.assertRaisesRegex(ValueError,'component'):inspect_package(fixture()*2)

    def test_repaired_checksum_does_not_hide_metadata_mismatch(self):
        raw=bytearray(fixture());raw[-12]^=1
        # A compensating checksum keeps the additive total at zero. The host
        # must still compare kind/reserved metadata beyond native's first 20 B.
        checksum=struct.unpack_from('<I',raw,len(raw)-4)[0]
        struct.pack_into('<I',raw,len(raw)-4,(checksum-1)&0xffffffff)
        with self.assertRaisesRegex(ValueError,'header/trailer'):inspect_package(raw)

    def test_unknown_component_rejected(self):
        with self.assertRaises(ValueError):inspect_package(fixture(kind=0x110))

    def test_invalid_lengths(self):
        for size in (0,15,17):
            with self.subTest(size=size),self.assertRaises(ValueError):fixture(size=size)
        raw=bytearray(fixture());struct.pack_into('<I',raw,12,0xfffffff0)
        with self.assertRaises(ValueError):inspect_package(raw)

    def test_extra_trailing_bytes_rejected(self):
        with self.assertRaises(ValueError):inspect_package(fixture()+b'garbage')


if __name__=='__main__':unittest.main()
