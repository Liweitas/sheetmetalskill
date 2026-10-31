"""Preserve input requirement/assumption status. Job numbers are not confirmation evidence."""
def apply_input_sources(project,job,resolved):
 mapping={
  'material':project['requirements']['material'],'thickness':project['requirements']['nominal_t'],
  'Ri':project['bending']['Ri'],'K_ANSI':project['bending']['K_value'],
  'method':project['fabrication']['method'],
  'seam_gap':project['fabrication']['seam_gap'],'end_inset':project['fabrication']['end_inset'],
  **{'dimensions.'+name:project['requirements']['dimensions'][axis] for name,axis in [('length','X'),('width','Y'),('height','Z')]},
  **{'lid.'+name:project['lid'][target] for name,target in [('g','gap'),('skirt_height','skirt_height'),('corner_gap','corner_gap'),('roof_gap','roof_gap'),('corner_scheme','corner_scheme')]}
 }
 explicit={key.strip('/').replace('/','.'):meta for key,meta in job.get('input_provenance',{}).items()}
 unknown=set(explicit)-set(mapping)
 if unknown:raise ValueError('Unsupported input_provenance fields: '+','.join(sorted(unknown)))
 candidates={'K_ANSI' if a['field']=='K_ANSI' else 'lid.corner_gap' for a in resolved.get('candidate_resolutions',[])}
 for key in ['K_ANSI','seam_gap','lid.corner_gap']:
  field=mapping[key]
  if field.get('value') is None or key in candidates:continue
  if key not in explicit:explicit[key]={'status':'assumed','source_kind':'engineering_assumption','source':'Unqualified job numerical input; trial assumption until explicitly sourced','note':'No customer confirmation or material/machine calibration inferred'}
 for key,meta in explicit.items():
  field=mapping[key]
  if field.get('value') is None:raise ValueError('Cannot assign evidence status to unresolved/not-applicable field: '+key)
  status=meta['status'];kind=meta.get('source_kind','engineering_assumption' if status=='assumed' else 'factory_measurement' if status=='measured' else 'user')
  if key in candidates and status!='assumed':raise ValueError('Auto-resolved trial candidates must remain assumed, never promoted to confirmed/measured')
  if kind=='engineering_assumption' and status!='assumed':raise ValueError('Engineering assumptions require assumed status: '+key)
  if status=='assumed' and kind!='engineering_assumption':raise ValueError('Assumed values require engineering_assumption source kind')
  if status=='measured' and kind!='factory_measurement':raise ValueError('Input measured values need actual factory measurement reference')
  if status=='confirmed' and kind not in ['user','factory_measurement','manufacturer_drawing']:raise ValueError('Confirmation source invalid')
  ident='input-'+key.replace('.','-')
  project['provenance'].append({'id':ident,'kind':kind,'ref':meta['source'],'message_at':None,'recorded_at':None})
  field.update(status=status,source=[ident],note=meta.get('note') or ('Explicit input '+status+'; factory release not inferred'))
 if job.get('general_process'):
  meta=job['general_process'];ident='general-current-calculation'
  project['provenance'].append({'id':ident,'kind':'engineering_assumption','ref':'Current brief compilation and same-version parameter source table; computed layout is not customer confirmation','message_at':None,'recorded_at':None})
  def calculated(field,note):field.update(status='assumed',source=[ident],note=note)
  if job.get('handles'):
   for k in ['quantity','position_and_orientation']:calculated(project['handles'][k],'Current-size computed mounting layout; actual handle body and load remain unverified')
  for group in project['hole_groups']:
   if group['id'].startswith('G-PORT'):
    calculated(group['laser_size']['magnitude'],'Reference roof round hole from current brief; not a qualified connector interface')
    for position in group['positions']:calculated(position['center'],'Current-size computed assembled position; reference opening, not customer-confirmed hardware')
 return project
