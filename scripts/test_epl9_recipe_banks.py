"""Host reference tests with synthetic records, never film look validation."""
from dataclasses import replace
from pathlib import Path
import struct
import tempfile
import unittest
import zlib
from epl9_sd_recipes import Recipe, pack_recipe
from epl9_recipe_banks import (Bank, BankController, HEADER, MAX_BANK_BYTES,
                               CARD_PATH, pack_bank, unpack_bank, read_bank)


def recipe(i):
    return Recipe(i, f'Synthetic-{i}', ((0,0,0),)*12, 0, (0,0,0), (1024,1024), tuple(n*16 for n in range(256)))


def bank(i=1, count=31):
    return Bank(i, tuple(recipe(n+1) for n in range(count)))


class BankTests(unittest.TestCase):
    def test_31_record_roundtrip(self):
        original = bank()
        self.assertEqual(unpack_bank(pack_bank(original)), original)
        self.assertEqual(len(pack_bank(original)), MAX_BANK_BYTES)
        self.assertEqual(MAX_BANK_BYTES, 20484)

    def test_bounds_and_duplicate(self):
        for items in ((), tuple(recipe(i+1) for i in range(32)), (recipe(1), recipe(1))):
            with self.assertRaises(ValueError):
                Bank(1, items)
        with self.assertRaises(ValueError):
            Bank(True, (recipe(1),))

    def test_corruption_truncation_and_trailing_bytes(self):
        raw = pack_bank(bank())
        for value in (raw[:-1], raw+b'x', raw[:12], raw[:26]+b'X'+raw[27:]):
            with self.assertRaises(ValueError):
                unpack_bank(value)

    def test_outer_checksum_cannot_hide_bad_recipe(self):
        raw = bytearray(pack_bank(bank()))
        raw[HEADER.size + 100] ^= 1
        struct.pack_into('<I', raw, 20, 0)
        struct.pack_into('<I', raw, 20, zlib.crc32(raw))
        with self.assertRaises(ValueError):
            unpack_bank(bytes(raw))

    def test_wrong_count_or_version(self):
        for at, value in ((4, 2), (12, 32)):
            raw = bytearray(pack_bank(bank()))
            raw[at] = value
            struct.pack_into('<I', raw, 20, 0)
            struct.pack_into('<I', raw, 20, zlib.crc32(raw))
            with self.assertRaises(ValueError):
                unpack_bank(bytes(raw))


class DeleteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root/CARD_PATH
        self.path.parent.mkdir()
        self.builtin = bank(1, 2)
        self.custom = bank(2)
        self.path.write_bytes(pack_bank(self.custom))
        self.controller = BankController(self.builtin)

    def tap(self, context='idle-still'):
        value = self.controller.key('down', context)
        self.controller.key('up', context)
        return value

    def test_builtin_sd_builtin_cycle(self):
        c = self.controller
        self.tap()
        self.assertEqual(c.service(self.root, 'idle-still'), 'sd')
        self.assertEqual(c.view.bank, self.custom)
        self.tap()
        self.assertEqual(c.service(None, 'idle-still'), 'embedded')
        self.assertEqual(c.view.bank, self.builtin)
        self.assertEqual(c.view.generation, 2)

    def test_single_action_per_press_and_pending_coalesced(self):
        c = self.controller
        c.key('down', 'idle-still')
        c.service(self.root, 'idle-still')
        for phase in ('hold','down','down'):
            c.key(phase, 'idle-still')
        self.assertFalse(c.pending)
        c.key('up', 'idle-still')
        self.tap()
        self.tap()
        c.service(self.root, 'idle-still')
        self.assertEqual(c.view.source, 'embedded')

    def test_playback_and_review_never_request_switch(self):
        for context in ('playback','review','capture','movie','menu','unknown'):
            self.assertEqual(self.tap(context), 'stock')
            self.assertFalse(self.controller.pending)

    def test_press_owner_preserved_across_context_change(self):
        c = self.controller
        self.assertEqual(c.key('down','playback'), 'stock')
        self.assertEqual(c.key('hold','idle-still'), 'stock')
        self.assertEqual(c.key('up','idle-still'), 'stock')
        self.assertFalse(c.pending)
        c.key('down','idle-still')
        self.assertEqual(c.key('up','playback'), 'handled')

    def test_no_io_in_key_handler_or_while_capture_has_lease(self):
        c = self.controller
        token, snapshot = c.acquire()
        self.path.write_bytes(b'corrupt')
        self.tap()
        self.assertEqual(c.last_status, 'embedded')
        self.assertEqual(c.service(self.root,'idle-still'), 'waiting-for-idle')
        self.assertEqual(c.view, snapshot)
        c.release(token)
        self.assertEqual(c.service(self.root,'idle-still'), 'sd-rejected-kept-embedded')
        self.assertEqual(c.view, snapshot)
        with self.assertRaises(ValueError):
            c.release(token)

    def test_card_removal_keeps_loaded_snapshot_and_can_return(self):
        c = self.controller
        self.tap()
        c.service(self.root,'idle-still')
        old = c.view
        self.path.unlink()
        self.assertEqual(c.view, old)
        self.tap()
        c.service(None,'idle-still')
        self.assertEqual(c.view.bank,self.builtin)
        self.tap()
        self.assertEqual(c.service(self.root,'idle-still'), 'sd-missing-kept-embedded')

    def test_new_bank_after_return_reloads_and_increments_generation(self):
        c = self.controller
        self.tap()
        c.service(self.root,'idle-still')
        first = c.view
        self.tap()
        c.service(self.root,'idle-still')
        updated = Bank(2, (replace(recipe(1), contrast=1),))
        self.path.write_bytes(pack_bank(updated))
        self.tap()
        c.service(self.root,'idle-still')
        self.assertEqual(c.view.bank,updated)
        self.assertEqual(first.bank,self.custom)
        self.assertEqual(c.view.generation,3)

    def test_busy_context_waits_and_failed_bank_does_not_partially_publish(self):
        c = self.controller
        original = c.view
        self.tap()
        self.assertEqual(c.service(self.root,'capture'), 'waiting-for-idle')
        self.path.write_bytes(pack_bank(self.custom)[:-1])
        c.service(self.root,'idle-still')
        self.assertEqual(c.view, original)
        self.assertFalse(c.pending)


if __name__ == '__main__':
    unittest.main()
