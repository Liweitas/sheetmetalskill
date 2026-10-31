#!/usr/bin/env python3
"""Existing STEP audit artifact completeness. A passing audit gate does not release manufacture."""
import hashlib,json,subprocess,tempfile,os
from pathlib import Path
from cut_dxf import parse_dxf
from dxf_topology import validate_planar
from source_contract import delivery_state,config_for

def exact(a,b):return json.dumps(a,sort_keys=True,allow_nan=False)==json.dumps(b,sort_keys=True,allow_nan=False)

def state_errors(actual,expected,label):
 return [label+' state mismatch: '+key for key,value in expected.items() if key not in actual or not exact(actual[key],value)]

def actual_readback(root,manifest,runtime=None):
 from runtime_paths import locate
 runtime=runtime or locate();script=Path(__file__).with_name("source_geometry_readback.py")
 with tempfile.TemporaryDirectory(prefix="sheetmetal-readback-") as td:
  td=Path(td);m=td/"manifest.json";output=td/"readback.json";m.write_text(json.dumps(manifest,allow_nan=False));cmd=[runtime["cad_python"],"-B",str(script),"--root",str(root),"--manifest",str(m),"--output",str(output),"--module-path",runtime["sheetmetal_path"]]
  if runtime["freecad_lib"]:cmd += ["--module-path",runtime["freecad_lib"]]
  r=subprocess.run(cmd,capture_output=True,text=True,timeout=900,env={**os.environ,"PYTHONDONTWRITEBYTECODE":"1"})
  if not output.exists():return {"ok":False,"errors":["Actual CAD readback unavailable: "+(r.stdout+r.stderr)[-1200:]],"CAD_executed":False}
  return json.loads(output.read_text())

sha=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()
def check_source(root,manifest,runtime=None,expected_source_sha256=None):
 root=Path(root).resolve();errors=[];geometry=None
 def path(name):
  p=(root/name).resolve()
  if not p.is_relative_to(root):raise ValueError('Path outside source run')
  return p
 try:
  listed={item['path']:item for item in manifest['artifacts']}
  if len(listed)!=len(manifest['artifacts']):errors.append('Duplicate artifact path')
  for name,item in listed.items():
   p=path(name)
   if not p.is_file() or sha(p)!=item['sha256']:errors.append('Missing/stale artifact '+name)
  report=json.loads(path(manifest['source_report']).read_text());state=delivery_state(report)
  # All derived fields must agree, including partial lists and holds, not just the headline.
  errors.extend(state_errors(manifest,state,'Manifest'))
  result_path=manifest.get('audit_result','AUDIT_RESULT.json');result=json.loads(path(result_path).read_text())
  errors.extend(state_errors(result,state,'AUDIT_RESULT'))
  for key,expected in {'source_sha256':report['source_sha256'],'source_unchanged':True,'CAD_executed':True,'CAD_audit_complete':True,'all_source_parts_in_PDF':True,'manifest':'source_manifest.json','pdf':manifest['pdf'],'pdf_pages':manifest['pdf_pages'],'manufacturing_K':report['config'].get('K_ANSI'),'diagnostic_K':report['config'].get('diagnostic_K_ANSI'),'native03_executed':False,'structure_changed':False,'model_healing_selected':False}.items():
   if key not in result or not exact(result[key],expected):errors.append('AUDIT_RESULT evidence mismatch: '+key)
  if manifest.get('contract_version') in ['2.5.1-R04','2.6.0-R05','2.6.1-R06'] and result_path not in listed:errors.append('Final AUDIT_RESULT missing artifact binding')
  blocked=path('BLOCKED_RESULT.json')
  if state['status']=='PARTIAL_HOLD':
   blocked_result=json.loads(blocked.read_text())
   for key,expected in state.items():
    if key not in blocked_result or not exact(blocked_result[key],expected):errors.append('BLOCKED_RESULT state mismatch: '+key)
  elif blocked.exists():errors.append('Unexpected BLOCKED_RESULT in complete geometry run')
  input_config=config_for(json.loads(path('source_config.json').read_text()))
  if not exact(input_config,report['config']):errors.append('Source report config differs from actual input configuration')
  for required in [manifest['source_report'],manifest['source_copy'],manifest['pdf'],*manifest['confirmation_images']]:
   if required not in listed:errors.append('Required artifact unlisted '+required)
  if expected_source_sha256 is not None and sha(path(manifest['source_copy']))!=expected_source_sha256:errors.append('Trusted source SHA256 mismatch')
  if sha(path(manifest['source_copy']))!=report['source_sha256'] or not report['source_unchanged']:errors.append('Source identity mismatch')
  if not report.get('CAD_executed') or not report.get('CAD_audit_complete'):errors.append('CAD audit incomplete')
  if report['solid_count']!=len(report['parts']):errors.append('Missing source part record')
  config=report['config'];valid_ids={p['id'] for p in report['parts']}
  if set(config.get('part_roles',{}))-valid_ids:errors.append('Configured source roles reference absent solids')
  interface=config.get('interface',{})
  if interface and (set(interface['body_ids'])|{interface['lid_id']})-valid_ids:errors.append('Configured interface references absent solids')
  for part in report['parts']:
   name='cad/'+part['formed_step']
   if name not in listed or sha(path(name))!=part['STEP_readback']['sha256']:errors.append('Missing/stale formed STEP '+part['id'])
   u=part['unfold'];idx=u.get('selected_attempt')
   if idx is None:
    if u['status']!='BLOCKED':errors.append('Absent flat not BLOCKED '+part['id'])
    continue
   attempt=u['attempts'][idx]
   for field,digest in [('flat_step','flat_step_sha256'),('dxf','dxf_sha256'),('native_raw_dxf','native_raw_dxf_sha256')]:
    name='cad/'+attempt[field]
    if name not in listed or sha(path(name))!=attempt[digest]:errors.append('Missing/stale '+part['id']+' '+field)
   entities=parse_dxf(path('cad/'+attempt['dxf']));validate_planar(entities,attempt['outer_boundary_entity_indices'])
   if not attempt['flat_BOP']['ok'] or attempt['native_vs_DXF_area_mm2']>1e-5 or attempt['native_vs_exported_STEP_area_mm2']>1e-5:errors.append('Actual flat checks failed '+part['id'])
   if not part['BOP']['ok'] and (u['status']!='DIAGNOSTIC_ONLY' or not u['diagnostic_only']):errors.append('Invalid source promoted '+part['id'])
   if part['bends'] and config.get('K_ANSI') is None and (u['status']!='DIAGNOSTIC_ONLY' or not u['diagnostic_only']):errors.append('Diagnostic K promoted '+part['id'])
   if u.get('manufacturing_accepted') is not False:errors.append('Source run cannot certify manufacture '+part['id'])
  if manifest['all_source_part_ids']!=[p['id'] for p in report['parts']]:errors.append('PDF scope omits source parts')
  from pypdf import PdfReader
  if len(PdfReader(path(manifest['pdf'])).pages)!=manifest['pdf_pages'] or manifest['rendered_pages']!=manifest['pdf_pages']:errors.append('PDF/render count mismatch')
  if manifest.get('contract_version') in ['2.6.0-R05','2.6.1-R06']:
   from corner03 import check_pdf_geometry
   if 'SOURCE_DRAWING_GEOMETRY.json' not in listed or 'cad/source_projections.json' not in listed:raise ValueError('ISOMETRIC: source drawing evidence missing artifact binding')
   drawings=json.loads(path('SOURCE_DRAWING_GEOMETRY.json').read_text());views=drawings.get('formed_isometric_views',{});projected=json.loads(path('cad/source_projections.json').read_text());expected={p['id'] for p in report['parts'] if p['bends']}
   if set(views)!=expected:raise ValueError('ISOMETRIC: source bent-part view coverage incomplete')
   pdfreader=PdfReader(path(manifest['pdf']))
   for owner,v in views.items():
    segments=[(a,b) for poly in projected[owner]['isometric'] for a,b in zip(poly,poly[1:])];check_pdf_geometry(path(manifest['pdf']),v['page_index'],segments,v['pdf_map']);p=next(p for p in report['parts'] if p['id']==owner);u=p['unfold'];labels=u.get('attempts',[])[u['selected_attempt']].get('bend_records',[]) if u.get('selected_attempt') is not None else []
    if v['bend_labels']!=labels:raise ValueError('ISOMETRIC: source bend direction evidence differs from native unfold')
    if labels:
     from formed_isometric import validate_flat_link
     validate_flat_link(u['attempts'][u['selected_attempt']]['bend_lines'],labels)
    page=pdfreader.pages[v['page_index']].extract_text()
    if owner not in page or 'ISOMETRIC' not in page:raise ValueError('ISOMETRIC: source page mislabeled')
    for b in labels:
     if b['id']+' '+b['direction'] not in page:raise ValueError('ISOMETRIC: source native direction missing from PDF')
  if manifest['manufacturing_delivery_complete'] or manifest['production_release']:errors.append('Manufacturing release forbidden')
  if manifest['status']!=state['status']:errors.append('Partial status changed')
  rendered=sorted((root/'preview').glob('page-*.png'))
  if len(rendered)!=manifest['rendered_pages']:errors.append('Actual rendered page coverage mismatch')
  if not errors:
   geometry=actual_readback(root,manifest,runtime)
   if not geometry.get('ok'):errors.extend('Actual geometry readback: '+str(e) for e in geometry.get('errors',[]))
 except Exception as ex:errors.append(str(ex))
 return {'ok':not errors,'errors':errors,'actual_geometry_readback':geometry,'gate_scope':'complete audit evidence only; source manufacture may be BLOCKED','production_release':False}
if __name__=='__main__':
 import argparse
 ap=argparse.ArgumentParser();ap.add_argument('root');ap.add_argument('manifest');ap.add_argument('--expect-source-sha256')
 for name in ['cad-python','freecad-lib','sheetmetal-path','pdf-renderer']:ap.add_argument('--'+name)
 a=ap.parse_args()
 try:
  from runtime_paths import locate
  runtime=locate(a.cad_python,a.freecad_lib,a.sheetmetal_path,a.pdf_renderer);r=check_source(a.root,json.loads(Path(a.manifest).read_text()),runtime,a.expect_source_sha256)
 except Exception as ex:r={'ok':False,'errors':[str(ex)],'production_release':False}
 print(json.dumps(r,indent=2));raise SystemExit(0 if r['ok'] else 2)
