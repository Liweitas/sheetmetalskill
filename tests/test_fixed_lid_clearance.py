import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import patch


SK = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('fixed_gap_entry', SK/'scripts/build_golden_package.py')
entry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(entry)


class FixedLidClearance(unittest.TestCase):
    def brief(self, thickness=.8):
        return dict(customer_requirement_text='箱体225×175，含盖高350，201不锈钢。',
                    dimensions=dict(length=225, width=175, height=350),
                    material='201', thickness=thickness,
                    holes=[dict(id='P1', part_id='LID', point=[70,60,350],
                                axis=[0,0,1], diameter=10)])

    def cfg(self, job):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/'job.json'
            p.write_text(json.dumps(job))
            with patch.dict(os.environ, SM_JOB=str(p)):
                return runpy.run_path(str(SK/'pipelines/u_endplates/cfg.py'))

    def test_cover_size_uses_actual_thickness_and_half_mm_on_each_side(self):
        for t, expected in [(.8, [227.6,177.6,350]), (1, [228,178,350])]:
            for explicit in ({}, {'g':.5}):
                with self.subTest(t=t, explicit=explicit):
                    job = entry.pipe_brief(self.brief(t) | explicit, 'FIXED-GAP')
                    self.assertEqual([job['L'],job['W'],job['H']], [225,175,350])
                    self.assertEqual(job['finished_outer_mm'], expected)
                    cfg = self.cfg(job)
                    self.assertEqual(cfg['g'], .5)
                    self.assertEqual([cfg['OUTER_L'],cfg['OUTER_W'],cfg['OUTER_H']], expected)

    def test_bad_gap_rejected_at_public_entry_and_worker(self):
        valid = entry.pipe_brief(self.brief(), 'FIXED-GAP')
        for g in [0, .4, .50001, 1, 1.2, float('nan'), float('inf'), None, 'bad']:
            with self.subTest(g=g):
                with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                    entry.pipe_brief(self.brief() | {'g':g}, 'WRONG-GAP')
                with self.assertRaises((ValueError, TypeError)):
                    self.cfg(valid | {'g':g})

    def test_stale_229_cover_cannot_bypass_worker_with_correct_gap(self):
        job = entry.pipe_brief(self.brief(), 'STALE-CAP')
        with self.assertRaisesRegex(ValueError, '盖外尺寸'):
            self.cfg(job | {'finished_outer_mm':[229,179,350]})


if __name__ == '__main__':
    unittest.main()
