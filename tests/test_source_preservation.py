import unittest,json,tempfile,subprocess,sys,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class SourceOutputProtection(unittest.TestCase):
 def test_validation_output_and_resolved_aliases_leave_input_unchanged(self):
  data=(ROOT/'assets/examples/demo-b.lid-clinch.json').read_bytes()
  with tempfile.TemporaryDirectory() as t:
   source=Path(t)/'project.json';source.write_bytes(data)
   for flag in ['--output','--resolved-output']:
    p=subprocess.run([sys.executable,str(ROOT/'scripts/validate_project.py'),str(source),flag,str(source)],capture_output=True);self.assertEqual(p.returncode,2);self.assertEqual(source.read_bytes(),data)
 def test_hardlink_alias_is_blocked(self):
  data=(ROOT/'assets/examples/demo-b.lid-clinch.json').read_bytes()
  with tempfile.TemporaryDirectory() as t:
   source=Path(t)/'project.json';source.write_bytes(data);alias=Path(t)/'alias.json';os.link(source,alias);p=subprocess.run([sys.executable,str(ROOT/'scripts/validate_project.py'),str(source),'--output',str(alias)],capture_output=True);self.assertEqual(p.returncode,2);self.assertEqual(source.read_bytes(),data)
 def test_two_output_artifacts_cannot_collide(self):
  with tempfile.TemporaryDirectory() as t:
   source=Path(t)/'project.json';data=(ROOT/'assets/examples/demo-b.lid-clinch.json').read_bytes();source.write_bytes(data);target=Path(t)/'two.json';p=subprocess.run([sys.executable,str(ROOT/'scripts/validate_project.py'),str(source),'--output',str(target),'--resolved-output',str(target)],capture_output=True);self.assertEqual(p.returncode,2);self.assertFalse(target.exists());self.assertEqual(source.read_bytes(),data)
 def test_pdf_and_native_report_cannot_overwrite_source_before_CAD_execution(self):
  with tempfile.TemporaryDirectory() as t:
   source=Path(t)/'project.json';data=(ROOT/'assets/examples/demo-b.lid-clinch.json').read_bytes();source.write_bytes(data)
   for script,args in [('render_review_pdf.py',[]),('native03_check.py',['--formed',str(source),'--unfold',str(source),'--dxf',str(source),'--body',str(source)])]:
    p=subprocess.run([sys.executable,str(ROOT/'scripts'/script),str(source),*args,'--output',str(source)],capture_output=True);self.assertEqual(p.returncode,2);self.assertEqual(source.read_bytes(),data)
if __name__=='__main__':unittest.main()
