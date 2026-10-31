#!/usr/bin/env python3
"""Compare an explicitly hypothesized03 profile to actual DXF; does not classify/redesign source."""
import argparse,json,math
from pathlib import Path
from corner03 import profile,expected_segments,same_segment
from cut_dxf import parse_dxf

def compare(path,t,Ri,skirt,corner_gap,K):
 ents=parse_dxf(Path(path));lines=[([float(e[10]),float(e[20])],[float(e[11]),float(e[21])]) for e in ents if e['type']=='LINE']
 if any(e['type']=='ARC' for e in ents):raise ValueError('03 diagnostic supports line-edged outer contour only')
 points=[p for line in lines for p in line]
 if not points or max(abs(min(p[k] for p in points)) for k in [0,1])>1e-5:raise ValueError('DXF outer must have actual min XY zero; do not move it merely to force03')
 s=profile(t,Ri,skirt,corner_gap,math.pi/2*(Ri+K*t));s['flat_size']=[max(p[k] for p in points) for k in [0,1]];actual=[(a,b) for a,b in lines if abs(a[0]-b[0])>1e-5 and abs(a[1]-b[1])>1e-5];expected=expected_segments(s);matched=[any(same_segment(a,b,u,v,1e-5) for u,v in actual) for a,b in expected]
 return {'profile_matches':len(actual)==8 and all(matched),'hypothesis_only':True,'source_design_changed':False,'actual_diagonals':actual,'expected_diagonals':expected,'matched_expected_of_8':sum(matched),'actual_diagonal_count':len(actual),'hypothesized_parameters':{'t':t,'Ri':Ri,'skirt':skirt,'corner_gap':corner_gap,'K':K},'CAD_executed':False,'production_release':False}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('dxf');p.add_argument('--t',type=float,required=True);p.add_argument('--Ri',type=float,required=True);p.add_argument('--skirt',type=float,required=True);p.add_argument('--corner-gap',type=float,required=True);p.add_argument('--K',type=float,required=True);p.add_argument('--output',required=True);a=p.parse_args();r=compare(a.dxf,a.t,a.Ri,a.skirt,a.corner_gap,a.K);out=Path(a.output)
 if out.exists() or out.resolve()==Path(a.dxf).resolve():p.error('Output must be new and different from source')
 out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2));raise SystemExit(0 if r['profile_matches'] else 2)
