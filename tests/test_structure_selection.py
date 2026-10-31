import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from select_structure import select_structure as choose

class StructureSelectionTests(unittest.TestCase):
    def test_greater(self):
        self.assertEqual(choose(200, 100, 150)['selected_method'], 'u_external_ends')
    def test_equal(self):
        self.assertEqual(choose(150, 100, 150)['selected_method'], 'u_external_ends')
    def test_less(self):
        r = choose(100, 120, 150)
        self.assertEqual(r['selected_method'], 'u_wrap_bottom_l')
        self.assertEqual(r['sheet_parts_with_requested_lid'], 3)
    def test_swap_all_boundaries(self):
        for L,W,H in [(200,100,150), (150,100,150), (100,120,150)]:
            self.assertEqual(choose(L,W,H), dict(choose(W,L,H), dimensions_mm=[float(L),float(W),float(H)]))
    def test_unit_normalization(self):
        self.assertEqual(choose(67,24,15,'cm'), choose(670,240,150,'mm'))
        self.assertEqual(choose('0.15','0.1','0.15','m')['comparison'], '>=')
        self.assertEqual(choose('1','0.5','1','inch')['comparison'], '>=')
    def test_four_requested_cases(self):
        for dims in [(670,240,150),(460,260,170),(280,175,155),(310,200,185)]:
            with self.subTest(dims=dims):
                r=choose(*dims)
                self.assertEqual(r['selected_method'],'u_external_ends')
                self.assertEqual(r['sheet_parts_with_requested_lid'],4)
                self.assertFalse(r['production_released'])
                self.assertEqual(r['manufacturability'],'not_evaluated')
    def test_existing_untouched(self):
        self.assertIsNone(choose(670,240,150,record_kind='existing')['selected_method'])
    def test_explicit_wins_for_new_and_existing(self):
        for kind in ['new','existing']:
            self.assertEqual(choose(670,240,150,record_kind=kind,explicit_method='u_wrap_bottom_l')['selected_method'],'u_wrap_bottom_l')
    def test_body_only_does_not_add_lid(self):
        r=choose(670,240,150,lid_required=False)
        self.assertFalse(r['lid_required'])
        self.assertEqual(r['sheet_parts_with_requested_lid'],3)
    def test_invalid_dimensions(self):
        for v in [None,True,0,-1,'NaN','Infinity','bad']:
            with self.subTest(v=v),self.assertRaises(ValueError): choose(v,100,100)
    def test_invalid_options(self):
        for kw in [dict(unit='feet'),dict(record_kind='maybe'),dict(explicit_method='guess'),dict(lid_required=None)]:
            with self.subTest(kw=kw),self.assertRaises(ValueError): choose(100,100,100,**kw)
