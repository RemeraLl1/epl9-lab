import unittest
from copy import deepcopy
from epl9_wb_extension import controls, adjusted


def fixture():
    return dict(schema='epl9-native-wb-controls-v1',recipes=[
        dict(watercolor_key=k,gain_q10=[1106,901]) for k in ('0x01010078','0x01020078')])


class WBTests(unittest.TestCase):
    def test_gain_bounds_unknown_keys_duplicate_keys_and_boolean_rejected(self):
        for field,value in (('gain_q10',[511,1024]),('gain_q10',[1024,2049]),
                            ('gain_q10',[True,1024]),('gain_q10',[1024]),
                            ('watercolor_key','0x01030078'),('unknown',1)):
            doc=deepcopy(fixture());doc['recipes'][0][field]=value
            with self.assertRaises(ValueError):controls(doc)
        doc=fixture();doc['recipes'][1]['watercolor_key']=doc['recipes'][0]['watercolor_key']
        with self.assertRaises(ValueError):controls(doc)

    def test_zero_input_is_untouched_and_upper_limit_saturates(self):
        self.assertEqual(adjusted((2048,1536,0,1024),(1106,901)),(2048,1536,0,1024))
        self.assertEqual(adjusted((65535,65535,1024,1024),(2048,512)),(65535,32768,1024,1024))
        self.assertEqual(adjusted((1,1,1,1),(512,512)),(1,1,1,1))
