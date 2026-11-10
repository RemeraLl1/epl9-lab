"""Host contract boundaries, including actual frozen full-size local controls."""
from dataclasses import replace
import unittest
from epl9_workspace_bridge import ROOT
from epl9_component_readback import references, ADDRESSES
from epl9_page_collection import Collection, PageResult, PAGE, COUNT, mapped_pages


def first():
    return PageResult(7, 'main', 0, 0, 3520, 0, 2, bytes(PAGE))


class PageCollectionTests(unittest.TestCase):
    def test_all_component_pages_and_relocation(self):
        table = list(range(1024))
        for kind, address in ADDRESSES.items():
            base = (address-0x40000000)//PAGE
            self.assertEqual(mapped_pages(table, kind), tuple(range(base, base+COUNT)))
        table[55], table[900], table[901] = 900, 901, 902
        self.assertEqual(mapped_pages(table, 'main')[:64], tuple(range(902*64, 903*64)))

    def test_cycles_and_invalid_indices(self):
        for value in (1024, -1, 0xffffffff):
            table = list(range(1024)); table[55] = value
            with self.assertRaises(ValueError):
                Collection(7, table)
        table = list(range(1024)); table[55], table[56] = 56, 55
        with self.assertRaises(ValueError):
            Collection(7, table)

    def test_bad_records_fail_entire_collection(self):
        for change in (dict(session=8), dict(component='picture'), dict(pass_index=2),
                       dict(ordinal=1), dict(physical_page=3521), dict(result=5),
                       dict(reader_state=3), dict(data=bytes(PAGE-1))):
            with self.subTest(change=change):
                c = Collection(7, range(1024))
                with self.assertRaises(ValueError): c.accept(replace(first(), **change))
                with self.assertRaises(ValueError): c.accept(first())

    def test_duplicate_and_partial_stream_refused(self):
        c = Collection(7, range(1024)); c.accept(first())
        with self.assertRaises(ValueError): c.accept(first())
        with self.assertRaises(ValueError): Collection(7, range(1024)).finish({}, 'v3')

    def test_both_full_components_twice_for_candidate_and_restore(self):
        refs = references(ROOT/'local/epl9-v3-private-packages-20261107', 'private-color-v3')
        for target in ('v3', 'stock'):
            c = Collection(7, range(1024))
            for kind in ADDRESSES:
                for run in (0, 1):
                    for page in range(COUNT):
                        c.accept(PageResult(7, kind, run, page, c.maps[kind][page], 0, 2,
                                            refs[target][kind][page*PAGE:(page+1)*PAGE]))
            result = c.finish(refs, target)
            self.assertTrue(result['both_component_bytes_match'])
            self.assertFalse(result['acquisition_provenance_verified'])
            self.assertFalse(result['physical_write_verified'])
            self.assertFalse(result['input_transport_qualified'])
            if target == 'v3':
                c.buffers[('main', 1)][100] ^= 1
                self.assertFalse(c.finish(refs, target)['both_component_bytes_match'])


if __name__ == '__main__':
    unittest.main()
