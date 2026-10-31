import unittest,sys,tempfile,json,copy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'));sys.path.insert(0,str(ROOT/'tests'))
from test_lid_defaults03 import new_demo,val,unknown
import test_lid_defaults03 as fixtures
from render_review_pdf import write_pdf,check_first_page
from corner03 import check_pdf_geometry,check_dxf,spec
from pypdf import PdfReader
class PDFPageOne(unittest.TestCase):
 def test_default_g_totals_and_unknown_q_on_first_page(self):
  d=new_demo();unknown(d['lid']['roof_gap'])
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'review.pdf';write_pdf(d,p);self.assertTrue(check_first_page(p,d));text=PdfReader(p).pages[0].extract_text();self.assertIn('单边g=0.5mm',text);self.assertIn('长向总差=1mm',text);self.assertIn('宽向总差=1mm',text);self.assertIn('独立参数，无默认',text)
 def test_explicit_g_one_prints_total_two_and_q_stays_independent(self):
  d=new_demo();val(d['lid'],'gap',1);val(d['lid'],'gap_basis','single_side');val(d['lid'],'roof_gap',.73)
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'review.pdf';write_pdf(d,p);text=PdfReader(p).pages[0].extract_text();self.assertIn('单边g=1mm',text);self.assertIn('长向总差=2mm',text);self.assertIn('0.73mm',text)
 def test_no_lid_g_is_not_applicable_in_pdf(self):
  d=new_demo();val(d['requirements'],'lid_required',False)
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'review.pdf';write_pdf(d,p);self.assertIn('本项目无盖',PdfReader(p).pages[0].extract_text());self.assertTrue(check_first_page(p,d))
 def test_stale_first_page_summary_rejected(self):
  d=new_demo()
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'review.pdf';write_pdf(d,p);val(d['lid'],'gap',1);val(d['lid'],'gap_basis','single_side');self.assertRaises(ValueError,check_first_page,p,d)
 def test_actual_pdf_vectors_match_DXF_and_wrong_map_is_rejected(self):
  d=new_demo();val(d['lid'],'corner_gap',.37,'assumed','trial')
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'flat.dxf';pdf=Path(t)/'review.pdf';s=spec(d);fixtures.Actual03Planar().make_dxf(p,s);actual=check_dxf(p,s);mapping=write_pdf(d,pdf,p);self.assertTrue(check_pdf_geometry(pdf,1,actual['outer_lines'],mapping['pdf_flat_map']));bad=mapping['pdf_flat_map'][:];bad[4]+=4;self.assertRaises(ValueError,check_pdf_geometry,pdf,1,actual['outer_lines'],bad)
if __name__=='__main__':unittest.main()
