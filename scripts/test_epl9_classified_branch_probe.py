"""Fail-closed evidence checks, independent of firmware/ISP availability."""
from copy import deepcopy
import unittest

from epl9_native_source_probe import checked_classified_prefix,STOP

FIELDS={'14':0x1000,'28':0x107,'48':3,'1832':0}
GAINS=[1106,901,1024,1024]
GAMMA=['0x604a4300','0x604a4500','0x604a4700']


def fixture():
    checkpoints=[dict(phase='old_constructor_site',index=1,gains=[1024]*4,fields={}),
        dict(phase='gain_entry',index=2,gains=[1024]*4,fields=dict(FIELDS)),
        dict(phase='gain_return',index=3,gains=list(GAINS),fields=dict(FIELDS))]
    case=dict(native_film=dict(source_gain_record=[1024]*4,request_gain_record=list(GAINS),
        request_fields=dict(FIELDS)),executor=dict(status='fault',
        error='owner buffer request exceeds declared fixture capacity',
        last_instructions=['0x6073eac3']),
        events=[dict(op='call',pc=0x6074a8bb,target=0x6073eab3)],
        output_changed=False,cpu_source_reads=[],event_bits_signalled=0)
    return case,checkpoints


class ClassifiedEvidenceTests(unittest.TestCase):
    def test_expected_buffer_limit_is_explicitly_incomplete(self):
        case,points=fixture()
        checked=checked_classified_prefix(case,points,GAINS)
        self.assertEqual(checked['status'],'incomplete')
        self.assertEqual(checked['expected_stop_verified'],'buffer_limit')
        self.assertFalse(checked['multiple_submissions_completed'])

    def test_arbitrary_fault_wrong_requester_and_missing_evidence_fail(self):
        for mutation in ('fault','requester','dispatch','source','gains','fields',
                         'output','missing_output','missing_reads','missing_signal'):
            case,points=fixture()
            if mutation=='fault':case['executor']['error']='unmapped instruction'
            elif mutation=='requester':case['events'][-1]['pc']=0x6074a8c2
            elif mutation=='dispatch':case['executor']['last_instructions']=['0x6073eac2']
            elif mutation=='source':case['native_film']['source_gain_record'][0]=1106
            elif mutation=='gains':case['native_film']['request_gain_record'][0]=1195
            elif mutation=='fields':case['native_film']['request_fields']['48']=7
            elif mutation=='output':case['output_changed']=True
            elif mutation=='missing_output':del case['output_changed']
            elif mutation=='missing_reads':del case['cpu_source_reads']
            else:del case['event_bits_signalled']
            with self.subTest(mutation=mutation):
                with self.assertRaises(ValueError):checked_classified_prefix(case,points,GAINS)

    def test_checkpoint_gain_mutation_double_entry_or_early_consumer_fail(self):
        for mutation in ('before','after','source_fields','double','missing','consumer'):
            case,points=fixture()
            if mutation=='before':points[0]['gains'][0]=1106
            elif mutation=='after':points[2]['gains'][0]=1195
            elif mutation=='source_fields':points[1]['fields']['1832']=0x900
            elif mutation=='double':points.append(deepcopy(points[1]))
            elif mutation=='missing':points.pop()
            else:points.append(dict(phase='gain_consumer',index=1,gains=GAINS,fields=FIELDS))
            with self.subTest(mutation=mutation):
                with self.assertRaises(ValueError):checked_classified_prefix(case,points,GAINS)

    def test_submission_and_hardware_require_their_exact_stop_contracts(self):
        case,points=fixture()
        with self.assertRaises(ValueError):checked_classified_prefix(case,points,GAINS,expected_stop='first_submission')
        case['executor']=dict(status='stop',pc=0x6074f11c)
        case['events']=[dict(op='call',pc=0x60762276,target=0x6074f11c)]
        self.assertEqual(checked_classified_prefix(case,points,GAINS,expected_stop='first_submission')['status'],'incomplete')
        case['events'][-1]['pc']=0x60762326
        with self.assertRaises(ValueError):checked_classified_prefix(case,points,GAINS,expected_stop='first_submission')
        case['executor']=dict(status='fault',error=STOP,last_instructions=['0x6073eafa'],registers={'d0':'0x800'})
        case['events']=[dict(op='call',pc=0x60762276,target=0x6074f11c)]
        case['native_film'].update(recipe_applied=True,gamma_hook=True,finalized_gain_hook=True,
            early_gain_hook=False,gamma_pointers=list(GAMMA))
        points.extend(dict(phase=p,index=i,gains=list(GAINS),fields=dict(FIELDS)) for i,p in
            enumerate(('submission','color_entry','gain_consumer'),4))
        self.assertEqual(checked_classified_prefix(case,points,GAINS,expected_stop='first_hardware',expected_gamma=GAMMA)['status'],'incomplete')
        case['native_film']['recipe_applied']=False
        with self.assertRaises(ValueError):checked_classified_prefix(case,points,GAINS,expected_stop='first_hardware',expected_gamma=GAMMA)

    def test_hardware_consumer_gamma_value_and_stage_evidence_are_mandatory(self):
        case,points=fixture()
        case['executor']=dict(status='fault',error=STOP,last_instructions=['0x6073eafa'],registers={'d0':'0x800'})
        case['events']=[dict(op='call',pc=0x60762276,target=0x6074f11c)]
        case['native_film'].update(recipe_applied=True,gamma_hook=True,finalized_gain_hook=True,
            early_gain_hook=False,gamma_pointers=list(GAMMA))
        points.extend(dict(phase=p,index=i,gains=list(GAINS),fields=dict(FIELDS)) for i,p in
            enumerate(('submission','color_entry','gain_consumer'),4))
        for mutation in ('consumer_gains','consumer_fields','missing_submission','double_color',
                         'gamma_hook','gamma_pointers','write_value','submission_event','missing_expected_gamma'):
            c,p=deepcopy(case),deepcopy(points)
            gamma=GAMMA
            if mutation=='consumer_gains':p[-1]['gains']=[1024]*4
            elif mutation=='consumer_fields':p[-2]['fields']['48']=7
            elif mutation=='missing_submission':p.pop(3)
            elif mutation=='double_color':p.append(deepcopy(p[-2]))
            elif mutation=='gamma_hook':c['native_film']['gamma_hook']=False
            elif mutation=='gamma_pointers':c['native_film']['gamma_pointers']=['0x0']*3
            elif mutation=='write_value':c['executor']['registers']['d0']='0x0'
            elif mutation=='submission_event':c['events']=[]
            else:gamma=None
            with self.subTest(mutation=mutation):
                with self.assertRaises(ValueError):checked_classified_prefix(c,p,GAINS,
                    expected_stop='first_hardware',expected_gamma=gamma)


if __name__=='__main__':unittest.main()
