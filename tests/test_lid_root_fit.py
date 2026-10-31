import copy,hashlib,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from design_job import resolve_job,project_for

def authorize_fixture(j):
 """Synthetic test evidence only; never customer/global authorization."""
 d=copy.deepcopy(j);d.pop('site_fit_acceptance',None)
 j['site_fit_acceptance']={'scope':'this_job_only','job_id':j['id'],'job_design_sha256':hashlib.sha256(json.dumps(d,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest(),'issue':'lid_root_interference','disposition':'site_fit_and_trial_assembly','authorization_source':'SYNTHETIC TEST FIXTURE: explicit simulated user acceptance, not a real customer','authorization_quote':'For this synthetic test job only retain dimensions and let the workshop fit and trial assemble the lid root.','authorized_by':'user','geometry_interference_eliminated':False,'trial_assembly_confirmed':False}
 return j

class LidRootFit(unittest.TestCase):
 def job(self,name='box-external.job.json'):return json.loads((ROOT/'assets/examples'/name).read_text())
 def project(self,j):
  with tempfile.TemporaryDirectory() as d:
   f=Path(d)/'job.json';f.write_text(json.dumps(j));return project_for(j,resolve_job(j),f,'20261022_1200','2026-10-22T12:00:00+08:00')
 def test_unaccepted_conflict_is_diagnostic_and_delivery_blocked_without_mutation(self):
  for n in ['box-external.job.json','box-wrap-l.job.json']:
   j=self.job(n);saved=copy.deepcopy(j);r=resolve_job(j)
   self.assertIn('fit',r);self.assertEqual(r['fit']['disposition'],'USER_REVIEW_REQUIRED')
   from site_fit import require_delivery_decision
   with self.assertRaisesRegex(ValueError,'LID_ROOT_FIT_REVIEW_REQUIRED'):require_delivery_decision(r)
   self.assertEqual(j,saved)
 def test_explicit_scoped_acceptance_does_not_change_q_g_or_height(self):
  j=authorize_fixture(self.job());r=resolve_job(j);self.assertIn('fit',r)
  from site_fit import require_delivery_decision
  require_delivery_decision(r);self.assertEqual((r['g'],r['q'],r['H']),(.5,0,100));self.assertEqual(r['fit']['disposition'],'AUTHORIZED_SITE_FIT_TRIAL_REQUIRED');self.assertFalse(r['fit']['geometry_interference_eliminated'])
 def test_scope_cannot_transfer_to_new_customer(self):
  j=authorize_fixture(self.job());j['id']='ANOTHER_CUSTOMER'
  with self.assertRaisesRegex(ValueError,'SITE_FIT'):resolve_job(j)
 def test_parameter_or_hole_change_invalidates_acceptance(self):
  for change in ['g','height','hole']:
   j=authorize_fixture(self.job())
   if change=='g':j['lid']['g']=.7
   elif change=='height':j['dimensions']['height']=101
   else:j['holes']=[{'id':'X','part_id':'LID','diameter':18,'point':[120,75,100],'axis':[0,0,1]}]
   with self.assertRaisesRegex(ValueError,'SITE_FIT'):resolve_job(j)
 def test_no_false_claim_of_elimination_or_trial(self):
  for k in ['geometry_interference_eliminated','trial_assembly_confirmed']:
   j=authorize_fixture(self.job());j['site_fit_acceptance'][k]=True
   with self.assertRaisesRegex(ValueError,'JOB_SCHEMA|SITE_FIT'):resolve_job(j)
 def test_missing_authorization_source_is_not_defaulted(self):
  j=authorize_fixture(self.job());j['site_fit_acceptance']['authorization_source']=''
  with self.assertRaisesRegex(ValueError,'JOB_SCHEMA|SITE_FIT'):resolve_job(j)
 def test_canonical_acceptance_is_scoped_and_preserves_positive_measurement(self):
  j=authorize_fixture(self.job());p=self.project(j)
  self.assertEqual(len(p['exceptions']),1);src=p['exceptions'][0]['authorization_source'];self.assertIn('SYNTHETIC TEST',next(s for s in p['provenance'] if s['id']==src)['ref'])
  p['lid']['root_overlap_volume']['value']=8.275862
  from site_fit import acceptance_from_project
  a=acceptance_from_project(p);self.assertIsNotNone(a)
  p['lid']['roof_gap']['value']=.2
  with self.assertRaisesRegex(ValueError,'SITE_FIT'):acceptance_from_project(p)
 def test_minimum_q_is_reported_as_tangency_only_not_auto_applied(self):
  r=resolve_job(self.job());self.assertIn('fit',r);self.assertAlmostEqual(r['fit']['minimum_q_ideal_tangency_mm'],.058380151290433724);self.assertEqual(r['q'],0)
 def test_no_lid_has_no_acceptance_and_no_fit_requirement(self):
  j=self.job();j['lid_required']=False;j.pop('lid');self.assertEqual(resolve_job(j).get('fit'),{'applicable':False})
  j=authorize_fixture(j)
  with self.assertRaisesRegex(ValueError,'SITE_FIT'):resolve_job(j)
 def test_nonintersecting_parameter_pair_needs_no_exception(self):
  j=self.job();j['lid']['roof_gap']=.2;r=resolve_job(j);self.assertIn('fit',r);self.assertTrue(r['fit']['analytic_feasible']);self.assertEqual(r['fit']['disposition'],'ACTUAL_GEOMETRY_CHECK_REQUIRED')
 def test_actual_overlap_requires_scope_and_cannot_accept_lower_skirt_collision(self):
  from site_fit import check_actual_overlap
  with self.assertRaisesRegex(ValueError,'REVIEW_REQUIRED'):check_actual_overlap(8.2,None,98,98)
  a=resolve_job(authorize_fixture(self.job()))['site_fit_acceptance']
  self.assertEqual(check_actual_overlap(8.2,a,98,98),'AUTHORIZED_SITE_FIT_TRIAL_REQUIRED')
  with self.assertRaisesRegex(ValueError,'below lid bend-root'):check_actual_overlap(8.2,a,90,98)
 def test_new_canonical_cut_cannot_accept_known_interference_without_user(self):
  from validate_project import validate
  p=self.project(self.job());codes={x['code'] for x in validate(p,'cut')['errors']}
  self.assertIn('LID_ROOT_FIT_REVIEW_REQUIRED',codes)
 def test_changed_project_scope_fails_even_model_check(self):
  from validate_project import validate
  p=self.project(authorize_fixture(self.job()));p['lid']['roof_gap']['value']=.2
  self.assertIn('SITE_FIT_SCOPE',{x['code'] for x in validate(p,'model')['errors']})

if __name__=='__main__':unittest.main()
