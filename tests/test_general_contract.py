import copy,hashlib,json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_general_process import brief
from general_process import compile_brief
from design_job import resolve_job,project_for
from bend_dxf import write,compare,read
from delivery_contract import check_envelope

class GeneralContractTests(unittest.TestCase):
 def test_existing_step_is_not_silently_replaced_with_rectangular_model(self):
  b=brief();b.update(shape='existing_step',shape_reference='SYNTHETIC actual STEP required, no file generated here');r=compile_brief(b);self.assertIsNone(r['job']);self.assertEqual(r['status'],'UNSUPPORTED_SHAPE_REQUIRES_ADAPTER')
 def test_small_roof_cannot_receive_default_reference_ports(self):
  b=brief(40,35,30,1);self.assertEqual(compile_brief(b)['job']['holes'],[])  # v2.8.2 default: no roof ports
  b['roof_ports']={'mode':'two_reference'}
  with self.assertRaisesRegex(ValueError,'PORT_LAYOUT_LIMIT'):compile_brief(b)
 def test_invalid_units_and_negative_thickness_not_guessed(self):
  for field,val in [('units','unknown'),('thickness',-1)]:
   b=brief();b[field]=val
   with self.assertRaisesRegex(ValueError,'BRIEF_SCHEMA'):compile_brief(b)
 def test_calculated_structure_and_default03_not_customer_confirmation(self):
  j=compile_brief(brief())['job'];p=project_for(j,resolve_job(j),__file__,'TEST','2026-10-23T00:00:00+08:00')
  for field in [p['fabrication']['method'],p['lid']['corner_scheme'],p['bending']['Ri']]:self.assertEqual(field['status'],'assumed')
 def test_bend_native_fragments_cannot_be_scaled_duplicated_or_mixed_with_cut(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'bend.dxf';segs=[[[1,2],[5,2]],[[1,9],[5,9]]];write(p,segs);compare(p,segs)
   with self.assertRaises(ValueError):compare(p,[[[2,4],[10,4]],[[2,18],[10,18]]])
   write(p,[segs[0],segs[0]])
   with self.assertRaises(ValueError):compare(p,segs)
   write(p,segs);p.write_text(p.read_text().replace('BEND','CUT'))
   with self.assertRaises(ValueError):read(p)
 def test_bend_units_cannot_be_unknown(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'x.dxf';write(p,[[[0,0],[1,0]]]);p.write_text(p.read_text().replace('$INSUNITS\n70\n4','$INSUNITS\n70\n0'))
   with self.assertRaises(ValueError):read(p)
 def test_review_dossier_cannot_use_complete_manufacturing_gate(self):
  with tempfile.TemporaryDirectory() as d:
   (Path(d)/'X_GENERAL_REVIEW_STATUS.json').write_text('{}')
   with self.assertRaisesRegex(ValueError,'GENERAL_CONFIRMATION_ONLY'):check_envelope(d)
 def factory_brief(self):
  b=brief();b.update(roof_ports={'mode':'none'},fixings={'mode':'none'});b['process']={'requested_stage':'production_record','K_ANSI':.42,'K_evidence':{'kind':'documented_trial','reference':'SYNTHETIC_TEST_ONLY','material':'201','thickness_mm':1.2,'Ri_mm':.8,'K_ANSI':.42,'tool_reference':'SYNTHETIC_TEST_TOOL'}}
  c=compile_brief(b);j=c['job'];r=resolve_job(j);hb=r['H']-r['t']-r['q']
  rec={'physical_design_sha256':c['physical_design_sha256'],'first_article_passed':True,'assembly_fit_passed':True,'tool_access_and_sequence_verified':True,'production_authorized_by_factory':True,'verified_date':'2026-10-23','material':'201','measured_thickness_mm':1.2,'thickness_tolerance_mm':.05,'measured_Ri_mm':.8,'Ri_tolerance_mm':.1,'body_outer_mm':[r['L'],r['W'],hb],'body_outer_mm_tolerance':[.1]*3,'assembly_outer_mm':[r['L']+3.4,r['W']+3.4,r['H']],'assembly_outer_mm_tolerance':[.1]*3,'records':[{'reference':f'SYNTHETIC_{i}','content':f'SYNTHETIC record {i}','sha256':hashlib.sha256(f'SYNTHETIC record {i}'.encode()).hexdigest()} for i in range(2)]}
  for key in ['signed_by','authorization_source','material_batch','machine_reference','upper_tool_reference','lower_tool_reference']:rec[key]='SYNTHETIC_TEST_ONLY'
  b['process']['factory_verification']=rec;return b
 def test_scoped_supplied_factory_records_not_automatic_release(self):
  c=compile_brief(self.factory_brief());self.assertEqual(c['effective_stage'],'factory_signed_production_record');self.assertFalse(c['production_release']);self.assertFalse(c['factory_record']['automatic_software_production_release'])
 def test_factory_records_wrong_scope_missing_documents_and_measurements_rejected(self):
  for change in ['scope','docs','measurement']:
   b=self.factory_brief();r=b['process']['factory_verification']
   if change=='scope':r['physical_design_sha256']='0'*64
   if change=='docs':r['records']=[]
   if change=='measurement':r['body_outer_mm'][0]+=10
   with self.assertRaises(ValueError):compile_brief(b)
if __name__=='__main__':unittest.main()
