"""Public new-box job parser and canonical project adapter; no CAD and no file mutation."""
import json, math, hashlib, copy
from pathlib import Path
from decimal import Decimal
from jsonschema import Draft202012Validator
from select_structure import select_structure, SCALE
from create_intake import build, contract, blank, apply_project_defaults, DEFAULT_SOURCE
from common_profiles import fill_trial_candidates,mounting_features
from site_fit import ACCEPTANCE_SCHEMA,attach

JOB_SCHEMA={
 "$schema":"https://json-schema.org/draft/2020-12/schema","title":"Sheetmetal reproducible box job 2.4.1","type":"object","additionalProperties":False,
 "required":["id","dimensions","material","thickness","Ri","K_ANSI","seam_gap","lid_required"],
 "properties":{
  "id":{"type":"string","pattern":"^[A-Za-z0-9_-]+$"},"units":{"enum":["mm","cm","m","inch"]},
  "record_kind":{"enum":["new","existing"]},"rebuild_existing_authorized":{"type":"boolean"},
  "method":{"enum":["u_external_ends","u_wrap_bottom_l"]},
  "dimensions":{"type":"object","required":["length","width","height"],"additionalProperties":False,"properties":{k:{"type":"number","exclusiveMinimum":0} for k in ["length","width","height"]}},
  "material":{"type":"string","minLength":1},"thickness":{"type":"number","exclusiveMinimum":0},"Ri":{"type":"number","exclusiveMinimum":0},
  "K_ANSI":{"type":"number","minimum":0,"maximum":1},"seam_gap":{"type":"number","minimum":0},"lid_required":{"type":"boolean"},
  "lid":{"type":"object","additionalProperties":False,"required":["skirt_height","corner_gap","roof_gap"],"properties":{"g":{"type":"number","minimum":0},"corner_scheme":{"type":"string"},"skirt_height":{"type":"number","exclusiveMinimum":0},"corner_gap":{"type":"number","minimum":0},"roof_gap":{"type":"number","minimum":0}}},
  "holes":{"type":"array","items":{"type":"object","additionalProperties":False,"required":["id","part_id","diameter","point","axis"],"properties":{"id":{"type":"string","minLength":1},"part_id":{"enum":["U","L","END_L","END_R","LID"]},"diameter":{"type":"number","exclusiveMinimum":0},"point":{"type":"array","items":{"type":"number"},"minItems":3,"maxItems":3},"axis":{"type":"array","items":{"type":"number"},"minItems":3,"maxItems":3}}}}
 },
 "allOf":[{"if":{"properties":{"lid_required":{"const":True}}},"then":{"required":["lid"]}}]
}
JOB_SCHEMA['properties'].update({
 'general_process':{'type':'object'},
 'delivery':__import__('delivery_contract').SCHEMA,
 'site_fit_acceptance':ACCEPTANCE_SCHEMA,
 'workflow_profile':{'enum':['common_review_v1']},
 'input_provenance':{'type':'object','additionalProperties':{'type':'object','additionalProperties':False,'required':['status','source'],'properties':{'status':{'enum':['requested','confirmed','assumed','measured']},'source':{'type':'string','minLength':1},'source_kind':{'enum':['user','engineering_assumption','factory_measurement','manufacturer_drawing']},'note':{'type':'string'}}}},
 'end_inset':{'type':'number','minimum':0},'end_top_flush':{'type':'boolean'},
 'handles':{'type':'object','additionalProperties':False,'required':['profile','centers'],'properties':{'profile':{'enum':['handle-85-62-30-v1']},'centers':{'type':'array','minItems':1,'items':{'type':'array','items':{'type':'number'},'minItems':2,'maxItems':2}},'center_wide_towards':{'enum':['positive_x','negative_x']}}},
 'fixings':{'type':'object','additionalProperties':False,'required':['profile'],'properties':{'profile':{'enum':['perimeter-m4-trial-v1','perimeter-m4-experience-v2']},'edge_offset':{'type':'number','exclusiveMinimum':0},'max_spacing':{'type':'number','exclusiveMinimum':0},'distance_from_lid_top':{'type':'number','exclusiveMinimum':0}}}
})

# Raw trial jobs may explicitly leave only these two opted-in candidates null.
JOB_SCHEMA['properties']['K_ANSI']['type']=['number','null']
JOB_SCHEMA['properties']['lid']['properties']['corner_gap']['type']=['number','null']
JOB_SCHEMA['allOf'].append({'if':{'required':['workflow_profile'],'properties':{'workflow_profile':{'const':'common_review_v1'}}},'then':{},'else':{'properties':{'K_ANSI':{'type':'number'},'lid':{'properties':{'corner_gap':{'type':'number'}}}}}})

def job_schema(review_only=False):
 schema=copy.deepcopy(JOB_SCHEMA)
 if review_only:
  schema['title']='Formed review only; unknown material/K retained, no manufacturing output'
  schema['properties']['material']['type']=['string','null']
  schema['allOf']=schema['allOf'][:1]
 return schema

def resolve_job(job,review_only=False):
 original_job=job
 if 'general_process' in job:
  from general_process import validate_compiled_job
  validate_compiled_job(job)
 job,candidate_resolutions=fill_trial_candidates(job)
 errors=list(Draft202012Validator(job_schema(review_only)).iter_errors(job))
 if errors:raise ValueError("JOB_SCHEMA: "+"; ".join("/".join(map(str,e.absolute_path))+": "+e.message for e in errors))
 def finite(v):
  if isinstance(v,bool) or v is None or isinstance(v,str):return True
  if isinstance(v,(int,float)):return math.isfinite(v)
  if isinstance(v,dict):return all(finite(x) for x in v.values())
  if isinstance(v,list):return all(finite(x) for x in v)
  return False
 if not finite(job):raise ValueError("Job contains nonfinite numbers")
 unit=job.get("units","mm");scale=float(SCALE[unit])
 L,W,H=[job["dimensions"][k]*scale for k in ["length","width","height"]]
 t,ri,seam=[job[k]*scale for k in ["thickness","Ri","seam_gap"]]
 kind=job.get("record_kind","new");explicit=job.get("method")
 if kind=="existing" and (not explicit or job.get("rebuild_existing_authorized") is not True):raise ValueError("EXISTING_PROTECTED: explicit method and rebuild_existing_authorized=true required; source files are never edited")
 choice=select_structure(L,W,H,record_kind=kind,explicit_method=explicit,lid_required=job["lid_required"])
 method=choice["selected_method"]
 lid=job.get("lid",{});has=job["lid_required"]
 if kind=='existing' and has and ('g' not in lid or 'corner_scheme' not in lid):raise ValueError('EXISTING_PROTECTED: existing lid needs explicit g and corner_scheme; new-project defaults cannot migrate it')
 if not has and lid:raise ValueError("No-lid scope forbids active lid design values")
 if has and lid.get("corner_scheme","03")!="03":raise ValueError("UNSUPPORTED_CORNER_ADAPTER: explicit corner override retained; this CAD worker supports 03 only, provide a separate verified adapter")
 g=lid.get("g",.5/scale)*scale if has else 0;q=lid.get("roof_gap",0)*scale if has else 0;skirt=lid.get("skirt_height",0)*scale;cg=lid.get("corner_gap",0)*scale
 ro=ri+t;hb=H-t-q if has else H
 if min(L,W)<=4*ro+2*seam or hb<=ro:raise ValueError("DIMENSIONS_OUTSIDE_ADAPTER: inadequate flat lengths for declared radii/thickness")
 if not 0<=seam<ri:raise ValueError("seam_gap must be smaller than Ri for the cavity corner adapter")
 if has and (not 0<=cg<ri or skirt<=ro or skirt>=hb):raise ValueError("03 adapter requires corner_gap<Ri and Ri+t<skirt<body height")
 roles={"U":"u_body","END_L":"endplate","END_R":"endplate"} if method=="u_external_ends" else {"U":"u_body","L":"bottom_l"}
 if has:roles["LID"]="lid"
 holes=[]
 for h in job.get("holes",[]):
  if h["part_id"] not in roles:raise ValueError("Hole owner not in selected structure: "+h["part_id"])
  if abs(math.sqrt(sum(v*v for v in h["axis"]))-1)>1e-8:raise ValueError("Hole axis must be a unit normal")
  holes.append({**h,"point":[v*scale for v in h["point"]],"diameter":h["diameter"]*scale})
 if len({h["id"] for h in holes})!=len(holes):raise ValueError("Duplicate hole IDs")
 inset=job.get('end_inset',0)*scale
 if inset>=ro or (inset and method!='u_external_ends'):raise ValueError('end_inset applies to external ends and must be smaller than Ri+t')
 result=dict(id=job["id"],L=L,W=W,H=H,t=t,Ri=ri,g=g,q=q,skirt=skirt,corner_gap=cg,K_ANSI=job["K_ANSI"],seam_gap=seam,method=method,lid_required=has,holes=holes,roles=roles,selection=choice,record_kind=kind,end_inset=inset,end_top_flush=job.get('end_top_flush',False),candidate_resolutions=candidate_resolutions)
 extra,patterns,pairs,profiles=mounting_features(job,result,scale);result['holes']+=extra
 if len({h['id'] for h in result['holes']})!=len(result['holes']):raise ValueError('Explicit and profile-generated hole IDs overlap')
 result.update(mounting_patterns=patterns,fixing_pairs=pairs,profiles=profiles,delivery=__import__('delivery_contract').resolved_delivery(job))
 if job.get('general_process'):result['general_process']=copy.deepcopy(job['general_process'])
 attach(original_job,result)
 return result

def project_for(job,resolved,input_path,version,recorded_at):
 _,p=build(resolved["lid_required"]);p["input_mode"]="new_design"
 p["provenance"].extend([
  {"id":"job","kind":"user","ref":"Explicit design specification: "+Path(input_path).name,"message_at":None,"recorded_at":recorded_at},
  {"id":"cad","kind":"step_measurement","ref":"Generated STEP exports and native unfold; geometric measurement only, not factory material data","message_at":None,"recorded_at":recorded_at}])
 profile_ids={p['id'] for p in resolved.get('profiles',[])}|{a['source_profile'] for a in resolved.get('candidate_resolutions',[])}
 for profile_id in sorted(profile_ids):p['provenance'].append({'id':'profile-'+profile_id,'kind':'engineering_assumption','ref':'Explicitly selected bundled assets/profiles/'+profile_id+'.json; geometric trial reference, not supplier/factory qualification','message_at':None,'recorded_at':recorded_at})
 def put(container,key,v,status="requested",source="job",note="Declared job requirement; not a claim of customer confirmation"):
  container[key].update(value=v,status=status,source=[source],note=note)
 for k,v in {"customer_id":resolved['delivery']['entity_id'] if resolved['delivery']['namespace']=='customer' else 'UNASSIGNED_CUSTOMER',"project_id":resolved["id"],"revision":"v2.8.1-R12","version":version,"recorded_at":recorded_at,"record_kind":resolved["record_kind"],"quantity_sets":resolved['delivery']['sets']}.items():put(p["project"],k,v)
 data=Path(input_path).read_bytes()
 for k,v in {"reference":Path(input_path).name,"filename":Path(input_path).name,"sha256":hashlib.sha256(data).hexdigest(),"bytes":len(data),"preserve_original":True}.items():put(p["attachment"],k,v)
 req=p["requirements"]
 for k,v in {"nuts_required":False,"material":job["material"],"nominal_t":resolved["t"],"dimension_basis":"outer","height_basis":"including_lid" if resolved["lid_required"] else "bare_body","length_axis":"X","width_axis":"Y","height_axis":"Z","origin_and_datums":"Body nominal outer X0..L, Y0..W, Z0..body_h. Lid outer top=H. All hole points use assembled mm coordinates."}.items():put(req,k,v)
 for k,v in zip("XYZ",[resolved[x] for x in ["L","W","H"]]):put(req["dimensions"],k,v)
 if job.get("method") is not None or resolved["record_kind"]=="existing":put(p["fabrication"],"method",resolved["method"])
 p=apply_project_defaults(p)
 fab=p["fabrication"]
 for k,v in {"external_end_count":2 if resolved["method"]=="u_external_ends" else 0,"seam_gap":resolved["seam_gap"],"end_inset":resolved["end_inset"],"geometry_difference_ref":"New dimensional design; no historical/source CAD edited","weld_requirement":"HOLD: butt seams require shop process qualification"}.items():put(fab,k,v)
 put(fab,'end_top_flush',resolved['end_top_flush']);fab['fixing_pairs']=resolved.get('fixing_pairs',[])
 bends={"u_body":2,"endplate":0,"bottom_l":1,"lid":4}
 part_schema=contract()["properties"]["fabrication"]["properties"]["parts"]["items"]
 for name,role in resolved["roles"].items():
  part=blank(part_schema);part["id"]=name
  for k,v in {"role":role,"name":name,"bends":bends[role]}.items():put(part,k,v)
  fab["parts"].append(part)
 if resolved["lid_required"]:
  for k,v in {"style":"external","gap":resolved["g"],"gap_basis":"single_side","gap_datum":"Lid inner straight walls to body nominal outer straight walls","skirt_height":resolved["skirt"],"roof_gap":resolved["q"],"seating_datum":"roof inner face versus body top","whole_height":resolved["H"],"corner_scheme":"03","corner_gap":resolved["corner_gap"]}.items():put(p["lid"],k,v)
  if "g" not in job["lid"]:put(p["lid"],"gap",resolved["g"],"default",DEFAULT_SOURCE,"New-lid conditional default g0.5mm per side")
  if "corner_scheme" not in job["lid"]:put(p["lid"],"corner_scheme","03","default",DEFAULT_SOURCE,"New-lid conditional default03; actual geometry required")
 for k,v in {"Ri":resolved["Ri"],"compensation_mode":"K_factor","K_value":resolved["K_ANSI"],"K_definition":"ANSI","calibrated":False,"tool_clearance_verified":False}.items():put(p["bending"],k,v)
 for assumption in resolved.get('candidate_resolutions',[]):
  container,key=(p['bending'],'K_value') if assumption['field']=='K_ANSI' else (p['lid'],'corner_gap')
  put(container,key,assumption['value'],'assumed','profile-'+assumption['source_profile'],assumption['note'])
 put(p["handles"],"enabled",False,note="This run creates declared sheet parts and declared holes only; no undeclared handles/hardware")
 for h in resolved["holes"]:
  group=blank(contract()["properties"]["hole_groups"]["items"]);group["id"]=h["id"]
  for k,v in {"purpose":h.get("purpose","mounting"),"type":"tap_drill" if h.get("nominal_thread")=="M4" and h["part_id"]!="LID" else "clearance","count":1,"position_datum":"Assembly coordinates from explicit job"}.items():put(group,k,v)
  put(group["laser_size"],"magnitude",h["diameter"]);put(group["laser_size"],"representation","diameter")
  pos=blank(contract()["properties"]["hole_groups"]["items"]["properties"]["positions"]["items"]);pos.update(id=h["id"],part_id=h["part_id"]);put(pos,"center",h["point"]);put(pos,"axis",h["axis"]);group["positions"]=[pos]
  put(group["seat"],"enabled",False);p["hole_groups"].append(group)
  if h.get('candidate'):
   source='profile-'+h['source_profile']
   put(group['laser_size'],'magnitude',h['diameter'],'assumed',source,'Selected reference pilot/clearance; not shop or supplier tolerance')
   put(pos,'center',h['point'],'assumed',source,'Pattern-derived current assembly datum; actual exported axes must be read back');pos['center']['source'].append('job')
   if h.get('nominal_thread'):put(group,'thread',h['nominal_thread'],'assumed',source,'Nominal fixing intent; no thread geometry or strength certification')
 if resolved.get('mounting_patterns'):
  from create_intake import HANDLE_SOURCE
  h=p['handles'];src='profile-handle-85-62-30-v1'
  for k,v in {'enabled':True,'layout':'four_hole_trapezoid','quantity':len(resolved['mounting_patterns']),'holes_per_handle':4,'hardware_ref':'handle-mount-interface','position_and_orientation':json.dumps(resolved['mounting_patterns'])}.items():put(h,k,v)
  put(h,'wide_row_pitch',85.,'default',HANDLE_SOURCE,'Explicit common four-hole trapezoid mode: actual wide-row centers85.00mm')
  put(h,'narrow_row_pitch',62.,'assumed',src,'Selected common reference; physical handle drawing/fit not verified')
  put(h,'row_spacing',30.,'assumed',src,'Selected common reference; width axisY, spacing axisX, wide row toward box centerX')
  h['patterns']=[{k:pat[k] for k in ['id','part_id','wide_hole_ids','narrow_hole_ids']} for pat in resolved['mounting_patterns']]
  h['hole_group_ids']=[hole['id'] for hole in resolved['holes'] if hole.get('purpose')=='handle']
  hardware=blank(contract()['properties']['hardware']['items']);hardware['id']='handle-mount-interface';put(hardware,'role','handle');put(hardware,'drawing_ref','assets/profiles/handle-85-62-30-v1.json','assumed',src,'Mounting reference only; actual handle body/model drawing unknown');put(hardware,'physical_fit_verified',False);p['hardware'].append(hardware)
  p['notes']+=' Handle body not modeled; only explicitly selected mounting interface. Physical fit and supplier drawing remain HOLD.'
 if resolved.get('fixing_pairs'):p['notes']+=' CandidateM4 pilot3.3/lid4.5; thin-sheet thread strength, tap process and actual screw fit remain HOLD.'
 for k,v in {"formats":["dxf","pdf","step_parts","step_assembly","step_exploded","confirmation_png"],"units":"mm","acceptance_criteria":"Geometric review/trial only; tooling, material batch, springback and first article unresolved"}.items():put(p["delivery"],k,v)
 for k in ["digital_checks_passed","first_article_passed","production_release"]:put(p["review"],k,False)
 from input_sources import apply_input_sources
 if resolved.get('site_fit_acceptance'):
  from site_fit import EXCEPTION_ID
  a=resolved['site_fit_acceptance'];src=EXCEPTION_ID+'-user-source';p['provenance'].append({'id':src,'kind':'user','ref':a['authorization_source'],'message_at':None,'recorded_at':recorded_at});item=blank(contract()['properties']['exceptions']['items']);item.update(id=EXCEPTION_ID,authorization_source=src,scope=json.dumps(a,ensure_ascii=False,sort_keys=True),evidence_ref='actual native03/root measurement generated for this job')
  put(item,'retained',True,'confirmed',src,'User accepted retaining lid-root interference for site fitting, not geometric elimination or production release')
  p['exceptions'].append(item)
 if resolved['lid_required']:p['notes']+=' Fit disposition: '+json.dumps(resolved['fit'],ensure_ascii=False,sort_keys=True)
 return apply_project_defaults(apply_input_sources(p,job,resolved))
