"""Synthetic image controls for separate SD-module relocation boundaries."""
import struct
import unittest
from epl9_workspace_bridge import BASE
from epl9_sd_placement import build, check_spans, SPANS, V3_SPAN, STATE_BASE, CONSUMER_BASE
from epl9_sd_state import build as synthetic_state
from epl9_sd_processing import build as synthetic_consumer
from epl9_sd_loader_probe import sample_recipe
from epl9_sd_recipes import pack_recipe


class PlacementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        image=bytearray(0x60ae1c73-BASE)
        for at,n in SPANS:image[at-BASE:at-BASE+n]=b'\xff'*n
        for pc,raw in ((0x60ae1a6f,'2cb400'),(0x60ae1a8a,'cdf5fdf020'),(0x60ae1c6e,'cd05042008'),
            (0x6079fb88,'f1d3f1ef53'),(0x6074f352,'0008257e0e'),(0x60752202,'881cf9140c')):
            image[pc-BASE:pc-BASE+len(bytes.fromhex(raw))]=bytes.fromhex(raw)
        cls.image=bytes(image);cls.defaults=[pack_recipe(sample_recipe())]*2

    def test_relocation_and_declared_changes(self):
        state,consumer,changed,reference,patches=build(self.image,self.defaults)
        self.assertEqual((state['base'],consumer['base']),(STATE_BASE,CONSUMER_BASE))
        self.assertEqual(len(patches),6)
        expected=bytearray(reference)
        for p in patches:
            at=p['address']-BASE;raw=bytes.fromhex(p['after']);expected[at:at+len(raw)]=raw
        self.assertEqual(changed,bytes(expected))
        self.assertEqual(changed[V3_SPAN[0]-BASE:V3_SPAN[1]-BASE],self.image[V3_SPAN[0]-BASE:V3_SPAN[1]-BASE])

    def test_descriptor_pointers_relocated(self):
        state,c,_,_,_=build(self.image,self.defaults)
        for i in range(2):
            at=0x2000+i*4096;desc=c['base']+at
            values=struct.unpack_from('<7I',c['data'],at)
            self.assertEqual(values[2:],(i+1,state['constants'][f'FALLBACK{i}'],desc+64,desc+3104,desc+3252))
        self.assertTrue(all(STATE_BASE<=pc<STATE_BASE+4096 for pc in state['symbols'].values()))
        self.assertTrue(all(CONSUMER_BASE<=pc<CONSUMER_BASE+8192 for pc in c['symbols'].values()))

    def test_original_builders_remain_synthetic(self):
        s=synthetic_state(self.defaults);c=synthetic_consumer(self.image,s)
        before=(s['data'],c['data'])
        build(self.image,self.defaults)
        self.assertEqual((s['base'],c['base']),(0x69000000,0x6a000000))
        self.assertEqual((s['data'],c['data']),before)

    def test_reject_nonpadding_and_unsafe_spans(self):
        image=bytearray(self.image);image[STATE_BASE-BASE]=0
        with self.assertRaises(ValueError):check_spans(bytes(image))
        for spans in (((STATE_BASE+1,6144),),((0x604a1300,6144),),
                      ((STATE_BASE,6144),(STATE_BASE+256,6144)),((0x604b0000,6144),)):
            with self.subTest(spans=spans):
                with self.assertRaises(ValueError):check_spans(self.image,spans)


if __name__=='__main__':unittest.main()
