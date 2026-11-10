import unittest
from epl9_component_readback import compare, difference, package_files


class ComponentReadbackTests(unittest.TestCase):
    def setUp(self):
        self.refs = {'v3': {'main': b'new main', 'osd': b'new osd'},
                     'stock': {'main': b'old main', 'osd': b'old osd'}}

    def samples(self, main='v3', osd='v3'):
        return {k: (self.refs[v][k],)*2 for k, v in [('main', main), ('osd', osd)]}

    def test_exact_both_targets_without_physical_claim(self):
        for target in self.refs:
            r = compare(self.samples(target, target), self.refs, target)
            self.assertTrue(r['both_component_bytes_match'])
            self.assertFalse(r['physical_write_verified'])

    def test_each_partial_install_and_restore_rejected(self):
        for target in self.refs:
            for main, osd in [('stock', 'v3'), ('v3', 'stock')]:
                r = compare(self.samples(main, osd), self.refs, target)
                self.assertFalse(r['both_component_bytes_match'])
                self.assertEqual(sum(x['target_matches'] for x in r['components']), 1)

    def test_second_read_corruption_rejected(self):
        s = self.samples()
        s['main'] = (s['main'][0], b'bad main')
        r = compare(s, self.refs, 'v3')
        self.assertFalse(r['both_component_bytes_match'])
        self.assertFalse(r['components'][0]['stable'])

    def test_missing_component_and_missing_repeat_rejected(self):
        with self.assertRaises(ValueError):
            compare({'main': (b'a', b'a')}, self.refs, 'stock')
        s = self.samples()
        s['main'] = s['main'][:1]
        with self.assertRaises(ValueError):
            compare(s, self.refs, 'v3')

    def test_truncated_and_swapped_rejected(self):
        for replacement in (b'new mai', b'new osd'):
            s = self.samples()
            s['main'] = (replacement,)*2
            self.assertFalse(compare(s, self.refs, 'v3')['both_component_bytes_match'])

    def test_difference_including_envelope_edges(self):
        self.assertEqual(difference(b'XbcY', b'abcd'), dict(size_matches=True,
            differing_bytes=2, first_difference='0x0', last_difference='0x3'))

    def test_generation_pins_do_not_accept_another_main_as_same_build(self):
        old,new=package_files('frozen-v3'),package_files('private-color-v3')
        self.assertNotEqual(old['v3'],new['v3'])
        self.assertEqual(old['stock'],new['stock'])
        with self.assertRaises(ValueError):package_files('unknown')


if __name__ == '__main__':
    unittest.main()
