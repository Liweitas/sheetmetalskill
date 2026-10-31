#!/usr/bin/env python3
"""Bounded negatives on copies of a real general-entry output; no model generation."""
import argparse,copy,json,shutil,sys
from pathlib import Path
from delivery_contract import check_envelope,sha
from general_process import validate_compiled_job
from general_sources import check as check_sources
from bend_dxf import read,write,compare,check_manifest
def main():
 p=argparse.ArgumentParser();p.add_argument('revision_root');p.add_argument('--output',required=True);a=p.parse_args();root=Path(a.revision_root).resolve();out=Path(a.output).resolve()
 if out.exists() or out.is_relative_to(root):raise ValueError('NEW_OUTSIDE_OUTPUT_REQUIRED')
 before={str(x.relative_to(root)):sha(x) for x in root.rglob('*') if x.is_file()};out.mkdir(parents=True);ep=next(root.glob('*DELIVERY_ENVELOPE*.json'));e=json.loads(ep.read_text());m=json.loads((root/e['manifest']).read_text());job=json.loads((root/next(a['path'] for a in m['artifacts'] if a['kind']=='source_job')).read_text());results=[]
 def run(name,fn,accepted=False):
  try:fn();actual=True;error=None
  except Exception as ex:actual=False;error=str(ex)
  results.append({'test':name,'accepted':actual,'expected':accepted,'error':error})
  if actual!=accepted:raise ValueError('UNEXPECTED_NEGATIVE_RESULT: '+name+' '+str(error))
 run('normal_current_general_transport_sources',lambda:check_envelope(root,check_cad=False),True)
 def envchange(name,change):
  d=out/name/Path(*root.parts[-3:]);shutil.copytree(root,d);env=json.loads((d/ep.name).read_text());change(env);(d/ep.name).write_text(json.dumps(env));return check_envelope(d,check_cad=False)
 run('delete_default_message_plan',lambda:envchange('delete_plan',lambda v:(v.pop('final_message_plan'),v.pop('message_dispatch_contract'))))
 run('false_manufacturing_grade',lambda:envchange('false_grade',lambda v:v.update(manufacturing_delivery_complete=True,general_design_stage='factory_signed_production_record')))
 run('false_envelope_quantity',lambda:envchange('false_sets',lambda v:v.update(sets=999)))
 for kind in ['general_source_brief','general_parameter_sources','general_parameter_csv']:
  bad=copy.deepcopy(m);bad['artifacts']=[a for a in bad['artifacts'] if a['kind']!=kind];run('omit_'+kind,lambda bad=bad:check_sources(root,bad,job))
 for field in ['geometry','grade','source']:
  bad=copy.deepcopy(job)
  if field=='geometry':bad['dimensions']['length']+=10
  if field=='grade':bad['general_process']['effective_stage']='factory_signed_production_record'
  if field=='source':bad['general_process']['parameter_sources'][0]['origin']='user-fabricated'
  run('synchronous_compiled_'+field+'_drift',lambda bad=bad:validate_compiled_job(bad))
 first=next(a for a in m['artifacts'] if a['kind']=='bend_dxf');segments=read(root/first['path']);bp=out/'double_scale_BEND.dxf';write(bp,[[[v*2 for v in point] for point in line] for line in segments]);run('double_scale_BEND',lambda:compare(bp,segments))
 report=json.loads((root/next(a['path'] for a in m['artifacts'] if a['kind']=='cad_report')).read_text());native={'checks':[{'part_id':name,'native_bends':[{'segments':p['bend_lines']}]} for name,p in report['parts'].items() if p['actual_bends']]};bad=copy.deepcopy(m);bad['artifacts']=[a for a in bad['artifacts'] if a is not None and not(a['kind']=='bend_dxf' and a['part_ids']==first['part_ids'])];run('missing_real_part_BEND',lambda:check_manifest(root,bad,native))
 if before!={str(x.relative_to(root)):sha(x) for x in root.rglob('*') if x.is_file()}:raise ValueError('ORIGINAL_CHANGED')
 result={'author_selftest_only':True,'new_CAD_generated':False,'full_CAD_acceptance':False,'production_release':False,'original_unchanged_files':len(before),'results':results};(out/'GENERAL_INTEGRITY_RESULTS.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps({'tests':len(results),'all_expected':True}))
if __name__=='__main__':main()
