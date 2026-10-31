# v2.8.2 pipeline u_l_t7u (DEFAULT structure): vendored from 干画图3's /workspace/orders/box-180x420x175/addendum-tools (S-201-1-20261021-007-v1).
# v2.8.2 changes: hardcoded order/skill/tmp paths -> env SM_ORDER (order folder) + this folder; job features from release_config.json.
# nest DXF + PNG + PDF drawings for Revision E main package (addendum-venv python)
import sys,json,math,numpy as np,ezdxf,matplotlib
sys.path.insert(0,__import__('os').path.dirname(__import__('os').path.abspath(__file__)));import cfg
from pathlib import Path
matplotlib.use('Agg');import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from matplotlib import font_manager as fm
FP=fm.FontProperties(fname='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')
W=Path(sys.argv[1]);rep=json.load(open(W/'E_main_report.json'));proj=json.load(open(W/'projections.json'));mesh=json.load(open(W/'mesh.json'));flats=json.load(open(W/'flats.json'))
P=rep['params'];Lx,Wy,Hz=P['L'],P['W'],P['H']
# ---- nest ----
SH=(2440,1220);M=10;G=10
sizes={n:rep['parts'][n]['flat_size'] for n in ('U','L','LID')}
# box-180x420x175: try one row U | L | LID (as 001); fall back to two rows (row1 U | L, row2 LID above U) as in 002
_one={'U':(M,M),'L':(M+sizes['U'][0]+G,M),'LID':(M+sizes['U'][0]+G+sizes['L'][0]+G,M)}
if _one['LID'][0]+sizes['LID'][0]<=SH[0]-M:place=_one;LAYOUT='one row: U | L | LID'
else:place={'U':(M,M),'L':(M+sizes['U'][0]+G,M),'LID':(M,M+sizes['U'][1]+G)};LAYOUT='two rows on one sheet: row1 U | L, row2 LID above U (left of L)'
def _ov(a,b):
    (ax,ay),(bx,by)=place[a],place[b];sa,sb=sizes[a],sizes[b]
    return not (ax+sa[0]+G<=bx+1e-9 or bx+sb[0]+G<=ax+1e-9 or ay+sa[1]+G<=by+1e-9 or by+sb[1]+G<=ay+1e-9)
assert not any(_ov(a,b) for a,b in (('U','L'),('U','LID'),('L','LID')))
nest=ezdxf.new('R2010');nest.units=4;msp=nest.modelspace();nest.layers.add('CUT');nest.layers.add('SHEET',color=8)   # 003 t33u rule: NO BEND layer / no dashed lines in the NEST
msp.add_lwpolyline([(0,0),(SH[0],0),(SH[0],SH[1]),(0,SH[1])],close=True,dxfattribs={'layer':'SHEET'})
cnt={}
for n,(ox,oy) in place.items():
    for f,layer in ((W/f'{n}.dxf','CUT'),):
        src=ezdxf.readfile(f)
        for e in src.modelspace():
            c=e.copy();c.dxf.layer=layer;c.translate(ox,oy,0);msp.add_entity(c);cnt[(n,layer,e.dxftype())]=cnt.get((n,layer,e.dxftype()),0)+1
    sx,sy=sizes[n];assert ox+sx<=SH[0]-M and oy+sy<=SH[1]-M
nest.saveas(W/'NEST_SHEET01.dxf')
chk=ezdxf.readfile(W/'NEST_SHEET01.dxf');aud=chk.audit()
spacing=[place['L'][0]-(place['U'][0]+sizes['U'][0]),place['LID'][0]-(place['L'][0]+sizes['L'][0])] if LAYOUT.startswith('one') else [place['L'][0]-(place['U'][0]+sizes['U'][0]),place['LID'][1]-(place['U'][1]+sizes['U'][1]),place['L'][0]-(place['LID'][0]+sizes['LID'][0])]
_ents=list(chk.modelspace());_lt={e.dxf.get('linetype','BYLAYER').upper() for e in _ents}
nodash={'layers':sorted(l.dxf.name for l in chk.layers),'entity_layers':sorted({e.dxf.layer for e in _ents}),'bend_layer_present':'BEND' in [l.dxf.name for l in chk.layers],
 'bend_entities':sum(1 for e in _ents if e.dxf.layer.upper()=='BEND'),'entity_linetypes':sorted(_lt),'non_continuous_entities':sum(1 for e in _ents if e.dxf.get('linetype','BYLAYER').upper() not in ('BYLAYER','CONTINUOUS')),
 'layer_linetypes':{l.dxf.name:l.dxf.linetype for l in chk.layers},'types':{t:sum(1 for e in _ents if e.dxftype()==t) for t in sorted({e.dxftype() for e in _ents})}}
assert not nodash['bend_layer_present'] and nodash['bend_entities']==0 and nodash['non_continuous_entities']==0
assert all(v.upper()=='CONTINUOUS' for v in nodash['layer_linetypes'].values()),nodash['layer_linetypes']
nestrep={'sheet':SH,'margin':M,'gap_min':min(spacing),'placement':place,'flat_sizes':sizes,'entity_counts':{'|'.join(k):v for k,v in cnt.items()},'audit_errors':len(aud.errors),'used_length_x':max(place[n][0]+sizes[n][0] for n in place)+M,'used_height_y':max(place[n][1]+sizes[n][1] for n in place)+M,'sheets':1,
 'bbox_fit_check':{n:[place[n][0]+sizes[n][0]<=SH[0]-M,place[n][1]+sizes[n][1]<=SH[1]-M] for n in place},'layout':LAYOUT,'no_bend_no_dash':nodash}
json.dump(nestrep,open(W/'nest_report.json','w'),indent=1)
# ---- 3D render ----
def subdiv(T,maxe=12.0):
    # split long triangles (longest edge midpoint) so painter depth sort is reliable
    out=[];stack=[T]
    while stack:
        X=stack.pop()
        e=np.stack([np.linalg.norm(X[:,1]-X[:,0],axis=1),np.linalg.norm(X[:,2]-X[:,1],axis=1),np.linalg.norm(X[:,0]-X[:,2],axis=1)],1)
        big=e.max(1)>maxe;out.append(X[~big]);Y=X[big]
        if len(Y)==0:continue
        k=e[big].argmax(1);Y=np.stack([np.roll(Y[i],-k[i],axis=0) for i in range(len(Y))])  # longest edge = v0-v1
        m=(Y[:,0]+Y[:,1])/2
        stack.append(np.stack([Y[:,0],m,Y[:,2]],1));stack.append(np.stack([m,Y[:,1],Y[:,2]],1))
    return np.concatenate(out)
def tri(n,shift=(0,0,0)):
    V=np.array(mesh['parts'][n]['v'])+np.array(shift);F=np.array(mesh['parts'][n]['f']);return subdiv(V[F])
COL={'U':(0.62,0.70,0.80),'L':(0.80,0.72,0.55),'LID':(0.65,0.80,0.65)}
def draw(ax,items):
    Lt=np.array([0.4,-0.5,0.8]);Lt/=np.linalg.norm(Lt)
    TT=[];CC=[]
    for n,T in items:
        nn=np.cross(T[:,1]-T[:,0],T[:,2]-T[:,0]);nn/=(np.linalg.norm(nn,axis=1)[:,None]+1e-12);sh=0.35+0.6*np.abs(nn@Lt)
        TT.append(T);CC+= [tuple(np.array(COL[n])*s) for s in sh]
    ax.add_collection3d(Poly3DCollection(np.concatenate(TT),facecolors=CC,edgecolors=CC,linewidths=0.2))  # one collection -> per-triangle depth sort
def lims(ax,items,pad=5):
    A=np.concatenate([T.reshape(-1,3) for _,T in items]);lo=A.min(0)-pad;hi=A.max(0)+pad
    ax.set_xlim(lo[0],hi[0]);ax.set_ylim(lo[1],hi[1]);ax.set_zlim(lo[2],hi[2]);ax.set_box_aspect(tuple(hi-lo));ax.set_axis_off()
VER=cfg.VER
def fig_lid(path):
    h16=sorted(rep['lid']['roof_holes_16'],key=lambda q:q[1]);cx=h16[0][0];assert h16[1][0]==cx   # t13u: holes along Y on the left short edge
    fig=plt.figure(figsize=(14,9),dpi=110);ax=fig.add_subplot(111,projection='3d');it=[('LID',tri('LID'))];draw(ax,it);lims(ax,it)
    ax.view_init(elev=40,azim=-60)
    off=P['g']+P['t']
    ax.text2D(0.03,0.92,f"盖面圆孔 Ø{cfg.ROOF_D:g}×2，靠左短边(X=0侧，{Wy:.0f}边)，沿宽度方向排列，孔距{h16[1][1]-h16[0][1]:g}，关于Y={Wy/2:g}居中对称\n中心({cx:g},{h16[0][1]:g}) / ({cx:g},{h16[1][1]:g})（箱体外面基准）= 距盖左外边{cx+off:g}；孔边距盖外边{cx+off-cfg.ROOF_D/2:g}",fontproperties=FP,fontsize=11,color='darkred',ha='left',transform=ax.transAxes,zorder=100)
    ax.text2D(0.03,0.85,f"盖裙转角(同上一单)：长边裙({Lx:.0f})盖住短边裙端头，长裙外露端{('比短裙外面退%g' % rep['lid']['long_skirt_cover_setback_mm']) if rep['lid']['long_skirt_cover_setback_mm'] else '与短裙外面齐平（不退让）'}；短裙端顶死长裙内面（0缝）\n无把手（不开把手孔）",fontproperties=FP,fontsize=11,color='darkgreen',ha='left',transform=ax.transAxes,zorder=100)
    b=rep['parts']['LID']['bbox']
    fig.suptitle(f'{VER}  盖(LID) 轴测 | {cfg.MATERIAL_CN} t{P["t"]:g} | 盖外形 {b[3]-b[0]:.0f}×{b[4]-b[1]:.0f}×{b[5]-b[2]:.0f}（裙高{P["skirt"]:g}）| 确认稿',fontproperties=FP,fontsize=13)
    plt.savefig(path,bbox_inches='tight');plt.close(fig)
def fig_box(path,exploded):
    fig=plt.figure(figsize=(13,13),dpi=110);ax=fig.add_subplot(111,projection='3d')
    sh=mesh['shifts'] if exploded else {k:[0,0,0] for k in mesh['shifts']}
    it=[(n,tri(n,sh[n])) for n in ('U','L','LID')];draw(ax,it);lims(ax,it);ax.view_init(elev=26,azim=-55)
    lab={'U':'U 三面包(左/后/右)','L':'L 前板+底板(盖住U，'+(f"退{P.get('L_cover_setback',0.2):g}" if P.get('L_cover_setback',0.2) else '0缝不退让')+')','LID':f'LID 盖(含Ø{cfg.ROOF_D:g}×2孔，无把手)'}
    for n,T in it:
        A=T.reshape(-1,3);lo=A.min(0);hi=A.max(0)
        pos={'U':(hi[0]-10,hi[1]*0.5,lo[2]-30),'L':(lo[0]-10,lo[1]-20,lo[2]+60),'LID':(hi[0],lo[1],hi[2]+25)}[n]
        ax.text(*pos,lab[n],fontproperties=FP,fontsize=11,color='black',zorder=100)
    fig.suptitle(VER+('  爆炸轴测' if exploded else '  装配轴测')+f' — {Lx:g}×{Wy:g}×{Hz:g}(含盖) {cfg.MATERIAL_CN} t{P["t"]:g} — 确认稿',fontproperties=FP,fontsize=13)
    plt.savefig(path,bbox_inches='tight');plt.close(fig)
out=Path(sys.argv[2]);out.mkdir(exist_ok=True)
fig_lid(out/'LID_iso.png');fig_box(out/'EXPLODED_iso.png',True);fig_box(out/'ASSEMBLY_iso.png',False)
print(json.dumps(nestrep,indent=1))
