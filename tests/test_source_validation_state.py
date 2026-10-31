import unittest,sys,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from validate_source_manifest import state_errors,exact
from source_contract import delivery_state
class SourceStateCrosscheck(unittest.TestCase):
 def setUp(self):self.state={'status':'PARTIAL_HOLD','geometry_delivery_complete':False,'manufacturing_delivery_complete':False,'production_release':False,'checked_parts':['SOLID_01'],'diagnostic_parts':['SOLID_03'],'holds':[{'part':'SOLID_02','code':'UNFOLD_BLOCKED','reason':'Wire is not closed'}],'audit_completed':True}
 def test_independent_false_geometry_and_coverage_case(self):
  bad=copy.deepcopy(self.state);bad.update(geometry_delivery_complete=True,checked_parts=['SOLID_01','SOLID_02','SOLID_03'],diagnostic_parts=[],holds=[]);errors=state_errors(bad,self.state,'Manifest');self.assertEqual(len(errors),4)
 def test_independent_final_result_release_case(self):
  bad=copy.deepcopy(self.state);bad.update(status='AUDIT_COMPLETE_WITH_HOLD',geometry_delivery_complete=True,manufacturing_delivery_complete=True,production_release=True);self.assertEqual(len(state_errors(bad,self.state,'AUDIT_RESULT')),4)
 def test_boolean_integer_and_string_not_equivalent(self):
  self.assertFalse(exact(False,0));self.assertFalse(exact(True,1));self.assertFalse(exact(False,'false'))
 def test_missing_derived_fields_are_not_optional(self):self.assertEqual(len(state_errors({},self.state,'Manifest')),len(self.state))
 def test_blocked_summary_carries_real_native_error(self):
  p={'id':'SOLID_02','BOP':{'ok':True},'bends':[{}],'unfold':{'status':'BLOCKED','attempts':[{'root_face':18,'error':'Wire is not closed'}]}}
  state=delivery_state({'version':'2.5.1-R04','CAD_audit_complete':True,'solid_count':1,'config':{'material':None,'K_ANSI':None},'parts':[p],'intersections':[]});self.assertIn('Face18: Wire is not closed',state['holds'][0]['reason'])
if __name__=='__main__':unittest.main()
