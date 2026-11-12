"""User rule t99u / audit t98u (2026-10-31, v2.8.20): body-face holes vs lid skirt free edge (盖裙遮挡)."""
import json, sys, unittest
from pathlib import Path
SK = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(SK / 'scripts'))
import conflict_checks as CC
import confirm_draft as CD

# S-201-1.2-20261029-003-v1 geometry from t98u audit
H, SKIRT = 230.0, 15.0
ZB = H - SKIRT  # 215.0
END_FEATURES = {
    'part': 'END_L',
    'circles': [
        {'id': 'E1', 'part': 'END_L', 'y': 40, 'z': 210.6, 'd': 30, 'use': 'cable/gland Ø30'},
        {'id': 'E2', 'part': 'END_L', 'y': 73, 'z': 210.6, 'd': 20, 'use': 'cable Ø20'},
        {'id': 'E4', 'part': 'END_L', 'y': 160, 'z': 210.6, 'd': 30, 'use': 'cable/gland Ø30'},
        {'id': 'E5a', 'part': 'END_L', 'y': 125, 'z': 180, 'd': 7.5, 'use': 'below meter'},
        {'id': 'E5b', 'part': 'END_L', 'y': 125, 'z': 165, 'd': 7.5, 'use': 'below meter'},
    ],
    'rects': [
        {'id': 'E3', 'part': 'END_L', 'cy': 114, 'cz': 210.6, 'w': 46, 'h': 27, 'use': 'meter 46×27'},
    ],
}


class HoleToLidSkirt(unittest.TestCase):
    def test_skirt_free_edge(self):
        self.assertEqual(CC.skirt_free_edge_z(H, SKIRT), 215.0)

    def test_error_under_skirt_says_geshan(self):
        r = CC.hole_to_lid_skirt({'H': H, 'skirt': SKIRT, 'end_features': END_FEATURES})
        self.assertEqual(r['id'], 'hole_to_lid_skirt')
        self.assertEqual(r['level'], 'ERROR')
        self.assertIn('盖裙遮挡', r['msg_cn'])
        self.assertFalse(r['ok'])
        ids = {v['id'] for v in r['data']['violations']}
        self.assertEqual(ids, {'E1', 'E2', 'E3', 'E4'})
        e1 = next(v for v in r['data']['violations'] if v['id'] == 'E1')
        self.assertAlmostEqual(e1['clearance_featureTop_to_skirtFreeEdge_mm'], -10.6, places=2)

    def test_warn_near_skirt(self):
        # Ø20 at Zc such that top is 5 mm below skirt free edge (clearance 5 < 10)
        feats = {'circles': [{'id': 'C1', 'part': 'END_L', 'z': ZB - 5 - 10, 'd': 20, 'use': 'cable'}]}
        # top = (ZB-15) + 10 = ZB-5 → clearance 5
        r = CC.hole_to_lid_skirt({'H': H, 'skirt': SKIRT, 'end_features': feats})
        self.assertEqual(r['level'], 'WARN')
        self.assertNotIn('盖裙遮挡', r['msg_cn'])  # WARN band uses 靠盖裙 wording
        self.assertIn('靠盖裙', r['msg_cn'])

    def test_ok_clearance_ge_10(self):
        feats = {'circles': [{'id': 'C1', 'part': 'END_L', 'z': 180, 'd': 7.5, 'use': 'low'}]}
        r = CC.hole_to_lid_skirt({'H': H, 'skirt': SKIRT, 'end_features': feats})
        self.assertEqual(r['level'], 'INFO')
        self.assertTrue(r['ok'])

    def test_exclude_m4_fixing(self):
        feats = {'circles': [
            {'id': 'M4', 'part': 'U', 'z': 222.5, 'd': 3.3, 'use': '箱体固定 M4 攻丝', 'role': 'm4_body'},
            {'id': 'L1', 'part': 'LID', 'z': 222.5, 'd': 4.5, 'use': '盖裙螺钉过孔', 'role': 'lid_screw'},
        ]}
        r = CC.hole_to_lid_skirt({'H': H, 'skirt': SKIRT, 'end_features': feats})
        self.assertEqual(r['level'], 'INFO')
        self.assertEqual(r['data']['features_checked'], 0)

    def test_waive_demotes_error(self):
        r = CC.hole_to_lid_skirt({'H': H, 'skirt': SKIRT, 'end_features': END_FEATURES,
                                 'hold_skirt_clearance_waived': True})
        self.assertEqual(r['level'], 'WARN')
        self.assertIn('盖裙遮挡', r['msg_cn'])

    def test_run_wired(self):
        base = {'t': 1.2, 'Ri': 0.8, 'K': 0.4, 'g': 0.5, 'q': 0.2,
                'H': H, 'skirt': SKIRT, 'end_features': END_FEATURES}
        r = CC.run(base)
        hit = [x for x in r if x['id'] == 'hole_to_lid_skirt']
        self.assertEqual(len(hit), 1)
        self.assertEqual(hit[0]['level'], 'ERROR')
        self.assertIn('盖裙遮挡', hit[0]['msg_cn'])

    def test_run_backward_compatible_no_H(self):
        base = {'t': 1.0, 'Ri': 0.8, 'K': 0.4, 'g': 0.5, 'q': 0.2}
        ids = [x['id'] for x in CC.run(base)]
        self.assertNotIn('hole_to_lid_skirt', ids)

    def test_force_lines_and_confirm_draft(self):
        res = CC.run({'t': 1.2, 'Ri': 0.8, 'K': 0.4, 'g': 0.5, 'q': 0.2,
                      'H': H, 'skirt': SKIRT, 'end_features': END_FEATURES})
        lines = CC.lid_skirt_force_lines_cn(res)
        self.assertTrue(lines)
        self.assertTrue(any('盖裙遮挡' in ln for ln in lines))
        brief = {'release': 'T99U-TEST', 'Ri': 0.8, 'K': 0.4,
                 'confirm': {'material_cn': '201', 't': 1.2, 'dims': {'L': 380, 'W': 200, 'H': 230},
                             'structure_cn': 'U+两端板+盖'}}
        txt, pend = CD.build(brief, res, checks_passed=False)
        self.assertIn('盖裙遮挡', txt)
        self.assertTrue(any('盖裙遮挡' in p for p in pend))
        self.assertIn('[ERROR]', txt)

    def test_skill_version(self):
        s = (SK / 'SKILL.md').read_text(encoding='utf-8')
        self.assertRegex(s, r'version:\s*"2\.8\.\d+"')  # bumped since t99u; keep rule text checks below
        self.assertIn('盖裙遮挡', s)
        self.assertIn('hole_to_lid_skirt', s)
        self.assertRegex((SK / 'VERSION').read_text().strip(), r'^2\.8\.\d+$')
        self.assertTrue((SK / 'references/hole-to-lid-skirt.md').exists())


if __name__ == '__main__':
    unittest.main()
