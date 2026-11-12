"""User rule t35u (2026-10-26 21:38 UTC+8, v2.8.5): cable holes (线孔) are at least 2 per box. Pure python."""
import sys, unittest
from pathlib import Path
SK = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(SK / 'scripts'))
import conflict_checks as CC


class CableHoles(unittest.TestCase):
    def test_suggest_toward_centre_25(self):
        r = CC.suggest_second_cable_hole(60, 185, 16, 0, 150)
        self.assertEqual((r['u'], r['v'], r['d'], r['pitch'], r['web']), (85.0, 185, 16, 25.0, 9.0)); self.assertTrue(r['toward_centre'])
        r = CC.suggest_second_cable_hole(110, 50, 16, 0, 150)
        self.assertEqual(r['u'], 85.0)

    def test_count_levels(self):
        self.assertEqual(CC.cable_hole_count([])['level'], 'INFO')
        w = CC.cable_hole_count([{'id': 'C1', 'd': 16}])
        self.assertEqual(w['level'], 'WARN'); self.assertIn('至少2个', w['msg_cn'])
        ok = CC.cable_hole_count([{'id': 'C1'}, {'id': 'C2', 'added_by_rule': True}])
        self.assertEqual(ok['level'], 'INFO'); self.assertIn('HOLD', ok['msg_cn'])

    def test_run_opt_in_backward_compatible(self):
        base = {'t': 1.0, 'Ri': 0.8, 'K': 0.4, 'g': 0.5, 'q': 0.2}
        self.assertNotIn('cable_hole_min_count', [x['id'] for x in CC.run(base)])
        r = CC.run({**base, 'cable_holes': [{'id': 'C1', 'd': 16}]})
        self.assertEqual([x for x in r if x['id'] == 'cable_hole_min_count'][0]['level'], 'WARN')

    def test_skill_md_rule(self):
        s = (SK / 'SKILL.md').read_text(encoding='utf-8')
        self.assertIn('线孔至少2个', s)
        self.assertIn('cable_hole_min_count', s)
        # version floats with skill bumps; require current VERSION matches frontmatter major.minor.patch
        ver = (SK / 'VERSION').read_text().strip()
        self.assertIn(f'version: "{ver}"', s)
        self.assertGreaterEqual(tuple(int(x) for x in ver.split('.')[:3]), (2, 8, 5))


if __name__ == '__main__':
    unittest.main()
