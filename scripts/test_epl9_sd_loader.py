"""Synthetic native loader/validator tests, with named public API fixtures.

The independent GNU/stock-wrapper/backend qualification is the separate probe.
"""
from dataclasses import replace
import struct
import unittest
import zlib

from epl9_sd_loader import build
from epl9_sd_loader_probe import (LoaderFixture,authored_code,sample_recipe,CTX,
                                  SD_STATUS,SECTION_FLAGS,BUFFER,FALLBACK,STACK,STOP,MANAGER)
from epl9_sd_recipes import pack_recipe
from mn103_calls import CallMachine
from mn103_subset import Memory,Region


def reseal(data):
    data=bytearray(data)
    struct.pack_into('<I',data,16,0)
    struct.pack_into('<I',data,16,zlib.crc32(data))
    return bytes(data)


class NativeLoaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module=build();cls.module['code']=authored_code(cls.module)
        cls.raw=pack_recipe(sample_recipe())

    def fixture(self,data='valid',**options):
        return LoaderFixture(self.module,self.raw if data=='valid' else data,**options)

    def test_valid_then_no_repeat(self):
        f=self.fixture()
        result=f.run()
        self.assertEqual((result['state'],result['selected']),(3,'sd'))
        counts=dict(f.counts)
        f.run()
        self.assertEqual(dict(f.counts),counts)
        self.assertTrue(f.owned)
        self.assertFalse(f.file_open)

    def test_missing_file_keeps_embedded_and_releases(self):
        f=self.fixture(None)
        result=f.run()
        self.assertEqual((result['state'],result['selected'],result['error_code']),(2,'embedded',2))
        self.assertEqual(f.counts['free'],1)
        f.file_data=self.raw
        f.run()
        self.assertEqual(f.counts['open'],1)

    def test_defer_until_actual_sd_ready(self):
        f=self.fixture(sd_status=0)
        self.assertEqual(f.run()['state'],0)
        self.assertEqual(f.counts['alloc'],0)
        f.memory.write(SD_STATUS,0xf000,4)
        self.assertEqual(f.run()['state'],3)

    def test_gate_controls_never_allocate(self):
        options=(dict(sd_status=0x3000),dict(sd_status=0xf001),dict(sections=510),dict(cpu=1),
                 dict(task=None),dict(task=55),dict(manager_task=0),dict(manager_task=0xffff))
        for option in options:
            with self.subTest(option=option):
                f=self.fixture(**option)
                self.assertEqual(f.run()['state'],0)
                self.assertEqual(f.counts['alloc'],0)

    def test_gate_wrong_events(self):
        for event in (0,0x02000101,0x02040100,0x04030120):
            f=self.fixture()
            self.assertEqual(f.run(event)['state'],0)
            self.assertEqual(f.counts['open'],0)

    def test_short_extra_and_corrupt_files(self):
        for raw in (b'',self.raw[:-1],self.raw+b'x',self.raw[:-1]+bytes([self.raw[-1]^1])):
            f=self.fixture(raw)
            r=f.run()
            self.assertEqual((r['state'],r['selected']),(2,'embedded'))
            self.assertFalse(f.owned or f.file_open)
            self.assertEqual(f.counts['close'],1)

    def test_allocation_failure(self):
        f=self.fixture(fail_alloc=True)
        r=f.run()
        self.assertEqual((r['state'],r['error_code']),(2,1))
        self.assertEqual(f.counts['open'],0)

    def test_close_failure_retains_unpublished_block(self):
        f=self.fixture(close_error=True)
        r=f.run()
        self.assertEqual((r['state'],r['selected']),(4,'embedded'))
        self.assertTrue(f.owned and f.file_open)
        self.assertEqual(f.counts['free'],0)
        counts=dict(f.counts)
        f.run()
        self.assertEqual(counts,dict(f.counts))

    def test_pending_read_does_not_fabricate_cleanup(self):
        f=self.fixture(stall_read=True)
        r=f.run()
        self.assertEqual(r['result']['status'],'fault')
        self.assertEqual((r['state'],r['selected']),(1,'embedded'))
        self.assertTrue(f.owned and f.file_open)
        self.assertEqual(f.counts['close'],0)
        self.assertEqual(f.counts['free'],0)

    def test_event_adapter_preserves_get_result_and_caller(self):
        f=self.fixture()
        r=f.event_adapter()
        top=STACK+32768
        self.assertEqual(r['state'],3)
        self.assertEqual(r['event_word'],0x02000100)
        self.assertEqual(r['registers'],dict(sp=top,d0=0,d1=0x11111111,d2=0x22222222,d3=top+4,
            a0=MANAGER,a1=top+4,a2=0x44444444,a3=MANAGER))
        self.assertEqual(f.counts['event_get'],1)

    def test_event_adapter_bypass_controls(self):
        for options in (dict(null_output=True),dict(unbound=True)):
            f=self.fixture()
            r=f.event_adapter(**options)
            self.assertEqual(r['state'],0)
            self.assertEqual(f.counts['alloc'],0)

    def validate(self,raw):
        # No host validator or firmware services exist in this execution.
        m=CallMachine(self.module['code'],Memory([
            Region(self.module['base'],bytearray(self.module['data']),False,'native code'),
            Region(BUFFER,bytearray(raw),False,'input'),
            Region(STACK,bytearray(65536),True,'stack')]),dict(a0=BUFFER,sp=STACK+32768))
        result=m.run(m.enter(self.module['symbols']['sd_validate'],STOP,0xf0,24),[STOP],limit=200000)
        self.assertEqual(result.get('pc'),STOP)
        self.assertEqual(m.r['sp'],STACK+32768)
        return m.r['d0']

    def test_native_crc_with_distinct_valid_records(self):
        base=sample_recipe()
        for recipe in (base,replace(base,name='A'*31,hsl=((-1000,-240,-100),(1000,240,100))*6,
                                    contrast=-2,tone=(-7,7,0),wb_q10=(512,2048)),
                       replace(base,recipe_id=0xffffffff,gamma=tuple((n*n*4095)//(255*255) for n in range(256)))):
            self.assertEqual(self.validate(pack_recipe(recipe)),0)

    def test_native_resealed_invalid_fields(self):
        for offset,fmt,value in ((4,'H',1),(8,'H',1420),(20,'I',0),(28,'I',1),(32,'B',64),
                                 (64,'h',1001),(66,'h',241),(68,'h',101),(136,'h',3),
                                 (138,'h',8),(144,'H',511),(146,'H',2049),(148,'H',4096),
                                 (150,'H',0)):
            with self.subTest(offset=offset,value=value):
                data=bytearray(self.raw)
                # Force the final gamma test to fold down from a positive first value.
                if offset==150: struct.pack_into('<H',data,148,16)
                struct.pack_into('<'+fmt,data,offset,value)
                self.assertEqual(self.validate(reseal(data)),1)

    def test_native_crc_rejects_payload_or_checksum_corruption(self):
        for offset in (16,40,64,148,659):
            data=bytearray(self.raw);data[offset]^=1
            self.assertEqual(self.validate(bytes(data)),1)


if __name__=='__main__': unittest.main()
