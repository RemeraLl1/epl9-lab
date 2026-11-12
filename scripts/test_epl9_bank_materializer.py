import struct
import unittest
from dataclasses import replace
from epl9_recipe_banks import Bank
from epl9_sd_loader_probe import sample_recipe
from epl9_sd_processing import descriptor, STRIDE, RECORD, GAMMA
from epl9_bank_materializer import materialize_snapshot, footprint, ARENA, RAW, ROM, build
from epl9_workspace_bridge import BASE


class BankMaterializerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rom = bytes(n%256 for n in range(3028))
        cls.image = bytes(ROM-BASE)+cls.rom

    def test_31_native_descriptors_equal_host_oracle(self):
        records = tuple(replace(sample_recipe(), recipe_id=100+i, name=f'Synthetic {i}',
                        contrast=(i%5)-2, tone=(i%15-7,0,7-i%15),
                        hsl=((i*10-150, i-15,15-i),)*12,
                        wb_q10=(512+i*32,2048-i*32)) for i in range(31))
        bank=Bank(7,records)
        arena=materialize_snapshot(bank,self.rom)
        for i,record in enumerate(records):
            from epl9_sd_recipes import pack_recipe
            want=descriptor(self.image,pack_recipe(record),ARENA+i*STRIDE,i+1,RAW+i*660)
            self.assertEqual(arena[i*STRIDE:(i+1)*STRIDE],want)
            self.assertEqual(struct.unpack_from('<I',arena,i*STRIDE+24)[0],ARENA+i*STRIDE+GAMMA)

    def test_delete_switch_materializes_only_after_old_capture_drains(self):
        import tempfile
        from pathlib import Path
        from epl9_recipe_banks import BankController, CARD_PATH, pack_bank
        embedded=Bank(1,(sample_recipe(),))
        custom=Bank(2,(replace(sample_recipe(),name='Synthetic SD',contrast=2),))
        c=BankController(embedded)
        token,old=c.acquire()
        old_arena=materialize_snapshot(old.bank,self.rom)
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/CARD_PATH).parent.mkdir()
            (root/CARD_PATH).write_bytes(pack_bank(custom))
            c.key('down','idle-still');c.key('up','idle-still')
            self.assertEqual(c.service(root,'idle-still'),'waiting-for-idle')
            self.assertEqual(materialize_snapshot(c.view.bank,self.rom),old_arena)
            c.release(token)
            self.assertEqual(c.service(root,'idle-still'),'sd')
            new_arena=materialize_snapshot(c.view.bank,self.rom)
            self.assertNotEqual(new_arena,old_arena)
            self.assertEqual(materialize_snapshot(old.bank,self.rom),old_arena)
            c.key('down','idle-still');c.key('up','idle-still')
            self.assertEqual(c.service(None,'idle-still'),'embedded')
            self.assertEqual(materialize_snapshot(c.view.bank,self.rom),old_arena)

    def test_single_record(self):
        self.assertEqual(len(materialize_snapshot(Bank(1,(sample_recipe(),)),self.rom)),4096)

    def test_template_required(self):
        for value in (b'',bytes(3027),bytes(3029),bytearray(3028)):
            with self.assertRaises(ValueError): materialize_snapshot(Bank(1,(sample_recipe(),)),value)

    def test_immutable_bank_validation_not_bypassed(self):
        with self.assertRaises(ValueError): materialize_snapshot(None,self.rom)

    def test_memory_cost_is_not_serialized_size(self):
        self.assertEqual(footprint(31)['expanded_descriptors_bytes'],126976)
        self.assertEqual(footprint(31)['both_retained_bytes'],147460)
        for count in (0,32,True):
            with self.assertRaises(ValueError): footprint(count)

    def test_module_has_no_loader_or_camera_patch(self):
        module=build()
        self.assertNotIn('call ',module['source'])
        self.assertNotIn('sd_slot_get',module['source'])
        self.assertLess(len(module['data']),4096)

if __name__=='__main__': unittest.main()
