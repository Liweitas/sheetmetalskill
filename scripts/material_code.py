"""Explicit description-to-code naming evidence; never edits source material or infers a certificate."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def normalize(text):return ' '.join(text.split()).casefold()
def resolve(request,source):
 legacy=request.get('material');code=request.get('material_code',legacy);mapping=request.get('material_mapping')
 if legacy is not None and 'material_code' in request and legacy!=code:raise ValueError('NAMING_MATERIAL_CODE_CONFLICT')
 if code is None:return None,None,[]
 if mapping:
  if mapping.get('source_description',source)!=source or mapping.get('code',code)!=code:raise ValueError('NAMING_MATERIAL_MAPPING_SCOPE: bind exact source description and requested code')
 source_known=isinstance(source,str) and bool(source.strip()) and normalize(source) not in ['unknown','unknown steel','tbd','unspecified','未知','待定','待确认','未确认']
 explicit='material_code' in request or 'material_mapping' in request
 if source_known and source==code and not mapping:
  identity={'contract':'explicit-material-code-v1','source_description':source,'code':code,'method':'exact_source_code','source_description_sha256':hashlib.sha256(source.encode()).hexdigest(),'material_qualification_inferred':False}
  return code,identity if explicit else None,[]
 path=ROOT/'assets/process/material-code-aliases-v1.json';policy=json.loads(path.read_text());canonical=next((k for k,aliases in policy['aliases'].items() if isinstance(source,str) and normalize(source) in [normalize(a) for a in aliases]),None)
 if canonical and code!=canonical:raise ValueError('NAMING_MATERIAL_DIFFERS_SOURCE: source grade and requested code conflict')
 if not canonical and mapping and mapping.get('confirmed') is True:raise ValueError('NAMING_MATERIAL_UNRECOGNIZED_DESCRIPTION: clarify actual material; no guessed grade mapping')
 if not canonical and source_known and source in policy['aliases'] and code!=source:raise ValueError('NAMING_MATERIAL_DIFFERS_SOURCE')
 identity={'contract':policy['contract'],'source_description':source,'code':code,'method':'explicit_confirmed_alias','source_description_sha256':hashlib.sha256(source.encode()).hexdigest() if isinstance(source,str) else None,'alias_policy_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'mapping':mapping,'status':'PENDING_CONFIRMATION','material_qualification_inferred':False}
 if not canonical:return code,identity,['source_material_confirmation']
 if not mapping or mapping.get('source_description')!=source or mapping.get('code')!=code or mapping.get('confirmed') is not True or not isinstance(mapping.get('source'),str) or not mapping['source'].strip():return code,identity,['material_mapping']
 identity.update(status='CONFIRMED_NAMING_MAPPING',confirmation_source=mapping['source'],confirmation_authenticity='Submitted user/factory confirmation reference; software does not authenticate the source or certify the material')
 return code,identity,[]
