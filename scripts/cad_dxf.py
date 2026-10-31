"""Shared actual planar CAD -> normalized mm/CUT DXF -> geometric readback.
Extracted from the new-box writer; no coordinate scaling, healing, or inferred units.
Split full circular wires canonicalize to one circle without changing geometry.
"""
import math
import FreeCAD as F,Part
from cut_dxf import parse_dxf
from dxf_topology import validate_planar
V=F.Vector
def dxf_record(edge):
    c=edge.Curve
    if isinstance(c,Part.Circle):
        if edge.isClosed():return {"type":"CIRCLE","center":[c.Center.x,c.Center.y],"radius":c.Radius}
        p0,pm,p1=[edge.valueAt(v) for v in [edge.FirstParameter,(edge.FirstParameter+edge.LastParameter)/2,edge.LastParameter]]
        ang=lambda p:math.degrees(math.atan2(p.y-c.Center.y,p.x-c.Center.x))%360
        a0,am,a1=ang(p0),ang(pm),ang(p1)
        if (am-a0)%360>(a1-a0)%360:a0,a1=a1,a0
        return {"type":"ARC","center":[c.Center.x,c.Center.y],"radius":c.Radius,"start":a0,"end":a1}
    if isinstance(c,Part.Line):
        return {"type":"LINE","p":list(edge.Vertexes[0].Point)[:2],"q":list(edge.Vertexes[-1].Point)[:2]}
    raise ValueError("Unsupported flat curve; requires actual CAD adapter: "+c.TypeId)
def write_dxf(path,face):
    pairs=[(0,"SECTION"),(2,"HEADER"),(9,"$INSUNITS"),(70,4),(0,"ENDSEC"),(0,"SECTION"),(2,"ENTITIES")]
    records=[];indices=[]
    for wire in [face.OuterWire]+[w for w in face.Wires if not w.isSame(face.OuterWire)]:
        loop=[]
        wire_records=[dxf_record(edge) for edge in wire.Edges]
        if wire.isClosed() and all(isinstance(edge.Curve,Part.Circle) for edge in wire.Edges):
            first=wire.Edges[0].Curve
            if all((edge.Curve.Center-first.Center).Length<1e-7 and abs(edge.Curve.Radius-first.Radius)<1e-7 for edge in wire.Edges) and abs(wire.Length-2*math.pi*first.Radius)<1e-5:
                wire_records=[{"type":"CIRCLE","center":[first.Center.x,first.Center.y],"radius":first.Radius}]
        for r in wire_records:
            loop.append(len(records));records.append(r);pairs.extend([(0,r["type"]),(8,"CUT")])
            if r["type"]=="LINE":pairs.extend([(10,r["p"][0]),(20,r["p"][1]),(11,r["q"][0]),(21,r["q"][1])])
            else:
                pairs.extend([(10,r["center"][0]),(20,r["center"][1]),(40,r["radius"])])
                if r["type"]=="ARC":pairs.extend([(50,r["start"]),(51,r["end"])])
        indices.append(loop)
    pairs.extend([(0,"ENDSEC"),(0,"EOF")]);path.write_text("\n".join(str(v) for pair in pairs for v in pair)+"\n")
    ents=parse_dxf(path);validate_planar(ents,indices[0])
    def entity_edge(e):
        if e['type']=='LINE':return Part.makeLine(V(float(e[10]),float(e[20]),0),V(float(e[11]),float(e[21]),0))
        center=V(float(e[10]),float(e[20]),0);r=float(e[40])
        if e['type']=='CIRCLE':return Part.makeCircle(r,center)
        start=math.radians(float(e[50]));sweep=(math.radians(float(e[51]))-start)%(2*math.pi)
        point=lambda u:center+V(r*math.cos(start+u*sweep),r*math.sin(start+u*sweep),0)
        return Part.Arc(point(0),point(.5),point(1)).toShape()
    rebuilt=[]
    for loop in indices:
        wire=Part.Wire(Part.__sortEdges__([entity_edge(ents[i]) for i in loop]))
        if not wire.isClosed():raise ValueError('Written DXF wire is open')
        rebuilt.append(Part.Face(wire))
    actual=rebuilt[0]
    for hole_face in rebuilt[1:]:actual=actual.cut(hole_face)
    difference=abs(face.cut(actual).Area)+abs(actual.cut(face).Area)
    if not actual.isValid() or difference>1e-5:raise ValueError('Actual written DXF differs from native flat face: '+str(difference))
    return records,indices,difference
