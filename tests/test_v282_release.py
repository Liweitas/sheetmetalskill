"""v2.8.2 tests: conflict checks, confirmation draft, release packaging (name/zip), release DXF gate (if ezdxf present)."""
import json, sys, tempfile, unittest, zipfile
from pathlib import Path
SK = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(SK / 'scripts'))
import conflict_checks as CC, confirm_draft as CD, release_package as RP


class Conflicts(unittest.TestCase):
    def test_lid_root_q(self):
        r = CC.lid_root(1.0, 0.8, 0.5, 0.2)
        self.assertTrue(r['ok']); self.assertAlmostEqual(r['data']['clearance'], 0.12918, 4); self.assertAlmostEqual(r['data']['q_rule'], 0.2)
        self.assertLess(r['data']['clearance_if_q0'], 0)
        self.assertEqual(CC.lid_root(1.0, 0.8, 0.5, 0.0)['level'], 'ERROR')
        self.assertEqual(CC.lid_root(1.0, 0.5, 1.0, 0.0)['level'], 'INFO')

    def test_m4_thin(self):
        self.assertEqual(CC.m4_tap(1.0)['level'], 'WARN'); self.assertEqual(CC.m4_tap(2.0)['level'], 'INFO')

    def test_deep_u(self):
        self.assertEqual(CC.press_brake('U', 148.8, 218)['level'], 'WARN')
        self.assertEqual(CC.press_brake('U', 148.8, 218, punch_height=120)['level'], 'ERROR')
        self.assertEqual(CC.press_brake('U', 40, 300)['level'], 'INFO')

    def test_hole_to_bend(self):
        rep = {'parts': {'P': {'flat_circles': [[10, 4.0, 3.3], [10, 50, 3.3]], 'bend_lines': [[[0, 0], [100, 0]]]}}}
        r = CC.hole_to_bend(rep, 1.0, 0.8, 0.4)
        self.assertFalse(r['ok']); self.assertEqual(len(r['data']['violations']), 1)

    def test_hole_to_outline(self):  # v2.8.2: hole edge >= 4 from the flat outline
        rep = {'parts': {'P': {'flat_size': [100, 60], 'flat_circles': [[5, 30, 3.3], [50, 30, 3.3]]}}}
        r = CC.hole_to_outline(rep)
        self.assertFalse(r['ok']); self.assertEqual(len(r['data']['violations']), 1); self.assertAlmostEqual(r['data']['min'], 3.35)

    def test_unrequested(self):
        self.assertEqual(CC.unrequested({'handles': False}, {'handles': 8})['level'], 'ERROR')
        self.assertTrue(CC.unrequested({'handles': True}, {'handles': 8})['ok'])


class Draft(unittest.TestCase):
    def test_xiejiao03_known_unknown_still_pending(self):
        b = json.load(open(SK / 'assets/examples/S-201-1-20261021-001-v1.release.json')); b['Ri'] = 0.8
        b['confirm']['named_processes'] = ['斜角03', '03', '未知工艺Q9']
        txt, pend = CD.build(b, [], True)
        self.assertFalse(any('斜角03' in p and '未在技能已知工艺库' in p for p in pend))
        self.assertTrue(any('未知工艺Q9' in p for p in pend))
        self.assertIn('corner03.py', txt)

    def test_unknown_process_and_two_readings(self):
        b = json.load(open(SK / 'assets/examples/S-201-1-20261021-001-v1.release.json')); b['Ri'] = 0.8
        b['confirm']['hole_refs'] = [{'what': '孔', 'axis': '距上沿', 'value': 15, 'diameter': 4}]
        txt, pend = CD.build(b, [{'level': 'WARN', 'msg_cn': 'x'}], True)
        self.assertIn('DRAFT - NOT SENT', txt); self.assertIn('未做实物试折/试装', txt); self.assertIn('production_release=false', txt)
        self.assertFalse(any('斜角03' in p for p in pend)); self.assertTrue(any('孔心' in p and '孔边' in p and '17' in p for p in pend))
        self.assertIn('经验值', txt)


class Package(unittest.TestCase):
    def _stage(self, d, ver):
        s = Path(d) / ver; (s / 'DOC').mkdir(parents=True); (s / 'DOC' / f'{ver}_README.md').write_text(ver); return s

    def test_name_exact_no_normalize(self):
        with tempfile.TemporaryDirectory() as d:
            for bad in ('S-201 v1', '订单-001', ''):
                s = self._stage(d, 'X' + str(abs(hash(bad))))
                g = RP.gate(s, bad); self.assertFalse(next(c for c in g['checks'] if c['check'] == 'name_ascii_exact')['pass'])

    def test_prefix_and_zip_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            v = 'S-201-1-20991231-009-v3'; s = self._stage(d, v); (s / 'DOC' / 'notes.md').write_text(v)
            g = RP.gate(s, v); self.assertFalse(next(c for c in g['checks'] if c['check'] == 'every_file_prefixed_with_release')['pass'])
            (s / 'DOC' / 'notes.md').unlink()
            z = RP.write_zip(s, v, Path(d) / f'{v}.zip')
            with zipfile.ZipFile(z['zip']) as f:
                self.assertTrue(all(n.startswith(v + '/') and n.isascii() for n in f.namelist()))

    def test_stale_version_in_step(self):
        with tempfile.TemporaryDirectory() as d:
            v = 'S-201-1-20991231-009-v3'; s = self._stage(d, v); (s / 'STEP').mkdir()
            (s / 'STEP' / f'{v}_U.step').write_text("HEADER;\nFILE_DESCRIPTION(('S-201-1-20991231-009-v2 U'));\nENDSEC;\nDATA;\nENDSEC;")
            g = RP.gate(s, v); c = {x['check']: x['pass'] for x in g['checks']}
            self.assertFalse(c['release_name_inside_step_dxf']); self.assertFalse(c['no_stale_release_in_step_dxf'])


try:
    import ezdxf  # noqa
    import release_dxf as RD
except ImportError:
    RD = None


@unittest.skipIf(RD is None, 'ezdxf not in this python (run with /workspace/addendum-venv/bin/python)')
class DxfGate(unittest.TestCase):
    def test_nest_rules(self):
        with tempfile.TemporaryDirectory() as d:
            doc = RD.new_doc('V1'); doc.layers.add('CUT'); doc.layers.add('SHEET'); m = doc.modelspace()
            m.add_lwpolyline([(0, 0), (2440, 0), (2440, 1220), (0, 1220)], close=True, dxfattribs={'layer': 'SHEET'})
            m.add_lwpolyline([(10, 10), (110, 10), (110, 60), (10, 60)], close=True, dxfattribs={'layer': 'CUT'})
            p = Path(d) / 'n.dxf'; doc.saveas(p); self.assertTrue(RD.check_dxf(p, 'nest')['pass'])
            doc.layers.add('BEND', linetype='DASHED'); m.add_line((10, 30), (110, 30), dxfattribs={'layer': 'BEND'}); doc.saveas(p)
            self.assertFalse(RD.check_dxf(p, 'nest')['pass'])

    def test_open_and_duplicate(self):
        with tempfile.TemporaryDirectory() as d:
            doc = RD.new_doc('V1'); doc.layers.add('CUT'); m = doc.modelspace()
            m.add_line((0, 0), (10, 0), dxfattribs={'layer': 'CUT'}); m.add_line((0, 0), (10, 0), dxfattribs={'layer': 'CUT'})
            p = Path(d) / 'c.dxf'; doc.saveas(p); r = RD.check_dxf(p, 'cut'); self.assertFalse(r['pass'])


if __name__ == '__main__':
    unittest.main()
