import unittest
from mn103_calls import CallMachine
from mn103_subset import Memory, Region
from epl9_deployment_probe import Observe, placement_coverage
from epl9_job_probe import JOB, SP


class ObserverTests(unittest.TestCase):
    def test_whole_module_must_fit_inside_one_loaded_section(self):
        self.assertEqual(placement_coverage(0x6066f800,0x3c00)['stock_section_covers_module'],[2])
        for start in (0x60600f00,0x617bd500):
            self.assertFalse(placement_coverage(start,0x3c00)['post_entry_loader_covers_module'])
        self.assertTrue(placement_coverage(0x60423600,0x3c00)['pre_main_mapping_unknown'])

    def test_reads_and_writes_remain_observed_after_memory_replacement(self):
        address=JOB+10440
        m=CallMachine({},Memory([Region(address,bytearray(1876),True)]),dict(a2=address,sp=SP))
        meter=Observe();meter(m)
        replacement=bytearray(1876)
        replacement[1568:1570]=b'\x34\x12'
        m.memory=Memory([Region(address,replacement,True)])
        m.trace.append(0x68000030)
        self.assertEqual(m.read('(1568,a2)',2),0x1234)
        m.write('(8,a2)',11)
        report=meter.result()
        self.assertEqual(len(report['wb_reads']),1)
        self.assertEqual(report['hook_request_writes'][0]['offset'],8)
        self.assertEqual(report['actual_hook_request_addresses'],[hex(address)])
        self.assertEqual(int.from_bytes(replacement[8:12],'little'),11)
