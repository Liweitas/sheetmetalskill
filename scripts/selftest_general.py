#!/usr/bin/env python3
"""Seven synthetic general-entry runs; explicit author test, never factory/independent qualification."""
import argparse,json,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',required=True)
 for n in ['cad-python','freecad-lib','sheetmetal-path','pdf-renderer']:p.add_argument('--'+n)
 a=p.parse_args();out=Path(a.output).resolve()
 if out.exists():raise ValueError('SELFTEST_OUTPUT_MUST_NOT_EXIST')
 out.mkdir(parents=True);rows=[]
 for key in ['A','B','C','D','Q0','MISSING','IRREGULAR']:
  cmd=[sys.executable,'-B',str(ROOT/'scripts/build_general_package.py'),str(ROOT/'assets/examples/general'/(key+'.json')),'--output',str(out/key)]
  for n in ['cad_python','freecad_lib','sheetmetal_path','pdf_renderer']:
   if getattr(a,n):cmd+=['--'+n.replace('_','-'),getattr(a,n)]
  start=time.monotonic()
  with (out/(key+'.stdout.json')).open('w') as so,(out/(key+'.stderr.log')).open('w') as se:r=subprocess.run(cmd,stdout=so,stderr=se,timeout=1800)
  row={'case':key,'returncode':r.returncode,'elapsed_s':round(time.monotonic()-start,1)};rows.append(row);(out/'results.json').write_text(json.dumps(rows,indent=2));print(json.dumps(row),flush=True)
  if r.returncode:raise RuntimeError('ACTUAL_GENERAL_CASE_FAILED: '+key)
  result=json.loads((out/(key+'.stdout.json')).read_text())
  if key in ['Q0','MISSING','IRREGULAR']:
   from validate_general_review import check
   check(result['revision_root'])
   from delivery_contract import check_envelope
   try:check_envelope(result['revision_root'])
   except ValueError as e:
    if 'GENERAL_CONFIRMATION_ONLY' not in str(e):raise
   else:raise ValueError('REVIEW_FALSE_MANUFACTURING_ACCEPTANCE')
 summary={'author_selftest_only':True,'synthetic_K_and_factory_records_are_test_fixtures_not_real_qualification':True,'production_release':False,'cases':rows};(out/'AUTHOR_GENERAL_RESULTS.json').write_text(json.dumps(summary,indent=2))
if __name__=='__main__':main()
