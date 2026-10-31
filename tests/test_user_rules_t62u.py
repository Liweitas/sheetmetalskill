"""user t62u 2026-10-28: NEST default is kit/1BOX — one complete box per DXF; order qty not expanded into SHEETnn."""
import json, sys, tempfile, unittest
from pathlib import Path
SK = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(SK / 'scripts'))

try:
    import ezdxf  # noqa
    import release_dxf as RD
except ImportError:
    RD = None


def _raw_rect(path, w, h):
    # raw_entities only picks LINE/ARC/CIRCLE (any layer)
    d = ezdxf.new('R2010', setup=True); d.units = 4; d.header['$INSUNITS'] = 4
    m = d.modelspace()
    for a, b in [((0, 0), (w, 0)), ((w, 0), (w, h)), ((w, h), (0, h)), ((0, h), (0, 0))]:
        m.add_line(a, b)
    d.saveas(path)


@unittest.skipIf(RD is None, 'ezdxf not in this python')
class NestKit1Box(unittest.TestCase):
    def test_kit_default_one_file_ignores_qty(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d); work = d / 'work'; out = d / 'out'; work.mkdir(); (out).mkdir()
            parts = ['U', 'LID', 'END_L', 'END_R']
            sizes = {'U': (100.0, 80.0), 'LID': (90.0, 70.0), 'END_L': (40.0, 50.0), 'END_R': (40.0, 50.0)}
            rep = {'parts': {}}
            for n, (w, h) in sizes.items():
                _raw_rect(work / f'{n}_CUT_raw.dxf', w, h)
                rep['parts'][n] = {'flat_size': [w, h], 'flat_area': w * h, 'bend_records': []}
            (work / 'report.json').write_text(json.dumps(rep))
            # qty would have been 2 under old sheets mode; kit must still emit one 1BOX
            checks, nest = RD.post_release(
                work, work / 'report.json', out, 'V1', parts, order=parts,
                qty={n: 2 for n in parts}, nest_mode='kit')
            self.assertTrue(all(c['pass'] for c in checks), checks)
            nest_files = sorted((out / 'NEST').glob('*.dxf'))
            self.assertEqual([f.name for f in nest_files], ['V1_NEST_2440x1220_1BOX.dxf'])
            self.assertEqual(nest['nest_mode'], 'kit')
            self.assertEqual(nest['sheets'], 1)
            self.assertEqual(len(nest['placements']), 4)  # one of each, not 8
            self.assertTrue(RD.check_dxf(nest_files[0], 'nest')['pass'])

    def test_sheets_mode_still_available(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d); work = d / 'work'; out = d / 'out'; work.mkdir(); out.mkdir()
            _raw_rect(work / 'U_CUT_raw.dxf', 2000.0, 1000.0)
            rep = {'parts': {'U': {'flat_size': [2000.0, 1000.0], 'flat_area': 2e6, 'bend_records': []}}}
            (work / 'report.json').write_text(json.dumps(rep))
            checks, nest = RD.post_release(
                work, work / 'report.json', out, 'V1', ['U'], order=['U'],
                qty={'U': 2}, nest_mode='sheets')
            self.assertTrue(all(c['pass'] for c in checks), checks)
            names = sorted(f.name for f in (out / 'NEST').glob('*.dxf'))
            self.assertEqual(names, ['V1_NEST_2440x1220_SHEET01.dxf', 'V1_NEST_2440x1220_SHEET02.dxf'])
            self.assertEqual(nest['sheets'], 2)


if __name__ == '__main__':
    unittest.main()
