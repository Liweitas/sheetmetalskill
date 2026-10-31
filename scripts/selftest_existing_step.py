#!/usr/bin/env python3
"""Synthetic supported-import author regression; never replaces testing the user's real STEP."""
import argparse,json,subprocess,sys,copy
from pathlib import Path
from validate_source_manifest import check_source
from runtime_paths import locate
ROOT=Path(__file__).resolve().parents[1]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',required=True)
 for name in ['cad-python','freecad-lib','sheetmetal-path','pdf-renderer']:ap.add_argument('--'+name)
 a=ap.parse_args();out=Path(a.output).resolve()
 if out.exists():ap.error('Output must not exist')
 out.mkdir(parents=True);extra=[]
 for name in ['cad_python','freecad_lib','sheetmetal_path','pdf_renderer']:
  if getattr(a,name):extra+=['--'+name.replace('_','-'),getattr(a,name)]
 def run(name,args,want):
  with (out/(name+'.log')).open('wb') as log:r=subprocess.run([sys.executable,'-B',*args,*extra],stdout=log,stderr=subprocess.STDOUT,timeout=1500)
  if r.returncode!=want:raise RuntimeError(name+' exit '+str(r.returncode)+'; inspect log')
 from record_site_fit import record
 job=json.loads((ROOT/'assets/examples/box-wrap-l.job.json').read_text());job,_=record(job,'SYNTHETIC SELFTEST authorization for this fixture only','For this synthetic fixture retain lid-root interference for site fitting and trial assembly; not real customer consent.');fixture_job=out/'fixture.job.json';fixture_job.write_text(json.dumps(job,indent=2))
 run('fixture',[str(ROOT/'scripts/build_package.py'),str(fixture_job),'--output',str(out/'fixture')],0)
 from factory_naming import published_root
 source=next((published_root(out/'fixture')/'STEP').glob('*ASSEMBLY_*.step'));config=out/'explicit-trial.json';config.write_text(json.dumps({'K_ANSI':.4,'K_status':'assumed','K_source':'Synthetic algorithm regression candidate; not calibrated','material':None}))
 run('supported',[str(ROOT/'scripts/audit_step.py'),str(source),'--config',str(config),'--output',str(out/'supported')],2)
 run('unknown',[str(ROOT/'scripts/audit_step.py'),str(source),'--output',str(out/'unknown')],2)
 results={};negative=[]
 for name in ['supported','unknown']:
  dest=next((out/name).rglob('AUDIT_RESULT.json')).parent;r=json.loads((dest/'AUDIT_RESULT.json').read_text());m=json.loads((dest/'source_manifest.json').read_text());gate=check_source(dest,m,runtime=locate(a.cad_python,a.freecad_lib,a.sheetmetal_path,a.pdf_renderer))
  if not gate['ok'] or r['manufacturing_delivery_complete'] or r['production_release']:raise RuntimeError('Bad source audit scope/status')
  if name=='supported' and (not r['geometry_delivery_complete'] or len(r['checked_parts'])!=3):raise RuntimeError('Supported imported bent sheets not completed')
  if name=='unknown' and (r['geometry_delivery_complete'] or r['manufacturing_K'] is not None):raise RuntimeError('Unknown source compensation promoted')
  for key in ['source_report','source_copy','pdf']:
   bad=copy.deepcopy(m);bad[key]='MISSING_FILE'
   if check_source(dest,bad,runtime=locate(a.cad_python,a.freecad_lib,a.sheetmetal_path,a.pdf_renderer))['ok']:raise RuntimeError('Missing source artifact passed '+key)
   negative.append({'case':name,'missing':key,'rejected':True})
  bad=copy.deepcopy(m);bad['all_source_part_ids']=bad['all_source_part_ids'][:-1]
  if check_source(dest,bad,runtime=locate(a.cad_python,a.freecad_lib,a.sheetmetal_path,a.pdf_renderer))['ok']:raise RuntimeError('Omitted source part passed')
  negative.append({'case':name,'missing':'source part in PDF scope','rejected':True})
  results[name]=r
 summary={'author_selftest_only':True,'synthetic_fixture_only':True,'real_source_test_required_separately':True,'cases':results,'negative_tests':negative,'production_release':False};(out/'AUTHOR_EXISTING_STEP_SELFTEST.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
