import contextlib,copy,io,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from delivery_contract import VERSION,WORKSHOP_CONTRACT,current_workshop_requirements,draw_nests,layout_parts,write_entities,parse_dxf,translate,pdf_nest_check

def sources(version=VERSION):
 return ({'project':{'revision':{'value':'v'+version}}},{'delivery_contract':version,'workshop_pdf_contract':WORKSHOP_CONTRACT},{'process_pdf':{'contract':WORKSHOP_CONTRACT}},{'package_version':version})

class CurrentWorkshopContractTests(unittest.TestCase):
 def test_current_three_source_versions_and_both_protocols_required(self):
  self.assertTrue(current_workshop_requirements(*sources()))
  for field in ['manifest','receipt']:
   p,m,s,r=sources()
   if field=='manifest':m.pop('workshop_pdf_contract')
   else:s['process_pdf'].pop('contract')
   with self.assertRaisesRegex(ValueError,'CURRENT_WORKSHOP_PROTOCOL_REQUIRED'):current_workshop_requirements(p,m,s,r)
 def test_legacy_protocol_cannot_replace_current_protocol(self):
  p,m,s,r=sources();s['process_pdf']['contract']='legacy'
  with self.assertRaisesRegex(ValueError,'CURRENT_WORKSHOP_PROTOCOL_REQUIRED'):current_workshop_requirements(p,m,s,r)
 def test_deleting_both_protocols_cannot_waive_current_source(self):
  p,m,s,r=sources();m.pop('workshop_pdf_contract');s['process_pdf']={}
  with self.assertRaisesRegex(ValueError,'CURRENT_WORKSHOP_PROTOCOL_REQUIRED'):current_workshop_requirements(p,m,s,r)
 def test_one_or_two_manufacturing_version_downgrades_rejected(self):
  for mask in range(1,7):
   p,m,s,r=sources()
   if mask&1:m['delivery_contract']='2.8.0-R11'
   if mask&2:p['project']['revision']['value']='v2.8.0-R11'
   if mask&4:r['package_version']='2.8.0-R11'
   with self.assertRaisesRegex(ValueError,'SOURCE_MANUFACTURING_VERSION_BINDING'):current_workshop_requirements(p,m,s,r)
 def test_legitimate_R10_R11_read_only_stay_legacy(self):
  for version in ['2.7.3-R10','2.8.0-R11']:
   p,m,s,r=sources(version);m.pop('workshop_pdf_contract');s['process_pdf']={}
   self.assertFalse(current_workshop_requirements(p,m,s,r,{}))
 def test_current_publisher_cannot_upgrade_legacy_manufacturing_claim(self):
  p,m,s,r=sources('2.8.0-R11');m.pop('workshop_pdf_contract');s['process_pdf']={}
  self.assertFalse(current_workshop_requirements(p,m,s,r,{'publisher_release':VERSION,'current_workshop_requirements_complete':False}))
  for claimed in [True,None,'false']:
   with self.assertRaisesRegex(ValueError,'ENVELOPE_SOURCE_STATE'):current_workshop_requirements(p,m,s,r,{'publisher_release':VERSION,'current_workshop_requirements_complete':claimed})
 def test_current_envelope_marker_cannot_be_deleted_or_lie(self):
  for envelope in [{},{'current_workshop_requirements_complete':False},{'current_workshop_requirements_complete':1}]:
   with self.assertRaisesRegex(ValueError,'ENVELOPE_SOURCE_STATE'):current_workshop_requirements(*sources(),envelope)
  self.assertTrue(current_workshop_requirements(*sources(),{'current_workshop_requirements_complete':True}))
 def test_prepare_legacy_message_reports_limit_instead_of_new_workshop_completion(self):
  import prepare_delivery_message as script
  gate={'fresh_CAD_checks_executed':True,'current_workshop_requirements_complete':False};buf=io.StringIO()
  with patch.object(sys,'argv',['prepare_delivery_message.py','/tmp/fixture']),patch.object(script,'check_envelope',return_value=gate),patch.object(script,'make_plan',return_value={'attachments':['whole.zip']}),patch.object(script,'check_plan',return_value={'ok':True}),contextlib.redirect_stdout(buf):script.main()
  result=json.loads(buf.getvalue());self.assertFalse(result['delivery_check']['current_workshop_requirements_complete']);self.assertIn('不代表已满足最新',result['delivery_check']['workshop_requirements_notice']);self.assertEqual(result['message_plan']['attachments'],['whole.zip'])
 def test_nest_pdf_chinese_material_stock_and_actual_part_dimensions(self):
  from pypdf import PdfReader
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);part=root/'part.dxf';points=[(0,0),(120,0),(120,80),(0,80),(0,0)];write_entities(part,[{'type':'LINE',10:a[0],20:a[1],11:b[0],21:b[1]} for a,b in zip(points,points[1:])]);stock={'length_mm':500,'width_mm':300,'edge_margin_mm':10,'part_gap_mm':10,'status':'assumed','source':'ENGLISH AUDIT SOURCE MUST STAY OUTSIDE WORKSHOP PDF'};layout=layout_parts({'U':part},{'sets':2,'stock':stock});nests={}
   for sheet in range(1,layout['required_sheets']+1):
    path=root/(str(sheet)+'.dxf');write_entities(path,[translate(e,*p['translation_mm']) for p in layout['placements'] if p['sheet']==sheet for e in parse_dxf(part)]);nests[sheet]=path
   project={'requirements':{'material':{'value':'201 stainless steel'},'nominal_t':{'value':1.2}}};pdf=root/'preview.pdf';maps=draw_nests(layout,nests,pdf,project,'SYNTHETIC');self.assertTrue(pdf_nest_check(pdf,layout,nests,maps,project,True));text=''.join(page.extract_text() for page in PdfReader(pdf).pages)
   for expected in ['201不锈钢','板厚 1.2','候选板幅，待确认','500×300','120×80','2件','板幅长 500','宽 300']:self.assertIn(expected,text)
   for forbidden in ['stainless steel','HOLD','ENGLISH AUDIT','assumed','CAM']:self.assertNotIn(forbidden,text)
   wrong=copy.deepcopy(project);wrong['requirements']['nominal_t']['value']=2.
   with self.assertRaisesRegex(ValueError,'CHINESE_METADATA_OR_ACTUAL_DIMENSIONS'):pdf_nest_check(pdf,layout,nests,maps,wrong,True)
if __name__=='__main__':unittest.main()
