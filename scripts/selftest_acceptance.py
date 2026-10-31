#!/usr/bin/env python3
"""Reproducible author regression of R01 failures; not independent agent acceptance."""
import argparse,copy,json,subprocess,sys
from pathlib import Path
from validate_manifest import check
ROOT=Path(__file__).resolve().parents[1]
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',required=True)
 for flag in ['cad-python','freecad-lib','sheetmetal-path','pdf-renderer']:ap.add_argument('--'+flag)
 a=ap.parse_args();out=Path(a.output).resolve()
 if out.exists():ap.error('Output must not exist')
 out.mkdir(parents=True);cases=[];negative=[]
 extra=[]
 for key in ['cad_python','freecad_lib','sheetmetal_path','pdf_renderer']:
  if getattr(a,key):extra+=['--'+key.replace('_','-'),getattr(a,key)]
 for name,example,count in [('N02','common-460-review.job.json',4),('A_center18','regression-A-center18.job.json',4),('B_center18','regression-B-center18.job.json',3)]:
  from record_site_fit import record
  job=json.loads((ROOT/'assets/examples'/example).read_text());job,_=record(job,'SYNTHETIC SELFTEST authorization for '+job['id']+' only; not real customer consent','For this synthetic test retain lid-root interference for site fitting and trial assembly; no geometry change or completed trial is claimed.');source=out/(name+'.job.json');source.write_text(json.dumps(job,indent=2))
  dest=out/name;cmd=[sys.executable,'-B',str(ROOT/'scripts/build_package.py'),str(source),'--output',str(dest),*extra]
  with (out/(name+'.log')).open('wb') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=1200)
  if r.returncode:raise RuntimeError(name+' failed; inspect '+str(out/(name+'.log')))
  from factory_naming import published_root
  dest=published_root(dest)
  result=json.loads(next(dest.glob('*RUN_RESULT_*.json')).read_text());p=json.loads((dest/result['project']).read_text());m=json.loads((dest/result['manifest']).read_text());cad=json.loads(next((dest/'evidence').glob('*cad_report_*.json')).read_text())
  if not check(p,m,dest)['ok'] or len(result['sheet_parts'])!=count or result['production_release']:raise RuntimeError('Final gate or structure failed '+name)
  if result['pdf_pages']!=result['pdf_rendered_pages'] or len(result['confirmation_images'])!=2:raise RuntimeError('Incomplete drawings '+name)
  if result['native03']['native_sloped_edges']!=8 or result['native03']['actual_roof_q_mm']!=0:raise RuntimeError('03/q check failed '+name)
  if p['bending']['K_value']['status']!='assumed' or p['lid']['corner_gap']['status']!='assumed':raise RuntimeError('Engineering candidates promoted '+name)
  lid=cad['parts']['LID'];measurement=lid['thickness_measurement']
  if abs(measurement['measured_t_mm']-p['requirements']['nominal_t']['value'])>1e-5:raise RuntimeError('Physical thickness mismatch '+name)
  if name=='N02':
   if len(result['fixing_pairs'])!=10 or sum(x['actual_holes'] for x in cad['parts'].values())!=28:raise RuntimeError('N02 incomplete holes')
   if abs(result['end_profile']['inset_yz_mm']-.2)>1e-5 or not result['end_profile']['concentric_with_U']:raise RuntimeError('N02 end profile')
   for q in cad['mounting_pattern_geometry']:
    if max(abs(q[k]-v) for k,v in [('actual_wide_pitch_mm',85),('actual_narrow_pitch_mm',62),('actual_spacing_mm',30)])>1e-5:raise RuntimeError('N02 handle pitch')
  for kind in ['dxf','step_part','step_assembly','step_exploded','unfold_step','pdf','confirmation_png']:
   bad=copy.deepcopy(m);bad['artifacts']=[x for x in bad['artifacts'] if x['kind']!=kind];errors=check(p,bad,dest)
   if errors['ok']:raise RuntimeError('Missing '+kind+' unexpectedly passed '+name)
   negative.append({'case':name,'test':'missing '+kind,'rejected':True})
  for field in ['native_geometry_report','body_step','part_geometry_report']:
   bad=copy.deepcopy(m);item=next(x for x in bad['artifacts'] if x.get('kind')=='dxf' and x.get('part_ids')==['LID']);item.pop(field)
   if check(p,bad,dest)['ok']:raise RuntimeError('Missing '+field+' passed')
   negative.append({'case':name,'test':'missing '+field,'rejected':True})
  if name=='N02':
   bad=copy.deepcopy(m);bad.pop('fixing_geometry_report')
   if check(p,bad,dest)['ok']:raise RuntimeError('Missing fixing evidence passed')
   negative.append({'case':name,'test':'missing fixing evidence','rejected':True})
   bad=copy.deepcopy(m);next(x for x in bad['artifacts'] if x.get('kind')=='dxf' and x.get('part_ids')==['LID']).pop('handle_geometry_report')
   if check(p,bad,dest)['ok']:raise RuntimeError('Missing handle evidence passed')
   negative.append({'case':name,'test':'missing handle evidence','rejected':True})
  cases.append({'name':name,'sheets':result['sheet_parts'],'actual_holes':{k:v['actual_holes'] for k,v in cad['parts'].items()},'pdf_pages':result['pdf_pages'],'pdf_rendered_pages':result['pdf_rendered_pages'],'actual_t':measurement,'native03':result['native03'],'source_status':{'K':p['bending']['K_value']['status'],'corner_gap':p['lid']['corner_gap']['status']},'production_release':False})
 report={'version':'2.5.0-R03','author_selftest_only':True,'independent_agent_acceptance':'pending','cases':cases,'negative_tests':negative,'production_release':False}
 (out/'AUTHOR_ACCEPTANCE_REGRESSION.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if __name__=='__main__':main()
