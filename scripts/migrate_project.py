#!/usr/bin/env python3
"""Create a new schema revision without mutating the source or applying defaults to existing orders."""
import json,copy,argparse
from pathlib import Path
from create_intake import build,apply_lid_defaults
def migrate(doc,new_project=False):
 fresh=build()[1]
 def merge(base,old):
  if isinstance(base,dict) and isinstance(old,dict):
   for k in base:
    if k in old:base[k]=merge(base[k],old[k])
   return base
  return copy.deepcopy(old)
 old=copy.deepcopy(doc);old.pop('schema_version',None);old.pop('policies',None);fresh=merge(fresh,old);fresh['schema_version']='2.4.1'
 for source in build()[1]['provenance']:
  if not any(x['id']==source['id'] for x in fresh['provenance']):fresh['provenance'].append(copy.deepcopy(source))
 fresh['project']['record_kind'].update(value='new' if new_project else 'existing',status='confirmed',source=['policy-timezone'],note='Explicit new-project resolution' if new_project else 'Migration preserves existing values; new defaults not silently applied')
 return apply_lid_defaults(fresh)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('input');p.add_argument('--output',required=True);p.add_argument('--new-project',action='store_true');a=p.parse_args()
 from safe_io import guard_outputs
 try:guard_outputs([a.input],[a.output])
 except ValueError as ex:p.error(str(ex))
 Path(a.output).write_text(json.dumps(migrate(json.loads(Path(a.input).read_text()),a.new_project),ensure_ascii=False,indent=2)+'\n')
