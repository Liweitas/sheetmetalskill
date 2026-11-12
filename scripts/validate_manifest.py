#!/usr/bin/env python3
"""Artifact/PDF/DXF checks plus actual STEP native direction readback; no CAM/release proof."""
import argparse,json,math,hashlib,collections,subprocess,tempfile,os
from pathlib import Path
from validate_project import validate,parameter_hash,diameter,value
from dxf_topology import validate_planar
from cut_dxf import parse_dxf
def closed_component_count(ents,indices):
 if not indices:raise ValueError('missing outer boundary')
 degree=collections.Counter();adj={};circles=0
 for i in indices:
  if not isinstance(i,int) or isinstance(i,bool) or not 0<=i<len(ents):raise ValueError('bad boundary index')
  e=ents[i];t=e['type']
  if t=='CIRCLE':circles+=1;continue
  if t=='LINE':a=(float(e[10]),float(e[20]));b=(float(e[11]),float(e[21]))
  else:
   x=float(e[10]);y=float(e[20]);r=float(e[40]);a0=math.radians(float(e[50]));a1=math.radians(float(e[51]));a=(x+r*math.cos(a0),y+r*math.sin(a0));b=(x+r*math.cos(a1),y+r*math.sin(a1))
  a=tuple(round(v,7) for v in a);b=tuple(round(v,7) for v in b);degree[a]+=1;degree[b]+=1;adj.setdefault(a,set()).add(b);adj.setdefault(b,set()).add(a)
 if any(d!=2 for d in degree.values()):raise ValueError('open/branched outer CUT boundary')
 seen=set();components=circles
 for seed in degree:
  if seed in seen:continue
  components+=1;pending=[seed]
  while pending:
   q=pending.pop()
   if q in seen:continue
   seen.add(q);pending.extend(adj[q]-seen)
 return components
def actual_native_directions(project,manifest,root,iso,runtime=None):
 from runtime_paths import locate
 runtime=runtime or locate();parts=[]
 for part in project['fabrication']['parts']:
  owner=part['id']
  if value(part['bends'])==0:continue
  step=next(i for i in manifest['artifacts'] if i.get('kind')=='step_part' and i.get('part_ids')==[owner])
  parts.append({'id':owner,'role':value(part['role']),'formed_step':step['path'],'t':value(project['requirements']['nominal_t']),'K_ANSI':value(project['bending']['K_value']),'claims':iso['views'][owner]['bend_labels']})
 data={'parts':parts}
 if manifest.get('workflow_contract')=='2.6.1-R06' and value(project['requirements']['lid_required']):
  item=next(i for i in manifest['artifacts'] if i.get('kind')=='dxf' and i.get('part_ids')==['LID']);data['interference']={'body_step':item['body_step'],'lid_step':item['formed_step'],'claimed_authority_mm3':value(project['lid']['root_overlap_volume'])}
 from pdf_dimension_authority import _resident_readback
 resident=_resident_readback('native_direction',root,data)
 if resident is not None:return resident
 with tempfile.TemporaryDirectory(prefix='sheetmetal-native-direction-') as td:
  td=Path(td);request=td/'request.json';result=td/'result.json';request.write_text(json.dumps(data,allow_nan=False))
  cmd=[runtime['cad_python'],'-B',str(Path(__file__).with_name('native_direction_readback.py')),'--root',str(root),'--request',str(request),'--output',str(result),'--module-path',runtime['sheetmetal_path']]
  if runtime.get('freecad_lib'):cmd+=['--module-path',runtime['freecad_lib']]
  run=subprocess.run(cmd,capture_output=True,text=True,timeout=900,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
  if not result.exists():return {'ok':False,'CAD_executed':False,'errors':['NATIVE_DIRECTION: actual CAD readback unavailable '+(run.stdout+run.stderr)[-1000:]]}
  return json.loads(result.read_text())

def check(project,manifest,root,runtime=None,allow_geometry_only=False):
 root=Path(root).resolve();errors=[];checks=[];p=validate(project,'cut');version=value(project['project']['version']);digest=parameter_hash(project)
 if not p['ok']:errors.append('PROJECT_BLOCKED')
 if manifest.get('version')!=version or manifest.get('timezone')!='Asia/Shanghai':errors.append('MANIFEST_VERSION_TIMEZONE')
 if manifest.get('parameter_hash')!=digest:errors.append('MANIFEST_PARAMETER_HASH')
 arts=manifest.get('artifacts',[])
 if not arts:errors.append('NO_ARTIFACTS')
 planned_sheets={part['id'] for part in project['fabrication']['parts'] if value(part['role']) in ['body','u_body','endplate','bottom_l','lid']}
 coverage=collections.Counter(owner for item in arts if item.get('kind')=='dxf' for owner in item.get('part_ids',[]))
 if set(coverage)!=planned_sheets or any(n!=1 for n in coverage.values()):errors.append('DXF_PART_COVERAGE: every planned sheet must have exactly one manufacturing DXF; missing, extra or duplicated parts forbidden')
 if project.get('input_mode')=='new_design':
  flat_coverage=collections.Counter(owner for item in arts if item.get('kind')=='unfold_step' for owner in item.get('part_ids',[]))
  if flat_coverage!=collections.Counter({owner:1 for owner in planned_sheets}):errors.append('UNFOLD_STEP_PART_COVERAGE')
 formats=value(project['delivery']['formats']) or []
 for fmt in ['pdf','step_parts','step_assembly','step_exploded','confirmation_png']:
  if fmt in formats:
   kind={'step_parts':'step_part','step_assembly':'step_assembly','step_exploded':'step_exploded','pdf':'pdf','confirmation_png':'confirmation_png'}[fmt]
   selected=[item for item in arts if item.get('kind')==kind]
   if not selected:errors.append('MISSING_FORMAT: '+fmt)
   if fmt=='step_parts' and collections.Counter(owner for item in selected for owner in item.get('part_ids',[]))!=collections.Counter({owner:1 for owner in planned_sheets}):errors.append('STEP_PART_COVERAGE')
 if project['fabrication'].get('fixing_pairs'):
  try:
   fp=(root/manifest['fixing_geometry_report']).resolve()
   if not fp.is_relative_to(root):raise ValueError('fixing evidence path escapes root')
   f=json.loads(fp.read_text())
   if f.get('ok') is not True or f.get('CAD_executed') is not True or f.get('parameter_hash')!=digest:raise ValueError('actual fixing axis report absent/failed/stale')
   wanted={x['id']:(x['body_hole_id'],x['lid_hole_id']) for x in project['fabrication']['fixing_pairs']}
   observed={x['id']:(x['body_hole_id'],x['lid_hole_id']) for x in f['pairs']}
   if observed!=wanted or len(f['pairs'])!=len(wanted):raise ValueError('fixing pair evidence coverage mismatch')
   for pair in f['pairs']:
    offset=pair.get('actual_axis_offset_mm')
    if isinstance(offset,bool) or not isinstance(offset,(int,float)) or not math.isfinite(offset) or not 0<=offset<=1e-5:raise ValueError('actual fixing axes not coaxial')
   for kind,key in [('step_part','formed_steps'),('dxf','dxfs')]:
    supplied={owner:item for item in arts if item.get('kind')==kind for owner in item.get('part_ids',[])}
    if set(f['input_sha256'][key])!=planned_sheets:raise ValueError('fixing input SHA ownership mismatch')
    for owner,item in supplied.items():
     path=(root/item['path']).resolve()
     if not path.is_relative_to(root) or hashlib.sha256(path.read_bytes()).hexdigest()!=f['input_sha256'][key][owner]:raise ValueError('fixing actual STEP/DXF SHA mismatch')
  except (KeyError,OSError,ValueError,TypeError) as ex:errors.append('FIXING_GEOMETRY: '+str(ex))
 for a in arts:
  try:
   rel=Path(a['path']);path=(root/rel).resolve()
   if rel.is_absolute() or not path.is_relative_to(root):raise ValueError('artifact path escapes root')
   if a.get('parameter_version')!=version or a.get('parameter_hash')!=digest:raise ValueError('artifact uses different parameter revision')
   if version not in path.name:raise ValueError('generated filename missing current minute version')
   if hashlib.sha256(path.read_bytes()).hexdigest()!=a['sha256']:raise ValueError('artifact SHA mismatch')
   rec={'path':a['path'],'sha_match':True,'version_match':True}
   if a['kind']=='confirmation_png':
    from PIL import Image
    with Image.open(path) as preview:
     if preview.format!='PNG' or min(preview.size)<600:raise ValueError('confirmation image invalid or too small')
     preview.verify()
    rec['confirmation_png_readback']=True
   if a['kind']=='dxf':
    if a.get('stage')!='laser':raise ValueError('CUT must be laser stage')
    owners=a.get('part_ids',[])
    if not owners or len(owners)!=len(set(owners)):raise ValueError('part ownership missing/duplicated')
    planned={p['id'] for p in project['fabrication']['parts']}
    if not set(owners)<=planned:raise ValueError('unknown planned part')
    ents=parse_dxf(path);indices=a.get('outer_boundary_entity_indices',[i for i,e in enumerate(ents) if e['type']!='CIRCLE'])
    if len(indices)!=len(set(indices)):raise ValueError('repeated boundary indices')
    if closed_component_count(ents,indices)!=len(owners):raise ValueError('outer boundary count differs from selected parts')
    remaining=[e for i,e in enumerate(ents) if i not in indices]
    if any(e['type']!='CIRCLE' for e in remaining):raise ValueError('non-circular inner features need CAD-specific validation adapter')
    expected=collections.Counter()
    for group in project['hole_groups']:
     D=diameter(group['laser_size'])
     for pos in group['positions']:
      if pos['part_id'] in owners:expected[round(D,7)]+=1
    actual=collections.Counter(round(2*float(e[40]),7) for e in remaining)
    if actual!=expected:raise ValueError('CUT hole counts/diameters differ from laser pilot contract (counterseat mouth must not enter CUT)')
    if project.get('input_mode')=='new_design':
     if len(owners)!=1:raise ValueError('new-design manufacturing DXFs must be per-part; nests are separate review artifacts')
     for kind,key in [('step_part','formed_step'),('unfold_step','unfold_step')]:
      declared=[item for item in arts if item.get('kind')==kind and item.get('part_ids')==owners]
      if len(declared)!=1 or (root/declared[0]['path']).resolve()!=(root/a[key]).resolve():raise ValueError('Declared STEP artifact differs from actual formed/unfold evidence owner')
     report_path=(root/a['part_geometry_report']).resolve()
     if not report_path.is_relative_to(root):raise ValueError('part geometry evidence escapes root')
     report=json.loads(report_path.read_text())
     if report.get('CAD_executed') is not True or report.get('ok') is not True or report.get('parameter_hash')!=digest or report.get('part_ids')!=owners:raise ValueError('actual per-part CAD/unfold evidence missing or stale')
     for key in ['native_DXF_area_difference_mm2','native_exported_unfold_area_difference_mm2']:
      delta=report.get(key)
      if isinstance(delta,bool) or not isinstance(delta,(int,float)) or not math.isfinite(delta) or not 0<=delta<=1e-5:raise ValueError('actual native STEP/DXF area comparison missing or failed')
     for key in ['formed_step','unfold_step']:
      source_path=(root/a[key]).resolve()
      if not source_path.is_relative_to(root) or hashlib.sha256(source_path.read_bytes()).hexdigest()!=report['input_sha256'][key]:raise ValueError('actual formed/unfold STEP SHA mismatch')
     if hashlib.sha256(path.read_bytes()).hexdigest()!=report['input_sha256']['dxf']:raise ValueError('actual unfolded DXF SHA mismatch')
     part=next(part for part in project['fabrication']['parts'] if part['id']==owners[0])
     if report.get('actual_bends')!=value(part['bends']):raise ValueError('actual bend count differs from structural plan')
    if any(value(part['role'])=='lid' and part['id'] in owners for part in project['fabrication']['parts']):
     from create_intake import apply_lid_defaults
     from corner03 import spec,check_dxf,check_pdf_geometry
     effective=apply_lid_defaults(project);scheme=value(effective['lid']['corner_scheme'])
     if scheme is None:raise ValueError('lid corner scheme unresolved; no silent redesign of existing project')
     if scheme!='03' and project.get('input_mode')=='new_design':raise ValueError('UNSUPPORTED_CORNER_ADAPTER: new-design worker supports03 only; explicit alternatives need a verified adapter')
     if scheme=='03':
      reading=check_dxf(path,spec(effective))
      def bound_file(key):
       p=(root/a[key]).resolve()
       if not p.is_relative_to(root):raise ValueError('03 evidence path escapes root')
       return p
      native=json.loads(bound_file('native_geometry_report').read_text())
      if native.get('ok') is not True or native.get('CAD_executed') is not True or native.get('parameter_hash')!=digest or native.get('actual_bends')!=4 or native.get('native_sloped_edges')!=8:raise ValueError('actual native03 report missing/failed/stale; label-only evidence insufficient')
      if project.get('input_mode')=='new_design':
       from site_fit import acceptance_from_project,VOLUME_TOL_MM3
       accepted=acceptance_from_project(project);volume=native.get('root_overlap_volume_mm3')
       if isinstance(volume,bool) or not isinstance(volume,(int,float)) or not math.isfinite(volume) or volume<0:raise ValueError('SITE_FIT: actual interference measurement absent/invalid')
       if volume>VOLUME_TOL_MM3 and not accepted:raise ValueError('SITE_FIT: positive interference lacks this-job user acceptance')
       if accepted:
        if native.get('site_fit_acceptance')!=accepted:raise ValueError('SITE_FIT: native acceptance differs from canonical scoped authorization')
        if native.get('assembly_interference_free') is not (volume<=VOLUME_TOL_MM3) or native.get('geometry_interference_eliminated') is not False or native.get('trial_assembly_confirmed') is not False:raise ValueError('SITE_FIT: native report falsely claims no interference/elimination/trial')
      if 'body_step' not in native.get('input_sha256',{}):raise ValueError('03 report must bind the actual body STEP for root and q checks')
      keys=['formed_step','unfold_step','body_step']
      for key in keys:
       if hashlib.sha256(bound_file(key).read_bytes()).hexdigest()!=native['input_sha256'][key]:raise ValueError('native03 STEP input SHA mismatch')
      if hashlib.sha256(path.read_bytes()).hexdigest()!=native['input_sha256']['dxf']:raise ValueError('native03 DXF input SHA mismatch')
      from render_review_pdf import check_first_page
      check_first_page(bound_file('geometry_pdf'),effective)
      check_pdf_geometry(bound_file('geometry_pdf'),a['pdf_flat_page_index'],reading['outer_lines'],a['pdf_flat_map'])
      rec['native_CAD_report_bound']=True;rec['PDF_vectors_match_actual_DXF']=True;rec['root_HOLDs']=native.get('holds',[])
    from create_intake import apply_project_defaults
    effective=apply_project_defaults(project)
    if value(effective['handles']['enabled']) is True and value(effective['handles']['layout'])=='four_hole_trapezoid' and any(pat['part_id'] in owners for pat in effective['handles']['patterns']):
     def handle_file(key):
      q=(root/a[key]).resolve()
      if not q.is_relative_to(root):raise ValueError('handle evidence path escapes root')
      return q
     report=json.loads(handle_file('handle_geometry_report').read_text())
     if report.get('ok') is not True or report.get('CAD_executed') is not True or report.get('parameter_hash')!=digest:raise ValueError('actual handle STEP/DXF report missing/failed/stale')
     for key,file in [('formed_step',handle_file('formed_step')),('dxf',path)]:
      if hashlib.sha256(file.read_bytes()).hexdigest()!=report['input_sha256'][key]:raise ValueError('handle geometry file SHA mismatch')
     from handle_readback import check_dxf
     handle_actual=check_dxf(effective,path,report['flat_maps'],owners)
     required={q['pattern_id'] for q in handle_actual['patterns']};reported={q['pattern_id'] for q in report['STEP']['patterns']}
     if required!=reported:raise ValueError('actual STEP report does not cover selected handle instances')
     rec['handle_actual_DXF']=handle_actual;rec['handle_STEP_report_bound']=True
    planar=validate_planar(ents,indices)
    rec.update(nonempty=True,closed_outer=True,circle_diameter_counts=dict(actual),only_CUT=True,**planar)
   checks.append(rec)
  except (ValueError,KeyError,OSError,TypeError) as ex:errors.append(a.get('path','?')+': '+str(ex))
 if project.get('input_mode')=='new_design' and (manifest.get('workflow_contract') in ['2.6.0-R05','2.6.1-R06'] or any(e['id']=='authorized-site-fit-lid-root' for e in project['exceptions'])):
  try:
   from formed_isometric import check_pdf
   def evidence_file(key):
    path=(root/manifest[key]).resolve()
    if not path.is_relative_to(root) or len([i for i in arts if (root/i['path']).resolve()==path])!=1:raise ValueError('ISOMETRIC: evidence missing artifact binding')
    return path
   iso_path=evidence_file('formed_isometric_report');iso=json.loads(iso_path.read_text());projection_path=evidence_file('cad_projections')
   pdfs=[i for i in arts if i.get('kind')=='pdf']
   if len(pdfs)!=1:raise ValueError('ISOMETRIC: one complete drawing PDF required')
   pdf_path=(root/pdfs[0]['path']).resolve()
   if iso.get('ok') is not True or iso.get('CAD_executed') is not True or iso.get('parameter_hash')!=digest or hashlib.sha256(pdf_path.read_bytes()).hexdigest()!=iso.get('pdf_sha256') or hashlib.sha256(projection_path.read_bytes()).hexdigest()!=iso.get('projections_sha256'):raise ValueError('ISOMETRIC: actual CAD/PDF binding stale')
   info=iso['parts']
   if set(info)!=planned_sheets:raise ValueError('ISOMETRIC: part evidence coverage mismatch')
   for part in project['fabrication']['parts']:
    owner=part['id'];step=next(i for i in arts if i.get('kind')=='step_part' and i.get('part_ids')==[owner])
    if info[owner]['actual_bends']!=value(part['bends']) or info[owner]['formed_sha256']!=step['sha256']:raise ValueError('ISOMETRIC: formed part SHA/bends mismatch')
   check_pdf(pdf_path,info,iso['views'],json.loads(projection_path.read_text()))
   from site_fit import acceptance_from_project,VOLUME_TOL_MM3
   accepted=acceptance_from_project(project);items=[i for i in arts if i.get('kind')=='run_result']
   if len(items)!=1:raise ValueError('SITE_FIT_RESULT: exactly one bound final RUN_RESULT required')
   result_path=(root/items[0]['path']).resolve()
   if not result_path.is_relative_to(root):raise ValueError('SITE_FIT_RESULT: path escapes root')
   final=json.loads(result_path.read_text())
   if final.get('site_fit_acceptance')!=accepted or final.get('geometry_interference_eliminated') is not False or final.get('trial_assembly_confirmed') is not False or final.get('production_release') is not False:raise ValueError('SITE_FIT_RESULT: false acceptance/elimination/trial/release state')
   if final.get('formed_isometric_parts')!=sorted(iso['views']) or final.get('formed_isometric_report')!=str(iso_path.relative_to(root)):raise ValueError('ISOMETRIC: final result view coverage differs')
   if value(project['requirements']['lid_required']):
    lid_item=next(i for i in arts if i.get('kind')=='dxf' and i.get('part_ids')==['LID']);np=(root/lid_item['native_geometry_report']).resolve()
    if not np.is_relative_to(root):raise ValueError('SITE_FIT_RESULT: native path escapes root')
    measured=json.loads(np.read_text());volume=measured['root_overlap_volume_mm3'];positive=volume>VOLUME_TOL_MM3;status='DELIVERED_FOR_AUTHORIZED_SITE_FIT_WITH_HOLD' if positive else 'GEOMETRY_CHECKED_WITH_HOLD'
    if positive and not accepted:raise ValueError('SITE_FIT_RESULT: positive root has no acceptance')
    if final.get('native03')!=measured or final.get('actual_root_overlap_volume_mm3')!=volume or final.get('assembly_interference_free') is not (not positive) or final.get('status')!=status or final.get('fit_disposition')!=measured.get('fit_disposition'):raise ValueError('SITE_FIT_RESULT: final result contradicts actual native report')
    if manifest.get('workflow_contract')=='2.6.1-R06':
     from interference_volume import measurement,require_same_measurement
     authority=value(project['lid']['root_overlap_volume']);policy=final['root_interference_measurement'];expected=measurement(authority,policy['pairwise_sum_mm3'])
     if policy!=expected or volume!=authority or measured.get('root_interference_measurement')!=measurement(authority):raise ValueError('INTERFERENCE_AUTHORITY: canonical/native/final source or display policy differs')
     require_same_measurement(authority,measured['fresh_body_lid_common_volume_mm3'])
  except (ValueError,KeyError,OSError,TypeError,StopIteration) as ex:errors.append('SITE_FIT_RESULT: '+str(ex))
 delivery=None
 if manifest.get('delivery_contract') or (value(project['project']['revision']) in ['v2.7.0-R07','v2.7.1-R08','v2.7.2-R09','v2.7.3-R10','v2.8.0-R11','v2.8.1-R12'] and not allow_geometry_only):
  try:
   from delivery_contract import manifest_contract_check,CONTRACT_REVISIONS
   if manifest.get('delivery_contract') not in CONTRACT_REVISIONS:raise ValueError('DELIVERY_CONTRACT_VERSION_REQUIRED_FOR_R07')
   delivery=manifest_contract_check(project,manifest,root)
  except Exception as ex:errors.append('COMPLETE_DELIVERY: '+str(ex))
 actual=None;general_bends=None
 if not errors and project.get('input_mode')=='new_design' and 'formed_isometric_report' in manifest:
  try:
   actual=actual_native_directions(project,manifest,root,iso,runtime)
   if actual.get('ok') is not True or actual.get('CAD_executed') is not True:errors.extend(actual.get('errors',['NATIVE_DIRECTION: actual readback failed']))
   elif manifest.get('general_process_contract'):
    from bend_dxf import check_manifest as check_bends
    general_bends=check_bends(root,manifest,actual)
  except Exception as ex:errors.append('NATIVE_DIRECTION: '+str(ex))
 dimensions=None
 if not errors and manifest.get('delivery_contract'):
  try:
   from pdf_dimension_authority import actual_dimensions
   dimensions=actual_dimensions(project,manifest,root,runtime)
  except Exception as ex:errors.append('ACTUAL_DIMENSION_AUTHORITY: '+str(ex))
 return {'ok':not errors,'errors':errors,'checks':checks,'actual_native_direction_readback':actual,'actual_BEND_DXF_readback':general_bends,'actual_STEP_dimension_readback':dimensions,'delivery_contract_check':delivery,'certifies_manufacture':False,'scope':'actual native CAD direction/root and fresh STEP dimensions vs source/canonical and printed PDF labels; complete digital contract is not production approval'}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('project');p.add_argument('manifest');p.add_argument('--root',required=True)
 for name in ['cad-python','freecad-lib','sheetmetal-path','pdf-renderer']:p.add_argument('--'+name)
 a=p.parse_args()
 try:
  runtime=None
  if any(getattr(a,k) for k in ['cad_python','freecad_lib','sheetmetal_path','pdf_renderer']):
   from runtime_paths import locate
   runtime=locate(a.cad_python,a.freecad_lib,a.sheetmetal_path,a.pdf_renderer)
  result=check(json.loads(Path(a.project).read_text()),json.loads(Path(a.manifest).read_text()),a.root,runtime)
 except Exception as ex:result={'ok':False,'errors':[str(ex)],'certifies_manufacture':False}
 print(json.dumps(result,ensure_ascii=False,indent=2));raise SystemExit(0 if result['ok'] else 2)
