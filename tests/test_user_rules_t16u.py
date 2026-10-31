"""User hard rules 2026-10-26 (source: user t16u): flush joints, default handle M6, no dashed DXF lines, M4 tapping,
tapped connector screw holes, compact PDF. Pure python; DXF tests need ezdxf (/workspace/addendum-venv/bin/python)."""
import json, sys, tempfile, unittest
from pathlib import Path
SK = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(SK / 'scripts'))
import conflict_checks as CC


class Defaults(unittest.TestCase):
    def test_end_inset_default_zero(self):
        d = json.loads((SK / 'assets/process/experience-defaults-v2.json').read_text())
        self.assertEqual(d['external_end_contour_inset_mm'], 0.0)

    def test_general_process_end_inset_zero(self):
        try:
            import jsonschema  # noqa
        except ImportError:
            self.skipTest('jsonschema not in this python (run with /workspace/sm-venv/bin/python)')
        from general_process import compile_brief
        b = {'input_contract': 'general-process-v1', 'id': 'T16U', 'units': 'mm', 'dimension_basis': 'outer', 'height_basis': 'including_lid',
             'lid_required': True, 'material': '201', 'thickness': 1.0, 'dimensions': {'length': 400, 'width': 220, 'height': 150}}
        j = compile_brief(b)['job']
        self.assertEqual(j['method'], 'u_external_ends')   # max(L,W) >= H -> U + two external end plates (rule 7)
        self.assertEqual(j['end_inset'], 0.0); self.assertEqual(j['seam_gap'], 0)
        b['dimensions'] = {'length': 200, 'width': 150, 'height': 300}
        self.assertEqual(compile_brief(b)['job']['method'], 'u_wrap_bottom_l')

    def test_handle_default_m6(self):
        h = json.loads((SK / 'assets/profiles/handle-85-62-30-v1.json').read_text()); s = json.dumps(h)
        self.assertIn('85', s); self.assertIn('62', s); self.assertIn('30', s); self.assertIn('6.6', s); self.assertIn('M6', s)

    def test_connector_profiles_tapped(self):
        for n, th, dr in (('schurter-6100-3-v1', 'M3', 2.5), ('anderson-50a-v1', 'M4', 3.3)):
            m = json.loads((SK / f'assets/profiles/{n}.json').read_text())['mount_holes']
            self.assertEqual((m['process'], m['thread'], m['tap_drill_mm'], m['diameter_mm']), ('tap', th, dr, dr))

    def test_u_l_t7u_cfg_defaults_zero(self):
        src = (SK / 'pipelines/u_l_t7u/cfg.py').read_text()
        self.assertIn("_C.get('l_cover_setback_mm', 0.0)", src); self.assertIn("_C.get('lid_long_skirt_setback_mm', 0.0)", src)
        self.assertNotIn('S=0.2', (SK / 'pipelines/u_l_t7u/build_main.py').read_text())

    def test_skill_md_has_rules(self):
        s = (SK / 'SKILL.md').read_text()
        for k in ('用户硬性规则', '不退让0.2mm', '所有DXF中不能有虚线', 'M4攻丝', '品字口', 'max(L,W) ≥ H'):
            self.assertIn(k, s)


class Checks(unittest.TestCase):
    def test_m4_tapping_stays_default_alternatives_only_pending(self):
        # t16u: M4 tapping is the default and is never silently replaced; t52u (2026-10-26) restored the thin-sheet
        # warning, so for t<=1.2 the alternatives are LISTED as 待确认 (not applied); thicker sheet: no alternatives.
        for t in (1.5, 2.0):
            m = CC.m4_tap(t)['msg_cn']
            for w in ('压铆', '拉铆', '焊接螺母', '点焊螺母', '翻孔'): self.assertNotIn(w, m)
        r = CC.m4_tap(1.0)
        self.assertEqual(r['data']['default_kept'], 'M4 tapped'); self.assertIn('待确认', r['msg_cn']); self.assertNotIn('翻孔', r['msg_cn'])

    def test_connector_taps(self):
        bad = CC.connector_screw_taps([{'name': '品字口', 'screw_holes': [{'d': 3.5}, {'d': 3.5}]}])
        self.assertEqual(bad['level'], 'ERROR'); self.assertIn('攻M3', bad['msg_cn']); self.assertIn('2.5', bad['msg_cn'])
        ok = CC.connector_screw_taps([{'name': 'anderson', 'screw_holes': [{'d': 3.3, 'thread': 'M4', 'process': 'tap'}] * 4}])
        self.assertTrue(ok['ok'])
        wrong = CC.connector_screw_taps([{'name': 'x', 'screw_holes': [{'d': 4.5, 'thread': 'M4', 'process': 'tap', 'tap_drill': 4.5}]}])
        self.assertFalse(wrong['ok'])

    def test_joint_flush(self):
        self.assertTrue(CC.joint_flush({'end_inset': 0, 'seam_gap': 0})['ok'])
        self.assertEqual(CC.joint_flush({'l_cover_setback_mm': 0.2})['level'], 'ERROR')
        self.assertEqual(CC.joint_flush({'end_inset': 0.2, 'setback_source_user': '用户本单要求'})['level'], 'WARN')

    def test_run_includes_new_checks(self):
        r = CC.run({'t': 1.0, 'Ri': .8, 'K': .4, 'g': .5, 'q': .2, 'connectors': [{'name': 'c', 'screw_holes': [{'d': 4.5}]}]})
        ids = {x['id'] for x in r}; self.assertIn('connector_screw_taps', ids); self.assertIn('joint_flush', ids)


try:
    import ezdxf  # noqa
    import release_dxf as RD
except ImportError:
    RD = None


@unittest.skipIf(RD is None, 'ezdxf not in this python (run with /workspace/addendum-venv/bin/python)')
class NoDash(unittest.TestCase):
    def _raw(self, d):
        doc = ezdxf.new('R2010'); doc.units = 4; m = doc.modelspace()
        for a, b in (((0, 0), (100, 0)), ((100, 0), (100, 50)), ((100, 50), (0, 50)), ((0, 50), (0, 0))): m.add_line(a, b)
        p = Path(d) / 'raw.dxf'; doc.saveas(p); return p

    def test_bend_dxf_default_continuous_and_labelled(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / 'b.dxf'
            RD.write_bend(self._raw(d), out, 'V1', [{'flat_line_mm': [(0, 25), (100, 25)], 'label': 'B1 上折 90°'}])
            r = RD.check_dxf(out, 'bend', expect_bends=1); self.assertTrue(r['pass'], r['fails'])
            doc = ezdxf.readfile(out)
            self.assertEqual(doc.layers.get('BEND').dxf.linetype.upper(), 'CONTINUOUS'); self.assertEqual(doc.layers.get('BEND').color, 1)
            self.assertTrue(any(e.dxftype() == 'TEXT' for e in doc.modelspace()))

    def test_write_bend_refuses_dashed(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                RD.write_bend(self._raw(d), Path(d) / 'b.dxf', 'V1', [], bend_linetype='DASHED')

    def test_dashed_fails_every_role(self):
        with tempfile.TemporaryDirectory() as d:
            for role, lay in (('bend', 'BEND'), ('cut', 'CUT'), ('bend', 'OUTLINE')):
                doc = RD.new_doc('V1'); doc.layers.add('OUTLINE'); doc.layers.add('CUT'); doc.layers.add('BEND', color=1); m = doc.modelspace()
                for a, b in (((0, 0), (100, 0)), ((100, 0), (100, 50)), ((100, 50), (0, 50)), ((0, 50), (0, 0))):
                    m.add_line(a, b, dxfattribs={'layer': 'OUTLINE' if role == 'bend' else 'CUT'})
                if role == 'bend': m.add_line((0, 25), (100, 25), dxfattribs={'layer': 'BEND', 'linetype': 'DASHED' if lay == 'BEND' else 'CONTINUOUS'})
                if lay == 'OUTLINE': doc.layers.get('OUTLINE').dxf.linetype = 'HIDDEN'
                if lay == 'CUT': doc.layers.get('CUT').dxf.linetype = 'CENTER'
                p = Path(d) / f'{role}_{lay}.dxf'; doc.saveas(p)
                r = RD.check_dxf(p, role); self.assertFalse(r['pass'], (role, lay)); self.assertTrue(any('dashed' in f for f in r['fails']), r['fails'])

    def test_dashed_layer_unused_still_fails(self):
        with tempfile.TemporaryDirectory() as d:
            doc = RD.new_doc('V1'); doc.layers.add('CUT'); doc.layers.add('JUNK', linetype='DASHED'); m = doc.modelspace()
            for a, b in (((0, 0), (100, 0)), ((100, 0), (100, 50)), ((100, 50), (0, 50)), ((0, 50), (0, 0))): m.add_line(a, b, dxfattribs={'layer': 'CUT'})
            p = Path(d) / 'c.dxf'; doc.saveas(p); self.assertFalse(RD.check_dxf(p, 'cut')['pass'])
            e, l = RD.noncontinuous(ezdxf.readfile(p)); self.assertEqual(e, []); self.assertEqual(l, [('JUNK', 'DASHED')])


if __name__ == '__main__':
    unittest.main()
