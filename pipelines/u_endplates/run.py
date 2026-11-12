#!/usr/bin/env python3
"""v2.8.3 pipeline u_endplates - end-to-end runner (03 lid corners + flat outer end plates; corner03.py + native03_check.py MANDATORY) (order of steps follows 干画图3 §1.5: cfg -> build -> post -> checks -> pdf -> docs -> release).
usage: python3 run.py BRIEF.json OUT_DIR       (OUT_DIR/work, OUT_DIR/stage/{VER}, OUT_DIR/{VER}_CONFIRM_DRAFT.zip)
Nothing is sent anywhere; the confirmation text is a DRAFT file for the user to review.
env overrides: SM_FC (FreeCAD python), SM_AV (python with ezdxf+matplotlib), SM_ORDERS (name-collision scan root)."""
import json, os, re, shutil, subprocess, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent; SK = HERE.parents[1]
FC = os.environ.get('SM_FC', '/opt/freecad-dl/FreeCAD-1.1.1/usr/bin/python'); AV = os.environ.get('SM_AV', '/workspace/addendum-venv/bin/python')
if len(sys.argv) != 4 or sys.argv[3] != '--geometry-only':
    raise SystemExit('Internal geometry worker; use sm golden / MCP sheetmetal_job')
brief_p = Path(sys.argv[1]).resolve(); out = Path(sys.argv[2]).resolve(); job = json.load(open(brief_p)); VER = job['release']
W = out / 'work'; S = out / 'stage' / VER
assert not W.exists() and not S.exists(), 'fresh output dir required (never overwrite a release)'
env = {**os.environ, 'SM_JOB': str(brief_p)}
sys.path.insert(0, str(SK / 'scripts'))
from execution_log import run_stage
logs = out / 'logs'
def run(*c):
    return run_stage(logs, Path(str(c[1])).stem, c, env=env)
run(FC, HERE / 'build.py', W)
sys.path.insert(0, str(HERE)); os.environ['SM_JOB'] = str(brief_p); import cfg as C   # same brief -> same values as build
SMP = os.environ.get('SHEETMETAL_PATH', '/workspace/sheetmetal/SheetMetal'); FCLIB = os.environ.get('SM_FCLIB', '/opt/freecad-dl/FreeCAD-1.1.1/usr/lib')
run(sys.executable, HERE / 'project03.py', W / 'project03.json')
run(FC, HERE / 'corner_slice03.py', W / 'LID.step', W / 'corner03_closure_sections.json')
run(FC, HERE / 'corner_probe03.py', W / 'LID.step', W / 'corner03_closure_rays.json')
S.mkdir(parents=True)
run(AV, HERE / 'post.py', W, S)
# STEP: copy with the release name in file name and header (DATA section untouched -> geometry hash unchanged)
(S / 'STEP').mkdir()
for p in sorted(W.glob('*.step')):
    if p.stem == 'BODY': continue   # native03 input only
    b = p.read_text(encoding='latin-1'); n = p.stem; fn = f'{VER}_{n}.step'
    b = b.replace("FILE_DESCRIPTION(('FreeCAD Model')", f"FILE_DESCRIPTION(('{VER} {n} CUSTOMER CONFIRMATION DRAFT - NOT FOR PRODUCTION (production_release=false)')", 1)
    b = re.sub(r"FILE_NAME\('[^']*'", f"FILE_NAME('{fn}'", b, count=1)
    (S / 'STEP' / fn).write_text(b, encoding='latin-1')
# conflict checks (v2.8.2 audit #8)
# v2.8.3 mandatory 03 checks on the RELEASED CUT_LID.dxf (skill scripts; exit code honoured, never silently switched)
cut_lid = S / 'DXF_CUT' / f'{VER}_CUT_LID.dxf'
r3 = run(sys.executable, SK / 'scripts/corner03.py', W / 'project03.json', '--dxf', cut_lid)
shutil.copy2(logs / 'corner03.stdout.log', W / 'corner03.json')
def native03(unfold, dxf, outp):
    return run_stage(logs, outp.stem, [FC, SK / 'scripts/native03_check.py', W / 'project03.json', '--formed', W / 'LID.step', '--unfold', unfold, '--dxf', dxf, '--body', W / 'BODY.step',
                           '--output', outp, '--module-path', FCLIB, '--module-path', SMP], cwd=SK / 'scripts', env=env).returncode
rn = native03(W / 'LID_UNFOLD.step', cut_lid, W / 'native03.json')
if (W / 'native_untrimmed').exists():   # corner_gap 0: native unfold double-counts the shared corner column; keep that run as evidence
    native03(W / 'native_untrimmed/LID_UNFOLD.step', W / 'native_untrimmed/LID_CUT_raw.dxf', W / 'native03_untrimmed_native_unfold.json')
print('corner03 rc', r3.returncode, '| native03 rc', rn)
if r3.returncode: sys.exit('corner03.py FAILED - see work/corner03.json; no release')
if rn and os.environ.get('SM_ACCEPT_NATIVE03_FAIL') != '1':
    sys.exit('native03_check FAILED - see work/native03.json. Report the numbers to the user; do NOT change corner_gap silently. '
             'Only with an explicit user decision set SM_ACCEPT_NATIVE03_FAIL=1 (recorded in the release).')
print('GEOMETRY_DONE', W, flush=True)
