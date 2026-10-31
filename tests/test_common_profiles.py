import unittest,json,sys,tempfile,copy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from design_job import resolve_job,project_for
from validate_project import validate
class CommonReviewProfiles(unittest.TestCase):
 def setUp(self):self.job=json.loads((ROOT/'assets/examples/common-460-review.job.json').read_text());self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'job.json'
 def tearDown(self):self.temp.cleanup()
 def project(self):
  self.path.write_text(json.dumps(self.job));r=resolve_job(self.job);return project_for(self.job,r,self.path,'20261021_2100','2026-10-21T21:00:00+08:00')
 def test_common_profile_28_holes_10_pairs_2_handles(self):
  r=resolve_job(self.job);self.assertEqual(len(r['holes']),28);self.assertEqual(len(r['fixing_pairs']),10);self.assertEqual(len(r['mounting_patterns']),2)
 def test_wide_rows_face_center_along_y_and_spacing_along_x(self):
  r=resolve_job(self.job);h={x['id']:x for x in r['holes']}
  for name,wide_x,narrow_x in [('H1',133,103),('H2',327,357)]:
   self.assertEqual(h[name+'-W1']['point'],[wide_x,87.5,170]);self.assertEqual(h[name+'-W2']['point'],[wide_x,172.5,170]);self.assertEqual(h[name+'-N1']['point'],[narrow_x,99,170]);self.assertEqual(h[name+'-N2']['point'],[narrow_x,161,170])
 def test_long_and_short_fixing_positions(self):
  r=resolve_job(self.job);h={x['id']:x for x in r['holes']}
  self.assertEqual([h['F-front-'+str(i)+'-B']['point'][0] for i in range(1,4)],[40,230,420])
  self.assertEqual([h['F-left-'+str(i)+'-B']['point'][1] for i in range(1,3)],[40,220])
  self.assertEqual({x['point'][2] for x in r['holes'] if x.get('fixing_pair')},{160})
 def test_selected_profiles_are_candidates_not_manufacturing_standards(self):
  p=self.project();self.assertEqual(p['bending']['K_value']['status'],'assumed');self.assertEqual(p['lid']['corner_gap']['status'],'assumed');self.assertTrue(p['handles']['enabled']['value']);self.assertEqual(p['handles']['narrow_row_pitch']['status'],'assumed');self.assertTrue(validate(p,'model')['ok'])
  body=next(g for g in p['hole_groups'] if g['id']=='F-front-1-B');cover=next(g for g in p['hole_groups'] if g['id']=='F-front-1-C');self.assertEqual(body['type']['value'],'tap_drill');self.assertEqual(body['laser_size']['magnitude']['value'],3.3);self.assertEqual(cover['laser_size']['magnitude']['value'],4.5)
 def test_end_inset_is_not_axial_gap(self):
  p=self.project();self.assertEqual(p['fabrication']['end_inset']['value'],0.0);self.assertEqual(p['fabrication']['seam_gap']['value'],0);self.assertFalse(p['fabrication']['end_top_flush']['value'])
 def test_no_opt_in_unknown_k_remains_blocked(self):
  self.job.pop('workflow_profile')
  with self.assertRaisesRegex(ValueError,'JOB_SCHEMA'):resolve_job(self.job)
 def test_profile_candidates_cannot_be_promoted_by_provenance(self):
  self.job['input_provenance']={'K_ANSI':{'status':'confirmed','source':'pretend approval'}}
  with self.assertRaisesRegex(ValueError,'must remain assumed'):self.project()
 def test_explicit_engineering_status_and_reference_are_retained(self):
  self.job['K_ANSI']=.5;self.job['lid']['corner_gap']=0;self.job['input_provenance']={'K_ANSI':{'status':'assumed','source':'Agent neutral axis midpoint, not calibrated'},'/lid/corner_gap':{'status':'assumed','source':'Diagnostic zero seam'}}
  p=self.project();self.assertEqual(p['bending']['K_value']['value'],.5);self.assertEqual(p['bending']['K_value']['status'],'assumed');source=p['bending']['K_value']['source'][0];self.assertEqual(next(s for s in p['provenance'] if s['id']==source)['ref'],'Agent neutral axis midpoint, not calibrated')
 def test_unsourced_job_numbers_are_not_client_confirmations(self):
  self.job['K_ANSI']=.5;p=self.project();self.assertEqual(p['bending']['K_value']['status'],'assumed');self.assertEqual(p['requirements']['dimensions']['X']['status'],'requested')
 def test_engineering_kind_cannot_claim_confirmation(self):
  self.job['K_ANSI']=.5;self.job['input_provenance']={'K_ANSI':{'status':'confirmed','source_kind':'engineering_assumption','source':'Agent estimate'}}
  with self.assertRaisesRegex(ValueError,'Engineering assumptions'):self.project()
 def test_selected_trial_profile_does_not_add_unrequested_mounts(self):
  self.job.pop('handles');self.job.pop('fixings');r=resolve_job(self.job);self.assertFalse(r['mounting_patterns']);self.assertFalse(r['fixing_pairs']);self.assertFalse(r['holes'])
 def test_fixings_cannot_create_unrequested_lid(self):
  self.job['lid_required']=False;self.job.pop('lid');self.job.pop('handles')
  with self.assertRaisesRegex(ValueError,'cannot add an unrequested lid'):resolve_job(self.job)
 def test_public_raw_schema_accepts_opted_null_candidates(self):
  from jsonschema import Draft202012Validator
  from design_job import JOB_SCHEMA
  self.assertFalse(list(Draft202012Validator(JOB_SCHEMA).iter_errors(self.job)))
  self.job.pop('workflow_profile');self.assertTrue(list(Draft202012Validator(JOB_SCHEMA).iter_errors(self.job)))
 def test_bundled_job_schema_matches_entry(self):
  from design_job import JOB_SCHEMA
  self.assertEqual(json.loads((ROOT/'references/job.schema.json').read_text()),JOB_SCHEMA)
if __name__=='__main__':unittest.main()
