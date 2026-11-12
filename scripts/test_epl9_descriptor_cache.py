import struct
import unittest
from dataclasses import replace
from epl9_descriptor_cache import DescriptorCache, CacheBusy
from epl9_recipe_banks import Bank
from epl9_sd_loader_probe import sample_recipe
from epl9_workspace_bridge import BASE
from epl9_bank_materializer import ROM

class CacheTests(unittest.TestCase):
    def setUp(self):
        self.cache=DescriptorCache(bytes(ROM-BASE)+bytes(n%256 for n in range(3028)))
        self.bank=Bank(1,tuple(replace(sample_recipe(),recipe_id=i+1,name=f'Synthetic {i}',contrast=i%5-2) for i in range(31)))

    def test_pins_backing_and_addresses_until_last_consumer(self):
        c=self.cache
        a=c.acquire(self.bank,1); b=c.acquire(self.bank,1)
        old=c.read(a)
        z=c.acquire(self.bank,2)
        with self.assertRaises(CacheBusy):c.acquire(self.bank,3)
        c.release(a)
        with self.assertRaises(CacheBusy):c.acquire(self.bank,3)
        self.assertEqual(c.read(b),old)
        self.assertEqual(struct.unpack_from('<I',old.data,12)[0],b.raw_address)
        c.release(b)
        new=c.acquire(self.bank,3)
        self.assertEqual(new.slot,a.slot)
        self.assertGreater(new.generation,a.generation)
        with self.assertRaises(ValueError):c.read(a)
        self.assertEqual(len(c.read(z).raw),660)

    def test_same_bank_id_changed_content_not_cache_hit(self):
        c=self.cache;a=c.acquire(self.bank,1)
        bank=replace(self.bank,recipes=(replace(self.bank.recipes[0],contrast=2),)+self.bank.recipes[1:])
        b=c.acquire(bank,1)
        self.assertNotEqual(a.slot,b.slot)
        self.assertNotEqual(c.read(a).data,c.read(b).data)

    def test_31_serial_recipes_need_only_two_slots(self):
        c=self.cache
        for i in range(1,32):
            h=c.acquire(self.bank,i)
            self.assertEqual(struct.unpack_from('<I',c.read(h).data,8)[0],i)
            c.release(h)
        self.assertEqual(len(c.slots),2)
        self.assertEqual(c.footprint()['total_resident_payload_bytes'],9512)

    def test_validation_does_not_replace_resident(self):
        c=self.cache;h=c.acquire(self.bank,1);old=c.read(h)
        for i in (0,32,True):
            with self.assertRaises(ValueError):c.acquire(self.bank,i)
        self.assertEqual(c.read(h),old)

    def test_double_release_rejected(self):
        c=self.cache;h=c.acquire(self.bank,1);c.release(h)
        with self.assertRaises(ValueError):c.release(h)

    def test_foreign_handle_rejected(self):
        c=self.cache;h=c.acquire(self.bank,1)
        other=DescriptorCache(c.image);foreign=other.acquire(self.bank,1)
        with self.assertRaises(ValueError):c.release(foreign)
        self.assertIsNotNone(c.read(h))

    def test_capacity(self):
        for n in (0,32,True):
            with self.assertRaises(ValueError):DescriptorCache(b'',n)

if __name__=='__main__':unittest.main()
