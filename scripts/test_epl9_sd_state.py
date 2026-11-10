"""Synthetic native checks for the separate manager tail and test-slot ABI."""
import hashlib
import unittest

from epl9_sd_loader import build as standalone
from epl9_sd_loader_probe import authored_code, sample_recipe
from epl9_sd_recipes import pack_recipe
from epl9_sd_state import build, overlay, ROOT_ADDRESS, CONTEXTS, MAGIC
from epl9_sd_state_probe import StateFixture, MANAGER
from epl9_workspace_bridge import BASE
from epl9_wifi_prototype import span


class StateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module=build([pack_recipe(sample_recipe())]*2)
        cls.module['code']=authored_code(cls.module)

    def fixture(self,initialize=True):
        f=StateFixture(self.module,{})
        if initialize:
            f.invoke(self.module['symbols']['sd_init_tail'],0xf0,24,a0=MANAGER)
            f.locked=True;f.memory.write(ROOT_ADDRESS,MANAGER,4);f.locked=False
        return f

    def test_standalone_generation_unchanged(self):
        raw=standalone()['data']
        self.assertEqual(len(raw),1322)
        self.assertEqual(hashlib.sha256(raw).hexdigest(),'ed4d4e9055d00393ad1eea267bd265abf4261c3a12fd1980cac7ad216f15d357')

    def test_init_preserves_original_prefix_and_guards(self):
        f=self.fixture()
        self.assertEqual(bytes(span(f.memory,MANAGER,180)),b'\xcd'*180)
        self.assertEqual(f.memory.read(MANAGER+192,4),MAGIC)
        self.assertEqual(f.memory.read(MANAGER+196,4),0x10002)
        self.assertEqual(f.memory.read(MANAGER+200,4),MANAGER)
        self.assertEqual(f.memory.read(MANAGER+204,4),288)
        self.assertEqual(f.states(),[0,0]);f.guards()

    def test_fallback_before_construction_and_unknown_slots(self):
        f=self.fixture(False)
        self.assertEqual(f.selected(1),self.module['constants']['FALLBACK0'])
        self.assertEqual(f.selected(2),self.module['constants']['FALLBACK1'])
        for slot in (0,3,29,0xffffffff):self.assertEqual(f.selected(slot),0)

    def test_invalid_registry_uses_fallback(self):
        for offset,value in ((192,0),(196,1),(200,MANAGER+4),(204,180)):
            with self.subTest(offset=offset):
                f=self.fixture();f.memory.write(MANAGER+offset,value,4)
                self.assertEqual(f.selected(1),self.module['constants']['FALLBACK0'])
                self.assertEqual(f.selected(2),self.module['constants']['FALLBACK1'])

    def test_slots_are_independent(self):
        f=self.fixture();ptr=MANAGER+0x840
        for i,context in enumerate(CONTEXTS):
            f.memory.write(MANAGER+context,3,4)
            f.memory.write(MANAGER+context+4,ptr+i*0x840,4)
            f.memory.write(MANAGER+context+12,ptr+i*0x840,4)
        self.assertEqual(f.selected(1),ptr)
        self.assertEqual(f.selected(2),ptr+0x840)
        f.memory.write(MANAGER+CONTEXTS[0],2,4)
        self.assertEqual(f.selected(1),self.module['constants']['FALLBACK0'])
        self.assertEqual(f.selected(2),ptr+0x840)

    def test_unpublished_states_keep_fallback(self):
        for state in (0,1,2,4,0xffffffff):
            with self.subTest(state=state):
                f=self.fixture();f.memory.write(MANAGER+216,state,4)
                f.memory.write(MANAGER+220,MANAGER+0x840,4)
                f.memory.write(MANAGER+228,MANAGER+0x840,4)
                self.assertEqual(f.selected(1),self.module['constants']['FALLBACK0'])

    def test_selected_pointer_checks(self):
        for selected,owned in ((0,0),(0x62266ffc,0x62266ffc),(0x6237f800,0x6237f800),
                               (MANAGER+0x842,MANAGER+0x842),(MANAGER+0x840,MANAGER+0x1080)):
            with self.subTest(selected=selected,owned=owned):
                f=self.fixture();f.memory.write(MANAGER+216,3,4)
                f.memory.write(MANAGER+220,selected,4);f.memory.write(MANAGER+228,owned,4)
                self.assertEqual(f.selected(1),self.module['constants']['FALLBACK0'])

    def test_overlay_requires_exact_stock_bytes(self):
        image=bytearray(0x60ae1c73-BASE)
        for pc,raw in ((0x60ae1a6f,'2cb400'),(0x60ae1a8a,'cdf5fdf020'),(0x60ae1c6e,'cd05042008')):
            image[pc-BASE:pc-BASE+len(bytes.fromhex(raw))]=bytes.fromhex(raw)
        patched,rows=overlay(bytes(image),self.module)
        self.assertEqual(len(patched),len(image));self.assertEqual(len(rows),3)
        image[0x60ae1a6f-BASE]^=1
        with self.assertRaises(ValueError):overlay(bytes(image),self.module)


if __name__=='__main__':unittest.main()
