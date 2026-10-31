"""User rule t52u (2026-10-26 15:37 UTC+8): restore the thin-sheet M4 tapping warning for t<=1.2 and make every
template that prints M4 tapped holes emit it (PDF + README + checklist). Pure python."""
import sys, unittest
from pathlib import Path
SK = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(SK / 'scripts'))
import conflict_checks as CC
import confirm_draft as CD

KEYS = ('约1扣有效螺纹', '强度偏低', '易滑牙', '不建议反复拆装', '压铆螺母', '拉铆螺母', '点焊螺母', '待确认')


class M4Warning(unittest.TestCase):
    def test_warn_up_to_1_2(self):
        for t in (0.8, 1.0, 1.2):
            r = CC.m4_tap(t)
            self.assertEqual(r['level'], 'WARN', t)
            for k in KEYS + ('底孔Ø3.3',): self.assertIn(k, r['msg_cn'])
            self.assertEqual(r['data']['pending_alternatives'], ['压铆螺母', '拉铆螺母', '点焊螺母'])

    def test_info_above_1_2(self):
        for t in (1.25, 1.5, 2.0): self.assertEqual(CC.m4_tap(t)['level'], 'INFO', t)

    def test_material_in_text(self):
        self.assertIn('1.0 mm 201 板直接攻M4', CC.m4_thin_sheet_warning_cn(1.0, '201'))

    def test_run_and_confirm_draft_carry_warning(self):
        res = CC.run({'t': 1.0, 'Ri': 0.8, 'K': 0.4, 'g': 0.5, 'q': 0.2, 'material_cn': '201'})
        m4 = [x for x in res if x['id'] == 'm4_tap_thin_sheet'][0]
        self.assertEqual(m4['level'], 'WARN')
        brief = {'release': 'T52U-TEST', 'Ri': 0.8, 'K': 0.4,
                 'confirm': {'material_cn': '201不锈钢', 't': 1.0, 'dims': {'L': 400, 'W': 220, 'H': 150}, 'structure_cn': 'U+两端板+盖'}}
        txt, _ = CD.build(brief, res, checks_passed=True)
        for k in KEYS: self.assertIn(k, txt)


class TemplatesEmitWarning(unittest.TestCase):
    def test_u_endplates_pdf_docs(self):
        pdf = (SK / 'pipelines/u_endplates/pdf.py').read_text(); docs = (SK / 'pipelines/u_endplates/docs.py').read_text()
        for k in ('约1扣有效螺纹', '易滑牙', '不建议反复拆装', '点焊螺母', '待确认'): self.assertIn(k, pdf); self.assertIn(k, docs)
        self.assertNotIn('不再提压铆', docs)
        # checklist table + README pending + README risks each carry it
        self.assertGreaterEqual(docs.count('{M4TXT}'), 3)

    def test_u_l_t7u_pdf_readme(self):
        for f in ('make_bend_pdf.py', 'make_readme.py'):
            s = (SK / 'pipelines/u_l_t7u' / f).read_text()
            for k in ('约1扣有效螺纹', '易滑牙', '不建议反复拆装', '点焊螺母', '待确认'): self.assertIn(k, s, f)
            self.assertIn('1.2', s, f)

    def test_rules_text(self):
        for f in ('SKILL.md', 'references/v2.8.2-delivery-rules.md', 'references/holes-and-hardware.md'):
            s = (SK / f).read_text()
            for k in ('t≤1.2', '易滑牙', '点焊螺母', '待确认'): self.assertIn(k, s, f)


if __name__ == '__main__':
    unittest.main()
