"""Synthetic BOOT-identification guards; fixtures are not real firmware."""
import unittest
import struct

from epl9_boot_source_audit import inspect_candidate,catalog_record
from epl9_recovery_audit import fixture,decoded_payload,ORDER


class BootSourceGuards(unittest.TestCase):
    def test_low_address_stabilizer_is_not_a_BOOT_tag(self):
        row=inspect_candidate(fixture(kind=0x10e,address=0x40002800))
        self.assertFalse(row['BOOT_tag_present'])

    def test_BOOT_tag_is_only_a_candidate(self):
        row=inspect_candidate(fixture(kind=0x110))
        self.assertTrue(row['BOOT_tag_present'])
        self.assertFalse(row['ready_to_install'])
        self.assertFalse(row['independently_bootable'])

    def test_other_model_is_rejected_even_with_good_checksum(self):
        with self.assertRaises(ValueError):inspect_candidate(fixture(kind=0x110,model=0x1220))

    def test_corruption_and_duplicates_are_rejected(self):
        package=fixture(kind=0x110);bad=bytearray(package);bad[40]^=1
        for raw in (bytes(bad),package+package,package[:-16],package+b'x'):
            with self.subTest(bytes=len(raw)):
                with self.assertRaises(ValueError):inspect_candidate(raw)

    def test_unidentified_raw_is_not_assigned_a_camera_model(self):
        row=inspect_candidate(bytes(range(64)))
        self.assertEqual(row['components'],[])
        self.assertFalse(row['model_proven_for_raw_dump'])
        self.assertFalse(row['ready_to_install'])

    def test_nested_BOOT_envelope_is_found_without_qualifying_the_outer_input(self):
        inner=fixture(kind=0x110)
        row=inspect_candidate(b'raw-dump-prefix'+inner+b'raw-dump-tail')
        self.assertEqual(len(row['nested_BOOT_scan']['accepted']),1)
        self.assertEqual(row['nested_BOOT_scan']['accepted'][0]['offset'],15)
        self.assertFalse(row['model_proven_for_raw_dump'])
        self.assertFalse(row['ready_to_install'])

    def test_nested_BOOT_in_decoded_component_and_corruption_control(self):
        inner=fixture(kind=0x110)
        for corrupt in (False,True):
            with self.subTest(corrupt=corrupt):
                body=bytearray(decoded_payload(fixture(size=512)[32:-32]))
                body[32:32+len(inner)]=inner
                if corrupt:body[72]^=1
                header=fixture(size=512)[:32];trailer=bytearray(header)
                total=sum(struct.unpack('<144I',header+body+trailer))
                struct.pack_into('<I',trailer,28,(-total)&0xffffffff)
                encoded=bytearray(512)
                for i,j in enumerate(ORDER):encoded[j::16]=bytes(x^255 for x in body[i::16])
                row=inspect_candidate(header+encoded+trailer)
                scan=row['components'][0]['nested_BOOT_scan']
                self.assertEqual(len(scan['accepted']),int(not corrupt))
                # Repeated metadata in the trailer also resembles a header;
                # raw search can reject that extra candidate independently.
                selected=scan['rejected'] if corrupt else scan['accepted']
                self.assertTrue(any(x['offset']==32 for x in selected))

    def test_catalog_checks_model_and_removes_signature(self):
        raw=b'<firmware_result><firmwares><firmware_info><model_name>E-PL9</model_name><model_id>1330</model_id><url>https://example.invalid/file.BIN?Signature=private</url></firmware_info></firmwares></firmware_result>'
        row=catalog_record(raw)
        self.assertEqual(row['url_without_temporary_signature'],'https://example.invalid/file.BIN')
        self.assertNotIn('private',str(row))
        with self.assertRaises(ValueError):catalog_record(raw.replace(b'1330',b'1220'))


if __name__=='__main__':unittest.main()
