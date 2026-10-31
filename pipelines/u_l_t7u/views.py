# v2.8.2 pipeline u_l_t7u (DEFAULT structure): vendored from 干画图3's /workspace/orders/box-180x420x175/addendum-tools (S-201-1-20261021-007-v1).
# v2.8.2 changes: hardcoded order/skill/tmp paths -> env SM_ORDER (order folder) + this folder; job features from release_config.json.
# HLR vector views from actual E STEP (TechDraw.projectEx) + measured features. FreeCAD python.
import sys,json,math
sys.path.insert(0,'/opt/freecad-dl/FreeCAD-1.1.1/usr/lib')
import FreeCAD as F,Part,TechDraw
sys.path.insert(0,__import__('os').path.dirname(__import__('os').path.abspath(__file__)));import cfg
W=str(cfg.W);RD=cfg.ROOF_D
TH=json.load(open(W+'/E_main_report.json'))['params']['t']
V=F.Vector
def proj_raw(shape,d):
    g=TechDraw.projectEx(shape,d);return g
def axis_map(d):
    # linear map of world axes into projectEx 2D, measured by projecting unit edges
    o=None;cols=[]
    for ax in (V(100,0,0),V(0,100,0),V(0,0,100)):
        e=Part.makeLine(V(0,0,0),ax);g=TechDraw.projectEx(e,d)
        es=[x for grp in g for x in (grp.Edges if grp else [])]
        if es:
            a=es[0].Vertexes[0].Point;b=es[0].Vertexes[-1].Point
            # orientation: identify which end is origin by projecting origin vertex
            cols.append((b-a))
            o=o
        else:cols.append(V(0,0,0))
    # origin offset
    v0=TechDraw.projectEx(Part.makeLine(V(0,0,0),V(100,0,0)),d);e0=[x for grp in v0 for x in (grp.Edges if grp else [])][0]
    return cols,e0
def pts_of(e):return [[p.x,p.y] for p in e.discretize(Deflection=0.03)]
def view(shape,d,right,up):
    """returns polylines in (right·p, up·p) world mm, verified by an affine fit on shape vertices"""
    g=proj_raw(shape,d);vis=[]
    for i in (0,1,3):
        if g[i]:vis+= [pts_of(e) for e in g[i].Edges]
    hid=[]
    if g[5]:hid=[pts_of(e) for e in g[5].Edges]
    # fit affine map from raw 2D -> target 2D using projected vertices of a reference compound of points: use shape bbox corners via tiny edges
    bb=shape.BoundBox;refs=[V(bb.XMin,bb.YMin,bb.ZMin),V(bb.XMax,bb.YMin,bb.ZMin),V(bb.XMin,bb.YMax,bb.ZMin),V(bb.XMin,bb.YMin,bb.ZMax)]
    raw=[];tgt=[]
    for p in refs:
        e=Part.makeLine(p,p+V(0.001,0.0013,0.0017))
        gg=TechDraw.projectEx(e,d);es=[x for grp in gg for x in (grp.Edges if grp else [])]
        q=es[0].Vertexes[0].Point;raw.append((q.x,q.y));tgt.append((right.dot(p) if right else None,up.dot(p) if up else None))
    return vis,hid,raw,refs
def fit(raw,tgt):
    # solve u = a*x+b*y+c via least squares (3 unknowns, 4 points)
    import numpy as np
    A=np.array([[x,y,1] for x,y in raw]);res=[]
    for k in (0,1):
        b=np.array([t[k] for t in tgt]);sol,*_=np.linalg.lstsq(A,b,rcond=None);res.append(sol.tolist())
    err=max(abs(np.array([[x,y,1] for x,y in raw])@np.array(res).T-np.array(tgt)).ravel())
    return res,float(err)
def apply(m,pols):return [[[m[0][0]*x+m[0][1]*y+m[0][2],m[1][0]*x+m[1][1]*y+m[1][2]] for x,y in p] for p in pols]
iso_d=V(1,-1,1);iso_d.normalize()
# iso target: standard isometric axes in 2D
c30=math.cos(math.radians(30));s30=0.5
def iso2(p):return (c30*(p.x+p.y)*1.0, (p.z) + s30*(p.y-p.x))   # viewer at (+x,-y,+z): x goes right-down, y right-up
VIEWS={'front':(V(0,-1,0),V(1,0,0),V(0,0,1)),'left':(V(-1,0,0),V(0,-1,0),V(0,0,1)),'right':(V(1,0,0),V(0,1,0),V(0,0,1)),'top':(V(0,0,1),V(1,0,0),V(0,1,0))}
out={}
shapes={n:Part.read(f'{W}/{n}.step') for n in ('U','L','LID','ASSEMBLY')}
for n,s in shapes.items():
    out[n]={}
    for vn,(d,r,u) in VIEWS.items():
        vis,hid,raw,refs=view(s,d,r,u)
        tgt=[(r.dot(p),u.dot(p)) for p in refs];m,err=fit(raw,tgt)
        if err>1e-4:  # try opposite direction
            vis,hid,raw,refs=view(s,d*-1,r,u);m,err=fit(raw,tgt)
        assert err<1e-4,(n,vn,err)
        out[n][vn]={'visible':apply(m,vis),'hidden':apply(m,hid),'fit_err_mm':err}
    vis,hid,raw,refs=view(s,iso_d,None,None)
    tgt=[iso2(p) for p in refs];m,err=fit(raw,tgt)
    if err>1e-3:
        vis,hid,raw,refs=view(s,iso_d*-1,None,None);m,err=fit(raw,tgt)
    assert err<1e-3,(n,'iso',err)
    out[n]['iso']={'visible':apply(m,vis),'fit_err_mm':err}
    bb=s.BoundBox;out[n]['bbox']=[bb.XMin,bb.YMin,bb.ZMin,bb.XMax,bb.YMax,bb.ZMax]
# measured features
def holes(s):
    res=[]
    for f in s.Faces:
        if isinstance(f.Surface,Part.Cylinder) and f.Surface.Radius<10:
            c=f.Surface.Center;a=f.Surface.Axis;bb=f.BoundBox
            ext=abs(a.x)*bb.XLength+abs(a.y)*bb.YLength+abs(a.z)*bb.ZLength
            if abs(ext-TH)>0.01 or abs(f.Area-2*math.pi*f.Surface.Radius*TH)>0.5*f.Area:continue  # through-hole wall of t=2 only (excludes bend cylinders)
            # centre at mid of face along axis
            mid=V((bb.XMin+bb.XMax)/2,(bb.YMin+bb.YMax)/2,(bb.ZMin+bb.ZMax)/2)
            res.append({'d':round(2*f.Surface.Radius,4),'center':[round(mid.x,4),round(mid.y,4),round(mid.z,4)],'axis':[round(a.x,3),round(a.y,3),round(a.z,3)]})
    # dedupe (split cylinder faces)
    uniq=[]
    for h in res:
        if not any(abs(h['d']-u['d'])<1e-6 and math.dist(h['center'],u['center'])<0.6 for u in uniq):uniq.append(h)
    return uniq
feat={n:{'holes':holes(shapes[n])} for n in ('U','L','LID')}
lid=shapes['LID'];roof=[f for f in lid.Faces if isinstance(f.Surface,Part.Plane) and abs(f.CenterOfMass.z-lid.BoundBox.ZMax)<1e-6]
roof=max(roof,key=lambda f:f.Area);inner=[w for w in roof.Wires if not w.isSame(roof.OuterWire)]
r16=[]
for w in inner:
    if all(isinstance(e.Curve,Part.Circle) for e in w.Edges) and abs(w.Edges[0].Curve.Radius-RD/2)<1e-6:
        c=w.Edges[0].Curve.Center;r16.append({'d':RD,'center':[round(c.x,4),round(c.y,4)],'measured_from':'LID.step roof inner wire'})
assert len(r16)==2,len(r16);r16.sort(key=lambda h:(h['center'][0],h['center'][1]))
assert not any(len(w.Edges)==8 for w in inner)   # no rectangular cutout in this order
feat['LID']['roof16']=r16
feat['LID']['cutout']=None
feat['LID']['outer']=out['LID']['bbox'];feat['body']={'U':out['U']['bbox'],'L':out['L']['bbox']}
out['features']=feat
json.dump(out,open(f'{W}/views_E.json','w'))
print(json.dumps({n:{v:out[n][v]['fit_err_mm'] for v in ('front','left','right','top','iso')} for n in shapes},indent=0))
print(json.dumps(feat['LID']['roof16']));print([h for h in feat['LID']['holes'] if h['d']>4.6])
print([h for h in feat['U']['holes']][:3]);print(feat['L']['holes'])
