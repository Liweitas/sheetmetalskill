"""Validate a declared attachment plan; never sends messages or grants authorization."""
import hashlib,json
from pathlib import Path

CONTRACT='single-zip-dispatch-v1'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def context(root,envelope=None,delivery=None,manifest=None):
 root=Path(root).resolve()
 if envelope is None:
  eps=list(root.glob('*DELIVERY_ENVELOPE_*.json'))
  if len(eps)!=1:raise ValueError('DISPATCH_ENVELOPE_REQUIRED')
  envelope=json.loads(eps[0].read_text())
 manifest=manifest or json.loads((root/envelope['manifest']).read_text())
 if delivery is None:
  specs=[a for a in manifest['artifacts'] if a['kind']=='delivery_spec']
  if len(specs)!=1:raise ValueError('DISPATCH_SOURCE_IDENTITY_REQUIRED')
  delivery=json.loads((root/specs[0]['path']).read_text())['delivery']
 identity={k:delivery[k] for k in ['namespace','entity_id','revision']}
 catalog={a['path']:{'path':a['path'],'kind':a['kind'],'sha256':a['sha256']} for a in manifest['artifacts']}
 catalog[envelope['zip']]={'path':envelope['zip'],'kind':'complete_delivery_zip','sha256':envelope['zip_sha256']}
 return root,envelope,identity,catalog

def make_plan(root,envelope=None,delivery=None,manifest=None,phase='final',selected=None,user_request=None):
 root,envelope,identity,catalog=context(root,envelope,delivery,manifest)
 paths=[envelope['zip']] if selected is None else list(selected)
 for p in paths:
  if p not in catalog:raise ValueError('DISPATCH_UNLISTED_ATTACHMENT: '+str(p))
 plan={'dispatch_contract':CONTRACT,**identity,'archive_sha256':envelope['zip_sha256'],'phase':phase,
       'messages':[{'attachments':[catalog[p].copy() for p in paths]}],
       'user_request':user_request,'production_release':False}
 check_plan(root,plan,envelope,delivery,manifest)
 return plan

def check_plan(root,plan,envelope=None,delivery=None,manifest=None):
 root,envelope,identity,catalog=context(root,envelope,delivery,manifest)
 if not isinstance(plan,dict) or set(plan)!={'dispatch_contract','namespace','entity_id','revision','archive_sha256','phase','messages','user_request','production_release'}:raise ValueError('DISPATCH_PLAN_FIELDS: include all declared messages, no alternate attachment fields')
 if plan.get('dispatch_contract')!=CONTRACT or plan.get('production_release') is not False:raise ValueError('DISPATCH_FALSE_CONTRACT_OR_RELEASE')
 if any(plan.get(k)!=v for k,v in identity.items()) or plan.get('archive_sha256')!=envelope['zip_sha256']:raise ValueError('DISPATCH_WRONG_IDENTITY_REVISION_OR_ARCHIVE')
 if plan.get('phase') not in ['final','confirmation']:raise ValueError('DISPATCH_PHASE_REQUIRED')
 messages=plan.get('messages')
 if not isinstance(messages,list) or not messages:raise ValueError('DISPATCH_MESSAGES_REQUIRED')
 attachments=[]
 for message in messages:
  if not isinstance(message,dict) or set(message)!={'attachments'} or not isinstance(message['attachments'],list) or not message['attachments']:raise ValueError('DISPATCH_ATTACHMENT_LIST_REQUIRED')
  attachments.extend(message['attachments'])
 paths=[]
 for a in attachments:
  if not isinstance(a,dict) or a.get('path') not in catalog or a!=catalog[a['path']]:raise ValueError('DISPATCH_UNLISTED_OR_FALSE_ATTACHMENT')
  p=root/a['path']
  if not p.resolve().is_relative_to(root) or not p.is_file() or sha(p)!=a['sha256']:raise ValueError('DISPATCH_ATTACHMENT_BYTES: '+a['path'])
  paths.append(a['path'])
 if len(paths)!=len(set(paths)):raise ValueError('DISPATCH_DUPLICATE_ATTACHMENT')
 request=plan.get('user_request')
 default=plan['phase']=='final' and len(messages)==1 and paths==[envelope['zip']]
 if request is None:
  if not default:raise ValueError('DISPATCH_DEFAULT_ONE_COMPLETE_ZIP: individual files require a current explicit user request')
  mode='DEFAULT_ONE_COMPLETE_ZIP'
 else:
  expected_scope={**identity,'archive_sha256':envelope['zip_sha256']}
  if not isinstance(request,dict) or request.get('scope')!=expected_scope or request.get('requested_paths')!=paths or request.get('current_for_this_delivery') is not True:raise ValueError('DISPATCH_USER_REQUEST_SCOPE')
  if not all(isinstance(request.get(k),str) and request[k].strip() for k in ['quote','source']):raise ValueError('DISPATCH_USER_REQUEST_EVIDENCE')
  if plan['phase']=='confirmation':
   if request.get('reason')!='confirmation_first' or any(catalog[p]['kind'] not in ['confirmation_png','confirmation_pdf'] for p in paths):raise ValueError('DISPATCH_CONFIRMATION_ONLY')
   mode='USER_REQUESTED_CONFIRMATION_FIRST_NOT_FINAL_DELIVERY'
  else:
   if request.get('reason')!='explicit_single_files':raise ValueError('DISPATCH_USER_REQUEST_REASON')
   mode='USER_REQUESTED_INDIVIDUAL_FILES'
 return {'ok':True,'dispatch_contract':CONTRACT,'mode':mode,'message_count':len(messages),'attachment_count':len(paths),
         'final_message_plan_checked':plan['phase']=='final','production_release':False,
         'authorization_text_authenticity':'sender must verify actual current user history; JSON cannot prove consent',
         'actual_messages_sent_or_controlled':False,'scope':'declared messages only; no guarantee against sender bypass'}
