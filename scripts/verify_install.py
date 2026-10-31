#!/usr/bin/env python3
"""Check the complete extracted skill manifest; no mutation."""
import hashlib,json
from pathlib import Path
def verify(root):
 root=Path(root).resolve();m=json.loads((root/"PACKAGE-SHA256.json").read_text());errors=[]
 for name,digest in m["files"].items():
  p=(root/name).resolve()
  if not p.is_relative_to(root) or not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=digest:errors.append(name)
 actual={str(p.relative_to(root)) for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name not in ['PACKAGE-SHA256.json','.DS_Store']}
 errors.extend('unlisted:'+name for name in sorted(actual-set(m['files'])))
 return {"ok":not errors,"version":m["version"],"verified_files":len(m["files"]),"missing_or_modified":errors,"CAD_or_independent_agent_acceptance":False}
if __name__=="__main__":
 result=verify(Path(__file__).resolve().parents[1]);print(json.dumps(result,indent=2));raise SystemExit(0 if result["ok"] else 2)
