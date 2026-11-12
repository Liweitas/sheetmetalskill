import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from build_golden_package import pipe_brief


class PanelHandleRotation(unittest.TestCase):
    def brief(self, rotated=False):
        holes = []
        for part, x, axis in [('END_L', 0, [-1, 0, 0]), ('END_R', 550, [1, 0, 0])]:
            for label, y, z in [('W1', 122.5, 114.4), ('W2', 207.5, 114.4),
                                ('N1', 134, 144.4), ('N2', 196, 144.4)]:
                point = [x, 330-y, 258.8-z] if rotated else [x, y, z]
                holes.append(dict(id=part+label, part_id=part, purpose='handle',
                                  diameter=6.6, point=point, axis=axis))
        return dict(dimensions=dict(length=550, width=330, height=260),
                    customer_requirement_text='长550宽330高260；两端板居中把手，按指定方向开孔。',
                    thickness=1, dim_basis='body_outer', q=.2, holes=holes)

    def test_explicit_180_degree_rotation_preserves_both_panel_hole_groups(self):
        brief = self.brief(rotated=True)
        original = copy.deepcopy(brief)
        try:
            job = pipe_brief(brief, 'TEST')
        except SystemExit:
            self.fail('Explicit 180 degree panel handle rotation was rejected')
        self.assertEqual(job['panel_holes'], original['holes'])
        self.assertEqual(brief, original)

    def test_existing_wide_row_down_remains_valid(self):
        brief = self.brief()
        self.assertEqual(pipe_brief(brief, 'TEST')['panel_holes'], brief['holes'])

    def test_rotation_still_rejects_incorrect_pitch_or_center(self):
        for key, value in [('diameter', 6.5), ('point', [0, 208.5, 144.4]),
                           ('point', [0, 207.5, 145.4])]:
            brief = self.brief(rotated=True)
            brief['holes'][0][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(SystemExit):
                pipe_brief(brief, 'TEST')


if __name__ == '__main__':
    unittest.main()
