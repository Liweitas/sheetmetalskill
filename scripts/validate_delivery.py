#!/usr/bin/env python3
"""Complete R07 delivery check, including inherited actual native CAD checks and ZIP coverage."""
import argparse,json
from delivery_contract import check_envelope
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('revision_root');a=p.parse_args()
 try:r=check_envelope(a.revision_root)
 except Exception as ex:r={'ok':False,'errors':[str(ex)],'digital_deliverables_complete':False,'production_release':False}
 print(json.dumps(r,ensure_ascii=False,indent=2));raise SystemExit(0 if r['ok'] else 2)
