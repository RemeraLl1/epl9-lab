"""Native descriptor/WB checks on synthetic recipes and a synthetic ROM table."""
import struct
import unittest
from dataclasses import replace
from epl9_sd_loader_probe import sample_recipe, authored_code
from epl9_sd_state import build as state_build
from epl9_sd_recipes import pack_recipe
from epl9_sd_processing import build, descriptor, BASE_ADDRESS, RECORD, GAMMA
from epl9_sd_processing_probe import ProcessingFixture, ARENA, wb_case
from epl9_workspace_bridge import BASE
from epl9_wifi_prototype import span


class ProcessingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        image=bytearray(0x608ee360-BASE+3028)
        image[-3028:]=bytes(n%256 for n in range(3028))
        cls.image=bytes(image)
        cls.defaults=[pack_recipe(replace(sample_recipe(),recipe_id=101+i,wb_q10=wb))
                      for i,wb in enumerate(((512,2048),(2048,512)))]
        cls.state=state_build(cls.defaults);cls.state['code']=authored_code(cls.state)
        cls.module=build(cls.image,cls.state)
        m=cls.module
        m['code']={pc:(m['data'][pc-m['base']:pc-m['base']+n],op,
            [hex(m['symbols'][a]) if a in m['symbols'] else a for a in args]) for pc,op,args,n in m['rows']}

    def fixture(self):return ProcessingFixture(self.state,self.module,{},self.image,{},None)

    def test_embedded_descriptors_before_loader(self):
        f=self.fixture()
        for slot in (1,2):
            ptr=f.selected_descriptor(slot)
            self.assertEqual(ptr,BASE_ADDRESS+0x2000+(slot-1)*4096)
            self.assertEqual(bytes(span(f.memory,ptr+RECORD,660)),self.defaults[slot-1])
            self.assertEqual(f.memory.read(ptr+24,4),ptr+GAMMA)
        for slot in (0,3,29):self.assertEqual(f.selected_descriptor(slot),0)

    def test_native_materializer_matches_independent_host(self):
        for slot in (1,2):
            with self.subTest(slot=slot):
                f=self.fixture();f.invoke(self.module['symbols']['sd_materialize'],0xf0,24,a0=ARENA,d0=slot)
                raw=bytes(span(f.memory,ARENA,3764))
                want=descriptor(self.image,self.defaults[slot-1],ARENA,slot,self.state['constants'][f'FALLBACK{slot-1}'])
                self.assertEqual(raw[:28],want[:28]);self.assertEqual(raw[64:3092],want[64:3092])
                self.assertEqual(raw[RECORD:],want[RECORD:3764]);f.guards()

    def test_native_wb_bounds_and_live_registers(self):
        f=self.fixture()
        for slot in (1,2):
            for values in ((1,1,1,1),(65535,65535,65535,65535),(2048,1536,1024,1056),
                           (0,100,100,100),(100,100,100,0)):
                with self.subTest(slot=slot,values=values):wb_case(f,slot,values)

    def test_wb_ignores_unrelated_identity(self):
        f=self.fixture()
        wb_case(f,1,(1000,2000,3000,4000),valid_header=False)


if __name__=='__main__':unittest.main()
