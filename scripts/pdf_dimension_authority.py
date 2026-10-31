"""Compare source/canonical design and printed dimensions to freshly read actual STEP extents."""
import json,math,re,subprocess,tempfile,os
from pathlib import Path
def check_printed_three_views(pdf,shapes,tolerance_mm=1e-5):
 from pypdf import PdfReader
 reader=PdfReader(pdf);pages=[p.extract_text() for p in reader.pages];norm=lambda s:re.sub(r'\s+','',s);results={}
 for name,record in shapes.items():
  title=norm(name+' - ACTUAL EXPORTED STEP THREE VIEWS');selected=[(i,t) for i,t in enumerate(pages) if title in norm(t)]
  if len(selected)!=1:raise ValueError('PDF_ACTUAL_STEP_DIMENSION_PAGE_COVERAGE: '+name)
  page,text=selected[0];numbers=[float(m.group(1)) for line in text.splitlines() if (m:=re.fullmatch(r'\s*([-+]?\d+\.\d{6})\s+mm\s*',line))]
  b=record['bbox_mm'];x,y,z=[b[i+3]-b[i] for i in range(3)];expected=[x,z,y,z,x,y]
  if len(numbers)!=6 or any(abs(a-b)>tolerance_mm for a,b in zip(numbers,expected)):raise ValueError('PDF_ACTUAL_STEP_DIMENSION_LABEL_MISMATCH: '+name)
  results[name]={'page_index':page,'printed_mm':numbers,'actual_STEP_extents_mm':[x,y,z],'label_order':'front X/Z, right Y/Z, top X/Y','numeric_readback_tolerance_mm':tolerance_mm}
 return results
def actual_dimensions(project,manifest,root,runtime=None):
 from validate_project import value
 from runtime_paths import locate
 runtime=runtime or locate();root=Path(root).resolve();shapes=[];owners={p['id']:value(p['role']) for p in project['fabrication']['parts']}
 for item in manifest['artifacts']:
  if item['kind']=='step_part':
   owner=item['part_ids'][0];shapes.append({'id':owner,'path':item['path'],'body_part':owners[owner]!='lid'})
  if item['kind'] in ['step_assembly','step_exploded']:shapes.append({'id':'ASSEMBLY' if item['kind']=='step_assembly' else 'EXPLODED','path':item['path'],'body_part':False})
 cn=manifest.get('workshop_pdf_contract')=='cn-workshop-dimensioned-v1'
 if cn:
  for item in manifest['artifacts']:
   if item['kind']=='unfold_step':shapes.append({'id':'FLAT:'+item['part_ids'][0],'path':item['path'],'body_part':False})
 data={'shapes':shapes,'dimensioned_CN_views':cn}
 if manifest.get('general_process_contract'):
  cad=json.loads((root/next(a['path'] for a in manifest['artifacts'] if a['kind']=='cad_report')).read_text());data['translation_only_parts']=cad['exploded_translations_mm']
 with tempfile.TemporaryDirectory(prefix='sheetmetal-actual-dimensions-') as td:
  td=Path(td);request=td/'request.json';target=td/'result.json';request.write_text(json.dumps(data));cmd=[runtime['cad_python'],'-B',str(Path(__file__).with_name('step_dimensions_readback.py')),'--root',str(root),'--request',str(request),'--output',str(target)]
  if runtime.get('freecad_lib'):cmd+=['--module-path',runtime['freecad_lib']]
  run=subprocess.run(cmd,capture_output=True,text=True,timeout=300,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
  if not target.exists():raise ValueError('ACTUAL_STEP_DIMENSIONS_UNAVAILABLE: '+(run.stdout+run.stderr)[-500:])
  actual=json.loads(target.read_text())
 if actual.get('ok') is not True or actual.get('CAD_executed') is not True:raise ValueError('ACTUAL_STEP_DIMENSIONS_FAILED: '+str(actual.get('errors')))
 L,W,H=[value(project['requirements']['dimensions'][a]) for a in 'XYZ'];t=value(project['requirements']['nominal_t']);has=value(project['requirements']['lid_required']);hb=H-t-value(project['lid']['roof_gap']) if has else H
 expected=[0.,0.,0.,L,W,hb]
 if any(abs(x-y)>1e-5 for x,y in zip(actual['body_bbox_mm'],expected)):raise ValueError('ACTUAL_STEP_BODY_DIMENSIONS_DIFFER_SOURCE: '+str(actual['body_bbox_mm'])+' vs '+str(expected))
 pdf=root/next(a['path'] for a in manifest['artifacts'] if a['kind']=='pdf')
 if cn:
  from cn_workshop import check_dimensions
  actual['printed_three_views']=check_dimensions(pdf,project,manifest,root,actual)
 else:actual['printed_three_views']=check_printed_three_views(pdf,actual['shapes'])
 return actual
