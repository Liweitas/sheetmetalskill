#!/usr/bin/env python3
"""Existing STEP entry: audit every solid, unfold supported pieces, report partial/HOLD honestly."""
import argparse,csv,hashlib,json,os,re,shutil,subprocess,sys
from pathlib import Path
from source_contract import config_for,delivery_state
ROOT=Path(__file__).resolve().parents[1]
sha=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()
def execute_core(a):
 src=Path(a.source).resolve();out=Path(a.output).resolve()
 if src.suffix.lower() not in ['.stp','.step']:raise ValueError('Expected an existing STEP file')
 if out.exists() or out==src or out in src.parents:raise ValueError('Output must be new and cannot contain/replace source')
 digest=sha(src)
 if a.expect_sha256 and digest!=a.expect_sha256:raise ValueError('Source SHA256 mismatch')
 cfg=config_for(json.loads(Path(a.config).read_text()) if a.config else {})
 if a.diagnostic_K is not None:cfg['diagnostic_K_ANSI']=a.diagnostic_K;cfg=config_for(cfg)
 # Part.read works in mm; this bounded imported adapter requires explicit source millimetres.
 # STEP headers may contain legacy local-codepage filenames; unit tokens are ASCII.
 header=src.read_bytes().decode('latin-1');mm=bool(re.search(r'SI_UNIT\s*\(\s*\.MILLI\.\s*,\s*\.METRE\.\s*\)',header,re.I))
 if not mm:raise ValueError('SOURCE_UNITS_UNSUPPORTED_OR_UNKNOWN: explicit STEP SI_UNIT(.MILLI.,.METRE.) required; do not infer units from bbox')
 from runtime_paths import locate,probe
 import reportlab,pypdf,numpy
 from PIL import Image
 runtime=locate(a.cad_python,a.freecad_lib,a.sheetmetal_path,a.pdf_renderer);runtime_probe=probe(runtime,ROOT)
 out.mkdir(parents=True);a.created=out;a.phase='CAD_source_audit';source_copy=out/('source_original'+src.suffix.lower());shutil.copy2(src,source_copy);config_path=out/'source_config.json';config_path.write_text(json.dumps(cfg,indent=2));(out/'runtime.json').write_text(json.dumps({'runtime':runtime,'probe':runtime_probe,'source_unit_evidence':'actual source SI_UNIT(.MILLI.,.METRE.)','no_unit_scaling_in_DXF':True},indent=2))
 cmd=[runtime['cad_python'],'-B',str(ROOT/'scripts/step_audit_cad.py'),str(source_copy),'--config',str(config_path),'--output',str(out/'cad'),'--module-path',runtime['sheetmetal_path']]
 if runtime['freecad_lib']:cmd+=['--module-path',runtime['freecad_lib']]
 with (out/'CAD_execution.log').open('wb') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=1500,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
 if r.returncode:raise RuntimeError('Source CAD audit failed; inspect CAD_execution.log and partial source_audit.json')
 report=json.loads((out/'cad/source_audit.json').read_text());assert digest==sha(source_copy)==sha(src)==report['source_sha256'];report['source_external_original_sha256']=digest
 from source_drawing_pdf import write_source_pdf
 a.phase='source_review_PDF';pdf=out/'SOURCE_REVIEW_BENDING_PARTIAL_HOLD.pdf';drawings=write_source_pdf(report,json.loads((out/'cad/source_projections.json').read_text()),pdf)
 (out/'SOURCE_DRAWING_GEOMETRY.json').write_text(json.dumps(drawings,indent=2))
 a.phase='source_confirmation_PNG'
 from source_confirmation import write_source_previews
 pictures=write_source_previews(report,json.loads((out/'cad/source_mesh.json').read_text()),out)
 with (out/'source_holes.csv').open('w',newline='') as f:
  writer=csv.writer(f);writer.writerow(['part','id','D_mm','X','Y','Z','axis_X','axis_Y','axis_Z','source_faces'])
  for p in report['parts']:
   for h in p['holes']:writer.writerow([p['id'],h['id'],h['D_mm'],*h['center_mm'],*h['axis'],str(h['source_faces'])])
 a.phase='source_PDF_render';preview=out/'preview';preview.mkdir()
 with (out/'PDF_render.log').open('wb') as log:r=subprocess.run([runtime['pdf_renderer'],'-png','-r','90',str(pdf),str(preview/'page')],stdout=log,stderr=subprocess.STDOUT,timeout=300)
 rendered=len(list(preview.glob('page-*.png')))
 if r.returncode or rendered!=drawings['pages']:raise ValueError('Source PDF rendering incomplete')
 state=delivery_state(report)
 result={**state,'version':'2.6.1-R06','source_sha256':digest,'source_unchanged':sha(src)==digest,'CAD_executed':True,'CAD_audit_complete':True,'artifact_verification':'source_manifest_check.json; rerun validator for fresh actual geometry proof','all_source_parts_in_PDF':True,'PDF_visual_review_required':True,'pdf_pages':drawings['pages'],'manifest':'source_manifest.json','pdf':pdf.name,'native03_executed':False,'source_corner_policy':'preserve existing source; no default03 applied','structure_changed':False,'model_healing_selected':False,'manufacturing_K':cfg['K_ANSI'],'diagnostic_K':cfg.get('diagnostic_K_ANSI')}
 (out/'AUDIT_RESULT.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 if state['status']=='PARTIAL_HOLD':(out/'BLOCKED_RESULT.json').write_text(json.dumps({**result,'blocking_scope':'complete manufacturing delivery','partial_files_are_not_delivery':True},ensure_ascii=False,indent=2)+'\n')
 manifest={**state,'contract_version':'2.6.1-R06','audit_result':'AUDIT_RESULT.json','source_report':'cad/source_audit.json','source_copy':source_copy.name,'pdf':pdf.name,'pdf_pages':drawings['pages'],'rendered_pages':rendered,'all_source_part_ids':drawings['all_source_part_ids'],'confirmation_images':[p.name for p in pictures],'artifacts':[{'path':str(p.relative_to(out)),'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(out.rglob('*')) if p.is_file()]}
 (out/'source_manifest.json').write_text(json.dumps(manifest,indent=2));a.phase='source_audit_complete_gate'
 from validate_source_manifest import check_source
 gate=check_source(out,manifest,runtime=runtime,expected_source_sha256=digest);(out/'source_manifest_check.json').write_text(json.dumps(gate,indent=2))
 if not gate['ok']:raise ValueError('Source audit evidence gate failed: '+str(gate['errors']))
 return 0 if state['status']=='AUDIT_COMPLETE_WITH_HOLD' else 2

def execute(a):
 from delivery_contract import revision_root
 from source_delivery import finalize_source
 name=a.entity_id or re.sub('[^A-Za-z0-9_-]','_',Path(a.source).stem)
 meta={'namespace':a.namespace,'entity_id':name}
 if a.revision:meta['revision']=a.revision
 root,d=revision_root(a.output,{'id':name,'delivery':meta});a.output=str(root)
 execute_core(a)
 a.phase='source_partial_delivery_envelope';result=finalize_source(root,d)
 print(json.dumps(result,ensure_ascii=False,indent=2));return 2

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('source');ap.add_argument('--output',required=True);ap.add_argument('--config');ap.add_argument('--expect-sha256');ap.add_argument('--diagnostic-K',dest='diagnostic_K',type=float)
 for name in ['cad-python','freecad-lib','sheetmetal-path','pdf-renderer']:ap.add_argument('--'+name)
 ap.add_argument('--namespace',choices=['customer','requirement'],default='requirement');ap.add_argument('--entity-id');ap.add_argument('--revision')
 a=ap.parse_args()
 try:code=execute(a)
 except Exception as ex:
  r={'status':'BLOCKED','stage':getattr(a,'phase','source_or_dependency_preflight'),'error':str(ex),'production_release':False,'manufacturing_delivery_complete':False}
  if hasattr(a,'created'):
   r['partial_files']=[{'path':str(p.relative_to(a.created)),'sha256':sha(p)} for p in a.created.rglob('*') if p.is_file()];(a.created/'BLOCKED_RESULT.json').write_text(json.dumps(r,indent=2))
  print(json.dumps(r),file=sys.stderr);code=2
 raise SystemExit(code)
if __name__=='__main__':main()
