"""Source-only adversarial corpus and native fixed-buffer boundaries."""
import unittest

from epl9_sd_loader import build
from epl9_sd_loader_probe import authored_code, sample_recipe
from epl9_sd_recipes import FILE_BYTES, pack_recipe
from epl9_sd_validator_probe import corpus, host_accepts, native_accepts, relocated_state
from epl9_sd_placement import STATE_BASE


class ValidatorTests(unittest.TestCase):
    def test_every_corruption_and_each_curve_index_is_present(self):
        cases = list(corpus())
        names = [name for name, _, _ in cases]
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual({n for n in names if n.startswith('invalid/crc/')},
                         {f'invalid/crc/{n}' for n in range(FILE_BYTES)})
        self.assertEqual({n for n in names if n.startswith('invalid/gamma-range/')},
                         {f'invalid/gamma-range/{n}' for n in range(256)})
        self.assertTrue(all(host_accepts(raw) == expected for _, raw, expected in cases))

    def test_corpus_is_deterministic_without_changing_global_random(self):
        import random
        before = random.getstate()
        self.assertEqual(list(corpus()), list(corpus()))
        self.assertEqual(random.getstate(), before)

    def test_native_entry_requires_fixed_sized_input(self):
        module = build()
        module['code'] = authored_code(module)
        raw = pack_recipe(sample_recipe())
        self.assertTrue(native_accepts(module, raw)[0])
        for changed in (raw[:-1], raw+b'\0', bytearray(raw)):
            with self.assertRaises(ValueError):
                native_accepts(module, changed)

    def test_placed_state_uses_same_relocated_validator_and_fallbacks(self):
        raw = pack_recipe(sample_recipe())
        module = relocated_state([raw]*2)
        self.assertEqual(module['base'], STATE_BASE)
        self.assertTrue(all(STATE_BASE <= pc < STATE_BASE+4096 for pc in module['symbols'].values()))
        for i in range(2):
            offset = module['constants'][f'FALLBACK{i}']-STATE_BASE
            self.assertEqual(module['data'][offset:offset+FILE_BYTES], raw)
        module['code'] = {pc: (module['data'][pc-STATE_BASE:pc-STATE_BASE+n], op,
            [hex(module['symbols'][a]) if a in module['symbols'] else a for a in args])
            for pc, op, args, n in module['rows']}
        self.assertTrue(native_accepts(module, raw)[0])
        self.assertFalse(native_accepts(module, bytes(FILE_BYTES))[0])


if __name__ == '__main__':
    unittest.main()
