import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_general_process import brief
from general_process import compile_brief,validate_compiled_job
class ExplicitPrecisionTests(unittest.TestCase):
 def test_explicit_skirt_not_rounded_up_to_tenth(self):
  for value in [12.01,12.099,12.1,12.299999999,12.34,19.9999]:
   b=brief();b['lid']={'skirt_height':value};r=compile_brief(b);self.assertEqual(r['job']['lid']['skirt_height'],value);row=next(x for x in r['parameter_sources'] if x['parameter']=='lid.skirt_height');self.assertEqual(row['value'],value);self.assertEqual(row['origin'],'user');self.assertEqual(r['job']['general_process']['brief']['lid']['skirt_height'],value)
 def test_explicit_skirt_unit_conversion_has_no_tenth_quantization(self):
  b=brief(37.6,22.4,14.2,.12);b['units']='cm';b['lid']={'skirt_height':1.234};self.assertAlmostEqual(compile_brief(b)['job']['lid']['skirt_height'],12.34,places=12)
 def test_explicit_other_dimensions_retained(self):
  b=brief(377.1234,225.4321,143.2345,1.07321);b['process']={'Ri':.834567,'K_ANSI':.41337,'seam_gap':.01234,'end_inset':.23456};b['lid']={'g':.56789,'roof_gap':.23456,'corner_gap':.12345,'skirt_height':12.34567};j=compile_brief(b)['job']
  for key in ['Ri','K_ANSI','seam_gap','end_inset']:self.assertEqual(j[key],b['process'][key])
  self.assertEqual(j['lid']['skirt_height'],b['lid']['skirt_height'])
  for key in ['g','roof_gap','corner_gap']:self.assertEqual(j['lid'][key],b['lid'][key])
  self.assertEqual(j['thickness'],b['thickness']);self.assertEqual(j['dimensions'],b['dimensions'])
 def test_only_default_skirt_is_user_general_default15(self):
  b=brief(376,224,142.34);r=compile_brief(b);self.assertAlmostEqual(r['job']['lid']['skirt_height'],15.);row=next(x for x in r['parameter_sources'] if x['parameter']=='lid.skirt_height');self.assertEqual(row['origin'],'experience_default')
 def test_explicit_numeric_sources_are_current_input_not_default_policy(self):
  b=brief();b['process']={'Ri':.83,'K_ANSI':.41337,'seam_gap':.01234,'end_inset':.23456};b['lid']={'g':.56,'roof_gap':.234,'corner_gap':.123,'skirt_height':12.34,'corner_scheme':'03'};r=compile_brief(b)
  for key in ['Ri','K_ANSI','seam_gap','end_inset','lid.g','lid.roof_gap','lid.corner_gap','lid.skirt_height','lid.corner_scheme']:
   row=next(x for x in r['parameter_sources'] if x['parameter']==key);self.assertEqual(row['origin'],'user');self.assertEqual(row['source'],'current brief',key)
 def test_old_rounded_value_cannot_remain_claimed_explicit(self):
  b=brief();b['lid']={'skirt_height':12.34};j=compile_brief(b)['job'];j['lid']['skirt_height']=12.4
  with self.assertRaisesRegex(ValueError,'COMPILED_INPUT_AUTHORITY'):validate_compiled_job(j)
if __name__=='__main__':unittest.main()
