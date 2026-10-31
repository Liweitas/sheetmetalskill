# v2.8.2 pipeline u_l_t7u (DEFAULT structure): vendored from 干画图3's /workspace/orders/box-180x420x175/addendum-tools (S-201-1-20261021-007-v1).
# v2.8.2 changes: hardcoded order/skill/tmp paths -> env SM_ORDER (order folder) + this folder; job features from release_config.json.
# assemble named release folder + ASCII OPEN_ME.zip (same layout as S-201-1-20261023-003-v1), plain python3; prefix from cfg (release_config.json)
import shutil,json,zipfile,subprocess,hashlib,sys
from pathlib import Path
sys.path.insert(0,__import__('os').path.dirname(__import__('os').path.abspath(__file__)));import cfg
VER=cfg.VER;B=Path(cfg.B);W=Path(cfg.W);P=Path(cfg.P);OUT=B/'named_release'/VER;ES=B/'evidence_src'
PDF=OUT/f'{VER}_完整折弯工艺PDF_折弯师傅作业图_4页.pdf';assert PDF.exists()
for n in ('README','NAMING_NOTE','CONFIRMATION_DRAFT'):assert (OUT/f'{VER}_{n}.txt').exists(),n
for d in ('STEP','DXF_CUT','DXF_BEND','NEST','PREVIEW','EVIDENCE'):(OUT/d).mkdir(exist_ok=True)
cp=lambda a,b:shutil.copy2(a,b)
# v2.8.2: the release name must be INSIDE every STEP/DXF (gate release_name_inside_step_dxf; 007 failed it).
# STEP: header FILE_NAME/FILE_DESCRIPTION only; DXF: a leading 999 comment. DATA / ENTITIES untouched -> geometry hash unchanged.
import re
def cp_step(a,b,n):
    t=Path(a).read_text(encoding='latin-1');t=re.sub(r"FILE_DESCRIPTION\(\('[^']*'",f"FILE_DESCRIPTION(('{VER} {n} CONFIRMATION DRAFT production_release=false'",t,count=1)
    Path(b).write_text(re.sub(r"FILE_NAME\('[^']*'",f"FILE_NAME('{Path(b).name}'",t,count=1),encoding='latin-1')
def cp_dxf(a,b):Path(b).write_bytes(f'999\n{VER} production_release=false\n'.encode()+Path(a).read_bytes())
for n in ('U','L','LID','ASSEMBLY','EXPLODED'):cp_step(W/f'{n}.step',OUT/'STEP'/f'{VER}_{n}.step',n)
for n in ('U','L','LID'):cp_dxf(W/f'{n}.dxf',OUT/'DXF_CUT'/f'{VER}_CUT_{n}.dxf');cp_dxf(W/f'{n}_BEND.dxf',OUT/'DXF_BEND'/f'{VER}_BEND_{n}.dxf')
cp_dxf(W/'NEST_SHEET01.dxf',OUT/'NEST'/f'{VER}_NEST_2440x1220_SHEET01.dxf')
import tempfile;tmp=Path(tempfile.mkdtemp(prefix='rel_'))   # v2.8.2: was fixed /tmp dir
subprocess.run(['pdftoppm','-r','110','-png',str(PDF),str(tmp/'pg')],check=True)
for i in range(1,5):cp(tmp/f'pg-{i}.png',OUT/'PREVIEW'/f'{VER}_PAGE-{i}.png')
PV=('LID_iso','ASSEMBLY_iso','EXPLODED_iso','LID_CORNER_closeup','NEST_preview')
for k in PV:cp(P/f'{k}.png',OUT/'PREVIEW'/f'{VER}_{k}.png')
E=OUT/'EVIDENCE'
_BR=sorted((B/'briefs').glob('*.brief.json'));assert len(_BR)==1,f'exactly one briefs/*.brief.json expected: {_BR}'   # v2.8.2: was the 007 file name
for src,dst in ((_BR[0],'brief.json'),
                (B/'logs/clearance.json','clearance.json'),(W/'E_main_report.json','main_report.json'),(W/'nest_report.json','nest_report.json'),
                (B/'evidence_src/resolved_job.json','skill_resolved_job.json'),(W/'verification_E.json','verification_E.json'),
                (B/'logs/bend_pdf_dimension_sources.json','pdf_dimension_sources.json'),(B/'logs/verify.json','verify.json'),
                (B/'logs/corner_probe_t7u.json','lid_corner_probe_t7u.json'),(B/'logs/bend_pdf_layout_check.json','pdf_layout_check.json')):cp(src,E/f'{VER}_{dst}')
# zip: one folder named after the release, ASCII-only names, no __MACOSX / dotfiles
z=OUT/f'{VER}_OPEN_ME.zip'
if z.exists():z.unlink()
items=[(OUT/'STEP'/f'{VER}_{n}.step',f'{VER}_{n}.step') for n in ('U','L','LID','ASSEMBLY','EXPLODED')]
items+=[(OUT/'DXF_CUT'/f'{VER}_CUT_{n}.dxf',f'{VER}_CUT_{n}.dxf') for n in ('U','L','LID')]+[(OUT/'DXF_BEND'/f'{VER}_BEND_{n}.dxf',f'{VER}_BEND_{n}.dxf') for n in ('U','L','LID')]
items+=[(OUT/'NEST'/f'{VER}_NEST_2440x1220_SHEET01.dxf',f'{VER}_NEST_2440x1220.dxf'),(PDF,f'{VER}_BEND_PDF_4p.pdf')]
items+=[(OUT/'PREVIEW'/f'{VER}_PAGE-{i}.png',f'{VER}_PAGE{i}.png') for i in range(1,5)]+[(OUT/'PREVIEW'/f'{VER}_{k}.png',f'{VER}_{k}.png') for k in PV]
items+=[(OUT/f'{VER}_README.txt',f'{VER}_README.txt'),(OUT/f'{VER}_NAMING_NOTE.txt',f'{VER}_NAMING_NOTE.txt'),(OUT/f'{VER}_CONFIRMATION_DRAFT.txt',f'{VER}_CONFIRMATION_DRAFT.txt')]
with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as zf:
    zf.writestr(zipfile.ZipInfo(VER+'/'),'')
    for src,arc in sorted(items,key=lambda x:x[1]):
        assert arc.isascii() and arc.startswith(VER),arc;zf.write(src,f'{VER}/{arc}')
with zipfile.ZipFile(z) as zf:
    bad=zf.testzip();names=zf.namelist()
    assert bad is None and all(n.isascii() for n in names) and all(n.startswith(VER+'/') for n in names)
    for src,arc in items:assert zf.read(f'{VER}/{arc}')==Path(src).read_bytes(),arc
# every delivered file starts with VER
bad_names=[str(p) for p in OUT.rglob('*') if p.is_file() and not p.name.startswith(VER)];assert not bad_names,bad_names
# v2.8.2: geometry-only hashes (STEP DATA / DXF ENTITIES with VER->{VER}) so a rename that stamps the new name still compares equal
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'));import release_package as _RP
geo={k:v for k,v in _RP.geomhash(OUT,VER).items() if k.split('/')[0] in ('STEP','DXF_CUT','DXF_BEND','NEST')}
json.dump(geo,open(B/'logs/geometry_sha256.json','w'),indent=1)
print(json.dumps({'zip':str(z),'testzip':bad,'entries':len(names),'sha256':hashlib.sha256(z.read_bytes()).hexdigest()},indent=1))
