import struct
import unittest
from epl9_job_probe import experiment
from epl9_offline_prototype import header
from epl9_film_handoff import base_request


class NativeParameterContractTests(unittest.TestCase):
    def test_request_kind_is_independent_of_pixel_format(self):
        row=base_request(0x01010078,0x1000)
        self.assertEqual(len(row),1876)
        self.assertEqual(struct.unpack_from('<H',row,14)[0],0x1000)
        self.assertEqual(struct.unpack_from('<H',row,28)[0],0x100)
        self.assertEqual(row[8:12],header(0x01010078))
        for kind in (0,0x1001,0x1200,0xffff):
            with self.subTest(kind=kind),self.assertRaisesRegex(ValueError,'unqualified synthetic format'):
                base_request(0x01010078,kind)

    def parameters(self):
        row=bytearray(32)
        struct.pack_into('<2I',row,0,0x607cfe8d,0x2c000000)
        row[8:12]=header(0x01010078)
        struct.pack_into('<H',row,16,0x1000)
        row[18]=row[19]=1
        return row

    def test_new_kind_requires_explicit_native_parameter_fixture(self):
        with self.assertRaisesRegex(ValueError,'declared target'):
            experiment(b'',{},0x01010078,0x1000,0)

    def test_mismatched_or_mutable_parameters_stop_before_firmware_execution(self):
        row=self.parameters()
        candidates=[row,bytes(row[:-1]),bytes(row)+b'\0']
        for at,value in ((0,0),(4,0),(8,0),(16,0),(21,2)):
            changed=bytearray(row)
            if at in (0,4):struct.pack_into('<I',changed,at,value)
            else:changed[at]=value
            # Kind 0x1000 occupies the high byte of the halfword.
            if at==16:changed[17]=0
            candidates.append(bytes(changed))
        for candidate in candidates:
            with self.subTest(parameter_type=type(candidate).__name__,value=bytes(candidate).hex()):
                with self.assertRaisesRegex(ValueError,'parameter fixture identity/size'):
                    experiment(b'',{},0x01010078,0x1000,0,parameter_fixture=candidate)


if __name__=='__main__':unittest.main()
