"""Actual projected STEP views and actual native flat geometry. No stock CAD silhouettes."""
from pathlib import Path
import io,json,math
def write_drawings(project,resolved,report,projections,path,lid_dxf=None,native_report=None):
 if project["project"]["revision"]["value"]=="v2.8.1-R12":
  from cn_workshop import write
  return write(project,resolved,report,projections,path,lid_dxf,native_report)
 from reportlab.pdfgen import canvas
 from reportlab.lib.pagesizes import A3,landscape
 from pypdf import PdfReader,PdfWriter
 from render_review_pdf import write_pdf
 first=Path(path).with_name("parameter-summary.tmp.pdf")
 mapping=write_pdf(project,first,lid_dxf,native_report,title="钣金工艺交接与三视折弯 / HOLD",workshop_resolved=resolved)
 pagew,pageh=landscape(A3);buf=io.BytesIO();cv=canvas.Canvas(buf,pagesize=(pagew,pageh))
 pages=[]
 def text(x,y,s,size=10):
  cv.setFont("Helvetica",size);cv.drawString(x,y,str(s))
 def title(s):
  text(35,pageh-35,s,18);text(35,pageh-55,"v2.8.1 R12 | "+resolved["id"]+" | "+project["project"]["version"]["value"]+" | mm | REVIEW / TRIAL ONLY | production_release=false",10)
 def finish(label):
  text(35,20,"Nominal geometric dimensions. Verify tools, springback and first article. "+label,9)
  cv.showPage();pages.append(label)
 def draw_lines(lines,rect,label):
  x,y,w,h=rect;pts=[p for line in lines for p in line]
  if not pts:raise ValueError("Empty actual STEP projection: "+label)
  xmin=min(p[0] for p in pts);xmax=max(p[0] for p in pts);ymin=min(p[1] for p in pts);ymax=max(p[1] for p in pts)
  scale=min((w-50)/max(xmax-xmin,1e-6),(h-55)/max(ymax-ymin,1e-6))
  ox=x+25-scale*xmin+(w-50-scale*(xmax-xmin))/2;oy=y+30-scale*ymin+(h-55-scale*(ymax-ymin))/2
  cv.setLineWidth(.45)
  for line in lines:
   p=cv.beginPath();p.moveTo(ox+scale*line[0][0],oy+scale*line[0][1])
   for q in line[1:]:p.lineTo(ox+scale*q[0],oy+scale*q[1])
   cv.drawPath(p)
  text(x+10,y+h-12,label+"  scale "+format(scale,".4g")+" pt/mm",10)
  left=ox+scale*xmin;right=ox+scale*xmax;bottom=oy+scale*ymin;top=oy+scale*ymax
  cv.setLineWidth(.35);cv.line(left,bottom-12,right,bottom-12)
  for xx in [left,right]:cv.line(xx,bottom-3,xx,bottom-16);cv.line(xx-2,bottom-14,xx+2,bottom-10)
  text((left+right)/2-20,bottom-24,format(xmax-xmin,'.6f')+' mm',9)
  cv.line(left-12,bottom,left-12,top)
  for yy in [bottom,top]:cv.line(left-3,yy,left-16,yy);cv.line(left-14,yy-2,left-10,yy+2)
  cv.saveState();cv.translate(left-18,(bottom+top)/2);cv.rotate(90);text(-20,0,format(ymax-ymin,'.6f')+' mm',9);cv.restoreState()
  return [scale,0,0,scale,ox,oy]
 def lines_page(name):
  title(name+" - ACTUAL EXPORTED STEP THREE VIEWS")
  views=projections[name];draw_lines(views["front"],(35,400,530,330),"FRONT");draw_lines(views["right"],(600,400,530,330),"RIGHT");draw_lines(views["top"],(35,65,530,315),"TOP")
 def rows(items,x=610,y=365):
  for item in items:
   text(x,y,item,10);y-=19
   if y<60:raise ValueError("Drawing note table overflow; use a separate drawing adapter")
 for name in ["ASSEMBLY","EXPLODED"]:
  lines_page(name)
  rows(["Method: "+resolved["method"],"Design body L/W and declared H (height basis above): "+str([resolved[k] for k in ["L","W","H"]]),"t="+str(resolved["t"])+"  Ri="+str(resolved["Ri"]),("g="+str(resolved["g"])+"  q="+str(resolved["q"]) if resolved["lid_required"] else "No lid: g and q not applicable"),"K ANSI="+str(resolved["K_ANSI"])+" (NOT SHOP CALIBRATED)","All body sheets separately unfolded and exported.",("Lid corner: 03; native fresh unfold mandatory." if resolved["lid_required"] else "No lid: corner and native03 not applicable."),("Body nominal height excludes roof t and q." if resolved["lid_required"] else "No lid: H is the bare-body nominal outer height."),("Authoritative BODY/LID common (mm3): "+__import__("interference_volume").display_volume(report["root_interference_measurement"]["authoritative_volume_mm3"]) if resolved["lid_required"] else "No lid: root/roof seating checks not applicable."),"Body top Z="+str(resolved["H"]-resolved["t"]-resolved["q"] if resolved["lid_required"] else resolved['H']),"HOLD: shop tooling, material batch, weld and trial.",("Fit: "+resolved['fit']['disposition'] if resolved["lid_required"] else "Weld and shop-tooling qualification remain HOLD.")])
  finish(name)
 flat_pages={};isometric_views={}
 for name,p in report["parts"].items():
  lines_page(name);bb=p["bbox"]
  rows(["Sheet: "+name,"Formed bbox X/Y/Z: "+str([round(bb[i+3]-bb[i],6) for i in range(3)]),"Actual bends: "+str(p["actual_bends"]),"Actual holes: "+str(p["actual_holes"]),"Native flat size: "+str([round(n,6) for n in p["flat_size_mm"]]),"t from native volume/area: "+format(p["unfold_t_mm"],".9f"),"Ri="+str(resolved["Ri"])+"  K ANSI="+str(resolved["K_ANSI"]),"Hole centers and axes: explicit assembly datums.","No physical springback/BG validation."])
  finish(name+" formed")
  if p['actual_bends']:
   from formed_isometric import iso_point
   title(name+' - ACTUAL FORMED ISOMETRIC / BEND DIRECTIONS')
   iso_map=draw_lines(projections[name]['isometric'],(35,145,720,560),'ISOMETRIC WIREFRAME - actual formed STEP')
   labels=p.get('bend_records',[])
   isometric_views[name]={'page_index':mapping['pages']+len(pages),'pdf_map':iso_map,'formed_sha256':p['formed_sha256'],'bend_labels':labels}
   cv.setStrokeColorRGB(.1,.25,.7)
   for b in labels:
    xx,yy=iso_point(b['source_formed_point_mm']);xx=iso_map[0]*xx+iso_map[4];yy=iso_map[3]*yy+iso_map[5]
    cv.circle(xx,yy,3,stroke=1,fill=0);cv.line(xx,yy,xx+16,yy+20);text(xx+18,yy+21,b['id']+' '+b['direction'],9)
   cv.setStrokeColorRGB(0,0,0)
   notes=['Actual exported STEP; no stock silhouette.','Wireframe shows all actual BRep edges.','Isometric extents are projected, not L/W/H.','Use three-view dimensions for fabrication.','B numbers also identify native flat lines.','Direction: SheetMetal native UP / DOWN','relative to selected root skin normal.','NOT machine bend order or tool approval.']
   for b in labels:notes.append(b['id']+' '+b['direction']+' signed '+format(b['angle_signed_deg'],'.6g')+' deg')
   if labels:notes+=['Root Face'+str(labels[0]['root_face']),'Root normal '+str([round(x,6) for x in labels[0]['root_skin_normal']])]
   rows(notes,790,700)
   text(50,105,'Actual formed part '+name+' | native bend identifiers / signed direction | fit and first article remain HOLD',10)
   finish(name+' formed isometric')
  actual_holes=[h for h in report['holes'] if h['part_id']==name]
  if actual_holes:
   hole_rows=['FORMED STEP: ID | D mm | actual surface centers (X,Y,Z) | axis']
   for h in actual_holes:
    fmt=lambda values:','.join(format(v,'.6f') for v in values)
    hole_rows.append(h['id']+' | '+format(h['diameter'],'.6f')+' | '+fmt(h['actual_surface_centers'][0])+' ; '+fmt(h['actual_surface_centers'][1])+' | '+fmt(h['axis']))
   hole_rows+=['NATIVE DXF: circle / entity index | actual D mm | actual flat X,Y mm','CUT numbering identifies actual DXF entities, not an assumed ID-to-flat assignment.']
   for idx,record in enumerate(p['records']):
    if record['type']=='CIRCLE':hole_rows.append('CUT entity '+str(idx)+' | '+format(2*record['radius'],'.6f')+' | '+','.join(format(v,'.6f') for v in record['center']))
   for start in range(0,len(hole_rows),25):
    title(name+' - ACTUAL FORMED / FLAT HOLE COORDINATES')
    rows(hole_rows[start:start+25],45,740)
    finish(name+' actual hole table')
  title(name+" - ACTUAL NATIVE UNFOLD / LASER CUT")
  fw,fh=p["flat_size_mm"];scale=min(690/max(fw,1e-9),580/max(fh,1e-9));ox=50;oy=130
  cv.setLineWidth(.6)
  for r in p["records"]:
   if r["type"]=="LINE":cv.line(ox+scale*r["p"][0],oy+scale*r["p"][1],ox+scale*r["q"][0],oy+scale*r["q"][1])
   elif r["type"]=="CIRCLE":cv.circle(ox+scale*r["center"][0],oy+scale*r["center"][1],scale*r["radius"],stroke=1,fill=0)
   else:
    x,y=r["center"];rad=r["radius"];cv.arc(ox+scale*(x-rad),oy+scale*(y-rad),ox+scale*(x+rad),oy+scale*(y+rad),startAng=r["start"],extent=(r["end"]-r["start"])%360)
  cv.setDash(4,3);cv.setStrokeColorRGB(.15,.3,.8)
  for line in p["bend_lines"]:cv.line(ox+scale*line[0][0],oy+scale*line[0][1],ox+scale*line[1][0],oy+scale*line[1][1])
  for b in p.get('bend_records',[]):
   center=[sum(pt[i] for pt in b['flat_line_mm'])/2 for i in [0,1]];text(ox+scale*center[0]+5,oy+scale*center[1]+5,b['id']+' '+b['direction'],9)
  cv.setDash();cv.setStrokeColorRGB(0,0,0)
  ba=math.pi/2*(resolved["Ri"]+resolved["K_ANSI"]*resolved["t"]);bd=2*(resolved["Ri"]+resolved["t"])-ba
  notes=["Flat extent (mm): "+format(fw,".9f")+" x "+format(fh,".9f"),("All folds 90 deg" if p['actual_bends'] else "No bends on this sheet")+"; t="+str(resolved["t"])+" Ri="+str(resolved["Ri"]),"BA90="+format(ba,".9f")+" BD90="+format(bd,".9f"),"K ANSI="+str(resolved["K_ANSI"])+" NOT CALIBRATED","Bend coordinates from native flat X0/Y0:","(Geometric centers, not measured machine BG)"]
  from formed_isometric import bend_note
  for label in p.get('bend_records',[]):notes.append(bend_note(label,ba))
  notes+=["Sequence: "+("long front/back, then short sides" if name=="LID" else "individual sheet bends; verify access"),"CUT contains outer contour and actual pilot holes.","Hole coordinates: see holes CSV and actual DXF."]
  if name=='LID':
   straight=resolved['skirt']-resolved['Ri']-resolved['t']
   notes+=['Skirt center from each own free straight edge:',format(straight+ba/2,'.9f')+' mm (NOT machine BG)','Bend band: '+format(straight,'.9f')+' to '+format(straight+ba,'.9f')]
  rows(notes,800,710)
  text(50,90,"FLAT "+format(fw,".9f")+" x "+format(fh,".9f")+" mm; do not measure paper. Blue dashed lines are fold centers.",10)
  flat_pages[name]={"page_index":mapping["pages"]+len(pages),"flat_map":[scale,0,0,scale,ox,oy]}
  if name in isometric_views:isometric_views[name].update(flat_page_index=flat_pages[name]['page_index'],flat_map=flat_pages[name]['flat_map'],BA_mm=ba)
  finish(name+" flat")
  if name=='LID':
   from corner03 import profile
   s=profile(resolved['t'],resolved['Ri'],resolved['skirt'],resolved['corner_gap'],ba)
   title('LID - 03 CORNER DETAIL FROM ACTUAL NATIVE DXF')
   lo=s['A']-2*s['Ro'];hi=s['B']+s['Ro'];zoom=460/(hi-lo);tx=90-zoom*lo;ty=180-zoom*lo
   cv.saveState();clip=cv.beginPath();clip.rect(80,170,480,480);cv.clipPath(clip,stroke=0,fill=0)
   cv.setLineWidth(.9)
   for record in p['records']:
    if record['type']=='LINE':cv.line(tx+zoom*record['p'][0],ty+zoom*record['p'][1],tx+zoom*record['q'][0],ty+zoom*record['q'][1])
   cv.restoreState()
   for label in ['P1','P2','P3']:
    xx,yy=s[label];cv.circle(tx+zoom*xx,ty+zoom*yy,2,stroke=1,fill=1);text(tx+zoom*xx+7,ty+zoom*yy+7,label,12)
   rows(['Eight actual sloped outer segments: two per corner.','Current t='+str(resolved['t'])+' Ri='+str(resolved['Ri']),'Corner gap='+str(resolved['corner_gap'])+' mm','Short-skirt retreat t+gap='+str(s['short_skirt_retreat'])]+[label+' = '+str([round(v,9) for v in s[label]]) for label in ['P1','P2','P3']]+['Actual native STEP re-unfold and DXF area match.','Root interference and q reported separately.','No historical fixed coordinate template.'],610,650)
   finish('LID actual03 corner')
 cv.save();writer=PdfWriter();writer.append_pages_from_reader(PdfReader(first));writer.append_pages_from_reader(PdfReader(io.BytesIO(buf.getvalue())));writer.add_metadata({"/Title":resolved["id"]+" sheetmetal three views and bending HOLD","/Author":"step-sheetmetal-delivery2.8.1 R12"});writer.write(path);first.unlink()
 from workshop_pdf import append_process_pages
 process=append_process_pages(path,project,resolved,report,projections)
 (Path(path).parents[1]/'evidence'/('PROCESS_PDF_'+project['project']['version']['value']+'.json')).write_text(json.dumps(process,ensure_ascii=False,indent=2))
 from formed_isometric import check_pdf
 checked=check_pdf(path,report['parts'],isometric_views,projections)
 return {**mapping,"total_pages":len(PdfReader(path).pages),"part_flat_pages":flat_pages,'formed_isometric_views':isometric_views,'isometric_vector_checks':checked}
