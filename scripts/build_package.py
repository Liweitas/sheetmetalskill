#!/usr/bin/env python3
"""One supported new-box run: resolve -> CAD -> native03 -> drawings -> complete manifest -> renders."""
import argparse,csv,hashlib,json,os,shutil,subprocess,sys
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from design_job import resolve_job,project_for
from validate_project import validate,parameter_hash,value
from validate_manifest import check
from drawing_pdf import write_drawings
ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(cmd,log,timeout=900):
 with Path(log).open("wb") as stream:
  result=subprocess.run(cmd,stdout=stream,stderr=subprocess.STDOUT,timeout=timeout,env={**os.environ,"PYTHONDONTWRITEBYTECODE":"1"})
 if result.returncode:raise RuntimeError("Required subprocess failed; inspect "+str(log))
def execute_core(a):
 source=Path(a.job).resolve();job=json.loads(source.read_text());resolved=resolve_job(job)
 resolved['delivery']=a._delivery
 from site_fit import require_delivery_decision,EXCEPTION_ID,VOLUME_TOL_MM3
 require_delivery_decision(resolved)
 import reportlab,pypdf
 from runtime_paths import locate,probe
 from PIL import Image
 import numpy
 runtime=locate(a.cad_python,a.freecad_lib,a.sheetmetal_path,a.pdf_renderer)
 dependency_probe=probe(runtime,ROOT)
 cad=Path(runtime['cad_python']);sm=Path(runtime['sheetmetal_path']);renderer=runtime['pdf_renderer'];a.freecad_lib=runtime['freecad_lib']
 out=Path(a.output).resolve()
 if out.exists():raise ValueError("OUTPUT_EXISTS: choose a new empty run path; no overwrite")
 if out==source or out in source.parents:raise ValueError("Output must not contain/replace the job input")
 now=datetime.now(ZoneInfo("Asia/Shanghai"));version=now.strftime("%Y%m%d_%H%M");recorded=now.isoformat(timespec="seconds")
 project=project_for(job,resolved,source,version,recorded);model_check=validate(project,"model")
 if not model_check["ok"]:raise ValueError("MODEL_PARAMETERS_BLOCKED: "+json.dumps(model_check["errors"]))
 out.mkdir(parents=True);a._created_output=out;a._phase="CAD_build";e=out/"evidence";e.mkdir();step=out/"STEP";step.mkdir();dxf=out/"DXF";dxf.mkdir();pdfdir=out/"PDF";pdfdir.mkdir()
 (e/("dependency_probe_"+version+".json")).write_text(json.dumps({"runtime":runtime,"API_probe":dependency_probe},indent=2))
 input_copy=out/("source_job_"+version+".json");shutil.copy2(source,input_copy)
 resolved_path=e/("resolved_job_"+version+".json");resolved_path.write_text(json.dumps(resolved,indent=2))
 cadout=e/"cad_work"
 cmd=[str(cad),str(ROOT/"scripts/cad_build.py"),str(resolved_path),"--output",str(cadout),"--sheetmetal-path",str(sm)]
 if a.freecad_lib:cmd+=["--freecad-lib",a.freecad_lib]
 run(cmd,e/("cad_execution_"+version+".log"))
 report=json.loads((cadout/"cad_report.json").read_text());projections=json.loads((cadout/"projections.json").read_text())
 formed={};unfolded={};dxfs={}
 for name,p in report["parts"].items():
  formed[name]=step/(name+"_"+version+".step");unfolded[name]=e/(name+"_UNFOLD_"+version+".step");dxfs[name]=dxf/(name+"_"+version+".dxf")
  (cadout/p["formed_step"]).rename(formed[name]);(cadout/p["unfold_step"]).rename(unfolded[name]);(cadout/p["dxf"]).rename(dxfs[name])
  part=next(x for x in project["fabrication"]["parts"] if x["id"]==name)
  for axis,n in zip("XYZ",[p["bbox"][i+3]-p["bbox"][i] for i in range(3)]):part["dimensions"][axis].update(value=n,status="measured",source=["cad"],note="Actual exported formed STEP bbox")
 body=e/("BODY_"+version+".step");(cadout/"BODY.step").rename(body)
 assembly=step/("ASSEMBLY_"+version+".step");exploded=step/("EXPLODED_"+version+".step");(cadout/"ASSEMBLY.step").rename(assembly);(cadout/"EXPLODED.step").rename(exploded)
 native=e/("LID_native03_"+version+".json")
 if resolved["lid_required"]:
  overlap=report['root_interference_measurement']['authoritative_volume_mm3']
  for k,v in {"root_check_passed":True,"root_overlap_volume":overlap,"root_check_ref":str(native.relative_to(out)),"geometry_evidence_ref":str(native.relative_to(out))}.items():project["lid"][k].update(value=v,status="measured",source=["cad"],note="Actual check completed; root_check_passed means measured/reviewed, not zero overlap. Positive overlap requires scoped site-fit acceptance.")
  for exception in project['exceptions']:
   if exception['id']==EXCEPTION_ID:
    exception['observed_overlap_volume'].update(value=overlap,status='measured',source=['cad'],note='Actual retained interference; not removed');exception['evidence_ref']=str(native.relative_to(out))
 project_path=out/("project_"+version+".json");project_path.write_text(json.dumps(project,ensure_ascii=False,indent=2))
 a._phase="cut_parameter_checks"
 cut_check=validate(project,"cut")
 if not cut_check["ok"]:raise RuntimeError("CUT_PARAMETERS_BLOCKED: "+json.dumps(cut_check["errors"]))
 digest=parameter_hash(project)
 if resolved["lid_required"]:
  a._phase="native03_readback"
  cmd=[str(cad),str(ROOT/"scripts/native03_check.py"),str(project_path),"--formed",str(formed["LID"]),"--unfold",str(unfolded["LID"]),"--dxf",str(dxfs["LID"]),"--body",str(body),"--module-path",str(sm),"--output",str(native)]
  if a.freecad_lib:cmd+=["--module-path",a.freecad_lib]
  run(cmd,e/("native03_execution_"+version+".log"));n=json.loads(native.read_text())
  if n.get("ok") is not True or n.get("CAD_executed") is not True:raise RuntimeError("NATIVE03_BLOCKED")
 else:n=None
 handle_reports={}
 if resolved.get('mounting_patterns'):
  for owner in sorted({pat['part_id'] for pat in resolved['mounting_patterns']}):
   a._phase='actual_handle_readback'
   maps={pat['id']:report['parts'][owner]['root_flat_map8'] for pat in resolved['mounting_patterns'] if pat['part_id']==owner}
   maps_path=e/(owner+'_handle_flat_maps_'+version+'.json');maps_path.write_text(json.dumps(maps,indent=2))
   target=e/(owner+'_handle_geometry_'+version+'.json')
   cmd=[str(cad),str(ROOT/'scripts/handle_readback.py'),str(project_path),'--step',str(formed[owner]),'--dxf',str(dxfs[owner]),'--flat-maps',str(maps_path),'--part',owner,'--output',str(target)]
   if a.freecad_lib:cmd+=['--module-path',a.freecad_lib]
   run(cmd,e/(owner+'_handle_execution_'+version+'.log'));handle_reports[owner]=target
 fixing_report=None
 if resolved.get('fixing_pairs'):
  fixing_report=e/('FIXINGS_geometry_'+version+'.json')
  fixing_report.write_text(json.dumps({'ok':True,'CAD_executed':True,'parameter_hash':digest,'pairs':report['fixing_pairs'],'input_sha256':{'formed_steps':{name:sha(path) for name,path in formed.items()},'dxfs':{name:sha(path) for name,path in dxfs.items()}},'strength_and_thread_fit':'HOLD','production_release':False},indent=2))
 from confirmation_png import previews
 image_paths=previews(resolved,report,json.loads((cadout/'preview_mesh.json').read_text()),out,version)
 a._phase="PDF_and_preview"
 master=pdfdir/(resolved["id"]+"_THREE_VIEWS_BENDING_HOLD_"+version+".pdf")
 mapping=write_drawings(project,resolved,report,projections,master,dxfs.get("LID"),native if n else None)
 iso_path=e/('FORMED_ISOMETRIC_'+version+'.json')
 iso_path.write_text(json.dumps({'ok':True,'CAD_executed':True,'parameter_hash':digest,'pdf_sha256':sha(master),'projections_sha256':sha(cadout/'projections.json'),'parts':{name:{**{k:p[k] for k in ['actual_bends','formed_sha256']},'native_fold_segments_mm':p['bend_lines']} for name,p in report['parts'].items()},'views':mapping['formed_isometric_views'],'checks':mapping['isometric_vector_checks'],'production_release':False},indent=2))
 manifest={"version":version,"timezone":"Asia/Shanghai","parameter_hash":digest,"workflow_contract":"2.6.1-R06","artifacts":[],**({"workshop_pdf_contract":mapping["workshop_pdf_contract"]} if mapping.get("workshop_pdf_contract") else {})}
 def artifact(path,kind,owners=None,**extra):
  item={"path":str(path.relative_to(out)),"kind":kind,"parameter_version":version,"parameter_hash":digest,"sha256":sha(path),**extra}
  if owners is not None:item["part_ids"]=owners
  manifest["artifacts"].append(item);return item
 for name,p in report["parts"].items():
  binding={"ok":True,"CAD_executed":True,"parameter_hash":digest,"part_ids":[name],"method":"Actual formed STEP readback and native SheetMetal unfold (rigid plane for zero-bend sheets)","actual_bends":p["actual_bends"],"actual_holes":p["actual_holes"],"input_sha256":{"formed_step":sha(formed[name]),"unfold_step":sha(unfolded[name]),"dxf":sha(dxfs[name])},"production_release":False}
  binding_path=e/(name+"_geometry_"+version+".json");binding_path.write_text(json.dumps(binding,indent=2))
  binding.update(native_DXF_area_difference_mm2=p['native_DXF_area_difference_mm2'],native_exported_unfold_area_difference_mm2=p['native_exported_unfold_area_difference_mm2'])
  binding_path.write_text(json.dumps(binding,indent=2))
  item=artifact(dxfs[name],"dxf",[name],stage="laser",outer_boundary_entity_indices=p["outer_boundary_entity_indices"],part_geometry_report=str(binding_path.relative_to(out)),formed_step=str(formed[name].relative_to(out)),unfold_step=str(unfolded[name].relative_to(out)))
  if name in handle_reports:item['handle_geometry_report']=str(handle_reports[name].relative_to(out))
  if name=="LID":item.update(native_geometry_report=str(native.relative_to(out)),body_step=str(body.relative_to(out)),geometry_pdf=str(master.relative_to(out)),pdf_flat_page_index=mapping["pdf_flat_page_index"],pdf_flat_map=mapping["pdf_flat_map"])
  artifact(formed[name],"step_part",[name]);artifact(unfolded[name],"unfold_step",[name]);artifact(binding_path,"geometry_report",[name])
 if resolved.get('general_process'):
  from bend_dxf import write as write_bend_dxf
  from general_sources import write as write_general_sources
  bd=out/'BEND';bd.mkdir();zero=[]
  for name,piece in report['parts'].items():
   if piece['actual_bends']:
    bp=bd/(name+'_BEND_ONLY_'+version+'.dxf');write_bend_dxf(bp,piece['bend_lines']);artifact(bp,'bend_dxf',[name],stage='bend_reference_not_laser')
   else:zero.append(name)
  usage=bd/('ZERO_BEND_AND_USAGE_'+version+'.txt');usage.write_text('BEND only: native fold fragments, never laser CUT. Zero-bend parts: '+','.join(zero)+'; no invented bend operations. All actual directions and sequence candidates are in the same PDF.\n');artifact(usage,'bend_usage')
  gp,gc,gr=write_general_sources(out,resolved['general_process'],version);artifact(gp,'general_parameter_sources');artifact(gc,'general_parameter_csv');artifact(gr,'general_parameter_report');manifest['general_process_contract']='general-process-v1';manifest['general_effective_stage']=resolved['general_process']['effective_stage']
  raw=out/('GENERAL_SOURCE_BRIEF_'+version+'.json')
  if getattr(a,'_general_brief_path',None):shutil.copyfile(a._general_brief_path,raw)
  else:raw.write_text(json.dumps(resolved['general_process']['brief'],ensure_ascii=False,indent=2))
  if json.loads(raw.read_text())!=resolved['general_process']['brief']:raise ValueError('GENERAL_RAW_BRIEF_CHANGED_DURING_BUILD')
  artifact(raw,'general_source_brief')
 artifact(assembly,"step_assembly");artifact(exploded,"step_exploded");artifact(master,"pdf")
 artifact(iso_path,'formed_isometric_report');manifest['formed_isometric_report']=str(iso_path.relative_to(out));manifest['cad_projections']='evidence/projections_'+version+'.json'
 if n:artifact(native,"geometry_report",["LID"])
 for name,path in handle_reports.items():artifact(path,'handle_geometry_report',[name])
 for path in image_paths:artifact(path,'confirmation_png')
 if fixing_report:
  artifact(fixing_report,'fixing_geometry_report');manifest['fixing_geometry_report']=str(fixing_report.relative_to(out))
 manifest_path=out/("manifest_"+version+".json");manifest_path.write_text(json.dumps(manifest,indent=2))
 a._phase="PDF_render"
 preview=out/"preview";preview.mkdir();run([str(renderer),"-png","-r","90",str(master),str(preview/"page")],e/("pdf_render_"+version+".log"))
 images=sorted(preview.glob("page-*.png"))
 if len(images)!=mapping["total_pages"]:raise RuntimeError("PDF_RENDER_INCOMPLETE")
 with (out/("holes_"+version+".csv")).open("w",newline="") as f:
  w=csv.writer(f);w.writerow(["id","part_id","D_mm","formed_X_mm","formed_Y_mm","formed_Z_mm","axis_X","axis_Y","axis_Z"])
  for h in resolved["holes"]:w.writerow([h["id"],h["part_id"],h["diameter"],*h["point"],*h["axis"]])
 for name in ["cad_report.json","projections.json","preview_mesh.json","cad_progress.json"]:
  (cadout/name).rename(e/(Path(name).stem+"_"+version+".json"))
 artifact(e/('projections_'+version+'.json'),'cad_projections')
 cadout.rmdir()
 result={"status":"GEOMETRY_CHECKED_WITH_HOLD","package_version":"2.8.1-R12","core_validation_contract":"2.6.1-R06","project":project_path.name,"manifest":manifest_path.name,"selected_method":resolved["method"],"sheet_parts":list(report["parts"]),"all_planned_DXFs_present":True,"CAD_executed":True,"native03_executed":bool(n),"native03":n,"pdf":str(master.relative_to(out)),"pdf_pages":mapping["total_pages"],"pdf_rendered_pages":len(images),"PDF_visual_review_required":True,"holds":report["holds"]+[x["code"] for x in cut_check["holds"]],"production_release":False,"source_job_sha256":sha(source)}
 result.update(candidate_resolutions=resolved.get('candidate_resolutions',[]),end_profile=report.get('end_profile'),fixing_pairs=report.get('fixing_pairs',[]),handle_geometry_reports={name:str(path.relative_to(out)) for name,path in handle_reports.items()},confirmation_images=[str(path.relative_to(out)) for path in image_paths],handle_body='not modeled; mounting reference only',manufacturing_profiles=[p['id'] for p in resolved.get('profiles',[])])
 result.update(fit=resolved['fit'],site_fit_acceptance=resolved.get('site_fit_acceptance'),geometry_interference_eliminated=False,trial_assembly_confirmed=False)
 if n:result['root_interference_measurement']=report['root_interference_measurement']
 result.update(formed_isometric_parts=sorted(mapping['formed_isometric_views']),formed_isometric_report=str(iso_path.relative_to(out)))
 if n:
  result.update(actual_root_overlap_volume_mm3=n['root_overlap_volume_mm3'],assembly_interference_free=n['assembly_interference_free'],fit_disposition=n['fit_disposition'])
  if n['root_overlap_volume_mm3']>VOLUME_TOL_MM3:result['status']='DELIVERED_FOR_AUTHORIZED_SITE_FIT_WITH_HOLD'
 if resolved.get('mounting_patterns'):result['holds'].append('ACTUAL_HANDLE_MODEL_AND_PHYSICAL_FIT_UNKNOWN')
 if resolved.get('fixing_pairs'):result['holds'].extend(['THIN_SHEET_M4_THREAD_STRENGTH','SHOP_TAP_AND_SCREW_FIT_NOT_VERIFIED'])
 result_path=out/("RUN_RESULT_"+version+".json");result_path.write_text(json.dumps(result,ensure_ascii=False,indent=2));a._tentative_result=result_path
 artifact(result_path,'run_result');manifest_path.write_text(json.dumps(manifest,indent=2))
 a._phase='core_geometry_gate_before_delivery';checked=check(project,manifest,out,runtime=runtime,allow_geometry_only=True)
 (e/('manifest_check_'+version+'.json')).write_text(json.dumps(checked,indent=2))
 if not checked['ok']:raise RuntimeError('ARTIFACT_GATE_BLOCKED: '+json.dumps(checked['errors']))
 a._tentative_result=None
 a._runtime=runtime
 return result
def execute(a):
 from delivery_contract import revision_root,finalize
 archive_base=Path(a.output).resolve()
 job=json.loads(Path(a.job).read_text());out,d=revision_root(archive_base/'.R09-unpublished-engineering',job)
 from factory_naming import resolve as naming_resolve
 from publish_named_delivery import leaf
 naming=json.loads(Path(a.naming).read_text()) if getattr(a,'naming',None) else None
 identity=naming_resolve(naming,job,d)
 if (archive_base/(d['namespace']+'_'+d['entity_id'])/'revisions'/leaf(identity,d)).exists():raise ValueError('NAMING_DUPLICATE_OUTPUT: choose explicitly authorized new revision or factory version, never auto renumber')
 a.output=str(out);a._delivery=d
 result=execute_core(a)
 a._phase='complete_delivery_nest_BOM_ZIP_gate'
 try:envelope=finalize(out,d,result,a._runtime)
 except Exception:
  for z in out.glob('*DELIVERY_*.zip'):z.rename(out/'evidence'/('UNACCEPTED_'+z.name))
  for e in out.glob('DELIVERY_ENVELOPE_*.json'):e.rename(out/'evidence'/('UNACCEPTED_'+e.name))
  for r in out.glob('RUN_RESULT_*.json'):r.rename(out/'evidence'/('GEOMETRY_ONLY_UNACCEPTED_'+r.name))
  raise
 from publish_named_delivery import publish
 published=publish(out,archive_base,naming,runtime=a._runtime,source_already_checked=True)
 published_root=Path(published['revision_root']);published_manifest=json.loads((published_root/published['delivery']['manifest']).read_text());published_result=json.loads((published_root/next(x['path'] for x in published_manifest['artifacts'] if x['kind']=='run_result')).read_text())
 print(json.dumps({**published,'engineering':published_result},ensure_ascii=False,indent=2));return published['delivery']
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument("job");ap.add_argument("--output",required=True);ap.add_argument("--cad-python");ap.add_argument("--freecad-lib");ap.add_argument("--sheetmetal-path");ap.add_argument("--pdf-renderer");ap.add_argument("--naming",help="Factory naming JSON, independent of geometric job/authorization; missing fields remain unnamed pending");a=ap.parse_args()
 try:execute(a)
 except Exception as ex:
  tentative=getattr(a,'_tentative_result',None)
  if tentative and tentative.exists():tentative.rename(tentative.parent/'evidence'/('UNACCEPTED_'+tentative.name))
  failure={"status":"BLOCKED","error":str(ex),"stage":getattr(a,"_phase","input_or_dependency_preflight"),"production_release":False,"partial_files_are_not_delivery":True}
  created=getattr(a,"_created_output",None)
  if created:
   progress=created/'evidence/cad_work/cad_progress.json'
   if progress.is_file():failure['CAD_progress']=json.loads(progress.read_text())
   failure["partial_files"]=[{"path":str(path.relative_to(created)),"bytes":path.stat().st_size,"sha256":sha(path)} for path in sorted(created.rglob("*")) if path.is_file()]
   (created/"BLOCKED_RESULT.json").write_text(json.dumps(failure,ensure_ascii=False,indent=2))
  print(json.dumps(failure,ensure_ascii=False),file=sys.stderr);raise SystemExit(2)
if __name__=="__main__":main()
