"""Publication policy is independent of the retained source manufacturing version."""
import json,re
from pathlib import Path
from delivery_dispatch import CONTRACT as DISPATCH_CONTRACT,check_plan

CONTRACT='named-single-zip-v2'
RELEASE='2.8.1-R12'
LEGACY_READ_ONLY_RELEASES={'2.7.3-R10'}
ENGINEERING_WITH_DISPATCH={'2.7.2-R09','2.7.3-R10','2.8.0-R11','2.8.1-R12'}

def signals(root,envelope,manifest):
 root=Path(root);names=[root.name,Path(envelope.get('zip','')).name]
 names += [Path(a['path']).name for a in manifest.get('artifacts',[])]
 return bool(envelope.get('naming') or any(k in envelope or k in manifest for k in ['publication_contract','publisher_release']) or
             list(root.glob('*FILE_NAMING.json')) or any(n.startswith('未命名待确认_') or re.match(r'^[SX]-[^-]+-[0-9]+(?:\.[0-9]+)?-[0-9]{8}-[0-9]{4}-v[1-9][0-9]*_',n) for n in names))

def check(root,envelope,manifest,allow_unpublished=False,allow_legacy_publication=False):
 named=signals(root,envelope,manifest);dispatch=None
 required=named or manifest.get('delivery_contract') in ENGINEERING_WITH_DISPATCH
 if required:
  if envelope.get('message_dispatch_contract')!=DISPATCH_CONTRACT or 'final_message_plan' not in envelope:raise ValueError('DISPATCH_REQUIRED_PUBLISHED: source manufacturing version cannot waive the publication plan')
 if 'final_message_plan' in envelope:
  dispatch=check_plan(root,envelope['final_message_plan'],envelope,manifest=manifest)
  if dispatch['mode']!='DEFAULT_ONE_COMPLETE_ZIP':raise ValueError('DISPATCH_GENERATED_DEFAULT_MUST_BE_ONE_ZIP: keep explicit exceptions outside the envelope')
 if not named:
  if manifest.get('delivery_contract') in ENGINEERING_WITH_DISPATCH and not allow_unpublished:raise ValueError('NAMING_PUBLICATION_REQUIRED')
  return dispatch,{'mode':'UNPUBLISHED_ENGINEERING_STAGE' if required else 'LEGACY_UNPUBLISHED_READ_ONLY','publication_contract':None,'source_manufacturing_contract':manifest['delivery_contract']}
 naming=envelope.get('naming')
 if not isinstance(naming,dict) or 'record' not in naming:raise ValueError('PUBLICATION_NAMING_DESCRIPTOR_REQUIRED')
 path=(Path(root)/naming['record']).resolve()
 if not path.is_relative_to(Path(root).resolve()) or not path.is_file():raise ValueError('NAMING_RECORD_ABSENT')
 record=json.loads(path.read_text())
 markers=[obj.get(key) for obj in [envelope,manifest,record] for key in ['publication_contract','publisher_release']]
 if allow_legacy_publication and not any(x is not None for x in markers):
  return dispatch,{'mode':'LEGACY_NAMED_INPUT_REQUIRES_REPUBLICATION','publication_contract':None,'source_manufacturing_contract':manifest['delivery_contract']}
 release=envelope.get('publisher_release')
 if release not in (LEGACY_READ_ONLY_RELEASES|{RELEASE}) or markers!=[CONTRACT,release]*3:raise ValueError('PUBLICATION_CONTRACT_BINDING: envelope, inventoried manifest and naming record must bind one supported publication release')
 req=record.get('request',{});material_extension=any(k in req for k in ['material_code','material_mapping']) or 'material_identity' in record.get('resolved',{})
 if material_extension and release!=RELEASE:raise ValueError('PUBLICATION_MATERIAL_MAPPING_REQUIRES_CURRENT_RELEASE')
 if record.get('source_manufacturing_contract')!=manifest['delivery_contract']:raise ValueError('PUBLICATION_SOURCE_MANUFACTURING_CONTRACT')
 return dispatch,{'mode':'CURRENT_NAMED_PUBLICATION','publication_contract':CONTRACT,'publisher_release':release,'source_manufacturing_contract':manifest['delivery_contract']}
