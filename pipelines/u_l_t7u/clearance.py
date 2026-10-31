# v2.8.2 pipeline u_l_t7u (DEFAULT structure): vendored from 干画图3's /workspace/orders/box-180x420x175/addendum-tools (S-201-1-20261021-007-v1).
# v2.8.2 changes: hardcoded order/skill/tmp paths -> env SM_ORDER (order folder) + this folder; job features from release_config.json.
# hole clearances in flat-pattern coordinates (CUT dxf + BEND dxf), same format as 005 logs/clearance*.json (addendum-venv python)
import sys,json,math,ezdxf
sys.path.insert(0,__import__('os').path.dirname(__import__('os').path.abspath(__file__)));import cfg
RD=cfg.ROOF_D;RR=RD/2
from pathlib import Path
W=Path(sys.argv[1]);rep=json.load(open(W/'E_main_report.json'));P=rep['params']
half=math.pi/2*(P['Ri']+P['K_ANSI']*P['t'])/2
def segd(p,a,b):
    ax,ay=a;bx,by=b;dx,dy=bx-ax,by-ay;L2=dx*dx+dy*dy;u=max(0,min(1,((p[0]-ax)*dx+(p[1]-ay)*dy)/L2));return math.hypot(p[0]-ax-u*dx,p[1]-ay-u*dy)
def outer_segs(msp):
    segs=[]
    for e in msp:
        if e.dxftype()=='LINE':segs.append(((e.dxf.start.x,e.dxf.start.y),(e.dxf.end.x,e.dxf.end.y)))
        elif e.dxftype()=='ARC':
            c=e.dxf.center;r=e.dxf.radius;a0=math.radians(e.dxf.start_angle);sw=(math.radians(e.dxf.end_angle)-a0)%(2*math.pi);n=24
            pts=[(c.x+r*math.cos(a0+sw*i/n),c.y+r*math.sin(a0+sw*i/n)) for i in range(n+1)];segs+=list(zip(pts[:-1],pts[1:]))
    return segs
out={'bend_half_zone_mm':half,'note':'flat-pattern coordinates; to_bend_tangent = edge-to-bend-zone edge; to_nearest_hole = edge-to-edge'}
for n in ('U','L','LID'):
    msp=ezdxf.readfile(W/f'{n}.dxf').modelspace();bl=[((e.dxf.start.x,e.dxf.start.y),(e.dxf.end.x,e.dxf.end.y)) for e in ezdxf.readfile(W/f'{n}_BEND.dxf').modelspace()]
    segs=outer_segs(msp);cs=[(e.dxf.center.x,e.dxf.center.y,e.dxf.radius) for e in msp if e.dxftype()=='CIRCLE']
    hs=[]
    for i,(x,y,r) in enumerate(cs):
        hs.append({'d':round(2*r,4),'c':[round(x,2),round(y,2)],'to_bend_tangent':round(min(segd((x,y),a,b) for a,b in bl)-half-r,2),'to_edge':round(min(segd((x,y),a,b) for a,b in segs)-r,2),
                   'to_nearest_hole':round(min(math.hypot(x-x2,y-y2)-r-r2 for j,(x2,y2,r2) in enumerate(cs) if j!=i),2)})
    out[n]={'holes':hs,'min_to_bend_tangent':min(h['to_bend_tangent'] for h in hs),'min_to_edge':min(h['to_edge'] for h in hs),'min_hole_to_hole':min(h['to_nearest_hole'] for h in hs)}
L=out['LID']['holes'];g=lambda d:[h for h in L if abs(h['d']-d)<1e-6]
o16,h66,s45=g(RD),g(6.6),g(4.5)
dd=lambda a,b:math.hypot(a['c'][0]-b['c'][0],a['c'][1]-b['c'][1])-a['d']/2-b['d']/2
out['LID'].update({'Oroof_to_bend_tangent':min(h['to_bend_tangent'] for h in o16),'Oroof_to_outer_edge':min(h['to_edge'] for h in o16),
  'Oroof_to_Oroof_edge':round(dd(o16[0],o16[1]),2),'Oroof_to_nearest_skirt_hole_edge':round(min(dd(a,b) for a in o16 for b in s45),2),
  'handle_holes':0,'skirt_hole_to_bend_tangent_min':min(h['to_bend_tangent'] for h in s45)})
assert not h66,'no handle holes expected'
# M4 (O3.3 tapped) body holes and O4.5 skirt holes vs bend LINES (flat bend centre line) and bend tangent; request: >=3 mm from bend line if possible
def bendcheck(n,d):
    bl=[((e.dxf.start.x,e.dxf.start.y),(e.dxf.end.x,e.dxf.end.y)) for e in ezdxf.readfile(W/f'{n}_BEND.dxf').modelspace()]
    hs=[h for h in out[n]['holes'] if abs(h['d']-d)<1e-6];r=d/2
    cl=[min(segd(tuple(h['c']),a,b) for a,b in bl) for h in hs]
    return {'holes':len(hs),'min_centre_to_bend_line':round(min(cl),2),'min_edge_to_bend_line':round(min(cl)-r,2),'min_edge_to_bend_tangent':min(h['to_bend_tangent'] for h in hs),
            'rule_edge_to_bend_line_ge_3':min(cl)-r>=3.0}
out['bend_margin_check']={'U_M4':bendcheck('U',3.3),'L_M4':bendcheck('L',3.3),'LID_skirt_O4.5':bendcheck('LID',4.5),'LID_roof_O12':bendcheck('LID',RD)}
# box-coordinate cross-check (formed LID): O16 edge to inner face of skirts / roof bend tangent
lh=rep['lid']['roof_holes_16'];g_,t,ri=P['g'],P['t'],P['Ri']
roof_flat_x0=-g_-t+t+ri  # roof flat starts after outer skirt + bend: x=-g-t+(t+ri) outer-radius end -> roof bend tangent (box coords)
lh=sorted(lh);bt=-g_-t+t+ri   # roof bend tangent (box coords) at x=0.3 / y=0.3 from box datum; mirror on far sides
Lb,Wb=P['L'],P['W']
out['LID_box_coords']={'rev':'t7u-corner','roof_hole_d':RD,'Oroof_centres':lh,'Oroof_pitch_y':round(lh[1][1]-lh[0][1],3),'Oroof_same_x':lh[0][0]==lh[1][0],
  'Oroof_edge_xmin':min(c[0] for c in lh)-RR,'Oroof_edge_ymin':min(c[1] for c in lh)-RR,'lid_outer_xmin':-g_-t,'lid_outer_ymin':-g_-t,
  'Oroof_edge_to_lid_outer_face_x':min(c[0] for c in lh)-RR-(-g_-t),'Oroof_edge_to_lid_outer_face_y':min(c[1] for c in lh)-RR-(-g_-t),
  'Oroof_edge_to_roof_bend_tangent_x':round(min(c[0] for c in lh)-RR-bt,3),'Oroof_edge_to_roof_bend_tangent_y':round(min(c[1] for c in lh)-RR-bt,3),
  'Oroof_edge_to_body_inner_wall_x':round(min(c[0] for c in lh)-RR-t,3),'Oroof_edge_to_body_inner_wall_y':round(min(c[1] for c in lh)-RR-t,3),
  'Oroof_edge_to_Oroof_edge':round(math.hypot(lh[1][0]-lh[0][0],lh[1][1]-lh[0][1])-RD,3),
  'Oroof_x_centres':[c[0] for c in lh],'Oroof_pitch_x':round(lh[1][0]-lh[0][0],3),'Oroof_same_y':lh[0][1]==lh[1][1],'Oroof_symmetric_about_L_half':abs((lh[0][0]+lh[1][0])/2-Lb/2)<1e-9,
  'Oroof_centre_to_lid_outer_face_y':lh[0][1]-(-g_-t),
  # t13u: holes on the left SHORT edge, along Y
  'Oroof_y_centres':[c[1] for c in lh],'Oroof_pitch_y_t13u':round(lh[1][1]-lh[0][1],3),'Oroof_symmetric_about_W_half':abs((lh[0][1]+lh[1][1])/2-Wb/2)<1e-9,
  'lid_outer_y_range':[-g_-t,Wb+g_+t],'lid_outer_width_y':Wb+2*(g_+t),'Oroof_symmetric_about_lid_outer_centre_y':abs((lh[0][1]+lh[1][1])/2-((-g_-t)+(Wb+g_+t))/2)<1e-9,
  'Oroof_centre_to_lid_outer_face_x':lh[0][0]-(-g_-t),
  'Oroof_edge_to_lid_front_outer_face_y':min(c[1] for c in lh)-RR-(-g_-t),'Oroof_edge_to_lid_back_outer_face_y':(Wb+g_+t)-max(c[1] for c in lh)-RR}
bh=[h for h in json.load(open(cfg.B/'evidence_src/resolved_job.json'))['holes'] if h['part_id'] in ('U','L')]
hb=P['body_height'];zc=bh[0]['point'][2]
out['body_M4_box_coords']={'body_fixing_hole_centre_z':zc,'body_top_z_U':hb,'centre_below_body_top':round(hb-zc,3),'hole_edge_to_body_top_edge':round(hb-zc-3.3/2,3),
  'no_rim_flange':'body top edge is a plain cut edge (no bend near the M4 holes)',
  'x_positions_long_walls':sorted({h['point'][0] for h in bh if abs(h['axis'][1])>.5}),'y_positions_short_walls':sorted({h['point'][1] for h in bh if abs(h['axis'][0])>.5}),
  'min_centre_to_vertical_corner_outer_face':min(min(h['point'][0],Lb-h['point'][0]) if abs(h['axis'][1])>.5 else min(h['point'][1],Wb-h['point'][1]) for h in bh)}
json.dump(out,open(sys.argv[2],'w'),indent=1);print(json.dumps({k:v for k,v in out['LID'].items() if k!='holes'},indent=1));print(json.dumps(out['LID_box_coords'],indent=1));print(json.dumps(out['bend_margin_check'],indent=1));print(json.dumps(out['body_M4_box_coords'],indent=1))
for n in ('U','L'):print(n,{k:v for k,v in out[n].items() if k!='holes'})
