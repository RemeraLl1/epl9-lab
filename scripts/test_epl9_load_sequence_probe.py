import unittest
from types import SimpleNamespace
from epl9_load_sequence_probe import LocalStorageRead, STORAGE_BASE
from mn103_subset import Memory, Region, Fault


class LocalStorageBoundaryTests(unittest.TestCase):
    def machine(self, destination=0x1000, source=0x406e0800, size=2048):
        backing = bytearray([0xa5])*16 + bytearray(4096) + bytearray([0xa5])*16
        m = SimpleNamespace(r=dict(d0=destination, d1=source, a0=size),
            memory=Memory([Region(0xff0, backing, True)]))
        return m, backing

    def test_copy_uses_storage_offset_and_preserves_destination_guards(self):
        source = bytes(i % 251 for i in range(8192))
        read = LocalStorageRead(source, 0x1000, 4096)
        m, data = self.machine()
        read.validate(m, 0xf0, 44); read.apply(m)
        offset = 0x406e0800-STORAGE_BASE
        self.assertEqual(data[16:2064], source[offset:offset+2048])
        self.assertEqual(data[:16]+data[-16:], b'\xa5'*32)
        self.assertEqual(data[2064:-16], bytes(2048))

    def test_out_of_range_and_unaligned_reads_stop_before_any_write(self):
        for dest,source,size in ((0x1000,0x406e0000,2048), (0x2000,0x406e0800,2048),
                (0x1000,0x406e0801,2048), (0x1000,0x406e0800,2047),
                (0x1000,0x406e0800,0), (0x1000,0x406e2000,4096)):
            with self.subTest(destination=dest, source=source, size=size):
                m,data = self.machine(dest,source,size); before = bytes(data)
                with self.assertRaises(Fault): LocalStorageRead(bytes(8192),0x1000,4096).apply(m)
                self.assertEqual(data,before)

    def test_wrong_call_contract_is_rejected(self):
        m,_ = self.machine(); read = LocalStorageRead(bytes(8192),0x1000,4096)
        for mask,frame in ((0,44),(0xf0,40)):
            with self.assertRaises(Fault): read.validate(m,mask,frame)


if __name__ == '__main__':
    unittest.main()
