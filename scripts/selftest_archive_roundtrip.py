#!/usr/bin/env python3
"""Fresh ZIP extraction and actual STEP/native bend/CUT/BEND/nest/PDF payload readback.
The external transport envelope is checked separately by validate_delivery at publication.
"""
import argparse,hashlib,json,zipfile
from pathlib import Path,PurePosixPath
from delivery_contract import sha,check_nest,resolved_delivery,expected_bom
def inspect(archive,out):
 archive=Path(archive).resolve();out=Path(out).resolve()
 if out.exists():raise ValueError('ROUNDTRIP_NEW_OUTPUT_REQUIRED')
 with zipfile.ZipFile(archive) as z:
  names=z.namelist();tops={PurePosixPath(n).parts[0] for n in names}
  if len(tops)!=1 or any(PurePosixPath(n).is_absolute() or '..' in PurePosixPath(n).parts for n in names):raise ValueError('ROUNDTRIP_SINGLE_SAFE_TOP_DIRECTORY')
  if z.testzip() is not None:raise ValueError('ROUNDTRIP_CRC')
  top=next(iter(tops));mf=[n for n in names if len(PurePosixPath(n).parts)==2 and '_manifest_' in n and n.endswith('.json')]
  if len(mf)!=1:raise ValueError('ROUNDTRIP_MANIFEST_REQUIRED')
  m=json.loads(z.read(mf[0]));one=lambda k:next(a for a in m['artifacts'] if a['kind']==k)
  spec=json.loads(z.read(top+'/'+one('delivery_spec')['path']));d=spec['delivery'];parent=out/(d['namespace']+'_'+d['entity_id'])/'revisions';parent.mkdir(parents=True);z.extractall(parent)
 root=parent/top
 for a in m['artifacts']:
  p=(root/a['path']).resolve()
  if not p.is_relative_to(root) or sha(p)!=a['sha256']:raise ValueError('ROUNDTRIP_ARTIFACT_SHA: '+a['path'])
 inventories=list(root.glob('*FILE_SHA256.json'))
 if len(inventories)!=1:raise ValueError('ROUNDTRIP_INVENTORY_REQUIRED')
 inv=json.loads(inventories[0].read_text());listed={x['path'] for x in inv['files']};actual={str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()}
 if actual!=listed|{inventories[0].name}:raise ValueError('ROUNDTRIP_INVENTORY_COVERAGE')
 for x in inv['files']:
  p=root/x['path']
  if sha(p)!=x['sha256'] or p.stat().st_size!=x['bytes']:raise ValueError('ROUNDTRIP_INVENTORY_HASH')
 job=json.loads((root/one('source_job')['path']).read_text());project=json.loads((root/one('parameters')['path']).read_text());report=json.loads((root/one('cad_report')['path']).read_text())
 from general_sources import check as sources
 source_check=sources(root,m,job)
 from factory_naming import resolve
 from publish_named_delivery import check_named
 record_path=next(root.glob('*FILE_NAMING.json'));record=json.loads(record_path.read_text());n=resolve(record['request'],job,d);naming={k:n[k] for k in ['status','code','prefix']};naming['record']=record_path.name
 naming_check=check_named(root,{'naming':naming,'zip':archive.name},m,d,job)
 expected=resolved_delivery(job);expected.update(revision=d['revision'],contract=m['delivery_contract'])
 if expected!=d or json.loads((root/one('bom_json')['path']).read_text())!=expected_bom(project,report,d):raise ValueError('ROUNDTRIP_INPUT_BOM_QUANTITY')
 from cut_dxf import parse_dxf
 from validate_manifest import closed_component_count,actual_native_directions
 from dxf_topology import validate_planar
 cut={}
 for a in m['artifacts']:
  if a['kind']=='dxf':
   ents=parse_dxf(root/a['path']);indices=a['outer_boundary_entity_indices'];closed=closed_component_count(ents,indices)
   if closed!=1:raise ValueError('ROUNDTRIP_CLOSED_SINGLE_PART_OUTLINE')
   cut[a['part_ids'][0]]={'entities':len(ents),'closed_outer_components':closed,'planar':validate_planar(ents,indices)}
 layout=json.loads((root/one('nest_layout')['path']).read_text());nest=check_nest(layout,{a['part_ids'][0]:root/a['path'] for a in m['artifacts'] if a['kind']=='dxf'},{a['sheet']:root/a['path'] for a in m['artifacts'] if a['kind']=='nest_dxf'})
 iso=json.loads((root/one('formed_isometric_report')['path']).read_text());native=actual_native_directions(project,m,root,iso)
 if native.get('ok') is not True or native.get('CAD_executed') is not True:raise ValueError('ROUNDTRIP_ACTUAL_NATIVE: '+str(native))
 from bend_dxf import check_manifest
 bend=check_manifest(root,m,native)
 from pdf_dimension_authority import actual_dimensions
 dimensions=actual_dimensions(project,m,root)
 from workshop_pdf import check_process_pdf
 from design_job import resolve_job
 process=check_process_pdf(root/one('pdf')['path'],project,report,d,m['version'],spec['process_pdf'],resolved_authority=resolve_job(job))
 return {'ok':True,'scope':'Fresh ZIP payload actual geometry/process readback; external transport-envelope check is separate at publication','archive_sha256':sha(archive),'ZIP_single_top':top,'CRC_and_inventory_all_file_hashes':True,'source_parameters':source_check,'naming':naming_check,'CUT':cut,'native_bend_counts':{x['part_id']:len(x['native_bends']) for x in native['checks']},'BEND':bend,'nest':nest,'actual_STEP_dimensions_and_translation_identity':dimensions,'source_derived_process_PDF':process,'extracted_revision_root':str(root),'production_release':False,'independent_agent_acceptance':False}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('zip');p.add_argument('--output',required=True);a=p.parse_args()
 try:r=inspect(a.zip,a.output)
 except Exception as ex:r={'ok':False,'error':str(ex),'production_release':False}
 target=Path(a.output);target.mkdir(parents=True,exist_ok=True);(target/'ROUNDTRIP_RESULT.json').write_text(json.dumps(r,ensure_ascii=False,indent=2));print(json.dumps(r,ensure_ascii=False,indent=2));raise SystemExit(0 if r['ok'] else 2)
