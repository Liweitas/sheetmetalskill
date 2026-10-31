#!/usr/bin/env python3
"""Read-only discovery of public FreeCAD/SheetMetal/Poppler installations."""
import argparse,json
from pathlib import Path
from runtime_paths import locate,probe
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--cad-python');p.add_argument('--freecad-lib');p.add_argument('--sheetmetal-path');p.add_argument('--pdf-renderer');p.add_argument('--probe',action='store_true');a=p.parse_args()
 try:
  runtime=locate(a.cad_python,a.freecad_lib,a.sheetmetal_path,a.pdf_renderer);result={'ok':True,'runtime':runtime,'CAD_executed':False}
  if a.probe:result['API_probe']=probe(runtime,Path(__file__).resolve().parents[1])
  print(json.dumps(result,indent=2))
 except Exception as ex:print(json.dumps({'ok':False,'status':'DEPENDENCY_BLOCKED','error':str(ex)}));raise SystemExit(2)
