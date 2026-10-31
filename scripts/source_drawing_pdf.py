"""All-source-parts review + actual native-flat/bending atlas; blocked parts stay visible."""
import math,textwrap
from pathlib import Path

def write_source_pdf(report,projections,path):
 from reportlab.pdfgen import canvas
 from reportlab.lib.pagesizes import A3,landscape
 from reportlab.pdfbase import pdfmetrics
 from reportlab.pdfbase.cidfonts import UnicodeCIDFont
 from source_contract import delivery_state
 pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'));W,H=landscape(A3);cv=canvas.Canvas(str(path),pagesize=(W,H));pages=[];state=delivery_state(report);isometric_views={}
 def text(x,y,s,size=10,chinese=False):cv.setFont('STSong-Light' if chinese else 'Helvetica',size);cv.drawString(x,y,str(s))
 def title(s):text(34,H-36,s,18);text(34,H-58,'v2.6.1 R06 | ACTUAL SOURCE STEP | mm | AUDIT / PARTIAL / HOLD | production_release=false',10)
 def finish(label):
  text(34,21,'Preserved source geometry. Diagnostic flats are NOT laser-release drawings. BG/tooling/springback/first article unverified. '+str(len(pages)+1),9);cv.showPage();pages.append(label)
 def rows(values,x=42,y=H-98,size=10):
  for value in values:
   for line in textwrap.wrap(str(value),width=135 if x<100 else 68,break_long_words=True) or ['']:
    if y<55:raise ValueError('Source PDF row overflow')
    text(x,y,line,size);y-=15
  return y
 def lines(polylines,rect,label,dimensions=True):
  x,y,w,h=rect;pts=[p for line in polylines for p in line]
  if not pts:text(x+10,y+h/2,'Projection unavailable: '+label);return
  xmin=min(p[0] for p in pts);xmax=max(p[0] for p in pts);ymin=min(p[1] for p in pts);ymax=max(p[1] for p in pts);scale=min((w-65)/max(xmax-xmin,1e-5),(h-65)/max(ymax-ymin,1e-5));ox=x+35-scale*xmin;oy=y+35-scale*ymin
  cv.setLineWidth(.5)
  for line in polylines:
   if len(line)<2:continue
   pp=cv.beginPath();pp.moveTo(ox+scale*line[0][0],oy+scale*line[0][1])
   for p in line[1:]:pp.lineTo(ox+scale*p[0],oy+scale*p[1])
   cv.drawPath(pp)
  text(x+5,y+h-10,label,10)
  if dimensions:
   cv.line(ox+scale*xmin,oy+scale*ymin-12,ox+scale*xmax,oy+scale*ymin-12);text(ox+scale*xmin,oy+scale*ymin-27,format(xmax-xmin,'.6f')+' mm projected extent',9)
   cv.saveState();cv.translate(ox+scale*xmin-14,oy+scale*ymin);cv.rotate(90);text(0,0,format(ymax-ymin,'.6f')+' mm',9);cv.restoreState()
  return [scale,0,0,scale,ox,oy]
 title('SOURCE STEP REVIEW / BENDING ATLAS - '+state['status'])
 text(42,H-100,'既有STEP审核／折弯图册：缺件和失败明确列出；诊断展开不得作为生产下料。',14,True)
 rows(['Source: '+report['source_filename'],'SHA256: '+report['source_sha256'],'Source preserved: '+str(report['source_unchanged']),'Actual solids: '+str(report['solid_count'])+'; physical cylindrical holes: '+str(sum(len(p['holes']) for p in report['parts'])),'Source coordinates retained. Role mappings are supplied classifications, not recovered assembly metadata.','Material: '+str(report['config'].get('material') or 'UNKNOWN')+'; manufacturing K: '+str(report['config'].get('K_ANSI') if report['config'].get('K_ANSI') is not None else 'UNKNOWN'),'Diagnostic K: '+str(report['config'].get('diagnostic_K_ANSI'))+' (algorithm probing ONLY; not a manufacturing candidate)','Source corners preserved. No new-order g0.5/03 policy is applied. No slit, redesign, face deletion or dimensional correction.','BRep bounding boxes may be conservative on BSpline surfaces; dimensions here are measured/projected geometry, not approved design tolerances.']+['Part '+p['id']+': isValid='+str(p['isValid'])+' strict BOP='+str(p['BOP']['ok'])+'; unfold='+p['unfold']['status'] for p in report['parts']]+['HOLD: '+str(h) for h in state['holds']],y=H-132)
 finish('scope and all-part status')
 for name in ['SOURCE_ASSEMBLY','SOURCE_EXPLODED']:
  title(name+' - actual imported BRep three views')
  for label,rect in [('XY',(35,410,530,330)),('XZ',(600,410,530,330)),('YZ',(35,65,530,315))]:lines(projections.get(name,{}).get(label,[]),rect,label+' source projection')
  rows(['Rigid BRep export/readback only.','No source manufacturing defect repaired by moving explosion.','Source interference diagnostic mm3:']+[str(p['parts'])+' = '+format(p['volume_mm3'],'.9f')+(' (invalid source: diagnostic)' if p['diagnostic_on_invalid_source'] else '') for p in report['intersections']],610,360)
  finish(name)
 for p in report['parts']:
  name=p['id'];title(name+' - actual source three views / '+p['unfold']['status'])
  for label,rect in [('XY',(35,410,530,330)),('XZ',(600,410,530,330)),('YZ',(35,65,530,315))]:lines(projections.get(name,{}).get(label,[]),rect,label+' source projection')
  bb=p['bbox_mm'];rows(['Role: '+p['role'],'isValid: '+str(p['isValid'])+'; strict BOP: '+str(p['BOP']['ok']),'BBox X/Y/Z: '+str([round(bb[i+3]-bb[i],6) for i in range(3)]),'Volume mm3: '+format(p['volume_mm3'],'.9f'),'Opposing-skin t mm: '+str(p['measured_planar_t_mm']),'Measured cylinder-pair bends: '+str(len(p['bends'])),'Actual physical holes: '+str(len(p['holes'])),'Corner type is SOURCE PRESERVED / UNCLASSIFIED.','No strict03 pass is inferred from eight diagonals.','Flat status: '+p['unfold']['status'],'Manufacturing accepted: FALSE'],610,365)
  finish(name+' formed')
  if p['bends'] and report.get('version') in ['2.6.0-R05','2.6.1-R06']:
   iso=projections.get(name,{}).get('isometric')
   if not iso:raise ValueError('ISOMETRIC: missing actual imported formed view '+name)
   title(name+' - ACTUAL FORMED ISOMETRIC / '+p['unfold']['status']);mp=lines(iso,(35,135,720,580),'ISOMETRIC actual source BRep; projected lengths, not design dimensions',False)
   u=p['unfold'];attempt=u.get('attempts',[])[u['selected_attempt']] if u.get('selected_attempt') is not None else {};labels=attempt.get('bend_records',[])
   notes=['Actual source STEP geometry; all edges visible.','Source BOP: '+str(p['BOP']['ok']),'Native unfold: '+u['status'],'No manufacturing release.']
   from formed_isometric import iso_point
   for b in labels:
    xx,yy=iso_point(b['source_formed_point_mm']);xx=mp[0]*xx+mp[4];yy=mp[3]*yy+mp[5];cv.circle(xx,yy,3);cv.line(xx,yy,xx+15,yy+19);text(xx+18,yy+20,b['id']+' '+b['direction'],9);notes.append(b['id']+' '+b['direction']+' signed '+format(b['angle_signed_deg'],'.6g')+' deg')
   if labels:notes+=['Direction relative to native root skin,','not machine order/tooling qualification.']
   else:notes+=['Native directions UNKNOWN: no accepted unfold.','Measured cylinder pairs are listed as M1...','Do not invent bend direction for blocked source.']
   rows(notes,790,H-110);isometric_views[name]={'page_index':len(pages),'pdf_map':mp,'bend_labels':labels};finish(name+' formed isometric')
  hole_rows=['ID | D mm | SOURCE X,Y,Z mm | AXIS | source face numbers']+[h['id']+' | '+format(h['D_mm'],'.6f')+' | '+','.join(format(v,'.6f') for v in h['center_mm'])+' | '+str(h['axis'])+' | '+str(h['source_faces']) for h in p['holes']]
  if p['holes']:
   for i in range(0,len(hole_rows),36):title(name+' - source hole centers and axes');rows(hole_rows[i:i+36]);finish(name+' holes')
  bendrows=[];kv=p['unfold'].get('K_ANSI_used');t=p['measured_planar_t_mm']
  for i,b in enumerate(p['bends'],1):
   angle=math.radians(b['angle_deg']);BA=angle*(b['Ri_mm']+kv*t) if kv is not None else None;BD=2*(b['Ri_mm']+t)*math.tan(angle/2)-BA if BA is not None and abs(angle)<math.pi-1e-6 else None
   bendrows+=['M'+str(i)+' source faces '+str(b['faces'])+' | Ri='+format(b['Ri_mm'],'.6f')+' Ro='+format(b['Ro_mm'],'.6f')+' angle='+format(b['angle_deg'],'.6f')+' deg','Axis '+str(b['axis'])+'; line origin perpendicular '+str([round(v,6) for v in b['axis_perpendicular_origin_mm']]),'Axial interval mm '+str([round(v,6) for v in b['axial_interval_mm']]),'BA mm '+(format(BA,'.9f') if BA is not None else 'UNKNOWN')+'; BD mm '+(format(BD,'.9f') if BD is not None else 'UNKNOWN')+'; diagnostic='+str(p['unfold'].get('diagnostic_only',False))]
  title(name+' - measured bends / compensation / tooling HOLD');rows(bendrows or ['No measured cylindrical bends; planar sheet rigid flattening only.']);finish(name+' bend parameters')
  u=p['unfold']
  if u.get('selected_attempt') is None:
   title(name+' - UNFOLD BLOCKED / manufacturing flat absent');rows(['No manufacturing DXF or approved flat dimensions for this part.','Reason: '+str(u.get('reason','Native unfolding failed for tested root faces.'))]+['Face'+str(a['root_face'])+': '+a.get('error','unknown') for a in u.get('attempts',[])]+['Any geometry edit requires its own authorized plan; this run preserves source geometry.','Bending sequence, tooling access and machine BG remain UNKNOWN.']);finish(name+' blocked flat');continue
  attempt=u['attempts'][u['selected_attempt']];title(name+' - '+u['status']+' / actual native flat')
  from dxf_topology import sampled
  ents=[]
  for r in attempt['records']:
   e={'type':r['type'],10:r.get('p',r.get('center'))[0],20:r.get('p',r.get('center'))[1]}
   if r['type']=='LINE':e.update({11:r['q'][0],21:r['q'][1]})
   else:e[40]=r['radius'];e.update({50:r.get('start',0),51:r.get('end',360)})
   ents.append(e)
  lines([sampled(e) for e in ents],(35,110,720,610),'Actual native flat - '+('DIAGNOSTIC ONLY' if u['diagnostic_only'] else 'GEOMETRY CHECKED / HOLD'))
  notes=['Flat extent mm: '+str([round(v,9) for v in attempt['flat_size_mm']]),'Physical flat thickness mm: '+format(attempt['flat_thickness_mm'],'.9f'),'Native vs written DXF area mm2: '+str(attempt['native_vs_DXF_area_mm2']),'Native vs written unfold STEP area mm2: '+str(attempt['native_vs_exported_STEP_area_mm2']),'Actual folds: '+str(attempt['actual_bends'])+'; actual holes: '+str(attempt['flat_hole_count']),'Sloped outer edges: '+str(attempt['sloped_outer_edges']),'Corner03: NOT CLASSIFIED, SOURCE PRESERVED','K used: '+str(kv)+'; status: '+u.get('K_status','unknown'),'DXF: mm INSUNITS4 / CUT; no CAM nesting.','Fold lines are actual native geometry:']
  notes+=['F'+str(i)+': '+str([[round(v,6) for v in point] for point in line]) for i,line in enumerate(attempt['bend_lines'],1)]
  rows(notes,800,H-110,size=9)
  # Overlay actual fold coordinates with the same display transform used by the flat drawing.
  fw,fh=attempt['flat_size_mm'];scale=min((720-65)/max(fw,1e-5),(610-65)/max(fh,1e-5));cv.setStrokeColorRGB(.15,.3,.8);cv.setDash(4,3)
  for line in attempt['bend_lines']:cv.line(70+scale*line[0][0],145+scale*line[0][1],70+scale*line[1][0],145+scale*line[1][1])
  for b in attempt.get('bend_records',[]):
   mid=[sum(pt[i] for pt in b['flat_line_mm'])/2 for i in [0,1]];text(75+scale*mid[0],150+scale*mid[1],b['id']+' '+b['direction'],9)
  cv.setDash();cv.setStrokeColorRGB(0,0,0);finish(name+' native flat')
 title('SOURCE VALIDITY / DESIGN DECISIONS / NO AUTOMATIC REPAIR')
 rows(['Strict BOP failures remain failures even if a native flat is valid.','Positive interference on invalid geometry is a stable diagnostic, not certified physical acceptance.','Preserve source corner, g, q and parts. A seam or new U/end-panel structure needs explicit user approval.','Material / K source / machine BG / tooling / springback / hardware and first article require independent confirmation.']+['Part '+p['id']+' repair '+r['method']+': BOP='+str(r.get('after',{}).get('BOP',{}).get('ok'))+'; equivalent_candidate='+str(r.get('equivalent_candidate'))+'; selected_for_output=False' for p in report['parts'] for r in p['repairs']]+['Measured interface: '+str(report.get('interface_measurement','Not requested; no g/q guessed.'))]);finish('limitations and decisions');cv.save()
 from corner03 import check_pdf_geometry
 checks={}
 for name,v in isometric_views.items():
  segments=[(a,b) for poly in projections[name]['isometric'] for a,b in zip(poly,poly[1:])];checks[name]=check_pdf_geometry(path,v['page_index'],segments,v['pdf_map'])
 return {'pages':len(pages),'page_labels':pages,'all_source_part_ids':[p['id'] for p in report['parts']],'scope':'audit_and_supported_bending_partial_HOLD','manufacturing_pdf_complete':False,'formed_isometric_views':isometric_views,'isometric_vector_checks':checks}
