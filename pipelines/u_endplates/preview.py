# v2.8.3 pipeline u_endplates PREVIEW (vendored from order box-400x220x150 t46u): PDF_P1, lid top crop, NEST, end-corner isos, LID_CORNER03_CLOSEUP, LID_FLAT_CORNER03_DETAIL.
# PREVIEW PNGs for the confirm draft (run with addendum-venv python): preview.py STAGE_DIR
import sys,subprocess,shutil,json
from pathlib import Path
import ezdxf,matplotlib
matplotlib.use('Agg');import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from PIL import Image,ImageDraw,ImageFont
sys.path.insert(0,str(Path(__file__).parent));from cfg import VER
S=Path(sys.argv[1]);W_=Path('work');P=S/'PREVIEW';P.mkdir(exist_ok=True)
CJK=[f for f in fm.findSystemFonts() if 'NotoSansCJK' in f or 'wqy' in f.lower() or 'SourceHan' in f]
FP=fm.FontProperties(fname=CJK[0]) if CJK else None
pdf=S/f'{VER}_BEND_PDF_A3_CN.pdf'
subprocess.run(['pdftoppm','-png','-r','60','-f','1','-l','1','-singlefile',str(pdf),str(P/f'{VER}_PDF_P1')],check=True)
subprocess.run(['pdftoppm','-png','-r','110','-f','3','-l','3','-singlefile',str(pdf),'/tmp/pv_p3'],check=True)
im=Image.open('/tmp/pv_p3.png');w,h=im.size
im.crop((0,int(h*0.05),int(w*0.42),int(h*0.62))).save(P/f'{VER}_LID_TOP_HANDLE_DETAIL.png')
shutil.copy(W_/'iso_corner_bottom.png',P/f'{VER}_ISO_END_CORNER_BOTTOM.png')
shutil.copy(W_/'iso_corner_top.png',P/f'{VER}_ISO_END_CORNER_TOP_LID.png')
# lid corner close-up (formed) with caption
SL=json.load(open(W_/'corner03_closure_sections.json'))['X0Y0']  # 4 corners identical
im=Image.open(W_/'iso_corner_lid03.png').convert('RGB');W0,H0=im.size
c=Image.new('RGB',(max(W0,1040),H0+120),'white');c.paste(im,(0,0));dr=ImageDraw.Draw(c)
f=ImageFont.truetype(CJK[0],20) if CJK else ImageFont.load_default()
z=SL.get('open_z_range') or [None,None]
dr.text((10,H0+8),f'{VER} 盖角03(corner_gap=0)成形后轴测 - CAD模型，非实物',fill='black',font=f)
dr.text((10,H0+38),f'直裙段/顶板闭合；折弯R区发丝缝 最大{SL["max_gap_mm"]:.3f} mm @Z{SL["z_at_max"]}，开口Z {z[0]}~{z[1]}（约{z[1]-z[0]:.2f} mm高）',fill='black',font=f)
dr.text((10,H0+68),'形状无需焊接；如要求防尘/防水，R区需点焊或密封胶。客户确认稿，未试制',fill=(200,0,0),font=f)
c.save(P/f'{VER}_LID_CORNER03_CLOSEUP.png')
# nest
def draw(path,ax,lw=0.6,col='k'):
    import math
    for e in ezdxf.readfile(path).modelspace():
        t=e.dxftype()
        if t=='LINE':ax.plot([e.dxf.start.x,e.dxf.end.x],[e.dxf.start.y,e.dxf.end.y],col,lw=lw)
        elif t=='LWPOLYLINE':
            q=[(p[0],p[1]) for p in e.get_points()]+([e.get_points()[0][:2]] if e.closed else []);ax.plot([a for a,b in q],[b for a,b in q],col,lw=lw)
        elif t=='CIRCLE':ax.add_patch(plt.Circle((e.dxf.center.x,e.dxf.center.y),e.dxf.radius,fill=False,color=col,lw=lw))
        elif t=='ARC':
            import numpy as np;a=np.radians(np.linspace(e.dxf.start_angle,e.dxf.end_angle if e.dxf.end_angle>e.dxf.start_angle else e.dxf.end_angle+360,40))
            ax.plot(e.dxf.center.x+e.dxf.radius*np.cos(a),e.dxf.center.y+e.dxf.radius*np.sin(a),col,lw=lw)
fig,ax=plt.subplots(figsize=(10.24,5.12),dpi=100);fig.patch.set_facecolor('#222831');ax.set_facecolor('#222831')
draw(S/'NEST'/f'{VER}_NEST_2440x1220_SHEET01.dxf',ax,0.8,'w');ax.set_aspect('equal');ax.axis('off');fig.tight_layout()
fig.savefig(P/f'{VER}_NEST_SHEET01.png',facecolor=fig.get_facecolor());plt.close(fig)
# flat corner detail
p=json.load(open(W_/'project03.json'))
fig,axs=plt.subplots(1,2,figsize=(14,7),dpi=110,gridspec_kw={'width_ratios':[1,1.25]})
cut=S/'DXF_CUT'/f'{VER}_CUT_LID.dxf'
draw(cut,axs[0],0.8);axs[0].set_aspect('equal');axs[0].set_title(f'{VER}_CUT_LID.dxf 全貌',fontproperties=FP)
axs[0].add_patch(plt.Rectangle((-3,-3),22,22,fill=False,color='r',lw=1.2,ls='--'))
ax=axs[1];draw(cut,ax,1.4);ax.set_xlim(-2.5,19);ax.set_ylim(-2.5,19);ax.set_aspect('equal');ax.grid(alpha=.25)
pts={'P1':(13.285,13.2),'P2':(15.085,15.085),'P3':(13.2,14.285)}
off={'P1':(1.0,-2.2),'P2':(0.6,1.2),'P3':(-8.5,1.6)}
for k,(x,y) in pts.items():
    ax.plot(x,y,'ro',ms=5);ax.annotate(f'{k} ({x}, {y})',(x,y),(x+off[k][0],y+off[k][1]),color='r',arrowprops=dict(arrowstyle='->',color='r'),fontsize=11)
ax.annotate('',(0,14.285),(0,0),arrowprops=dict(arrowstyle='<->',color='b'));ax.text(-2.3,6.5,'14.285',color='b',rotation=90)
ax.annotate('',(13.285,-1.2),(0,-1.2),arrowprops=dict(arrowstyle='<->',color='b'));ax.text(5,-2.2,'13.285',color='b')
ax.text(0.5,16.6,'短裙（Y向）退让 t+gap=1.0',color='b',fontproperties=FP);ax.text(14.2,4,'长裙全长',color='b',fontproperties=FP,rotation=90)
ax.set_title('盖展开角部 03 斜角（corner_gap=0，左下角，四角对称）',fontproperties=FP)
fig.text(0.02,0.02,'坐标读回自发布DXF；P1/P2/P3 = 03方案定义；缝0角柱修正：每角去除13.2×1.0（native03 未通过，见EVIDENCE）。客户确认稿，非生产放行。',fontproperties=FP,fontsize=10,color='darkred')
fig.tight_layout(rect=(0,0.04,1,1));fig.savefig(P/f'{VER}_LID_FLAT_CORNER03_DETAIL.png');plt.close(fig)
print(sorted(x.name for x in P.iterdir()))
