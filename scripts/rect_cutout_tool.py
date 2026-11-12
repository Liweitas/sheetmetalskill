"""Order-local rectangular panel cutout helper (007). Supports axis-aligned X/Y/Z.
Not a global skill change; used only by this order's cad_build adapter.
size_xy = (size along first tangential axis, size along second):
  axis +Z: (X, Y); axis +Y/-Y: (X, Z); axis +X/-X: (Y, Z)
"""
import math
from FreeCAD import Vector as V
import Part

def _rounded_rect_face_2d(cx, cy, sx, sy, r, z0, e1, e2, n):
    """Build face in plane through origin+z0*n? Actually place at point c0 = cx*e1+cy*e2 + z0_offset along n elsewhere.
    Here cx,cy are center coords in (e1,e2); corners in 3D via e1/e2; face extruded later along n.
    """
    hw, hh = sx/2.0, sy/2.0
    def P(a, b):
        return V(0,0,0) + e1*a + e2*b  # relative; caller translates
    # work in 2D then map
    pts2 = [
        (cx - hw + (r if r>0 else 0), cy - hh),
        (cx + hw - (r if r>0 else 0), cy - hh),
        (cx + hw, cy - hh + (r if r>0 else 0)),
        (cx + hw, cy + hh - (r if r>0 else 0)),
        (cx + hw - (r if r>0 else 0), cy + hh),
        (cx - hw + (r if r>0 else 0), cy + hh),
        (cx - hw, cy + hh - (r if r>0 else 0)),
        (cx - hw, cy - hh + (r if r>0 else 0)),
    ]
    def M(a,b):
        return e1*a + e2*b
    if r <= 1e-9:
        # simple rectangle wire
        corners = [M(cx-hw, cy-hh), M(cx+hw, cy-hh), M(cx+hw, cy+hh), M(cx-hw, cy+hh)]
        edges = [Part.makeLine(corners[i], corners[(i+1)%4]) for i in range(4)]
        wire = Part.Wire(edges)
        face = Part.Face(wire)
        if face.Area <= 0:
            raise ValueError('rect face invalid')
        return face
    if 2*r > min(sx, sy) + 1e-9:
        raise ValueError('corner_radius too large')
    p = [M(*xy) for xy in pts2]
    s2 = 1/math.sqrt(2)
    arcs_mid = [
        M(cx + hw - r + r*s2, cy - hh + r - r*s2),
        M(cx + hw - r + r*s2, cy + hh - r + r*s2),
        M(cx - hw + r - r*s2, cy + hh - r + r*s2),
        M(cx - hw + r - r*s2, cy - hh + r - r*s2),
    ]
    edges = [
        Part.makeLine(p[0], p[1]),
        Part.Arc(p[1], arcs_mid[0], p[2]).toShape(),
        Part.makeLine(p[2], p[3]),
        Part.Arc(p[3], arcs_mid[1], p[4]).toShape(),
        Part.makeLine(p[4], p[5]),
        Part.Arc(p[5], arcs_mid[2], p[6]).toShape(),
        Part.makeLine(p[6], p[7]),
        Part.Arc(p[7], arcs_mid[3], p[0]).toShape(),
    ]
    wire = Part.Wire(edges)
    face = Part.Face(wire)
    if face.Area <= 0:
        raise ValueError('rounded rect face invalid')
    return face

def rounded_rect_prism(center, size_xy, corner_radius, axis=(0,0,1), length=20.0):
    cx, cy, cz = center
    sx, sy = size_xy
    r = float(corner_radius or 0)
    ax = V(*axis)
    if ax.Length < 1e-9:
        raise ValueError('axis zero')
    n = ax.normalize()
    # choose tangential basis
    if abs(abs(n.z) - 1) < 1e-9:
        e1, e2 = V(1,0,0), V(0,1,0)
        c1, c2 = cx, cy
        origin = V(0, 0, cz)  # plane at z=cz; face at relative 0 then shift
        # build face in XY at z=0 then translate
        face = _rounded_rect_face_2d(c1, c2, sx, sy, r, 0, e1, e2, n)
        face.translate(V(0,0,cz))
        solid = face.extrude(n * length)
        solid.translate(-n * (length/2.0))
    elif abs(abs(n.y) - 1) < 1e-9:
        e1, e2 = V(1,0,0), V(0,0,1)  # X, Z on face
        face = _rounded_rect_face_2d(cx, cz, sx, sy, r, 0, e1, e2, n)
        face.translate(V(0, cy, 0))
        solid = face.extrude(n * length)
        solid.translate(-n * (length/2.0))
    elif abs(abs(n.x) - 1) < 1e-9:
        e1, e2 = V(0,1,0), V(0,0,1)  # Y, Z
        face = _rounded_rect_face_2d(cy, cz, sx, sy, r, 0, e1, e2, n)
        face.translate(V(cx, 0, 0))
        solid = face.extrude(n * length)
        solid.translate(-n * (length/2.0))
    else:
        raise ValueError('rect_cutout_tool supports axis-aligned X/Y/Z only')
    if not solid.isValid() or not solid.Solids:
        raise ValueError('rounded rect solid invalid')
    return solid
