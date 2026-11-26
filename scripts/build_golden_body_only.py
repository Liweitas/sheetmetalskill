"""Public golden adapter for an explicitly open, hole-free U+2-ends box."""
from pathlib import Path
import os,sys,json,math,subprocess,shutil,hashlib,re,csv,zipfile
SK=Path(__file__).resolve().parents[1];GOLD=SK/'assets/bend-pdf-golden-001-visual'
def execute(src,code,out,source_path):
 from execution_log import run_stage
 from release_dxf import post_release
 assert src.get('lid_required') is False and src.get('height_basis')=='bare_body'
 assert src.get('material')=='201' and src.get('units','mm')=='mm' and src.get('dim_basis','body_outer')=='body_outer'
 assert src.get('holes')==[] and src.get('handles',{}).get('mode')=='none' and src.get('fixings',{}).get('mode')=='none' and src.get('roof_ports',{}).get('mode')=='none','body-only adapter requires explicit no-hole/no-handle/no-fixing declarations'
 for k in ['lid_ports','panel_holes','rect_cutouts','top_fixings']:assert not src.get(k),'unsupported feature in hole-free adapter'
 assert float(src.get('seam_gap',0))==0 and float(src.get('end_inset',0))==0
 dims=src['dimensions'];L,W,H=[float(dims[k]) for k in ['length','width','height']];t=float(src['thickness']);ri=float(src.get('Ri',.8));K=float(src.get('K',((2*(ri+t)-1.7*t)/(math.pi/2)-ri)/t))
 assert all(math.isfinite(v) and v>0 for v in [L,W,H,t,ri]) and max(L,W)>=H and 0<K<1
 assert t==1 and src.get('structure') in [None,'u_endplates','u_external_ends_body_only'],'reviewed body-only adapter is currently201/1mm,U+2ends'
 assert src.get('quantity',1)==1,'this reviewed adapter currently publishes exactly one box kit'
 assert src.get('customer_requirement_text') and Path(src['customer_image']).is_file()
 out=Path(out);out.mkdir(parents=True,exist_ok=False);stage=out/code;stage.mkdir();pipe=out.parent/'pipe';pipe.mkdir();logs=pipe/'logs';logs.mkdir();fc=os.environ['SM_FC'];env={**os.environ,'SHEETMETAL_PATH':os.environ.get('SHEETMETAL_PATH',str(SK.parents[0]/'.deps/SheetMetal'))}
 j={'release':code,'order_id':str(src['order_id']),'material_cn':'201不锈钢','lid_required':False,'body_only':True,'height_basis':'bare_body','dim_basis':'body_outer','structure':'u_external_ends_body_only','L':L,'W':W,'H':H,'t':t,'Ri':ri,'K':K,'holes':[],'handles':{},'lid_ports':[],'panel_holes':[],'top_fixings':[],'lid':None,'q':None,'g':None,'skirt':None,'quantity':1,'production_release':False,'customer_requirement_text':src['customer_requirement_text'],'customer_image':str(Path(src['customer_image']).resolve()),'ordinary_local_dimensions_review':True,'kr_source':'工程候选Ri0.8，90度扣除BD1.7t，非刀模实测'}
 jp=pipe/'pipe.json';jp.write_text(json.dumps(j,ensure_ascii=False,indent=2));env['SM_JOB']=str(jp)
 def run(label,*cmd):return run_stage(logs,label,[str(x) for x in cmd],env=env)
 run('body_geometry',fc,SK/'pipelines/u_endplates/build_body_only.py',pipe/'work')
 work=pipe/'work';rep=json.loads((work/'report.json').read_text());assert rep['lid_required'] is False and all(abs(a-b)<1e-5 for a,b in zip(rep['assembly']['actual_outer_mm'],[L,W,H]))
 checks,nest=post_release(work,work/'report.json',stage,code,list(rep['parts']),order=['U','END_L','END_R'],sheet=(2440,1220),margin=10,gap=10,material_cn='201不锈钢1mm 无盖无孔',bend_text=lambda n,b:f'{b["id"]} {b["direction"]} 90deg Ri{ri:g}')
 assert all(q['pass'] for q in checks);(work/'dxf_checks.json').write_text(json.dumps({'dxf_checks':checks,'nest':nest},ensure_ascii=False,indent=2))
 step=stage/'STEP';step.mkdir()
 for f in work.glob('*.step'):
  text=f.read_text(encoding='latin-1');name=code+'_'+f.name;text=text.replace('HEADER;','HEADER;\n/* '+code+' CUSTOMER CONFIRMATION DRAFT - NOT FOR PRODUCTION */',1);text=re.sub(r"FILE_NAME\('[^']*'",lambda m:"FILE_NAME('"+name+"'",text,count=1);(step/name).write_text(text,encoding='latin-1')
 assert len(list(step.glob('*.step')))==8
 # Fresh Chinese subset follows the existing golden path; source font is environment supplied.
 from fontTools.ttLib import TTCollection,TTFont
 import build_cjk_subset_ttf as sub
 fontsrc=os.environ.get('SM_CJK_SOURCE_TTC','/System/Library/Fonts/Hiragino Sans GB.ttc');col=TTCollection(fontsrc);sub.pick_sc=lambda:col.fonts[0];font=pipe/'cjk-sub.ttf';sub.build(font,[f.read_text() for f in GOLD.glob('*.py')]+[jp.read_text(),(work/'report.json').read_text()]);ft=TTFont(font);family='SMBody'+code.replace('-','')
 for nm in ft['name'].names:
  if nm.nameID in [1,3,4,6,16]:nm.string=family.encode(nm.getEncoding())
 ft.save(font);env['SM_CJK_FONT']=str(font)
 add=pipe/'addendum-tools';add.mkdir()
 for f in GOLD.glob('*.py'):(add/f.name).symlink_to(f)
 run('golden_body_pdf',fc,add/'make_bend_pdf.py',work,stage)
 run('golden_gate',sys.executable,SK/'scripts/check_bend_pdf_golden.py',pipe,'--strict-overlap','--json-out',logs/'golden_gate.json')
 run('render_review','pdftoppm','-png','-r','90',stage/(code+'_BEND_PDF_A3_CN.pdf'),pipe/'page')
 for f in pipe.glob('page-*.png'):shutil.copy2(f,stage/'PREVIEW'/(code+'_'+f.name))
 for name in ['DOC','SOURCE','EVIDENCE']:(stage/name).mkdir()
 def cp(p,sub,name=None):shutil.copy2(p,stage/sub/(code+'_'+(name or Path(p).name)))
 cp(source_path,'SOURCE','original_brief.json');cp(jp,'SOURCE','resolved_brief.json');cp(src['customer_image'],'SOURCE','customer_original.png');cp(font,'SOURCE')
 for f in [Path(__file__),SK/'pipelines/u_endplates/build_body_only.py',*GOLD.glob('*.py')]:cp(f,'SOURCE')
 cp(SK/'SKILL.md','DOC');cp(SK/'references/parameters.md','DOC')
 for f in list(work.glob('*.json'))+list(logs.iterdir()):
  if f.is_file():cp(f,'EVIDENCE')
 with (stage/'DOC'/(code+'_BOM.csv')).open('w',encoding='utf-8-sig',newline='') as stream:
  wr=csv.writer(stream);wr.writerow(['release','part','per_box','sets','material','thickness','flat_X','flat_Y','bends'])
  for n,p in rep['parts'].items():wr.writerow([code,n,1,1,'201',t,*p['flat_size'],len(p['bend_records'])])
 with (stage/'DOC'/(code+'_BEND_BIDIRECTIONAL.csv')).open('w',encoding='utf-8-sig',newline='') as stream:
  wr=csv.writer(stream);wr.writerow(['release','part','bend','axis','from_edge','opposite_edge','length','direction','angle'])
  for n,p in rep['parts'].items():
   for b in p['bend_records']:
    p1,p2=b['flat_line_mm'];axis='Y' if abs(p1[1]-p2[1])<1e-6 else 'X';pos=p1[1] if axis=='Y' else p1[0];total=p['flat_size'][1 if axis=='Y' else 0];wr.writerow([code,n,b['id'],axis,pos,total-pos,math.dist(p1,p2),b['direction'],abs(b['angle_signed_deg'])])
 with (stage/'DOC'/(code+'_PARAMETER_SOURCES.csv')).open('w',encoding='utf-8-sig',newline='') as stream:
  wr=csv.writer(stream);wr.writerow(['parameter','value','status','source'])
  for row in [['L/W/H',f'{L}/{W}/{H}','requested','customer screenshot244/191/180'],['material/t','201/1mm','requested','order row'],['lid/holes','none/none','requested','customer:不要盖子，不用开孔'],['height_basis','bare body','default+requested no lid','SKILL no-lid height rule'],['structure','U+2 external ends','default','SKILL max244>=180'],['Ri',ri,'candidate','SKILL reference'],['K',K,'candidate','computed from BD1.7t; not measured'],['seam/end inset','0/0','default','SKILL external ends cover U'],['weld','two U-end contacts','candidate','open box needs assembly; weld method/strength/warp first article'],['g/q/skirt','not applicable','not applicable','no lid']]:wr.writerow(row)
 (stage/'DOC'/(code+'_README.txt')).write_text(f'''{code}｜订单{j['order_id']}｜201不锈钢1mm｜数量1｜无盖、无孔
客户图244长、191宽、180高，按mm直接做裸箱体外244×191×180。无盖时不扣盖板厚、顶隙或盖裙；盖子/合盖尺寸均不适用。无任何孔、固定孔、把手、螺钉或默认线孔。
结构按SKILL为U形底壳＋两外封端板，3主板，端板盖U、不退让、接触零缝，拼接处焊接固定。实际单端U外缘接触长度约{rep['weld_candidate']['outer_seam_length_each_mm']:.2f}mm；焊法/焊缝要求和变形须首件确认，未捏造焊道实体。
实际STEP回读244×191×180、3主件有效、实体间无体积交叠、顶口探针自由、孔0、端板完全盖U通过。U从实际底外面原生展开2折、实际板厚1回读，左右端板0折刚体正旋转展开，平坯面积×厚度及CUT面积回读通过。未运行盖角03检查：本单无盖，不适用。
Ri{ri:g}、K{K:.6f}、BD{rep['params']['BD']:.2f}为工程候选，非本厂刀模实折。图中标实际标准尺寸线/箭头/线上数值，U每道弯两侧定位与心距；UP/DOWN按实际展开根面，不是已标定的机床后挡料。无孔，不写薄板螺钉或假设M4。
完整格式：8STEP（3成形+3原生展开/转平+装配+仅平移爆炸）；7DXF（3CUT/3BEND/一盒NEST）；4页红蓝A3折弯PDF含客户原图、成形实际轴测/三视、U和端板展开标准尺寸及焊接候选；1页NEST预览；BOM、逐弯双向CSV、参数来源、原始图文和实际检查。CUT/NEST择一加工，勿重复下料。NEST2440×1220、边距10、件距10，只排1套。
该无盖无孔分支为本次实际几何适配，沿金样渲染入口复用颜色/轴测/标准尺寸函数；不代表任意有孔或其它结构支持。数字格式与实际检查通过不等于实物首件，production_release=false。通用R07/R12封套门禁不支持本适配器目录，另行记录，不冒称通用生产放行。
''')
 (stage/'DOC'/(code+'_CUSTOMER_REQUIREMENT.txt')).write_text(code+'\n'+src['customer_requirement_text'])
 # The order reviewer must inspect rendered pages before package publication.
 result={'release':code,'stage':str(stage),'pipe':str(pipe),'parts':3,'STEP':8,'DXF':7,'bend_pages':4,'nest_pages':1,'status':'GEOMETRY_AND_FORMATS_READY_FOR_VISUAL_REVIEW','production_release':False};(out.parent/'body_only_run_result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False));return result
