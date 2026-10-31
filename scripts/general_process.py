"""Four layers: generic constraints, conditional experience, current calculations, user/evidence override."""
import copy,hashlib,json,math
from pathlib import Path
from select_structure import select_structure

CONTRACT='general-process-v1'
ROOT=Path(__file__).resolve().parents[1]
SCALE={'mm':1.,'cm':10.,'m':1000.,'inch':25.4}
def digest(x):return hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def defaults():return json.loads((ROOT/'assets/process/experience-defaults-v2.json').read_text())
def positive(v,name,zero=False):
 if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or (v<0 if zero else v<=0):raise ValueError('GENERAL_PARAMETER: '+name)
 return float(v)

def compile_brief(brief,embed=True):
 from jsonschema import Draft202012Validator
 schema=json.loads((ROOT/'references/general-brief.schema.json').read_text());errors=list(Draft202012Validator(schema).iter_errors(brief))
 if errors:raise ValueError('GENERAL_BRIEF_SCHEMA: '+'; '.join('/'.join(map(str,e.absolute_path))+': '+e.message for e in errors))
 b=copy.deepcopy(brief);policy=defaults();rows=[];pending=[];decisions=[]
 def decision(issue,detail,advice):
  return {'contract':CONTRACT,'status':'NEEDS_PROCESS_DECISION','job':None,'missing':[detail],'pending':[issue],'parameter_sources':rows,'adjustment_candidates':[{'issue':issue,'detail':detail,'default_skirt_mm':policy['skirt_default_mm'],'suggestion':advice,'automatic_geometry_change':False,'needs_confirmation':True}],'production_release':False}
 def add(path,value,unit,origin,source,note='',critical=False):
  rows.append({'parameter':path,'value':value,'unit':unit,'origin':origin,'source':source,'note':note,'needs_confirmation':origin in ['experience_default','pending'] or critical});return value
 required=['units','dimension_basis','height_basis','lid_required','thickness','dimensions']
 missing=[k for k in required if k not in b or b[k] is None]
 if isinstance(b.get('dimensions'),dict):missing += ['dimensions.'+k for k in ['length','width','height'] if k not in b['dimensions']]
 for k in missing:add(k,None,None,'pending','current user input required','No implicit unit/size/thickness or size datum',True)
 if missing:return {'contract':CONTRACT,'status':'NEEDS_ESSENTIAL_INPUT','missing':missing,'parameter_sources':rows,'job':None,'production_release':False}
 if b.get('shape','rectangular_box')!='rectangular_box':return {'contract':CONTRACT,'status':'UNSUPPORTED_SHAPE_REQUIRES_ADAPTER','missing':['dimensioned shape drawing or actual STEP + manufacturing split approval'],'parameter_sources':rows,'job':None,'production_release':False}
 unit=b['units'];scale=SCALE[unit];t=positive(b['thickness'],'thickness')*scale;dims=b['dimensions'];raw=[positive(dims[k],'dimensions.'+k)*scale for k in ['length','width','height']]
 for k,v in zip(['length','width','height'],raw):add('input.dimensions.'+k,v,'mm','user','current brief','Basis='+b['dimension_basis']+'/'+b['height_basis'])
 add('units',unit,None,'user','current brief');add('material',b.get('material'),None,'user' if b.get('material') else 'pending','current brief','Actual batch certificate remains separate',not bool(b.get('material')));add('thickness',t,'mm','user','current brief')
 p=b.get('process',{});lid=b.get('lid',{});has=b['lid_required'];L,W=raw[:2]
 if b['dimension_basis']=='inner':L+=2*t;W+=2*t
 ri=add('Ri',positive(p.get('Ri',policy['Ri_mm']/scale),'Ri')*scale,'mm','user' if 'Ri' in p else 'experience_default','current brief' if 'Ri' in p else policy['id'],'Actual tool/material capability must be checked')
 g=add('lid.g',positive(lid.get('g',policy['g_each_side_mm']/scale),'g',True)*scale if has else 0.,'mm','user' if 'g' in lid else 'experience_default','current brief' if 'g' in lid else policy['id'],'Single side, inner straight lid wall to nominal body outer wall')
 seam=add('seam_gap',positive(p.get('seam_gap',policy['butt_seam_candidate_mm']/scale),'seam_gap',True)*scale,'mm','user' if 'seam_gap' in p else 'experience_default','current brief' if 'seam_gap' in p else policy['id'],'Independent butt-seam candidate; never the external contour inset')
 qmin=ri-math.sqrt(max(0.,ri*ri-max(0.,ri-g)**2)) if has else 0.
 q=positive(lid['roof_gap'],'roof_gap',True)*scale if has and 'roof_gap' in lid else (math.ceil((qmin+max(.05,t*.05))*10)/10 if has else 0.)
 add('lid.roof_gap',q,'mm','user' if 'roof_gap' in lid else 'calculated','current brief' if 'roof_gap' in lid else 'necessary Ri/g envelope + explicit candidate margin rounded up to 0.1mm','Unset q only; closed total height retained and body height calculated. Actual geometry still required')
 if q+1e-10<qmin:
  pending.append('EXPLICIT_LID_ROOT_ENVELOPE_CONFLICT');decisions.append({'issue':'lid-root interference','current_q_mm':q,'ideal_tangency_q_mm':qmin,'candidate_q_mm':math.ceil((qmin+max(.05,t*.05))*10)/10,'automatic_geometry_change':False,'site_fit_authorized':False})
 H=raw[2]
 if b['height_basis']=='bare_body':
  hb=H+(t if b['dimension_basis']=='inner' else 0);H=hb+t+q if has else hb
 else:
  if not has:raise ValueError('GENERAL_HEIGHT_BASIS: including_lid requires a lid')
  H+=2*t if b['dimension_basis']=='inner' else 0.;hb=H-t-q
 for k,v in [('length',L),('width',W),('height',H),('body_height',hb)]:add('calculated.'+k,v,'mm','calculated','current datum conversion','Outer body X/Y, outer closed top Z; bare body preserved when requested')
 choice=select_structure(L,W,H,explicit_method=b.get('structure'),lid_required=has);method=choice['selected_method'];add('structure',method,None,'user' if b.get('structure') else 'calculated','current dimensions + max(L,W)>=H rule')
 ro=ri+t
 explicit_skirt=has and 'skirt_height' in lid
 skirt=positive(lid['skirt_height'],'skirt_height')*scale if explicit_skirt else policy['skirt_default_mm'] if has else 0.
 add('lid.skirt_height',skirt,'mm','user' if explicit_skirt else 'experience_default' if has else 'calculated','current brief' if explicit_skirt else policy['skirt_default_source'] if has else 'no lid scope','Explicit current input retained without quantization; no machine qualification inferred' if explicit_skirt else 'User default 15mm retained; no thickness/size/tool-driven increase. Conflicts require confirmation.' if has else 'No lid requested; skirt not applicable')
 if has and not explicit_skirt and (skirt<=ro or skirt>=hb):
  return decision('DEFAULT_SKIRT_GEOMETRY_CONFLICT',f'Default skirt15mm cannot satisfy Ri+t={ro} < skirt < body_height={hb}; default remains15, no model generated','Confirm a current explicit skirt or revise dimensions/radius/material/tool plan; no automatic increase')
 base_cg=positive(lid.get('corner_gap',policy['corner_gap_candidate_mm']/scale),'corner_gap',True)*scale if has else 0.
 cg=base_cg;candidate=p.get('corner_relief_candidate');relief_candidate=bool(candidate)
 if candidate:
  baseline=copy.deepcopy(b);baseline['process'].pop('corner_relief_candidate')
  baseline_hashes={digest(baseline)}
  if not baseline['process']:
   baseline.pop('process');baseline_hashes.add(digest(baseline))
  proposed=math.ceil(max(base_cg,t-2*ri)*100-1e-10)/100
  if candidate['baseline_brief_sha256'] not in baseline_hashes or candidate['baseline_corner_gap_mm']!=base_cg or candidate['value_mm']!=proposed or candidate['needs_confirmation'] is not True or not candidate['source'].strip():raise ValueError('CORNER_CANDIDATE_SCOPE: only a separately derived, bound unconfirmed proposal with an explicit source is supported')
  cg=candidate['value_mm']
  add('lid.corner_gap.original',base_cg,'mm','user' if 'corner_gap' in lid else 'experience_default','current brief' if 'corner_gap' in lid else policy['id'],'Original input/default retained in baseline; not overwritten')
  add('lid.corner_gap',cg,'mm','calculated',candidate['source'],'Separately derived unconfirmed geometry candidate; no minimum-gap proof or factory qualification; actual BRep/native03 mandatory',True)
  pending.append('CORNER_RELIEF_CANDIDATE_REQUIRES_CONFIRMATION')
  decisions.append({'issue':'separate corner relief candidate','baseline_candidate_mm':base_cg,'computed_candidate_mm':cg,'source':candidate['source'],'necessity_proven':False,'needs_confirmation':True,'skirt_kept_mm':skirt,'original_default_changed':False})
  if cg<=base_cg or cg>=ri:return decision('CORNER_RELIEF_CANDIDATE_OUTSIDE_ADAPTER',f'Skirt={skirt}mm retained; separate candidate={cg}mm must exceed baseline and be <Ri={ri}; no geometry generated','Confirm radius/corner/tooling; never silently change original parameters')
 if has and (cg>=ri or skirt<=ro or skirt>=hb):raise ValueError('GENERAL_ADAPTER_LIMIT: corner gap must be <Ri and Ri+t<skirt<body height; provide suitable current parameters')
 if has and lid.get('corner_scheme','03')!='03':raise ValueError('GENERAL_CORNER_ADAPTER_REQUIRED: explicit alternative retained; current generator supports 03 only')
 if not relief_candidate:add('lid.corner_gap',cg,'mm','user' if 'corner_gap' in lid else 'experience_default','current brief' if 'corner_gap' in lid else policy['id'],'03 is the corner scheme, not a 0.3mm gap')
 add('lid.corner_scheme','03' if has else None,None,'user' if 'corner_scheme' in lid else 'experience_default','current brief' if 'corner_scheme' in lid else '03 conditional rule for supported new external lid')
 inset=positive(p.get('end_inset',policy['external_end_contour_inset_mm']/scale if method=='u_external_ends' else 0.),'end_inset',True)*scale
 add('end_inset',inset,'mm','user' if 'end_inset' in p else 'experience_default','current brief' if 'end_inset' in p else policy['id'],'Outer end profile retreat and matched concentric radius; not axial seam')
 kval=p.get('K_ANSI',p.get('K_evidence',{}).get('K_ANSI',policy['K_ANSI_draft_candidate']));positive(kval,'K_ANSI',True)
 if kval>1:raise ValueError('GENERAL_K_RANGE')
 evidence=p.get('K_evidence');qualified=False
 if evidence:
  qualified=evidence['material']==b.get('material') and abs(evidence['thickness_mm']-t)<1e-8 and abs(evidence['K_ANSI']-kval)<1e-8 and abs(evidence['Ri_mm']-ri)<1e-8 and bool(evidence.get('reference'))
  if not qualified:raise ValueError('GENERAL_COMPENSATION_EVIDENCE_SCOPE: material/t/K mismatch')
 if not qualified:pending.append('K_AND_TOOLING_CALIBRATION_NOT_PROVIDED')
 add('K_ANSI',kval,None,'user' if 'K_ANSI' in p else 'experience_default',evidence.get('reference') if evidence else 'current brief' if 'K_ANSI' in p else policy['id'],'Declared scoped trial record, not independent physical certification' if qualified else 'Uncalibrated draft candidate, never factory confirmed',not qualified)
 if not b.get('material'):pending.append('MATERIAL_UNSPECIFIED')
 name=b.get('id') or 'REQ_'+digest(b)[:10].upper();job={'id':name,'units':'mm','dimensions':{'length':L,'width':W,'height':H},'material':b.get('material'),'thickness':t,'Ri':ri,'K_ANSI':kval,'seam_gap':seam,'lid_required':has,'method':method,'end_inset':inset,'end_top_flush':p.get('end_top_flush',False),'holes':[]}
 if has:job['lid']={'g':g,'skirt_height':skirt,'corner_gap':cg,'roof_gap':q,'corner_scheme':'03'}
 if b.get('delivery'):job['delivery']=copy.deepcopy(b['delivery'])
 # v2.8.2 (audit #3): roof ports default to NONE. Field lesson 2026-10-26: unrequested lid holes (2xO18 here, O12 cable holes
 # in a Codex package) were the top customer complaint. Holes are generated only when the brief explicitly asks for them.
 ports=b.get('roof_ports',{});mode=ports.get('mode','none')
 if mode!='none' and not has:raise ValueError('GENERAL_PORT_OWNER: no lid; specify explicit supported body holes instead')
 if mode=='two_reference':
  D=positive(ports.get('diameter',policy['roof_round_reference_diameter_mm']/scale),'roof port diameter')*scale;pitch=positive(ports.get('pitch',W/3/scale),'roof port pitch')*scale;x=positive(ports.get('from_body_short_end',max(2*D,ro+D/2+max(t,1))/scale),'roof port offset')*scale
  if pitch<D+2*max(t,1) or x+D/2>=L-ro or W/2-pitch/2-D/2<=ro:raise ValueError('GENERAL_PORT_LAYOUT_LIMIT: roof too small or conflicting diameter/pitch; explicitly choose no holes or provide a fitting interface')
  for i,y in enumerate([W/2-pitch/2,W/2+pitch/2],1):job['holes'].append({'id':'G-PORT'+str(i),'part_id':'LID','diameter':D,'point':[x,y,H],'axis':[0,0,1]})
  add('roof_ports',job['holes'].copy(),'mm','user' if 'roof_ports' in b else 'experience_default',policy['id'],'Two reference round holes; not automatically PG9/PG11 or a qualified hardware interface',not bool(ports.get('interface_reference')))
  if not ports.get('interface_reference'):pending.append('ROOF_PORT_INTERFACE_REFERENCE_UNCONFIRMED')
 elif mode!='none':raise ValueError('GENERAL_PORT_MODE_UNSUPPORTED')
 else:add('roof_ports',[],None,'user' if 'roof_ports' in b else 'calculated','current scope','Explicit no-hole override retained' if 'roof_ports' in b else 'Default v2.8.2: no roof holes unless explicitly requested')
 for hole in b.get('holes',[]):job['holes'].append({**hole,'point':[v*scale for v in hole['point']],'diameter':hole['diameter']*scale})
 handles=b.get('handles',{});hm=handles.get('mode','none')
 if hm!='none':
  if not has:raise ValueError('GENERAL_HANDLE_OWNER: lid required for current mounting adapter')
  n=1 if hm=='single' else 2 if hm=='double' else (2 if L>=340 else 1)
  centers=handles.get('centers');centers=[[v*scale for v in c] for c in centers] if centers else [[L*(i+1)/(n+1),W/2] for i in range(n)]
  if len(centers)!=n:raise ValueError('GENERAL_HANDLE_COUNT_CENTER_MISMATCH')
  if W<85+6.6+2*max(t,1):raise ValueError('GENERAL_HANDLE_ADAPTER_LIMIT: common 85mm pattern does not fit; need actual alternative hardware drawing')
  job['handles']={'profile':policy['handle_profile'],'centers':centers};add('handles.centers',centers,'mm','user' if handles.get('centers') else 'calculated','current dimensions + explicitly selected common mounting reference','Mounting holes only; physical moving envelope/load unknown');pending.append('HANDLE_BODY_ENVELOPE_AND_LOAD_UNVERIFIED')
 else:add('handles',0,None,'user' if 'handles' in b else 'experience_default','current scope','No unrequested handle body or mounting holes')
 fix=b.get('fixings',{});fm=fix.get('mode','perimeter_reference' if has else 'none')
 if fm!='none':
  if not has:raise ValueError('GENERAL_FIXING_OWNER')
  fp=json.loads((ROOT/'assets/profiles'/(policy['fixing_profile']+'.json')).read_text());lr=fp['lid_laser_diameter_mm']/2;br=fp['body_laser_diameter_mm']/2;down=skirt/2;minimum_down=max(ro+lr,t+q+br);maximum_down=skirt-lr
  if down<=minimum_down or down>=maximum_down:
   return decision('SKIRT_FIXING_STRAIGHT_WALL_CONFLICT',f'Skirt={skirt}mm retained; current midpoint fixing down={down}mm does not keep full circles on straight lid/body walls; geometric allowable down interval ({minimum_down}, {maximum_down})mm','Confirm alternate hole datum/profile or explicit skirt/tool plan; no automatic height increase or hole relocation')
  edge=positive(fix.get('edge_offset',min(40.,max(4*4.5,2*ro,min(L,W)*.15),min(L,W)/4)/scale),'fixing edge')*scale;spacing=positive(fix.get('max_spacing',policy['fixing_max_spacing_reference_mm']/scale),'fixing max pitch')*scale
  job['fixings']={'profile':policy['fixing_profile'],'edge_offset':edge,'max_spacing':spacing,'distance_from_lid_top':skirt/2};add('fixings',job['fixings'],None,'calculated' if not fix else 'user','current spans + max-spacing candidate','M4 pilot/clearance is a candidate; sheet thread strength and actual tap/screw remain HOLD')
 from common_profiles import mounting_features
 extra,patterns,pairs,_=mounting_features(job,{'L':L,'W':W,'H':H,'t':t,'Ri':ri,'g':g,'q':q,'skirt':skirt,'method':method,'lid_required':has},1.)
 if pairs:
  add('fixings.pair_count',len(pairs),'pairs','calculated','current spans / candidate maximum spacing','All four sides; actual paired axes must be read back')
  add('fixings.current_holes',extra,'mm','calculated',policy['fixing_profile'],'Current coordinates only, no customer-case coordinates copied')
 physical_sha=digest({'job':job,'additional_mounting_holes':extra,'experience_policy':policy})
 requested=p.get('requested_stage','confirmation');stage='evidence_based_trial' if requested=='trial' and qualified and not pending else 'confirmation_draft'
 factory_record=None
 if requested=='production_record':
  if not p.get('factory_verification'):
   pending.append('FACTORY_FIRST_ARTICLE_ASSEMBLY_AND_SIGNED_RELEASE_RECORD_REQUIRED');stage='confirmation_draft'
  elif not qualified or any(v in pending for v in ['EXPLICIT_LID_ROOT_ENVELOPE_CONFLICT','MATERIAL_UNSPECIFIED','ROOF_PORT_INTERFACE_REFERENCE_UNCONFIRMED','CORNER_RELIEF_CANDIDATE_REQUIRES_CONFIRMATION']):
   raise ValueError('FACTORY_RECORD_CANNOT_OVERRIDE_UNRESOLVED_INPUT_OR_CAD_FIT')
  else:
   from factory_verification import verify
   factory_record=verify(p['factory_verification'],physical_sha,job,L,W,H,hb,g);stage='factory_signed_production_record'
 add('physical_design_sha256',physical_sha,None,'calculated','resolved geometry + mounting holes + policy','Factory first-article records must bind this exact current design')
 if 'EXPLICIT_LID_ROOT_ENVELOPE_CONFLICT' in pending or not b.get('material'):route='formed_confirmation'
 else:route='full_candidate_geometry'
 for field in ['method','Ri','K_ANSI','seam_gap','end_inset','dimensions.length','dimensions.width','dimensions.height','lid.g','lid.skirt_height','lid.corner_gap','lid.roof_gap','lid.corner_scheme']:
  if field.startswith('lid.') and not has:continue
  key='structure' if field=='method' else 'calculated.'+field.split('.')[1] if field.startswith('dimensions.') else field;row=next((x for x in rows if x['parameter']==key),None)
  if row:job.setdefault('input_provenance',{})[field]={'status':'requested' if row['origin']=='user' else 'assumed','source_kind':'user' if row['origin']=='user' else 'engineering_assumption','source':str(row['source']),'note':row['origin']+': '+row['note']}
 result={'contract':CONTRACT,'status':'COMPILED_WITH_HOLD','job':job,'route':route,'effective_stage':stage,'requested_stage':requested,'pending':sorted(set(pending)),'adjustment_candidates':decisions,'parameter_sources':rows,'production_release':False,'policy_sha256':digest(policy),'physical_design_sha256':physical_sha,'factory_record':factory_record}
 if embed:job['general_process']={k:copy.deepcopy(result[k]) for k in ['contract','route','effective_stage','requested_stage','pending','adjustment_candidates','parameter_sources','policy_sha256','physical_design_sha256','factory_record']};job['general_process']['brief']=b
 return result

def validate_compiled_job(job):
 meta=job['general_process'];expected=compile_brief(meta['brief']);actual=copy.deepcopy(job);actual.pop('site_fit_acceptance',None)
 if actual!=expected['job']:raise ValueError('GENERAL_COMPILED_INPUT_AUTHORITY: compiled job/source/default/grade drift; recompile original brief instead of editing generated claims')
 return expected
