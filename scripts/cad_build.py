#!/usr/bin/env python3
"""Isolated FreeCAD/SheetMetal worker. Reads one resolved job; writes only a NEW run directory."""
import argparse, json, math, sys, hashlib, itertools
from pathlib import Path

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("resolved_job");ap.add_argument("--output",required=True)
    ap.add_argument("--formed-review-only",action="store_true");ap.add_argument("--freecad-lib");ap.add_argument("--sheetmetal-path",required=True)
    a=ap.parse_args()
    if a.freecad_lib:sys.path.insert(0,a.freecad_lib)
    sys.path.insert(0,a.sheetmetal_path)
    import FreeCAD as F, Part, TechDraw
    import SheetMetalNewUnfolder as NU
    from cut_dxf import parse_dxf
    from dxf_topology import validate_planar
    from corner03 import check_dxf, profile
    j=json.loads(Path(a.resolved_job).read_text());out=Path(a.output).resolve()
    from site_fit import require_delivery_decision,check_actual_overlap,VOLUME_TOL_MM3
    if not a.formed_review_only:require_delivery_decision(j)
    if out.exists():raise ValueError("CAD output directory already exists; no overwrite")
    out.mkdir(parents=True)
    V=F.Vector
    L,W,H,t,ri,g,q,skirt,cg,K,seam=[j[k] for k in ("L","W","H","t","Ri","g","q","skirt","corner_gap","K_ANSI","seam_gap")]
    ro=ri+t;hb=H-t-q if j["lid_required"] else H
    def box(x,y,z,p):return Part.makeBox(x,y,z,V(*p))
    def wire_face(points,arcs=None):
        arcs=arcs or {}
        return Part.Face(Part.Wire([Part.Arc(V(*p),V(*arcs[i]),V(*points[(i+1)%len(points)])).toShape() if i in arcs else Part.makeLine(V(*p),V(*points[(i+1)%len(points)])) for i,p in enumerate(points)]))
    def u_cross(width,height,xyz):
        points=[(0,height),(0,ro),(ro,0),(width-ro,0),(width,ro),(width,height),(width-t,height),(width-t,ro),(width-ro,t),(ro,t),(t,ro),(t,height)]
        mids={1:(ro-ro/math.sqrt(2),ro-ro/math.sqrt(2)),3:(width-ro+ro/math.sqrt(2),ro-ro/math.sqrt(2)),7:(width-ro+ri/math.sqrt(2),ro-ri/math.sqrt(2)),9:(ro-ri/math.sqrt(2),ro-ri/math.sqrt(2))}
        return wire_face([xyz(*p) for p in points],{i:xyz(*p) for i,p in mids.items()})
    def reflect(s,axis):
        m=F.Matrix();setattr(m,["A11","A22","A33"][axis],-1);return s.transformed(m)
    def lid03():
        hx=L/2+g+t;hy=W/2+g+t;cx=hx-ro;cy=hy-ro;cz=H-ro;bottom=H-skirt;straight=skirt-ro
        def bend(a0,a1):
            def pt(i,side):
                u=i/500;theta=math.pi/2*u;span=a0+(a1-a0)*u
                return V(side*span,cz+ro*math.cos(theta),cy+ro*math.sin(theta))
            def curve(side,reverse=False):
                pts=[pt(i,side) for i in range(501)]
                if reverse:pts.reverse()
                c=Part.BSplineCurve();c.interpolate(pts);return c.toShape()
            wire=Part.Wire([Part.makeLine(pt(0,-1),pt(0,1)),curve(1),Part.makeLine(pt(500,1),pt(500,-1)),curve(-1,True)])
            surf=Part.makeCylinder(ro,2*hx+20,V(-hx-10,cz,cy),V(1,0,0)).Face1.Surface
            face=Part.Face(surf,wire);face.validate()
            if not face.isValid():raise ValueError("03 cylindrical trim face invalid")
            return face.makeOffsetShape(-t,1e-7,fill=True)
        b1=bend(cx,hx);savecy=cy;cy=cx;b2=bend(hy-ro,hy-t-cg);cy=savecy
        m=F.Matrix();m.A11=0;m.A13=1;m.A31=-1;m.A33=0;b2=b2.transformed(m)
        bends=[b1,reflect(b1,2),b2,reflect(b2,0)]
        if max(abs(a.common(b).Volume) for a,b in itertools.combinations(bends,2))>1e-5:raise ValueError("03 lid bend corners intersect")
        roof=box(2*cx,t,2*cy,(-cx,H-t,-cy))
        longwall=box(2*hx,straight,t,(-hx,bottom,hy-t))
        shortwall=box(t,straight,2*(hy-t-cg),(hx-t,bottom,-hy+t+cg))
        lid=roof.multiFuse(bends+[longwall,reflect(longwall,2),shortwall,reflect(shortwall,0)]).removeSplitter()
        tr=F.Matrix();tr.A22=0;tr.A23=-1;tr.A32=1;tr.A33=0;lid=lid.transformed(tr);lid.translate(V(L/2,W/2,0))
        return lid
    if j["method"]=="u_external_ends":
        u=u_cross(W,hb,lambda y,z:(t+seam,y,z)).extrude(V(L-2*t-2*seam,0,0))
        inset=j.get('end_inset',0);eradius=ro-inset;etop=hb if j.get('end_top_flush',False) else hb-inset
        pts=[(0,inset,etop),(0,inset,ro),(0,ro,inset),(0,W-ro,inset),(0,W-inset,ro),(0,W-inset,etop)]
        arcs={1:(0,ro-eradius/math.sqrt(2),ro-eradius/math.sqrt(2)),3:(0,W-ro+eradius/math.sqrt(2),ro-eradius/math.sqrt(2))}
        e=wire_face(pts,arcs).extrude(V(t,0,0));er=e.copy();er.translate(V(L-t,0,0))
        parts={"U":u,"END_L":e,"END_R":er};expected={"U":2,"END_L":0,"END_R":0}
    elif j["method"]=="u_wrap_bottom_l":
        u=u_cross(L,W,lambda x,p:(x,W-p,0)).extrude(V(0,0,hb))
        x0=t+seam;x1=L-t-seam;radius=ri-seam
        pts=[(x0,0,0),(x1,0,0),(x1,W-ro,0),(L-ro,W-t-seam,0),(ro,W-t-seam,0),(x0,W-ro,0)]
        arcs={2:(L-ro+radius/math.sqrt(2),W-ro+radius/math.sqrt(2),0),4:(ro-radius/math.sqrt(2),W-ro+radius/math.sqrt(2),0)}
        cavity=wire_face(pts,arcs).extrude(V(0,0,hb+1))
        pts=[(x0,0,hb),(x0,0,ro),(x0,ro,0),(x0,W,0),(x0,W,t),(x0,ro,t),(x0,t,ro),(x0,t,hb)]
        arcs={1:(x0,ro-ro/math.sqrt(2),ro-ro/math.sqrt(2)),5:(x0,ro-ri/math.sqrt(2),ro-ri/math.sqrt(2))}
        el=wire_face(pts,arcs).extrude(V(x1-x0,0,0)).common(cavity).removeSplitter()
        parts={"U":u,"L":el};expected={"U":2,"L":1}
    else:raise ValueError("Unsupported structure; no fallback generator")
    if j["lid_required"]:parts["LID"]=lid03();expected["LID"]=4
    for hole in j["holes"]:
        if hole["part_id"] not in parts:raise ValueError("Hole owner not in selected structure")
        p=V(*hole["point"]);axis=V(*hole["axis"])
        tool=Part.makeCylinder(hole["diameter"]/2,4*ro+4,p-axis*(2*ro+2),axis)
        parts[hole["part_id"]]=parts[hole["part_id"]].cut(tool).removeSplitter()
    sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    def bbox(s):return [getattr(s.BoundBox,k) for k in ("XMin","YMin","ZMin","XMax","YMax","ZMax")]
    def export(s,path,solids):
        if not s.isValid() or len(s.Solids)!=solids:raise ValueError("Invalid CAD solid: "+path.name)
        for solid in s.Solids:solid.check(True)
        s.exportStep(str(path));back=Part.read(str(path))
        for solid in back.Solids:solid.check(True)
        if not back.isValid() or len(back.Solids)!=solids or abs(back.Volume-s.Volume)>max(.01,s.Volume*1e-7):raise ValueError("STEP export/readback mismatch")
        if max(abs(x-y) for x,y in zip(bbox(s),bbox(back)))>1e-5:raise ValueError("STEP bbox changed")
        return back
    report={"CAD_executed":True,"FreeCAD_version":F.Version(),"OCCT":Part.OCC_VERSION,"job_sha256":sha(a.resolved_job),"method":j["method"],"parts":{},"holds":["NO_FACTORY_CALIBRATION","TOOLING_AND_FIRST_ARTICLE_NOT_VERIFIED"],"production_release":False,"intersections":[],"holes":[]}
    report.update(fit=j.get('fit'),site_fit_acceptance=j.get('site_fit_acceptance'),geometry_interference_eliminated=False,trial_assembly_confirmed=False)
    progress={'status':'IN_PROGRESS','verified_formed_parts':[],'verified_unfold_DXF_parts':[],'overall_delivery_complete':False}
    def save_progress():(out/'cad_progress.json').write_text(json.dumps(progress,indent=2))
    save_progress()
    for name,shape in list(parts.items()):
        path=out/(name+".step");parts[name]=export(shape,path,1)
        report["parts"][name]={"formed_step":path.name,"formed_sha256":sha(path),"bends":expected[name],"bbox":bbox(parts[name]),"volume_mm3":parts[name].Volume}
        progress['verified_formed_parts'].append({'part_id':name,'path':path.name,'sha256':sha(path)});save_progress()
    for a1,b1 in itertools.combinations(parts,2):
        intersection=parts[a1].common(parts[b1]);overlap=abs(intersection.Volume);record={"parts":[a1,b1],"volume_mm3":overlap};report["intersections"].append(record)
        if overlap>VOLUME_TOL_MM3:
            if "LID" in (a1,b1):
                record['intersection_bbox']=bbox(intersection)
                (out/'interference_measurements.json').write_text(json.dumps(report,indent=2))
                record['fit_disposition']='REVIEW_ONLY_NOT_DELIVERY' if a.formed_review_only else check_actual_overlap(overlap,j.get('site_fit_acceptance'),intersection.BoundBox.ZMin,H-t-ri)
                report["holds"].append(record['fit_disposition']+':'+a1+'/'+b1+':'+str(overlap))
            else:raise ValueError("Body sheets intersect: "+a1+"/"+b1+" "+str(overlap))
    report['assembly_interference_free']=not any(i['volume_mm3']>VOLUME_TOL_MM3 for i in report['intersections'])
    if (out/'interference_measurements.json').exists():(out/'interference_measurements.json').unlink()
    for hole in j["holes"]:
        axis=V(*hole["axis"]);pt=V(*hole["point"]);shape=parts[hole["part_id"]]
        matches=[edge.Curve for edge in shape.Edges if isinstance(edge.Curve,Part.Circle) and edge.isClosed() and abs(edge.Curve.Radius-hole["diameter"]/2)<1e-5 and abs(abs(edge.Curve.Axis.dot(axis))-1)<1e-6 and (edge.Curve.Center-pt).cross(axis).Length<1e-5 and abs((edge.Curve.Center-pt).dot(axis))<t+1e-5]
        if len(matches)!=2 or abs((matches[0].Center-matches[1].Center).Length-t)>1e-5:raise ValueError("Hole surface centers/thickness not found: "+hole["id"])
        report["holes"].append({**hole,"actual_surface_centers":[list(c.Center) for c in matches],"actual_diameter_mm":2*matches[0].Radius})
    report['fixing_pairs']=[]
    by_id={h['id']:h for h in report['holes']}
    report['mounting_pattern_geometry']=[]
    for pattern in j.get('mounting_patterns',[]):
        def actual(hid):return max([V(*pt) for pt in by_id[hid]['actual_surface_centers']],key=lambda point:point.z)
        wide=[actual(hid) for hid in pattern['wide_hole_ids']];narrow=[actual(hid) for hid in pattern['narrow_hole_ids']]
        wm=(wide[0]+wide[1])*.5;nm=(narrow[0]+narrow[1])*.5;center=(wm+nm)*.5
        if math.hypot(center.x-pattern['center_mm'][0],center.y-pattern['center_mm'][1])>1e-5:raise ValueError('Actual handle center differs from declared center')
        expected_sign=1 if pattern['wide_towards']=='positive_x' else -1
        if (wm.x-nm.x)*expected_sign<=0 or abs(wm.y-nm.y)>1e-5:raise ValueError('Actual handle row orientation differs from profile')
        report['mounting_pattern_geometry'].append({'id':pattern['id'],'actual_center_xy_mm':[center.x,center.y],'wide_midpoint_xy_mm':[wm.x,wm.y],'narrow_midpoint_xy_mm':[nm.x,nm.y],'actual_wide_pitch_mm':(wide[1]-wide[0]).Length,'actual_narrow_pitch_mm':(narrow[1]-narrow[0]).Length,'actual_spacing_mm':(wm-nm).Length,'wide_towards':pattern['wide_towards']})
    for pair in j.get('fixing_pairs',[]):
        b=by_id[pair['body_hole_id']];c=by_id[pair['lid_hole_id']];axis=V(*b['axis'])
        delta=V(*c['actual_surface_centers'][0])-V(*b['actual_surface_centers'][0]);offset=delta.cross(axis).Length
        if offset>1e-5 or V(*c['axis']).cross(axis).Length>1e-6:raise ValueError('Actual fixing hole axes are not coaxial: '+pair['id'])
        report['fixing_pairs'].append({**pair,'actual_axis_offset_mm':offset,'body_actual_D_mm':b['actual_diameter_mm'],'lid_actual_D_mm':c['actual_diameter_mm'],'thin_sheet_thread_strength':'HOLD'})
    if j['method']=='u_external_ends':
        inset=j.get('end_inset',0);corner=ro-inset;results=[]
        u_arcs=[edge.Curve for edge in parts['U'].Edges if isinstance(edge.Curve,Part.Circle) and not edge.isClosed() and abs(abs(edge.Curve.Axis.x)-1)<1e-6 and abs(edge.Curve.Radius-ro)<1e-5]
        if not u_arcs:raise ValueError('Actual U outer corner arcs absent')
        for name in ['END_L','END_R']:
            b=parts[name].BoundBox;top=hb if j.get('end_top_flush',False) else hb-inset
            if max(abs(b.YMin-inset),abs(b.YMax-(W-inset)),abs(b.ZMin-inset),abs(b.ZMax-top))>1e-5:raise ValueError('Actual end contour offset incorrect')
            arcs=[edge.Curve for edge in parts[name].Edges if isinstance(edge.Curve,Part.Circle) and not edge.isClosed() and abs(abs(edge.Curve.Axis.x)-1)<1e-6 and abs(edge.Curve.Radius-corner)<1e-5]
            if len(arcs)!=4:raise ValueError('Actual end bottom corner arcs missing')
            for arc in arcs:
                if min(math.hypot(arc.Center.y-ro,arc.Center.z-ro),math.hypot(arc.Center.y-(W-ro),arc.Center.z-ro))>1e-5:raise ValueError('End/U corner axes are not concentric')
                if min(math.hypot(arc.Center.y-ref.Center.y,arc.Center.z-ref.Center.z) for ref in u_arcs)>1e-5:raise ValueError('Actual end corner axes differ from actual U arcs')
            results.append({'part_id':name,'actual_bbox':bbox(parts[name]),'corner_radius_mm':corner,'corner_centers_yz':[[arc.Center.y,arc.Center.z] for arc in arcs]})
        report['end_profile']={'inset_yz_mm':inset,'top_flush':j.get('end_top_flush',False),'concentric_with_U':True,'axial_gaps_mm':[parts['U'].BoundBox.XMin-parts['END_L'].BoundBox.XMax,parts['END_R'].BoundBox.XMin-parts['U'].BoundBox.XMax],'ends':results}
    body=Part.makeCompound([s for n,s in parts.items() if n!="LID"]);body_back=export(body,out/"BODY.step",len(parts)-int(j["lid_required"]))
    if j['lid_required']:
        from interference_volume import measurement
        authoritative=abs(body_back.common(parts['LID']).Volume)
        report['root_interference_measurement']=measurement(authoritative,sum(i['volume_mm3'] for i in report['intersections'] if 'LID' in i['parts']))
    assembly=Part.makeCompound(list(parts.values()));export(assembly,out/"ASSEMBLY.step",len(parts))
    exploded=[];shifts={}
    for i,(name,s) in enumerate(parts.items()):
        delta=V(0,0,0) if name=="U" else V(0,0,skirt+hb*.5) if name=="LID" else V((-1 if name in ("END_L","L") else 1)*(L*.35+20),0,0)
        copy=s.copy();copy.translate(delta);exploded.append(copy);shifts[name]=list(delta)
    export(Part.makeCompound(exploded),out/"EXPLODED.step",len(parts));report["exploded_translations_mm"]=shifts
    doc=F.newDocument("IsolatedSheetmetalBuild")
    def normalize(flat,normal):
        flat=flat.transformed(F.Placement(V(),F.Rotation(normal,V(0,0,1))).toMatrix())
        bb=flat.BoundBox;flat.translate(V(-bb.XMin,-bb.YMin,-bb.ZMax));return flat
    def plane_face(shape):
        fs=[f for f in shape.Faces if isinstance(f.Surface,Part.Plane) and abs(abs(f.normalAt(0,0).z)-1)<1e-6 and abs(f.CenterOfMass.z)<1e-5]
        return max(fs,key=lambda f:f.Area)
    from cad_dxf import write_dxf
    if not a.formed_review_only:
        for name,shape in parts.items():
            ob=doc.addObject("Part::Feature",name);ob.Shape=shape
            if expected[name]:
                faces=[i for i,f in enumerate(shape.Faces) if isinstance(f.Surface,Part.Plane)]
                if name=="LID":faces=[i for i in faces if abs(shape.Faces[i].CenterOfMass.z-H)<1e-5 and shape.Faces[i].normalAt(0,0).z>.999]
                root=max(faces,key=lambda i:shape.Faces[i].Area)
                from measured_unfold import get_unfold
                from formed_isometric import track_bends,records as bend_records
                with track_bends(NU):(_,flat,lines,normal,bends),thickness_measurement=get_unfold(NU.BendAllowanceCalculator.from_single_value(K,"ansi"),ob,"Face"+str(root+1),t)
                if len(bends)!=expected[name]:raise ValueError("Actual bend count mismatch: "+name)
                rot=F.Placement(V(),F.Rotation(normal,V(0,0,1))).toMatrix();lines=lines.transformed(rot)
                flat=flat.transformed(rot);bb=flat.BoundBox;delta=V(-bb.XMin,-bb.YMin,-bb.ZMax);flat.translate(delta);lines.translate(delta)
                combined=F.Placement(delta,F.Rotation()).toMatrix().multiply(rot)
                report['parts'][name]['bend_records']=bend_records(bends,combined,root+1,normal,[[[p.x,p.y] for p in edge.discretize(Number=2)] for edge in lines.Edges])
                report['parts'][name]['root_flat_map8']=[combined.A11,combined.A12,combined.A13,combined.A14,combined.A21,combined.A22,combined.A23,combined.A24]
                report['parts'][name]['thickness_measurement']=thickness_measurement
            else:
                # Rigidly rotate the actual planar end sheet; no synthetic rectangle.
                f=max([f for f in shape.Faces if isinstance(f.Surface,Part.Plane)],key=lambda f:f.Area)
                normal=f.normalAt(0,0);flat=normalize(shape,normal);lines=Part.Shape();bends=[];root=None
            if not flat.isValid() or len(flat.Solids)!=1 or abs(flat.BoundBox.ZLength-t)>1e-5:raise ValueError("Unfold thickness/solid check failed: "+name)
            face=plane_face(flat)
            if abs(flat.Volume/face.Area-t)>1e-5:raise ValueError("Flat volume/area thickness mismatch: "+name)
            flat_back=export(flat,out/(name+"_UNFOLD.step"),1);back_face=plane_face(flat_back)
            step_difference=abs(face.cut(back_face).Area)+abs(back_face.cut(face).Area)
            if step_difference>1e-5:raise ValueError('Written unfold STEP differs from actual native flat: '+str(step_difference))
            records,indices,dxf_difference=write_dxf(out/(name+".dxf"),face)
            circles=[r for r in records if r["type"]=="CIRCLE"]
            want=sorted(h["diameter"] for h in j["holes"] if h["part_id"]==name)
            if len(circles)!=len(want) or any(abs(x-y)>1e-5 for x,y in zip(sorted(2*r["radius"] for r in circles),want)):raise ValueError("Native flat hole contract mismatch")
            bend_lines=[[[p.x,p.y] for p in e.discretize(Number=2)] for e in lines.Edges]
            report["parts"][name].update(unfold_step=name+"_UNFOLD.step",dxf=name+".dxf",flat_size_mm=[face.BoundBox.XLength,face.BoundBox.YLength],unfold_t_mm=flat.Volume/face.Area,records=records,outer_boundary_entity_indices=indices[0],bend_lines=bend_lines,unfold_sha256=sha(out/(name+"_UNFOLD.step")),dxf_sha256=sha(out/(name+".dxf")),actual_bends=len(bends),actual_holes=len(circles))
            report['parts'][name].update(native_DXF_area_difference_mm2=dxf_difference,native_exported_unfold_area_difference_mm2=step_difference)
            if name=="LID":
                s=profile(t,ri,skirt,cg,math.pi/2*(ri+K*t));s["flat_size"]=report["parts"][name]["flat_size_mm"]
                check_dxf(out/(name+".dxf"),s)
            print(name,"native STEP/unfold/DXF checked",flush=True)
            progress['verified_unfold_DXF_parts'].append(name);save_progress()
    F.closeDocument(doc.Name)
    report['formed_review_only']=a.formed_review_only
    report['manufacturing_K']=K
    for name in parts:report['parts'][name]['actual_formed_holes']=sum(h['part_id']==name for h in report['holes'])
    projections={}
    for name,shape in {**parts,"ASSEMBLY":assembly,"EXPLODED":Part.makeCompound(exploded)}.items():
        projections[name]={}
        from formed_isometric import actual_lines
        projections[name]['isometric']=actual_lines(shape)
        for label,direction in [("front",V(0,-1,0)),("right",V(1,0,0)),("top",V(0,0,1))]:
            groups=TechDraw.projectEx(shape,direction);pol=[]
            for item in groups[:5]:
                for edge in item.Edges:
                    vv=edge.discretize(Deflection=.05);pol.append([[p.x,p.y] if label=="top" else [-p.y,p.x] if label=="right" else [p.y,-p.x] for p in vv])
            projections[name][label]=pol
    (out/"projections.json").write_text(json.dumps(projections))
    mesh={}
    for name,shape in parts.items():
        vertices,triangles=shape.tessellate(.35)
        mesh[name]={'vertices':[list(v) for v in vertices],'triangles':triangles,'formed_sha256':report['parts'][name]['formed_sha256']}
    (out/'preview_mesh.json').write_text(json.dumps({'parts':mesh,'exploded_translations_mm':shifts}))
    (out/"cad_report.json").write_text(json.dumps(report,indent=2))
    progress['status']='CAD_STAGE_CHECKED_WITH_HOLD';save_progress()
    print("CAD worker complete; production_release=false",flush=True)

if __name__=="__main__":main()
