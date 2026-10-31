# v2.8.2 pipeline u_l_t7u (DEFAULT structure): vendored from 干画图3's /workspace/orders/box-180x420x175/addendum-tools (S-201-1-20261021-007-v1).
# v2.8.2 changes: hardcoded order/skill/tmp paths -> env SM_ORDER (order folder) + this folder; job features from release_config.json.
#!/usr/bin/env python3
# One-step rename of the box-180x420x175 release prefix:  python3 rename_release.py NEWVER
# - writes NEWVER to release_config.json (single source used by cfg.py and every tool)
# - regenerates everything that prints the prefix: iso PNGs (post.py, PNG part only; NEST DXF restored byte-identical),
#   nest preview, 4-page PDF (sm-venv), README / NAMING_NOTE / CONFIRMATION_DRAFT, named folder + OPEN_ME.zip (testzip)
# - removes the old named folder, then verifies STEP/DXF/NEST sha256 are unchanged (logs/geometry_sha256.json)
# Never touches any other order folder.
import sys,json,re,shutil,subprocess,hashlib
from pathlib import Path
import os;B=Path(os.environ['SM_ORDER']);T=Path(__file__).resolve().parent;CFG=B/'release_config.json'   # v2.8.2
if len(sys.argv)!=2:sys.exit('usage: rename_release.py NEWVER')
NEW=sys.argv[1].strip()
if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*',NEW):sys.exit('NEWVER must be ASCII letters/digits/._- only: '+NEW)
conf=json.load(open(CFG));OLD=conf['VER']
if NEW==OLD:sys.exit('NEWVER equals current prefix')
OLDDIR=B/'named_release'/OLD;NEWDIR=B/'named_release'/NEW
if NEWDIR.exists():sys.exit(f'{NEWDIR} already exists')
geo_before=json.load(open(B/'logs/geometry_sha256.json'))
FC='/opt/freecad-dl/FreeCAD-1.1.1/usr/bin/python';AV='/workspace/addendum-venv/bin/python';SV='/workspace/sm-venv/bin/python'
W=B/'work_main';keep={p:p.read_bytes() for p in (W/'NEST_SHEET01.dxf',W/'nest_report.json')}
import tempfile;BK=Path(tempfile.mkdtemp(prefix='rename_bk_'))/'bk'   # v2.8.2
for d in ('post_out','logs'):shutil.copytree(B/d,BK/d)
def run(cmd):
    print('>>',' '.join(map(str,cmd)));subprocess.run(cmd,cwd=T,check=True)
conf['VER']=NEW;conf.setdefault('history',[]).append(OLD);json.dump(conf,open(CFG,'w'),indent=1,ensure_ascii=False)
try:
    run([AV,'post.py',str(W),str(B/'post_out')])
    for p,b in keep.items():p.write_bytes(b)          # nest geometry stays byte-identical
    run([AV,'nest_png.py',str(W/'NEST_SHEET01.dxf'),str(B/'post_out'/'NEST_preview.png'),f'{NEW}  NEST 2440x1220 SHEET01 - cut only, no bend lines'])
    run([SV,'make_bend_pdf.py'])
    run(['python3','make_readme.py'])
    run(['python3','release.py'])
except Exception:
    for p,b in keep.items():p.write_bytes(b)
    for d in ('post_out','logs'):shutil.rmtree(B/d);shutil.copytree(BK/d,B/d)
    conf['VER']=OLD;conf['history'].pop();json.dump(conf,open(CFG,'w'),indent=1,ensure_ascii=False)
    shutil.rmtree(NEWDIR,ignore_errors=True);print('FAILED - prefix reverted to',OLD);raise
geo_after=json.load(open(B/'logs/geometry_sha256.json'))
assert geo_after==geo_before,'geometry hash changed!'
if OLDDIR.exists():shutil.rmtree(OLDDIR)
left=[str(p) for p in NEWDIR.rglob('*') if p.is_file() and not p.name.startswith(NEW)]
assert not left,left
print(json.dumps({'old':OLD,'new':NEW,'folder':str(NEWDIR),'geometry_sha256_unchanged':True,'files':sum(1 for p in NEWDIR.rglob('*') if p.is_file())},indent=1))
