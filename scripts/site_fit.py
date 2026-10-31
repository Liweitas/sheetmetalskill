"""Project-scoped lid-root disposition. Never edits dimensions or certifies fit.

Authorization text is user-supplied evidence, not something software can authenticate.
The executing agent must verify it against the actual user instruction before adding it.
"""
import copy,hashlib,json,math

VOLUME_TOL_MM3=1e-7  # unchanged numeric intersection limit; not a manufacturing tolerance
EXCEPTION_ID='authorized-site-fit-lid-root'
ACCEPTANCE_SCHEMA={'type':'object','additionalProperties':False,'required':['scope','job_id','job_design_sha256','issue','disposition','authorization_source','authorization_quote','authorized_by','geometry_interference_eliminated','trial_assembly_confirmed'],'properties':{
 'scope':{'const':'this_job_only'},'job_id':{'type':'string','minLength':1},'job_design_sha256':{'type':'string','pattern':'^[0-9a-f]{64}$'},'issue':{'const':'lid_root_interference'},'disposition':{'const':'site_fit_and_trial_assembly'},'authorization_source':{'type':'string','minLength':1},'authorization_quote':{'type':'string','minLength':1},'authorized_by':{'const':'user'},'geometry_interference_eliminated':{'const':False},'trial_assembly_confirmed':{'const':False}}}

def design_sha256(job):
 d=copy.deepcopy(job);d.pop('site_fit_acceptance',None)
 return hashlib.sha256(json.dumps(d,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

def assess(ri,g,q,H,t):
 vals=(ri,g,q,H,t)
 if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in vals) or ri<=0 or g<0 or q<0 or t<=0 or H<=t+q:raise ValueError('FIT_INPUT: finite Ri>0,g/q>=0,t>0,H>t+q required')
 dx=max(0.,ri-g);bound=ri-math.sqrt(max(0.,ri*ri-dx*dx))
 return {'applicable':True,'Ri_mm':ri,'g_each_side_mm':g,'q_mm':q,'minimum_q_ideal_tangency_mm':bound,'analytic_feasible':q>=bound,'closed_height_mm':H,'body_height_mm':H-t-q,'body_height_relative_to_zero_q_mm':-q,'actual_geometry_verified':False,'geometry_interference_eliminated':False,'trial_assembly_confirmed':False,'production_release':False,'scope':'Necessary straight-edge envelope only; tangency is not manufacturing clearance; actual all-part CAD check required'}

def bound_parameters(r):
 keys=['id','L','W','H','t','Ri','g','q','skirt','corner_gap','method','K_ANSI','seam_gap','end_inset','end_top_flush']
 p={k:r[k] for k in keys}
 p['holes']=sorted([{'id':h['id'],'part_id':h['part_id'],'diameter':h['diameter'],'point':h['point'],'axis':h['axis']} for h in r['holes']],key=lambda h:h['id'])
 return p

def validate_acceptance(a):
 if not isinstance(a,dict) or set(a)!=set(ACCEPTANCE_SCHEMA['required']):raise ValueError('SITE_FIT_SCHEMA: complete scoped fields only')
 for key,spec in ACCEPTANCE_SCHEMA['properties'].items():
  v=a[key]
  if 'const' in spec and (type(v)!=type(spec['const']) or v!=spec['const']):raise ValueError('SITE_FIT_SCHEMA: invalid '+key)
  if spec.get('type')=='string' and (not isinstance(v,str) or not v.strip()):raise ValueError('SITE_FIT_SCHEMA: nonempty '+key+' required')
 import re
 if not re.fullmatch('[0-9a-f]{64}',a['job_design_sha256']):raise ValueError('SITE_FIT_SCHEMA: invalid design SHA256')
 if not a['authorization_source'].strip() or not a['authorization_quote'].strip():raise ValueError('SITE_FIT_SOURCE: actual user authorization reference and quote required')

def attach(job,resolved):
 raw=job.get('site_fit_acceptance')
 if not resolved['lid_required']:
  if raw is not None:raise ValueError('SITE_FIT_SCOPE: no-lid job cannot use a lid-root acceptance')
  resolved.update(fit={'applicable':False},site_fit_acceptance=None);return
 f=assess(*[resolved[k] for k in ['Ri','g','q','H','t']]);a=None
 if raw is not None:
  validate_acceptance(raw)
  if raw['job_id']!=job['id'] or raw['job_design_sha256']!=design_sha256(job):raise ValueError('SITE_FIT_SCOPE: job id or exact design SHA changed; obtain applicable user acceptance, never transfer an exception')
  a={**copy.deepcopy(raw),'bound_parameters_mm':bound_parameters(resolved)}
 f['disposition']='AUTHORIZED_SITE_FIT_TRIAL_REQUIRED' if a else 'ACTUAL_GEOMETRY_CHECK_REQUIRED' if f['analytic_feasible'] else 'USER_REVIEW_REQUIRED'
 f['authorization_source']=a['authorization_source'] if a else None
 meta=job.get('input_provenance',{}).get('lid.roof_gap',job.get('input_provenance',{}).get('/lid/roof_gap',{}));f['q_source_status']=meta.get('status','requested')
 resolved.update(fit=f,site_fit_acceptance=a)

def require_delivery_decision(r):
 if not r['lid_required']:return
 f=assess(*[r[k] for k in ['Ri','g','q','H','t']]);a=r.get('site_fit_acceptance')
 if a:
  validate_acceptance({k:v for k,v in a.items() if k!='bound_parameters_mm'})
  if a.get('bound_parameters_mm')!=bound_parameters(r):raise ValueError('SITE_FIT_SCOPE: resolved parameters changed')
 if not f['analytic_feasible'] and not a:raise ValueError('LID_ROOT_FIT_REVIEW_REQUIRED: known root envelope conflict; q minimum ideal tangency='+format(f['minimum_q_ideal_tangency_mm'],'.12g')+' mm (not a manufacturing recommendation). No dimensions changed. Obtain this-job user disposition for site fitting or a separately approved design change.')

def project_parameters(p):
 v=lambda f:f['value'];req=p['requirements'];lid=p['lid'];fab=p['fabrication'];bend=p['bending']
 r={'id':v(p['project']['project_id']),'L':v(req['dimensions'][v(req['length_axis'])]),'W':v(req['dimensions'][v(req['width_axis'])]),'H':v(lid['whole_height']),'t':v(req['nominal_t']),'Ri':v(bend['Ri']),'g':v(lid['gap']) if v(lid['gap_basis'])=='single_side' else v(lid['gap'])/2,'q':v(lid['roof_gap']),'skirt':v(lid['skirt_height']),'corner_gap':v(lid['corner_gap']),'method':v(fab['method']),'K_ANSI':v(bend['K_value']),'seam_gap':v(fab['seam_gap']),'end_inset':v(fab['end_inset']),'end_top_flush':v(fab['end_top_flush']),'holes':[]}
 if r['H']!=v(req['dimensions'][v(req['height_axis'])]):raise ValueError('SITE_FIT_SCOPE: closed height datum changed')
 for group in p['hole_groups']:
  size=group['laser_size'];D=v(size['magnitude'])*(2 if v(size['representation'])=='radius' else 1)
  for pos in group['positions']:r['holes'].append({'id':pos['id'],'part_id':pos['part_id'],'diameter':D,'point':v(pos['center']),'axis':v(pos['axis'])})
 return bound_parameters(r)

def acceptance_from_project(p):
 entries=[e for e in p['exceptions'] if e['id']==EXCEPTION_ID]
 if not entries:return None
 if len(entries)!=1:raise ValueError('SITE_FIT_SCOPE: duplicate acceptance')
 e=entries[0]
 try:a=json.loads(e['scope'])
 except (ValueError,TypeError) as ex:raise ValueError('SITE_FIT_SCOPE: invalid scoped record') from ex
 validate_acceptance({k:v for k,v in a.items() if k!='bound_parameters_mm'})
 sources=[s for s in p['provenance'] if s['id']==e['authorization_source']]
 if e['retained']['value'] is not True or len(sources)!=1 or sources[0]['kind']!='user' or sources[0]['ref']!=a['authorization_source']:raise ValueError('SITE_FIT_SCOPE: source/retention mismatch')
 if a['job_id']!=p['project']['project_id']['value'] or a.get('bound_parameters_mm')!=project_parameters(p):raise ValueError('SITE_FIT_SCOPE: acceptance belongs to different design parameters/holes')
 return a

def check_actual_overlap(volume,acceptance,intersection_z_min,root_z_min):
 if isinstance(volume,bool) or not isinstance(volume,(int,float)) or not math.isfinite(volume) or volume<0:raise ValueError('SITE_FIT_MEASUREMENT: finite nonnegative actual volume required')
 if volume<=VOLUME_TOL_MM3:return 'NO_POSITIVE_INTERFERENCE_DETECTED'
 if not acceptance:raise ValueError('LID_ROOT_FIT_REVIEW_REQUIRED: actual positive interference '+str(volume)+' mm3; no this-job site-fitting authorization')
 if intersection_z_min<root_z_min-1e-5:raise ValueError('SITE_FIT_SCOPE: intersection extends below lid bend-root zone; this exception cannot accept unrelated collision')
 return 'AUTHORIZED_SITE_FIT_TRIAL_REQUIRED'
