import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from plan_lid_fixings import plan_side_fixings
class SpacingTests(unittest.TestCase):
 def test_current_order_uses_six_connections(self):
  p=plan_side_fixings(290,190,overhang=1.5);self.assertEqual(p['long_x'],[10.5,145,279.5]);self.assertEqual(p['short_y'],[]);self.assertEqual(p['connection_count'],6)
 def test_long_box_cannot_remain_three_per_row(self):
  p=plan_side_fixings(850,230,overhang=1.5);self.assertGreater(len(p['long_x']),3);self.assertTrue(p['short_y']);self.assertLessEqual(p['long_row_max_pitch_mm'],200);self.assertLessEqual(p['short_row_max_pitch_mm'],200)
 def test_rotation_and_boundaries(self):
  for a,b in [(100,100),(200,150),(221,190),(420,199),(1000,1000),(190,850)]:
   p=plan_side_fixings(a,b,overhang=1.5)
   for name,size in [('long_x',a),('short_y',b)]:
    x=p[name]
    self.assertTrue(all(0<v<size for v in x));self.assertEqual(x,sorted(set(x)));self.assertTrue(all(v-u<=200+1e-9 for u,v in zip(x,x[1:])))
 def test_manufacturing_entry_uses_planner(self):
  from build_golden_package import pipe_brief
  brief={'dimensions':{'length':850,'width':230,'height':200},'thickness':1,'material':'201','customer_requirement_text':'长箱按跨度布盖体连接孔','holes':[{'part_id':'LID','point':[425,115,200],'diameter':20}]}
  job=pipe_brief(brief,'SPACING');self.assertGreater(len(job['long_x']),3);self.assertTrue(job['short_y'])
  with self.assertRaises(SystemExit):pipe_brief(brief|{'long_x':[20,425,830]},'TOO-SPARSE')
 def test_invalid_parameters(self):
  for args in [(float('nan'),100),(20,100),(-1,100)]:
   with self.assertRaises(ValueError):plan_side_fixings(*args,overhang=1.5)
if __name__=='__main__':unittest.main()
