import copy
import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / 'scripts/build_golden_package.py'
spec = importlib.util.spec_from_file_location('golden_entry_under_test', path)
entry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(entry)


class GoldenWrap(unittest.TestCase):
    def test_default_width_length_exclude_lid_height_includes_it(self):
        brief = self.brief()
        brief.pop('dim_basis')
        brief.update(dimensions=dict(length=450, width=380, height=220),
                     rect_cutouts=[], handles=dict(profile='handle-85-62-30-v1',
                                                  cx=[115.5, 340.5], cy=193))
        job = entry.pipe_brief(brief, 'BODY-DATUM')
        self.assertEqual([job['L'], job['W'], job['H']], [450, 380, 220])
        self.assertEqual(job['finished_outer_mm'], [453, 383, 220])
        self.assertEqual(job['handles'], brief['handles'])

    def test_finished_outer_is_rejected_even_when_explicit(self):
        brief = self.brief()
        brief.update(dim_basis='finished_outer',
                     dimensions=dict(length=450, width=380, height=220),
                     rect_cutouts=[], handles=dict(profile='handle-85-62-30-v1',
                                                  cx=[115.5, 340.5], cy=193))
        with self.assertRaises(SystemExit):
            entry.pipe_brief(brief, 'EXPLICIT-FINISHED')

    def test_body_length_width_do_not_shrink_with_lid_overhang(self):
        for thickness in (.8, 1, 1.2):
            for clearance in (.5, 1):
                brief = self.brief() | dict(dimensions=dict(length=430,width=245,height=170),
                    thickness=thickness,g=clearance,rect_cutouts=[],
                    handles=dict(profile='handle-85-62-30-v1',cx=[215],cy=122.5))
                job=entry.pipe_brief(brief,'FIXED-BODY')
                self.assertEqual([job['L'],job['W'],job['H']],[430,245,170])
                self.assertEqual(job['finished_outer_mm'],
                    [430+2*(thickness+clearance),245+2*(thickness+clearance),170])

    def test_external_end_rectangle_stays_on_declared_outer_face(self):
        brief=self.brief() | dict(dimensions=dict(length=430,width=245,height=170),
            handles=dict(profile='handle-85-62-30-v1',cx=[215],cy=122.5),
            rect_cutouts=[dict(id='R1',part_id='END_R',center=[430,53,145],
                axis=[1,0,0],size_xy=[26.5,18])])
        self.assertEqual(entry.pipe_brief(brief,'RIGHT-END')['rect_cutouts'],brief['rect_cutouts'])
        brief['rect_cutouts'][0]['center'][0]=429
        with self.assertRaises(SystemExit):entry.pipe_brief(brief,'WRONG-FACE')

    def brief(self):
        return {'dimensions': {'length': 202, 'width': 192, 'height': 350},
                'customer_requirement_text': '长20.5cm宽19.5cm高35cm；盖子上面一个把手。',
                'dim_basis': 'body_outer', 'material': '201', 'thickness': 1,
                'handles': {'profile': 'handle-85-62-30-v1', 'cx': [101], 'cy': 96},
                'rect_cutouts': [{'id': 'RECT', 'part_id': 'U', 'center': [202, 152, 32],
                                 'axis': [1, 0, 0], 'size_xy': [27, 20]}]}

    def test_wrap_preserves_features_and_finished_dimensions(self):
        brief = self.brief()
        original = copy.deepcopy(brief)
        job = entry.pipe_brief(brief, 'TEST')
        self.assertEqual(job['structure'], 'u_l_t7u')
        self.assertEqual(job['finished_outer_mm'], [205, 195, 350])
        self.assertEqual(job['rect_cutouts'], brief['rect_cutouts'])
        self.assertEqual(job['handles'], brief['handles'])
        self.assertEqual(brief, original)

    def test_customer_words_and_updates_survive_without_rewriting(self):
        original = '  方孔 中心距底32 mm\n保留原话和单位；201不锈钢。  '
        updates = ['方孔 中心距底320 mm', '盖上把手不变']
        job = entry.pipe_brief(self.brief() | {
            'customer_requirement_text': original,
            'customer_requirement_updates': updates}, 'TEST')
        self.assertEqual(job.get('customer_requirement_text'), original)
        self.assertEqual(job.get('customer_requirement_updates'), updates)

    def test_missing_or_invalid_customer_words_are_rejected(self):
        for text in (None, '', ' \n ', 12, ['原文'], '原文\x00'):
            with self.subTest(text=text), self.assertRaises(SystemExit):
                entry.pipe_brief(self.brief() | {'customer_requirement_text': text}, 'TEST')
        for updates in ('修改', [None], [''], ['修改\x00']):
            with self.subTest(updates=updates), self.assertRaises(SystemExit):
                entry.pipe_brief(self.brief() | {'customer_requirement_updates': updates}, 'TEST')

    def test_handle_only_needs_no_invented_ports(self):
        job = entry.pipe_brief(self.brief() | {'rect_cutouts': []}, 'TEST')
        self.assertEqual(job['lid_ports'], [])
        self.assertEqual(job['panel_holes'], [])

    def test_endplate_selection_including_equality(self):
        for height in (200, 202):
            job = entry.pipe_brief(self.brief() | {
                'dimensions': {'length': 202, 'width': 192, 'height': height},
                'rect_cutouts': []}, 'TEST')
            self.assertEqual(job['structure'], 'u_endplates')

    def test_unsupported_wrap_face_rejected(self):
        brief = self.brief()
        brief['rect_cutouts'][0].update(center=[50, 0, 32], axis=[0, 1, 0])
        with self.assertRaises(SystemExit):
            entry.pipe_brief(brief, 'TEST')

    def test_edge_crossing_and_nonfinite_rect_rejected(self):
        for override in ({'center': [202, 190, 32]}, {'size_xy': [float('nan'), 20]}):
            brief = self.brief()
            brief['rect_cutouts'][0].update(override)
            with self.assertRaises(SystemExit):
                entry.pipe_brief(brief, 'TEST')


if __name__ == '__main__':
    unittest.main()
