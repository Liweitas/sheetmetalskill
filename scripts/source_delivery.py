"""Existing STEP audit envelope: explicit unsupported manufacturing slots, never fake a complete box package."""
import json,hashlib,zipfile
from pathlib import Path
from delivery_contract import VERSION,sha
def finalize_source(root,d):
 root=Path(root);report=json.loads((root/'cad/source_audit.json').read_text());result=json.loads((root/'AUDIT_RESULT.json').read_text());ver=d['revision']
 parts=[{'part_id':p['id'],'role':p['role'],'quantity':1,'material':report['config'].get('material'),'material_source':report['config'].get('material_source'),'measured_t_mm':p.get('measured_planar_t_mm'),'thickness_scope':p['thickness_scope'],'native_unfold_status':p['unfold']['status']} for p in report['parts']]
 reasons=['SOURCE_AUDIT_ADAPTER_NOT_COMPLETE_MANUFACTURING_DELIVERY','Actual source may have invalid topology, unknown compensation, unsupported splits/features; do not substitute new-box generator','Manufacturing stock/quantity/sequence/datum/tooling not yet confirmed; source audit PDF is not the new-box full process contract']
 state={'contract':VERSION,'version':ver,'namespace':d['namespace'],'entity_id':d['entity_id'],'revision':d['revision'],'status':'SOURCE_AUDIT_ONLY_PARTIAL_HOLD','digital_deliverables_complete':False,'manufacturing_delivery_complete':False,'production_release':False,'source_sha256':report['source_sha256'],'audit_status':result['status'],'required_output_slots':{
 'original_STEP':{'status':'PRESENT','path':next(root.glob('source_original.*')).name},'confirmation':{'status':'AUDIT_ONLY','paths':result.get('confirmation_images',json.loads((root/'source_manifest.json').read_text())['confirmation_images'])},'formed_parts_assembly_exploded':{'status':'AUDIT_ONLY','reason':'Actual exported source solids/rigid assembly; no structural change or manufacturing split approval inferred'},'per_part_true_unfold_DXF':{'status':'PARTIAL_OR_AUDIT_ONLY','parts':{p['id']:p['unfold']['status'] for p in report['parts']}},'central_stock_nest_DXF':{'status':'BLOCKED_UNSUPPORTED','reason':'Not all source parts necessarily have manufacturing flats/confirmed material/K/stock; no guessed nest'},'stock_preview_PDF':{'status':'BLOCKED_UNSUPPORTED','reason':'No accepted source manufacturing nesting set'},'full_workshop_bending_PDF':{'status':'AUDIT_ONLY','path':result['pdf'],'reason':'All source pieces shown, but manufacturing datum/sequence/tool access and complete drawing contract unsupported'},'BOM_parameters_acceptance':{'status':'AUDIT_ONLY','path':f'SOURCE_BOM_{ver}.json'},'hashes_and_ZIP':{'status':'AUDIT_ONLY','reason':'Transport completeness only, not manufacturing completeness'}},'holds':reasons+result.get('holds',[])}
 (root/f'SOURCE_BOM_{ver}.json').write_text(json.dumps(parts,ensure_ascii=False,indent=2));sp=root/f'SOURCE_DELIVERY_STATUS_{ver}.json';sp.write_text(json.dumps(state,ensure_ascii=False,indent=2))
 inventory=root/f'SOURCE_FILE_SHA256_{ver}.json';inventory.write_text(json.dumps({'files':[{'path':str(p.relative_to(root)),'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(root.rglob('*')) if p.is_file()]},indent=2))
 zp=root/f'{d["namespace"]}_{d["entity_id"]}_SOURCE_AUDIT_HOLD_{ver}.zip';prefix='/'.join(root.parts[-3:])
 with zipfile.ZipFile(zp,'x',zipfile.ZIP_DEFLATED) as z:
  for p in sorted(root.rglob('*')):
   if p.is_file() and p!=zp:z.write(p,prefix+'/'+str(p.relative_to(root)))
 with zipfile.ZipFile(zp) as z:
  if z.testzip():raise ValueError('SOURCE_AUDIT_ZIP_CRC')
  for p in root.rglob('*'):
   if p.is_file() and p!=zp:
    if hashlib.sha256(z.read(prefix+'/'+str(p.relative_to(root)))).hexdigest()!=sha(p):raise ValueError('SOURCE_AUDIT_ZIP_MEMBER_SHA')
 return {**state,'revision_root':str(root),'zip':zp.name,'zip_sha256':sha(zp),'CRC':'PASS','member_hashes':'PASS'}
