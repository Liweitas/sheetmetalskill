import copy,sys,unittest,tempfile,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from factory_naming import resolve,filename_map,published_root

class FactoryNamingTests(unittest.TestCase):
 def setUp(self):
  self.job={'material':'201','thickness':1.0};self.delivery={'namespace':'requirement','entity_id':'SYNTHETIC','revision':'R02'};self.request={'channel':'S','material':'201','thickness':'1.0','date':'2026/10/23','number':1,'factory_version':1,'source':'SYNTHETIC_FACTORY_ALLOCATION_NOT_BOX530'}
 def test_first_code_and_padding(self):self.assertEqual(resolve(self.request,self.job,self.delivery)['code'],'S-201-1.0-20261023-0001-v1')
 def test_factory_version_does_not_follow_R02(self):self.assertTrue(resolve(self.request,self.job,self.delivery)['code'].endswith('-v1'))
 def test_upgrade_preserves_first_five(self):
  previous=resolve(self.request,self.job,self.delivery)['code'];self.request.update(previous_code=previous,factory_version=2)
  self.assertEqual(resolve(self.request,self.job,self.delivery)['code'],previous[:-1]+'2')
 def test_upgrade_identity_change_or_same_version_rejected(self):
  previous=resolve(self.request,self.job,self.delivery)['code']
  for change in [{'date':'20261024'},{'number':2},{'factory_version':1}]:
   request={**self.request,'previous_code':previous,'factory_version':2,**change}
   with self.assertRaisesRegex(ValueError,'UPGRADE_KEEP_FIRST_FIVE'):resolve(request,self.job,self.delivery)
 def test_calendar_dates(self):
  for day in ['20260229','20261301','20260431']:
   with self.assertRaisesRegex(ValueError,'DATE_INVALID'):resolve({**self.request,'date':day},self.job,self.delivery)
  self.assertIn('20240229',resolve({**self.request,'date':'2024-02-29'},self.job,self.delivery)['code'])
 def test_missing_fields_stay_unnamed(self):
  r=resolve({'channel':'S'},self.job,self.delivery);self.assertIsNone(r['code']);self.assertEqual(r['status'],'UNNAMED_PENDING_CONFIRMATION');self.assertIn('number',r['missing_fields']);self.assertNotIn('0001',r['prefix'])
 def test_empty_UI_fields_do_not_create_formal_code(self):
  r=resolve({**self.request,'number':None,'date':''},self.job,self.delivery);self.assertIsNone(r['code']);self.assertIn('number',r['missing_fields']);self.assertIn('date',r['missing_fields'])
 def test_invalid_channels_numbers_versions(self):
  for field,values in [('channel',['A','s']),('number',[0,10000,True,'00000']),('factory_version',[0,-1,'2',True])]:
   for value in values:
    with self.assertRaises(ValueError):resolve({**self.request,field:value},self.job,self.delivery)
 def test_example_material_does_not_override_201(self):
  with self.assertRaisesRegex(ValueError,'MATERIAL_DIFFERS_SOURCE'):resolve({**self.request,'material':'Q235'},self.job,self.delivery)
 def test_wrong_thickness_rejected(self):
  with self.assertRaisesRegex(ValueError,'THICKNESS_DIFFERS_SOURCE'):resolve({**self.request,'thickness':'1.2'},self.job,self.delivery)
 def test_padded_decimal_canonical(self):self.assertIn('-1.0-',resolve({**self.request,'thickness':'1.00','number':'0001'},self.job,self.delivery)['code'])
 def test_cut_nest_process_preview_share_prefix_and_distinct_roles(self):
  names=['NEST/NEST_SHEET01.dxf','PDF/THREE_VIEWS.pdf','PDF/NEST_PREVIEW.pdf','DXF/U.dxf','BEND/U.dxf'];m={'artifacts':[{'path':n,'kind':k} for n,k in zip(names,['nest_dxf','pdf','nest_preview_pdf','dxf','bend_dxf'])]};code=resolve(self.request,self.job,self.delivery)['code'];mapping=filename_map(names,m,code)
  self.assertEqual(len(set(mapping.values())),5)
  for n in mapping.values():self.assertTrue(Path(n).name.startswith(code+'_'))
  for role in ['套料CUT','完整折弯工艺PDF','套料预览PDF']:self.assertTrue(any(role in n for n in mapping.values()))
 def test_version_upgrade_removes_previous_code_from_filename(self):
  old='S-201-1.0-20261023-0001-v1';new=old[:-1]+'2';p=old+'_套料CUT_NEST_SHEET01.dxf';result=filename_map([p],{'artifacts':[{'path':p,'kind':'nest_dxf'}]},new,old)[p];self.assertNotIn(old,result);self.assertTrue(result.startswith(new+'_套料CUT_'))
 def test_published_lookup_excludes_unpublished_stage(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);stage=root/'.R09-unpublished-engineering/x';stage.mkdir(parents=True);(stage/'DELIVERY_ENVELOPE_1.json').write_text('{}');final=root/'customer_T/revisions/CODE_R02';final.mkdir(parents=True);(final/'CODE_DELIVERY_ENVELOPE_1.json').write_text('{}');self.assertEqual(published_root(root),final)
 def test_published_lookup_never_guesses_between_versions(self):
  with tempfile.TemporaryDirectory() as td:
   for rev in ['v1','v2']:
    p=Path(td)/rev;p.mkdir();(p/'CODE_DELIVERY_ENVELOPE_1.json').write_text('{}')
   with self.assertRaisesRegex(ValueError,'EXPLICIT_PUBLISHED_REVISION'):published_root(td)
if __name__=='__main__':unittest.main()
