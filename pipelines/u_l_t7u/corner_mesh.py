# rev t7u: fine tessellation of the LID corner at box (x=0,y=0) for the close-up PNG
import sys,json
sys.path.insert(0,'/opt/freecad-dl/FreeCAD-1.1.1/usr/lib')
import FreeCAD as F,Part
V=F.Vector
s=Part.read(sys.argv[1]).Solids[0];H=float(sys.argv[3]) if len(sys.argv)>3 else 200.0
c=s.common(Part.makeBox(9,9,11,V(-2.5,-2.5,H-10)))
v,f=c.tessellate(0.005)
edges=[[[p.x,p.y,p.z] for p in e.discretize(Deflection=0.005)] for e in c.Edges]
sec=[[[p.x,p.y] for p in w.discretize(Deflection=0.002)] for w in c.slice(V(0,0,1),H-8)]
c2=s.common(Part.makeBox(4.5,4.5,5,V(-2.0,-2.0,H-4)))
v2,f2=c2.tessellate(0.003)
edges2=[[[p.x,p.y,p.z] for p in e.discretize(Deflection=0.003)] for e in c2.Edges]
json.dump({'sec':sec,'v2':[list(x) for x in v2],'f2':[list(x) for x in f2],'edges2':edges2,'v':[list(x) for x in v],'f':[list(x) for x in f],'edges':edges},open(sys.argv[2],'w'))
print(len(v),len(f),len(edges))
