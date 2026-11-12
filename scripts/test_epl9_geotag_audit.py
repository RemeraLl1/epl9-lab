import copy
import unittest
from epl9_geotag_audit import audit

def fixture():
    return {'schema':1,'units':'elapsed_realtime_ms','ground_truth_shots':['s1','s2'],
            'events':[{'boot':'b1','event_id':'e1','received_ms':1000,'shot_id':'s1'}],
            'requests':[{'boot':'b1','event_id':'e1','request_id':'r1','start_ms':1010,'end_ms':1500,
                         'status':'fix','fix_boot':'b1','fix_ms':1400,'accuracy_m':10}]}

class Audit(unittest.TestCase):
    def test_valid_and_missing_shot(self):
        a=audit(fixture()); self.assertEqual(a['events_with_usable_fix'],1)
        self.assertEqual(a['shots_without_associated_event'],1)
        self.assertEqual(a['shots_without_usable_fix'],1)
    def test_cached_stale(self):
        d=fixture();d['requests'][0]['fix_ms']=0
        a=audit(d,max_age_ms=1000);self.assertEqual(a['fix_rejections'],{'stale':1})
    def test_accuracy(self):
        d=fixture();d['requests'][0]['accuracy_m']=99
        self.assertEqual(audit(d)['events_with_usable_fix'],0)
    def test_null_denominator_and_multiple_requests(self):
        d=fixture();r=copy.deepcopy(d['requests'][0]);r.update(request_id='r2',status='null')
        for k in ['fix_ms','fix_boot','accuracy_m']:del r[k]
        d['requests'].append(r)
        a=audit(d);self.assertEqual(a['null_fraction_of_requests'],.5)
        self.assertEqual(a['events_with_usable_fix'],1)
    def test_no_ground_truth_no_miss_claim(self):
        d=fixture();del d['ground_truth_shots'];del d['events'][0]['shot_id']
        self.assertIsNone(audit(d)['shots_without_usable_fix'])
    def test_no_request(self):
        d=fixture();d['requests']=[];a=audit(d)
        self.assertEqual(a['events_without_request'],1);self.assertIsNone(a['null_fraction_of_requests'])
    def test_cross_boot_future_nan_order_rejected(self):
        for change in [{'fix_boot':'b2'},{'fix_ms':2000},{'accuracy_m':float('nan')},{'start_ms':999},{'end_ms':False}]:
            with self.subTest(change=change):
                d=fixture();d['requests'][0].update(change)
                with self.assertRaises(ValueError):audit(d)
    def test_duplicate_request_rejected(self):
        d=fixture();d['requests']*=2
        with self.assertRaises(ValueError):audit(d)
    def test_duplicate_shot_association_rejected(self):
        d=fixture();e=copy.deepcopy(d['events'][0]);e['event_id']='e2';d['events'].append(e)
        with self.assertRaises(ValueError):audit(d)
    def test_empty_is_not_zero_loss(self):
        self.assertIsNone(audit({'schema':1,'units':'elapsed_realtime_ms','events':[],'requests':[]})['shots_without_usable_fix'])
    def test_reboot_requires_new_namespace(self):
        d=fixture();r=d['requests'][0];r['boot']='b2'
        with self.assertRaises(ValueError):audit(d)
    def test_failures_are_not_nulls(self):
        for status in ['timeout','error','cancelled','interrupted']:
            d=fixture();r=d['requests'][0];r['status']=status
            for k in ['fix_ms','fix_boot','accuracy_m']:del r[k]
            a=audit(d);self.assertEqual(a['null_fraction_of_requests'],0)
            self.assertEqual(a['outcomes'][status],1)

if __name__=='__main__': unittest.main()
