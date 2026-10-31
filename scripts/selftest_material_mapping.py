#!/usr/bin/env python3
"""Source-bound naming negatives on repacked copies of a real mapped delivery; no new CAD."""
import argparse,copy,json,shutil,zipfile
from pathlib import Path
from delivery_contract import sha,check_envelope
def main():
 p=argparse.ArgumentParser();p.add_argument('revision_root');p.add_argument('--output',required=True);p.add_argument('--keep-full-copies',action='store_true');a=p.parse_args();source=Path(a.revision_root).resolve();out=Path(a.output).resolve()
 if out.exists() or out.is_relative_to(source):raise ValueError('NEW_ISOLATED_TEST_OUTPUT_REQUIRED')
 before={str(x.relative_to(source)):sha(x) for x in source.rglob('*') if x.is_file()};out.mkdir(parents=True);ep=next(source.glob('*DELIVERY_ENVELOPE*.json'));e0=json.loads(ep.read_text());results=[]
 def case(label,change,expected):
  dest=out/label/Path(*source.parts[-3:]);shutil.copytree(source,dest);e=copy.deepcopy(e0);m=json.loads((dest/e['manifest']).read_text());record_path=dest/e['naming']['record'];record=json.loads(record_path.read_text());change(e,m,record,dest);record_path.write_text(json.dumps(record,ensure_ascii=False,indent=2))
  for art in m['artifacts']:art['sha256']=sha(dest/art['path'])
  (dest/e['manifest']).write_text(json.dumps(m,ensure_ascii=False,indent=2));e['revision_root']=str(dest);excluded={ep.name,e['zip'],e['inventory']}
  rows=[{'path':str(p.relative_to(dest)),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(dest.rglob('*')) if p.is_file() and str(p.relative_to(dest)) not in excluded];(dest/e['inventory']).write_text(json.dumps({'contract':e['contract'],'files':rows},ensure_ascii=False,indent=2))
  with zipfile.ZipFile(dest/e['zip'],'w',zipfile.ZIP_DEFLATED) as z:
   for p in sorted(dest.rglob('*')):
    if p.is_file() and p.name not in [ep.name,e['zip']]:z.write(p,dest.name+'/'+str(p.relative_to(dest)))
  e['zip_sha256']=sha(dest/e['zip'])
  if e.get('final_message_plan'):
   e['final_message_plan']['archive_sha256']=e['zip_sha256']
   for msg in e['final_message_plan']['messages']:
    for art in msg['attachments']:
     if art['path']==e['zip']:art['sha256']=e['zip_sha256']
  (dest/ep.name).write_text(json.dumps(e,ensure_ascii=False,indent=2))
  try:check_envelope(dest,check_cad=False)
  except Exception as ex:error=str(ex)
  else:raise ValueError('FALSE_ACCEPTANCE: '+label)
  if expected not in error:raise ValueError('WRONG_GUARD: '+label+' '+error)
  with zipfile.ZipFile(dest/e['zip']) as z:
   if z.testzip() is not None:raise ValueError('NEGATIVE_REPACK_CRC')
   members={dest.name+'/'+str(p.relative_to(dest)):sha(p) for p in dest.rglob('*') if p.is_file() and p.name not in [ep.name,e['zip']]}
   if set(members)!=set(z.namelist()) or any(__import__('hashlib').sha256(z.read(n)).hexdigest()!=h for n,h in members.items()):raise ValueError('NEGATIVE_REPACK_MEMBER_HASH')
  result={'test':label,'all_inventory_manifest_ZIP_hashes_rebound':True,'ZIP_CRC_and_members_verified':True,'rejected':True,'error':error,'expected_guard':expected,'ZIP_sha256':e['zip_sha256']}
  proof=out/(label+'_EVIDENCE');proof.mkdir();catalog=[]
  for p in sorted(dest.rglob('*')):
   if not p.is_file():continue
   rel=str(p.relative_to(dest));digest=sha(p);same=before.get(rel)==digest;catalog.append({'path':rel,'sha256':digest,'bytes':p.stat().st_size,'same_as_unchanged_canonical_source':same})
   if not same and p.suffix=='.json':
    q=proof/rel;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
  (proof/'RECONSTRUCTION_CATALOG.json').write_text(json.dumps({'canonical_source':str(source),'source_file_hashes':before,'modified_JSON_in_this_directory':True,'copy_catalog':catalog,'result':result},ensure_ascii=False,indent=2))
  results.append(result);(out/'MATERIAL_MAPPING_NEGATIVES.json').write_text(json.dumps({'author_test_only':True,'partial':len(results)<8,'results':results},ensure_ascii=False,indent=2))
  if not a.keep_full_copies:shutil.rmtree(out/label)

 case('mapping_other_grade',lambda e,m,r,d:r['request']['material_mapping'].update(code='304'),'MAPPING_SCOPE')
 case('mapping_wrong_source_description',lambda e,m,r,d:r['request']['material_mapping'].update(source_description='304 stainless steel'),'MAPPING_SCOPE')
 case('remove_mapping_proof',lambda e,m,r,d:r['request'].pop('material_mapping'),'NAMING_SOURCE_RULE_MISMATCH')
 case('unconfirmed_mapping',lambda e,m,r,d:r['request']['material_mapping'].update(confirmed=False),'NAMING_SOURCE_RULE_MISMATCH')
 def conflicting(e,m,r,d):r['request']['material_code']='304';r['request']['material_mapping']['code']='304'
 case('synchronous_target_grade_change',conflicting,'MATERIAL_DIFFERS_SOURCE')
 case('changed_resolved_confirmation_source',lambda e,m,r,d:r['resolved']['material_identity'].update(confirmation_source='forged resolved-only reference'),'NAMING_SOURCE_RULE_MISMATCH')
 def downgrade(e,m,r,d):
  for x in [e,m,r]:x['publisher_release']='2.7.3-R10'
 case('coherent_publisher_downgrade',downgrade,'MATERIAL_MAPPING_REQUIRES_CURRENT_RELEASE')
 def remove(e,m,r,d):e.pop('final_message_plan');e.pop('message_dispatch_contract')
 case('erase_default_dispatch',remove,'DISPATCH_REQUIRED_PUBLISHED')
 if before!={str(x.relative_to(source)):sha(x) for x in source.rglob('*') if x.is_file()}:raise ValueError('ORIGINAL_CHANGED')
 result={'author_test_only':True,'full_CAD_recheck_for_negatives':False,'positive_actual_CAD_readback_separately_required':True,'source_unchanged_files':len(before),'production_release':False,'results':results};(out/'MATERIAL_MAPPING_NEGATIVES.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps({'cases':len(results),'all_rejected_by_expected_source_guard':True}))
if __name__=='__main__':main()
