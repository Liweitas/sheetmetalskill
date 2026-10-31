#!/usr/bin/env python3
"""Integrity/source check of a confirmation dossier; never a manufacturing acceptance gate."""
import argparse,hashlib,json,zipfile
from pathlib import Path
from general_process import compile_brief
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def check(root):
 root=Path(root).resolve();sp=list(root.glob('*GENERAL_REVIEW_STATUS.json'))
 if len(sp)!=1:raise ValueError('GENERAL_REVIEW_STATUS_REQUIRED')
 s=json.loads(sp[0].read_text())
 if s.get('contract')!='general-confirmation-only-v1' or any(s.get(k) is not False for k in ['production_release','manufacturing_delivery_complete','digital_manufacturing_complete']):raise ValueError('GENERAL_REVIEW_FALSE_RELEASE_OR_COMPLETENESS')
 catalog=s['artifacts'];paths=[a['path'] for a in catalog]
 if len(paths)!=len(set(paths)):raise ValueError('GENERAL_REVIEW_DUPLICATE_ARTIFACT')
 for a in catalog:
  p=root/a['path']
  if not p.resolve().is_relative_to(root) or not p.is_file() or sha(p)!=a['sha256']:raise ValueError('GENERAL_REVIEW_ARTIFACT_HASH')
  if p.suffix.lower()=='.dxf':raise ValueError('GENERAL_REVIEW_CANNOT_CLAIM_MANUFACTURING_DXF')
 def one(stem):
  x=[root/p for p in paths if Path(p).name.endswith(stem)]
  if len(x)!=1:raise ValueError('GENERAL_REVIEW_SOURCE_REQUIRED: '+stem)
  return x[0]
 source=one('original_brief.json');compiled=compile_brief(json.loads(source.read_text()))
 if sha(source)!=s['source_brief_sha256'] or json.loads(one('confirmation_parameters.json').read_text())!=compiled:raise ValueError('GENERAL_REVIEW_ORIGINAL_INPUT_AUTHORITY')
 if bool(compiled['job'])!=s['actual_CAD_executed']:raise ValueError('GENERAL_REVIEW_FALSE_CAD_EXECUTION')
 if compiled.get('job'):
  report=json.loads(one('cad_report.json').read_text())
  if report['intersections']!=s['actual_intersections'] or report.get('formed_review_only') is not True:raise ValueError('GENERAL_REVIEW_ACTUAL_REPORT_MISMATCH')
 z=list(root.glob('*.zip'))
 if len(z)!=1:raise ValueError('GENERAL_REVIEW_SINGLE_ZIP_REQUIRED')
 with zipfile.ZipFile(z[0]) as f:
  expected={root.name+'/'+p for p in paths}|{root.name+'/'+sp[0].name}
  if f.testzip() or set(f.namelist())!=expected:raise ValueError('GENERAL_REVIEW_ZIP_COVERAGE')
  for p in paths+[sp[0].name]:
   if hashlib.sha256(f.read(root.name+'/'+p)).hexdigest()!=sha(root/p):raise ValueError('GENERAL_REVIEW_ZIP_BYTES')
 return {'ok':True,'scope':'source and confirmation dossier integrity only; not independent geometry/manufacturing acceptance','manufacturing_delivery_complete':False,'production_release':False,'zip':str(z[0]),'zip_sha256':sha(z[0]),'artifacts':len(paths)}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('root');a=p.parse_args()
 try:r=check(a.root)
 except Exception as e:r={'ok':False,'error':str(e),'production_release':False}
 print(json.dumps(r,ensure_ascii=False,indent=2));raise SystemExit(0 if r['ok'] else 2)
