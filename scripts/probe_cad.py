#!/usr/bin/env python3
"""Run with FreeCAD's Python to inspect required API dependencies without opening a document."""
import argparse,sys,json,hashlib
from pathlib import Path
def main():
 p=argparse.ArgumentParser();p.add_argument("--freecad-lib");p.add_argument("--sheetmetal-path",required=True);a=p.parse_args()
 if a.freecad_lib:sys.path.insert(0,a.freecad_lib)
 sys.path.insert(0,a.sheetmetal_path)
 try:
  import FreeCAD,Part,TechDraw,networkx,SheetMetalNewUnfolder as NU
  from xml.etree import ElementTree as ET
  root=ET.parse(Path(a.sheetmetal_path)/"package.xml").getroot()
  version=next((x.text for x in root if x.tag.split("}")[-1]=="version"),None)
  if not callable(NU.getUnfold) or not callable(NU.BendAllowanceCalculator.from_single_value):raise ValueError("SheetMetal API contract absent")
  print(json.dumps({"ok":True,"CAD_executed":False,"python":sys.version,"FreeCAD":FreeCAD.Version(),"OCCT":Part.OCC_VERSION,"networkx":networkx.__version__,"SheetMetal":version,"SheetMetalNewUnfolder_sha256":hashlib.sha256(Path(NU.__file__).read_bytes()).hexdigest()},indent=2))
 except Exception as ex:
  print(json.dumps({"ok":False,"status":"DEPENDENCY_BLOCKED","error":str(ex)}));raise SystemExit(2)
if __name__=="__main__":main()
