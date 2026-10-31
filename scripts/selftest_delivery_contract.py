#!/usr/bin/env python3
"""Reproduce R07 author validation with raw synthetic jobs; independent review remains separate."""
import argparse,copy,hashlib,json,shutil,subprocess,sys
from pathlib import Path
from delivery_contract import check_envelope,manifest_contract_check,parse_dxf,write_entities,translate,bbox,sha
from validate_manifest import actual_native_directions
ROOT=Path(__file__).resolve().parents[1]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',required=True);ap.add_argument('--reuse-author-directory',help='Resume author check from previously generated synthetic raw runs, never modifies them');a=ap.parse_args();out=Path(a.output).resolve()
 if out.exists():ap.error('Output must not exist')
 out.mkdir(parents=True);results={'author_selftest_only':True,'independent_acceptance':'PENDING','production_release':False,'positive':[],'negative':[]}
 runs=Path(a.reuse_author_directory).resolve() if a.reuse_author_directory else out/'runs'
 if not a.reuse_author_directory:
  runs.mkdir()
  for name in ['external','wrap']:
   src=ROOT/'assets/examples'/('delivery-'+name+'.job.json');job=json.loads(src.read_text());target=runs/(name+'.job.json');target.write_text(json.dumps(job,indent=2))
   with (runs/(name+'.log')).open('wb') as log:r=subprocess.run([sys.executable,'-B',str(ROOT/'scripts/build_package.py'),str(target),'--output',str(runs/'deliveries')],stdout=log,stderr=subprocess.STDOUT,timeout=1500)
   if r.returncode:raise RuntimeError(name+' generation failed; inspect raw log')
  first=next((runs/'deliveries/requirement_AUTHOR_EXTERNAL_380').rglob('*DELIVERY_ENVELOPE_*.json')).parent;source=next((first/'STEP').glob('*ASSEMBLY_*.step'))
  with (runs/'source.log').open('wb') as log:r=subprocess.run([sys.executable,'-B',str(ROOT/'scripts/audit_step.py'),str(source),'--output',str(runs/'source_deliveries'),'--entity-id','AUTHOR_IMPORTED_NO_K','--revision','R01'],stdout=log,stderr=subprocess.STDOUT,timeout=1500)
  if r.returncode!=2:raise RuntimeError('Source unknown-K case must exit2')
 positives=[]
 for key in ['requirement_AUTHOR_EXTERNAL_380','customer_AUTHOR_WRAP_185']:
  envs=sorted((runs/'deliveries'/key).rglob('*DELIVERY_ENVELOPE_*.json'))
  if not envs:raise RuntimeError('No completed synthetic case '+key)
  root=envs[-1].parent;gate=check_envelope(root);env=json.loads(envs[-1].read_text());m=json.loads((root/env['manifest']).read_text());p=json.loads(next(root.glob('*project_*.json')).read_text());positives.append((root,p,m));results['positive'].append({'root':str(root),'gate':gate,'envelope':env})
 source=next((runs/'source_deliveries').rglob('SOURCE_DELIVERY_STATUS_*.json'));state=json.loads(source.read_text())
 if state['digital_deliverables_complete'] or state['manufacturing_delivery_complete'] or state['production_release']:raise RuntimeError('False source completeness')
 try:check_envelope(source.parent,check_cad=False)
 except Exception as ex:results['negative'].append({'case':'source unknown material/K','test':'promote source audit to full manufacturing','rejected':True,'error':str(ex)})
 else:raise RuntimeError('Source partial accepted as complete')
 results['source_partial']=state
 root,p,m=positives[0]
 # Negative fixtures are copies, correctly nested in the same relative revision layout.
 def fixture(label):
  dest=out/'negative_fixtures'/label/Path(*root.parts[-3:]);shutil.copytree(root,dest);return dest,copy.deepcopy(p),copy.deepcopy(m)
 def reject(label,mutate,whole=False):
  dest,project,manifest=fixture(label);mutate(dest,project,manifest)
  try:
   if whole:check_envelope(dest,check_cad=False)
   else:manifest_contract_check(project,manifest,dest)
  except Exception as ex:results['negative'].append({'test':label,'rejected':True,'error':str(ex),'fixture':str(dest)})
  else:raise RuntimeError('Negative unexpectedly accepted '+label)
 kinds=['step_assembly','step_exploded','step_part','unfold_step','dxf','confirmation_png','pdf','formed_isometric_report','cad_projections','source_job','parameters','hole_table','cad_report','delivery_spec','bom_json','bom_csv','nest_layout','nest_dxf','nest_preview_pdf','acceptance_report']
 for kind in kinds:
  reject('missing_'+kind,lambda dest,p,m,k=kind:m.update(artifacts=[a for a in m['artifacts'] if a['kind']!=k]))
 reject('removed_R07_contract_no_silent_core_downgrade',lambda dest,p,m:m.pop('delivery_contract'))
 def edit(dest,m,kind,fn):
  art=next(a for a in m['artifacts'] if a['kind']==kind);path=dest/art['path'];d=json.loads(path.read_text());fn(d);path.write_text(json.dumps(d,ensure_ascii=False,indent=2));art['sha256']=sha(path)
 reject('wrong_version_rebound_SHA',lambda dest,p,m:edit(dest,m,'delivery_spec',lambda d:d.update(version='STALE')))
 reject('wrong_material_rebound_SHA',lambda dest,p,m:edit(dest,m,'bom_json',lambda rows:rows[0].update(material='304_WRONG')))
 reject('wrong_actual_thickness_rebound_SHA',lambda dest,p,m:edit(dest,m,'cad_report',lambda d:d['parts']['U'].update(unfold_t_mm=2.4)))
 def layout_mutation(dest,m,mode):
  a=next(a for a in m['artifacts'] if a['kind']=='nest_layout');path=dest/a['path'];layout=json.loads(path.read_text());dxfs={a['part_ids'][0]:dest/a['path'] for a in m['artifacts'] if a['kind']=='dxf'}
  if mode=='omit':layout['placements'].pop()
  if mode=='overlap':
   p1,p2=layout['placements'][:2];p2['translation_mm']=[v+3 for v in p1['translation_mm']];p2['sheet']=p1['sheet'];p2['bbox_mm']=bbox([translate(e,*p2['translation_mm']) for e in parse_dxf(dxfs[p2['part_id']])])
  path.write_text(json.dumps(layout,indent=2));a['sha256']=sha(path)
  for na in [a for a in m['artifacts'] if a['kind']=='nest_dxf']:
   es=[translate(e,*p['translation_mm']) for p in layout['placements'] if p['sheet']==na['sheet'] for e in parse_dxf(dxfs[p['part_id']])]
   if mode=='scale':
    for e in es:
     for k in [10,20,11,21,40]:
      if k in e:e[k]=float(e[k])*2
   write_entities(dest/na['path'],es);na['sha256']=sha(dest/na['path'])
 for mode in ['omit','overlap','scale']:reject('nest_'+mode+'_rebound_layout_DXF_SHA',lambda dest,p,m,mode=mode:layout_mutation(dest,m,mode))
 def missing_zip(dest,p,m):
  e=json.loads(next(dest.glob('*DELIVERY_ENVELOPE_*.json')).read_text());(dest/e['zip']).unlink()
 reject('missing_final_ZIP',missing_zip,True)
 # The actual source CAD re-read must reject a synchronized JSON direction lie.
 for root,p,m in positives:
  iso=json.loads((root/m['formed_isometric_report']).read_text());changed=False
  for v in iso['views'].values():
   for b in v['bend_labels']:
    if b['direction']=='DOWN':b['direction']='UP';b['angle_signed_deg']=90.;changed=True
  if not changed:raise RuntimeError('Synthetic fixture lacks native DOWN bend for direction counterexample')
  actual=actual_native_directions(p,m,root,iso)
  if actual.get('ok'):raise RuntimeError('Native CAD direction lie accepted')
  results['negative'].append({'test':'inherited_R06_actual_DOWN_vs_synchronized_UP_json','case':str(root),'rejected':True,'evidence':actual})
 for root,p,m in positives:check_envelope(root,check_cad=False)
 results['status']='AUTHOR_CONTROLLED_VALIDATION_PASS_PENDING_INDEPENDENT_REVIEW';(out/'AUTHOR_DELIVERY_CONTRACT_RESULTS.json').write_text(json.dumps(results,ensure_ascii=False,indent=2));print(json.dumps({'status':results['status'],'positive_cases':len(results['positive']),'negative_cases':len(results['negative']),'source_partial':state['status']},indent=2))
if __name__=='__main__':main()
