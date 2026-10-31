#!/usr/bin/env python3
"""v2.8.3 pipeline u_endplates - end-to-end runner (03 lid corners + flat outer end plates; corner03.py + native03_check.py MANDATORY) (order of steps follows 干画图3 §1.5: cfg -> build -> post -> checks -> pdf -> docs -> release).
usage: python3 run.py BRIEF.json OUT_DIR       (OUT_DIR/work, OUT_DIR/stage/{VER}, OUT_DIR/{VER}_CONFIRM_DRAFT.zip)
Nothing is sent anywhere; the confirmation text is a DRAFT file for the user to review.
env overrides: SM_FC (FreeCAD python), SM_AV (python with ezdxf+matplotlib), SM_ORDERS (name-collision scan root)."""
import json, os, re, shutil, subprocess, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent; SK = HERE.parents[1]
FC = os.environ.get('SM_FC', '/opt/freecad-dl/FreeCAD-1.1.1/usr/bin/python'); AV = os.environ.get('SM_AV', '/workspace/addendum-venv/bin/python')
brief_p = Path(sys.argv[1]).resolve(); out = Path(sys.argv[2]).resolve(); job = json.load(open(brief_p)); VER = job['release']
W = out / 'work'; S = out / 'stage' / VER
assert not W.exists() and not S.exists(), 'fresh output dir required (never overwrite a release)'
env = {**os.environ, 'SM_JOB': str(brief_p)}
def run(*c): print('+', ' '.join(map(str, c)), flush=True); subprocess.run(list(map(str, c)), check=True, env=env)
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
r3 = subprocess.run([sys.executable, SK / 'scripts/corner03.py', W / 'project03.json', '--dxf', cut_lid], capture_output=True, text=True); (W / 'corner03.json').write_text(r3.stdout)
def native03(unfold, dxf, outp):
    return subprocess.run([FC, 'native03_check.py', W / 'project03.json', '--formed', W / 'LID.step', '--unfold', unfold, '--dxf', dxf, '--body', W / 'BODY.step',
                           '--output', outp, '--module-path', FCLIB, '--module-path', SMP], cwd=SK / 'scripts', capture_output=True, text=True).returncode
rn = native03(W / 'LID_UNFOLD.step', cut_lid, W / 'native03.json')
if (W / 'native_untrimmed').exists():   # corner_gap 0: native unfold double-counts the shared corner column; keep that run as evidence
    native03(W / 'native_untrimmed/LID_UNFOLD.step', W / 'native_untrimmed/LID_CUT_raw.dxf', W / 'native03_untrimmed_native_unfold.json')
print('corner03 rc', r3.returncode, '| native03 rc', rn)
if r3.returncode: sys.exit('corner03.py FAILED - see work/corner03.json; no release')
if rn and os.environ.get('SM_ACCEPT_NATIVE03_FAIL') != '1':
    sys.exit('native03_check FAILED - see work/native03.json. Report the numbers to the user; do NOT change corner_gap silently. '
             'Only with an explicit user decision set SM_ACCEPT_NATIVE03_FAIL=1 (recorded in the release).')
if not (C.TEMPLATE_OK and C.CORNER_GAP == 0 and (W / 'native03_untrimmed_native_unfold.json').exists()):
    sys.exit('CAD/DXF/03 checks done. pdf.py/docs.py are a text template validated only for 400x220x150 corner_gap 0 - write job-specific PDF/DOC text before release.')
rep = json.load(open(W / 'report.json')); P = rep['parts']; pr = rep['params']
cp = {'t': pr['t'], 'Ri': pr['Ri'], 'K': pr['K_ANSI'], 'g': pr['g'], 'q': pr['q'], 'm4_count': len(rep['holes']),
      'deep_u': [{'part': 'U', 'wall_h': pr['Hb'], 'inner_w': pr['W'] - 2 * pr['t']}],
      'requested': {'handles': bool(job.get('handles')), 'roof_ports': bool(job.get('roof_ports'))},
      'features': {'handles': len(rep.get('handle_holes', [])), 'roof_ports': 0}}
json.dump(cp, open(W / 'conflict_params.json', 'w'), indent=1)
r = subprocess.run([sys.executable, SK / 'scripts/conflict_checks.py', W / 'conflict_params.json', W / 'report.json'], capture_output=True, text=True)
(W / 'conflicts.json').write_text(r.stdout); conf = json.loads(r.stdout)
if r.returncode: sys.exit('conflict ERROR - resolve or get explicit user acceptance first:\n' + r.stdout)
run(AV, HERE / 'pdf.py', W, S)
for p_ in S.glob('*.pdf'):   # ASCII release file name (gate: ASCII names)
    if p_.name != f'{VER}_BEND_PDF_A3_CN.pdf': p_.rename(S / f'{VER}_BEND_PDF_A3_CN.pdf')
print('+ docs.py', S, flush=True); subprocess.run([AV, str(HERE / 'docs.py'), str(S)], check=True, env=env, cwd=out)   # docs/preview read ./work
sys.path.insert(0, str(SK / 'scripts')); import confirm_draft
txt, pend = confirm_draft.build(job | {'Ri': pr['Ri'], 'K': pr['K_ANSI']}, conf, True)
(S / 'DOC' / f'{VER}_CONFIRMATION_DRAFT.txt').write_text(txt, encoding='utf-8')
# evidence + sources (reproducible)
E = S / 'EVIDENCE'; E.mkdir(exist_ok=True)
for n in ('report.json', 'dxf_checks.json', 'conflicts.json', 'project03.json', 'corner03.json', 'native03.json', 'native03_untrimmed_native_unfold.json', 'corner03_closure_sections.json', 'corner03_closure_rays.json'):
    if (W / n).exists(): shutil.copy(W / n, E / f"{VER}_{'cad_report.json' if n == 'report.json' else n}")
shutil.copy(brief_p, E / f'{VER}_brief.json')
for p in sorted(HERE.glob('*.py')): shutil.copy(p, E / f'{VER}_src_{p.name}')
# previews (PDF_P1, lid top crop, NEST, end-corner isos, LID_CORNER03_CLOSEUP, LID_FLAT_CORNER03_DETAIL)
subprocess.run([AV, str(HERE / 'preview.py'), str(S)], check=True, cwd=out)
# gate + single ASCII zip
run(sys.executable, SK / 'scripts/release_package.py', 'package', S, VER, '--zip', out / f'{VER}_CONFIRM_DRAFT.zip', '--pdf-pages', '4', '--pdf-max-pages', '4',
    '--orders', os.environ.get('SM_ORDERS', '/workspace/orders'), '--dxf-python', AV)
print('DONE', out / f'{VER}_CONFIRM_DRAFT.zip'); print('pending (待确认):', *pend, sep='\n  ')
