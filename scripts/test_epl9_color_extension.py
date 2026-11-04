import unittest
from copy import deepcopy
from epl9_color_extension import controls, matrix_result, KEYS
from epl9_deployment_probe import Registers


def fixture():
    return dict(schema='epl9-native-color-controls-v1',recipes=[
        dict(watercolor_key=k,matrix_delta=[-2,2,0,0,1,-1,1,0,-1],six_axis=list(range(12))) for k in KEYS])


class ExtendedColorTests(unittest.TestCase):
    def test_matrix_overlay_preserves_neutral_row_sum_and_native_variation(self):
        row=controls(fixture())[KEYS[0]]
        source=(124,10,-6,8,124,-4,-2,6,124)
        actual=matrix_result(source,row['matrix_delta'])
        self.assertEqual([sum(actual[n:n+3]) for n in (0,3,6)],[128]*3)
        self.assertNotEqual(actual,source)
        self.assertEqual(matrix_result([32767]*9,row['matrix_delta']),(32767,)*9)

    def test_unknown_slots_fields_nonzero_sums_and_bad_width_rejected(self):
        for field,value in (('watercolor_key','0x01030078'),('matrix_delta',[1]*9),
                            ('matrix_delta',[-17,17,0]*3),('six_axis',[0]*11),
                            ('six_axis',[32768]*12),('six_axis',[False]*12),('wb',[1,1])):
            doc=deepcopy(fixture());doc['recipes'][0][field]=value
            with self.assertRaises(ValueError):controls(doc)

    def test_null_overrides_are_explicit_and_input_copied(self):
        doc=fixture();doc['recipes'][0].update(matrix_delta=None,six_axis=None)
        rows=controls(doc)
        self.assertIsNone(rows[KEYS[0]]['six_axis'])
        doc['recipes'][1]['six_axis'][0]=99
        self.assertEqual(rows[KEYS[1]]['six_axis'][0],0)

    def test_stack_meter_tracks_assignment_and_update_including_restoration(self):
        regs=Registers(dict(sp=4096))
        regs['sp']=4000;regs.update(sp=3500);regs.update({'sp':4096})
        self.assertEqual(regs.minimum_sp,3500)
