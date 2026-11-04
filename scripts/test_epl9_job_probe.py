"""Synthetic contract tests only: no firmware, camera, RTOS or ISP required."""
import struct
import unittest

from epl9_job_probe import (FixtureOwner, FixturePool, FixturePoolFree, FixtureEventBits, FixtureConsumerSlot, FixtureLock, FixtureSignal, FixtureCompletion,
                            JOB, CACHE, SOURCE, OUTPUT, STACK, SP, SCRATCH, OWNER_CALLBACK, OWNER_CONTEXT)
from epl9_offline_prototype import check_packing
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
    def test_pool_free_rejects_pending_and_double_free(self):
        m=fixture(); pool=FixturePool(); pool.live=[JOB,CACHE]
        release=FixturePoolFree(pool); m.r['a0']=CACHE
        m.memory.write(JOB+13640,JOB,4)
        with self.assertRaises(Fault): release.validate(m,0,4)
        self.assertEqual(pool.live,[JOB,CACHE])
        m.memory.write(JOB+13640,0,4)
        release.validate(m,0,4); release.apply(m)
        self.assertEqual(pool.live,[JOB])
        with self.assertRaises(Fault): release.validate(m,0,4)

    def test_owner_free_rejects_borrowed_mismatched_and_duplicate_buffer(self):
        owner=FixtureOwner(); m=fixture(owner); record=JOB+5668
        m.memory.write(record+64,OUTPUT,4)
        with self.assertRaises(Fault): callback(m,20,record)
        m.memory.write(record+64,0,4)
        m.memory.write(record+72,64,4); m.memory.write(record+76,0x1000,4)
        callback(m,19,record)
        pointer=m.memory.read(record+64,4)
        m.memory.write(record+72,63,4)
        with self.assertRaises(Fault): callback(m,20,record)
        m.memory.write(record+72,64,4)
        callback(m,20,record)
        self.assertEqual(owner.released_buffers,{pointer})
        with self.assertRaises(Fault): callback(m,20,record)

    def test_completion_wait_never_invents_signal_and_checks_output(self):
        m=fixture(); pool=FixtureEventBits(); signal=FixtureSignal(pool)
        wait=FixtureCompletion('wait',signal,None,None)
        pool.allocated=1
        m.r.update(d0=0xe3,d1=1,a1=1,a0=SP+32)
        m.memory.write(SP+4,1000,4)
        with self.assertRaises(Fault): wait.validate(m,0xf0,40)
        signal.signalled=1
        m.r['a0']=SP
        with self.assertRaises(Fault): wait.validate(m,0xf0,40)
        m.r['a0']=SP+32
        wait.validate(m,0xf0,40); wait.apply(m)
        self.assertEqual(m.memory.read(SP+32,4),1)
        self.assertEqual(signal.signalled,1)

    def test_event_clear_before_release_and_double_release_rejected(self):
        m=fixture(); pool=FixtureEventBits(); signal=FixtureSignal(pool)
        pool.allocated=signal.signalled=1
        clear=FixtureCompletion('clear',signal,None,None)
        release=FixtureCompletion('token',signal,None,None)
        m.r['d0']=1
        with self.assertRaises(Fault): release.validate(m,0xe0,16)
        m.r.update(d0=0xe3,d1=0xfffffffe)
        clear.validate(m,0xf0,20); clear.apply(m)
        m.r['d0']=1
        release.validate(m,0xe0,16); release.apply(m)
        self.assertEqual(pool.allocated,0)
        m.r['d0']=1
        with self.assertRaises(Fault): release.validate(m,0xe0,16)

    def test_cleanup_rejects_live_processing_and_preserves_order(self):
        m=fixture(); ids=FixtureConsumerSlot('id'); workspace=FixtureConsumerSlot('workspace',ids)
        ids.used=workspace.used=True
        release=FixtureCompletion('workspace',None,ids,workspace)
        free=FixtureCompletion('id',None,ids,workspace)
        m.r['d0']=0x8000; m.memory.write(SCRATCH+9592,2,1)
        with self.assertRaises(Fault): release.validate(m,0x80,8)
        m.processor_return=0x9e40
        with self.assertRaises(Fault): free.validate(m,0xc0,12)
        release.validate(m,0x80,8); release.apply(m)
        m.r['d0']=0x8000
        free.validate(m,0xc0,12); free.apply(m)
        self.assertFalse(ids.used)
        m.r['d0']=0x8000
        with self.assertRaises(Fault): free.validate(m,0xc0,12)

    def test_event_signal_requires_allocated_token_and_never_produces_pixels(self):
        m=fixture(); pool=FixtureEventBits(); signal=FixtureSignal(pool)
        m.r.update(d0=0,d1=1)
        with self.assertRaises(Fault): signal.validate(m,0xc0,12)
        pool.validate(m,0xe0,16); pool.apply(m)
        m.r.update(d0=0,d1=1)
        signal.validate(m,0xc0,12); detail=signal.apply(m)
        self.assertEqual(signal.signalled,1)
        self.assertFalse(detail['pixels_completed'])
        with self.assertRaises(Fault): signal.validate(m,0xc0,12)

    def test_owner_slots_allocate_once_then_activate(self):
        owner=FixtureOwner(provide_slot=True); m=fixture(owner)
        for identifier,offset in [(0xff07,4960),(0xff0b,5200)]:
            m.memory.write(JOB+offset+8,0x302,2)
            for field in (10,12,14):
                m.memory.write(JOB+offset+field,4,2)
            m.memory.write(SP+64,JOB+36,4); m.memory.write(SP+68,identifier,2)
            with self.assertRaises(Fault):
                callback(m,23,SP+64)
            callback(m,14,SP+64)
            address=m.memory.read(JOB+offset,4)
            callback(m,14,SP+64)
            self.assertEqual(m.memory.read(JOB+offset,4),address)
            callback(m,23,SP+64)
            with self.assertRaises(Fault):
                callback(m,23,SP+64)
        self.assertEqual(len(owner.buffers),2)
        self.assertEqual(owner.active_slots,{0xff07,0xff0b})

    def test_owner_borrowed_slot_and_invalid_dimensions(self):
        owner=FixtureOwner(provide_slot=True); m=fixture(owner)
        m.memory.write(SP+64,JOB+36,4); m.memory.write(SP+68,0xff07,2)
        m.memory.write(JOB+4968,0x302,2)
        before=[bytes(r.data) for r in m.memory.regions]
        with self.assertRaises(Fault):
            callback(m,14,SP+64)
        self.assertEqual(before,[bytes(r.data) for r in m.memory.regions])
        m.memory.write(JOB+4960,OUTPUT,4)
        for field in (10,12,14):
            m.memory.write(JOB+4960+field,4,2)
        callback(m,23,SP+64)
        self.assertEqual(owner.buffers,[])
        self.assertEqual(m.memory.read(JOB+4960,4),OUTPUT)

    def test_workspace_release_requires_live_slot_and_does_not_complete_frame(self):
        m=fixture(); ids=FixtureConsumerSlot('id'); workspace=FixtureConsumerSlot('workspace',ids)
        release=FixtureConsumerSlot('release',workspace)
        m.r['a0']=SCRATCH
        with self.assertRaises(Fault):
            release.validate(m,0xf0,24)
        ids.validate(m,0xf0,20); ids.apply(m)
        workspace.validate(m,0xf0,36); workspace.apply(m)
        release.validate(m,0xf0,24); detail=release.apply(m)
        self.assertFalse(detail['completed'])
        self.assertEqual(m.memory.read(SCRATCH+9592,1),2)
        with self.assertRaises(Fault):
            release.validate(m,0xf0,24)

    def test_coefficient_notification_preserves_all_nine_native_values(self):
        m=fixture()
        m.events.append(dict(op='call',pc=0x6079c026,target=0x6073eab3))
        values=[128,10,65530,8,124,65532,65534,6,124]
        for index,value in enumerate(values):
            m.memory.write(SP+64+index*2,value,2)
        callback(m,2,SP+64)
        self.assertEqual(m.events[-1]['coefficients_preserved'],values)
        self.assertEqual([m.memory.read(SP+64+i*2,2) for i in range(9)],values)
        self.assertEqual(m.r['sp'],SP)

    def test_coefficient_notification_rejects_unknown_caller_and_frame_overlap(self):
        for arg,caller in [(SP+64,False),(SP,True),(SP+65,True),(STACK+16368,True),(OUTPUT,True)]:
            m=fixture()
            if caller:
                m.events.append(dict(op='call',pc=0x6079c026,target=0x6073eab3))
            before=[bytes(r.data) for r in m.memory.regions]
            with self.assertRaises(Fault):
                callback(m,2,arg)
            self.assertEqual(m.r['sp'],SP)
            self.assertEqual(before,[bytes(r.data) for r in m.memory.regions])

    def test_uncontended_locks_reject_wrong_key_abi_and_reentry(self):
        for value,mask,frame in [(16,0xa0,12),(8,0xc0,16)]:
            m=fixture(); lock=FixtureLock(value,mask,frame)
            for bad_value,bad_mask,bad_frame in [(value+1,mask,frame),(value,0,frame),(value,mask,0)]:
                m.r['d0']=bad_value
                with self.assertRaises(Fault):
                    lock.validate(m,bad_mask,bad_frame)
                self.assertFalse(lock.held)
            m.r['d0']=value
            lock.validate(m,mask,frame)
            detail=lock.apply(m)
            self.assertTrue(detail['held'])
            self.assertFalse(detail['device_accessed'])
            with self.assertRaises(Fault):
                lock.validate(m,mask,frame)

    def test_packing_oracle_preserves_prior_state_and_checks_relocated_pointers(self):
        table=bytes(3028)
        initial=bytes([0xa5])*5200
        packed=bytearray(initial)
        packed[688:980]=bytes(292)
        # Zero-valued table leaves only the ten relocated LUT pointers nonzero.
        for index,offset in enumerate((336,1680,720,1104,2064,2448,1296,2640,1488,2832)):
            struct.pack_into('<I',packed,3124+index*4,0x19010000+offset)
        check_packing(packed,table,[0]*12,initial=initial,table_address=0x19010000)
        for offset in (500,3124):
            changed=bytearray(packed); changed[offset]^=1
            with self.assertRaises(ValueError):
                check_packing(changed,table,[0]*12,initial=initial,table_address=0x19010000)

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
