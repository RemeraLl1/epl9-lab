"""Synthetic contract tests only: no firmware, camera, RTOS or ISP required."""
import unittest

from epl9_job_probe import (FixtureOwner, FixturePool, FixtureEventBits, FixtureConsumerSlot,
                            JOB, CACHE, SOURCE, OUTPUT, STACK, SP, SCRATCH, OWNER_CALLBACK, OWNER_CONTEXT)
from mn103_calls import CallMachine
from mn103_subset import Memory, Region, Fault


def fixture(owner=None):
    regions=[Region(JOB,bytearray(16384),True),Region(CACHE,bytearray(16384),True),
             Region(STACK,bytearray(16384),True),Region(OWNER_CONTEXT,bytearray(4)),
             Region(SOURCE,bytearray(32)),Region(OUTPUT,bytearray(32),True),
             Region(0x8050,bytearray(4)),Region(SCRATCH,bytearray(9596),True)]
    m=CallMachine({0x2000:(b'\xf0\xf3','calls',['(a3)'])},Memory(regions),
                  {'sp':SP,'a3':OWNER_CALLBACK,'a1':OWNER_CONTEXT},
                  models={OWNER_CALLBACK:owner or FixtureOwner()})
    for offset,address in [(36,SOURCE),(100,OUTPUT),(4264,OUTPUT)]:
        m.memory.write(JOB+offset,address,4)
        for field in (10,12,14):
            m.memory.write(JOB+offset+field,4,2)
    m.memory.write(JOB+10440+1484,CACHE,4)
    return m


def callback(m,event,arg):
    m.r.update(d0=event,a0=arg,a1=OWNER_CONTEXT,a3=OWNER_CALLBACK)
    return m.run(0x2000,[0x2002])


class JobContractTests(unittest.TestCase):
    def test_owner_continue_and_reject_are_explicit(self):
        for value in (False,True):
            m=fixture(FixtureOwner(value,value))
            callback(m,13,0)
            self.assertEqual(m.r['d0'],int(value))
            callback(m,21,JOB+10440)
            self.assertEqual(m.r['d0'],int(value))
            self.assertEqual(m.r['sp'],SP)
            self.assertTrue(all(e['op']=='modeled_call' for e in m.events))

    def test_unknown_owner_event_and_bad_context_are_atomic(self):
        for event,arg,context in [(31,0,OWNER_CONTEXT),(13,1,OWNER_CONTEXT),(13,0,0)]:
            m=fixture()
            m.r.update(d0=event,a0=arg,a1=context)
            before=[bytes(r.data) for r in m.memory.regions]
            with self.assertRaises(Fault):
                m.run(0x2000)
            self.assertEqual(m.r['sp'],SP)
            self.assertEqual(before,[bytes(r.data) for r in m.memory.regions])

    def test_descriptor_bounds_and_missing_descriptor(self):
        for identifier in (1,2,0xff12):
            m=fixture()
            m.memory.write(SP+64,JOB+36,4)
            m.memory.write(SP+68,identifier,2)
            callback(m,14,SP+64)
            self.assertEqual(m.r['d0'],1)
        for identifier,stride in [(0xff07,4),(1,5),(1,0)]:
            m=fixture()
            m.memory.write(SP+64,JOB+36,4)
            m.memory.write(SP+68,identifier,2)
            m.memory.write(JOB+46,stride,2)
            with self.assertRaises(Fault):
                callback(m,14,SP+64)
            self.assertEqual(m.r['sp'],SP)

    def test_buffer_allocation_sets_base_and_preserves_native_fields(self):
        owner=FixtureOwner()
        m=fixture(owner)
        record=JOB+5668
        for index in range(2):
            arg=record+index*88
            m.memory.write(arg+72,64,4)
            m.memory.write(arg+76,4096+index,4)
            callback(m,19,arg)
            region=next(r for r in m.memory.regions if r.address==owner.buffers[-1]['address'])
            self.assertEqual(region.data,b'\xcd'*64+b'\xa5'*16)
            self.assertEqual(m.memory.read(arg+64,4),region.address)
            self.assertEqual(m.memory.read(arg,4),0)  # Native caller supplies this later.
            self.assertEqual((m.memory.read(arg+72,4),m.memory.read(arg+76,4)),(64,4096+index))
        with self.assertRaisesRegex(Fault,'capacity'):
            callback(m,19,record)

    def test_buffer_rejects_invalid_size_address_and_overlap_before_mutation(self):
        for size,offset,overlap in [(0,0,False),(32*1024*1024+1,0,False),(64,4,False),(64,0,True)]:
            m=fixture()
            arg=JOB+5668+offset
            m.memory.write(arg+72,size,4)
            if overlap:
                m.memory=Memory([*m.memory.regions,Region(0x20000000,bytearray(4),True)])
            before=[bytes(r.data) for r in m.memory.regions]
            with self.assertRaises(Fault):
                callback(m,19,arg)
            self.assertEqual(before,[bytes(r.data) for r in m.memory.regions])
            self.assertEqual(m.r['sp'],SP)

    def test_two_pool_slots_are_bounded(self):
        m=fixture(); pool=FixturePool()
        for address in (JOB,CACHE):
            m.r['d0']=0x10004
            pool.validate(m,0xe0,16); pool.apply(m)
            self.assertEqual(m.r['a0'],address)
        with self.assertRaises(Fault):
            pool.validate(m,0xe0,16)
        self.assertEqual(pool.live,[JOB,CACHE])

    def test_event_tokens_never_imply_completion_and_exhaust(self):
        m=fixture(); pool=FixtureEventBits()
        for n in range(32):
            pool.validate(m,0xe0,16)
            detail=pool.apply(m)
            self.assertEqual(m.r['d0'],1 << n)
            self.assertFalse(detail['completed'])
        with self.assertRaises(Fault):
            pool.validate(m,0xe0,16)

    def test_consumer_slot_requires_declared_id_and_cannot_be_reused(self):
        m=fixture(); ids=FixtureConsumerSlot('id'); workspace=FixtureConsumerSlot('workspace',ids)
        with self.assertRaises(ValueError):
            FixtureConsumerSlot('unknown')
        m.r['d0']=0x8000
        with self.assertRaises(Fault):
            workspace.validate(m,0xf0,36)
        ids.validate(m,0xf0,20); ids.apply(m)
        workspace.validate(m,0xf0,36); workspace.apply(m)
        self.assertEqual(m.r['a0'],SCRATCH)
        self.assertEqual(m.memory.read(SCRATCH+9588,4),0x8000)
        self.assertEqual(m.memory.read(SCRATCH+9592,1),1)
        for model,frame in [(ids,20),(workspace,36)]:
            with self.assertRaises(Fault):
                model.validate(m,0xf0,frame)


if __name__=='__main__':
    unittest.main()
