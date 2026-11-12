#!/usr/bin/env python3
"""General brief -> explicit sourced job -> real supported geometry or honest confirmation-only dossier."""
import argparse,contextlib,io,json,sys,tempfile
from pathlib import Path
from general_process import compile_brief

def execute(a):
 raise SystemExit('sm general is closed; the only drawing entry is sm golden (bend-pdf-golden-001-visual)')
 source=Path(a.brief).resolve();brief=json.loads(source.read_text());compiled=compile_brief(brief)
 if a.resolve_only:
  print(json.dumps(compiled,ensure_ascii=False,indent=2));return compiled
 base=Path(a.output).resolve();inputs=base/'.general-process-inputs';inputs.mkdir(parents=True,exist_ok=True);run=Path(tempfile.mkdtemp(prefix='brief-',dir=inputs));(run/'original_brief.json').write_bytes(source.read_bytes());(run/'compilation.json').write_text(json.dumps(compiled,ensure_ascii=False,indent=2))
 if compiled['job'] is None or compiled['route']=='formed_confirmation':
  from general_review import build_review
  result=build_review(source,compiled,base,run,a)
  print(json.dumps(result,ensure_ascii=False,indent=2));return result
 job=run/'compiled_general.job.json';job.write_text(json.dumps(compiled['job'],ensure_ascii=False,indent=2))
 from build_package import execute as build_explicit
 args=argparse.Namespace(job=str(job),output=str(base),naming=a.naming,cad_python=a.cad_python,freecad_lib=a.freecad_lib,sheetmetal_path=a.sheetmetal_path,pdf_renderer=a.pdf_renderer,_general_brief_path=str(source))
 with contextlib.redirect_stdout(io.StringIO()) as captured:build_explicit(args)
 result=json.loads(captured.getvalue());result['general_input_report']=str(run/'compilation.json');print(json.dumps(result,ensure_ascii=False,indent=2));return result
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('brief');p.add_argument('--output',required=True);p.add_argument('--naming');p.add_argument('--resolve-only',action='store_true')
 for n in ['cad-python','freecad-lib','sheetmetal-path','pdf-renderer']:p.add_argument('--'+n)
 a=p.parse_args()
 try:execute(a)
 except Exception as e:print(json.dumps({'ok':False,'status':'GENERAL_PROCESS_BLOCKED','error':str(e),'production_release':False},ensure_ascii=False),file=sys.stderr);raise SystemExit(2)
if __name__=='__main__':main()
