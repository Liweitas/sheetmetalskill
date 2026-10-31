#!/usr/bin/env python3
"""Derive a separate unconfirmed relief proposal; never modify baseline/default or certify feasibility."""
import argparse,copy,json,math
from pathlib import Path
from general_process import compile_brief,digest
def derive(brief,source):
 base=copy.deepcopy(brief);compiled=compile_brief(base)
 if not compiled.get('job') or not compiled['job']['lid_required']:raise ValueError('SUPPORTED_BASELINE_LID_REQUIRED')
 if base.get('process',{}).get('corner_relief_candidate'):raise ValueError('ALREADY_A_CANDIDATE')
 if not isinstance(source,str) or not source.strip():raise ValueError('CANDIDATE_EVIDENCE_SOURCE_REQUIRED')
 j=compiled['job'];value=math.ceil(max(j['lid']['corner_gap'],j['thickness']-2*j['Ri'])*100-1e-10)/100
 child=copy.deepcopy(base);child.setdefault('process',{})['corner_relief_candidate']={'baseline_brief_sha256':digest(base),'baseline_corner_gap_mm':j['lid']['corner_gap'],'value_mm':value,'source':source,'needs_confirmation':True};compile_brief(child);return child
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('brief');p.add_argument('--output',required=True);p.add_argument('--source',required=True);a=p.parse_args();target=Path(a.output)
 if target.exists():raise ValueError('NO_OVERWRITE')
 target.write_text(json.dumps(derive(json.loads(Path(a.brief).read_text()),a.source),ensure_ascii=False,indent=2));print(str(target))
