import copy,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from source_contract import config_for,delivery_state,CONFIG_SCHEMA
class ExistingSTEPContract(unittest.TestCase):
 def report(self,status='BLOCKED',bop=True,K=None):
  return {'CAD_audit_complete':True,'solid_count':1,'config':{'material':None,'K_ANSI':K},'parts':[{'id':'SOLID_01','BOP':{'ok':bop},'bends':[{}],'unfold':{'status':status}}],'intersections':[]}
 def test_empty_source_config_leaves_material_and_k_unknown(self):
  c=config_for({});self.assertIsNone(c['material']);self.assertIsNone(c['K_ANSI']);self.assertFalse(c['diagnose_invalid']);self.assertFalse(c['try_non_design_repair'])
 def test_unknown_k_is_not_an_opted_diagnostic(self):self.assertNotIn('diagnostic_K_ANSI',config_for({}))
 def test_diagnostic_k_never_becomes_manufacturing_k(self):
  c=config_for({'diagnostic_K_ANSI':.5});self.assertIsNone(c['K_ANSI']);self.assertEqual(c['diagnostic_K_ANSI'],.5)
 def test_explicit_k_requires_source_and_status(self):
  for c in [{'K_ANSI':.4},{'K_ANSI':.4,'K_source':'estimate'},{'K_ANSI':.4,'K_source':'estimate','K_status':'confirmed'}]:
   with self.assertRaises(ValueError):config_for(c)
 def test_engineering_k_status_preserved(self):
  c=config_for({'K_ANSI':.4,'K_source':'trial estimate','K_status':'assumed'});self.assertEqual(c['K_status'],'assumed')
 def test_material_cannot_come_from_filename_alone(self):
  with self.assertRaises(ValueError):config_for({'material':'stainless'})
 def test_nonfinite_and_excessive_retries_rejected(self):
  for c in [{'diagnostic_K_ANSI':float('nan')},{'max_root_attempts':10}]:
   with self.assertRaises(ValueError):config_for(c)
 def test_structure_or_gap_edits_not_options(self):
  for c in [{'split_frame':True},{'method':'u_external_ends'},{'lid':{'g':.5}},{'corner_scheme':'03'},{'tolerance':.1}]:
   with self.assertRaises(ValueError):config_for(c)
 def test_diagnostic_flat_keeps_partial(self):
  r=delivery_state(self.report('DIAGNOSTIC_ONLY',False));self.assertEqual(r['status'],'PARTIAL_HOLD');self.assertFalse(r['geometry_delivery_complete']);self.assertFalse(r['manufacturing_delivery_complete']);self.assertFalse(r['production_release'])
 def test_known_k_does_not_fix_missing_flat(self):self.assertEqual(delivery_state(self.report(K=.4))['status'],'PARTIAL_HOLD')
 def test_every_source_piece_must_be_checked(self):
  j=self.report('GEOMETRY_CHECKED_WITH_HOLD',True,.4);j['solid_count']=2;self.assertFalse(delivery_state(j)['geometry_delivery_complete'])
 def test_bop_failure_does_not_pass_from_flat_validity(self):self.assertFalse(delivery_state(self.report('GEOMETRY_CHECKED_WITH_HOLD',False,.4))['geometry_delivery_complete'])
 def test_complete_geometry_still_not_manufacturing_release(self):
  j=delivery_state(self.report('GEOMETRY_CHECKED_WITH_HOLD',True,.4));self.assertEqual(j['status'],'AUDIT_COMPLETE_WITH_HOLD');self.assertFalse(j['manufacturing_delivery_complete']);self.assertFalse(j['production_release'])
 def test_distributed_source_schema_matches_entry(self):self.assertEqual(json.loads((ROOT/'references/source-audit.schema.json').read_text()),CONFIG_SCHEMA)
 def test_formed_review_keeps_unknown_material_and_k(self):
  from design_job import resolve_job
  job=json.loads((ROOT/'assets/examples/box-external.job.json').read_text());job['material']=None;job['K_ANSI']=None
  r=resolve_job(job,review_only=True);self.assertIsNone(r['K_ANSI'])
  with self.assertRaises(ValueError):resolve_job(job)
 def test_review_reject_existing_directory_without_writing(self):
  import tempfile,subprocess
  with tempfile.TemporaryDirectory() as td:
   dest=Path(td);sentinel=dest/'keep.txt';sentinel.write_text('preserve')
   result=subprocess.run([sys.executable,str(ROOT/'scripts/review_box.py'),'not-a-job','--output',str(dest)],capture_output=True)
   self.assertEqual(result.returncode,2);self.assertEqual(list(dest.iterdir()),[sentinel]);self.assertEqual(sentinel.read_text(),'preserve')
if __name__=='__main__':unittest.main()
