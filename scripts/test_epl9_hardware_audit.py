"""Contract tests for finite hardware-status replay; no firmware or camera."""
import unittest

from epl9_hardware_audit import RegisterReplay, TaskWake
from mn103_calls import CallMachine
from mn103_subset import Region, Fault


class HardwareReplayTests(unittest.TestCase):
    def test_unknown_and_exhausted_reads_stop(self):
        m=RegisterReplay([],{0x9f000070:[0x2000]},[])
        self.assertEqual(m.read(0x9f000070,4),0x2000)
        self.assertTrue(m.exhausted())
        with self.assertRaises(Fault): m.read(0x9f000070,4)
        with self.assertRaises(Fault): m.read(0x9f000068,4)
        with self.assertRaises(Fault): m.read(0x9f000070,2)

    def test_writes_do_not_manufacture_readiness(self):
        m=RegisterReplay([],{0x9f000070:[0,0x2000]},[0x9f000070])
        m.write(0x9f000070,0xffffffff,4)
        self.assertEqual(m.read(0x9f000070,4),0)
        m.write(0x9f000070,0,4)
        self.assertEqual(m.read(0x9f000070,4),0x2000)
        with self.assertRaises(Fault): m.write(0x9f000078,1,4)
        with self.assertRaises(Fault): m.write(0x9f000070,1,2)

    def test_normal_memory_bounds_remain_enforced(self):
        m=RegisterReplay([Region(0x1000,bytearray(4),True)],{},[])
        m.write(0x1000,42,4)
        self.assertEqual(m.read(0x1000,4),42)
        with self.assertRaises(Fault): m.write(0x1004,0,4)

    def test_task_wakeup_does_not_run_scheduler(self):
        m=CallMachine({},RegisterReplay([],{},[]),{'d0':149})
        wake=TaskWake()
        with self.assertRaises(Fault): wake.validate(m,0,4)
        m.r['d0']=148
        with self.assertRaises(Fault): wake.validate(m,0,8)
        wake.validate(m,0,4)
        self.assertFalse(wake.apply(m)['scheduler_executed'])


if __name__=='__main__':
    unittest.main()
