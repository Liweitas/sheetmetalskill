#!/usr/bin/env python3
"""Author CAD self-test; never an independent agent acceptance."""
import argparse,json,sys,subprocess,hashlib,copy
from pathlib import Path
from validate_manifest import check
from corner03 import check_dxf,spec
ROOT=Path(__file__).resolve().parents[1]
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--output",required=True);ap.add_argument("--cad-python",required=True);ap.add_argument("--freecad-lib");ap.add_argument("--sheetmetal-path",required=True);ap.add_argument("--pdf-renderer");a=ap.parse_args();out=Path(a.output).resolve()
 if out.exists():ap.error("selftest output must not exist")
 out.mkdir(parents=True);cases=[];negative=[]
 for name,example in [("external","box-external.job.json"),("wrap_l","box-wrap-l.job.json"),("body_only","box-wrap-l.job.json")]:
  job=json.loads((ROOT/"assets/examples"/example).read_text());L,W,H=[job["dimensions"][k] for k in ["length","width","height"]];hb=H-job["thickness"]
  job["id"]="SELFTEST_"+name.upper()
  if name=="external":
   job["holes"]=[{"id":"HU","part_id":"U","diameter":4,"point":[L/2,0,hb/2],"axis":[0,-1,0]},{"id":"HE1","part_id":"END_L","diameter":4,"point":[0,W/2,hb/2],"axis":[-1,0,0]},{"id":"HE2","part_id":"END_R","diameter":4,"point":[L,W/2,hb/2],"axis":[1,0,0]},{"id":"HC","part_id":"LID","diameter":4,"point":[L/2,W/2,H],"axis":[0,0,1]}]
  else:
   job["holes"]=[{"id":"HU","part_id":"U","diameter":4,"point":[0,W/2,hb/2],"axis":[-1,0,0]},{"id":"HL","part_id":"L","diameter":4,"point":[L/2,0,hb/2],"axis":[0,-1,0]}]
   if name!="body_only":job["holes"].append({"id":"HC","part_id":"LID","diameter":4,"point":[L/2,W/2,H],"axis":[0,0,1]})
   else:job["lid_required"]=False;job.pop("lid")
  if name!='body_only':
   from record_site_fit import record
   job,_=record(job,'SYNTHETIC SELFTEST authorization for '+job['id']+' only; not a real customer','For this synthetic test retain lid-root interference for site fitting and trial assembly; no geometric change or completed trial is claimed.')
  source=out/(name+".job.json");source.write_text(json.dumps(job,indent=2));dest=out/name
  cmd=[sys.executable,str(ROOT/"scripts/build_package.py"),str(source),"--output",str(dest),"--cad-python",a.cad_python,"--sheetmetal-path",a.sheetmetal_path]
  if a.freecad_lib:cmd+=["--freecad-lib",a.freecad_lib]
  if a.pdf_renderer:cmd+=["--pdf-renderer",a.pdf_renderer]
  with (out/(name+".log")).open("wb") as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=1200)
  if r.returncode:raise RuntimeError("Author CAD case failed: "+name+"; see "+str(out/(name+".log")))
  from factory_naming import published_root
  dest=published_root(dest)
  result=json.loads(next(dest.glob("*RUN_RESULT_*.json")).read_text());project=json.loads((dest/result["project"]).read_text());manifest=json.loads((dest/result["manifest"]).read_text())
  if not check(project,manifest,dest)["ok"]:raise RuntimeError("Completed run failed its own complete artifact gate")
  expected=4 if name=="external" else 2 if name=="body_only" else 3
  if len(result["sheet_parts"])!=expected or result["production_release"] or result["pdf_pages"]!=result["pdf_rendered_pages"]:raise RuntimeError("Sheet count/release/render selftest failed")
  if name=="body_only" and ("LID" in result["sheet_parts"] or result["native03_executed"]):raise RuntimeError("No-lid scope expanded")
  if name!="body_only" and (result["native03"]["native_sloped_edges"]!=8 or result["native03"]["actual_roof_q_mm"]!=0 or result["native03"]["root_overlap_volume_mm3"]<=0):raise RuntimeError("03/q0/interference preservation failed")
  if name=='body_only':
   actual=json.loads(next((dest/'evidence').glob('*cad_report_*.json')).read_text())['parts']['U']['bbox']
   if abs(actual[5]-actual[2]-job['dimensions']['height'])>1e-5:raise RuntimeError('No-lid bare height changed')
  cases.append({"name":name,"directory":str(dest),"sheets":result["sheet_parts"],"pages":result["pdf_pages"],"native03":result["native03"],"production_release":False})
  def rejected(label,m):
   actual=check(project,m,dest)
   if actual["ok"]:raise RuntimeError("Negative selftest unexpectedly passed: "+label)
   negative.append({"case":name,"test":label,"rejected":True,"errors":actual["errors"]})
  bad=copy.deepcopy(manifest);bad["artifacts"]=[x for x in bad["artifacts"] if not(x.get("kind")=="dxf" and "U" in x.get("part_ids",[]))];rejected("missing planned U DXF",bad)
  bad=copy.deepcopy(manifest);bad["artifacts"].append(copy.deepcopy(next(x for x in bad["artifacts"] if x["kind"]=="dxf")));rejected("duplicate manufacturing DXF",bad)
  bad=copy.deepcopy(manifest);bad['artifacts']=[x for x in bad['artifacts'] if x.get('kind')!='pdf'];rejected('missing required PDF',bad)
  bad=copy.deepcopy(manifest);first=next(x for x in bad['artifacts'] if x.get('kind')=='step_part');bad['artifacts'].remove(first);rejected('missing required formed STEP part',bad)
  bad=copy.deepcopy(manifest);bad['artifacts']=[x for x in bad['artifacts'] if x.get('kind')!='unfold_step'];rejected('missing required native unfold STEP',bad)
  bad=copy.deepcopy(manifest);next(x for x in bad['artifacts'] if x.get('kind')=='dxf').pop('part_geometry_report');rejected('missing actual per-part native evidence',bad)
  if name!="body_only":
   bad=copy.deepcopy(manifest);next(x for x in bad["artifacts"] if x.get("kind")=="dxf" and x.get("part_ids")==["LID"]).pop("native_geometry_report");rejected("missing mandatory native03 report",bad)
   bad=copy.deepcopy(manifest);next(x for x in bad['artifacts'] if x.get('kind')=='dxf' and x.get('part_ids')==['LID']).pop('body_step');rejected('03 without actual body binding',bad)
   bad=copy.deepcopy(manifest);next(x for x in bad['artifacts'] if x.get('kind')=='dxf' and x.get('part_ids')==['LID'])['pdf_flat_map'][4]+=5;rejected('PDF vectors shifted away from actual DXF',bad)
   points=[(0,0),(2,0),(4,0),(6,0),(8,0),(10,0),(10,2),(10,4),(10,6),(10,8),(10,10),(8,10),(6,10),(4,10),(2,10),(0,10),(0,8),(0,6),(0,4),(0,2)]
   pairs=[(0,"SECTION"),(2,"HEADER"),(9,"$INSUNITS"),(70,4),(0,"ENDSEC"),(0,"SECTION"),(2,"ENTITIES")]
   for p,q in zip(points,points[1:]+points[:1]):pairs.extend([(0,"LINE"),(8,"CUT"),(10,p[0]),(20,p[1]),(11,q[0]),(21,q[1])])
   pairs.extend([(0,"ENDSEC"),(0,"EOF")]);wrong=out/(name+"_claimed03_bad.dxf");wrong.write_text("\n".join(str(v) for pair in pairs for v in pair)+"\n")
   try:check_dxf(wrong,spec(project))
   except ValueError as ex:negative.append({"case":name,"test":"claimed03 with20 axis edges and0 slopes","rejected":True,"error":str(ex)})
   else:raise RuntimeError("Wrong lid geometry passed03")
 print(json.dumps({"author_selftest_only":True,"cases":cases,"negative_tests":negative,"production_release":False},indent=2))
 (out/"AUTHOR_CAD_SELFTEST.json").write_text(json.dumps({"author_selftest_only":True,"cases":cases,"negative_tests":negative,"production_release":False},indent=2))
if __name__=="__main__":main()
