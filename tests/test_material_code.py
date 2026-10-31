import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from factory_naming import resolve
class MaterialCodeTests(unittest.TestCase):
 def setUp(self):
  self.d={'namespace':'requirement','entity_id':'SYNTHETIC_MAPPING','revision':'R01'}
  self.j={'material':'201 stainless steel','thickness':1.}
  self.r={'channel':'S','material_code':'201','thickness':1,'date':'20261023','number':23,'factory_version':1,'source':'SYNTHETIC_FACTORY_TEST_ONLY'}
 def mapping(self,source='201 stainless steel',code='201'):
  return {'source_description':source,'code':code,'confirmed':True,'source':'SYNTHETIC explicit material-code confirmation, not real factory allocation'}
 def test_confirmed_201_description_maps_without_source_mutation(self):
  before=copy.deepcopy(self.j);r=resolve({**self.r,'material_mapping':self.mapping()},self.j,self.d);self.assertEqual(r['code'],'S-201-1.0-20261023-0023-v1');self.assertEqual(self.j,before);self.assertEqual(r['material_identity']['source_description'],self.j['material']);self.assertEqual(r['material_identity']['confirmation_source'],self.mapping()['source'])
 def test_304_and_Q235_known_descriptions(self):
  for source,code in [('304 stainless steel','304'),('Q235 carbon steel','Q235')]:
   j={**self.j,'material':source};r=resolve({**self.r,'material_code':code,'material_mapping':self.mapping(source,code)},j,self.d);self.assertIn('-'+code+'-',r['code'])
 def test_no_confirmation_is_pending_not_formal(self):
  for mapping in [None,{},dict(self.mapping(),confirmed=False),dict(self.mapping(),source='')]:
   req={**self.r}
   if mapping is not None:req['material_mapping']=mapping
   r=resolve(req,self.j,self.d);self.assertIsNone(r['code']);self.assertIn('material_mapping',r['missing_fields'])
 def test_missing_serial_still_pending_after_material_confirmation(self):
  req={**self.r,'material_mapping':self.mapping()};req.pop('number');r=resolve(req,self.j,self.d);self.assertIsNone(r['code']);self.assertIn('number',r['missing_fields'])
 def test_unknown_and_ambiguous_descriptions_not_guessed(self):
  for src in ['unknown steel','201 / 304 stainless steel','304L stainless steel','Q235B carbon steel']:
   j={**self.j,'material':src}
   with self.assertRaisesRegex(ValueError,'UNRECOGNIZED_DESCRIPTION'):resolve({**self.r,'material_mapping':self.mapping(src)},j,self.d)
 def test_known_grade_conflicts_rejected_even_with_confirmation(self):
  with self.assertRaisesRegex(ValueError,'MATERIAL_DIFFERS_SOURCE'):resolve({**self.r,'material_code':'304','material_mapping':self.mapping(code='304')},self.j,self.d)
 def test_mapping_bound_to_exact_source_and_code(self):
  for mapping in [self.mapping('201 stainless steel '),self.mapping(code='304')]:
   with self.assertRaisesRegex(ValueError,'MAPPING_SCOPE'):resolve({**self.r,'material_mapping':mapping},self.j,self.d)
 def test_two_code_fields_cannot_conflict(self):
  with self.assertRaisesRegex(ValueError,'MATERIAL_CODE_CONFLICT'):resolve({**self.r,'material':'304','material_mapping':self.mapping()},self.j,self.d)
 def test_legacy_exact_code_outputs_unchanged(self):
  req={**self.r,'material':'201'};req.pop('material_code');r=resolve(req,{**self.j,'material':'201'},self.d);self.assertEqual(r['code'],'S-201-1.0-20261023-0023-v1');self.assertNotIn('material_identity',r)
 def test_exact_new_code_does_not_require_description_translation(self):
  r=resolve(self.r,{**self.j,'material':'201'},self.d);self.assertEqual(r['material_identity']['method'],'exact_source_code')
 def test_unknown_source_not_promoted(self):
  r=resolve(self.r,{**self.j,'material':None},self.d);self.assertIsNone(r['code']);self.assertIn('source_material_confirmation',r['missing_fields'])
 def test_upgrade_keeps_material_code_and_identity(self):
  req={**self.r,'material_mapping':self.mapping()};first=resolve(req,self.j,self.d);up=resolve({**req,'previous_code':first['code'],'factory_version':2},self.j,self.d);self.assertEqual(first['material_identity'],up['material_identity']);self.assertEqual(first['code'][:-1]+'2',up['code'])
if __name__=='__main__':unittest.main()
