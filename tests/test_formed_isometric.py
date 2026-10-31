import unittest,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
class FormedIsometric(unittest.TestCase):
 def test_isometric_basis_preserves_three_axes_and_does_not_flatten_height(self):
  self.assertTrue((ROOT/'scripts/formed_isometric.py').is_file(),'Default bending PDF lacks per-part actual formed isometric adapter')
  from formed_isometric import iso_point
  p=[iso_point(x) for x in [[0,0,0],[1,0,0],[0,1,0],[0,0,1]]]
  self.assertNotEqual(p[1],p[2]);self.assertNotEqual(p[3],p[0]);self.assertAlmostEqual(sum(v*v for v in p[1]),2/3)
 def test_missing_isometric_coverage_or_direction_is_rejected(self):
  self.assertTrue((ROOT/'scripts/formed_isometric.py').is_file())
  from formed_isometric import require_coverage
  parts={'U':{'actual_bends':2,'formed_sha256':'a'},'LID':{'actual_bends':4,'formed_sha256':'b'}}
  with self.assertRaisesRegex(ValueError,'ISOMETRIC'):require_coverage(parts,{})
  with self.assertRaisesRegex(ValueError,'ISOMETRIC'):require_coverage(parts,{'U':{'formed_sha256':'a','bend_labels':[]},'LID':{'formed_sha256':'b','bend_labels':[]}})
 def test_flat_b_label_must_link_to_actual_native_line_not_claimed_coordinate(self):
  import formed_isometric as m
  self.assertTrue(hasattr(m,'validate_flat_link'),'Native flat/identifier geometric linkage missing')
  lines=[[[0,1],[10,1]],[[0,5],[10,5]]]
  with self.assertRaisesRegex(ValueError,'BEND_FLAT_LINK'):m.validate_flat_link(lines,[{'id':'B1','flat_segments_mm':[[[0,8],[10,8]]]}])
  self.assertTrue(m.validate_flat_link(lines,[{'id':'B1','flat_segments_mm':[lines[0]]},{'id':'B2','flat_segments_mm':[lines[1]]}]))
 def test_bend_table_uses_same_id_and_native_axis_as_flat_marker(self):
  import formed_isometric as m
  self.assertTrue(hasattr(m,'bend_note'),'B table has a separate inconsistent numbering path')
  self.assertEqual(m.bend_note({'id':'B3','flat_line_mm':[[15,2],[15,100]]},2),'B3: X=15.000000000  zone +/-1.000000000')
if __name__=='__main__':unittest.main()
