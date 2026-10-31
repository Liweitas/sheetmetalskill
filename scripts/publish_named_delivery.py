#!/usr/bin/env python3
"""Publish a renamed copy, preserving every CAD/DXF byte and the original design job."""
import argparse,copy,hashlib,json,shutil,zipfile
from pathlib import Path
from factory_naming import resolve,filename_map
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def rewrite(value,table):
 if isinstance(value,dict):return {table.get(k,k):rewrite(v,table) for k,v in value.items()}
 if isinstance(value,list):return [rewrite(v,table) for v in value]
 return table.get(value,value) if isinstance(value,str) else value

def leaf(naming,delivery):return naming['prefix'] if naming['code'] is None else naming['prefix']+'_'+delivery['revision']

def check_named(root,envelope,manifest,delivery,job):
 root=Path(root);n=envelope.get('naming')
 if not isinstance(n,dict) or 'record' not in n:raise ValueError('NAMING_R09_PUBLICATION_REQUIRED')
 record_path=root/n['record']
 if not record_path.resolve().is_relative_to(root.resolve()) or not record_path.is_file():raise ValueError('NAMING_RECORD_ABSENT')
 record=json.loads(record_path.read_text());expected=resolve(record['request'],job,delivery)
 if record['resolved']!=expected or any(n.get(k)!=expected[k] for k in ['status','code','prefix']):raise ValueError('NAMING_SOURCE_RULE_MISMATCH')
 if record['original_source_job_sha256']!=envelope_source_sha(root,manifest):raise ValueError('NAMING_ORIGINAL_JOB_BINDING')
 protected={str(p.relative_to(root)) for p in root.rglob('*') if p.is_file() and p.suffix.lower() in ['.step','.stp','.dxf','.fcstd','.brep']}
 protected.update(a['path'] for a in manifest['artifacts'] if a['kind']=='source_job');proof=record.get('manufacturing_and_source_job_bytes_unchanged',{})
 if set(proof)!=protected or any(sha(root/p)!=h for p,h in proof.items()):raise ValueError('NAMING_MANUFACTURING_BYTE_BINDING')
 if tuple(root.parts[-3:])!=(delivery['namespace']+'_'+delivery['entity_id'],'revisions',leaf(expected,delivery)):raise ValueError('NAMING_DIRECTORY_IDENTITY')
 prefix=expected['prefix']+'_'
 if not envelope['zip'].startswith(prefix) or any(not p.name.startswith(prefix) for p in root.rglob('*') if p.is_file()):raise ValueError('NAMING_ALL_FILES_REQUIRE_SHARED_PREFIX')
 for art in manifest['artifacts']:
  label=__import__('factory_naming').LABELS.get(art['kind'])
  if label and not Path(art['path']).name.startswith(prefix+label+'_'):raise ValueError('NAMING_ROLE_SUFFIX: '+art['kind'])
 return {'ok':True,'status':expected['status'],'code':expected['code'],'missing_fields':expected['missing_fields'],'source_job_and_manufacturing_bytes_preserved':True,'factory_allocation_authenticity':'sender/factory verifies; no global serial assignment or reset'}

def envelope_source_sha(root,manifest):
 arts=[a for a in manifest['artifacts'] if a['kind']=='source_job']
 if len(arts)!=1:raise ValueError('NAMING_SOURCE_JOB_REQUIRED')
 return sha(Path(root)/arts[0]['path'])

def publish(source,base,request=None,runtime=None,source_already_checked=False):
 from delivery_contract import check_envelope,current_workshop_requirements
 from delivery_dispatch import make_plan,CONTRACT
 from validate_project import parameter_hash
 source=Path(source).resolve();base=Path(base).resolve()
 if not source_already_checked:check_envelope(source,runtime=runtime,allow_unpublished=True,allow_legacy_publication=True)
 ep=next(source.glob('*DELIVERY_ENVELOPE_*.json'));e=json.loads(ep.read_text());mp=source/e['manifest'];m=json.loads(mp.read_text());spec=json.loads((source/next(a['path'] for a in m['artifacts'] if a['kind']=='delivery_spec')).read_text());d=spec['delivery'];job=json.loads((source/next(a['path'] for a in m['artifacts'] if a['kind']=='source_job')).read_text())
 project=json.loads((source/next(a['path'] for a in m['artifacts'] if a['kind']=='parameters')).read_text());source_result=json.loads((source/next(a['path'] for a in m['artifacts'] if a['kind']=='run_result')).read_text());workshop_complete=current_workshop_requirements(project,m,spec,source_result)
 naming=resolve(request,job,d);dest=base/(d['namespace']+'_'+d['entity_id'])/'revisions'/leaf(naming,d)
 if dest.exists():raise ValueError('NAMING_DUPLICATE_OUTPUT: factory owns number/reset; never auto renumber or overwrite')
 if dest.is_relative_to(source) or source.is_relative_to(dest):raise ValueError('NAMING_OUTPUT_MUST_NOT_CONTAIN_SOURCE')
 previous=e.get('naming',{}).get('code')
 if previous and naming['code']!=previous and (not request or request.get('previous_code')!=previous):raise ValueError('NAMING_UPGRADE_REQUIRES_ACTUAL_PREVIOUS_CODE')
 before={str(p.relative_to(source)):sha(p) for p in source.rglob('*') if p.is_file()};exclude={e['zip'],e['inventory'],ep.name}
 if e.get('naming',{}).get('record'):exclude.add(e['naming']['record'])
 files=sorted(set(before)-exclude);mapping=filename_map(files,m,naming['prefix'],e.get('naming',{}).get('prefix'));dest.mkdir(parents=True)
 for name,new in mapping.items():
  target=dest/new;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source/name,target)
 raw_job=next(a['path'] for a in m['artifacts'] if a['kind']=='source_job');json_files=[name for name in files if Path(name).suffix=='.json' and name!=raw_job]
 for name in json_files:
  path=dest/mapping[name];path.write_text(json.dumps(rewrite(json.loads(path.read_text()),mapping),ensure_ascii=False,indent=2))
 params=next(a['path'] for a in m['artifacts'] if a['kind']=='parameters');old_parameter_hash=m['parameter_hash'];new_parameter_hash=parameter_hash(json.loads((dest/mapping[params]).read_text()))
 for name in json_files:
  path=dest/mapping[name];path.write_text(json.dumps(rewrite(json.loads(path.read_text()),{old_parameter_hash:new_parameter_hash}),ensure_ascii=False,indent=2))
 aliases={}
 for iteration in range(40):
  changes={}
  # Only rewritten JSON creates a changed hash dependency. A native report and
  # its historical stdout log can originally share bytes; logs stay untouched.
  for name in json_files:
   old=before[name];new=sha(dest/mapping[name])
   if old in changes and changes[old]!=new:raise ValueError('NAMING_AMBIGUOUS_HASH_DEPENDENCY')
   changes[old]=new
  aliases={k:changes.get(v,v) for k,v in aliases.items()};aliases.update(changes);modified=False
  for name in json_files:
   path=dest/mapping[name];data=json.loads(path.read_text());updated=rewrite(data,aliases)
   if data!=updated:
    previous=sha(path);path.write_text(json.dumps(updated,ensure_ascii=False,indent=2));aliases[previous]=sha(path);modified=True
  if not modified:break
 else:raise ValueError('NAMING_HASH_DEPENDENCIES_DID_NOT_CONVERGE')
 from publication_contract import CONTRACT as PUBLICATION_CONTRACT,RELEASE as PUBLISHER_RELEASE
 newm=json.loads((dest/mapping[e['manifest']]).read_text());newm['publication_contract']=PUBLICATION_CONTRACT;newm['publisher_release']=PUBLISHER_RELEASE
 for art in newm['artifacts']:art['sha256']=sha(dest/art['path'])
 (dest/mapping[e['manifest']]).write_text(json.dumps(newm,ensure_ascii=False,indent=2))
 geometry=[name for name in files if Path(name).suffix.lower() in ['.step','.stp','.dxf','.fcstd','.brep'] or name==raw_job]
 for name in geometry:
  if sha(dest/mapping[name])!=before[name]:raise ValueError('NAMING_CHANGED_MANUFACTURING_OR_JOB_BYTES: '+name)
 record_name=naming['prefix']+'_文件更名与命名记录_FILE_NAMING.json';record={'request':request or {},'resolved':naming,'original_source_zip_sha256':before[e['zip']],'original_source_job_sha256':before[raw_job],'mapping':mapping,'manufacturing_and_source_job_bytes_unchanged':{mapping[n]:before[n] for n in geometry},'original_parameter_hash':old_parameter_hash,'renamed_reference_parameter_hash':new_parameter_hash,'manufacturing_geometry_changed':False,'production_release':False,'publication_contract':PUBLICATION_CONTRACT,'publisher_release':PUBLISHER_RELEASE,'source_manufacturing_contract':m['delivery_contract']}
 (dest/record_name).write_text(json.dumps(record,ensure_ascii=False,indent=2))
 inventory_name=naming['prefix']+'_文件哈希_FILE_SHA256.json';zp=dest/(naming['prefix']+'_完整资料.zip');envpath=dest/(naming['prefix']+'_交付封套_DELIVERY_ENVELOPE_正式.json')
 rows=[{'path':str(p.relative_to(dest)),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(dest.rglob('*')) if p.is_file()];(dest/inventory_name).write_text(json.dumps({'contract':e['contract'],'files':rows},ensure_ascii=False,indent=2))
 with zipfile.ZipFile(zp,'x',zipfile.ZIP_DEFLATED) as z:
  for p in sorted(dest.rglob('*')):
   if p.is_file() and p!=zp:z.write(p,dest.name+'/'+str(p.relative_to(dest)))
 newe={k:v for k,v in e.items() if k not in ['naming','final_message_plan','publication_stage']};newe.update(revision_root=str(dest),manifest=mapping[e['manifest']],inventory=inventory_name,zip=zp.name,zip_sha256=sha(zp),naming={k:naming[k] for k in ['status','code','prefix']},current_workshop_requirements_complete=workshop_complete);newe['publication_contract']=PUBLICATION_CONTRACT;newe['publisher_release']=PUBLISHER_RELEASE;newe['naming']['record']=record_name;newe['message_dispatch_contract']=CONTRACT;newe['final_message_plan']=make_plan(dest,newe,d,newm);envpath.write_text(json.dumps(newe,ensure_ascii=False,indent=2))
 gate=check_envelope(dest,runtime=runtime)
 assert before=={str(p.relative_to(source)):sha(p) for p in source.rglob('*') if p.is_file()}
 return {'revision_root':str(dest),'delivery':newe,'checks':gate,'manufacturing_geometry_changed':False,'original_source_unchanged':True}

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('revision_root');p.add_argument('--output',required=True);p.add_argument('--naming');a=p.parse_args()
 try:print(json.dumps(publish(a.revision_root,a.output,json.loads(Path(a.naming).read_text()) if a.naming else None),ensure_ascii=False,indent=2))
 except Exception as ex:print(json.dumps({'ok':False,'error':str(ex),'production_release':False},ensure_ascii=False));raise SystemExit(2)
