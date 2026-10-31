#!/usr/bin/env python3
"""Record explicitly supplied this-job user acceptance in a new job copy; no CAD/geometry changes.
The agent must verify source/quote against the actual user instruction. This CLI cannot authenticate it.
"""
import argparse,copy,json,hashlib
from pathlib import Path
from design_job import resolve_job
from site_fit import design_sha256,require_delivery_decision

def record(job,source,quote):
 if job.get('site_fit_acceptance') is not None:raise ValueError('SITE_FIT: source already contains acceptance; do not silently replace it')
 if not source.strip() or not quote.strip():raise ValueError('SITE_FIT: user authorization source and exact quote required')
 d=copy.deepcopy(job)
 d['site_fit_acceptance']={'scope':'this_job_only','job_id':d['id'],'job_design_sha256':design_sha256(job),'issue':'lid_root_interference','disposition':'site_fit_and_trial_assembly','authorization_source':source,'authorization_quote':quote,'authorized_by':'user','geometry_interference_eliminated':False,'trial_assembly_confirmed':False}
 r=resolve_job(d);require_delivery_decision(r)
 return d,{'status':'USER_AUTHORIZED_SITE_FIT_TRIAL_REQUIRED','dimensions_modified':False,'source_design_sha256':design_sha256(job),'accepted_design_sha256':design_sha256(d),'acceptance':r['site_fit_acceptance'],'fit':r['fit'],'geometry_interference_eliminated':False,'trial_assembly_confirmed':False,'production_release':False}

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('job');ap.add_argument('--output',required=True);ap.add_argument('--authorization-source',required=True);ap.add_argument('--authorization-quote',required=True);a=ap.parse_args()
 try:
  source=Path(a.job).resolve();out=Path(a.output).resolve()
  if out.exists() or out==source or out in source.parents:raise ValueError('OUTPUT_EXISTS_OR_CONTAINS_INPUT: choose a new directory')
  original=source.read_bytes();d,r=record(json.loads(original),a.authorization_source,a.authorization_quote)
  r.update(source_file=source.name,source_file_sha256=hashlib.sha256(original).hexdigest())
  out.mkdir(parents=True);(out/'site-fit.job.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n');(out/'AUTHORIZATION_RECORD.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'status':r['status'],'job':str(out/'site-fit.job.json'),'record':str(out/'AUTHORIZATION_RECORD.json'),'geometry_modified':False,'production_release':False},ensure_ascii=False))
 except (ValueError,OSError,KeyError) as ex:ap.exit(2,json.dumps({'status':'BLOCKED','error':str(ex),'production_release':False},ensure_ascii=False)+'\n')
if __name__=='__main__':main()
