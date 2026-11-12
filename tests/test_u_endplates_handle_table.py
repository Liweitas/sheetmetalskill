import json
import os
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import patch


class LidHandleTable(unittest.TestCase):
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
