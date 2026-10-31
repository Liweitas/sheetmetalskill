#!/usr/bin/env python3
"""Bounded transport/message tests on copies of an existing delivery; no CAD generation."""
import argparse,copy,json,shutil,zipfile
from pathlib import Path
from delivery_contract import check_envelope,sha
from delivery_dispatch import make_plan,check_plan

def main():
 p=argparse.ArgumentParser();p.add_argument('revision_root');p.add_argument('--output',required=True);a=p.parse_args();source=Path(a.revision_root).resolve();out=Path(a.output).resolve()
 if out.exists() or out.is_relative_to(source):p.error('new output outside original revision required')
 before={str(x.relative_to(source)):sha(x) for x in source.rglob('*') if x.is_file()};out.mkdir(parents=True)
 ep=next(source.glob('*DELIVERY_ENVELOPE_*.json'));e=json.loads(ep.read_text());m=json.loads((source/e['manifest']).read_text())
 pdf=next(x['path'] for x in m['artifacts'] if x['kind']=='pdf');png=next(x['path'] for x in m['artifacts'] if x['kind']=='confirmation_png');results=[]
 def trial(name,fn,accepted):
  try:r=fn();ok=True;error=None
  except Exception as ex:r=None;ok=False;error=str(ex)
  if ok!=accepted:raise RuntimeError(name+' unexpected result: '+str(error))
  results.append({'test':name,'accepted':ok,'expected':accepted,'error':error,'result':r})
 def verify(root,plan=None):
  gate=check_envelope(root,check_cad=False)
  return {'transport':gate,'message':check_plan(root,plan or make_plan(root))}
 trial('normal_one_complete_ZIP',lambda:verify(source),True)
 def copy_root(name):
  dest=out/name/Path(*source.parts[-3:]);shutil.copytree(source,dest);return dest
 def missing():
  dest=copy_root('missing_process_PDF');(dest/pdf).unlink();return verify(dest)
 trial('missing_required_PDF',missing,False)
 def topology(mode):
  dest=copy_root(mode);envpath=next(dest.glob('*DELIVERY_ENVELOPE_*.json'));env=json.loads(envpath.read_text());zp=dest/env['zip']
  with zipfile.ZipFile(zp) as z:rows=[(n,z.read(n)) for n in z.namelist()]
  if mode=='multiple_top_directories':
   name,data=rows[0];parts=name.split('/');parts[0]='OTHER';rows[0]=('/'.join(parts),data)
  else:
   changed=[]
   for name,data in rows:
    parts=name.split('/');parts[0 if env.get('naming') else 2]='WRONG_REVISION';changed.append(('/'.join(parts),data))
   rows=changed
  with zipfile.ZipFile(zp,'w',zipfile.ZIP_DEFLATED) as z:
   for n,b in rows:z.writestr(n,b)
  env['zip_sha256']=sha(zp);env['revision_root']=str(dest)
  if 'final_message_plan' in env:
   env['final_message_plan']['archive_sha256']=env['zip_sha256'];env['final_message_plan']['messages'][0]['attachments'][0]['sha256']=env['zip_sha256']
  envpath.write_text(json.dumps(env,indent=2));return verify(dest)
 trial('multiple_top_directories',lambda:topology('multiple_top_directories'),False)
 trial('wrong_revision_inside_same_top',lambda:topology('wrong_revision_inside_same_top'),False)
 trial('default_ZIP_plus_individual_PDF',lambda:make_plan(source,selected=[e['zip'],pdf]),False)
 def scatter():
  plan=make_plan(source);single=make_plan(source,selected=[pdf],user_request=request([pdf]));plan['messages']+=single['messages'];return check_plan(source,plan)
 def request(paths,reason='explicit_single_files'):
  plan=make_plan(source);return {'reason':reason,'quote':'SYNTHETIC 本轮单件/先确认图请求','source':'AUTHOR_TEST_ONLY_NOT_CLIENT_AUTHORIZATION','current_for_this_delivery':True,'scope':{k:plan[k] for k in ['namespace','entity_id','revision','archive_sha256']},'requested_paths':paths}
 trial('default_split_message_scatter',scatter,False)
 trial('explicit_user_single_PDF',lambda:verify(source,make_plan(source,selected=[pdf],user_request=request([pdf]))),True)
 trial('confirmation_first_not_final',lambda:verify(source,make_plan(source,phase='confirmation',selected=[png],user_request=request([png],'confirmation_first'))),True)
 def stale():
  req=request([pdf]);req['current_for_this_delivery']=False;return make_plan(source,selected=[pdf],user_request=req)
 trial('old_not_current_exception',stale,False)
 if e.get('publication_contract') or e['contract'] in ['2.7.2-R09','2.7.3-R10']:
  def change_embedded(name,remove):
   dest=copy_root(name);envpath=next(dest.glob('*DELIVERY_ENVELOPE_*.json'));env=json.loads(envpath.read_text())
   if remove:env.pop('final_message_plan');env.pop('message_dispatch_contract')
   else:
    art=next(x for x in m['artifacts'] if x['path']==pdf);env['final_message_plan']['messages'][0]['attachments'].append({k:art[k] for k in ['path','kind','sha256']})
   envpath.write_text(json.dumps(env,indent=2));return verify(dest)
  trial('R09_deleted_default_plan',lambda:change_embedded('R09_deleted_default_plan',True),False)
  trial('R09_scattered_embedded_plan',lambda:change_embedded('R09_scattered_embedded_plan',False),False)
 assert before=={str(x.relative_to(source)):sha(x) for x in source.rglob('*') if x.is_file()}
 result={'status':'AUTHOR_BOUNDED_TRANSPORT_MESSAGE_TEST_PASS','fresh_CAD_executed':False,'new_CAD_generated':False,'production_release':False,'original_files_unchanged':len(before),'sender_behavior_guaranteed':False,'results':results}
 (out/'DISPATCH_TEST_RESULTS.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'status':result['status'],'cases':len(results),'source_unchanged':True},indent=2))
if __name__=='__main__':main()
