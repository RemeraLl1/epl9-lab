"""Fail-closed evidence controls; no firmware or RTOS is simulated here."""
import copy
import unittest
from unittest.mock import patch

import epl9_iseq_protocol_probe as probe


def evidence(allocate=True):
    calls=[dict(pc='0x609a6b97',target='0x609a6c22')]
    if allocate:
        calls.insert(0,dict(pc='0x609a6b7d',target='0x609a6bcc'))
    return dict(stop=dict(status='stop',pc=hex(probe.END)),return_value=0,
        sp_after=hex(probe.SP),native_calls=calls,result_list_count=0,
        result_list_hex='00'*probe.RESULT_BYTES,graph_result_supplied=False,
        executor_or_worker_entered=False,kernel_or_hardware_modeled=False,
        modeled_software_fills=[dict(target=0x4700111e,model='assumed-byte-fill',
            start=hex(probe.SP-offset),count=count,byte=0) for offset,count in ((356,16),(340,324))])


class TransactionEvidenceTests(unittest.TestCase):
    def test_status_never_claims_job_execution_or_completion(self):
        for allocate in (True,False):
            r=probe.checked_transaction(evidence(allocate),allocate)
            self.assertEqual(r['status'],'bounded_connector_only')
            self.assertFalse(r['worker_dispatch_observed'])
            self.assertFalse(r['job_reuse_proven'])
            self.assertFalse(r['real_completion_observed'])

    def test_wrong_stop_fault_return_or_stack_rejected(self):
        for field,value in (('stop',dict(status='fault',error='unrelated fault')),
                ('stop',dict(status='stop',pc='0x609a6c22')),('return_value',39937),
                ('sp_after','0x10011ff0')):
            row=evidence();row[field]=value
            with self.subTest(field=field,value=value),self.assertRaises(ValueError):
                probe.checked_transaction(row,True)

    def test_empty_result_and_no_execution_are_mandatory(self):
        for field,value in (('result_list_count',1),('result_list_hex','00'),
                ('result_list_hex','00'*(probe.RESULT_BYTES-1)+'01'),
                ('graph_result_supplied',True),('executor_or_worker_entered',True),
                ('kernel_or_hardware_modeled',True)):
            row=evidence();row[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):
                probe.checked_transaction(row,True)

    def test_exact_calls_and_fill_contract_required(self):
        variants=[]
        row=evidence();row['native_calls'].append(dict(pc='0x609a6c97',target='0x609a6ceb'));variants.append(row)
        row=evidence();row['native_calls'].pop(0);variants.append(row)
        row=evidence();row['native_calls'][0]['pc']='0x609a6b7e';variants.append(row)
        row=evidence();row['modeled_software_fills'][1]['count']=2;variants.append(row)
        row=evidence();row['modeled_software_fills'][1]['model']='graph-success';variants.append(row)
        row=evidence();row['modeled_software_fills'].pop();variants.append(row)
        for row in variants:
            with self.subTest(row=row),self.assertRaises(ValueError):
                probe.checked_transaction(row,True)

    def test_missing_evidence_rejected(self):
        original=evidence()
        for field in original:
            row=copy.deepcopy(original);del row[field]
            with self.subTest(field=field),self.assertRaises(ValueError):
                probe.checked_transaction(row,True)


class ReferenceEvidenceTests(unittest.TestCase):
    def test_reference_inventory_and_context_both_required(self):
        candidates={target:[dict(pc=hex(pc),op='call',raw='cd0000f010') for pc in pcs]
            for target,pcs in probe.EXPECTED_REFERENCES.items()}
        code={int(r['pc'],16):(bytes.fromhex(r['raw']),'call',[hex(target),'[d2,d3,a2,a3]','16'])
            for target,rows in candidates.items() for r in rows}
        with patch.object(probe,'direct_candidates',side_effect=lambda im,base,target:candidates[target]), \
                patch.object(probe,'literal_positions',return_value=[]):
            self.assertEqual(len(probe.references(b'',code)),len(probe.EXPECTED_REFERENCES))
            broken=dict(code);broken.pop(next(iter(broken)))
            with self.assertRaisesRegex(ValueError,'containing-context'):
                probe.references(b'',broken)
        with patch.object(probe,'direct_candidates',return_value=[]), \
                patch.object(probe,'literal_positions',return_value=[]):
            with self.assertRaisesRegex(ValueError,'inventory differs'):
                probe.references(b'',code)


if __name__=='__main__':
    unittest.main()
