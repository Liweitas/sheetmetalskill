"""Golden body-only/no-hole adapter; shared actual projection, standard dimensions and visual language."""
from pathlib import Path
import ast,os,sys,json,math,datetime
from zoneinfo import ZoneInfo
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle
from matplotlib.collections import PolyCollection
from matplotlib.text import Text
from matplotlib.font_manager import FontProperties,fontManager
from matplotlib.backends.backend_pdf import PdfPages
from PIL import Image
W_=Path(sys.argv[1]);R=Path(sys.argv[2]);JOB=json.loads(Path(os.environ['SM_JOB']).read_text());rep=json.loads((W_/'report.json').read_text());assert JOB['lid_required'] is False and set(rep['parts'])=={'U','END_L','END_R'} and rep['holes']==[]
P=rep['parts'];proj=json.loads((W_/'projections.json').read_text());flats=json.loads((W_/'flats.json').read_text());mesh=json.loads((W_/'mesh.json').read_text())
VER=JOB['release'];L,W,H,t,ri,K=[JOB[k] for k in ['L','W','H','t','Ri','K']];OUTER_L,OUTER_W=L,W;PW,PH=420,297;NPAGES=4
NAVY=(.10,.22,.45);REDC=(.82,.10,.10);BLU='#0040a0';DIMC=(0,.2,.65);TAN=(.55,.40,.20);GRN=(.2,.55,.3)
FS_NOTE=9.4;FS_FOOT=9.4;FS_TITLE=10.5;MINPT=9.4;FP=FontProperties(fname=os.environ['SM_CJK_FONT']);fontManager.addfont(os.environ['SM_CJK_FONT']);plt.rcParams['font.family']=[FP.get_name(),'DejaVu Sans'];plt.rcParams['axes.unicode_minus']=False;plt.rcParams['pdf.fonttype']=42;plt.rcParams['ps.fonttype']=42
_LD_RECORDS=[];_PAGE_LAYOUT=[];stamp=datetime.datetime.now(ZoneInfo('Asia/Shanghai')).strftime('%Y-%m-%d %H:%M Asia/Shanghai')
# Reuse gold functions without executing the lid-only configuration at module import.
shared=Path(__file__).with_name('engine_u_endplates.py');tree=ast.parse(shared.read_text());wanted={'_fs','foot','layout_issues','save_page','_subdiv_tris','render_assy_iso_png','sd_ink','sd_h','sd_v'}
class NoLidWords(ast.NodeTransformer):
 def visit_Constant(self,node):
  if isinstance(node.value,str):return ast.copy_location(ast.Constant(node.value.replace('绿盖 / 褐箱','无盖 / 无孔').replace('投产包：','确认稿：')),node)
  return node
nodes=[NoLidWords().visit(n) for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in wanted];assert {n.name for n in nodes}==wanted;exec(compile(ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[])),str(shared),'exec'),globals())
def od_n(v):return f'{v:.2f}'.rstrip('0').rstrip('.')
def newpage(i,total=4):
 fig=plt.figure(figsize=(PW/25.4,PH/25.4),dpi=120);a=fig.add_axes([0,0,1,1]);a.set(xlim=(0,PW),ylim=(0,PH));a.axis('off')
 a.add_patch(Rectangle((0,PH-18),PW,18,fc=NAVY,ec='none'));a.add_patch(Rectangle((0,PH-34),PW,16,fc=REDC,ec='none'))
 a.text(8,PH-12,VER+'  钣金折弯工艺确认稿（非生产放行）',color='w',fontsize=13,va='center',weight='bold');a.text(PW-70,PH-12,'出图 '+stamp,color='w',fontsize=9.4,ha='right',va='center');a.text(PW-8,PH-12,f'{i}/{total}',fontsize=12,color='w',ha='right',va='center')
 a.text(8,PH-22,f'201不锈钢｜t={t:g}mm｜裸箱体外{L:g}×{W:g}×{H:g}｜无盖、不开孔｜每套3件｜Ri{ri:g} K{K:.4f} BD{rep["params"]["BD"]:.3f}（候选）',fontsize=9.4,color='w',va='center')
 a.text(8,PH-31,f'{VER}｜尺寸mm｜本图高度为裸箱体外高｜金样无盖分支｜首件试折与焊接待确认',fontsize=9.4,color='w',va='center');foot(a);return fig,a

def axes(fig,x,y,w,h):
 a=fig.add_axes([x/PW,y/PH,w/PW,h/PH]);a.set(xlim=(0,w),ylim=(0,h));a.axis('off');a.s=1;a._ld_panel=(x,y,w,h);return a

def line(a,pts,**kw):
 q=np.array(pts);a.plot(q[:,0],q[:,1],**kw)

def iso(fig,names,x,y,w,h,exploded=False):
 f=R/'PREVIEW'/(VER+'_'+('_'.join(names))+('_EXP' if exploded else '')+'_ISO.png');render_assy_iso_png(f,names,dpi=180,exploded=exploded);a=fig.add_axes([x/PW,y/PH,w/PW,h/PH]);a.imshow(np.asarray(Image.open(f)));a.axis('off')

def viewdim(fig,name,face,ox,oy,cw,ch):
 d=P[name]['size'] if name in P else [L,W,H];ww,hh=(d[0],d[2]) if face=='front' else (d[1],d[2]) if face=='right' else (d[0],d[1]);fn={'front':lambda u,v:(v,-u),'right':lambda u,v:(-v,u),'top':lambda u,v:(u,v)}[face]
 # U starts at global X=t; normalize its own measured X extent for part drawings.
 xoff=P[name]['bbox'][0] if name in P and face in ['front','top'] else 0
 a=axes(fig,ox,oy,cw,ch);sc=min((cw-10)/ww,(ch-15)/hh);gx=(cw-ww*sc)/2;gy=3;b=(gx,gx+ww*sc,gy,gy+hh*sc)
 for path in proj[name][face]['vis']:
  q=[fn(*p) for p in path];line(a,[(gx+(u-xoff)*sc,gy+v*sc) for u,v in q],color='k',lw=.6)
 sd_h(a,gx,gx+ww*sc,gy+5,gy,gy,ww,b,name+'_'+face+'_width');sd_v(a,gy,gy+hh*sc,gx+ww*sc-4,gx+ww*sc,gx+ww*sc,hh,b,name+'_'+face+'_height')
 a.text(cw/2,ch-1,{'front':'正视','right':'右视','top':'俯视（开口）'}[face],fontsize=9.4,color=NAVY,ha='center',va='top')

R.mkdir(parents=True,exist_ok=True);(R/'PREVIEW').mkdir(exist_ok=True)
with PdfPages(R/(VER+'_BEND_PDF_A3_CN.pdf')) as pdf:
 fig,a=newpage(1);a.text(12,252,'无盖箱体总图｜实际外长、外宽、外高｜数量1',fontsize=10.5,color=NAVY)
 im=fig.add_axes([12/PW,171/PH,105/PW,70/PH]);im.imshow(np.asarray(Image.open(JOB['customer_image'])));im.axis('off');im.set_title('客户原图',fontsize=9.4,loc='left');iso(fig,list(P),126,168,144,80)
 for i,s in enumerate([f'订单 {JOB["order_id"]}',f'裸箱体外尺寸 {L:g}×{W:g}×{H:g}',f'板厚{t:g}；U底＋两外端板', '合盖总外包：不适用', '盖子尺寸/顶隙：不适用', '所有孔0；把手0；固定孔0', '端板盖U、零缝零退让', '拼接处焊接固定，焊缝首件确认']):a.text(282,240-i*7,s,fontsize=9.4,color=NAVY)
 for face,x in [('front',12),('top',147),('right',282)]:viewdim(fig,'ASSEMBLY',face,x,28,126,128)
 a.text(12,19,'180是裸箱体外高，不扣盖厚或顶隙；顶部敞开。焊接变形/刀模/回弹须首件确认。',fontsize=9.4,color=REDC);save_page(pdf,fig)
 fig,a=newpage(2);a.text(12,252,'U形底壳｜一件/套｜原生展开2道90°折弯｜外表面朝读者',fontsize=10.5,color=NAVY)
 iso(fig,['U'],12,179,80,63)
 p=P['U'];fx,fy=p['flat_size'];ax=axes(fig,12,45,260,190);sc=min(250/fx,180/fy);gx=(260-fx*sc)/2;gy=3;bd=(gx,gx+fx*sc,gy,gy+fy*sc)
 for wire in flats['U']['wires']:line(ax,[(gx+x*sc,gy+y*sc) for x,y in wire+[wire[0]]],color='k',lw=.65)
 yy=sorted(b['flat_line_mm'][0][1] for b in p['bend_records']);
 for b in p['bend_records']:
  q=b['flat_line_mm'];line(ax,[(gx+x*sc,gy+y*sc) for x,y in q],color=REDC,lw=.8);ax.text(gx+fx*sc/2+2,gy+q[0][1]*sc+1,b['id'],fontsize=9.4,color=REDC)
 for u,v in zip([0]+yy,yy+[fy]):sd_v(ax,gy+u*sc,gy+v*sc,gx+fx*.2*sc,gx,gx,v-u,bd,'U_bend_chain')
 sd_v(ax,gy,gy+yy[1]*sc,gx+fx*.45*sc,gx,gx,yy[1],bd,'U_B2_bottom');sd_v(ax,gy+yy[0]*sc,gy+fy*sc,gx+fx*.70*sc,gx+fx*sc,gx+fx*sc,fy-yy[0],bd,'U_B1_top');sd_v(ax,gy,gy+fy*sc,gx+(fx-12)*sc,gx+fx*sc,gx+fx*sc,fy,bd,'U_flat_total_Y');sd_h(ax,gx,gx+fx*sc,gy+fy*.61*sc,gy+fy*.61*sc,gy+fy*.61*sc,fx,bd,'U_flat_total_X')
 for face,y in [('front',170),('top',96),('right',22)]:viewdim(fig,'U',face,282,y,126,70)
 for i,b in enumerate(p['bend_records']):a.text(12+i*126,32,f'{i+1}. {b["id"]} {b["direction"]} 90°；折线长{math.dist(*b["flat_line_mm"]):g}',fontsize=9.4,color=BLU)
 a.text(12,18,'建议先B1后B2；UP朝读者、DOWN背向读者。展开中心尺寸不是已标定机床挡料，须试折。',fontsize=9.4,color=REDC);save_page(pdf,fig)
 fig,a=newpage(3);a.text(12,252,'两外封端板｜各1件/套｜零折弯｜均按外表面朝读者展开',fontsize=10.5,color=NAVY)
 for name,ox,title in [('END_L',12,'左端板'),('END_R',218,'右端板')]:
  a.text(ox,240,title+'  成形/展开同轮廓，板厚1mm',fontsize=9.4,color=NAVY);ax=axes(fig,ox,43,190,190);fx,fy=P[name]['flat_size'];sc=min(180/fx,175/fy);gx=(190-fx*sc)/2;gy=3;bd=(gx,gx+fx*sc,gy,gy+fy*sc)
  for wire in flats[name]['wires']:line(ax,[(gx+x*sc,gy+y*sc) for x,y in wire+[wire[0]]],color='k',lw=.65)
  sd_h(ax,gx,gx+fx*sc,gy+7,gy,gy,fx,bd,name+'_flat_X');sd_v(ax,gy,gy+fy*sc,gx+fx*sc-5,gx+fx*sc,gx+fx*sc,fy,bd,name+'_flat_Y')
  ax.annotate(f'底角2×R{ri+t:g}',(gx+((ri+t)*(1-1/math.sqrt(2)))*sc,gy+((ri+t)*(1-1/math.sqrt(2)))*sc),(gx+35,gy+22),fontsize=9.4,color=BLU,arrowprops=dict(arrowstyle='->',color=BLU,lw=.35))
  ax.text(gx+fx*sc/2,gy+fy*sc*.65,'零折弯；无孔\n不得镜像翻成内表面',fontsize=9.4,color=BLU,ha='center',linespacing=1.3)
 a.text(12,29,'左端外视平坯X′=W−Y；右端X′=Y；Y′=Z；厚度1mm。真实外侧刚体转平，行列式+1。',fontsize=9.4,color=BLU)
 a.text(12,18,'端板外轮廓完整盖住U端面；轴向接触零缝、不退让。拼接处按本单焊接候选处理。',fontsize=9.4,color=REDC);save_page(pdf,fig)
 fig,a=newpage(4);a.text(12,252,'拼接焊接位置与首件确认｜无盖、无孔｜工艺候选',fontsize=10.5,color=NAVY);iso(fig,list(P),12,127,178,111,exploded=True)
 ax=axes(fig,218,124,190,113);sc=min(174/W,96/H);gx=(190-W*sc)/2;gy=3;bd=(gx,gx+W*sc,gy,gy+H*sc)
 # Actual end face and the two outer U-contact profiles are derived from the source contour.
 for wire in flats['END_R']['wires']:line(ax,[(gx+y*sc,gy+z*sc) for y,z in wire+[wire[0]]],color='k',lw=.65)
 for path in rep['weld_candidate']['paths_YZ']:line(ax,[(gx+y*sc,gy+z*sc) for y,z in path],color=REDC,lw=1.3)
 sd_h(ax,gx,gx+W*sc,gy+5,gy,gy,W,bd,'weld_end_W');sd_v(ax,gy,gy+H*sc,gx+W*sc-4,gx+W*sc,gx+W*sc,H,bd,'weld_end_H')
 ax.text(95,111,'两端接触面同截面｜红线为拼焊位置',fontsize=9.4,color=NAVY,ha='center',va='top')
 lines=[f'BOM：U×1，左端板×1，右端板×1；每套3件，订单1套。',f'裸箱体外{L:g}×{W:g}×{H:g}；盖/盖裙/盖体余量：不适用；孔0、把手0。',f'接触面X={t:g}/{L-t:g}；两端各按U外缘拼焊，实际单端轮廓长约{rep["weld_candidate"]["outer_seam_length_each_mm"]:.2f}mm。','红线仅说明焊接接缝，不进入CUT/NEST；未生成未经确认的焊道实体。焊法、焊缝与变形须首件确认。',f'Ri{ri:g}、K{K:.6f}、90°扣除BD{rep["params"]["BD"]:.2f}为工程候选，不是本厂刀模实测标定值。','客户原文：线上 5127618062065088636，201，1mm，2026/11/20，数量1，001；不要盖子，不用开孔。','实物试折/焊接未进行。完成外长、外宽、外高及对角线/顶口复核后再批量；production_release=false。','CUT单件与NEST套料择一切割，勿重复下料；NEST一盒一文件2440×1220，边距/件距10。']
 for i,text in enumerate(lines):a.text(12,112-i*11,text,fontsize=9.4,color=BLU if i<3 else REDC if i in [4,6] else NAVY)
 save_page(pdf,fig)
# Same golden overlap/bounds records as the covered-box path.
log=W_.parent/'logs';log.mkdir(exist_ok=True);remaining=sum(len(q['issues']) for q in _PAGE_LAYOUT);ov={'pass':remaining==0,'remaining':remaining,'pages':4,'page_checks':_PAGE_LAYOUT,'attempted':0,'resolved_by_nudge':0,'resolved_by_flip':0,'dimension_remaining':0,'ver':VER,'stamp':stamp};(log/'bend_pdf_overlap.json').write_text(json.dumps(ov,ensure_ascii=False,indent=2));(W_/'local_dimension_coverage.json').write_text(json.dumps(_LD_RECORDS,ensure_ascii=False,indent=2));
if remaining:raise ValueError('PDF overlap/clipping; see bend_pdf_overlap.json')
# Actual NEST entities; one standard golden-colour preview page.
import ezdxf
fig,a=newpage(1,total=1);a.text(12,252,'一盒套料预览｜2440×1220｜边距10、件距10｜只含3块板、无孔无盖',fontsize=10.5,color=NAVY);ax=fig.add_axes([20/PW,43/PH,380/PW,190/PH]);ax.axis('off');ax.set(xlim=(-8,2448),ylim=(-8,1228));ax.set_aspect('equal')
for e in ezdxf.readfile(R/'NEST'/(VER+'_NEST_2440x1220_1BOX.dxf')).modelspace():
 color='0.5' if e.dxf.layer=='SHEET' else 'k'
 if e.dxftype()=='LINE':ax.plot([e.dxf.start.x,e.dxf.end.x],[e.dxf.start.y,e.dxf.end.y],color=color,lw=.5)
 elif e.dxftype()=='ARC':
  st,en=e.dxf.start_angle,e.dxf.end_angle;aa=np.radians(np.linspace(st,st+(en-st)%360,40));ax.plot(e.dxf.center.x+e.dxf.radius*np.cos(aa),e.dxf.center.y+e.dxf.radius*np.sin(aa),color=color,lw=.5)
 elif e.dxftype()=='LWPOLYLINE':
  pts=list(e.get_points('xy'));pts+=pts[:1] if e.closed else [];line(ax,pts,color=color,lw=.5)
fig.savefig(R/'PREVIEW'/(VER+'_NEST_PREVIEW.png'),dpi=100);fig.savefig(R/'NEST'/(VER+'_NEST_PREVIEW.pdf'));plt.close(fig)
print('PASS golden body-only4pages,actual dimensions and1NEST preview')
