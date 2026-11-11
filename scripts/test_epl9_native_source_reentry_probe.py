"""Firmware-independent controls for cloned reentry evidence and validation."""
import copy
import struct
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from epl9_native_source_reentry_probe import (JOB, STACK, REQUEST, REENTRY_SP, STOP,
    CAPACITY_ERROR, EXPECTED_REQUEST_CHANGES, EXPECTED_CONTINUED_REQUEST_CHANGES,
    EXPECTED_LATE_JOB_CHANGES, continue_outer, OUTPUT, OWNER_CALLBACK, clone_state, blob, differences,
    state_digest, checked_reentry)
from mn103_calls import CallMachine
from mn103_subset import Memory, Region

GAINS=[1106,901,1024,1024]
GAMMA=['0x604a3800','0x604a3c00','0x604a4000']


def good_row(site='gain_return'):
    state=dict(cursor=1,count=2,error=0,cancelled=0,source_gains=[1024]*4,
        request_gains=list(GAINS),request_fields={'14':0x1000,'28':0x107,'48':3,'1832':0},
        classifier_flags=[1,0,0],pending='00'*56)
    if site=='COLOR':
        state['pending']=(struct.pack('<5I',JOB,0,REQUEST,0x8000,1)+bytes(36)).hex()
    safe=dict(output_changed=False,source_pixel_reads=[],event_bits_signalled=0,
        buffers=[dict(payload_changed=False,canary_intact=True)])
    events=[dict(op='call',pc=0x6074a8bb,target=0x6073eab3)]
    capacity=dict(executor=dict(status='fault',error=CAPACITY_ERROR,
        last_instructions=['0x6073eac3']),events=events)
    hardware=dict(executor=dict(status='fault',error=STOP,last_instructions=['0x6073eafa'],
        registers={'d0':'0x800'}),fields=dict(request_gains=list(GAINS),gamma_pointers=GAMMA))
    row=dict(**copy.deepcopy(safe),**copy.deepcopy(capacity),site=site,
        repeated_work_dispatches=[dict(pc='0x6074e765',target='0x60751319')],
        parent_ram_and_models_unchanged=True,memory_and_model_aliases_preserved=True,
        outer_live_stack_unchanged=True,before=copy.deepcopy(state),after=copy.deepcopy(state),
        cache_changes=[],checkpoints=[],gain_writes=[],request_changes=[],request_unchanged=True,
        resources_before=dict(buffers=[{'id':i} for i in (0x1000,7,8,10,11,12,13)]),
        resources_after=dict(buffers=[{'id':i} for i in (0x1000,7,8,10,11,12,13)]),
        job_changes=copy.deepcopy(EXPECTED_LATE_JOB_CHANGES),
        baseline_continuation=dict(**copy.deepcopy(safe),**copy.deepcopy(hardware)),
        overlap_continuation=dict(**copy.deepcopy(safe),**copy.deepcopy(hardware)),
        continued_request_changes_vs_baseline=[],continued_cache_changes_vs_baseline=[])
    if site=='gain_return':
        row.update(request_changes=copy.deepcopy(EXPECTED_REQUEST_CHANGES),request_unchanged=False,
            resources_before=dict(buffers=[{'id':0x1000}]),
            resources_after=dict(buffers=[{'id':i} for i in (0x1000,0x1000,7,8,10,11,12)]),
            checkpoints=[dict(phase=p,request_gains=list(g)) for p,g in
                (('old_constructor_site',[1024]*4),('gain_entry',[1024]*4),('gain_return',GAINS))],
            overlap_continuation=dict(**copy.deepcopy(safe),**copy.deepcopy(capacity),
                fields=dict(request_gains=list(GAINS),gamma_pointers=['0x0']*3),
                cache_unchanged_from_snapshot=True),
            continued_request_changes_vs_baseline=copy.deepcopy(EXPECTED_CONTINUED_REQUEST_CHANGES),
            continued_cache_changes_vs_baseline=[dict(offset=0,length=4)])
    return row


class SnapshotTests(unittest.TestCase):
    def parent(self):
        job=bytearray(16384)
        struct.pack_into('<H',job,10390,2)
        storage=bytearray(b'abcdefgh')
        region=Region(0x2c000000,storage,True)
        shared=SimpleNamespace(allocated=1)
        owner=SimpleNamespace(regions=[region],storage=storage,shared=shared)
        parent=CallMachine({},Memory([Region(JOB,job,True),Region(STACK,bytearray(16384),True),region]),
            dict(sp=STACK+15000),models={1:owner,2:shared,3:SimpleNamespace(pool=shared)})
        return parent

    def test_clone_preserves_ram_owner_and_resource_aliases(self):
        parent=self.parent();child=clone_state(parent)
        owner=child.models[1]
        region,_=child.memory.region(0x2c000000,1)
        self.assertIs(owner.storage,region.data)
        self.assertIs(owner.regions[0],region)
        self.assertIs(owner.shared,child.models[2])
        self.assertIs(child.models[3].pool,child.models[2])
        self.assertIsNot(owner.storage,parent.models[1].storage)
        self.assertEqual((child.r['sp'],child.r['d0'],child.r['d1']),(REENTRY_SP,JOB,2))
        self.assertEqual(child.r.minimum_sp,REENTRY_SP)

    def test_clone_changes_leave_parent_bytes_and_models_unchanged(self):
        parent=self.parent();before=state_digest(parent);child=clone_state(parent)
        child.memory.write(JOB,123,4)
        child.models[1].storage[0]=255
        child.models[2].allocated=7
        self.assertEqual(state_digest(parent),before)
        self.assertNotEqual(state_digest(child),before)
        self.assertEqual(parent.models[2].allocated,1)
        self.assertEqual(parent.models[1].storage,b'abcdefgh')

    def test_digest_covers_model_and_memory_changes(self):
        parent=self.parent();before=state_digest(parent)
        parent.models[2].allocated=2
        self.assertNotEqual(state_digest(parent),before)
        before=state_digest(parent);parent.memory.write(JOB,1,4)
        self.assertNotEqual(state_digest(parent),before)

    def test_continuation_restores_all_native_state_not_reentry_registers(self):
        parent=self.parent()
        for i,key in enumerate(parent.r):
            if key!='sp':parent.r[key]=0x100+i
        parent.n,parent.z,parent.c,parent.v=True,False,True,True
        parent.loop=dict(start=0x60761c98,end=0x60761c9d,nested=[1,2])
        parent.memory=Memory([*parent.memory.regions,Region(OUTPUT,bytearray([0xcd])*16,True)])
        parent.models[OWNER_CALLBACK]=SimpleNamespace(buffers=[])
        parent.models[0x6074af2c]=SimpleNamespace(signalled=0)
        child=clone_state(parent);expected=dict(parent.r);calls=[]
        def inspect(machine,pc):
            calls.append(pc)
            self.assertEqual(dict(machine.r),expected)
            self.assertEqual((machine.n,machine.z,machine.c,machine.v),(True,False,True,True))
            self.assertEqual(machine.loop,parent.loop)
            self.assertIsNot(machine.loop,parent.loop)
            machine.loop['nested'].append(3)
            machine.memory.write(parent.r['sp'],0x1234,4)
            return dict(status='stop',pc=pc)
        with patch('epl9_native_source_reentry_probe.resume',side_effect=inspect), \
             patch('epl9_native_source_reentry_probe.fields',return_value={}), \
             patch('epl9_native_source_reentry_probe.resource_state',return_value={}):
            result=continue_outer(parent,child.memory,child.models,0x60761ca4)
        self.assertEqual(calls,[0x60761ca4])
        self.assertEqual(parent.memory.read(parent.r['sp'],4),0)
        self.assertEqual(parent.loop['nested'],[1,2])
        self.assertEqual(result['report']['executor']['pc'],0x60761ca4)

    def test_all_changed_spans_and_trailing_byte_are_retained(self):
        self.assertEqual(differences(b'abcdef',b'aXXdY!'),[
            dict(offset=1,length=2,before='6263',after='5858'),
            dict(offset=4,length=2,before='6566',after='5921')])
        self.assertEqual(differences(b'abc',b'abc'),[])
        with self.assertRaises(ValueError):differences(b'a',b'ab')

    def test_blob_requires_one_complete_region(self):
        parent=self.parent()
        self.assertEqual(blob(parent.memory,0x2c000002,3),b'cde')
        with self.assertRaises(ValueError):blob(parent.memory,0x2c000004,5)


class ReentryValidatorTests(unittest.TestCase):
    def check(self,row):return checked_reentry(row,GAINS,GAMMA)
    def rejected(self,row):
        with self.assertRaises(ValueError):self.check(row)

    def test_all_three_sites_have_scoped_incomplete_results(self):
        for site in ('gain_return','submission','COLOR'):
            with self.subTest(site=site):
                result=self.check(good_row(site))
                self.assertEqual(result['status'],'incomplete')
                self.assertFalse(result['wb_accumulation_observed'])
                self.assertFalse(result['whole_job_completed'])
                self.assertEqual(result['request_reconstructed'],site=='gain_return')

    def test_arbitrary_fault_or_wrong_native_requester_is_not_a_pass(self):
        for key,value in (('error','different error'),('status','stop'),('last_instructions',['0x6073eac4'])):
            row=good_row();row['executor'][key]=value;self.rejected(row)
        row=good_row();row['events'][-1]['pc']=0x6074a8bc;self.rejected(row)
        row=good_row();row['events']=[];self.rejected(row)

    def test_duplicate_dispatch_must_have_run_beyond_old_stop(self):
        row=good_row();row['repeated_work_dispatches']=[];self.rejected(row)
        row=good_row();row['repeated_work_dispatches'][0]['target']='0x6074e765';self.rejected(row)

    def test_output_source_completion_and_guards_must_stay_untouched(self):
        for section in (None,'baseline_continuation','overlap_continuation'):
            for key,value in (('output_changed',True),('source_pixel_reads',[{}]),('event_bits_signalled',1)):
                row=good_row();target=row if section is None else row[section]
                target[key]=value;self.rejected(row)
            row=good_row();target=row if section is None else row[section]
            target['buffers'][0]['canary_intact']=False;self.rejected(row)

    def test_missing_completion_or_buffer_evidence_is_rejected(self):
        row=good_row();del row['event_bits_signalled'];self.rejected(row)
        row=good_row();row['buffers']=[];self.rejected(row)

    def test_accumulated_or_changed_source_gain_is_rejected(self):
        row=good_row();row['after']['request_gains'][0]=1195;self.rejected(row)
        row=good_row();row['after']['source_gains'][0]=1106;self.rejected(row)
        row=good_row();row['overlap_continuation']['fields']['request_gains'][0]=1195;self.rejected(row)

    def test_reconstruction_requires_fresh_source_copy_and_one_hook(self):
        row=good_row();row['checkpoints'][1]['request_gains']=GAINS;self.rejected(row)
        row=good_row();row['checkpoints'].append(copy.deepcopy(row['checkpoints'][1]));self.rejected(row)

    def test_request_differences_cannot_be_omitted_or_hidden(self):
        row=good_row();row['request_changes']=[];self.rejected(row)
        row=good_row('submission');row['request_unchanged']=False;self.rejected(row)
        row=good_row('COLOR');row['request_changes']=[dict(offset=1568,length=1)];self.rejected(row)

    def test_pending_live_COLOR_record_is_preserved(self):
        row=good_row('COLOR');self.check(row)
        row['after']['pending']='00'*56;self.rejected(row)
        row=good_row();row['after']['pending']='01'+'00'*55;self.rejected(row)

    def test_clone_and_suspended_stack_isolation_is_required(self):
        for key in ('parent_ram_and_models_unchanged','memory_and_model_aliases_preserved','outer_live_stack_unchanged'):
            row=good_row();row[key]=False;self.rejected(row)

    def test_baseline_and_late_continuations_require_exact_hardware_and_gamma(self):
        row=good_row();row['baseline_continuation']['executor']['registers']['d0']='0';self.rejected(row)
        row=good_row('submission');row['overlap_continuation']['fields']['gamma_pointers']=[];self.rejected(row)
        row=good_row('COLOR');row['continued_cache_changes_vs_baseline']=[{}];self.rejected(row)

    def test_equal_span_count_cannot_hide_unrelated_request_corruption(self):
        row=good_row()
        row['continued_request_changes_vs_baseline'][0]['offset']=5
        self.rejected(row)
        row=good_row()
        row['continued_request_changes_vs_baseline'][0]['after']='ffff'
        self.rejected(row)
        row=good_row('submission')
        row['job_changes'][0]['after']='ffff'
        self.rejected(row)

    def test_unfinished_cache_requires_original_bytes_and_unset_gamma(self):
        row=good_row();row['overlap_continuation']['cache_unchanged_from_snapshot']=False
        self.rejected(row)
        row=good_row();row['overlap_continuation']['fields']['gamma_pointers']=GAMMA
        self.rejected(row)

    def test_gain_return_disruption_must_not_be_reported_as_completion(self):
        row=good_row();row['overlap_continuation']=copy.deepcopy(row['baseline_continuation']);self.rejected(row)
        row=good_row();row['continued_request_changes_vs_baseline']=[];self.rejected(row)


if __name__=='__main__':unittest.main()
