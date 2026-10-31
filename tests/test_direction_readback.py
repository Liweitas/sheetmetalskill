import copy,unittest,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
class ActualDirection(unittest.TestCase):
 def fixture(self):
  actual={'native_signed_angle_deg':-90.,'native_direction':'DOWN','formed_point_mm':[20,1,1],'axis':[1,0,0],'segments':[[[0,19],[40,19]]]}
  claim={'id':'B1','root_face':1,'root_skin_normal':[0,-1,0],'direction':'DOWN','angle_signed_deg':-90.,'source_formed_point_mm':[20,1,1],'source_formed_axis':[1,0,0],'flat_segments_mm':[[[0,19],[40,19]]]}
  return actual,claim
 def test_synchronous_UP_plus90_claim_cannot_override_actual_DOWN_minus90(self):
  p=ROOT/'scripts/native_direction_readback.py';self.assertTrue(p.exists(),'No actual native angle comparator')
  from native_direction_readback import compare_claims
  a,c=self.fixture();self.assertTrue(compare_claims([a],[c],1,[0,-1,0]))
  c.update(direction='UP',angle_signed_deg=90.)
  with self.assertRaisesRegex(ValueError,'NATIVE_DIRECTION'):compare_claims([a],[c],1,[0,-1,0])
 def test_root_axis_or_flat_link_change_is_not_an_angle_evidence_substitute(self):
  self.assertTrue((ROOT/'scripts/native_direction_readback.py').exists())
  from native_direction_readback import compare_claims
  for key,value in [('root_skin_normal',[0,1,0]),('source_formed_axis',[0,0,1]),('flat_segments_mm',[[[0,25],[40,25]]])]:
   a,c=self.fixture();c[key]=value
   with self.assertRaisesRegex(ValueError,'NATIVE_DIRECTION'):compare_claims([a],[c],1,[0,-1,0])
class InterferenceAuthority(unittest.TestCase):
 def test_authority_and_pair_sum_are_distinct_and_display_has_declared_precision(self):
  self.assertTrue((ROOT/'scripts/interference_volume.py').exists(),'No shared measurement/display contract')
  from interference_volume import measurement,display_volume
  m=measurement(2.0190650778320265,2.019099125183112)
  self.assertEqual(m['authoritative_volume_mm3'],2.0190650778320265)
  self.assertAlmostEqual(m['pair_sum_minus_authority_mm3'],.00003404735108558654)
  self.assertEqual(display_volume(m['authoritative_volume_mm3']),'2.019065')
if __name__=='__main__':unittest.main()
