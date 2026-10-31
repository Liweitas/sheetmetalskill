#!/usr/bin/env python3
"""Formed-only dimensional review with real STEP/PNG; permits unknown material/K, no manufacture."""
import argparse,json,os,subprocess,sys,hashlib
from pathlib import Path
from design_job import resolve_job
from runtime_paths import locate,probe
ROOT=Path(__file__).resolve().parents[1]
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('job');ap.add_argument('--output',required=True);ap.add_argument('--review-note',action='append',default=[])
 for name in ['cad-python','freecad-lib','sheetmetal-path','pdf-renderer']:ap.add_argument('--'+name)
 a=ap.parse_args();out=Path(a.output).resolve();created=False
 try:
  if out.exists():raise ValueError('Output must not exist')
  source=Path(a.job).resolve();job=json.loads(source.read_text());r=resolve_job(job,review_only=True);r['review_only']=True;r['review_notes']=a.review_note;runtime=locate(a.cad_python,a.freecad_lib,a.sheetmetal_path,a.pdf_renderer);probe(runtime,ROOT);out.mkdir(parents=True);created=True;resolved=out/'review_resolved_job.json';resolved.write_text(json.dumps(r,indent=2));(out/'review_source_job.json').write_bytes(source.read_bytes())
  cmd=[runtime['cad_python'],'-B',str(ROOT/'scripts/cad_build.py'),str(resolved),'--output',str(out/'cad'),'--sheetmetal-path',runtime['sheetmetal_path'],'--formed-review-only']
  if runtime['freecad_lib']:cmd+=['--freecad-lib',runtime['freecad_lib']]
  with (out/'review_CAD.log').open('wb') as log:result=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=900,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
  if result.returncode:raise RuntimeError('Formed review CAD failed; inspect review_CAD.log')
  from confirmation_png import previews
  report=json.loads((out/'cad/cad_report.json').read_text());pics=previews(r,report,json.loads((out/'cad/preview_mesh.json').read_text()),out,'FORMED_REVIEW_HOLD');receipt={'status':'FORMED_REVIEW_ONLY_HOLD','CAD_executed':True,'strict_BOP_checked_including_export_readback':True,'planned_parts':list(report['parts']),'actual_holes':len(report['holes']),'material':job['material'],'manufacturing_K':r['K_ANSI'],'proposed_corner_scheme':job.get('lid',{}).get('corner_scheme','03'),'manufacturing_delivery_complete':False,'production_release':False,'no_DXF_or_bend_allowance_generated':True,'confirmation_images':[p.name for p in pics],'source_job_sha256':hashlib.sha256(source.read_bytes()).hexdigest()};receipt['review_notes']=a.review_note;receipt['artifacts']=[{'path':str(p.relative_to(out)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(out.rglob('*')) if p.is_file()];(out/'FORMED_REVIEW_RESULT.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt,indent=2))
 except Exception as ex:
  failure={'status':'BLOCKED','error':str(ex),'production_release':False}
  if created:(out/'BLOCKED_RESULT.json').write_text(json.dumps(failure,indent=2))
  print(json.dumps(failure),file=sys.stderr);raise SystemExit(2)
if __name__=='__main__':main()
