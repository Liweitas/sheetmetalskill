# v2.8.2 pipeline u_l_t7u (DEFAULT structure): vendored from 干画图3's /workspace/orders/box-180x420x175/addendum-tools (S-201-1-20261021-007-v1).
# v2.8.2 changes: hardcoded order/skill/tmp paths -> env SM_ORDER (order folder) + this folder; job features from release_config.json.
# 4-page A3 shop bend PDF (box-180x420x175 / S-201-1-20261021-007-v1, workflow of S-201-1-20261025-002-v1; same format as 003 Rev t8u): full engineering dimensioning (extension lines + arrows + values) on every view.
# Flat numbers are read from this release's laser DXF (work_main/<part>.dxf + bend records); formed numbers from the
# STEP-derived HLR views / hole features (views_E.json) and the STEP section (corner_mesh.json). Geometry files are only read.
# Every text is collision-checked against all texts and drawn lines of its page (report -> logs/bend_pdf_layout_check.json).
import json,math
from pathlib import Path
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.pagesizes import A3,landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.pdfmetrics import stringWidth
import sys;sys.path.insert(0,__import__('os').path.dirname(__import__('os').path.abspath(__file__)));import cfg
VER=cfg.VER;RD=cfg.ROOF_D;RR=RD/2
B=Path(cfg.B);Wd=Path(cfg.W);OUT=B/'named_release'/VER
rep=json.load(open(Wd/'E_main_report.json'));VW=json.load(open(Wd/'views_E.json'));FT=VW['features']
P=rep['params'];Lx,Wy,Hz,TT,RI=P['L'],P['W'],P['H'],P['t'],P['Ri']
# user t16u 2026-10-26: L盖U / 长裙盖短裙，不留缝隙，不退让 -> texts follow the report values (old reports: 0.2)
_S=float(P.get('L_cover_setback',0.2));_SL=float(rep.get('lid',{}).get('long_skirt_cover_setback_mm',0.2))
_stx=lambda v:'0缝不退让' if abs(v)<1e-9 else f'退{v:g}'
PW,PH=landscape(A3)
# v2.8.2: embedded fonts (lessons 干画图3 §3.6). 007 used unembedded STSong-Light/Helvetica -> release_package gate FAILs.
# Build a glyf subset of Noto CJK SC with scripts/build_cjk_subset_ttf.py (AV python has fontTools) and embed it + LiberationSans.
import os as _os,subprocess as _sp
_FT=Path(_os.environ.get('SM_CJK_TTF',str(B/'logs'/'cjk-sub.ttf')));_LIB='/usr/share/fonts/truetype/liberation/LiberationSans-'
if not _FT.exists():
    _FT.parent.mkdir(parents=True,exist_ok=True)
    _sp.run([_os.environ.get('SM_AV','/workspace/addendum-venv/bin/python'),str(Path(__file__).resolve().parents[2]/'scripts'/'build_cjk_subset_ttf.py'),str(_FT),
             __file__,str(Path(__file__).with_name('cfg.py')),str(B/'release_config.json')],check=True)
from reportlab.pdfbase.ttfonts import TTFont
pdfmetrics.registerFont(TTFont('CNF',str(_FT)));pdfmetrics.registerFont(TTFont('LS',_LIB+'Regular.ttf'));pdfmetrics.registerFont(TTFont('LSB',_LIB+'Bold.ttf'))
CN='CNF';NF='LS'
DIMC=(0,.2,.65);RED=(.8,0,0);GRN=(0,.42,0);BLK=(0,0,0);GRY=(.5,.5,.5)
LEV=11.5;DS=8.5
def fmt(v):
    s=f'{round(v,3)+0:.3f}'.rstrip('0').rstrip('.');return '0' if s in('-0','') else s
fg=lambda v:f'{v:g}'
LOG=[];ISSUES=[]
def load_cut(name):
    L=(Wd/f'{name}.dxf').read_text().splitlines();ents=[];i=0
    while i<len(L)-1:
        if L[i].strip()=='0':
            t=L[i+1].strip();d={};j=i+2
            while j<len(L)-1 and L[j].strip()!='0':d[int(L[j])]=L[j+1].strip();j+=2
            if t=='LINE':ents.append(('L',float(d[10]),float(d[20]),float(d[11]),float(d[21])))
            elif t=='CIRCLE':ents.append(('C',float(d[10]),float(d[20]),float(d[40])))
            elif t=='ARC':ents.append(('A',float(d[10]),float(d[20]),float(d[40]),float(d[50]),float(d[51])))
            i=j;continue
        i+=1
    return ents
def seg_rect(a,b,c,d,r):
    x0,y0,x1,y1=r
    if x0>=x1 or y0>=y1:return False
    if max(a,c)<x0 or min(a,c)>x1 or max(b,d)<y0 or min(b,d)>y1:return False
    t0,t1=0.,1.;dx,dy=c-a,d-b
    for p,q in ((-dx,a-x0),(dx,x1-a),(-dy,b-y0),(dy,y1-b)):
        if abs(p)<1e-12:
            if q<0:return False
        else:
            t=q/p
            if p<0:
                if t>t1:return False
                t0=max(t0,t)
            else:
                if t<t0:return False
                t1=min(t1,t)
    return True
def clip_seg(a,b,c,d,r):
    x0,y0,x1,y1=r;t0,t1=0.,1.;dx,dy=c-a,d-b
    for p,q in ((-dx,a-x0),(dx,x1-a),(-dy,b-y0),(dy,y1-b)):
        if abs(p)<1e-12:
            if q<0:return None
        else:
            t=q/p
            if p<0:
                if t>t1:return None
                t0=max(t0,t)
            else:
                if t<t0:return None
                t1=min(t1,t)
    return (a+t0*dx,b+t0*dy,a+t1*dx,b+t1*dy)
def seg_seg(p,q,r,s):
    d=(q[0]-p[0])*(s[1]-r[1])-(q[1]-p[1])*(s[0]-r[0])
    if abs(d)<1e-12:return False
    t=((r[0]-p[0])*(s[1]-r[1])-(r[1]-p[1])*(s[0]-r[0]))/d;u=((r[0]-p[0])*(q[1]-p[1])-(r[1]-p[1])*(q[0]-p[0]))/d
    return 0.02<t<0.98 and 0<=u<=1
def rov(r,s):return r[0]<s[2] and s[0]<r[2] and r[1]<s[3] and s[1]<r[3]
class Pg:
    def __init__(s,path):s.cv=Canvas(str(path),pagesize=landscape(A3),initialFontName='LS');s.n=0;s.reset();s.report=[]
    def reset(s):s.T=[];s.S=[];s.G={};s.oid=0;s.VL=[];s.BL=[]
    def nid(s):s.oid+=1;return s.oid
    def addseg(s,a,b,c,d,o):
        s.S.append((a,b,c,d,o));i=len(s.S)-1;C=24
        for gx in range(int(min(a,c)//C),int(max(a,c)//C)+1):
            for gy in range(int(min(b,d)//C),int(max(b,d)//C)+1):s.G.setdefault((gx,gy),[]).append(i)
    def segs_in(s,r):
        C=24;out=set()
        for gx in range(int(r[0]//C),int(r[2]//C)+1):
            for gy in range(int(r[1]//C),int(r[3]//C)+1):out.update(s.G.get((gx,gy),()))
        return out
    @staticmethod
    def fnt(txt):return NF if all(ord(ch)<128 for ch in txt) else CN
    def tw(s,txt,size):txt=str(txt).replace('Ø','Φ');return stringWidth(txt,s.fnt(txt),size)
    def tbox(s,x,y,txt,size,anchor='l',rot=0):
        txt=str(txt).replace('Ø','Φ');f=s.fnt(txt);w=stringWidth(txt,f,size);asc=size*(.74 if f==NF else .88);des=size*(.2 if f==NF else .14)
        u0={'l':0,'c':-w/2,'r':-w}[anchor]
        if rot==0:return (x+u0,y-des,x+u0+w,y+asc)
        return (x-asc,y+u0,x+des,y+u0+w)
    def hits(s,r,owner=None,tpad=1.0,spad=.35):
        rt=(r[0]-tpad,r[1]-tpad,r[2]+tpad,r[3]+tpad);n=0
        for (b,o,_,_) in s.T:
            if rov(rt,b):n+=1
        rs=(r[0]+spad,r[1]+spad,r[2]-spad,r[3]-spad)
        for i in s.segs_in(rs):
            a,b,c,d,o=s.S[i]
            if o!=owner and seg_rect(a,b,c,d,rs):n+=1
        if r[0]<26 or r[2]>PW-26 or r[1]<33 or r[3]>PH-77:n+=5
        return n
    def seghits(s,a,b,c,d,owner=None):
        return sum(1 for (r,o,_,_) in s.T if o!=owner and seg_rect(a,b,c,d,(r[0]+.3,r[1]+.3,r[2]-.3,r[3]-.3)))
    def geocross(s,p,q):
        r=(min(p[0],q[0])-1,min(p[1],q[1])-1,max(p[0],q[0])+1,max(p[1],q[1])+1);n=0
        for i in s.segs_in(r):
            a,b,c,d,o=s.S[i]
            if seg_seg(p,q,(a,b),(c,d)):n+=1
        return n
    def t(s,x,y,txt,size=10,c=BLK,anchor='l',rot=0,owner=None,reg=True,font=None):
        txt=str(txt).replace('Ø','Φ');f=font or s.fnt(txt);cv=s.cv
        cv.saveState();cv.setFillColorRGB(*c);cv.setFont(f,size);cv.translate(x,y)
        if rot:cv.rotate(rot)
        {'l':cv.drawString,'c':cv.drawCentredString,'r':cv.drawRightString}[anchor](0,0,txt);cv.restoreState()
        if reg:s.T.append((s.tbox(x,y,txt,size,anchor,rot),owner,txt,s.n+1))
    def ft(s,x,y,txt,size=10,c=BLK,owner=None):
        """free text: try to keep it collision free by nudging down/right; returns box"""
        best=None
        for dy in (0,-4,4,-8,8,-12,12):
            for dx in (0,6,-6,12,-12):
                h=s.hits(s.tbox(x+dx,y+dy,txt,size),owner)
                if best is None or h<best[0]:best=(h,dx,dy)
                if h==0:break
            if best[0]==0:break
        s.t(x+best[1],y+best[2],txt,size,c,owner=owner)
    def line(s,a,b,c,d,lw=.5,col=BLK,dash=None,owner='geo',reg=True):
        cv=s.cv;cv.setLineWidth(lw);cv.setStrokeColorRGB(*col)
        if dash:cv.setDash(list(dash),0)
        cv.line(a,b,c,d)
        if dash:cv.setDash()
        cv.setStrokeColorRGB(0,0,0)
        if reg:s.addseg(a,b,c,d,owner)
    def pl(s,pts,lw=.6,col=BLK,dash=None,owner='geo',close=False,reg=True):
        if len(pts)<2:return
        cv=s.cv;cv.setLineWidth(lw);cv.setStrokeColorRGB(*col)
        if dash:cv.setDash(list(dash),0)
        p=cv.beginPath();p.moveTo(*pts[0])
        for q in pts[1:]:p.lineTo(*q)
        if close:p.close()
        cv.drawPath(p,stroke=1,fill=0)
        if dash:cv.setDash()
        cv.setStrokeColorRGB(0,0,0)
        if reg:
            for i in range(len(pts)-1):s.addseg(*pts[i],*pts[i+1],owner)
            if close:s.addseg(*pts[-1],*pts[0],owner)
    def circ(s,c,r,lw=.6,col=BLK,owner='geo'):
        cv=s.cv;cv.setLineWidth(lw);cv.setStrokeColorRGB(*col);cv.circle(c[0],c[1],r,stroke=1,fill=0);cv.setStrokeColorRGB(0,0,0)
        pts=[(c[0]+r*math.cos(2*math.pi*k/20),c[1]+r*math.sin(2*math.pi*k/20)) for k in range(21)]
        for i in range(20):s.addseg(*pts[i],*pts[i+1],owner)
    def arrow(s,x,y,ux,uy,col=DIMC,a=5.0,w=1.6):
        cv=s.cv;p=cv.beginPath();p.moveTo(x,y);p.lineTo(x-a*ux+w*uy,y-a*uy-w*ux);p.lineTo(x-a*ux-w*uy,y-a*uy+w*ux);p.close()
        cv.setFillColorRGB(*col);cv.drawPath(p,fill=1,stroke=0);cv.setFillColorRGB(0,0,0)
    def head(s,title,sub):
        cv=s.cv;cv.setFillColorRGB(.10,.22,.45);cv.rect(0,PH-46,PW,46,fill=1,stroke=0)
        s.t(24,PH-31,title,19,(1,1,1),owner='head');cv.setFillColorRGB(1,1,1);cv.setFont('LSB',15);cv.drawRightString(PW-24,PH-26,VER);s.t(PW-24,PH-41,'R01 首版（尺寸标注版，格式同 003 Rev t8u）',9,(1,1,1),'r',owner='head')
        cv.setFillColorRGB(.82,.1,.1);cv.rect(0,PH-74,PW,28,fill=1,stroke=0)
        s.t(24,PH-66,f'材料 {cfg.MATERIAL_CN}　｜　板厚 {fg(TT)} mm　｜　箱体外形 {fg(Lx)}×{fg(Wy)}　｜　总高 {fg(Hz)}（含盖）　｜　内R{fg(RI)}　｜　1套　｜　'+sub,15,(1,1,1),owner='head')
    def frame(s,x,y,w,h,title,c=(.25,.3,.45)):
        o='frame';s.line(x,y,x+w,y,.6,c,owner=o);s.line(x+w,y,x+w,y+h,.6,c,owner=o);s.line(x+w,y+h,x,y+h,.6,c,owner=o);s.line(x,y+h,x,y,.6,c,owner=o)
        s.t(x+6,y+h-14,title,10.5,(.1,.2,.45),owner='frame')
    def check(s):
        """final per-page collision report: text/text overlaps, text crossed by lines of another owner."""
        bad=[]
        for i,(b,o,txt,_) in enumerate(s.T):
            if o=='head':continue
            for j in range(i+1,len(s.T)):
                b2,o2,t2,_=s.T[j]
                if o2!='head' and rov((b[0]+.2,b[1]+.2,b[2]-.2,b[3]-.2),b2):bad.append(('text/text',txt,t2))
            rs=(b[0]+.35,b[1]+.35,b[2]-.35,b[3]-.35)
            for k in s.segs_in(rs):
                a,bb,c,d,oo=s.S[k]
                if oo!=o and seg_rect(a,bb,c,d,rs):bad.append(('line/text',txt,str(oo)));break
        s.report.append({'page':s.n+1,'texts':len(s.T),'segments':len(s.S),'collisions':bad})
        return bad
    def place_labels(s):
        for a in s.BL:bendlabel(s,*a)
        for (m,e,key) in s.VL:
            a=m((e[0],e[3]));b=m((e[2],e[1]));w=s.tw(key,10);best=None
            for (x,y) in ((a[0],a[1]+4),(a[0]-w-6,a[1]-10),(a[0]-w-6,b[1]+3),(a[0],b[1]-14),(b[0]+6,a[1]-10),(b[0]+6,b[1]+3),(a[0]-w-30,a[1]-10),(a[0]+(b[0]-a[0])/2-w/2,a[1]+4),(a[0]+(b[0]-a[0])/2-w/2,b[1]-14)):
                h=s.hits(s.tbox(x,y,key,10),'vl')
                if best is None or h<best[0]:best=(h,x,y)
                if h==0:break
            s.t(best[1],best[2],key,10,(.1,.2,.45),owner='vl')
    def foot(s):
        s.place_labels();cv=s.cv;s.line(24,30,PW-24,30,.8,(.15,.3,.55),owner='foot')
        s.t(24,14,'版本 '+VER+'　尺寸单位 mm；展开尺寸取自本版激光 DXF，成形尺寸取自本版 STEP；按数值加工，不按纸量。试折首件确认后量产。',9,owner='foot')
        cv.setFillColorRGB(0,0,0);cv.setFont('LSB',11);cv.drawRightString(PW-24,13,f'{VER}   {s.n+1}/4')
        bad=s.check();print('page',s.n+1,'texts',len(s.T),'collisions',len(bad))
        for b in bad:print('   ',b)
        cv.showPage();s.n+=1;s.reset()
def mapper(ox,oy,sc,u0,v0):return lambda p:(ox+sc*(p[0]-u0),oy+sc*(p[1]-v0))
def ext(pols):
    xs=[q[0] for p in pols for q in p];ys=[q[1] for p in pols for q in p];return min(xs),min(ys),max(xs),max(ys)
# ---------------- dimension primitives ----------------
def _log(pg,txt,val,src,h):
    LOG.append({'page':pg.n+1,'text':txt,'value_mm':val,'source':src,'placement_hits':h})
    if h:ISSUES.append({'page':pg.n+1,'text':txt,'hits':h})
def dimH(pg,pa,pb,yl,val,src,txt=None,ga=1.5,gb=1.5,col=DIMC,size=DS,pref=.5):
    o=pg.nid();txt=txt or fmt(val)
    for (x,y,g) in ((pa[0],pa[1],ga),(pb[0],pb[1],gb)):
        if abs(yl-y)>g+1:d=1 if yl>y else -1;pg.line(x,y+d*g,x,yl+d*2.5,.3,col,owner=o)
    x1,x2=sorted((pa[0],pb[0]));w=pg.tw(txt,size);cands=[]
    if x2-x1>=w+12:
        lo,hi=x1+5+w/2,x2-5-w/2
        for f in (pref,.5,.35,.65,.22,.78,.1,.9,0,1):cands.append(('c',lo+(hi-lo)*f))
    for k in range(5):cands+=[('l',x2+9+k*12),('r',x1-9-k*12)]
    best=None
    for an,cx in cands:
        h=pg.hits(pg.tbox(cx,yl+2,txt,size,an),o)
        if best is None or h<best[0]:best=(h,an,cx)
        if h==0:break
    h,an,cx=best
    if an=='c':pg.line(x1,yl,x2,yl,.3,col,owner=o);pg.arrow(x1,yl,-1,0,col);pg.arrow(x2,yl,1,0,col)
    else:
        e1=min(x1-8,cx-w-1) if an=='r' else x1-8;e2=max(x2+8,cx+w+1) if an=='l' else x2+8
        pg.line(e1,yl,e2,yl,.3,col,owner=o);pg.arrow(x1,yl,1,0,col);pg.arrow(x2,yl,-1,0,col)
    pg.t(cx,yl+2,txt,size,col,an,owner=o);_log(pg,txt,val,src,h)
def dimV(pg,pa,pb,xl,val,src,txt=None,ga=1.5,gb=1.5,col=DIMC,size=DS,pref=.5,hside=0):
    o=pg.nid();txt=txt or fmt(val)
    for (x,y,g) in ((pa[0],pa[1],ga),(pb[0],pb[1],gb)):
        if abs(xl-x)>g+1:d=1 if xl>x else -1;pg.line(x+d*g,y,xl+d*2.5,y,.3,col,owner=o)
    y1,y2=sorted((pa[1],pb[1]));w=pg.tw(txt,size);cands=[];X=xl-2
    if y2-y1>=w+12:
        lo,hi=y1+5+w/2,y2-5-w/2
        for f in (pref,.5,.35,.65,.22,.78,.1,.9,0,1):cands.append(('c',lo+(hi-lo)*f))
    if hside:cands=[('h',(y1+y2)/2)]
    for k in range(5):cands+=[('l',y2+9+k*12),('r',y1-9-k*12)]
    best=None
    for an,cy in cands:
        if an=='h':
            h=pg.hits(pg.tbox(xl+hside*3,cy-size*.35,txt,size,'l' if hside>0 else 'r'),o)
            if best is None or h<best[0]:best=(h,an,cy)
            if h==0:break
            continue
        h=pg.hits(pg.tbox(X,cy,txt,size,an,90),o)
        if best is None or h<best[0]:best=(h,an,cy)
        if h==0:break
    h,an,cy=best
    if an=='h':
        pg.line(xl,y1-8,xl,y2+8,.3,col,owner=o);pg.arrow(xl,y1,0,1,col);pg.arrow(xl,y2,0,-1,col)
        pg.t(xl+hside*3,cy-size*.35,txt,size,col,'l' if hside>0 else 'r',owner=o);_log(pg,txt,val,src,h);return
    if an=='c':pg.line(xl,y1,xl,y2,.3,col,owner=o);pg.arrow(xl,y1,0,-1,col);pg.arrow(xl,y2,0,1,col)
    else:
        e1=min(y1-8,cy-w-1) if an=='r' else y1-8;e2=max(y2+8,cy+w+1) if an=='l' else y2+8
        pg.line(xl,e1,xl,e2,.3,col,owner=o);pg.arrow(xl,y1,0,1,col);pg.arrow(xl,y2,0,-1,col)
    pg.t(X,cy,txt,size,col,an,90,owner=o);_log(pg,txt,val,src,h)
def stack(pg,kind,datum,feats,base,sgn,src):
    """baseline dims from one datum. feats: [(page_pt,val,gap,src)] -> innermost = smallest value.
       kind 'H': dim lines horizontal at y=base+sgn*(14+i*LEV); 'V': vertical at x=..."""
    for i,(pt,val,g,s) in enumerate(sorted(feats,key=lambda q:q[1])):
        lv=base+sgn*(14+i*LEV)
        (dimH if kind=='H' else dimV)(pg,datum,pt,lv,val,f'{src}: {s}',gb=g)
    return base+sgn*(14+(len(feats)-1)*LEV)
def callout(pg,c,r,txt,src,val,col=DIMC,size=9,angs=(45,135,-45,-135,60,120,-60,-120,30,150,-30,-150,75,105,-75,-105),lens=(14,24,36,50,68,90),dot=False):
    o=pg.nid();txt=txt.replace('Ø','Φ');w=pg.tw(txt,size);best=None
    for L in lens:
        for a in angs:
            ux,uy=math.cos(math.radians(a)),math.sin(math.radians(a));sx=1 if ux>=0 else -1
            tip=(c[0]+r*ux,c[1]+r*uy);el=(tip[0]+L*ux,tip[1]+L*uy);sh=(el[0]+sx*(w+3),el[1])
            tb=pg.tbox(el[0]+sx*1.5,el[1]+1.5,txt,size,'l' if sx>0 else 'r')
            h=pg.hits(tb,o)*3+pg.seghits(*tip,*el)*2+pg.seghits(*el,*sh)*2;hg=h+.25*pg.geocross(tip,el)
            if best is None or hg<best[0]:best=(hg,h,tip,el,sh,sx)
            if hg==0:break
        if best[0]==0:break
    hg,h,tip,el,sh,sx=best
    pg.line(*tip,*el,.35,col,owner=o);pg.line(*el,*sh,.35,col,owner=o)
    if dot:pg.cv.setFillColorRGB(*col);pg.cv.circle(tip[0],tip[1],1.1,fill=1,stroke=0);pg.cv.setFillColorRGB(0,0,0)
    else:pg.arrow(tip[0],tip[1],-(el[0]-tip[0])/math.hypot(el[0]-tip[0],el[1]-tip[1]),-(el[1]-tip[1])/math.hypot(el[0]-tip[0],el[1]-tip[1]),col)
    pg.t(el[0]+sx*1.5,el[1]+1.5,txt,size,col,'l' if sx>0 else 'r',owner=o);_log(pg,txt,val,src,h)
def cmark(pg,c,r,col=GRY):
    e=r+3;pg.line(c[0]-e,c[1],c[0]+e,c[1],.25,col,(4,1.5,1,1.5),owner='cl');pg.line(c[0],c[1]-e,c[0],c[1]+e,.25,col,(4,1.5,1,1.5),owner='cl')
def bendlabel(pg,p0,p1,txt,o,col=RED,size=9):
    vert=abs(p0[0]-p1[0])<1e-6;w=pg.tw(txt,size);best=None
    for f in (.5,.3,.7,.2,.8,.4,.6,.12,.88):
        for side in (1,-1):
            if vert:
                x=p0[0]+(2+size*.88 if side>0 else -2-size*.14);y=p0[1]+(p1[1]-p0[1])*f;b=pg.tbox(x,y,txt,size,'c',90)
            else:
                x=p0[0]+(p1[0]-p0[0])*f;y=p0[1]+(2+size*.14 if side>0 else -2-size*.88);b=pg.tbox(x,y,txt,size,'c')
            h=pg.hits(b,o)
            if best is None or h<best[0]:best=(h,x,y)
            if h==0:break
        if best[0]==0:break
    h,x,y=best;pg.t(x,y,txt,size,col,'c',90 if vert else 0,owner=o);_log(pg,txt,None,'bend record',h)
def isoview(pg,name,x,y,w,h):
    V=VW[name]['iso']['visible'];e=ext(V);sc=min((w-90)/(e[2]-e[0]),(h-70)/(e[3]-e[1]))
    m=mapper(x+45+(w-90-sc*(e[2]-e[0]))/2,y+30+(h-70-sc*(e[3]-e[1]))/2,sc,e[0],e[1])
    for p in V:pg.pl([m(q) for q in p],.5)
    bb=VW[name]['bbox'];c30=math.cos(math.radians(30));iso=lambda X,Y,Z:m((c30*(X+Y),Z+.5*(Y-X)))
    x0,y0,z0,x1,y1,z1=bb
    for (A,Bp,val,lab,nx,ny) in (((x0,y0,z0),(x1,y0,z0),x1-x0,'X',-.5,-1),((x1,y0,z0),(x1,y1,z0),y1-y0,'Y',.5,-1),((x0,y0,z0),(x0,y0,z1),z1-z0,'Z',-1,0)):
        a=iso(*A);b=iso(*Bp);o=pg.nid();n=math.hypot(nx,ny);nx,ny=nx/n,ny/n;off=14
        pa=(a[0]+nx*off,a[1]+ny*off);pb=(b[0]+nx*off,b[1]+ny*off)
        pg.line(a[0]+nx*2,a[1]+ny*2,pa[0]+nx*3,pa[1]+ny*3,.3,DIMC,owner=o);pg.line(b[0]+nx*2,b[1]+ny*2,pb[0]+nx*3,pb[1]+ny*3,.3,DIMC,owner=o)
        pg.line(*pa,*pb,.35,DIMC,owner=o);L=math.hypot(pb[0]-pa[0],pb[1]-pa[1]);ux,uy=(pb[0]-pa[0])/L,(pb[1]-pa[1])/L
        pg.arrow(*pa,-ux,-uy);pg.arrow(*pb,ux,uy);txt=fmt(val);best=None
        an='r' if lab=='Z' else 'c'
        for f in (.5,.4,.6,.3,.7):
            for k in ((4,7,10) if lab=='Z' else (8,14,20)):
                cx,cy=pa[0]+(pb[0]-pa[0])*f+nx*k,pa[1]+(pb[1]-pa[1])*f+ny*k-3;hh=pg.hits(pg.tbox(cx,cy,txt,DS,an),'iso-self')
                if best is None or hh<best[0]:best=(hh,cx,cy)
                if hh==0:break
            if best[0]==0:break
        pg.t(best[1],best[2],txt,DS,DIMC,an,owner=o);_log(pg,lab+' '+txt,val,name+'.step bbox (iso)',best[0])
def draw_view(pg,name,key,ox,oy,sc,lw=.7,hidden=False):
    V=VW[name][key];e=ext(V['visible']);m=mapper(ox,oy,sc,e[0],e[1])
    if hidden:
        for p in V['hidden']:pg.pl([m(q) for q in p],.3,GRY,(2.5,1.5),owner='hid',reg=False)
    for p in V['visible']:pg.pl([m(q) for q in p],lw)
    return m,e
def draw_flat(pg,name,m,sc,win=None,lw=.8):
    ents=load_cut(name);cv=pg.cv
    if win:
        a=m((win[0],win[1]));b=m((win[2],win[3]));cv.saveState();pth=cv.beginPath();pth.rect(a[0],a[1],b[0]-a[0],b[1]-a[1]);cv.clipPath(pth,stroke=0,fill=0);W=(a[0],a[1],b[0],b[1])
    def reg(pts):
        for i in range(len(pts)-1):
            s_=(*pts[i],*pts[i+1])
            if win:s_=clip_seg(*s_,W)
            if s_:pg.addseg(*s_,'geo')
    cv.setLineWidth(lw)
    for e in ents:
        if e[0]=='L':p,q=m((e[1],e[2])),m((e[3],e[4]));cv.line(*p,*q);reg([p,q])
        elif e[0]=='C':
            c=m((e[1],e[2]));cv.circle(*c,sc*e[3],stroke=1,fill=0);reg([(c[0]+sc*e[3]*math.cos(2*math.pi*k/20),c[1]+sc*e[3]*math.sin(2*math.pi*k/20)) for k in range(21)])
        else:
            c=(e[1],e[2]);r=e[3];a0,a1=e[4],e[5];ext_=(a1-a0)%360;pa=m((c[0]-r,c[1]-r));pb=m((c[0]+r,c[1]+r));cv.arc(*pa,*pb,startAng=a0,extent=ext_)
            reg([m((c[0]+r*math.cos(math.radians(a0+ext_*k/8)),c[1]+r*math.sin(math.radians(a0+ext_*k/8)))) for k in range(9)])
    br=rep['parts'][name]['bend_records'];cv.setStrokeColorRGB(*RED);cv.setLineWidth(1.2);cv.setDash([7,3,1.5,3],0)
    for b in br:
        p,q=m(b['flat_line_mm'][0]),m(b['flat_line_mm'][1]);cv.line(*p,*q);s_=(*p,*q)
        if win:s_=clip_seg(*s_,W)
        if s_:pg.addseg(*s_,'bend_'+b['id'])
    cv.setDash();cv.setStrokeColorRGB(0,0,0)
    if win:cv.restoreState()
    return ents
def circles(ents,d=None):return [(e[1],e[2],2*e[3]) for e in ents if e[0]=='C' and (d is None or abs(2*e[3]-d)<1e-6)]
def bends(name):
    out=[]
    for b in rep['parts'][name]['bend_records']:
        (ax,ay),(bx,by)=b['flat_line_mm'];vert=abs(ax-bx)<1e-6
        out.append(dict(id=b['id'],dir=b['direction'],vert=vert,pos=ax if vert else ay,p0=(ax,ay),p1=(bx,by),R=b['radius_on_selected_skin_mm']))
    return out
def blabel(b):return f"{b['id']} {'上折' if b['dir']=='UP' else '下折'}90° 内R{fg(RI)}"
def bendtable(pg,x,ytop,w,rows,notes,title='折弯表（展开基准：DXF 左下角 X=0 / Y=0；顺序为候选，首件确认）'):
    cols=[('序',24),('折弯',34),('折线位置（距基准）',w-12-24-34-88-36-36),('方向',88),('角度',36),('内R',36)];rh=17
    hgt=24+rh*(len(rows)+1)+15*len(notes)+8;cv=pg.cv
    cv.setFillColorRGB(1,.96,.96);cv.rect(x,ytop-hgt,w,hgt,fill=1,stroke=0);cv.setFillColorRGB(0,0,0)
    o='tbl';pg.line(x,ytop,x+w,ytop,.6,RED,owner=o);pg.line(x,ytop-hgt,x+w,ytop-hgt,.6,RED,owner=o);pg.line(x,ytop,x,ytop-hgt,.6,RED,owner=o);pg.line(x+w,ytop,x+w,ytop-hgt,.6,RED,owner=o)
    pg.t(x+6,ytop-15,title,10,RED,owner=o);yy=ytop-24
    xs=[x+6];[xs.append(xs[-1]+c[1]) for c in cols]
    pg.line(x+4,yy,xs[-1],yy,.3,GRY,owner=o)
    for (c,_),cx in zip(cols,xs):pg.t(cx+2,yy-12,c,9.5,owner=o)
    yy-=rh;pg.line(x+4,yy,xs[-1],yy,.3,GRY,owner=o)
    for i,r in enumerate(rows):
        for v,cx in zip([str(i+1),*r],xs):pg.t(cx+2,yy-12,v,9.5,owner=o)
        yy-=rh;pg.line(x+4,yy,xs[-1],yy,.3,GRY,owner=o)
    for k in range(len(xs)):pg.line(xs[k],ytop-24,xs[k],yy,.3,GRY,owner=o)
    yy-=4
    for n in notes:pg.t(x+6,yy-10,n,9,owner=o);yy-=15
    return ytop-hgt
# ---------------- data ----------------
OUT.mkdir(parents=True,exist_ok=True);path=OUT/f'{VER}_完整折弯工艺PDF_折弯师傅作业图_4页.pdf'
for old in OUT.glob(f'{VER}_完整折弯工艺PDF_*.pdf'):old.unlink()
pg=Pg(path)
h16=sorted(FT['LID']['roof16'],key=lambda q:q['center'][1]);hx=h16[0]['center'][0];hy=[h['center'][1] for h in h16];assert h16[1]['center'][0]==hx   # t13u: along Y, left short edge
assert rep['lid']['handle_holes']==[] and rep['lid']['handle_centres']==[]   # no handle
assert not [h for h in FT['LID']['holes'] if abs(h['axis'][2])>.5 and abs(h['d']-RD)>1e-6]
UB=FT['body']['U'];LB=FT['body']['L'];BOD=[min(UB[0],LB[0]),min(UB[1],LB[1]),min(UB[2],LB[2]),max(UB[3],LB[3]),max(UB[4],LB[4]),max(UB[5],LB[5])];LD=VW['LID']['bbox']
_lh=[h for h in FT['LID']['holes'] if abs(h['d']-4.5)<1e-6];ZL=_lh[0]['center'][2];_bh=FT['U']['holes']+FT['L']['holes'];ZB=_bh[0]['center'][2]
# ================= PAGE 1 : assembly =================
pg.head('箱体 总装三视图 + 斜视图（给折弯师傅）','U+L+盖 3件')
pg.frame(24,36,880,PH-36-80,'总装三视图（第一角画法；尺寸取自 ASSEMBLY.step；基准 = 箱体外面 x=0 / y=0 / 底面 z=0）')
sc=.9;FX=96;FY=560   # 420x180x175 (total height 175: FY lowered): sc .9 (as 001)
mf,ef=draw_view(pg,'ASSEMBLY','front',FX,FY,sc);ml,el=draw_view(pg,'ASSEMBLY','left',FX+sc*(ef[2]-ef[0])+72,FY,sc)
TY=FY-sc*(ef[3]-ef[1])*0-46-sc*(VW['LID']['bbox'][4]-VW['LID']['bbox'][1]);mt,et=draw_view(pg,'ASSEMBLY','top',FX,TY,sc)
for key,m_,e_ in (('主视',mf,ef),('左视',ml,el),('俯视',mt,et)):pg.VL.append((m_,e_,key))
# body outline (hidden, from U∪L bbox) in top view
bx0,by0,bx1,by1=BOD[0],BOD[1],BOD[3],BOD[4];pg.pl([mt((bx0,by0)),mt((bx1,by0)),mt((bx1,by1)),mt((bx0,by1))],.4,GRY,(3,2),owner='hid',close=True)
# front view
ftop=mf((0,ef[3]))[1];fbot=mf((0,ef[1]))[1]
dimH(pg,mf((LD[0],Hz)),mf((LD[3],Hz)),ftop+16,LD[3]-LD[0],'LID.step bbox X (盖外形)')
dimH(pg,mf((BOD[0],0)),mf((BOD[3],0)),fbot-16,BOD[3]-BOD[0],'U∪L bbox X (箱体外形)')
dimV(pg,mf((ef[0],0)),mf((LD[0],Hz)),mf((ef[0],0))[0]-16,Hz,'ASSEMBLY.step bbox Z (总高含盖)')
xr=mf((ef[2],0))[0];dimV(pg,mf((BOD[3],0)),mf((BOD[3],BOD[5])),xr+16,BOD[5]-BOD[2],'U∪L bbox Z (箱体高)')
dimV(pg,mf((LD[3],LD[2])),mf((LD[3],LD[5])),xr+16+LEV*2.2,LD[5]-LD[2],'LID.step bbox Z (盖裙高)')
# left view (horizontal coord = -y)
ltop=ml((0,el[3]))[1];lbot=ml((0,el[1]))[1]
dimH(pg,ml((-LD[4],Hz)),ml((-LD[1],Hz)),ltop+16,LD[4]-LD[1],'LID.step bbox Y (盖外形)')
dimH(pg,ml((-BOD[4],0)),ml((-BOD[1],0)),lbot-16,BOD[4]-BOD[1],'U∪L bbox Y (箱体外形)')
dimV(pg,ml((-LD[1],0)),ml((-LD[1],Hz)),ml((el[2],0))[0]+16,Hz,'ASSEMBLY.step bbox Z (总高含盖)')
# top view: roof holes (O12 x2 along X, near front long edge y=0)
for h in h16:c=mt(h['center'][:2]);cmark(pg,c,sc*RR)
pg.line(*mt((-12,Wy/2)),*mt((60,Wy/2)),.3,GRY,(6,2,1,2),owner='cl')
tb=mt((0,et[1]))[1]
end=stack(pg,'H',mt((0,0)),[(mt((hx,hy[0])),hx,sc*RR+1.5,'roof holes centre X (box x=0)'),(mt((BOD[3],0)),BOD[3]-BOD[0],1.5,'body X')],tb,-1,'ASSEMBLY top, datum box x=0')
dimH(pg,mt((LD[0],LD[1])),mt((LD[3],LD[1])),end-LEV,LD[3]-LD[0],'LID.step bbox X')
xl_=mt((et[0],0))[0]
end=stack(pg,'V',mt((0,0)),[(mt((hx,hy[0])),hy[0],sc*RR+1.5,'roof hole1 centre Y (box y=0)'),(mt((hx,hy[1])),hy[1],sc*RR+1.5,'roof hole2 centre Y (box y=0)'),(mt((0,BOD[4])),BOD[4]-BOD[1],1.5,'body Y')],xl_,-1,'ASSEMBLY top, datum box y=0')
dimV(pg,mt((LD[0],LD[1])),mt((LD[0],LD[4])),end-LEV,LD[4]-LD[1],'LID.step bbox Y')
xp_=mt((hx+RR,0))[0]+24
dimV(pg,mt((hx,hy[0])),mt((hx,hy[1])),xp_,hy[1]-hy[0],'roof hole pitch ΔY (LID.step)',ga=sc*RR+1.5,gb=sc*RR+1.5,hside=1)
dimV(pg,mt((0,0)),mt((hx,(hy[0]+hy[1])/2)),xp_+LEV+14,(hy[0]+hy[1])/2,'hole pair centre Y = W/2',txt=fmt(Wy/2)+'（居中）',ga=1.5,gb=xp_-mt((hx,0))[0]+16,hside=1)   # ext line starts past the pitch-30 text
dimH(pg,mt((LD[0],hy[1])),mt((hx,hy[1])),mt((0,hy[1]+RR))[1]+16,hx-LD[0],'roof hole centre X - lid outer edge (LID.step)',ga=1.5,gb=sc*RR+1.5)
dimH(pg,mt((LD[0],hy[0])),mt((hx-RR,hy[0])),mt((0,hy[0]-RR))[1]-16,hx-RR-LD[0],'roof hole edge - lid outer edge (LID.step)',ga=1.5,gb=1.5)
callout(pg,mt((hx,hy[1])),sc*RR,f'Ø{fmt(RD)}×2 通孔','LID roof inner circles d=%g'%RD,RD,RED,9.5,angs=(45,30,60,-45))
yN=end-LEV
nt=[f'俯视基准：箱体外面 x=0（左）/ y=0（前），虚线=箱体外形 {fmt(BOD[3]-BOD[0])}×{fmt(BOD[4]-BOD[1])}；盖外沿比箱体每边大 {fmt(-LD[0])}',
    f'Ø{fmt(RD)}×2：中心 ({fmt(hx)},{fmt(hy[0])}) / ({fmt(hx)},{fmt(hy[1])})（箱体基准），靠左短边 {fg(Wy)}，沿 {fg(Wy)} 方向孔距 {fmt(hy[1]-hy[0])}，关于 Y={fmt(Wy/2)} 居中',
    f'孔心距盖左外边 {fmt(hx-LD[0])}，孔边距盖外边 {fmt(hx-LD[0]-RR)}（开孔距离离边50 = 孔心距盖外边）；盖宽 {fg(LD[4]-LD[1])} 也居中；不设把手']
yy=mt((0,et[1]))[1]-14-LEV*5-24
for s_ in nt:pg.ft(40,yy,s_,9.5,DIMC);yy-=15
IX=914;IW=PW-24-IX;pg.frame(IX,PH-80-330,IW,330,'总装斜视（实测 STEP，标注外形）');isoview(pg,'ASSEMBLY',IX,PH-80-330,IW,312)
ky=PH-80-330-8;pg.cv.setFillColorRGB(1,.97,.88);pg.cv.rect(IX,36,IW,ky-36,fill=1,stroke=0);pg.cv.setFillColorRGB(0,0,0);pg.frame(IX,36,IW,ky-36,'说明')
yy=ky-34
for txt,c in [('三件：件01 U(左/后/右)×1　件02 L(前+底)×1',BLK),('　　　件03 LID 盖×1',BLK),
              (('L 盖住 U：L外露边与U外面齐平（0缝不退让）' if abs(_S)<1e-9 else f'L 盖住 U：L外露边比U外面退 {fmt(_S)}'),RED),(('盖裙转角：长裙盖短裙端头，外露端齐平（不退让），' if abs(_SL)<1e-9 else f'盖裙转角(同003)：长裙盖短裙端头，外露端退 {fmt(_SL)}，'),RED),('　短裙端顶死长裙内面 0 缝',RED),
              (f'U/L 上沿 Ø3.3×{len(_bh)} 攻 M4（中心离箱体顶 {fmt(BOD[5]-ZB)}）',BLK),(f'盖裙 Ø4.5×{len(_lh)}（中心离盖顶 {fmt(Hz-ZL)}）',BLK),*([(f'警告：t{fg(TT)}直接攻M4仅约1扣有效螺纹，',RED),('强度偏低、易滑牙，不建议反复拆装；',RED),('压铆/拉铆/点焊螺母替代：待确认',RED)] if TT<=1.2+1e-9 else []),   # user t52u
              (f'盖顶与箱体上沿间隙 {fmt(Hz-TT-BOD[5])}；盖裙高 {fmt(LD[5]-LD[2])}',BLK),(f'展开按 内R{fg(RI)} / K={fg(P["K_ANSI"])}（经验值，未标定）',BLK),
              ('各件展开与孔位尺寸见第 2–4 页',BLK),('首件：机台___ 上模___ 下模___',BLK),('　　　回弹___ 签字___',BLK)]:
    pg.t(IX+10,yy,txt,10,c,owner='notes');yy-=19
pg.foot()
# ================= PART PAGES =================
NAMES={'U':'件01 U 三面包（左/后/右）','L':f'件02 L 前板+底板（盖住U，{_stx(_S)}）','LID':f'件03 LID 盖（Φ{fmt(RD)}×2，无把手；长裙盖短裙{_stx(_SL)}）'}
def flat_common(name,m,sc,ents,lab_owner=True):
    for b in bends(name):pg.BL.append((m(b['p0']),m(b['p1']),blabel(b),'bend_'+b['id']))
    for (x,y,d) in circles(ents):cmark(pg,m((x,y)),sc*d/2)
def bend_rows(name,order=None):
    bs=bends(name)
    if order:bs=sorted(bs,key=lambda b:order.index(b['id']))
    return [(b['id'],f"{'X' if b['vert'] else 'Y'} = {fmt(b['pos'])}（距{'左' if b['vert'] else '下'}边）",'上折(朝看图者)' if b['dir']=='UP' else '下折(背离)','90°',f'{fmt(b["R"] if b["dir"]=="UP" else RI)}') for b in bs]
# ---------- PAGE 2: U ----------
pg.head(NAMES['U']+'　—　展开尺寸 / 成形尺寸 / 折弯','本页：U')
ents=load_cut('U');fw,fh=rep['parts']['U']['flat_size']
pg.frame(24,436,PW-48,PH-80-436,'U 展开图（激光 DXF 同源，图示比例不按纸量；红点划线 = 折弯线；基准 = 左边 X=0 / 下边 Y=0）',(.6,.1,.1))
sc=0.94;m=mapper(92,492,sc,0,0);draw_flat(pg,'U',m,sc);flat_common('U',m,sc,ents)   # 180x420x175: U flat 774.6 x 172.8 -> sc 0.94
H=circles(ents);top=m((0,fh))[1];bot=m((0,0))[1]
stack(pg,'H',m((0,fh)),[(m((x,y)),x,sc*d/2+1.5,f'U.dxf circle X') for x,y,d in H],top,1,'U.dxf datum left edge')
bs=bends('U');e_=stack(pg,'H',m((0,0.8)),[(m((b['pos'],0)),b['pos'],1.5,b['id']+' bend line') for b in bs],bot,-1,'U_BEND.dxf datum left edge')
dimH(pg,m((0,0.8)),m((fw,0.8)),e_-LEV,fw,'U.dxf flat bbox X')
hl=min(H);dimV(pg,m((0.8,0)),m((hl[0],hl[1])),m((0,0))[0]-16,hl[1],'U.dxf circle Y from bottom edge',gb=sc*hl[2]/2+1.5)
dimV(pg,m((0.8,0)),m((0,fh)),m((0,0))[0]-16-LEV,fh,'U.dxf flat bbox Y')
hr=max(H);dimV(pg,m((fw,fh)),m((hr[0],hr[1])),m((fw,0))[0]+16,fh-hr[1],'U.dxf top edge - circle Y',gb=sc*hr[2]/2+1.5)
callout(pg,m((H[2][0],H[2][1])),sc*H[2][2]/2,f'Ø{fmt(H[0][2])}×{len(H)} 攻M4','U.dxf circles',H[0][2])
arcs=[e for e in ents if e[0]=='A'];callout(pg,m((arcs[0][1]-arcs[0][3]*.7071,arcs[0][2]-arcs[0][3]*.7071)),0,f'R{fmt(arcs[0][3])}×{len(arcs)}（下角）','U.dxf arcs',arcs[0][3])
# formed views
pg.frame(24,36,616,392,'U 成形三视图（第一角；尺寸取自 U.step）')
sc=.58;fx=92;mf,ef=draw_view(pg,'U','front',fx,250,sc);ml,el=draw_view(pg,'U','left',fx+sc*Lx+62,250,sc);mt,et=draw_view(pg,'U','top',fx,96,sc)
for key,m_,e_ in (('主视',mf,ef),('左视',ml,el),('俯视',mt,et)):pg.VL.append((m_,e_,key))
ub=VW['U']['bbox'];hb=sorted([h for h in FT['U']['holes'] if abs(h['axis'][1])>.5],key=lambda h:h['center'][0]);hs_=sorted([h for h in FT['U']['holes'] if h['axis'][0]<-.5],key=lambda h:h['center'][1])
for h in hb:cmark(pg,mf((h['center'][0],h['center'][2])),sc*h['d']/2)
ft_=mf((0,ub[5]))[1]
e_=stack(pg,'H',mf((ub[0],ub[5])),[(mf((h['center'][0],h['center'][2])),h['center'][0]-ub[0],sc*h['d']/2+1.5,'back-wall hole X') for h in hb],ft_,1,'U.step datum left outer face')
dimH(pg,mf((ub[0],ub[5])),mf((ub[3],ub[5])),e_+LEV,ub[3]-ub[0],'U.step bbox X')
dimV(pg,mf((ub[0],ub[2])),mf((ub[0],ub[5])),mf((ub[0],0))[0]-16,ub[5]-ub[2],'U.step bbox Z')
dimV(pg,mf((ub[3],ub[5])),mf((hb[-1]['center'][0],hb[-1]['center'][2])),mf((ub[3],0))[0]+14,ub[5]-hb[-1]['center'][2],'U.step top - hole centre Z',gb=sc*hb[-1]['d']/2+1.5)
for h in hs_:cmark(pg,ml((-h['center'][1],h['center'][2])),sc*h['d']/2)
lt=ml((0,ub[5]))[1]
e_=stack(pg,'H',ml((-ub[1],ub[5])),[(ml((-h['center'][1],h['center'][2])),h['center'][1]-ub[1],sc*h['d']/2+1.5,'side-wall hole Y from front end') for h in hs_],lt,1,'U.step datum front end y=1')
dimH(pg,ml((-ub[1],ub[5])),ml((-ub[4],ub[5])),e_+LEV,ub[4]-ub[1],'U.step bbox Y')
dimV(pg,mt((ub[0],ub[1])),mt((ub[0],ub[4])),mt((ub[0],0))[0]-16,ub[4]-ub[1],'U.step bbox Y')
r_=RI;callout(pg,mt((ub[0]+TT+r_-r_*.7071,ub[4]-TT-r_+r_*.7071)),0,f'B1 内R{fg(RI)}','U.step inner bend radius',RI,RED)
callout(pg,mt((ub[3]-TT-r_+r_*.7071,ub[4]-TT-r_+r_*.7071)),0,f'B2 内R{fg(RI)}','U.step inner bend radius',RI,RED)
callout(pg,mt((ub[0]+TT/2,(ub[1]+ub[4])/2)),0,f't{fg(TT)}','U.step thickness',TT,BLK,dot=True)
pg.t(40,46,f'U 前端开口（Y={fmt(ub[1])}），成形后被 L 前板挡住；下端 Z={fmt(ub[2])} 落在 L 底板上。',9.5,owner='n')
yb=bendtable(pg,650,428,PW-24-650,bend_rows('U'),['两道折弯同向：左侧板、后板、右侧板一体；上折 = 朝 DXF 正面（看图者）方向。','折线 = 弯曲区中线（展开 DXF BEND 层）；孔、外形按 CUT 层激光切割。',f'Ø3.3×{len(H)} 攻 M4，孔心离成形上沿 {fmt(fh-H[0][1])}。'])
pg.frame(650,36,PW-24-650,yb-44,'U 斜视（实测外形）');isoview(pg,'U',650,36,PW-24-650,yb-52)
pg.foot()
# ---------- PAGE 3: L ----------
pg.head(NAMES['L']+'　—　展开尺寸 / 成形尺寸 / 折弯','本页：L')
ents=load_cut('L');fw,fh=rep['parts']['L']['flat_size']
pg.frame(24,322,616,PH-80-322,'L 展开图（激光 DXF 同源；红点划线 = 折弯线；基准 = 左边 X=0 / 下边 Y=0）',(.6,.1,.1))
sc=.9;m=mapper(112,410,sc,0,0);draw_flat(pg,'L',m,sc);flat_common('L',m,sc,ents)
H=circles(ents);bot=m((0,0))[1]
e_=stack(pg,'H',m((0,0)),[(m((x,y)),x,sc*d/2+1.5,'L.dxf circle X') for x,y,d in H],bot,-1,'L.dxf datum left edge')
dimH(pg,m((0,0)),m((fw,0)),e_-LEV,fw,'L.dxf flat bbox X')
b=bends('L')[0];hl=min(H);arcs=[e for e in ents if e[0]=='A']
e_=stack(pg,'V',m((0,0)),[(m((hl[0],hl[1])),hl[1],sc*hl[2]/2+1.5,'circle Y'),(m(b['p0']),b['pos'],1.5,'B1 bend line'),(m((arcs[0][1],fh)),fh,1.5,'flat bbox Y')],m((0,0))[0],-1,'L.dxf datum bottom edge')
callout(pg,m((H[1][0],H[1][1])),sc*H[1][2]/2,f'Ø{fmt(H[0][2])}×{len(H)} 攻M4','L.dxf circles',H[0][2])
a0=max(arcs,key=lambda a:a[1]);callout(pg,m((a0[1]+a0[3]*.7071,a0[2]+a0[3]*.7071)),0,f'R{fmt(a0[3])}×{len(arcs)}（后角）','L.dxf arcs',a0[3])
pg.t(m((fw*.5,b['pos']*.5))[0],m((0,b['pos']*.5))[1],'前板（成形后竖直）',10,GRY,'c',owner='n');pg.t(m((fw*.5,0))[0],m((0,(b['pos']+fh)*.5))[1],'底板',10,GRY,'c',owner='n')
pg.frame(650,322,PW-24-650,PH-80-322,'L 成形三视图（第一角；尺寸取自 L.step）')
sc=.48;fx=716;mf,ef=draw_view(pg,'L','front',fx,598,sc);ml,el=draw_view(pg,'L','left',fx+sc*(Lx-0.4)+62,598,sc);mt,et=draw_view(pg,'L','top',fx,438,sc)
for key,m_,e_ in (('主视',mf,ef),('左视',ml,el),('俯视',mt,et)):pg.VL.append((m_,e_,key))
lb=VW['L']['bbox'];hb=sorted(FT['L']['holes'],key=lambda h:h['center'][0])
for h in hb:cmark(pg,mf((h['center'][0],h['center'][2])),sc*h['d']/2)
ft_=mf((0,lb[5]))[1]
e_=stack(pg,'H',mf((lb[0],lb[5])),[(mf((h['center'][0],h['center'][2])),h['center'][0]-lb[0],sc*h['d']/2+1.5,'front-plate hole X') for h in hb],ft_,1,'L.step datum left edge')
dimH(pg,mf((lb[0],lb[5])),mf((lb[3],lb[5])),e_+LEV,lb[3]-lb[0],'L.step bbox X')
dimV(pg,mf((lb[0],lb[2])),mf((lb[0],lb[5])),mf((lb[0],0))[0]-16,lb[5]-lb[2],'L.step bbox Z')
dimV(pg,mf((lb[3],lb[5])),mf((hb[-1]['center'][0],hb[-1]['center'][2])),mf((lb[3],0))[0]+14,lb[5]-hb[-1]['center'][2],'L.step top - hole centre Z',gb=sc*hb[-1]['d']/2+1.5)
dimH(pg,ml((-lb[4],lb[2])),ml((-lb[1],lb[2])),ml((0,lb[2]))[1]-16,lb[4]-lb[1],'L.step bbox Y')
callout(pg,ml((-(TT+RI-RI*.7071),TT+RI-RI*.7071)),0,f'B1 内R{fg(RI)}','L.step inner bend radius',RI,RED)
callout(pg,ml((-TT/2,lb[5]*.6)),0,f't{fg(TT)}','L.step thickness',TT,BLK,dot=True)
dimV(pg,mt((lb[0],lb[1])),mt((lb[0],lb[4])),mt((lb[0],0))[0]-16,lb[4]-lb[1],'L.step bbox Y')
pg.ft(fx-40,mt((0,lb[1]))[1]-30,(f'L 外露边与 U 外面齐平（0缝不退让）' if abs(_S)<1e-9 else f'L 外露边比 U 外面退 {fmt(_S)}')+f'（L 左右边 X={fmt(lb[0])}/{fmt(lb[3])}，U 外面 X=0/{fmt(Lx)}）',9.5,RED,'n')
yb=bendtable(pg,24,312,616,bend_rows('L'),['只一道折弯（前板与底板交界）；上折 = 朝 DXF 正面（看图者）。',f'底板后两角 R{fmt(a0[3])}（与 U 外角同心）。',f'Ø3.3×{len(H)} 攻 M4，孔心离前板上沿 {fmt(H[0][1])}。'])
pg.frame(650,36,PW-24-650,278,'L 斜视（实测外形）');isoview(pg,'L',650,36,PW-24-650,262)
pg.foot()
# ---------- PAGE 4: LID ----------
pg.head(NAMES['LID']+'　—　展开尺寸 / 成形尺寸 / 折弯','本页：LID')
ents=load_cut('LID');fw,fh=rep['parts']['LID']['flat_size'];CO=rep['parts']['LID']['profile03']['corner_outline_flat_bl']
pg.frame(24,288,812,PH-80-288,'LID 展开图（激光 DXF 同源；红点划线 = 折弯线；基准 = 左边 X=0 / 下边 Y=0）',(.6,.1,.1))
sc=1.0;m=mapper(118,400,sc,0,0);draw_flat(pg,'LID',m,sc);flat_common('LID',m,sc,ents)
C=circles(ents);C16=circles(ents,RD);C66=circles(ents,6.6);C45=circles(ents,4.5);assert len(C16)==2 and len(C66)==0 and len(C45)==sum(1 for h in FT['LID']['holes'] if abs(h['d']-4.5)<1e-6)==10
sk_bot=sorted([c for c in C45 if c[1]<10],key=lambda c:c[0]);sk_top=sorted([c for c in C45 if c[1]>fh-10]);sk_l=sorted([c for c in C45 if c[0]<10],key=lambda c:c[1]);sk_r=sorted([c for c in C45 if c[0]>fw-10],key=lambda c:c[1])
assert len(sk_bot)==len(sk_top)>=2 and len(sk_l)==len(sk_r)>=2 and len(sk_bot)+len(sk_top)+len(sk_l)+len(sk_r)==len(C45)
bs={b['id']:b for b in bends('LID')};A_=CO[4][1];XL=CO[0][0]   # short-flange edge Y (14.28), long-flange tip X (13.49)
g=lambda c:sc*c[2]/2+1.5
bot=m((0,0))[1];top=m((0,fh))[1];lft=m((0,0))[0];rgt=m((fw,0))[0]
e_=stack(pg,'H',m((0,A_)),[(m(sk_l[0][:2]),sk_l[0][0],g(sk_l[0]),'left skirt hole X')]+[(m(c[:2]),c[0],g(c),'front skirt hole X') for c in sk_bot]+[(m(sk_r[0][:2]),sk_r[0][0],g(sk_r[0]),'right skirt hole X')],bot,-1,'LID.dxf datum left edge X=0')
dimH(pg,m((0,A_)),m((fw,A_)),e_-LEV,fw,'LID.dxf flat bbox X')
up=[(m((bs['B1']['p0'][0],max(bs['B1']['p0'][1],bs['B1']['p1'][1]))),bs['B1']['pos'],1.5,'B1 bend line'),(m((bs['B4']['p0'][0],max(bs['B4']['p0'][1],bs['B4']['p1'][1]))),bs['B4']['pos'],1.5,'B4 bend line')]
stack(pg,'H',m((0,fh-A_)),up,top,1,'LID.dxf datum left edge X=0')
lf=[(m(c[:2]),c[1],g(c),'left skirt hole Y') for c in sk_l]
e_=stack(pg,'V',m((XL,0)),lf,lft,-1,'LID.dxf datum bottom edge Y=0')
dimV(pg,m((XL,0)),m((XL,fh)),e_-LEV,fh,'LID.dxf flat bbox Y')
rf=[(m(sk_bot[-1][:2]),sk_bot[-1][1],g(sk_bot[-1]),'front skirt hole Y'),(m(sk_top[-1][:2]),sk_top[-1][1],g(sk_top[-1]),'back skirt hole Y'),(m((max(bs['B2']['p0'][0],bs['B2']['p1'][0]),bs['B2']['pos'])),bs['B2']['pos'],1.5,'B2 bend line'),(m((max(bs['B3']['p0'][0],bs['B3']['p1'][0]),bs['B3']['pos'])),bs['B3']['pos'],1.5,'B3 bend line')]
stack(pg,'V',m((fw-XL,0)),rf,rgt,1,'LID.dxf datum bottom edge Y=0')
# local roof-hole dims inside the flat (holes along X near the front long edge)
c0,c1=sorted(C16,key=lambda c:c[1])   # t13u: along Y near the left short skirt (B1)
yq=m((0,c1[1]+RR+16))[1]
dimH(pg,m((0,c1[1])),m(c1[:2]),yq,c1[0],'LID.dxf roof hole centre X (local, from left edge X=0)',gb=g(c1))
dimH(pg,m((bs['B1']['pos'],c1[1])),m(c1[:2]),yq+LEV,c1[0]-bs['B1']['pos'],'LID.dxf roof hole centre X - B1 bend line',gb=g(c1))
xq=m((c1[0]+40,0))[0]
dimV(pg,m((c0[0],0)),m(c0[:2]),xq,c0[1],'LID.dxf roof hole1 centre Y (local, from bottom edge Y=0)',gb=g(c0))
dimV(pg,m((c1[0],0)),m(c1[:2]),xq+LEV,c1[1],'LID.dxf roof hole2 centre Y (local, from bottom edge Y=0)',gb=g(c1))
dimV(pg,m(c0[:2]),m(c1[:2]),m((c1[0]+RR+12,0))[0],c1[1]-c0[1],'LID.dxf roof hole pitch',ga=g(c0),gb=g(c1),hside=1)
callout(pg,m(c0[:2]),sc*RR,f'Ø{fmt(RD)}×2 通孔','LID.dxf circles d=%g'%RD,RD,RED,angs=(-45,-30,-60,30,45))
callout(pg,m(sk_bot[1][:2]),sc*2.25,f'Ø{fmt(C45[0][2])}×{len(C45)} 裙边孔','LID.dxf circles d=4.5',4.5)
pg.ft(40,294,f'上下裙孔 X 相同、左右裙孔 Y 相同（对称）；Ø{fmt(RD)}×2 靠 B1 短边裙，关于展开中线 Y={fmt(fh/2)} 对称；无把手孔。',9,GRY)
# --- flat corner detail
DX,DY,DW,DH=846,470,PW-24-846,PH-80-470
pg.frame(DX,DY,DW,DH,'局部 A：展开图左下角 V 口（放大 8:1，DXF 实测，其余 3 角镜像）',(.6,.1,.1))
sc=8.0;win=(-2,-2,21,21);m=mapper(DX+92,DY+76,sc,win[0],win[1]);draw_flat(pg,'LID',m,sc,win,1.0)
P0,P1,P2,P3,P4=[tuple(p) for p in CO]
e_=stack(pg,'H',m((0,P4[1])),[(m(P3),P3[0],1.5,'short-flange end corner X'),(m(P0),P0[0],1.5,'long-flange tip X'),(m((bs['B1']['pos'],win[1])),bs['B1']['pos'],0,'B1 bend line X'),(m(P2),P2[0],1.5,'V apex X')],m((0,win[1]))[1],-1,'LID.dxf corner')
BLB=min((bs['B2'],bs['B3']),key=lambda b:b['pos'])   # bottom long-skirt bend (id order from the skill differs per job)
e_=stack(pg,'V',m((P0[0],0)),[(m(P1),P1[1],1.5,'long-flange tip end Y'),(m((win[0],BLB['pos'])),BLB['pos'],0,BLB['id']+' bend line Y'),(m(P4),P4[1],1.5,'short-flange edge Y'),(m(P2),P2[1],1.5,'V apex Y')],m((win[0],0))[0],-1,'LID.dxf corner')
callout(pg,m(((P0[0]+P1[0])/2,6)),0,f'长裙端 X{fmt(P0[0])}（{_stx(_SL)}）','LID.dxf long flange tip',P0[0],RED,8.5,angs=(180,),lens=(14,10,18))
callout(pg,m((6,P4[1])),0,'短裙端（0 缝）','LID.dxf short flange end',P4[1],RED,8.5,angs=(90,110,70,130),lens=(30,45,60))
callout(pg,m(P2),0,'V 口顶点','LID.dxf notch apex',None,DIMC,8.5,angs=(45,30,60,15),lens=(30,45,60))
pg.ft(DX+8,DY+8,f'B1/{BLB["id"]} 折线 = {fmt(bs["B1"]["pos"])}；'+(f'长裙端比无退让时 {fmt(P0[0]-_SL)} 外移 {fmt(_SL)}。' if abs(_SL)>1e-9 else '长裙端不退让（与短裙外面齐平）。'),8.5,GRY)
# --- formed corner section (STEP slice Z=H-8)
SX,SY,SW,SH=846,250,PW-24-846,212
pg.frame(SX,SY,SW,SH,f'局部 B：成形盖角水平剖面 Z={fmt(Hz-8)}（LID.step 实测，俯视）',(.1,.4,.1))
sec=json.load(open(Wd/'corner_mesh.json'))['sec'][0];sc=21.0;m=mapper(SX+110,SY+44,sc,-2.2,-2.2);WB=(-2.2,-2.2,3.4,3.4)
wa=m(WB[:2]);wb=m(WB[2:]);cv_=pg.cv;cv_.saveState();cp=cv_.beginPath();cp.rect(wa[0],wa[1],wb[0]-wa[0],wb[1]-wa[1]);cv_.clipPath(cp,stroke=0,fill=0)
cv_.setFillColorRGB(.8,.88,.8);p=cv_.beginPath();p.moveTo(*m(sec[0]))
for q in sec[1:]:p.lineTo(*m(q))
p.close();cv_.drawPath(p,fill=1,stroke=0);cv_.setFillColorRGB(0,0,0);pg.pl([m(q) for q in sec],1.0,close=True,reg=False);cv_.restoreState()
for i in range(len(sec)):
    s_=clip_seg(*m(sec[i]),*m(sec[(i+1)%len(sec)]),(wa[0],wa[1],wb[0],wb[1]))
    if s_:pg.addseg(*s_,'geo')
for (a_,b_) in (((WB[0],WB[3]),(-1.5+0.0,WB[3])),):pass
xs_=[q[0] for q in sec];ys_=[q[1] for q in sec];xo=min(xs_);yo=min(ys_);xe=min(q[0] for q in sec if abs(q[1]-yo)<1e-6);yi=max(q[1] for q in sec if abs(q[0]-xo)<1e-6 and q[1]<0)
xi=max(q[0] for q in sec if abs(q[1]-6.5)<1e-6 and q[0]<2);yi2=max(q[1] for q in sec if abs(q[0]-6.5)<1e-6 and q[1]<2)
pg.line(*m((xe,yi)),*m((xi,yi)),.5,BLK,(1.5,1.2))
if abs(xe-xo)>1e-6:dimH(pg,m((xo,yi)),m((xe,yo)),m((0,yo))[1]-16,xe-xo,'LID.step section: long-skirt end X - short-skirt outer X (setback)',gb=1.5)
else:pg.ft(m((xo,yo))[0],m((0,yo))[1]-16,'长裙端与短裙外面齐平（0退让）',8.5,RED)
dimH(pg,m((xo,3.0)),m((xi,3.0)),m((0,3.0))[1],xi-xo,'LID.step section: short-skirt thickness',txt=f't{fmt(xi-xo)}')
dimV(pg,m((2.9,yo)),m((2.9,yi2)),m((2.9,0))[0],yi2-yo,'LID.step section: long-skirt thickness',txt=f't{fmt(yi2-yo)}')
callout(pg,m(((xe+xi)/2,yi)),0,'0 缝（短裙端顶死长裙内面）','LID.step section',0.0,RED,8.5,angs=(45,30,60),lens=(40,60,80),dot=True)
pg.t(m((0.9,-1.0))[0],m((0,-1.0))[1]-3,f'长边裙（{fg(Lx)} 侧）',8.5,GRN,'c',owner='n');pg.t(m((-1.0,1.2))[0]+3,m((0,1.2))[1],f'短边裙({fg(Wy)}侧)',8,GRN,'c',90,owner='n')
pg.ft(SX+8,SY+20,f'局部截取 X/Y -2.2…3.4；盖外沿 X={fmt(xo)} / Y={fmt(yo)}；长裙端 X={fmt(xe)}（'+(f'退 {fmt(xe-xo)}' if abs(xe-xo)>1e-6 else '齐平，不退让')+'）。',8,GRY);pg.ft(SX+8,SY+8,'仅 R1.8 外圆角顶点留 ≤约0.6 工艺小孔（焊/补）。',8,GRY)
# --- formed views (bottom-left)
pg.frame(24,36,470,244,'LID 成形主视 / 俯视（第一角；尺寸取自 LID.step；基准 = 盖外沿）')
sc=.55;fx=104;mf,ef=draw_view(pg,'LID','front',fx,212,sc);mt,et=draw_view(pg,'LID','top',fx,86,sc)
for key,m_,e_ in (('主视',mf,ef),('俯视',mt,et)):pg.VL.append((m_,e_,key))
lb=LD;dimH(pg,mf((lb[0],lb[5])),mf((lb[3],lb[5])),mf((0,lb[5]))[1]+14,lb[3]-lb[0],'LID.step bbox X')
fr=mf((lb[3],0))[0];hk=max([h for h in FT['LID']['holes'] if abs(h['d']-4.5)<1e-6 and h['axis'][1]<-.5],key=lambda h:h['center'][0])
dimV(pg,mf((lb[3],lb[2])),mf((lb[3],lb[5])),fr+14,lb[5]-lb[2],'LID.step bbox Z (skirt)')
dimV(pg,mf((lb[3],lb[5])),mf((hk['center'][0],hk['center'][2])),fr+14+LEV*2,lb[5]-hk['center'][2],'LID.step top - skirt hole centre Z',gb=sc*2.25+1.5)
for h in h16:cmark(pg,mt(h['center'][:2]),sc*RR)
dimV(pg,mt((lb[0],lb[1])),mt((lb[0],lb[4])),mt((lb[0],0))[0]-16,lb[4]-lb[1],'LID.step bbox Y')
xs_=mt((hx,0))[0]+sc*RR+12
end=stack(pg,'V',mt((lb[0],lb[1])),[(mt((hx,hy[0])),hy[0]-lb[1],sc*RR+1.5,'roof hole1 centre Y from lid edge'),(mt((hx,hy[1])),hy[1]-lb[1],sc*RR+1.5,'roof hole2 centre Y from lid edge')],xs_-14,1,'LID.step datum lid outer edge Y')
dimV(pg,mt((hx,hy[0])),mt((hx,hy[1])),end+LEV,hy[1]-hy[0],'LID.step roof hole pitch ΔY',ga=sc*RR+1.5,gb=sc*RR+1.5,hside=1)
dimH(pg,mt((lb[0],hy[1])),mt((hx,hy[1])),mt((0,hy[1]+RR))[1]+14,hx-lb[0],'LID.step roof hole centre X from lid outer edge',ga=1.5,gb=sc*RR+1.5)
dimH(pg,mt((lb[0],hy[0])),mt((hx-RR,hy[0])),mt((0,hy[0]-RR))[1]-14,hx-RR-lb[0],'LID.step roof hole edge to lid outer edge',ga=1.5,gb=1.5)
bo=['B1','B4','B2','B3']
yb=bendtable(pg,502,280,336,[(r[0],r[1].replace('（距','（').replace('边）','边）'),r[2],r[3],r[4]) for r in bend_rows('LID',bo)],
   ['顺序：先 B1/B4 短边裙，后 B2/B3 长边裙盖住短裙端头。','下折 = 背离 DXF 正面（看图者）；裙高 15。',f'Ø{fmt(RD)}×2：孔心距盖左外边 {fmt(hx-lb[0])}（孔边 {fmt(hx-lb[0]-RR)}），孔距 {fmt(hy[1]-hy[0])} 居中；转角见局部 A/B。'],title='折弯表（基准 DXF 左下角；顺序见下）')
pg.frame(846,36,PW-24-846,206,'LID 斜视（实测外形）');isoview(pg,'LID',846,36,PW-24-846,190)
pg.foot()
pg.cv.save()
json.dump(LOG,open(B/'logs'/'bend_pdf_dimension_sources.json','w'),ensure_ascii=False,indent=1)
json.dump({'pages':pg.report,'placement_issues':ISSUES},open(B/'logs'/'bend_pdf_layout_check.json','w'),ensure_ascii=False,indent=1)
print(path,len(LOG),'placement issues',len(ISSUES))
