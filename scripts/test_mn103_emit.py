import unittest
from mn103_emit import assemble, encode


class EmitTests(unittest.TestCase):
    def test_known_native_encodings_and_relative_targets(self):
        vectors = [
            ('mov',['a0','a3'],'93'),
            ('mov',['d2','d0'],'88'),
            ('mov',['a0','d0'],'f1d0'),
            ('mov',['d1','a2'],'f1e6'),
            ('mov',['(4,sp)','a0'],'5c04'),
            ('movbu',['d0','(61,sp)'],'f8923d'),
            ('movbu',['d0','(1795,a2)'],'fa520307'),
            ('movhu',['(1832,a2)','d0'],'fa622807'),
            ('inc4',['a3'],'53'),
            ('add',['-88','sp'],'f8fea8'),
            ('add',['-356','sp'],'fafe9cfe'),
            ('add',['-2048','sp'],'fafe00f8'),
            ('add',['2048','sp'],'fafe0008'),
            ('add',['64','a1'],'2140'),
            ('add',['d1','d1'],'e5'),
            ('add',['d0','d1'],'e1'),
            ('lsr',['7','d1'],'f8c507'),
            ('clr',['d2'],'08'),
            ('or',['0x10000002','d0'],'fce402000010'),
            ('cmp',['a3','a0'],'bc'),
            ('call',['0x6079d328','[d2,d3,a2,a3]','28'],'dd34fbfffff01c'),
            ('ret',['[d2,d3,a2,a3]','28'],'dff01c'),
        ]
        for op,args,expected in vectors:
            self.assertEqual(encode(op,args,0x6079d7f4,{}).hex(),expected)

    def test_labels_forward_backward_and_alignment_by_instruction_length(self):
        data,symbols,_ = assemble('start:\n beq end\n nop\nend:\n bra start\n',0x2000)
        self.assertEqual(data.hex(),'c803cbcafd')
        self.assertEqual(symbols,{'start':0x2000,'end':0x2003})

    def test_branch_overflow_undefined_and_duplicate_labels_are_rejected(self):
        for source in ('beq end\n'+'nop\n'*128+'end:\n', 'jmp missing', 'x:\nx:\n'):
            with self.assertRaises(ValueError):
                assemble(source,0x2000)

    def test_unsupported_forms_masks_and_widths_are_rejected(self):
        for op,args in [('mystery',[]),('ret',['[d0]','0']),('add',['128','d0']),
                        ('mov',['(256,sp)','d0']),('udfu01',['256','d0']),
                        ('mov',['d0','d0']),('mov',['a1','a1']),('mov',['(a0)','(a1)']),
                        ('add',['32768','sp']),('add',['-32769','sp'])]:
            with self.assertRaises(ValueError):
                encode(op,args,0x2000,{})


if __name__ == '__main__':
    unittest.main()
