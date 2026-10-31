import copy,tempfile,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from delivery_contract import envelope_authority
from pdf_dimension_authority import check_printed_three_views
class ReceiptAuthorityTests(unittest.TestCase):
 def setUp(self):
  self.project={'project':{'quantity_sets':{'value':2}}};self.spec={'delivery':{'sets':2,'stock':{'status':'assumed'}}};self.layout={'sets':2,'required_sheets':3};self.final={'status':'GEOMETRY_CHECKED_WITH_HOLD'};self.bom=[{'part_id':'U','quantity':2},{'part_id':'LID','quantity':2}];self.envelope={'sets':2,'required_stock_sheets':3,'stock_status':'assumed','engineering_status':'GEOMETRY_CHECKED_WITH_HOLD','PDF_visual_review_required':True,'independent_review':'PENDING'}
 def test_source_quantities_agree(self):self.assertEqual(envelope_authority(self.envelope,self.project,self.spec,self.layout,self.final,self.bom)['input_sets'],2)
 def test_envelope_999_not_source2(self):
  self.envelope['sets']=999
  with self.assertRaisesRegex(ValueError,'sets.*999.*2'):envelope_authority(self.envelope,self.project,self.spec,self.layout,self.final,self.bom)
 def test_board_count_not_self_reported(self):
  self.envelope['required_stock_sheets']=999
  with self.assertRaisesRegex(ValueError,'required_stock_sheets'):envelope_authority(self.envelope,self.project,self.spec,self.layout,self.final,self.bom)
 def test_quantity_string_not_accepted(self):
  self.envelope['sets']='2'
  with self.assertRaises(ValueError):envelope_authority(self.envelope,self.project,self.spec,self.layout,self.final,self.bom)
 def test_source_layout_quantity_disagrees(self):
  self.layout['sets']=999
  with self.assertRaisesRegex(ValueError,'INPUTS_DISAGREE'):envelope_authority(self.envelope,self.project,self.spec,self.layout,self.final,self.bom)
 def pdf(self,root,numbers):
  from reportlab.pdfgen.canvas import Canvas
  p=root/'view.pdf';cv=Canvas(str(p));cv.drawString(40,800,'U - ACTUAL EXPORTED STEP THREE VIEWS')
  for i,v in enumerate(numbers):cv.drawString(40,760-i*30,format(v,'.6f')+' mm')
  cv.save();return p
 def test_actual_STEP_dimensions_accept_correct_labels(self):
  with tempfile.TemporaryDirectory() as td:
   p=self.pdf(Path(td),[218,94,148,94,218,148]);self.assertIn('U',check_printed_three_views(p,{'U':{'bbox_mm':[0,0,0,218,148,94]}}))
 def test_vectors_unchanged_but_wrong_dimension_text_rejected(self):
  with tempfile.TemporaryDirectory() as td:
   p=self.pdf(Path(td),[999,888,94]*2)
   with self.assertRaisesRegex(ValueError,'ACTUAL_STEP_DIMENSION_LABEL_MISMATCH'):check_printed_three_views(p,{'U':{'bbox_mm':[0,0,0,218,148,94]}})
 def test_front_right_axis_swap_is_not_same_dimension_contract(self):
  with tempfile.TemporaryDirectory() as td:
   p=self.pdf(Path(td),[148,94,218,94,218,148])
   with self.assertRaisesRegex(ValueError,'ACTUAL_STEP_DIMENSION_LABEL_MISMATCH'):check_printed_three_views(p,{'U':{'bbox_mm':[0,0,0,218,148,94]}})
if __name__=='__main__':unittest.main()
