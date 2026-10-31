import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from general_process import compile_brief,validate_compiled_job
from design_job import resolve_job

def brief(L=376,W=224,H=142,t=1.2):return {'input_contract':'general-process-v1','id':'SYNTHETIC_GENERAL','units':'mm','dimension_basis':'outer','height_basis':'including_lid','lid_required':True,'material':'201','thickness':t,'dimensions':{'length':L,'width':W,'height':H}}
class GeneralProcessTests(unittest.TestCase):
 def test_minimal_design_gets_transparent_defaults(self):
  r=compile_brief(brief());self.assertEqual(r['job']['holes'],[])  # v2.8.2: no unrequested roof holes
  b=brief();b['roof_ports']={'mode':'two_reference'};r=compile_brief(b);j=r['job'];self.assertEqual(j['Ri'],.8);self.assertEqual(j['lid']['g'],.5);self.assertEqual(j['end_inset'],0.0);self.assertEqual(j['seam_gap'],0);self.assertEqual(len(j['holes']),2);self.assertEqual(r['effective_stage'],'confirmation_draft');self.assertGreater(j['lid']['roof_gap'],0);self.assertFalse(r['production_release']);resolve_job(j)
 def test_explicit_no_holes_and_no_fixings_override(self):
  b=brief();b.update(roof_ports={'mode':'none'},fixings={'mode':'none'});r=compile_brief(b);self.assertEqual(r['job']['holes'],[]);self.assertNotIn('fixings',r['job']);self.assertEqual(resolve_job(r['job'])['holes'],[])
 def test_multiple_aspects_select_current_structure(self):
  for dims,expected in [((376,224,142),'u_external_ends'),((145,132,286),'u_wrap_bottom_l'),((94,74,58),'u_external_ends')]:self.assertEqual(compile_brief(brief(*dims))['job']['method'],expected)
 def test_customer_override_wins(self):
  b=brief();b['structure']='u_wrap_bottom_l';b['process']={'Ri':1.4,'end_inset':0};b['lid']={'g':.7,'roof_gap':.3,'skirt_height':19,'corner_gap':.1};j=compile_brief(b)['job'];self.assertEqual(j['method'],'u_wrap_bottom_l');self.assertEqual(j['Ri'],1.4);self.assertEqual(j['lid']['skirt_height'],19)
 def test_inner_size_and_bare_height_conversion(self):
  b=brief(300,180,100,t=1);b.update(dimension_basis='inner',height_basis='bare_body');r=compile_brief(b);j=r['job'];self.assertEqual(j['dimensions']['length'],302);self.assertEqual(j['dimensions']['width'],182);self.assertAlmostEqual(j['dimensions']['height']-j['thickness']-j['lid']['roof_gap'],101)
 def test_unit_equivalence(self):
  a=brief();b=brief(37.6,22.4,14.2,.12);b['units']='cm';ja=compile_brief(a)['job'];jb=compile_brief(b)['job'];self.assertEqual(ja['dimensions'],jb['dimensions']);self.assertEqual(ja['thickness'],jb['thickness'])
 def test_missing_essential_input_does_not_guess_thickness_or_units(self):
  for key in ['thickness','units','height_basis']:
   b=brief();b.pop(key);r=compile_brief(b);self.assertIsNone(r['job']);self.assertIn(key,r['missing'])
 def test_missing_dimension_reports_without_CAD(self):
  b=brief();b['dimensions'].pop('height');r=compile_brief(b);self.assertIn('dimensions.height',r['missing'])
 def test_explicit_zero_q_not_silently_changed_or_site_fit_accepted(self):
  b=brief();b['lid']={'roof_gap':0};r=compile_brief(b);self.assertEqual(r['route'],'formed_confirmation');self.assertEqual(r['job']['lid']['roof_gap'],0);self.assertNotIn('site_fit_acceptance',r['job']);self.assertGreater(r['adjustment_candidates'][0]['candidate_q_mm'],0)
 def test_compiled_claims_cannot_drift(self):
  j=compile_brief(brief())['job'];j['general_process']['effective_stage']='evidence_based_trial'
  with self.assertRaisesRegex(ValueError,'COMPILED_INPUT_AUTHORITY'):resolve_job(j)
 def test_geometry_value_cannot_drift_from_original_brief(self):
  j=compile_brief(brief())['job'];j['dimensions']['length']=530
  with self.assertRaisesRegex(ValueError,'COMPILED_INPUT_AUTHORITY'):resolve_job(j)
 def test_current_profile_does_not_copy_530_hole_positions(self):
  _p=lambda x:{**x,'roof_ports':{'mode':'two_reference'}};a=compile_brief(_p(brief(376,224,142)))['job'];b=compile_brief(_p(brief(622,308,195)))['job'];self.assertNotEqual([h['point'] for h in a['holes']],[h['point'] for h in b['holes']])
 def test_handles_are_opt_in_and_centers_computed(self):
  b=brief(622,308,195);b['handles']={'mode':'auto'};j=compile_brief(b)['job'];self.assertEqual(j['handles']['centers'],[[622/3,154],[622*2/3,154]]);self.assertEqual(len(resolve_job(j)['mounting_patterns']),2)
 def test_trial_requires_scoped_compensation_record(self):
  b=brief();b.update(roof_ports={'mode':'none'},fixings={'mode':'none'});b['process']={'requested_stage':'trial','K_ANSI':.42,'K_evidence':{'kind':'documented_trial','reference':'SYNTHETIC trial record','material':'201','thickness_mm':1.2,'Ri_mm':.8,'K_ANSI':.42,'tool_reference':'SYNTHETIC tooling'}};r=compile_brief(b);self.assertEqual(r['effective_stage'],'evidence_based_trial');self.assertFalse(r['production_release'])
 def test_K_record_cannot_transfer_material_or_radius(self):
  b=brief();b['process']={'K_evidence':{'kind':'documented_trial','reference':'TEST','material':'304','thickness_mm':1.2,'Ri_mm':1,'K_ANSI':.4,'tool_reference':'TEST'}}
  with self.assertRaisesRegex(ValueError,'EVIDENCE_SCOPE'):compile_brief(b)
 def test_production_label_cannot_appear_without_physical_records(self):
  b=brief();b['process']={'requested_stage':'production_record'};r=compile_brief(b);self.assertEqual(r['effective_stage'],'confirmation_draft');self.assertIn('FACTORY_FIRST_ARTICLE_ASSEMBLY_AND_SIGNED_RELEASE_RECORD_REQUIRED',r['pending'])
 def test_irregular_shape_is_explicit_adapter_boundary(self):
  b=brief();b['shape']='irregular';r=compile_brief(b);self.assertEqual(r['status'],'UNSUPPORTED_SHAPE_REQUIRES_ADAPTER');self.assertIsNone(r['job'])
if __name__=='__main__':unittest.main()
