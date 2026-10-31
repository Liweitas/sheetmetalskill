#!/usr/bin/env python3
"""Author-only synthetic site-fit/isometric end-to-end test; never independent acceptance."""
import argparse,copy,json,hashlib,subprocess,sys
from pathlib import Path
from record_site_fit import record
from validate_manifest import check
ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',required=True)
 for f in ['cad-python','freecad-lib','sheetmetal-path','pdf-renderer']:ap.add_argument('--'+f)
 a=ap.parse_args();out=Path(a.output).resolve()
 if out.exists():ap.error('Output must not exist')
 out.mkdir(parents=True);initial={str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'scripts').glob('*.py')};cases=[];negative=[];extra=[]
 for key in ['cad_python','freecad_lib','sheetmetal_path','pdf_renderer']:
  if getattr(a,key):extra+=['--'+key.replace('_','-'),getattr(a,key)]
 for name,example in [('external','regression-A-center18.job.json'),('wrap_l','regression-B-center18.job.json')]:
  job=json.loads((ROOT/'assets/examples'/example).read_text());job['id']='R05_SYNTHETIC_'+name.upper();source=out/(name+'-unaccepted.job.json');source.write_text(json.dumps(job,indent=2))
  cmd=[sys.executable,'-B',str(ROOT/'scripts/build_package.py'),str(source),'--output',str(out/(name+'-must-block')),*extra];r=subprocess.run(cmd,capture_output=True,text=True,timeout=120)
  if r.returncode!=2 or 'LID_ROOT_FIT_REVIEW_REQUIRED' not in r.stderr or (out/(name+'-must-block')).exists():raise RuntimeError('Unauthorised conflicting design was not blocked before CAD')
  negative.append({'case':name,'test':'unaccepted known conflict','rejected':True,'stderr':r.stderr})
  accepted,receipt=record(job,'SYNTHETIC SELFTEST explicit user authorization for '+job['id']+' only; NOT real customer consent','For this synthetic test retain Ri0.8/g0.5/q0 and actual lid-root interference for site fitting and trial assembly; geometry is unchanged and trial is not confirmed.')
  source=out/(name+'.job.json');source.write_text(json.dumps(accepted,indent=2));(out/(name+'_authorization.json')).write_text(json.dumps(receipt,indent=2));dest=out/name
  cmd=[sys.executable,'-B',str(ROOT/'scripts/build_package.py'),str(source),'--output',str(dest),*extra]
  with (out/(name+'.log')).open('wb') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=1200)
  if r.returncode:raise RuntimeError(name+' failed: inspect '+str(out/(name+'.log')))
  from factory_naming import published_root
  dest=published_root(dest)
  result_path=next(dest.glob('*RUN_RESULT_*.json'));result=json.loads(result_path.read_text());project=json.loads((dest/result['project']).read_text());manifest=json.loads((dest/result['manifest']).read_text());base=check(project,manifest,dest)
  expected=['LID','U'] if name=='external' else ['L','LID','U']
  if not base['ok'] or result['status']!='DELIVERED_FOR_AUTHORIZED_SITE_FIT_WITH_HOLD' or result['assembly_interference_free'] is not False or result['actual_root_overlap_volume_mm3']<=0 or result['formed_isometric_parts']!=expected or result['geometry_interference_eliminated'] or result['trial_assembly_confirmed'] or result['pdf_pages']!=result['pdf_rendered_pages']:raise RuntimeError('Actual retained geometry/status/isometric coverage failed '+name+': '+str(base['errors']))
  tests={
   'missing isometric report':lambda m:m.pop('formed_isometric_report'),
   'missing U DXF':lambda m:m.update(artifacts=[x for x in m['artifacts'] if not (x.get('kind')=='dxf' and x.get('part_ids')==['U'])]),
   'missing mandatory native03':lambda m:next(x for x in m['artifacts'] if x.get('kind')=='dxf' and x.get('part_ids')==['LID']).pop('native_geometry_report')}
  for label,mutate in tests.items():
   m=copy.deepcopy(manifest);mutate(m);c=check(project,m,dest)
   if c['ok']:raise RuntimeError(label+' unexpectedly passed')
   negative.append({'case':name,'test':label,'rejected':True,'errors':c['errors']})
  # Use only isolated copies, and rebind changed report SHA so this tests state/geometry, not just hashes.
  for label,field,new in [('false interference eliminated','geometry_interference_eliminated',True),('false zero overlap','actual_root_overlap_volume_mm3',0),('false final state','status','GEOMETRY_CHECKED_WITH_HOLD')]:
   original=result_path.read_bytes();tampered=copy.deepcopy(result);tampered[field]=new
   try:
    result_path.write_text(json.dumps(tampered,indent=2));m=copy.deepcopy(manifest);next(x for x in m['artifacts'] if x.get('kind')=='run_result')['sha256']=sha(result_path);c=check(project,m,dest)
    if c['ok']:raise RuntimeError(label+' unexpectedly passed')
    negative.append({'case':name,'test':label+' with rebound SHA','rejected':True,'errors':c['errors']})
   finally:result_path.write_bytes(original)
  iso=dest/result['formed_isometric_report'];original=iso.read_bytes()
  for label,mutate in [('missing formed lid view',lambda d:d['views'].pop('LID')),('wrong isometric map',lambda d:d['views']['U']['pdf_map'].__setitem__(4,d['views']['U']['pdf_map'][4]+5)),('missing bend direction',lambda d:d['views']['U']['bend_labels'][0].pop('direction'))]:
   d=json.loads(original);mutate(d)
   try:
    iso.write_text(json.dumps(d,indent=2));m=copy.deepcopy(manifest);next(x for x in m['artifacts'] if x.get('kind')=='formed_isometric_report')['sha256']=sha(iso);c=check(project,m,dest)
    if c['ok']:raise RuntimeError(label+' unexpectedly passed')
    negative.append({'case':name,'test':label+' with rebound SHA','rejected':True,'errors':c['errors']})
   finally:iso.write_bytes(original)
  if not check(project,manifest,dest)['ok']:raise RuntimeError('Original test output was not restored')
  cases.append({'case':name,'result':str(result_path),'status':result['status'],'root_overlap_mm3':result['actual_root_overlap_volume_mm3'],'isometric_parts':result['formed_isometric_parts'],'PDF_pages':result['pdf_pages'],'PDF_rendered_pages':result['pdf_rendered_pages'],'geometry_interference_eliminated':False,'trial_assembly_confirmed':False})
 if initial!={str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'scripts').glob('*.py')}:raise RuntimeError('Source changed during author test; do not use mixed revision results')
 report={'version':'2.6.1-R06','author_selftest_only':True,'independent_agent_acceptance':'pending','cases':cases,'negative_tests':negative,'source_unchanged_during_run':True,'production_release':False};(out/'AUTHOR_SITE_FIT_AND_ISOMETRIC.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if __name__=='__main__':main()
