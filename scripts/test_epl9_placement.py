import unittest
from epl9_placement import check_slot,module_regions,with_module_data,CANDIDATE,MODULE_SIZE
from epl9_workspace_bridge import BASE


class PlacementTests(unittest.TestCase):
    def test_only_complete_reviewed_ff_slot_is_allowed(self):
        image=bytearray(CANDIDATE-BASE+MODULE_SIZE+4)
        image[CANDIDATE-BASE:CANDIDATE-BASE+MODULE_SIZE]=b'\xff'*MODULE_SIZE
        self.assertIn('early-load',check_slot(image,CANDIDATE,MODULE_SIZE))
        for base,size in ((CANDIDATE+4,MODULE_SIZE),(CANDIDATE,MODULE_SIZE-4)):
            with self.assertRaises(ValueError):check_slot(image,base,size)
        image[CANDIDATE-BASE]=0
        with self.assertRaises(ValueError):check_slot(image,CANDIDATE,MODULE_SIZE)

    def test_embedded_module_has_one_memory_mapping_and_oracle_is_private(self):
        image=b'\xff'*(CANDIDATE-BASE+MODULE_SIZE)
        module=dict(base=CANDIDATE,data=b'\x42'*MODULE_SIZE)
        patched=with_module_data(image,module)
        self.assertEqual(module_regions(patched,module),[])
        self.assertEqual(image[CANDIDATE-BASE],255)
        with self.assertRaises(ValueError):module_regions(image,module)
