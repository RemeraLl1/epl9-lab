"""Synthetic controls for the relative-transfer search; no firmware required."""
import struct
import unittest

from epl9_ok_entry_audit import BASE, cstring, transfers


class TransferSearchGuards(unittest.TestCase):
    def test_calls_and_jumps_forward(self):
        data = bytearray(256); target = BASE+200
        sites = [(8, b'\xcd', 2), (24, b'\xdd', 4),
                 (40, b'\xcc', 2), (56, b'\xdc', 4),
                 (72, b'\xfa\xff', 2), (88, b'\xfc\xff', 4)]
        for offset, opcode, width in sites:
            delta = target-(BASE+offset)
            raw = opcode+delta.to_bytes(width, 'little', signed=True)
            data[offset:offset+len(raw)] = raw
        hits = {(int(r['site'], 16), r['encoding']) for r in transfers(data, {target})}
        self.assertTrue({(BASE+offset, kind) for (offset, _, _), kind in zip(
            sites, ('call16','call32','jmp16','jmp32','calls','calls'))} <= hits)

    def test_backward_signed_transfer(self):
        data = bytearray(128); offset, target = 80, BASE+12
        data[offset:offset+7] = b'\xdd'+struct.pack('<i', target-(BASE+offset))+b'\x00\x04'
        self.assertIn(dict(site=hex(BASE+offset), target=hex(target), encoding='call32'),
                      transfers(data, {target}))

    def test_conditional_branch_and_nop(self):
        data = bytearray(80); target = BASE+40
        data[8:10] = bytes((0xc8, 32))
        data[24] = 0xcb
        self.assertIn(dict(site=hex(BASE+8), target=hex(target), encoding='branch8'),
                      transfers(data, {target}))
        self.assertFalse(any(r['site'] == hex(BASE+24) for r in transfers(data, {target})))

    def test_truncated_encodings_are_not_read_past_end(self):
        for data in (b'\xcd', b'\xdd\x01\x02', b'\xfa\xff\x01', b'\xfc\xff\x01\x02'):
            with self.subTest(raw=data.hex()):
                self.assertEqual(transfers(data, {BASE+1}), [])

    def test_unterminated_and_outside_strings_are_rejected(self):
        self.assertEqual(cstring(b'OK\0', BASE), 'OK')
        for data, address in ((b'OK', BASE), (b'OK\0', BASE-1), (b'OK\0', BASE+3)):
            with self.subTest(address=hex(address), data=data):
                with self.assertRaises(ValueError):
                    cstring(data, address)


if __name__ == '__main__':
    unittest.main()
