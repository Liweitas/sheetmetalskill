#!/usr/bin/env python3
"""Check a complete delivery and produce/check an attachment plan; never sends files."""
import argparse,json
from pathlib import Path
from delivery_contract import check_envelope
from delivery_dispatch import make_plan,check_plan

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('revision_root');p.add_argument('--plan',help='Validate an existing whole-message plan');p.add_argument('--output',help='New plan file outside immutable revision root');p.add_argument('--phase',choices=['final','confirmation'],default='final');p.add_argument('--file',action='append',dest='selected',help='Exact manifest-relative file path; explicit user request required');p.add_argument('--user-request',help='JSON containing actual current user quote, source and exact delivery/file scope');a=p.parse_args();root=Path(a.revision_root).resolve()
 if a.plan and (a.selected or a.user_request or a.phase!='final'):raise ValueError('DISPATCH_EXISTING_PLAN_NO_REINTERPRETATION')
 gate=check_envelope(root)
 if a.plan:plan=json.loads(Path(a.plan).read_text())
 else:plan=make_plan(root,phase=a.phase,selected=a.selected,user_request=json.loads(Path(a.user_request).read_text()) if a.user_request else None)
 checked=check_plan(root,plan)
 if a.output:
  dest=Path(a.output).resolve()
  if dest.is_relative_to(root):raise ValueError('DISPATCH_PLAN_MUST_NOT_MUTATE_FROZEN_REVISION')
  with dest.open('x') as f:f.write(json.dumps(plan,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'ok':True,'delivery_check':{'fresh_CAD_checks_executed':gate['fresh_CAD_checks_executed'],'current_workshop_requirements_complete':gate['current_workshop_requirements_complete'],'workshop_requirements_notice':'本版中文作业图及尺寸协议已核验，仍须人工全页复核与现场试折' if gate['current_workshop_requirements_complete'] else '旧版制造资料；本次仅规范命名与打包，不代表已满足最新中文紧凑作业图要求','production_release':False},'message_check':checked,'message_plan':plan},ensure_ascii=False,indent=2))
if __name__=='__main__':
 try:main()
 except Exception as ex:
  print(json.dumps({'ok':False,'error':str(ex),'production_release':False},ensure_ascii=False));raise SystemExit(2)
