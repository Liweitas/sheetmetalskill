"""Same current geometry confirmation, or explicit essential-input dossier; never invent laser/manufacturing completeness."""
import hashlib,json,shutil,subprocess,sys,zipfile,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def pdf(path,compiled,report=None,projections=None):
 from cn_confirmation import write
 return write(path,compiled,report,projections)

def build_review(source,compiled,base,run,a):
 from delivery_contract import resolved_delivery,revision_root
 from factory_naming import resolve,filename_map
 from publish_named_delivery import leaf
 from delivery_dispatch import make_plan,check_plan,CONTRACT
 source=Path(source);work=run/'confirmation_work';work.mkdir();job=compiled.get('job');report=None;projections=None
 if job:
  jobpath=run/'compiled_review.job.json';jobpath.write_text(json.dumps(job,ensure_ascii=False,indent=2));cmd=[sys.executable,'-B',str(ROOT/'scripts/review_box.py'),str(jobpath),'--output',str(work/'formed')]
  for key in ['cad_python','freecad_lib','sheetmetal_path','pdf_renderer']:
   if getattr(a,key,None):cmd+=['--'+key.replace('_','-'),getattr(a,key)]
  p=subprocess.run(cmd,capture_output=True,text=True,timeout=1500);(work/'review_entry.stdout.json').write_text(p.stdout);(work/'review_entry.stderr.log').write_text(p.stderr)
  if p.returncode:raise ValueError('GENERAL_FORMED_REVIEW_FAILED: '+p.stderr[-1200:])
  report=json.loads((work/'formed/cad/cad_report.json').read_text());projections=json.loads((work/'formed/cad/projections.json').read_text())
  _,delivery=revision_root(base,job);request=json.loads(Path(a.naming).read_text()) if a.naming else None;naming=resolve(request,job,delivery)
 else:
  brief=json.loads(source.read_text());pseudo={'id':brief.get('id','REQ_'+hashlib.sha256(source.read_bytes()).hexdigest()[:10]),'delivery':brief.get('delivery',{})};_,delivery=revision_root(base,pseudo);naming={'prefix':'未命名待确认_'+delivery['namespace']+'_'+delivery['entity_id']+'_'+delivery['revision'],'code':None,'status':'UNNAMED_PENDING_PROCESS_DECISION' if compiled['status']=='NEEDS_PROCESS_DECISION' else 'UNNAMED_PENDING_ESSENTIAL_INPUT'}
 (work/'original_brief.json').write_bytes(source.read_bytes());(work/'confirmation_parameters.json').write_text(json.dumps(compiled,ensure_ascii=False,indent=2));pdf(work/'确认稿_三视来源与参数.pdf',compiled,report,projections)
 artifacts=[]
 for p in work.rglob('*'):
  if p.is_file():
   kind='confirmation_pdf' if p.suffix=='.pdf' else 'confirmation_png' if p.suffix=='.png' else 'step_assembly' if p.name=='ASSEMBLY.step' else 'step_exploded' if p.name=='EXPLODED.step' else 'step_part' if p.suffix=='.step' else 'review_evidence';artifacts.append({'path':str(p.relative_to(work)),'kind':kind})
 mapping=filename_map([x['path'] for x in artifacts],{'artifacts':artifacts,'general_effective_stage':'confirmation_draft'},naming['prefix']);dest=Path(base)/(delivery['namespace']+'_'+delivery['entity_id'])/'revisions'/(leaf(naming,delivery)+'_CONFIRMATION')
 if dest.exists():raise ValueError('REVIEW_REVISION_EXISTS')
 dest.mkdir(parents=True);catalog=[]
 for art in artifacts:
  q=dest/mapping[art['path']];q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(work/art['path'],q);assert sha(q)==sha(work/art['path']);catalog.append({'path':mapping[art['path']],'kind':art['kind'],'sha256':sha(q)})
 status={'contract':'general-confirmation-only-v1','status':'FORMED_CONFIRMATION_ONLY_HOLD' if job else compiled['status'],'naming':naming,'production_release':False,'manufacturing_delivery_complete':False,'digital_manufacturing_complete':False,'source_brief_sha256':sha(source),'actual_CAD_executed':report is not None,'actual_intersections':report['intersections'] if report else [],'pending':compiled.get('pending',compiled.get('missing',[])),'adjustment_candidates':compiled.get('adjustment_candidates',[]),'format_slots':{'STEP_assembly_exploded_parts':'PRESENT_REVIEW_ONLY' if report else 'BLOCKED_PROCESS_CONFLICT' if compiled['status']=='NEEDS_PROCESS_DECISION' else 'BLOCKED_ESSENTIAL_INPUT','true_unfold_CUT_BEND_nest':'NOT_GENERATED_UNRESOLVED_REVIEW','bending_PDF':'CONFIRMATION_ONLY_NO_MACHINE_PROGRAM'},'artifacts':catalog}
 sp=dest/(naming['prefix']+'_确认状态_GENERAL_REVIEW_STATUS.json');sp.write_text(json.dumps(status,ensure_ascii=False,indent=2));z=dest/(naming['prefix']+'_确认稿资料.zip')
 with zipfile.ZipFile(z,'x',zipfile.ZIP_DEFLATED) as f:
  for p in sorted(dest.rglob('*')):
   if p.is_file() and p!=z:f.write(p,dest.name+'/'+str(p.relative_to(dest)))
 envelope={'zip':z.name,'zip_sha256':sha(z)};plan=make_plan(dest,envelope,delivery,{'artifacts':catalog});check_plan(dest,plan,envelope,delivery,{'artifacts':catalog})
 with zipfile.ZipFile(z) as f:
  assert f.testzip() is None
  for art in catalog:assert hashlib.sha256(f.read(dest.name+'/'+art['path'])).hexdigest()==art['sha256']
 from validate_general_review import check
 integrity=check(dest)
 return {'review_integrity':integrity,'revision_root':str(dest),'review':status,'zip':str(z),'zip_sha256':sha(z),'default_final_message_plan':plan,'production_release':False}
