"""Synthetic codec, independent fallback and immutable-session checks."""
from dataclasses import replace
from pathlib import Path
import struct
import tempfile
import unittest
import zlib

from epl9_sd_recipes import (ROOT, CARD_DIRECTORY, CRC_OFFSET, FILE_BYTES, HEADER,
                             Recipe, Slot, pack_recipe, unpack_recipe, load_session)


def recipe(ident=1, name='Synthetic'):
    return Recipe(ident,name,((0,0,0),)*12,0,(0,0,0),(1024,1024),tuple(n*16 for n in range(256)))


def reseal(data):
    struct.pack_into('<I',data,CRC_OFFSET,0)
    struct.pack_into('<I',data,CRC_OFFSET,zlib.crc32(data))
    return bytes(data)


class CodecTests(unittest.TestCase):
    def test_roundtrip_and_size(self):
        item=replace(recipe(),contrast=-2,tone=(-7,0,7),wb_q10=(512,2048))
        self.assertEqual(len(pack_recipe(item)),660)
        self.assertEqual(unpack_recipe(pack_recipe(item)),item)

    def test_every_single_byte_corruption_rejected(self):
        raw=pack_recipe(recipe())
        for n in range(len(raw)):
            with self.subTest(byte=n):
                changed=bytearray(raw)
                changed[n] ^= 1
                with self.assertRaises(ValueError):
                    unpack_recipe(bytes(changed))

    def test_truncation_and_extra_bytes(self):
        raw=pack_recipe(recipe())
        for n in (0,1,63,64,659):
            with self.assertRaises(ValueError):
                unpack_recipe(raw[:n])
        with self.assertRaises(ValueError):
            unpack_recipe(raw+b'\0')

    def test_resealed_incompatible_headers(self):
        for offset,size,value in ((4,2,1),(8,2,1420),(10,2,1100),(24,4,2),(28,4,1)):
            with self.subTest(offset=offset):
                data=bytearray(pack_recipe(recipe()))
                struct.pack_into('<H' if size==2 else '<I',data,offset,value)
                with self.assertRaises(ValueError):
                    unpack_recipe(reseal(data))

    def test_resealed_invalid_values_and_names(self):
        changes=((HEADER.size,struct.pack('<h',1001)),
                 (HEADER.size+72,struct.pack('<h',3)),
                 (HEADER.size+80,struct.pack('<H',0)),
                 (HEADER.size+84,struct.pack('<HH',100,0)),
                 (32,b'@'),(32,b'A'*32),(34,b'Z'))
        for offset,value in changes:
            with self.subTest(offset=offset,value=value):
                data=bytearray(pack_recipe(recipe(name='A')))
                data[offset:offset+len(value)]=value
                with self.assertRaises(ValueError):
                    unpack_recipe(reseal(data))

    def test_immutable_validated_values(self):
        for change in (dict(recipe_id=True),dict(name='@A076@'),dict(name='X'*32),
                       dict(gamma=tuple(range(255))),dict(contrast=True),dict(tone=(8,0,0)),
                       dict(hsl=tuple(((0,0,101),)*12))):
            with self.assertRaises(ValueError):
                replace(recipe(),**change)


class SlotTests(unittest.TestCase):
    def setUp(self):
        base=(ROOT/'local/test-temp').resolve()
        self.assertTrue(base.is_relative_to(ROOT.resolve()))
        base.mkdir(parents=True,exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(prefix='sd-recipes-',dir=base)
        self.root=Path(self.temp.name)
        self.assertTrue(self.root.resolve().is_relative_to(base))
        self.addCleanup(self.temp.cleanup)
        (self.root/CARD_DIRECTORY).mkdir()
        self.first,self.second=recipe(1,'Default 1'),recipe(2,'Default 2')
        self.custom=recipe(3,'Custom')
        self.slots=(Slot('fixed',self.first),Slot('custom1',self.first,1),Slot('custom2',self.second,2))

    def write(self,index,data):
        (self.root/CARD_DIRECTORY/f'SLOT{index:02}.RCP').write_bytes(data)

    def test_no_card_and_no_files_keep_all_defaults(self):
        for card in (None,self.root):
            snapshot=load_session(self.slots,card)
            self.assertEqual(tuple(x.recipe for x in snapshot),(self.first,self.first,self.second))
            self.assertEqual(tuple(x.source for x in snapshot),('embedded',)*3)

    def test_good_override_and_missing_neighbor(self):
        self.write(1,pack_recipe(self.custom))
        snapshot=load_session(self.slots,self.root)
        self.assertEqual(tuple(x.recipe for x in snapshot),(self.first,self.custom,self.second))
        self.assertEqual(tuple(x.status for x in snapshot),('built-in','loaded','missing'))

    def test_bad_neighbor_does_not_cancel_good_override(self):
        self.write(1,pack_recipe(self.custom))
        self.write(2,b'broken')
        snapshot=load_session(self.slots,self.root)
        self.assertEqual(snapshot[1].recipe,self.custom)
        self.assertEqual(snapshot[2].recipe,self.second)
        self.assertTrue(snapshot[2].status.startswith('rejected:'))

    def test_session_keeps_data_after_file_changes(self):
        self.write(1,pack_recipe(self.custom))
        old=load_session(self.slots,self.root)
        self.write(1,pack_recipe(self.second))
        self.assertEqual(old[1].recipe,self.custom)
        self.assertEqual(load_session(self.slots,self.root)[1].recipe,self.second)

    def test_file_can_move_to_another_reserved_slot(self):
        self.write(2,pack_recipe(self.custom))
        self.assertEqual(load_session(self.slots,self.root)[2].recipe,self.custom)

    def test_unassigned_file_never_overrides_builtin(self):
        self.write(3,pack_recipe(self.custom))
        self.assertEqual(load_session(self.slots,self.root)[0].recipe,self.first)

    def test_io_error_and_oversize_keep_defaults(self):
        (self.root/CARD_DIRECTORY/'SLOT01.RCP').mkdir()
        self.write(2,b'\0'*(FILE_BYTES+1))
        snapshot=load_session(self.slots,self.root)
        self.assertEqual(tuple(x.recipe for x in snapshot),(self.first,self.first,self.second))

    def test_duplicate_slot_bindings_rejected(self):
        for slots in ((self.slots[0],self.slots[0]),(self.slots[1],Slot('other',self.second,1)),
                      (Slot('invalid',self.first,0),),(Slot('invalid',self.first,True),)):
            with self.assertRaises(ValueError):
                load_session(slots,self.root)


if __name__ == '__main__':
    unittest.main()
