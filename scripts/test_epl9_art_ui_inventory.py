import unittest
from epl9_art_ui_inventory import BASE,SIMPLE,inventory,records,reconcile


def fixture():
    keys=[0x801+i*256 for i in range(27)]+sorted(SIMPLE)
    labels=[(k,4,100+i,BASE) for i,k in enumerate(keys)]
    choices=[(k,200+i,k>>8,1,0) for i,k in enumerate(keys[:27])]
    variants=[(k,1,300+i,200+i,k>>8,0) for i,k in enumerate(keys[:27])]
    choices += [(k,400+i,k,0,0) for i,k in enumerate(keys[27:])]
    return labels,choices,variants


class TestInventory(unittest.TestCase):
    def test_partition(self):
        rows=reconcile(*fixture())
        self.assertEqual(len(rows),31)
        self.assertEqual(sum(r['variant']!=0 for r in rows),27)
        self.assertTrue(all(r['processing_key'] is None for r in rows))
    def test_duplicate_label(self):
        a,b,c=fixture();a[1]=a[0]
        with self.assertRaises(ValueError):reconcile(a,b,c)
    def test_reordered_choice(self):
        a,b,c=fixture();b[0],b[1]=b[1],b[0]
        with self.assertRaises(ValueError):reconcile(a,b,c)
    def test_variant_mismatch(self):
        a,b,c=fixture();c[0]=(c[0][0],2,*c[0][2:])
        with self.assertRaises(ValueError):reconcile(a,b,c)
    def test_wrong_image(self):
        with self.assertRaises(ValueError):inventory(b'not OEM')
    def test_truncated_or_unaligned(self):
        for start,end in [(BASE,BASE+8),(BASE-1,BASE),(BASE,BASE+3)]:
            with self.assertRaises(ValueError):records(b'1234',start,end,'<I')

if __name__=='__main__':unittest.main()
