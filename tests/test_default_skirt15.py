import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_general_process import brief
from general_process import compile_brief,digest,validate_compiled_job
from derive_corner_candidate import derive
class DefaultSkirt15Tests(unittest.TestCase):
 def test_all_default_lids_remain15_across_thickness_and_structure(self):
  for dims in [(376,224,142),(142,120,275)]:
   for t in [.8,1.,1.2,1.5,2.,2.5]:
    b=brief(*dims,t=t);b.update(roof_ports={'mode':'none'},fixings={'mode':'none'});r=compile_brief(b);self.assertEqual(r['job']['lid']['skirt_height'],15.)
    row=next(x for x in r['parameter_sources'] if x['parameter']=='lid.skirt_height');self.assertEqual(row['origin'],'experience_default');self.assertTrue(row['needs_confirmation']);self.assertIn('Sentinel_a06b1b0204b8819192a24d11cae4cdc4',row['source'])
 def test_explicit_override_remains_exact(self):
  for value in [12.34,16.789,20.01]:
   b=brief();b['lid']={'skirt_height':value};j=compile_brief(b)['job'];self.assertEqual(j['lid']['skirt_height'],value)
 def test_default_unusable_geometry_yields_decision_not_automatic_raise(self):
  b=brief();b['process']={'Ri':14.};b['thickness']=2.;r=compile_brief(b);self.assertIsNone(r['job']);self.assertEqual(r['status'],'NEEDS_PROCESS_DECISION');row=next(x for x in r['parameter_sources'] if x['parameter']=='lid.skirt_height');self.assertEqual(row['value'],15.);self.assertFalse(r['adjustment_candidates'][0]['automatic_geometry_change'])
 def test_default_fixing_circle_not_fitting_straight_wall_yields_decision(self):
  b=brief(t=6.);b['roof_ports']={'mode':'none'};b['lid']={'corner_gap':.2};r=compile_brief(b);self.assertIsNone(r['job']);self.assertIn('FIXING',r['pending'][0]);self.assertEqual(next(x for x in r['parameter_sources'] if x['parameter']=='lid.skirt_height')['value'],15.)
 def test_thick_lid_corner_relief_is_computed_candidate_not_user_or_skirt_change(self):
  b=brief(t=2.);b.update(roof_ports={'mode':'none'},fixings={'mode':'none'});self.assertEqual(compile_brief(b)['job']['lid']['corner_gap'],.2);from derive_corner_candidate import derive;b=derive(b,'SYNTHETIC controlled CAD probe only');r=compile_brief(b);self.assertEqual(r['job']['lid']['skirt_height'],15.);self.assertEqual(r['job']['lid']['corner_gap'],.4);row=next(x for x in r['parameter_sources'] if x['parameter']=='lid.corner_gap');self.assertEqual(row['origin'],'calculated');self.assertTrue(row['needs_confirmation']);self.assertIn('CORNER_RELIEF_CANDIDATE_REQUIRES_CONFIRMATION',r['pending'])
 def test_explicit_corner_gap_never_silently_enlarged(self):
  b=brief(t=2.);b.update(roof_ports={'mode':'none'},fixings={'mode':'none'});b['lid']={'corner_gap':.2};self.assertEqual(compile_brief(b)['job']['lid']['corner_gap'],.2)
 def test_no_lid_does_not_get_lid15(self):
  b=brief();b.update(lid_required=False,height_basis='bare_body',roof_ports={'mode':'none'},fixings={'mode':'none'});r=compile_brief(b);self.assertNotIn('lid',r['job'])
 def candidate_baseline(self):
  b=brief(t=2.);b.update(roof_ports={'mode':'none'},fixings={'mode':'none'});return b
 def test_separate_candidate_binds_absent_and_empty_process_without_mutating_original(self):
  for explicit_empty in [False,True]:
   b=self.candidate_baseline()
   if explicit_empty:b['process']={}
   original=copy.deepcopy(b);child=derive(b,'SYNTHETIC candidate derivation, not physical qualification');r=compile_brief(child)
   self.assertEqual(b,original);self.assertEqual(child['process']['corner_relief_candidate']['baseline_brief_sha256'],digest(original));self.assertEqual(compile_brief(original)['job']['lid']['corner_gap'],.2);self.assertEqual(r['job']['lid']['corner_gap'],.4);self.assertEqual(r['effective_stage'],'confirmation_draft');self.assertFalse(r['production_release']);validate_compiled_job(r['job'])
 def test_candidate_binding_rejects_baseline_dimension_radius_or_skirt_drift(self):
  child=derive(self.candidate_baseline(),'SYNTHETIC controlled proposal')
  for field in ['dimension','radius','skirt']:
   changed=copy.deepcopy(child)
   if field=='dimension':changed['dimensions']['length']+=1
   elif field=='radius':changed['process']['Ri']=.81
   else:changed['lid']={'skirt_height':12.34}
   with self.assertRaisesRegex(ValueError,'CORNER_CANDIDATE_SCOPE'):compile_brief(changed)
 def test_candidate_binding_rejects_value_hash_original_and_blank_source_drift(self):
  child=derive(self.candidate_baseline(),'SYNTHETIC controlled proposal')
  for key,value in [('value_mm',.41),('baseline_brief_sha256','0'*64),('baseline_corner_gap_mm',.3),('source','   ')]:
   changed=copy.deepcopy(child);changed['process']['corner_relief_candidate'][key]=value
   with self.assertRaisesRegex(ValueError,'CORNER_CANDIDATE_SCOPE'):compile_brief(changed)
 def test_candidate_never_promoted_to_trial_despite_scoped_K_record(self):
  b=self.candidate_baseline();b['process']={'requested_stage':'trial','K_ANSI':.42,'K_evidence':{'kind':'documented_trial','reference':'SYNTHETIC scoped K record only','material':'201','thickness_mm':2.,'Ri_mm':.8,'K_ANSI':.42,'tool_reference':'SYNTHETIC tooling'}};r=compile_brief(derive(b,'SYNTHETIC corner proposal'))
  self.assertEqual(r['effective_stage'],'confirmation_draft');self.assertIn('CORNER_RELIEF_CANDIDATE_REQUIRES_CONFIRMATION',r['pending']);self.assertFalse(r['production_release']);self.assertIsNone(r['factory_record'])
 def test_requested_production_candidate_has_no_implicit_factory_record(self):
  b=self.candidate_baseline();b['process']={'requested_stage':'production_record'};r=compile_brief(derive(b,'SYNTHETIC corner proposal'))
  self.assertEqual(r['effective_stage'],'confirmation_draft');self.assertIn('FACTORY_FIRST_ARTICLE_ASSEMBLY_AND_SIGNED_RELEASE_RECORD_REQUIRED',r['pending']);self.assertIn('CORNER_RELIEF_CANDIDATE_REQUIRES_CONFIRMATION',r['pending']);self.assertIsNone(r['factory_record']);self.assertFalse(r['production_release'])
 def test_factory_claim_cannot_override_unconfirmed_corner_candidate(self):
  b=self.candidate_baseline();b['process']={'requested_stage':'production_record','K_ANSI':.42,'K_evidence':{'kind':'documented_trial','reference':'SYNTHETIC scoped K record only','material':'201','thickness_mm':2.,'Ri_mm':.8,'K_ANSI':.42,'tool_reference':'SYNTHETIC tooling'}};child=derive(b,'SYNTHETIC corner proposal');child['process']['factory_verification']={'test_claim_only':True};bound_baseline=copy.deepcopy(child);bound_baseline['process'].pop('corner_relief_candidate');child['process']['corner_relief_candidate']['baseline_brief_sha256']=digest(bound_baseline)
  with self.assertRaisesRegex(ValueError,'FACTORY_RECORD_CANNOT_OVERRIDE_UNRESOLVED'):compile_brief(child)
 def test_candidate_outside_adapter_is_decision_and_does_not_change_baseline(self):
  b=self.candidate_baseline();b['thickness']=2.5;original=copy.deepcopy(b);child=derive(b,'SYNTHETIC empirical formula; feasibility not proven');r=compile_brief(child)
  self.assertEqual(b,original);self.assertEqual(compile_brief(b)['job']['lid']['corner_gap'],.2);self.assertIsNone(r['job']);self.assertEqual(r['pending'],['CORNER_RELIEF_CANDIDATE_OUTSIDE_ADAPTER']);self.assertEqual(r['adjustment_candidates'][0]['default_skirt_mm'],15.);self.assertFalse(r['adjustment_candidates'][0]['automatic_geometry_change']);self.assertFalse(r['production_release'])
if __name__=='__main__':unittest.main()
