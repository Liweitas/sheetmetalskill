"""Locate public CAD/PDF dependencies; never installs or edits environment configuration."""
import os,sys,shutil,subprocess,json
from pathlib import Path
def locate(cad_python=None,freecad_lib=None,sheetmetal_path=None,pdf_renderer=None):
 home=Path.home()
 cad_candidates=[cad_python,os.environ.get('FREECAD_PYTHON'),'/Applications/FreeCAD.app/Contents/Resources/bin/python']
 cad=next((Path(x).expanduser().resolve() for x in cad_candidates if x and Path(x).expanduser().is_file()),None)
 if cad_python and not Path(cad_python).expanduser().is_file():raise ValueError('DEPENDENCY_BLOCKED: explicit CAD Python does not exist')
 lib=Path(freecad_lib).expanduser().resolve() if freecad_lib else cad.parent.parent/'lib' if cad and (cad.parent.parent/'lib').is_dir() else None
 roots=[home/'Library/Application Support/FreeCAD',home/'.local/share/FreeCAD',home/'.FreeCAD']
 if os.environ.get('APPDATA'):roots.insert(0,Path(os.environ['APPDATA'])/'FreeCAD')
 candidates=[]
 for root in roots:
  candidates.extend(sorted(root.glob('v*/Mod/SheetMetal'),reverse=True));candidates.append(root/'Mod/SheetMetal')
 if lib:candidates.append(lib.parent/'Mod/SheetMetal')
 if os.environ.get('SHEETMETAL_PATH'):candidates.insert(0,Path(os.environ['SHEETMETAL_PATH']))
 if sheetmetal_path:
  specified=Path(sheetmetal_path).expanduser().resolve()
  options=[specified,specified/'SheetMetal']
  sm=next((p for p in options if (p/'SheetMetalNewUnfolder.py').is_file()),None)
  if sm is None:raise ValueError('DEPENDENCY_BLOCKED: explicit SheetMetal path lacks SheetMetalNewUnfolder.py; omit --sheetmetal-path to search versioned user addon directories')
 else:sm=next((p.resolve() for p in candidates if (p/'SheetMetalNewUnfolder.py').is_file()),None)
 renderer=pdf_renderer or shutil.which('pdftoppm')
 if not cad or not sm or not renderer or not Path(renderer).is_file():raise ValueError('DEPENDENCY_BLOCKED: FreeCAD Python, SheetMetalNewUnfolder or pdftoppm not found; run scripts/discover_runtime.py and configure public dependencies')
 return {'cad_python':str(cad),'freecad_lib':str(lib) if lib else None,'sheetmetal_path':str(sm),'pdf_renderer':str(Path(renderer).resolve())}
def probe(runtime,root):
 cmd=[runtime['cad_python'],str(Path(root)/'scripts/probe_cad.py'),'--sheetmetal-path',runtime['sheetmetal_path']]
 if runtime['freecad_lib']:cmd+=['--freecad-lib',runtime['freecad_lib']]
 result=subprocess.run(cmd,capture_output=True,text=True,timeout=90,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
 if result.returncode:raise ValueError('DEPENDENCY_PROBE_BLOCKED: '+(result.stdout+result.stderr)[-1800:]+' If Qt reports NEON in a restricted sandbox, use the authorized isolated CAD execution environment; do not control another GUI process.')
 data=json.loads(result.stdout)
 if data.get('ok') is not True:raise ValueError('CAD dependency API probe failed')
 return data
