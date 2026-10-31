"""Conservative planar LINE/ARC/CIRCLE boundary checks; no formed CAD/CAM validation.
Analytic intersection/distance tests; point winding uses <=0.001 mm arc sag.
A 0.002 mm uncertainty guard rejects close hole/boundary/nesting cases for CAD review.
"""
import math
EPS=1e-7
GUARD=.002
def xy(e):return (float(e[10]),float(e[20]))
def dist(a,b):return math.hypot(a[0]-b[0],a[1]-b[1])
def cross(a,b):return a[0]*b[1]-a[1]*b[0]
def sub(a,b):return (a[0]-b[0],a[1]-b[1])
def angles(e):
 a=math.radians(float(e.get(50,0)));s=(math.radians(float(e.get(51,360)))-a)%(2*math.pi)
 return a,s if e['type']=='ARC' else 2*math.pi
def ends(e):
 if e['type']=='LINE':return xy(e),(float(e[11]),float(e[21]))
 a,s=angles(e);c=xy(e);r=float(e[40]);return tuple(c[i]+r*f(a) for i,f in enumerate([math.cos,math.sin])),tuple(c[i]+r*f(a+s) for i,f in enumerate([math.cos,math.sin]))
def on(e,p):
 if e['type']=='LINE':
  a,b=ends(e);return abs(cross(sub(p,a),sub(b,a)))<=EPS*max(1,dist(a,b)) and sum((p[i]-a[i])*(p[i]-b[i]) for i in range(2))<=EPS
 c=xy(e);r=float(e[40]);a,s=angles(e)
 return abs(dist(c,p)-r)<=EPS and (e['type']=='CIRCLE' or (math.atan2(p[1]-c[1],p[0]-c[0])-a)%(2*math.pi)<=s+EPS or dist(p,ends(e)[0])<=EPS)
def intersections(e,f):
 if e['type']=='LINE' and f['type']=='LINE':
  a,b=ends(e);c,d=ends(f);u=sub(b,a);v=sub(d,c);den=cross(u,v)
  if abs(den)<EPS:
   pts=[p for p in [a,b,c,d] if on(e,p) and on(f,p)]
   return pts
  t=cross(sub(c,a),v)/den;p=(a[0]+t*u[0],a[1]+t*u[1]);return [p] if on(e,p) and on(f,p) else []
 if e['type']!='LINE' and f['type']=='LINE':return intersections(f,e)
 if e['type']=='LINE':
  a,b=ends(e);c=xy(f);u=sub(b,a);v=sub(a,c);A=sum(q*q for q in u);B=2*sum(u[i]*v[i] for i in range(2));C=sum(q*q for q in v)-float(f[40])**2;disc=B*B-4*A*C
  if disc< -EPS:return []
  ts=[(-B+sign*math.sqrt(max(0,disc)))/(2*A) for sign in [-1,1]];pts=[(a[0]+t*u[0],a[1]+t*u[1]) for t in ts]
 else:
  a=xy(e);b=xy(f);r=float(e[40]);s=float(f[40]);d=dist(a,b)
  if d<EPS:
   if abs(r-s)>EPS:return []
   # Coincident arcs/circles overlap is deliberately unsupported, even split circles.
   raise ValueError('coincident curved boundaries need CAD adapter')
  if d>r+s+EPS or d<abs(r-s)-EPS:return []
  x=(d*d+r*r-s*s)/(2*d);h=math.sqrt(max(0,r*r-x*x));u=((b[0]-a[0])/d,(b[1]-a[1])/d);m=(a[0]+x*u[0],a[1]+x*u[1]);pts=[(m[0]+sign*h*u[1],m[1]-sign*h*u[0]) for sign in [-1,1]]
 return [p for p in pts if on(e,p) and on(f,p)]
def distance(e,p):
 if e['type']=='LINE':
  a,b=ends(e);v=sub(b,a);u=sub(p,a);t=max(0,min(1,sum(u[i]*v[i] for i in range(2))/sum(q*q for q in v)));return dist(p,(a[0]+t*v[0],a[1]+t*v[1]))
 c=xy(e);r=float(e[40]);d=dist(c,p)
 if d<EPS:return r
 q=(c[0]+r*(p[0]-c[0])/d,c[1]+r*(p[1]-c[1])/d)
 return abs(d-r) if on(e,q) else min(dist(p,a) for a in ends(e))
def sampled(e,reverse=False):
 if e['type']=='LINE':p=list(ends(e))
 else:
  a,s=angles(e);r=float(e[40]);step=min(math.pi/90,2*math.acos(max(-1,1-min(.001/r,1))));n=max(2,math.ceil(s/step));c=xy(e);p=[(c[0]+r*math.cos(a+s*i/n),c[1]+r*math.sin(a+s*i/n)) for i in range(n+1)]
 return p[::-1] if reverse else p
def inside(p,poly):
 x,y=p;hit=False
 for a,b in zip(poly,poly[1:]+poly[:1]):
  if (a[1]>y)!=(b[1]>y) and x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:hit=not hit
 return hit
def validate_planar(ents,indices):
 boundaries=[ents[i] for i in indices];loops=[];pending=set(range(len(boundaries)))
 for i,e in enumerate(boundaries):
  for j in range(i):
   f=boundaries[j];pts=intersections(e,f)
   common=[] if 'CIRCLE' in [e['type'],f['type']] else [a for a in ends(e) for b in ends(f) if dist(a,b)<EPS]
   if any(not any(dist(p,q)<EPS for q in common) for p in pts) or len({(round(p[0],7),round(p[1],7)) for p in pts})>1:raise ValueError('self-intersecting/overlapping outer boundaries')
 while pending:
  seed=min(pending);pending.remove(seed);e=boundaries[seed];loop=[e];poly=sampled(e)
  if e['type']!='CIRCLE':
   while dist(poly[-1],poly[0])>EPS:
    options=[(j,dist(ends(boundaries[j])[1],poly[-1])<EPS) for j in pending if boundaries[j]['type']!='CIRCLE' and any(dist(a,poly[-1])<EPS for a in ends(boundaries[j]))]
    if len(options)!=1:raise ValueError('outer loop cannot be ordered uniquely')
    j,rev=options[0];pending.remove(j);loop.append(boundaries[j]);poly.extend(sampled(boundaries[j],rev)[1:])
  area=abs(sum(a[0]*b[1]-a[1]*b[0] for a,b in zip(poly,poly[1:]+poly[:1])))/2
  if area<=1e-6:raise ValueError('zero-area outer boundary')
  loops.append((loop,poly))
 for i,(loop,poly) in enumerate(loops):
  for j,(other,opol) in enumerate(loops):
   if i!=j and inside(poly[0],opol):raise ValueError('nested outer boundaries need CAD adapter')
 holes=[e for i,e in enumerate(ents) if i not in indices]
 for i,h in enumerate(holes):
  c=xy(h);r=float(h[40]);matches=[loop for loop,poly in loops if inside(c,poly) and min(distance(e,c) for e in loop)>r+GUARD]
  if len(matches)!=1:raise ValueError('hole outside/crossing outer boundary or within0.002mm review guard')
  if any(dist(c,xy(f))<=r+float(f[40])+GUARD for f in holes[:i]):raise ValueError('overlapping/touching inner circles')
 return {'planar_checked':True,'boundary_guard_mm':GUARD,'arc_winding_max_sag_mm':.001}
