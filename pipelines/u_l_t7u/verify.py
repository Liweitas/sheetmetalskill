# v2.8.2 pipeline u_l_t7u (DEFAULT structure): vendored from 干画图3's /workspace/orders/box-180x420x175/addendum-tools (S-201-1-20261021-007-v1).
# v2.8.2 changes: hardcoded order/skill/tmp paths -> env SM_ORDER (order folder) + this folder; job features from release_config.json.
import sys,json,glob
sys.path.insert(0,'/opt/freecad-dl/FreeCAD-1.1.1/usr/lib')
import FreeCAD as F,Part
sys.path.insert(0,__import__('os').path.dirname(__import__('os').path.abspath(__file__)));import cfg
V=F.Vector;W=str(cfg.W);R=cfg.REV_ROOT;RR=cfg.ROOF_D/2
rep=json.load(open(W+'/E_main_report.json'));H=rep['params']['H'];H16=rep['lid']['roof_holes_16'];HH=rep['lid']['handle_holes']
bb=lambda s:[round(getattr(s.BoundBox,k),4) for k in ('XLength','YLength','ZLength')]
out={}
for n in ('U','L','LID','ASSEMBLY','EXPLODED'):
    s=Part.read(f'{W}/{n}.step');o={'solids':len(s.Solids),'valid':s.isValid(),'bbox_size':bb(s),'volume':s.Volume}
    if n in ('LID','ASSEMBLY','EXPLODED'):
        dz=rep['assembly']['exploded_translations_mm']['LID'][2] if n=='EXPLODED' else 0
        o['Oroof_centres_open']=[not any(x.isInside(V(cx,cy,H-.5+dz),1e-7,True) for x in s.Solids) for cx,cy in H16]
        o[f'Oroof_ring_r{RR-0.1:g}_open']=[not any(x.isInside(V(cx+RR-0.1,cy,H-.5+dz),1e-7,True) for x in s.Solids) for cx,cy in H16]
        o[f'Oroof_ring_r{RR+0.1:g}_material']=[any(x.isInside(V(cx+RR+0.1,cy,H-.5+dz),1e-7,True) for x in s.Solids) for cx,cy in H16]
        o['handle_O6.6_centres_open']=[not any(x.isInside(V(cx,cy,H-.5+dz),1e-7,True) for x in s.Solids) for cx,cy in HH]
    out[n]=o
sk={}
for n in ('U','L','LID','ASSEMBLY'):
    p=glob.glob(f'{R}/STEP/*_{n}_*.step')[0];s=Part.read(p);sk[n]={'bbox_size':bb(s),'volume':s.Volume}
out['skill_baseline']=sk
out['volume_delta_E_minus_skill']={n:out[n]['volume']-sk[n]['volume'] for n in ('U','L','LID')}
# expected L/U deltas: U loses front-edge strip & bottom strip; L shrinks by the L cover setback (default 0 since user t16u) -- report only
lid=out['LID']
P=rep['params'];_st=P['skirt']-P['Ri']-P['t'];_fill=4*P['t']*P['corner_gap_bend_zone']*_st;_cut=4*P['t']*rep['lid']['long_skirt_cover_setback_mm']*_st
out['lid_volume_check']={'skill_LID':sk['LID']['volume'],'E_LID_t7u':lid['volume'],'delta':lid['volume']-sk['LID']['volume'],
 'straight_skirt_seam_closed_plus':_fill,'straight_long_skirt_setback_minus':_cut,'bend_zone_remainder':lid['volume']-sk['LID']['volume']-_fill+_cut,
 'skill_reproduction_sym_diff':rep['lid']['skill_reproduction_check']['sym_diff_vs_skill_LID'],
 'note':f"003 t7u corner: seam 0.4->0 (straight + bend zone), long skirts set back {rep['lid']['long_skirt_cover_setback_mm']:g} (0 = flush, user t16u); no handle holes"}
txt=open(W+'/LID.dxf').read().split('\n');out['LID_dxf_counts']={k:sum(1 for i in range(0,len(txt)-1) if txt[i].strip()=='0' and txt[i+1].strip()==k) for k in ('LINE','ARC','CIRCLE')}
out['LID_dxf_roof_holes_flat']=rep['parts']['LID']['flat_roof_holes_16'];out['LID_dxf_non_circular_inner_loops']=len(rep['parts']['LID']['dxf_cutout_loop_checks'])
json.dump(out,open(W+'/verification_E.json','w'),indent=1,ensure_ascii=False);print(json.dumps(out,indent=1,ensure_ascii=False))
