"""Check scoped factory-supplied records, never simulate first-article measurements or sign release."""
import hashlib,math,datetime

def verify(record,physical_sha,job,L,W,H,hb,g):
 if not isinstance(record,dict):raise ValueError('FACTORY_RECORD_REQUIRED')
 if record.get('physical_design_sha256')!=physical_sha:raise ValueError('FACTORY_RECORD_DESIGN_SCOPE')
 for key in ['first_article_passed','assembly_fit_passed','tool_access_and_sequence_verified','production_authorized_by_factory']:
  if record.get(key) is not True:raise ValueError('FACTORY_RECORD_EXPLICIT_PASS_REQUIRED: '+key)
 for key in ['signed_by','authorization_source','material_batch','machine_reference','upper_tool_reference','lower_tool_reference']:
  if not isinstance(record.get(key),str) or not record[key].strip():raise ValueError('FACTORY_RECORD_SOURCE_REQUIRED: '+key)
 try:datetime.date.fromisoformat(record['verified_date'])
 except Exception:raise ValueError('FACTORY_RECORD_DATE')
 if record.get('material')!=job['material']:raise ValueError('FACTORY_RECORD_MATERIAL_SCOPE')
 def near(actual,nominal,tolerance,name):
  if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in [actual,nominal,tolerance]) or tolerance<=0:raise ValueError('FACTORY_RECORD_MEASUREMENT_REQUIRED: '+name)
  if abs(actual-nominal)>tolerance:raise ValueError('FACTORY_RECORD_MEASUREMENT_OUT_OF_TOLERANCE: '+name)
 near(record.get('measured_thickness_mm'),job['thickness'],record.get('thickness_tolerance_mm'),'thickness')
 near(record.get('measured_Ri_mm'),job['Ri'],record.get('Ri_tolerance_mm'),'Ri')
 t=job['thickness'];has=job['lid_required'];nominal=[L+2*(g+t),W+2*(g+t),H] if has else [L,W,H]
 for key,expected in [('body_outer_mm',[L,W,hb]),('assembly_outer_mm',nominal)]:
  actual=record.get(key);tols=record.get(key+'_tolerance')
  if not isinstance(actual,list) or not isinstance(tols,list) or len(actual)!=3 or len(tols)!=3:raise ValueError('FACTORY_RECORD_THREE_DIMENSIONS_REQUIRED: '+key)
  for i in range(3):near(actual[i],expected[i],tols[i],key+'/'+str(i))
 docs=record.get('records',[])
 if len(docs)<2:raise ValueError('FACTORY_FIRST_ARTICLE_AND_ASSEMBLY_RECORDS_REQUIRED')
 for d in docs:
  if not d.get('reference') or not isinstance(d.get('content'),str) or not d['content'].strip() or hashlib.sha256(d['content'].encode()).hexdigest()!=d.get('sha256'):raise ValueError('FACTORY_RECORD_DOCUMENT_HASH')
 if job.get('handles') and record.get('hardware_physical_fit_verified') is not True:raise ValueError('FACTORY_HANDLE_PHYSICAL_FIT_RECORD_REQUIRED')
 return {'record_checks_passed':True,'factory_release_recorded':True,'physical_design_sha256':physical_sha,
         'authenticity':'Factory/operator-supplied signed records; software did not witness the physical measurements or authenticate the signer',
         'automatic_software_production_release':False}
