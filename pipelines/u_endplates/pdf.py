# v2.8.3 pipeline u_endplates PDF = TEXT TEMPLATE vendored from order box-400x220x150 (S-201-1-20261021-001-v1, t46u: 03 corners gap 0, outer end plates).
# Layout + wording validated ONLY for that geometry and corner_gap=0 (incl. its native03 gap-0 finding); run.py refuses other jobs (write job-specific text).
# Outbound confirmation drawings do not use this file. The only PDF pipeline is
# assets/bend-pdf-golden-001-visual/engine_u_endplates.py.
# A3 all-Chinese confirmation/bend PDF (4 pages) + iso renders (addendum-venv python)
import sys
raise SystemExit('pdf.py is not an outbound PDF pipeline; use assets/bend-pdf-golden-001-visual/engine_u_endplates.py')
import json,math,numpy as np,matplotlib,datetime
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent));from cfg import *
matplotlib.use('Agg');import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from matplotlib import font_manager as fm
from matplotlib.patches import Rectangle,Circle,FancyBboxPatch
matplotlib.rcParams['pdf.fonttype']=42
FPATH='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc';fm.fontManager.addfont(FPATH)
FP=fm.FontProperties(fname=FPATH);matplotlib.rcParams['font.family']='Noto Sans CJK SC';matplotlib.rcParams['axes.unicode_minus']=False
W_=Path(sys.argv[1]);R=Path(sys.argv[2])
rep=json.load(open(W_/'report.json'));proj=json.load(open(W_/'projections.json'));mesh=json.load(open(W_/'mesh.json'))
# v2.8.20 / t99u: force hole_to_lid_skirt findings onto PDF p1 when present
_conf=[];_cp=W_/'conflicts.json'
if _cp.exists():
    try: _conf=json.load(open(_cp))
    except Exception: _conf=[]
try:
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
    from conflict_checks import lid_skirt_force_lines_cn
    _SKIRT_LINES=lid_skirt_force_lines_cn(_conf)
except Exception:
    _SKIRT_LINES=[f"[{x.get('level')}] {x.get('msg_cn')}" for x in _conf if x.get('id')=='hole_to_lid_skirt' and x.get('level') in ('WARN','ERROR')]
flats=json.load(open(W_/'flats.json'));sec=json.load(open(W_/'section_mid.json'));dchk=json.load(open(W_/'dxf_checks.json'))
P=rep['parts'];G=rep['gap_check']
NOTCH_LID=skirt-ro+BA/2
csec=json.load(open(W_/'corner_sections.json'));cmesh=json.load(open(W_/'corner_mesh.json'))
BGL=lambda outer: outer-OSSB+BA/2      # edge -> bend-line(centre of BA) distance
# ---------- iso renders ----------
def subdiv(T,maxe=14.0):
    out=[];st=[T]
    while st:
        X=st.pop();e=np.stack([np.linalg.norm(X[:,1]-X[:,0],axis=1),np.linalg.norm(X[:,2]-X[:,1],axis=1),np.linalg.norm(X[:,0]-X[:,2],axis=1)],1)
        big=e.max(1)>maxe;out.append(X[~big]);Y=X[big]
        if len(Y)==0:continue
        k=e[big].argmax(1);Y=np.stack([np.roll(Y[i],-k[i],axis=0) for i in range(len(Y))]);m=(Y[:,0]+Y[:,1])/2
        st.append(np.stack([Y[:,0],m,Y[:,2]],1));st.append(np.stack([m,Y[:,1],Y[:,2]],1))
    return np.concatenate(out)
COL={'U':(0.62,0.70,0.80),'END_L':(0.80,0.72,0.55),'END_R':(0.80,0.72,0.55),'LID':(0.65,0.80,0.65),'HANDLE_REF_L':(0.35,0.35,0.38),'HANDLE_REF_R':(0.35,0.35,0.38)}
def iso(path,exploded,elev=24,azim=-58,zones=False):
    fig=plt.figure(figsize=(9,7),dpi=130);ax=fig.add_subplot(111,projection='3d')
    sh=mesh['shifts'] if exploded else {k:[0,0,0] for k in mesh['shifts']}
    TT=[];CC=[];Lt=np.array([0.4,-0.5,0.8]);Lt/=np.linalg.norm(Lt)
    for n in mesh['parts']:
        Vv=np.array(mesh['parts'][n]['v'])+np.array(sh[n]);T=subdiv(Vv[np.array(mesh['parts'][n]['f'])])
        nn=np.cross(T[:,1]-T[:,0],T[:,2]-T[:,0]);nn/=(np.linalg.norm(nn,axis=1)[:,None]+1e-12);s=0.35+0.6*np.abs(nn@Lt)
        TT.append(T);CC+=[tuple(np.array(COL[n])*x) for x in s]
    ax.add_collection3d(Poly3DCollection(np.concatenate(TT),facecolors=CC,edgecolors=CC,linewidths=0.15))
    A=np.concatenate([T.reshape(-1,3) for T in TT]);lo=A.min(0)-5;hi=A.max(0)+5
    ax.set_xlim(lo[0],hi[0]);ax.set_ylim(lo[1],hi[1]);ax.set_zlim(lo[2],hi[2]);ax.set_box_aspect(tuple(hi-lo));ax.set_axis_off();ax.view_init(elev=elev,azim=azim)
    plt.savefig(path,bbox_inches='tight',pad_inches=0.02);plt.close(fig)
iso(W_/'iso_asm.png',False,zones=True);iso(W_/'iso_exp.png',True,zones=True)
def iso_corner(path,tag,elev,azim,title=None):
    fig=plt.figure(figsize=(6,6),dpi=150);ax=fig.add_subplot(111,projection='3d')
    TT=[];CC=[];Lt=np.array([-0.5,-0.6,0.7]);Lt/=np.linalg.norm(Lt)
    col={'U':(0.55,0.65,0.82),'END_L':(0.85,0.70,0.45),'LID':(0.55,0.80,0.55)}
    for n,m in cmesh[tag].items():
        Vv=np.array(m['v']);T=subdiv(Vv[np.array(m['f'])],maxe=3.0)
        nn=np.cross(T[:,1]-T[:,0],T[:,2]-T[:,0]);nn/=(np.linalg.norm(nn,axis=1)[:,None]+1e-12);s_=0.35+0.6*np.abs(nn@Lt)
        TT.append(T);CC+=[tuple(np.array(col[n])*x) for x in s_]
    ax.add_collection3d(Poly3DCollection(np.concatenate(TT),facecolors=CC,edgecolors=CC,linewidths=0.1))
    A=np.concatenate([T.reshape(-1,3) for T in TT]);lo=A.min(0);hi=A.max(0)
    ax.set_xlim(lo[0],hi[0]);ax.set_ylim(lo[1],hi[1]);ax.set_zlim(lo[2],hi[2]);ax.set_box_aspect(tuple(hi-lo));ax.set_axis_off();ax.view_init(elev=elev,azim=azim)
    if title:fig.text(0.02,0.96,title,fontsize=10,weight='bold')
    plt.savefig(path,bbox_inches='tight',pad_inches=0.02);plt.close(fig)
iso_corner(W_/'iso_corner_bottom.png','bottom',-28,-130)
iso_corner(W_/'iso_corner_top.png','top',22,-130)
iso_corner(W_/'iso_corner_lid03.png','lid03',28,-135)
C3=rep['corner03'];CL=json.load(open(W_/'corner03_closure_sections.json'));N3=json.load(open(W_/'native03.json'));N3R=json.load(open(W_/'native03_untrimmed_native_unfold.json'))
SL=max(v['max_gap_mm'] for v in CL.values());SLZ=CL['X0Y0']['open_z_range']
# ---------- drawing helpers ----------
PW,PH=420,297
RED='#c00000';BLU='#0040a0';PH_C='#d04000'
def page(n,title):
    fig=plt.figure(figsize=(PW/25.4,PH/25.4));ax=fig.add_axes([0,0,1,1]);ax.set_xlim(0,PW);ax.set_ylim(0,PH);ax.axis('off')
    ax.add_patch(Rectangle((5,5),PW-10,PH-10,fill=False,lw=1.2))
    ax.text(PW/2,PH/2,'客户确认图 — 非生产放行',fontsize=80,color=RED,alpha=0.09,ha='center',va='center',rotation=20,zorder=0)
    ax.text(10,PH-14,f'{VER}   客户确认图 — 非生产放行',fontsize=17,color=RED,weight='bold')
    ax.text(10,PH-22,title,fontsize=11)
    ax.text(PW-10,PH-14,'201不锈钢   板厚 t = 1.0 mm',fontsize=15,ha='right',weight='bold',color=BLU)
    ax.text(PW-10,PH-22,'箱体外形 400×220（已确认）  含盖总高 150（已确认）',fontsize=11,ha='right',weight='bold',color=BLU)
    x0,y0=PW-135,5
    ax.add_patch(Rectangle((x0,y0),130,30,fill=True,fc='white',ec='k',lw=1,zorder=5))
    rows=[f'图号/版本：{VER}','名称：400×220×150 钣金箱（U形底壳+两外封端板+可拆上盖）','材料：201不锈钢  t1.0   单位 mm   比例见各视图',f'阶段：客户确认稿（production_release=false）  第 {n}/4 页','计算检查：native03缝0未通过(见第4页) / 实物试折试装：未进行   2026-10-26 (UTC+8)']
    for i,r in enumerate(rows):ax.text(x0+2,y0+25.5-i*5.6,r,fontsize=7.2,zorder=6)
    return fig,ax
def vax(fig,x,y,xlim,ylim,s,title=None,tfs=9):
    w=(xlim[1]-xlim[0])*s;h=(ylim[1]-ylim[0])*s
    a=fig.add_axes([x/PW,y/PH,w/PW,h/PH]);a.set_xlim(*xlim);a.set_ylim(*ylim);a.axis('off');a.s=s
    if title:fig.axes[0].text(x,y+h+1.5,title,fontsize=tfs,weight='bold')
    return a
def pl(ax,poly,fn=lambda a,b:(a,b),**k):
    a=np.array([fn(p[0],p[1]) for p in poly]);ax.plot(a[:,0],a[:,1],**k)
def view(ax,name,v,fn,lw=0.7,hidden=True):
    for p in proj[name][v]['vis']:pl(ax,p,fn,color='k',lw=lw)
    if hidden:
        for p in proj[name][v]['hid']:pl(ax,p,fn,color='0.55',lw=0.35,ls=(0,(3,2)))
def dimh(ax,x1,x2,y,yr1,yr2,s,fs=7,c='k'):
    o=1.0/ax.s
    for x,yr in ((x1,yr1),(x2,yr2)):ax.plot([x,x],[yr,y+(o if y>yr else -o)],color=c,lw=0.35)
    ax.annotate('',xy=(x1,y),xytext=(x2,y),arrowprops=dict(arrowstyle='<|-|>',lw=0.5,color=c,mutation_scale=6,shrinkA=0,shrinkB=0))
    ax.text((x1+x2)/2,y+0.4/ax.s,s,fontsize=fs,ha='center',va='bottom',color=c)
def dimv(ax,y1,y2,x,xr1,xr2,s,fs=7,c='k'):
    o=1.0/ax.s
    for y,xr in ((y1,xr1),(y2,xr2)):ax.plot([xr,x+(o if x>xr else -o)],[y,y],color=c,lw=0.35)
    ax.annotate('',xy=(x,y1),xytext=(x,y2),arrowprops=dict(arrowstyle='<|-|>',lw=0.5,color=c,mutation_scale=6,shrinkA=0,shrinkB=0))
    ax.text(x-0.4/ax.s,(y1+y2)/2,s,fontsize=fs,ha='right',va='center',rotation=90,color=c)
def box(ax,x,y,w,h,lines,fs=7.5,title=None,ec='k',tc='k'):
    fs=fs*1.12
    ax.add_patch(Rectangle((x,y),w,h,fill=True,fc='white',ec=ec,lw=0.8,zorder=2))
    yy=y+h-4.5
    if title:ax.text(x+2,yy,title,fontsize=fs+1.5,weight='bold',color=ec if ec!='k' else 'k',zorder=3);yy-=fs*0.62
    for l in lines:
        col=tc
        if isinstance(l,tuple):l,col=l
        ax.text(x+2,yy,l,fontsize=fs,zorder=3,color=col);yy-=fs*0.56
def img(fig,path,x,y,w,h):
    a=fig.add_axes([x/PW,y/PH,w/PW,h/PH]);a.imshow(plt.imread(path));a.axis('off')
def flatdraw(ax,n):
    for w in flats[n]['wires']:pl(ax,w+[w[0]],color='k',lw=0.7)
    for b in P[n]['bend_lines']:pl(ax,b,color=RED,lw=0.7,ls=(0,(6,2,1,2)))
HH=handle_holes()
def hdl(ax,body=True,only=None,lab=False):
    for h in HH:
        if only and h['handle']!=only:continue
        ax.add_patch(Circle((h['x'],h['y']),D_HDL/2,fill=False,ec=BLU,lw=0.8));ax.plot([h['x']-5,h['x']+5],[h['y']]*2,color=BLU,lw=0.3);ax.plot([h['x']]*2,[h['y']-5,h['y']+5],color=BLU,lw=0.3)
        if lab:ax.text(h['x']+4,h['y']+(4 if h['y']>110 else -7),f"{h['id']}\n({h['x']:g},{h['y']:g})",fontsize=5.8,color=BLU)
    if body:
        for cx in HANDLE_CX:
            if only and ((cx<L/2)!=(only=='L')):continue
            ax.add_patch(Rectangle((cx-HREF_BX/2,HANDLE_CY-HREF_BY/2),HREF_BX,HREF_BY,fill=False,ec='0.45',ls=(0,(8,2,2,2,2,2)),lw=0.6))
            ax.add_patch(Rectangle((cx-5,HANDLE_CY-50),10,100,fill=False,ec='0.45',ls=(0,(8,2,2,2,2,2)),lw=0.5))
            ax.text(cx,HANDLE_CY+HREF_BY/2+2,'把手参考包络（非实物）',fontsize=5.5,color='0.35',ha='center')
pdf_path=R/f'{VER}_客户确认图_折弯工艺PDF_A3_4页.pdf'
co=rep['hole_coaxial'];coax=all(c['axis_line_material_lid_mm']==0 and c['axis_line_material_body_mm']==0 and c['lid_open_at_r']==0 and c['body_open_at_r']==0 and c['body_material_at_r_plus']>0 and c['lid_material_at_r_plus']>0 for c in co)
cs=dchk['dxf_checks'];allpass=all(c['pass'] for c in cs);ints=rep['intersections_mm3']
off=P['LID']['flat_size'][0]/2-L/2
with PdfPages(pdf_path) as pdf:
    # ================= PAGE 1 =================
    fig,ax=page(1,'第1页  总装确认图：三视图（第一角投影 1:2.8）、轴测、关键尺寸、盖顶把手（铆接，M6孔Ø6.6）')
    s=0.36
    a=vax(fig,14,168,(-45,430),(-28,215),s,'主视图（从前侧 Y=0 看）1:2.8   灰色=把手参考包络（非实物，待确认）')
    F1=lambda u,v:(v,-u);view(a,'ASSEMBLY','front',F1)
    dimv(a,0,150,-25,-1.5,-1.5,'150 含盖总高（已确认）');dimv(a,0,Hb,418,400,400,f'{Hb:g} 箱体高');dimv(a,135,150,408,401.5,401.5,'15')
    dimh(a,-1.5,401.5,205,150,150,'403 盖外长');dimh(a,0,400,-18,0,0,'400 箱体外长（已确认）')
    dimv(a,150,196,40,55,55,'把手包络≈46 参考',fs=6,c='0.35')
    for x in LONG_X:a.plot([x],[ZH],'+',color=BLU,ms=7,mew=1)
    for x1,x2,tx in ((0,50,'50'),(50,200,'150'),(200,350,'150'),(350,400,'50')):dimh(a,x1,x2,120,ZH,ZH,tx,fs=6.5,c=BLU)
    a.text(60,95,'长边每侧 M4×3：盖Ø4.5过孔 / 箱体Ø3.3攻M4\n孔心距盖顶 7.5（Z=142.5）',fontsize=7,color=BLU)
    a.text(60,40,'盖裙下沿 Z=135；箱体顶边 Z=148.8；顶隙 q=0.2',fontsize=7)
    a=vax(fig,14,40,(-45,430),(-45,262),s,'俯视图（从上看）1:2.8   盖顶把手×2 铆接（每只Ø6.6×4）')
    view(a,'ASSEMBLY','top',lambda u,v:(u,v),hidden=False);hdl(a,body=False)
    dimh(a,-1.5,401.5,-25,-1.5,-1.5,'403 盖外长');dimv(a,-1.5,221.5,-22,-1.5,-1.5,'223 盖外宽')
    a.plot([200,200],[-12,236],color=RED,lw=0.5,ls='-.');a.text(200,238,'对称中心 X=200',fontsize=7,color=RED,ha='center')
    dimh(a,80,320,250,165,165,'把手中心距 240（中心X=80 / 320，Y=110）',fs=7)
    a.text(110,15,'两把手铆接于盖顶，关于X=200镜像对称、Y居中；\n横跨220方向，宽排(85)朝盖中心，两把手相向。\n孔型同前单：Ø6.6×4/只，85/62/排距30（M6）',fontsize=6.6,color=BLU)
    a=vax(fig,198,168,(-40,250),(-28,215),s,'左视图（外封端板侧）1:2.8')
    view(a,'ASSEMBLY','right',lambda u,v:(-v,u))
    dimh(a,-1.5,221.5,205,150,150,'223 盖外宽');dimh(a,0,220,-18,0,0,'220 箱体外宽（已确认）')
    for y in SHORT_Y:a.plot([y],[ZH],'+',color=BLU,ms=7,mew=1)
    for x1,x2,tx in ((0,50,'50'),(50,170,'120'),(170,220,'50')):dimh(a,x1,x2,120,ZH,ZH,tx,fs=6.5,c=BLU)
    a.text(15,60,'短边每侧 M4×2（孔在端板）\n端板=整块外封板，盖住U端面\n外轮廓220×148.8，底角R1.8',fontsize=7,color=BLU)
    img(fig,W_/'iso_asm.png',318,168,96,84);ax.text(320,254,'装配轴测（深灰=把手参考包络）',fontsize=8.5,weight='bold')
    img(fig,W_/'iso_exp.png',318,40,96,108);ax.text(320,150,'爆炸轴测（各件仅平移）',fontsize=8.5,weight='bold')
    box(ax,196,40,118,124,[('尺寸口径（已确认）',RED),'· 400×220 = 箱体外尺寸；150 = 含盖总高',f'· 箱体高 = 150 − 1.0 − 顶隙{q:g} = {Hb:g}','· 盖外形 403×223×15；盖内 401×221',
        ('结构 / 零件拆分',BLU),'· 件1 U形底壳：底+两长侧壁（弯线沿400）','· 件2/3 外封端板：零折平板，盖住U端面，','  拼缝0、不退让、上边齐口；接合待确认','· 件4 上盖：四边裙15，03斜角折弯收口(缝0)，','  M4螺钉四边固定共10组','· 把手×2：盖顶铆接，Ø6.6×8（M6孔）',
        ('不做',BLU),'· 无电源孔、无百叶、无PG7/PG9/线孔',('待确认',RED),'· 把手型号；铆钉型号（孔Ø6.6 M6过孔=默认）','· 盖角缝0：native03未通过（见第4页），定方案','· 端板接合（无搭接，不能点焊）',('· M4直接攻1.0板仅约1扣、易滑牙（第4页）；',RED),('  压铆/拉铆/点焊螺母替代：待确认',RED)]+([ (ln,RED) for ln in _SKIRT_LINES ] if _SKIRT_LINES else []),title='关键参数',fs=7.0)
    pdf.savefig(fig);plt.close(fig)
    # ================= PAGE 2 =================
    fig,ax=page(2,'第2页  箱体零件：件1 U形底壳、件2/3 外封端板（端板盖U，拼缝0，完全遮盖）—— 截面、展开、端角局部、折弯参数')
    a=vax(fig,14,196,(-35,250),(-25,165),0.36,'件1 U形底壳 截面A-A（X=200，过孔S2/N2）1:2.8')
    for w in sec['U']:pl(a,w,color='k',lw=0.8)
    dimh(a,0,W,-15,0,0,'220 外');dimv(a,0,Hb,-15,0,0,f'{Hb:g} 外');dimh(a,1,219,20,1,1,'218 内',fs=6.5)
    a.text(110,40,'B1/B2 侧壁向上(向内)折90°\n内R0.8（外R1.8）',fontsize=6.8,color=RED,ha='center')
    a.annotate(f'Ø3.3攻M4，孔心距顶{Hb-ZH:.1f}',xy=(W,ZH),xytext=(120,105),fontsize=6.5,color=BLU,arrowprops=dict(arrowstyle='->',color=BLU,lw=0.5))
    fx,fy=P['U']['flat_size'];b1=P['U']['bend_lines'][0][0][1];b2=P['U']['bend_lines'][1][0][1]
    a=vax(fig,118,90,(-35,440),(-25,530),0.3,f'件1 U 展开 {fx:.2f}×{fy:.2f}（外表面朝读者，1:3.3）')
    flatdraw(a,'U');dimh(a,0,fx,-15,0,0,f'{fx:.2f}（=400−2×端板t1）');dimv(a,0,fy,-15,0,0,f'{fy:.2f}')
    dimv(a,0,b1,425,fx,fx,f'{b1:.2f}',c=RED);dimv(a,b1,b2,425,fx,fx,f'{b2-b1:.2f}',c=RED);dimv(a,b2,fy,425,fx,fx,f'{fy-b2:.2f}',c=RED)
    a.text(200,b1+5,'B1  向内折90°  内R0.8',fontsize=7,color=RED,ha='center');a.text(200,b2+5,'B2  向内折90°  内R0.8',fontsize=7,color=RED,ha='center')
    ux=sorted({round(c[0],3) for c in P['U']['flat_circles']})
    for x1,x2 in zip([0]+ux,ux+[fx]):dimh(a,x1,x2,40,6.3,6.3,f'{x2-x1:g}',fs=6,c=BLU)
    a.text(60,60,'Ø3.3×3（攻M4）孔心距边6.30（两长边各3）\n展开X=49/199/349 = 箱体X50/200/350 − 1（U始于X=1）',fontsize=6.2,color=BLU)
    ex_,ey_=P['END_L']['flat_size']
    a=vax(fig,262,180,(-30,240),(-22,165),0.36,f'件2 左端板（件3相同）零折平板 {ex_:g}×{ey_:g}  1:2.8')
    flatdraw(a,'END_L');dimh(a,0,ex_,-14,0,0,f'{ex_:g}（=U外宽）');dimv(a,0,ey_,-14,0,0,f'{ey_:g}（=U外高，上边齐口）')
    for x1,x2 in ((0,50),(50,170),(170,220)):dimh(a,x1,x2,ey_+8,ZH,ZH,f'{x2-x1:g}',fs=6.3,c=BLU)
    dimv(a,ZH,ey_,232,220,220,f'{ey_-ZH:.1f}',fs=6,c=BLU);dimv(a,0,ZH,232,220,220,f'{ZH:g}',fs=6,c=BLU)
    a.text(20,70,'Ø3.3×2 攻M4（短边固定孔，单层）\n底角 R1.8 = U外圆角，圆心(1.8,1.8)同心\n无折弯、无回边；激光切割后去毛刺',fontsize=6.5,color=RED)
    a.annotate('R1.8',xy=(0.53,0.53),xytext=(18,22),fontsize=6.5,color=RED,arrowprops=dict(arrowstyle='->',color=RED,lw=0.5))
    # end-cover corner details
    a=vax(fig,262,104,(-2.5,9),(-2.5,9),5.0,'局部IV 端角俯剖（Z=74）5:1：端板盖住U侧壁端面',tfs=7.5)
    for n_,c in (('END_L','#b07000'),('U','#3050a0')):
        for w in csec[n_]['XY_Z74']:pl(a,w,color=c,lw=1.2)
    a.fill([0,1,1,0],[-2.3,-2.3,8.8,8.8],color='#e8c890',alpha=0.5,lw=0);a.fill([1,8.8,8.8,1],[0,0,1,1],color='#b0c4e8',alpha=0.6,lw=0)
    dimh(a,0,1,-1.5,0,0,'t1',fs=6,c='#b07000');dimv(a,0,1,8.2,1,1,'t1',fs=6,c='#3050a0')
    a.text(2.2,3.0,'拼缝 0（U端面顶死端板内面）\n端板外面 X=0 = 箱体外端\nU侧壁外面 Y=0 与端板侧边齐平\n无外露U端边',fontsize=5.8,color=RED)
    a.text(-2.4,8.3,'端板',fontsize=6,color='#b07000');a.text(4.5,-1.2,'U侧壁',fontsize=6,color='#3050a0')
    a=vax(fig,330,104,(-2.5,9),(-2.5,9),5.0,'局部V 底角（YZ）5:1：端板R1.8与U外圆同心',tfs=7.5)
    for w in csec['END_L']['YZ_face']:pl(a,w,color='#b07000',lw=2.2)
    for w in csec['U']['YZ_X200']:pl(a,w,color='#3050a0',lw=0.9,ls=(0,(3,1.5)))
    a.plot([1.8],[1.8],'+',color=RED,ms=8);a.text(2.2,2.3,'圆心(1.8,1.8)\n端板外R1.8 = U外R1.8\n端板轮廓 = U外轮廓',fontsize=5.8,color=RED)
    a.text(3.5,-1.6,'实线=端板外形  虚线=U截面',fontsize=5.6)
    a=vax(fig,262,40,(-3,10),(141.8,151.5),5.0,'局部VI 端顶纵剖（Y=110）5:1：端板上边齐口、盖裙间隙',tfs=7.5)
    for n_,c in (('END_L','#b07000'),('LID','#208020')):
        for w in csec[n_]['XZ_Y110']:pl(a,w,color=c,lw=1.2)
    a.annotate('',xy=(-0.5,144),xytext=(0,144),arrowprops=dict(arrowstyle='<|-|>',color=RED,lw=0.6,mutation_scale=5,shrinkA=0,shrinkB=0));a.text(-2.9,144.6,'g0.5\n(盖裙↔端板外面)',fontsize=6,color=RED)
    a.annotate('',xy=(5,149),xytext=(5,Hb),arrowprops=dict(arrowstyle='<|-|>',color=RED,lw=0.6,mutation_scale=5,shrinkA=0,shrinkB=0));a.text(5.4,148.6,f'q{q:g}',fontsize=6,color=RED)
    a.text(1.6,142.3,f'端板顶 Z={Hb:g}（与U口齐平）\n盖内R0.8↔端板顶外棱 {G["lid_root_fillet_vs_body_edge"]["clearance"]:.3f}',fontsize=5.8,color=RED)
    img(fig,W_/'iso_corner_bottom.png',334,37,54,54);ax.text(334,92,'端角轴测（底前左，橙=端板）',fontsize=6.5,weight='bold')
    box(ax,14,92,100,100,[('依据：技能 u_external_ends 外封端板',BLU),'box-generation.md L13：封板零折，','  底部圆角随U外轮廓，沿X拼缝按seam_gap','cad_build.py L62-65：U长=L−2t−2seam；','  端板轮廓 inset/top_flush','本单：seam 0、inset 0、上边齐口','（用户：端板盖U 不要留缝隙，完全遮盖）',
        ('接合（待确认）',PH_C),'· 端板盖U端面，无搭接，不能电阻点焊','· 建议：箱内沿U三边断续角焊','  （TIG，段长20/间距50）或外侧激光焊','· 焊后打磨、去氧化色、钝化','· 外观面不得焊穿、压痕'],title='端板盖U 做法',fs=6.6,ec=BLU)
    box(ax,118,10,140,72,['零件 | 折弯 | 方向 | 角度 | 内R | 翼边外 | 弯线距边（后挡料计算值）',
          f'件1 U | B1 | 侧壁向上(向内) | 90° | 0.8 | {Hb:g} | {BGL(Hb):.2f}',
          f'件1 U | B2 | 侧壁向上(向内) | 90° | 0.8 | {Hb:g} | {BGL(Hb):.2f}（调头）',
          '件2/3 端板 | 无折弯（零折平板）| — | — | — | — | —',
          '顺序：U  B1→B2（第2道侧壁高149、内宽218，','  须确认上模高度/滑块避让）',
          f'BA={BA:.4f}；OSSB={OSSB:.1f}；BD={BD:.4f}；展开=Σ外尺寸−n·BD',
          ('K0.4 经验值，非本厂实测；后挡料须首件试折修正',RED)],title='箱体折弯参数表',fs=6.4)
    box(ax,14,10,100,78,[f'U：{P["U"]["size"][0]:g}×{P["U"]["size"][1]:g}×{P["U"]["size"][2]:g}（X 1~399）',f'端板：{P["END_L"]["size"][0]:g}×{P["END_L"]["size"][1]:g}×{P["END_L"]["size"][2]:g}（X 0~1 / 399~400）','外形 = 400×220×148.8（端板外面~外面）','U外宽220不变 → 盖口全周间隙0.5',
        f'U端面未遮盖面积：{rep["end_cover"]["END_L"]["U_end_profile_uncovered_area_mm2"]:.3f} mm²',f'轴向拼缝：{rep["end_cover"]["END_L"]["axial_gap_mm"]:g} / {rep["end_cover"]["END_R"]["axial_gap_mm"]:g}',f'U↔端板干涉：{ints["U/END_L"]:.0f} / {ints["U/END_R"]:.0f} mm³（接触）'],title='遮盖校核（CAD）',fs=6.6)
    pdf.savefig(fig);plt.close(fig)
    # ================= PAGE 3 =================
    fig,ax=page(3,'第3页  件4 上盖：俯视（把手孔）、展开、剖面A-A、局部I（间隙基准）、局部II（盖角）、局部III（把手孔型）')
    a=vax(fig,14,172,(-40,430),(-30,250),0.32,'件4 上盖 俯视 1:3.1（把手铆接孔 Ø6.6×8）')
    view(a,'LID','top',lambda u,v:(u,v),hidden=False);hdl(a,body=True)
    dimh(a,-1.5,401.5,-20,-1.5,-1.5,'403');dimv(a,-1.5,221.5,-20,-1.5,-1.5,'223')
    for x1,x2,yy in ((0,65,232),(0,95,242),(305,400,242),(335,400,232)):dimh(a,x1,x2,yy,152.5 if x2 in(95,) or x1==305 else 141,152.5 if x2 in(95,) or x1==305 else 141,f'{x2-x1:g}',fs=6.2,c=BLU)
    dimh(a,80,320,-8,110,110,'240',fs=6.2,c=BLU)
    a.text(130,175,'X/Y为箱体外面基准（盖外边=−1.5）\n孔边→盖外边≥63.2；→折弯切点≥61.4；\n→最近裙边M4孔≥67.4',fontsize=6.3,color=BLU)
    lfx,lfy=P['LID']['flat_size']
    a=vax(fig,172,180,(-35,450),(-25,265),0.28,f'件4 上盖展开 {lfx:.2f}×{lfy:.2f}（外表面朝读者，1:3.6）')
    flatdraw(a,'LID');dimh(a,0,lfx,-15,0,0,f'{lfx:.2f}');dimv(a,0,lfy,-15,0,0,f'{lfy:.2f}')
    off=lfx/2-L/2
    a.text(140,120,f'B1~B4 向内(向下)折90° 内R0.8\n弯线距边 {BGL(skirt):.2f}；四角=03斜角收口（每角2段斜边，见局部II）\nØ4.5×10 孔心距边 7.5\nØ6.6×8 展开坐标 = 箱体坐标 + {off:.3f}',fontsize=6.6,color=RED)
    a=vax(fig,320,205,(-30,255),(-20,165),0.32,'剖面A-A（X=200）1:3.1')
    for n_,c in (('U','k'),('LID','#208020')):
        for w in sec[n_]:pl(a,w,color=c,lw=0.7)
    a.add_patch(Rectangle((-5,138),10,14,fill=False,ec=RED,lw=0.7));a.text(-14,150,'I',fontsize=9,color=RED)
    a.text(60,60,'绿=上盖  黑=U底壳',fontsize=6.5)
    a=vax(fig,14,38,(-4.6,5.0),(139.0,151.6),7.0,'局部I（7:1）间隙基准：盖裙内表面↔箱体侧壁外表面',tfs=8)
    for n_,c in (('U','#3050a0'),('LID','#208020')):
        for w in sec[n_]:pl(a,w,color=c,lw=1.3)
    for xx in (-0.5,0):a.plot([xx,xx],[139.2,149.3],color=RED,lw=0.6,ls=':')
    a.annotate('',xy=(-0.5,146.5),xytext=(0,146.5),arrowprops=dict(arrowstyle='<|-|>',color=RED,lw=0.7,mutation_scale=7,shrinkA=0,shrinkB=0))
    a.text(-4.4,146.3,'g = 0.5（单边）\n盖内 = 箱体外 + 2×0.5',fontsize=6.6,color=RED)
    a.plot([0.5,3.5],[149,149],color=RED,lw=0.5,ls=':');a.plot([1,3.5],[Hb,Hb],color=RED,lw=0.5,ls=':')
    a.annotate('',xy=(3.0,149.0),xytext=(3.0,Hb),arrowprops=dict(arrowstyle='<|-|>',color=RED,lw=0.6,mutation_scale=5,shrinkA=0,shrinkB=0))
    a.text(3.2,149.6,f'q={q:g}',fontsize=6.6,color=RED);a.text(1.4,150.3,'盖顶板（内面Z=149）',fontsize=5.8);a.text(1.4,147.7,'箱体顶边 Z=148.8',fontsize=5.8)
    a.text(-4.4,149.3,f'盖内R0.8↔箱体顶外棱\n最小间隙 {G["lid_root_fillet_vs_body_edge"]["clearance"]:.3f}',fontsize=6)
    a.plot([-4.5,4.9],[ZH,ZH],color=BLU,lw=0.6,ls='-.');a.text(1.3,ZH-0.9,'孔轴线 Z=142.5\n盖Ø4.5/箱体Ø3.3攻M4',fontsize=6,color=BLU)
    a.text(-4.4,139.6,'盖裙 t1',fontsize=6.3,color='#208020');a.text(1.3,139.6,'U侧壁 t1',fontsize=6.3,color='#3050a0')
    a=vax(fig,90,40,(36,128),(48,176),0.75,'局部III 左把手孔型（1:1.33）右把手镜像',tfs=8)
    hdl(a,body=True,only='L',lab=True)
    dimv(a,67.5,152.5,123,95,95,'85 宽排',fs=6.5,c=BLU);dimv(a,79,141,44,65,65,'62 窄排',fs=6.5,c=BLU)
    dimh(a,65,95,53,79,67.5,'30 排距',fs=6.5,c=BLU)
    a.plot([80,80],[95,125],color='0.4',lw=0.4,ls='-.');a.plot([60,100],[110,110],color='0.4',lw=0.4,ls='-.')
    a.text(81,111,'把手中心\n(80,110)',fontsize=5.8)
    a.annotate('朝盖中心X=200',xy=(127,172),xytext=(98,172),fontsize=6,color=RED,va='center',arrowprops=dict(arrowstyle='->',color=RED,lw=0.6))
    a=vax(fig,192,122,(-2.5,17.5),(-2.5,17.5),2.75,'局部II 盖展开角03（2.75:1，三角镜像）',tfs=7.5)
    for w in flats['LID']['wires']:
        ww=[q for q in w+[w[0]]]
        pl(a,ww,color='k',lw=1.0)
    for b_ in P['LID']['bend_lines']:pl(a,b_,color=RED,lw=0.6,ls=(0,(6,2,1,2)))
    for nm_,pt_,dx_,dy_ in (('P1',C3['P1'],0.6,-1.6),('P2',C3['P2'],0.4,0.4),('P3',C3['P3'],-6.2,0.5)):
        a.plot(*pt_,'o',ms=2.2,color=BLU);a.text(pt_[0]+dx_,pt_[1]+dy_,f"{nm_}({pt_[0]:.3f},{pt_[1]:.3f})",fontsize=5.4,color=BLU)
    a.text(-2.2,12.0,f"Ro=Ri+t=1.8  A=15−Ro=13.2\nB=A+BA90={C3['B']:.3f}\n短裙退 t+缝 = {C3['short_skirt_retreat']:g}（缝={C3['corner_gap']:g}）",fontsize=5.2,color=RED,va='top')
    a.text(1.0,16.0,'短裙(长221)',fontsize=5.4);a.text(14.2,2.0,'长裙\n(全长403)',fontsize=5.4)
    img(fig,W_/'iso_corner_lid03.png',252,124,60,52);ax.text(268,178.0,'成形后盖角03轴测',fontsize=6.5,weight='bold')
    ax.text(252,122.6,f'直段/顶板：0缝闭合；R区仅发丝缝≤{SL:.3f}',fontsize=5.6,color=RED);ax.text(252,119.6,f'（Z {SLZ[0]:.2f}~{SLZ[1]:.2f}，高约{SLZ[1]-SLZ[0]:.2f}）',fontsize=5.6,color=RED)
    box(ax,188,40,126,78,['· 盖裙15，直段13.2；盖孔心距盖顶7.5：',f'  孔上缘距折弯切点{15/2-D_LID/2-ro:.2f}，下缘距裙边{15/2-D_LID/2:.2f}',f'· 箱体孔Ø3.3：上缘距顶边{Hb-ZH-D_BODY/2:.2f}',f'· 盖孔↔箱体孔 10组同轴：{"通过" if coax else "不通过"}',
        '· 裙孔↔盖角03区(B=15.085)：孔心距36.4，孔边距34.2',('冲突：Ri0.8 > g0.5，q=0时盖根圆角压箱体',RED),(f'顶外棱{-G["lid_root_fillet_vs_body_edge"]["clearance_if_q0"]:.3f} → g保持0.5，q={q:g}，箱体高{Hb:g}',RED),
        '· 把手在盖顶、螺钉在裙侧：螺丝刀水平进刀，','  与把手无干涉；把手随盖整体提起，开盖无阻碍',f'· 两把手间净距{rep["min_distance_mm"]["HANDLE_REF_L/HANDLE_REF_R"]:.0f}（参考包络）'],title='盖 / 箱体配合与冲突',fs=6.6)
    box(ax,320,40,95,158,[f'B1/B2 长边裙：向下(向内)90°',f'B3/B4 短边裙：向下(向内)90°','内R0.8；翼边外尺寸15',f'弯线距边 = 后挡料 {BGL(skirt):.2f}','（计算值，须试折验证）','','顺序：B1→B2（长边，整刀）','     →B3→B4（短边，分段上模','       长≤219，避开已成形长裙）','','角部：03斜角折弯收口（用户“不要有缝”',f'  corner_gap={C3["corner_gap"]:g}）：短裙端头顶住长裙内面','  R区发丝缝见局部II；需密封时点焊/打胶','','把手孔Ø6.6×8（M6过孔）：激光切出；','  折弯后铆接（非焊接），背面垫实；','  铆钉型号待确认（定终孔径）'],title='上盖折弯参数',fs=7.0)
    pdf.savefig(fig);plt.close(fig)
    # ================= PAGE 4 =================
    fig,ax=page(4,'第4页  BOM、M4固定孔表、把手铆接孔表、K值/展开计算、校核结果、待确认清单')
    bom=['序号 | 零件 | 数量 | 材料 | 成形外形 | 展开尺寸 | 折弯数 | 质量kg']
    for i,(n,cn) in enumerate((('U','件1 U形底壳'),('END_L','件2 左端板'),('END_R','件3 右端板'),('LID','件4 上盖')),1):
        p=P[n];bom.append(f'{i} | {cn} | 1 | 201不锈钢 t1.0 | {p["size"][0]:.1f}×{p["size"][1]:.1f}×{p["size"][2]:.1f} | {p["flat_size"][0]:.2f}×{p["flat_size"][1]:.2f} | {len(p["bend_records"])} | {p["mass_kg"]:.3f}')
    bom+=['5 | M4螺钉（型号/长度待确认） | 10 | 不锈钢（待确认） | — | — | — | —','6 | 盖顶把手（孔型85/62/30，型号待确认） | 2 | 待确认 | 参考包络50×105×46 | — | — | —','7 | 铆钉/拉铆螺母 M6级（型号待确认，每把手4） | 8 | 不锈钢（待确认） | — | — | — | —']
    box(ax,12,222,262,50,bom,title='BOM（每套）',fs=6.8)
    ht=['编号 | 位置 | X / Y / Z（箱体外面基准） | 盖孔 | 箱体孔 | 加工']
    nm={'U':'件1','END_L':'件2','END_R':'件3'}
    for h in rep['holes']:ht.append(f"{h['id']} | {h['side']} | {h['point'][0]:g} / {h['point'][1]:g} / {h['point'][2]:g} | Ø4.5过孔 | Ø3.3（{nm[h['body_part']]}） | 激光Ø3.3后攻M4")
    box(ax,12,146,262,73,ht+['边距：长边孔距箱体外端50、孔距150；短边孔距外侧50、孔距120',('盖-体固定：箱体Ø3.3攻M4、盖Ø4.5过孔（用户默认M4攻丝；首件试装确认）',RED),('【警告】1.0 mm 201 板直接攻M4（底孔Ø3.3）仅约1扣有效螺纹，强度偏低、易滑牙，不建议反复拆装',RED),('　　　替代方案：压铆螺母 / 拉铆螺母 / 点焊螺母 —— 列为待确认（本版仍按M4直接攻丝出图）',RED)],title='M4固定孔位表（10组，盖↔箱体一一对应）',fs=6.6)
    hh=['编号 | 排 | X / Y（箱体基准） | X / Y（盖外角基准） | 展开图X / Y | 孔边→盖外边 | →折弯切点 | →最近裙孔']
    for h in rep['handle_holes']:
        hh.append(f"{h['id']} | {'宽85' if h['row']=='wide' else '窄62'} | {h['x']:g} / {h['y']:g} | {h['x']+1.5:g} / {h['y']+1.5:g} | {h['x']+off:.2f} / {h['y']+off:.2f} | {h['edge_to_lid_outer']:.1f} | {h['edge_to_bend_tangent']:.1f} | {h['edge_to_nearest_skirt_hole_3d']:.1f}（{h['nearest_skirt_hole']}）")
    box(ax,12,82,262,61,hh+[('Ø6.6×8 通孔（M6过孔，默认把手孔型85/62/30）',RED)],title='把手铆接孔表（每只4孔：宽排85/窄排62/排距30，宽排朝盖中心）',fs=6.6)
    box(ax,12,10,262,69,[f'BA = π/2×(Ri+K·t) = π/2×(0.8+0.4×1.0) = {BA:.4f}；OSSB = Ri+t = {OSSB:.1f}；BD = 2×OSSB−BA = {BD:.4f}',f'U展开宽 = 220+2×{Hb:g}−2×{BD:.4f} = {W+2*Hb-2*BD:.2f}（CAD原生展开 {P["U"]["flat_size"][1]:.2f}）',f'盖展开 = 403+30−2BD = {433-2*BD:.2f}；223+30−2BD = {253-2*BD:.2f}；端板零折，展开=外形220×148.8（刚体转平）','弯线位置（=后挡料计算值）= 翼边外尺寸 − OSSB + BA/2',('K=0.4：经验/默认值（未经本厂机床实测）；Ri0.8：候选；后挡料：计算值，须试折验证',RED),'坐标基准：箱体外面 X=0（左端外面）、Y=0（前侧外面）、Z=0（底外面）','把手孔型来源：S-201-1-20261024-005-v1 README（Ø6.6×4，85/62，排距30）；S-201-20261024-002-v1 同孔型'],title='K值、折弯扣除、后挡料来源；孔型来源',fs=6.6)
    hp=rep['handle_pattern_check'];hok=all(v['wide_pitch']==85 and v['narrow_pitch']==62 and v['row_spacing']==30 and v['wide_row_toward_centre'] for v in hp.values()) and rep['handle_mirror_ok']
    hopen=all(h['axis_line_lid_material_mm']==0 and h['open_at_r']==0 and h['material_at_r_plus_min']>0 for h in rep['handle_holes'])
    box(ax,280,146,135,126,[('【计算检查】（CAD计算，非实物；native03缝0未通过）',RED),f'· 模型：箱体400×220×{Hb:g}；盖403×223×15；总高150',f'· 装配干涉（含把手参考体）：最大 {max(ints.values()):.0f} mm³',f'· 盖-箱最小间隙 {rep["min_distance_mm"]["U/LID"]:.3f}；侧面0.5',f'· M4孔盖↔箱体 10/10 同轴 {"通过" if coax else "不通过"}',
        f'· 把手孔 8/8 通透、85/62/30、镜像 {"通过" if (hok and hopen) else "不通过"}',f'· 把手孔边距盖外边≥63.2、折弯切点≥61.4','· 螺丝刀进刀锥 ↔ 把手：0 干涉',f'· 铆钉尾包络Ø12×12 ↔ 箱体：距{rep["rivet_tail_envelope"]["min_dist_to_body"]:.0f}，0干涉',f'· DXF闭合/无重复/无重叠：9个 {"通过" if allpass else "不通过"}',f'· corner03.py：8斜边/坐标 通过；盖/箱根部重叠 {N3R["root_overlap_volume_mm3"]:g}',(f'· native03：缝0时原生展开把角柱1×1×13.2算给两裙(+52.8mm²)；',RED),(f'  按03定义切除后与原生展开差52.8mm² → 未通过',RED),'· 全部DXF实线无虚线；CUT/套料无折弯线',f'· 版本一致：{VER}',
        ('【实物试折试装：未进行】',RED),'· 首件试折、盖配合、螺钉、把手铆接：未进行',('· 生产放行：否（production_release=false）',RED)],title='校核结果',fs=6.6)
    box(ax,280,40,135,103,['1. 把手型号（孔型85/62/30）','2. 铆钉型号（孔Ø6.6=M6过孔，默认）','3. 盖角缝0：native03未通过(差52.8mm²)，请定：接受切除版/改缝/接受干涉','4. 端板接合：内侧角焊或外侧激光焊（无搭接，不能点焊）',('5. M4直接攻丝仅约1扣（WARN）；压铆/拉铆/点焊螺母替代',RED),('   待确认；首件试装',RED),'6. 螺钉型号、长度、材质','7. 内R0.8、K0.4、后挡料：按实际刀具试折','8. 顶隙q=0.2 / 箱体高148.8 是否接受','9. 公差、表面、去毛刺',('已确认：400×220=箱体外；150=含盖总高',BLU),('无电源孔/百叶/PG7/PG9/线孔',BLU)]+([ (ln,RED) for ln in _SKIRT_LINES ] if _SKIRT_LINES else []),title='待确认清单',fs=6.8,ec=RED)
    pdf.savefig(fig);plt.close(fig)
    d=pdf.infodict();d['Title']=VER+' 客户确认图 非生产放行';d['Subject']=VER;d['Keywords']=VER+' production_release=false'
print(pdf_path)
