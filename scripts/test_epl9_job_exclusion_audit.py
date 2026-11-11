"""Source-only regression controls for the scoped native-reference inventory."""
import struct
import unittest
from unittest.mock import patch

import epl9_job_exclusion_audit as audit


class ReferenceInventoryTests(unittest.TestCase):
    def test_relative_calls_and_jumps_both_widths(self):
        base,target=0x1000,0x1040
        image=bytearray(80)
        expected=[]
        for at,opcode,width,trailer,op in ((0,0xcd,2,b'\xf0\x20','call'),
                (8,0xdd,4,b'\xf0\x20','call'),(20,0xcc,2,b'','jmp'),
                (30,0xdc,4,b'','jmp')):
            raw=bytes((opcode,))+(target-base-at).to_bytes(width,'little',signed=True)+trailer
            image[at:at+len(raw)]=raw
            expected.append(dict(pc=hex(base+at),op=op,raw=raw.hex()))
        self.assertEqual(audit.direct_candidates(image,base,target),expected)

    def test_negative_displacements_wrap_and_incomplete_bytes(self):
        # Unsigned address wrap is architectural; partial CALLs are not records.
        image=b'\xdd'+struct.pack('<i',-8)+b'\xf0\x20'+b'\xcd\x00\x00'
        self.assertEqual(audit.direct_candidates(image,4,0xfffffffc),
            [dict(pc='0x4',op='call',raw='ddf8fffffff020')])
        self.assertEqual(audit.direct_candidates(b'\xcd\x00\x00',0,0),[])
        self.assertEqual(audit.direct_candidates(b'\xdd\x00\x00\x00\x00',0,0),[])

    def test_relative_calls_fast_forms(self):
        image=b'\xfa\xff\x10\x00'+b'\xfc\xff\xfc\xff\xff\xff'
        self.assertEqual(audit.direct_candidates(image,0x1000,0x1010),
            [dict(pc='0x1000',op='calls',raw='faff1000')])
        self.assertEqual(audit.direct_candidates(image,0x1000,0x1000),
            [dict(pc='0x1004',op='calls',raw='fcfffcffffff')])
        self.assertEqual(audit.direct_candidates(b'\xfa\xff\x00',0,0),[])
        self.assertEqual(audit.direct_candidates(b'\xfc\xff\x00\x00\x00',0,0),[])

    def test_unrelated_targets_ignored(self):
        self.assertEqual(audit.direct_candidates(b'\xcd\x10\x00\xf0\x20',0x1000,0x1020),[])

    def test_literal_matches_include_overlap(self):
        self.assertEqual(audit.literal_positions(bytes(5),0x1000,0),['0x1000','0x1001'])
        self.assertEqual(audit.literal_positions(b'\x01\x02\x03',0x1000,0),[])

    def test_inventory_does_not_claim_closed_graph(self):
        rows=[dict(pc=hex(pc),op='call',raw='uninspected') for pc in audit.EXPECTED_CALLS]
        with patch.object(audit,'direct_candidates',return_value=rows), \
                patch.object(audit,'literal_positions',return_value=[]):
            r=audit.inventory(b'')
        self.assertFalse(r['complete_call_graph_proven'])
        self.assertFalse(r['computed_indirect_targets_excluded'])

    def test_inventory_rejects_missing_extra_jump_or_literal(self):
        rows=[dict(pc=hex(pc),op='call') for pc in audit.EXPECTED_CALLS]
        invalid=[rows[:-1],rows+[dict(pc='0x61030000',op='call')],
            [dict(r,op='jmp') if i==0 else r for i,r in enumerate(rows)]]
        for candidates in invalid:
            with self.subTest(candidates=candidates), \
                    patch.object(audit,'direct_candidates',return_value=candidates), \
                    patch.object(audit,'literal_positions',return_value=[]):
                with self.assertRaisesRegex(ValueError,'inventory differs'):
                    audit.inventory(b'')
        with patch.object(audit,'direct_candidates',return_value=rows), \
                patch.object(audit,'literal_positions',return_value=['0x60400020']):
            with self.assertRaisesRegex(ValueError,'literal inventory differs'):
                audit.inventory(b'')


if __name__=='__main__':
    unittest.main()
