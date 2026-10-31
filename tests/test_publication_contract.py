import copy,json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from publication_contract import CONTRACT,RELEASE,signals,check
from delivery_dispatch import make_plan,CONTRACT as DISPATCH,sha

class PublicationTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)/'customer_T/revisions/S-201-1.0-20261023-0007-v1_R01';self.root.mkdir(parents=True)
  (self.root/'complete.zip').write_bytes(b'fixture');(self.root/'spec.json').write_text(json.dumps({'delivery':{'namespace':'customer','entity_id':'T','revision':'R01'}}))
  self.manifest={'delivery_contract':'2.7.1-R08','publication_contract':CONTRACT,'publisher_release':RELEASE,'artifacts':[{'path':'spec.json','kind':'delivery_spec','sha256':sha(self.root/'spec.json')}]}
  self.envelope={'zip':'complete.zip','zip_sha256':sha(self.root/'complete.zip'),'naming':{'record':'NAMING.json'},'publication_contract':CONTRACT,'publisher_release':RELEASE,'message_dispatch_contract':DISPATCH}
  self.record={'publication_contract':CONTRACT,'publisher_release':RELEASE,'source_manufacturing_contract':'2.7.1-R08'};self.save_record();self.envelope['final_message_plan']=make_plan(self.root,self.envelope,manifest=self.manifest)
 def save_record(self):(self.root/'NAMING.json').write_text(json.dumps(self.record))
 def test_retained_R08_manufacturing_contract_cannot_waive_dispatch(self):
  e=copy.deepcopy(self.envelope);e.pop('final_message_plan');e.pop('message_dispatch_contract')
  with self.assertRaisesRegex(ValueError,'DISPATCH_REQUIRED_PUBLISHED'):check(self.root,e,self.manifest)
 def test_current_publication_binds_three_sources(self):
  dispatch,pub=check(self.root,self.envelope,self.manifest);self.assertEqual(pub['source_manufacturing_contract'],'2.7.1-R08');self.assertEqual(dispatch['attachment_count'],1)
 def test_legitimate_R10_exact_code_read_only_compatibility(self):
  e=copy.deepcopy(self.envelope);m=copy.deepcopy(self.manifest);record=copy.deepcopy(self.record)
  for item in [e,m,record]:item['publisher_release']='2.7.3-R10'
  record['request']={'material':'201'};record['resolved']={'code':'S-201-1.0-20261023-0007-v1'};(self.root/'NAMING.json').write_text(json.dumps(record))
  self.assertEqual(check(self.root,e,m)[1]['publisher_release'],'2.7.3-R10')
 def test_material_mapping_cannot_claim_R10_publisher(self):
  e=copy.deepcopy(self.envelope);m=copy.deepcopy(self.manifest);record=copy.deepcopy(self.record)
  for item in [e,m,record]:item['publisher_release']='2.7.3-R10'
  record['request']={'material_code':'201'};(self.root/'NAMING.json').write_text(json.dumps(record))
  with self.assertRaisesRegex(ValueError,'MATERIAL_MAPPING_REQUIRES'):check(self.root,e,m)
 def test_one_contract_or_release_downgrade_rejected(self):
  for obj in ['envelope','manifest','record']:
   for key in ['publication_contract','publisher_release']:
    e=copy.deepcopy(self.envelope);m=copy.deepcopy(self.manifest);record=copy.deepcopy(self.record)
    {'envelope':e,'manifest':m,'record':record}[obj][key]='OLD'
    (self.root/'NAMING.json').write_text(json.dumps(record))
    with self.assertRaisesRegex(ValueError,'PUBLICATION_CONTRACT_BINDING'):check(self.root,e,m)
  self.save_record()
 def test_all_markers_erased_still_requires_current_publication(self):
  e=copy.deepcopy(self.envelope);m=copy.deepcopy(self.manifest);record=copy.deepcopy(self.record)
  for obj in [e,m,record]:obj.pop('publication_contract');obj.pop('publisher_release')
  (self.root/'NAMING.json').write_text(json.dumps(record))
  with self.assertRaisesRegex(ValueError,'PUBLICATION_CONTRACT_BINDING'):check(self.root,e,m)
  self.assertEqual(check(self.root,e,m,allow_legacy_publication=True)[1]['mode'],'LEGACY_NAMED_INPUT_REQUIRES_REPUBLICATION')
 def test_legacy_upgrade_input_also_requires_plan(self):
  e=copy.deepcopy(self.envelope);e.pop('final_message_plan')
  with self.assertRaisesRegex(ValueError,'DISPATCH_REQUIRED_PUBLISHED'):check(self.root,e,self.manifest,allow_legacy_publication=True)
 def test_erased_naming_and_markers_cannot_hide_named_layout(self):
  e=copy.deepcopy(self.envelope);m=copy.deepcopy(self.manifest)
  for obj in [e,m]:obj.pop('publication_contract');obj.pop('publisher_release')
  e.pop('naming');e.pop('final_message_plan');e.pop('message_dispatch_contract')
  self.assertTrue(signals(self.root,e,m))
  with self.assertRaisesRegex(ValueError,'DISPATCH_REQUIRED_PUBLISHED'):check(self.root,e,m)
 def test_raw_R08_read_only_compatibility(self):
  raw=Path(self.temp.name)/'legacy/customer_T/revisions/R01';raw.mkdir(parents=True)
  result=check(raw,{'zip':'customer_T_R01_DELIVERY.zip'},{'delivery_contract':'2.7.1-R08','artifacts':[]});self.assertIsNone(result[0]);self.assertEqual(result[1]['mode'],'LEGACY_UNPUBLISHED_READ_ONLY')
 def test_manufacturing_contract_lie_is_not_publication_upgrade(self):
  m=copy.deepcopy(self.manifest);m['delivery_contract']='2.7.0-R07'
  with self.assertRaisesRegex(ValueError,'PUBLICATION_SOURCE_MANUFACTURING_CONTRACT'):check(self.root,self.envelope,m)
if __name__=='__main__':unittest.main()
