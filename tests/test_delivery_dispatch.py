import copy,json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from delivery_dispatch import make_plan,check_plan,sha

class DispatchTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)/'customer_T/revisions/R01';self.root.mkdir(parents=True)
  for n in ['complete.zip','part.step','view.pdf','confirm.png']:(self.root/n).write_bytes(n.encode())
  self.d={'namespace':'customer','entity_id':'T','revision':'R01'};self.e={'zip':'complete.zip','zip_sha256':sha(self.root/'complete.zip')};self.m={'artifacts':[{'path':n,'kind':k,'sha256':sha(self.root/n)} for n,k in [('part.step','step_part'),('view.pdf','pdf'),('confirm.png','confirmation_png')]]}
 def plan(self,**kw):return make_plan(self.root,self.e,self.d,self.m,**kw)
 def check(self,p):return check_plan(self.root,p,self.e,self.d,self.m)
 def evidence(self,paths,reason='explicit_single_files'):
  return {'reason':reason,'quote':'用户明确要求本次选定单件（合成测试）','source':'SYNTHETIC_TEST_ONLY','current_for_this_delivery':True,'scope':{**self.d,'archive_sha256':self.e['zip_sha256']},'requested_paths':paths}
 def test_default_one_complete_zip(self):
  p=self.plan();self.assertEqual(self.check(p)['attachment_count'],1);self.assertEqual(p['messages'][0]['attachments'][0]['path'],'complete.zip')
 def test_default_zip_plus_pdf_rejected(self):
  with self.assertRaisesRegex(ValueError,'DEFAULT_ONE_COMPLETE_ZIP'):self.plan(selected=['complete.zip','view.pdf'])
 def test_default_individual_step_rejected(self):
  with self.assertRaisesRegex(ValueError,'DEFAULT_ONE_COMPLETE_ZIP'):self.plan(selected=['part.step'])
 def test_second_message_scatter_rejected(self):
  p=self.plan();p['messages'].append({'attachments':[{'path':'view.pdf','kind':'pdf','sha256':sha(self.root/'view.pdf')}]})
  with self.assertRaisesRegex(ValueError,'DEFAULT_ONE_COMPLETE_ZIP'):self.check(p)
 def test_explicit_single_file_exception(self):
  p=self.plan(selected=['view.pdf'],user_request=self.evidence(['view.pdf']));self.assertEqual(self.check(p)['mode'],'USER_REQUESTED_INDIVIDUAL_FILES')
 def test_confirmation_first_is_not_final(self):
  p=self.plan(phase='confirmation',selected=['confirm.png'],user_request=self.evidence(['confirm.png'],'confirmation_first'));self.assertFalse(self.check(p)['final_message_plan_checked'])
 def test_confirmation_cannot_include_manufacturing_parts(self):
  with self.assertRaisesRegex(ValueError,'CONFIRMATION_ONLY'):self.plan(phase='confirmation',selected=['part.step'],user_request=self.evidence(['part.step'],'confirmation_first'))
 def test_old_other_revision_request_rejected(self):
  a=self.evidence(['view.pdf']);a['scope']['revision']='OLD'
  with self.assertRaisesRegex(ValueError,'USER_REQUEST_SCOPE'):self.plan(selected=['view.pdf'],user_request=a)
 def test_evidence_and_currentness_required(self):
  for field,value in [('quote',''),('source',''),('current_for_this_delivery',False)]:
   a=self.evidence(['view.pdf']);a[field]=value
   with self.assertRaises(ValueError):self.plan(selected=['view.pdf'],user_request=a)
 def test_selected_files_match_actual_request(self):
  with self.assertRaisesRegex(ValueError,'USER_REQUEST_SCOPE'):self.plan(selected=['part.step'],user_request=self.evidence(['view.pdf']))
 def test_missing_or_changed_attachment_rejected(self):
  p=self.plan();(self.root/'complete.zip').unlink()
  with self.assertRaisesRegex(ValueError,'ATTACHMENT_BYTES'):self.check(p)
 def test_false_identity_or_archive_rejected(self):
  for field in ['entity_id','archive_sha256']:
   p=self.plan();p[field]='FALSE'
   with self.assertRaisesRegex(ValueError,'WRONG_IDENTITY'):self.check(p)
 def test_extra_attachment_fields_cannot_hide_scatter(self):
  p=self.plan();p['extra_attachments']=['view.pdf']
  with self.assertRaisesRegex(ValueError,'PLAN_FIELDS'):self.check(p)
 def test_missing_plan_field_rejected(self):
  p=self.plan();p.pop('messages')
  with self.assertRaisesRegex(ValueError,'PLAN_FIELDS'):self.check(p)
if __name__=='__main__':unittest.main()
