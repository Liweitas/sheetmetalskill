import datetime
# shared drawing helpers for S-201-1-20261025-008-v1 4-page PDF (copied from reference job t31u helpers) (sm-venv python, reportlab). Font: embedded TrueType subset of Noto Sans CJK SC
# built by skill scripts/build_cjk_subset_ttf.py (all text incl. digits uses it -> every font embedded). Min text 9.4 pt (~3.3 mm at A3).
import json,math,csv,glob,datetime
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.pagesizes import A3,landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os
FONT_TTF=os.environ.get('V005_FONT','/workspace/orders/box-550x195x150/work/font/NotoSansCJKsc_subset.ttf')
pdfmetrics.registerFont(TTFont('NotoCJK',FONT_TTF));PW,PH=landscape(A3);F='NotoCJK';MINPT=9.4
def sw(txt,size):return pdfmetrics.stringWidth(clean(txt),F,max(size,MINPT))
def wrap(txt,width,size):
    out=[];cur=''
    for ch in clean(txt):
        if sw(cur+ch,size)>width and cur:out.append(cur);cur=ch
        else:cur+=ch
    if cur:out.append(cur)
    return out
DIMC=(0.0,0.2,0.65);RED=(0.8,0,0);GRN=(0,.45,.15);GREY=(.55,.55,.55);NAVY=(.1,.2,.45);BLUE=(0,0,.8)
VER='S-201-0.8-20261023-005-v1'
def f1(v,n=3):
    v=round(v,n);s=f'{v:.{n}f}'.rstrip('0').rstrip('.');return '0' if s in('-0','') else s
def clean(txt):
    return str(txt).replace('Ø','Φ').replace('−','-').replace('·','、').replace('•','-').replace('²','2').replace('³','3').replace('√','sqrt').replace('≥','>=').replace('≤','<=').replace('±','+/-')
LOG=[]
class Pg:
    def __init__(s,path,head_line):s.cv=Canvas(str(path),pagesize=landscape(A3),initialFontName=F,initialFontSize=10);s.n=0;s.N=0;s.hl=head_line
    def t(s,x,y,txt,size=10,c=(0,0,0),anchor='l',rot=0):
        size=max(size,MINPT);cv=s.cv;cv.saveState();cv.setFillColorRGB(*c);cv.setFont(F,size);cv.translate(x,y)
        if rot:cv.rotate(rot)
        {'l':cv.drawString,'c':cv.drawCentredString,'r':cv.drawRightString}[anchor](0,0,clean(txt));cv.restoreState()
    def box(s,x,y,w,h,fill=(1,1,1),stroke=(.3,.3,.3),lw=.6):
        cv=s.cv;cv.setFillColorRGB(*fill);cv.setStrokeColorRGB(*stroke);cv.setLineWidth(lw);cv.rect(x,y,w,h,fill=1,stroke=1);cv.setFillColorRGB(0,0,0);cv.setStrokeColorRGB(0,0,0)
    def head(s,title,part=None):
        cv=s.cv;cv.setFillColorRGB(.10,.22,.45);cv.rect(0,PH-46,PW,46,fill=1,stroke=0)
        s.t(24,PH-31,title,18,(1,1,1));stamp=datetime.datetime.now().strftime('%Y-%m-%d %H:%M')+' Asia/Shanghai'  # user t75u
        s.t(PW-24,PH-18,f'出图 {stamp}',11,(1,1,1),'r');s.t(PW-24,PH-34,VER,13,(1,1,1),'r');# 图号说明改由红条/正文；页眉右侧改为出图时间+VER（t75u）
        cv.setFillColorRGB(.82,.1,.1);cv.rect(0,PH-74,PW,28,fill=1,stroke=0)
        s.t(24,PH-66,s.hl+('　｜　'+part if part else ''),13,(1,1,1))
    def foot(s):
        cv=s.cv;cv.setStrokeColorRGB(.15,.3,.55);cv.setLineWidth(.8);cv.line(24,30,PW-24,30)
        s.t(24,14,'单位 mm；尺寸取自本版 skill 实算 STEP/DXF/孔表（来源 EVIDENCE pdf_dimension_sources.json）。按数值加工，不按纸量取。确认稿：首件试折与装配确认前不得批量。',9.4)
        s.t(PW-24,13,f'{VER}   {s.n+1}/{s.N}',11,anchor='r');cv.showPage();s.n+=1
    def frame(s,x,y,w,h,title,c=(.25,.3,.45)):
        cv=s.cv;cv.setStrokeColorRGB(*c);cv.setLineWidth(.6);cv.rect(x,y,w,h);s.t(x+6,y+h-15,title,11,NAVY);cv.setStrokeColorRGB(0,0,0)
    def line(s,a,b,lw=.8,c=(0,0,0),dash=None):
        cv=s.cv;cv.setLineWidth(lw);cv.setStrokeColorRGB(*c)
        if dash:cv.setDash(*dash)
        cv.line(*a,*b);cv.setDash();cv.setStrokeColorRGB(0,0,0)
    def poly(s,pts,lw=.8,c=(0,0,0),dash=None,close=False,fill=None):
        cv=s.cv;cv.setLineWidth(lw);cv.setStrokeColorRGB(*c)
        if dash:cv.setDash(*dash)
        p=cv.beginPath();p.moveTo(*pts[0])
        for q in pts[1:]:p.lineTo(*q)
        if close:p.close()
        if fill:cv.setFillColorRGB(*fill)
        cv.drawPath(p,stroke=1,fill=1 if fill else 0);cv.setDash();cv.setStrokeColorRGB(0,0,0);cv.setFillColorRGB(0,0,0)
    def circ(s,c,r,lw=.7,col=(0,0,0),dash=None,cross=True):
        cv=s.cv;cv.setLineWidth(lw);cv.setStrokeColorRGB(*col)
        if dash:cv.setDash(*dash)
        cv.circle(*c,r,stroke=1,fill=0);cv.setDash()
        if cross:
            cv.setLineWidth(.25);cv.setStrokeColorRGB(.5,.5,.5);e=r+2.5;cv.line(c[0]-e,c[1],c[0]+e,c[1]);cv.line(c[0],c[1]-e,c[0],c[1]+e)
        cv.setStrokeColorRGB(0,0,0)
    def arrow(s,x,y,dx,dy,c=DIMC):
        cv=s.cv;l=math.hypot(dx,dy)
        if l<1e-9:return
        ux,uy=dx/l,dy/l;a=5;w=1.6
        p=cv.beginPath();p.moveTo(x,y);p.lineTo(x-a*ux+w*uy,y-a*uy-w*ux);p.lineTo(x-a*ux-w*uy,y-a*uy+w*ux);p.close();cv.setFillColorRGB(*c);cv.drawPath(p,fill=1,stroke=0);cv.setFillColorRGB(0,0,0)
    def dim(s,a,b,off,val,src,vertical=False,size=9.5,label=None,tdx=0,c=DIMC):
        """horizontal (or vertical) dimension between page points a,b; off = offset of dim line from the farther point (signed)."""
        cv=s.cv;cv.setStrokeColorRGB(*c);cv.setLineWidth(.45);txt=label if label is not None else f1(val)
        if not vertical:
            y=(max(a[1],b[1])+off) if off>0 else (min(a[1],b[1])+off)
            sg=1 if off>0 else -1
            cv.line(a[0],a[1]+sg*1.5,a[0],y+sg*3);cv.line(b[0],b[1]+sg*1.5,b[0],y+sg*3);cv.line(a[0],y,b[0],y)
            if abs(b[0]-a[0])>14:s.arrow(a[0],y,a[0]-b[0],0,c);s.arrow(b[0],y,b[0]-a[0],0,c)
            else:
                cv.line(min(a[0],b[0])-8,y,max(a[0],b[0])+8,y);s.arrow(min(a[0],b[0]),y,1,0,c);s.arrow(max(a[0],b[0]),y,-1,0,c)
            s.t((a[0]+b[0])/2+tdx,y+2,txt,size,c,'c')
        else:
            x=(max(a[0],b[0])+off) if off>0 else (min(a[0],b[0])+off)
            sg=1 if off>0 else -1
            cv.line(a[0]+sg*1.5,a[1],x+sg*3,a[1]);cv.line(b[0]+sg*1.5,b[1],x+sg*3,b[1]);cv.line(x,a[1],x,b[1])
            if abs(b[1]-a[1])>14:s.arrow(x,a[1],0,a[1]-b[1],c);s.arrow(x,b[1],0,b[1]-a[1],c)
            else:
                cv.line(x,min(a[1],b[1])-8,x,max(a[1],b[1])+8);s.arrow(x,min(a[1],b[1]),0,1,c);s.arrow(x,max(a[1],b[1]),0,-1,c)
            s.t(x-2,(a[1]+b[1])/2+tdx,txt,size,c,'c',rot=90)
        cv.setStrokeColorRGB(0,0,0);LOG.append({'page':s.n+1,'text':txt,'value_mm':val,'source':src})
    def dimA(s,pa,pb,qa,qb,val,src,size=9.5,label=None,c=DIMC,flip=False):
        cv=s.cv;cv.setStrokeColorRGB(*c);cv.setLineWidth(.45);txt=label if label is not None else f1(val)
        for p,q in ((pa,qa),(pb,qb)):
            dx,dy=q[0]-p[0],q[1]-p[1];l=math.hypot(dx,dy) or 1;cv.line(p[0]+dx/l*1.5,p[1]+dy/l*1.5,q[0]+dx/l*3,q[1]+dy/l*3)
        cv.line(*qa,*qb);s.arrow(*qa,qa[0]-qb[0],qa[1]-qb[1],c);s.arrow(*qb,qb[0]-qa[0],qb[1]-qa[1],c)
        ang=math.degrees(math.atan2(qb[1]-qa[1],qb[0]-qa[0]))
        if ang>90:ang-=180
        if ang<=-90:ang+=180
        nx,ny=-math.sin(math.radians(ang)),math.cos(math.radians(ang));sg=-1 if flip else 1
        mx,my=(qa[0]+qb[0])/2+sg*nx*2.5,(qa[1]+qb[1])/2+sg*ny*2.5
        if flip:mx-=nx*size*.75;my-=ny*size*.75
        s.t(mx,my,txt,size,c,'c',rot=ang);cv.setStrokeColorRGB(0,0,0);LOG.append({'page':s.n+1,'text':txt,'value_mm':val,'source':src})
    def leader(s,p,q,txt,src=None,val=None,c=DIMC,size=9.5,anchor=None):
        cv=s.cv;cv.setStrokeColorRGB(*c);cv.setLineWidth(.45);cv.line(*p,*q);cv.setFillColorRGB(*c);cv.circle(*p,1,fill=1,stroke=0);cv.setStrokeColorRGB(0,0,0)
        a=anchor or ('l' if q[0]>=p[0] else 'r');s.t(q[0]+(2 if a=='l' else -2),q[1]-3,txt,size,c,a)
        if src:LOG.append({'page':s.n+1,'text':txt,'value_mm':val,'source':src})
    def table(s,x,y,cols,rows,size=9.4,rh=13.5,head_fill=(.88,.92,1),title=None,colors=None):
        tw=sum(w for _,w in cols)
        if title:s.t(x,y+4,title,10.5,NAVY)
        yy=y-rh;s.box(x,yy,tw,rh,fill=head_fill);cx=x
        for h,w in cols:s.t(cx+3,yy+3.4,h,size);cx+=w
        for i,r in enumerate(rows):
            yy-=rh;s.box(x,yy,tw,rh,fill=(1,1,1),lw=.3);cx=x;col=(colors[i] if colors else (0,0,0))
            for (h,w),v in zip(cols,r):s.t(cx+3,yy+3.4,v,size,col);cx+=w
        cv=s.cv;cv.setLineWidth(.3);cx=x
        for h,w in cols[:-1]:cx+=w;cv.line(cx,yy,cx,y)
        return yy
class View:
    """orthographic view: model (u,v) -> page; origin (ox,oy) is page position of model (u0,v0)."""
    def __init__(s,pg,ox,oy,sc,u0=0,v0=0):s.pg=pg;s.ox=ox;s.oy=oy;s.sc=sc;s.u0=u0;s.v0=v0
    def __call__(s,u,v):return (s.ox+s.sc*(u-s.u0),s.oy+s.sc*(v-s.v0))
    def rect(s,u0,v0,u1,v1,lw=.8,c=(0,0,0),dash=None,fill=None):
        s.pg.poly([s(u0,v0),s(u1,v0),s(u1,v1),s(u0,v1)],lw=lw,c=c,dash=dash,close=True,fill=fill)
    def ln(s,u0,v0,u1,v1,lw=.8,c=(0,0,0),dash=None):s.pg.line(s(u0,v0),s(u1,v1),lw,c,dash)
    def hole(s,u,v,d,col=(0,0,0),dash=None,lw=.7):s.pg.circ(s(u,v),s.sc*d/2,lw=lw,col=col,dash=dash)
    def arc(s,cu,cv_,r,a0,a1,lw=.8,c=(0,0,0),n=24):
        pts=[s(cu+r*math.cos(math.radians(a0+(a1-a0)*i/n)),cv_+r*math.sin(math.radians(a0+(a1-a0)*i/n))) for i in range(n+1)];s.pg.poly(pts,lw=lw,c=c)
# ---------- iso (skill fixed basis: horizontal (1,1,0)/sqrt2, vertical (-1,1,2)/sqrt6; viewer toward (1,-1,1))
IS2=math.sqrt(2);IS6=math.sqrt(6);DV=(1/math.sqrt(3),-1/math.sqrt(3),1/math.sqrt(3))
def iso_pt(X,Y,Z):return ((X+Y)/IS2,(-X+Y+2*Z)/IS6)
def boxfaces(x0,y0,z0,x1,y1,z1,tag):
    P=lambda a,b,c:(a,b,c)
    return [((-1,0,0),[P(x0,y0,z0),P(x0,y1,z0),P(x0,y1,z1),P(x0,y0,z1)],tag),((1,0,0),[P(x1,y0,z0),P(x1,y1,z0),P(x1,y1,z1),P(x1,y0,z1)],tag),
            ((0,-1,0),[P(x0,y0,z0),P(x1,y0,z0),P(x1,y0,z1),P(x0,y0,z1)],tag),((0,1,0),[P(x0,y1,z0),P(x1,y1,z0),P(x1,y1,z1),P(x0,y1,z1)],tag),
            ((0,0,-1),[P(x0,y0,z0),P(x1,y0,z0),P(x1,y1,z0),P(x0,y1,z0)],tag),((0,0,1),[P(x0,y0,z1),P(x1,y0,z1),P(x1,y1,z1),P(x0,y1,z1)],tag)]
def circle3(c,axis,d,n=36):
    r=d/2;ax=[abs(a) for a in axis];k=ax.index(max(ax));e=[i for i in range(3) if i!=k]
    pts=[]
    for i in range(n+1):
        a=2*math.pi*i/n;p=list(c);p[e[0]]+=r*math.cos(a);p[e[1]]+=r*math.sin(a);pts.append(tuple(p))
    return pts
def iso_draw(pg,faces,holes,x,y,w,h,margin=40,fills=None,shift=None):
    """faces: (normal,[4 pts],tag); holes: (center,axis,d,tag). painter + back-face culling. returns mapper I(X,Y,Z,tag)."""
    shift=shift or {}
    def sh(p,tag):d=shift.get(tag,(0,0,0));return (p[0]+d[0],p[1]+d[1],p[2]+d[2])
    vis=[(n,[sh(p,tag) for p in pts],tag) for n,pts,tag in faces if n[0]*DV[0]+n[1]*DV[1]+n[2]*DV[2]>1e-9]
    allp=[iso_pt(*p) for _,pts,_ in vis for p in pts];xs=[p[0] for p in allp];ys=[p[1] for p in allp]
    sc=min((w-2*margin)/(max(xs)-min(xs)),(h-2*margin)/(max(ys)-min(ys)))
    ox=x+(w-sc*(max(xs)-min(xs)))/2;oy=y+(h-sc*(max(ys)-min(ys)))/2
    M=lambda p:(ox+sc*(iso_pt(*p)[0]-min(xs)),oy+sc*(iso_pt(*p)[1]-min(ys)))
    depth=lambda pts:sum(p[0]*DV[0]+p[1]*DV[1]+p[2]*DV[2] for p in pts)/len(pts)
    for n,pts,tag in sorted(vis,key=lambda f:depth(f[1])):
        fc=(fills or {}).get(tag,(1,1,1));pg.poly([M(p) for p in pts],lw=.6,close=True,fill=fc)
        for c,axis,d,htag in holes:
            if htag!=tag:continue
            cc=sh(c,tag)
            k=[abs(a) for a in axis].index(1)
            if abs(n[k])<.5 or n[k]*axis[k]<0:continue
            # hole lies on this face plane?
            plane=pts[0][k]
            if abs(cc[k]-plane)>1e-6:continue
            pg.poly([M(p) for p in circle3(cc,axis,d)],lw=.45)
    def I(X,Y,Z,tag=None):return M(sh((X,Y,Z),tag) if tag else (X,Y,Z))
    I.sc=sc;return I
def isodim(pg,I,P0,P1,off,val,src,label=None,size=9.5,flip=False):
    q0=tuple(a+b for a,b in zip(P0,off));q1=tuple(a+b for a,b in zip(P1,off))
    pg.dimA(I(*P0),I(*P1),I(*q0),I(*q1),val,src,label=label,size=size,flip=flip)

# ---------- shaded isometric image rendered from the skill formed-STEP meshes (iso_png.py), same basis as iso_pt
def iso_img(pg,b,x,y,w,h,margin=30,title=None,frame=True):
    """draws PNG b (bounds dict) fitted in rect; returns I(X,Y,Z,part=None) page mapping (handles lid flip + per-part shift)."""
    if frame:pg.frame(x,y,w,h,title or '')
    du=b['umax']-b['umin'];dv=b['vmax']-b['vmin'];top=18 if title else 0
    sc=min((w-2*margin)/du,(h-2*margin-top)/dv);iw,ih=sc*du,sc*dv;ox=x+(w-iw)/2;oy=y+(h-top-ih)/2
    pg.cv.drawImage(b['png'],ox,oy,iw,ih)
    shifts={n:sh for n,sh in b['parts']};flip=b.get('flip',False)
    def I(X,Y,Z,part=None):
        if flip:Y,Z=208.0-Y,150.0-Z
        if part:d=shifts[part];X,Y,Z=X+d[0],Y+d[1],Z+d[2]
        u,v=iso_pt(X,Y,Z);return (ox+sc*(u-b['umin']),oy+sc*(v-b['vmin']))
    I.sc=sc;return I
def isodimP(pg,I,P0,P1,off,val,src,label=None,size=9.5,flip=False,part=None):
    q0=tuple(a+b for a,b in zip(P0,off));q1=tuple(a+b for a,b in zip(P1,off))
    pg.dimA(I(*P0,part),I(*P1,part),I(*q0,part),I(*q1,part),val,src,label=label,size=size,flip=flip)
