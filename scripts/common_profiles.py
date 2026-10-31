"""Reusable, explicitly selected mounting and trial profiles. All lengths returned in mm."""
import copy,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def profile(name):return json.loads((ROOT/"assets/profiles"/(name+".json")).read_text())
def fill_trial_candidates(job):
 d=copy.deepcopy(job);assumptions=[]
 if d.get("workflow_profile")=="common_review_v1":
  p=profile("trial-review-v1");scale={"mm":1,"cm":10,"m":1000,"inch":25.4}.get(d.get("units","mm"),1)
  if d.get("K_ANSI") is None:d["K_ANSI"]=p["K_ANSI"];assumptions.append({"field":"K_ANSI","value":p["K_ANSI"],"source_profile":p["id"],"status":"assumed","note":"Explicitly opted-in trial candidate, not calibrated"})
  if d.get("lid_required") is True and isinstance(d.get("lid"),dict) and d["lid"].get("corner_gap") is None:
   d["lid"]["corner_gap"]=p["corner_gap_mm"]/scale;assumptions.append({"field":"corner_gap","value":p["corner_gap_mm"],"source_profile":p["id"],"status":"assumed","note":"Explicitly opted-in trial corner clearance, verify tooling and seam"})
 return d,assumptions
def mounting_features(job,r,scale):
 holes=[];patterns=[];pairs=[];sources=[]
 L,W,H,t,g,skirt=[r[k] for k in ["L","W","H","t","g","skirt"]]
 h=job.get("handles")
 if h:
  if not r["lid_required"]:raise ValueError("Handle mounting profile requires the explicitly requested lid")
  p=profile(h["profile"]);sources.append(p)
  if p["id"]!="handle-85-62-30-v1":raise ValueError("Unsupported handle profile")
  for i,center in enumerate(h["centers"],1):
   cx,cy=[v*scale for v in center];direction=1 if cx<L/2 else -1
   if abs(cx-L/2)<1e-9:
    direction=1 if h.get("center_wide_towards","positive_x")=="positive_x" else -1
   wide_x=cx+direction*p["row_spacing_mm"]/2;narrow_x=cx-direction*p["row_spacing_mm"]/2
   pat={"id":"H"+str(i),"part_id":"LID","center_mm":[cx,cy],"wide_towards":"positive_x" if direction>0 else "negative_x","wide_hole_ids":[],"narrow_hole_ids":[]}
   for row,x,pitch,ids in [("W",wide_x,p["wide_pitch_mm"],pat["wide_hole_ids"]),("N",narrow_x,p["narrow_pitch_mm"],pat["narrow_hole_ids"])]:
    for k,sign in enumerate([-1,1],1):
     hid=pat["id"]+"-"+row+str(k);ids.append(hid);point=[x,cy+sign*pitch/2,H]
     if not 0<point[0]<L or not 0<point[1]<W:raise ValueError("Handle mounting holes lie outside nominal roof")
     holes.append({"id":hid,"part_id":"LID","point":point,"axis":[0,0,1],"diameter":p["laser_diameter_mm"],"purpose":"handle","nominal_thread":"M6","source_profile":p["id"],"candidate":True})
   patterns.append(pat)
 f=job.get("fixings")
 if f:
  if not r["lid_required"]:raise ValueError("Perimeter lid/body fixing profile cannot add an unrequested lid")
  p=profile(f["profile"]);sources.append(p)
  edge=f.get("edge_offset",p["edge_offset_mm"]/scale)*scale;max_pitch=f.get("max_spacing",p["max_spacing_mm"]/scale)*scale
  down=f.get("distance_from_lid_top",skirt/2/scale)*scale;z=H-down
  if edge<=0 or max_pitch<=0 or min(L,W)<=2*edge:raise ValueError("Fixing profile needs positive margins and usable side spans; explicitly override for smaller boxes")
  if not H-skirt<z<H-r["Ri"]-t or not 0<z<H-t-r["q"]:raise ValueError("Fixing center is outside straight lid/body overlap; do not cut in bend roots")
  def positions(length):
   intervals=max(1,math.ceil((length-2*edge)/max_pitch));return [edge+(length-2*edge)*i/intervals for i in range(intervals+1)]
  for side,length in [("front",L),("back",L),("left",W),("right",W)]:
   for i,coord in enumerate(positions(length),1):
    pid="F-"+side+"-"+str(i)
    if side in ["front","back"]:
     point=[coord,0 if side=="front" else W,z];axis=[0,-1 if side=="front" else 1,0]
     owner="L" if side=="front" and r["method"]=="u_wrap_bottom_l" else "U"
     lidpoint=[coord,-g-t if side=="front" else W+g+t,z]
    else:
     point=[0 if side=="left" else L,coord,z];axis=[-1 if side=="left" else 1,0,0]
     owner=("END_L" if side=="left" else "END_R") if r["method"]=="u_external_ends" else "U"
     lidpoint=[-g-t if side=="left" else L+g+t,coord,z]
    bh={"id":pid+"-B","part_id":owner,"point":point,"axis":axis,"diameter":p["body_laser_diameter_mm"],"purpose":"lid_body_fixing","nominal_thread":"M4","source_profile":p["id"],"candidate":True,"fixing_pair":pid}
    ch={"id":pid+"-C","part_id":"LID","point":lidpoint,"axis":axis,"diameter":p["lid_laser_diameter_mm"],"purpose":"lid_body_fixing","nominal_thread":"M4 clearance","source_profile":p["id"],"candidate":True,"fixing_pair":pid}
    holes.extend([bh,ch]);pairs.append({"id":pid,"body_hole_id":bh["id"],"lid_hole_id":ch["id"],"side":side})
 return holes,patterns,pairs,sources
