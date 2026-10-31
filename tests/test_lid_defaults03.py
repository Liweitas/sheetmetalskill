import unittest,json,copy,sys,math,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from create_intake import build,apply_lid_defaults
from migrate_project import migrate
from validate_project import validate,parameter_hash
from corner03 import profile,spec,check_dxf

def val(d,k,x,status='confirmed',source='user'):
 d[k].update(value=x,status=status,source=[source],note='SYNTHETIC test input')
def unknown(f):f.update(value=None,status='unknown',source=[],note=None)
def example():return json.loads((ROOT/'assets/examples/demo-b.lid-clinch.json').read_text())
def new_demo():
 d=example();val(d['project'],'record_kind','new','confirmed','policy-timezone')
 for k in ['gap','gap_basis','gap_datum','corner_scheme']:unknown(d['lid'][k])
 return d
class ConditionalDefaults(unittest.TestCase):
 def test_unfilled_new_lid_gets_half_per_side_total_one(self):
  d=new_demo();before=copy.deepcopy(d);x=apply_lid_defaults(d);self.assertEqual(d,before);self.assertEqual(x['lid']['gap']['value'],.5);self.assertEqual(x['lid']['gap_basis']['value'],'single_side');self.assertEqual(x['lid']['gap']['status'],'default');self.assertEqual(x['lid']['corner_scheme']['value'],'03');a=validate(d,'model');self.assertTrue(a['ok'],a['errors']);self.assertEqual(a['computed']['lid_gap_total_length_mm'],1);self.assertEqual(a['computed']['lid_gap_total_width_mm'],1)
 def test_explicit_single_one_is_preserved(self):
  d=new_demo();val(d['lid'],'gap',1);val(d['lid'],'gap_basis','single_side');x=apply_lid_defaults(d);self.assertEqual(x['lid']['gap']['value'],1);self.assertEqual(x['lid']['gap']['source'],['user']);self.assertEqual(validate(d,'model')['computed']['lid_gap_total_width_mm'],2)
 def test_explicit_total_one_is_half_each_side(self):
  d=new_demo();val(d['lid'],'gap',1);val(d['lid'],'gap_basis','total');self.assertEqual(validate(d,'model')['computed']['lid_gap_each_side_mm'],.5)
 def test_missing_value_with_explicit_total_basis_defaults_total_one(self):
  d=new_demo();val(d['lid'],'gap_basis','total');x=apply_lid_defaults(d);self.assertEqual(x['lid']['gap']['value'],1);self.assertEqual(x['lid']['gap']['status'],'default')
 def test_default_source_cannot_be_mislabeled_single_one(self):
  d=apply_lid_defaults(new_demo());d['lid']['gap']['value']=1;self.assertIn('DEFAULT_GAP_VALUE',{x['code'] for x in validate(d,'model')['errors']})
 def test_q_unknown_stays_unknown_and_explicit_q_is_not_overwritten(self):
  d=new_demo();unknown(d['lid']['roof_gap']);self.assertIsNone(apply_lid_defaults(d)['lid']['roof_gap']['value']);self.assertIn('ROOF_Q_UNKNOWN',{x['code'] for x in validate(d,'model')['holds']});val(d['lid'],'roof_gap',.73);self.assertEqual(apply_lid_defaults(d)['lid']['roof_gap']['value'],.73)
 def test_no_lid_intake_is_not_applicable(self):
  _,d=build(False);self.assertEqual(d['lid']['gap']['status'],'not_applicable');self.assertIsNone(d['lid']['gap']['value']);self.assertEqual(d['lid']['corner_scheme']['status'],'not_applicable')
 def test_unknown_scope_has_declared_policy_not_active_fit(self):
  _,d=build();self.assertIsNone(d['lid']['gap']['value']);self.assertEqual(d['policies']['lid_gap_single_side']['value'],.5);self.assertIsNone(d['requirements']['lid_required']['value'])
 def test_existing_record_does_not_acquire_new_default(self):
  d=example();unknown(d['lid']['gap']);unknown(d['lid']['corner_scheme']);x=apply_lid_defaults(d);self.assertIsNone(x['lid']['gap']['value']);self.assertIsNone(x['lid']['corner_scheme']['value'])
 def test_existing_explicit_values_survive_migration(self):
  d=example();d['schema_version']='2.0.0';d.pop('policies');d['project'].pop('record_kind');val(d['lid'],'gap',1);val(d['lid'],'roof_gap',.19);x=migrate(d);self.assertEqual(x['project']['record_kind']['value'],'existing');self.assertEqual(x['lid']['gap'],d['lid']['gap']);self.assertEqual(x['lid']['roof_gap'],d['lid']['roof_gap'])
 def test_corner_override_is_not_overwritten(self):
  d=new_demo();val(d['lid'],'corner_scheme','customer-other-corner');self.assertEqual(apply_lid_defaults(d)['lid']['corner_scheme']['value'],'customer-other-corner')
 def test_no_default_ri_corner_seam_or_roof_q(self):
  _,d=build(True);self.assertIsNone(d['bending']['Ri']['value']);self.assertIsNone(d['lid']['corner_gap']['value']);self.assertIsNone(d['lid']['roof_gap']['value'])
 def test_positive_root_interference_stays_hold_despite_g_half(self):
  d=new_demo();val(d['lid'],'root_check_passed',True,'measured','step');val(d['lid'],'root_overlap_volume',.12,'measured','step');val(d['lid'],'root_check_ref','SYNTHETIC actual-check assertion');a=validate(d,'model');self.assertIn('LID_ROOT_INTERFERENCE',{x['code'] for x in a['holds']});self.assertFalse(validate(d,'release')['ok'])
 def test_resolved_and_unresolved_new_contract_hash_agree(self):
  d=new_demo();self.assertEqual(parameter_hash(d),parameter_hash(apply_lid_defaults(d)))
class Actual03Planar(unittest.TestCase):
 def make_dxf(self,path,s,right_angle=False):
  # Independent rectangular cross blank, four mirrored03 chains; all inputs fictional.
  A=s['A'];B=s['B'];P=s['P1'];Q=s['P2'];T=s['P3'];L,W=s['flat_size'];lower=[(P[0],0),(L-P[0],0),(L-P[0],A),(L-Q[0],Q[1]),(L-T[0],T[1]),(L,T[1]),(L,W-T[1]),(L-T[0],W-T[1]),(L-Q[0],W-Q[1]),(L-P[0],W-A),(L-P[0],W),(P[0],W),(P[0],W-A),(Q[0],W-Q[1]),(T[0],W-T[1]),(0,W-T[1]),(0,T[1]),(T[0],T[1]),(Q[0],Q[1]),(P[0],A)]
  if right_angle:
   #20 nonzero axis-parallel edges, not03 even if a filename/JSON calls it03.
   lower=[(0,0),(2,0),(4,0),(6,0),(8,0),(10,0),(10,2),(10,4),(10,6),(10,8),(10,10),(8,10),(6,10),(4,10),(2,10),(0,10),(0,8),(0,6),(0,4),(0,2)]
  pairs=[(0,'SECTION'),(2,'HEADER'),(9,'$INSUNITS'),(70,4),(0,'ENDSEC'),(0,'SECTION'),(2,'ENTITIES')]
  for a,b in zip(lower,lower[1:]+lower[:1]):pairs +=[(0,'LINE'),(8,'CUT'),(10,a[0]),(20,a[1]),(11,b[0]),(21,b[1])]
  pairs +=[(0,'ENDSEC'),(0,'EOF')];path.write_text('\n'.join(str(v) for pair in pairs for v in pair)+'\n')
 def sample(self):
  d=new_demo();val(d['lid'],'corner_gap',.37,'assumed','trial');return spec(d)
 def test_profile_recalculates_t_ri_seam_and_uses_corrected_third_point(self):
  p=profile(1.4,1.1,11,.27,2.63);self.assertAlmostEqual(p['P3'][1],p['B']-1.1+.27);self.assertNotAlmostEqual(p['P3'][1],p['B']+1.1-1.4-.27);q=profile(1.8,1.3,12,.31,3.1);self.assertNotEqual(p,q)
 def test_no_seam_is_invented_for03_spec(self):
  d=new_demo();self.assertRaises(ValueError,spec,d)
 def test_actual_two_slopes_per_corner_accepts_recomputed_outline(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'synthetic.dxf';s=self.sample();self.make_dxf(p,s);self.assertEqual(check_dxf(p,s)['actual_sloped_edges'],8)
 def test_claimed03_twenty_axis_edges_zero_slopes_is_rejected(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'claimed03.dxf';s=self.sample();self.make_dxf(p,s,True);self.assertRaises(ValueError,check_dxf,p,s)
 def test_stale_geometry_after_t_or_Ri_change_is_rejected(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'stale.dxf';s=self.sample();self.make_dxf(p,s);d=new_demo();val(d['lid'],'corner_gap',.37,'assumed','trial');val(d['bending'],'Ri',2.4,'assumed','trial');self.assertRaises(ValueError,check_dxf,p,spec(d))
if __name__=='__main__':unittest.main()
