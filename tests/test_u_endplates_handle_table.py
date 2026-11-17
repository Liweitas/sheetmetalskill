import json
import os
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import patch


class LidHandleTable(unittest.TestCase):
    def test_explicit_90_degree_handle_keeps_wide_row_toward_positive_x(self):
        job = dict(structure='u_l_t7u', release='ROTATION90', material_cn='201',
                   L=200,W=170,H=285,t=1,Ri=.8,K=.4,g=.5,q=.2,
                   long_x=[],short_y=[],handles=dict(profile='handle-85-62-30-v1',
                                                   cx=[103],cy=88,rotations=[90]))
        with tempfile.TemporaryDirectory() as directory:
            brief=Path(directory)/'brief.json';brief.write_text(json.dumps(job))
            with patch.dict(os.environ,SM_JOB=str(brief)):
                cfg=runpy.run_path(str(Path(__file__).resolve().parents[1]/'pipelines/u_endplates/cfg.py'))
        self.assertEqual({(h['x'],h['y'],h['d']) for h in cfg['LID_HOLES']},
                         {(118,45.5,6.6),(118,130.5,6.6),(88,57,6.6),(88,119,6.6)})

    def test_verified_top_fixings_reach_lid_table_without_side_fixings(self):
        job = dict(structure='u_endplates', release='TOP4-TEST', material_cn='201',
                   L=547.4, W=297.4, H=130, t=.8, Ri=.8, K=.4, g=.5, q=.2,
                   long_x=[], short_y=[], top_fixings=[
                       dict(id=i, formed=[x, y, 130], lid_clearance=4.5)
                       for i, (x, y) in enumerate(((10.7,10.7),(10.7,286.7),
                                                  (536.7,10.7),(536.7,286.7)),1)])
        with tempfile.TemporaryDirectory() as directory:
            brief = Path(directory)/'brief.json'
            brief.write_text(json.dumps(job))
            with patch.dict(os.environ, SM_JOB=str(brief)):
                cfg = runpy.run_path(str(Path(__file__).resolve().parents[1] /
                                        'pipelines/u_endplates/cfg.py'))
        self.assertEqual(len(cfg['LID_HOLES']),4)
        self.assertEqual(cfg['LONG_X'],[])
        self.assertEqual(cfg['SHORT_Y'],[])
        self.assertEqual({h['id'] for h in cfg['LID_HOLES']},{'F1','F2','F3','F4'})
        self.assertEqual({h['d'] for h in cfg['LID_HOLES']},{4.5})

    def test_handle_mounting_holes_reach_pdf_table(self):
        job = dict(structure='u_endplates', release='TEST', material_cn='201',
                   L=480, W=300, H=230, t=1, Ri=.8, K=.4, g=.5, q=.2,
                   long_x=[80, 240, 400], short_y=[75, 225],
                   handles=dict(profile='handle-85-62-30-v1', cx=[240], cy=150))
        with tempfile.TemporaryDirectory() as directory:
            brief = Path(directory) / 'brief.json'
            brief.write_text(json.dumps(job))
            with patch.dict(os.environ, SM_JOB=str(brief)):
                cfg = runpy.run_path(str(Path(__file__).resolve().parents[1] /
                                        'pipelines/u_endplates/cfg.py'))
        self.assertEqual({(h['x'], h['y'], h['d']) for h in cfg['LID_HOLES']},
                         {(225, 107.5, 6.6), (225, 192.5, 6.6),
                          (255, 119, 6.6), (255, 181, 6.6)})
