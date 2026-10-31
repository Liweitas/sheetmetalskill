# rev t7u close-up of one formed LID corner (box corner x=0,y=0; lid outer corner x=y=-1.5), from LID.step (FreeCAD fine mesh + section)
import sys,json,numpy as np,matplotlib
matplotlib.use('Agg');import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection,Line3DCollection
from matplotlib import font_manager as fm
FP=fm.FontProperties(fname='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')
m=json.load(open(sys.argv[1]));out=sys.argv[2];title=sys.argv[3];notes=sys.argv[4].split('|');H=float(sys.argv[5]);LO=sys.argv[6]
SB=float(sys.argv[7]) if len(sys.argv)>7 else 0.0   # long-skirt end setback (user t16u: default 0 = flush; 003/007 used 0.2)
XE=-1.5+SB
Lt=np.array([-0.5,-0.7,0.9]);Lt/=np.linalg.norm(Lt)
def panel(ax,v,f,edges,lim,elev,azim,sub):
    V=np.array(v);T=V[np.array(f)]
    n=np.cross(T[:,1]-T[:,0],T[:,2]-T[:,0]);nn=np.linalg.norm(n,axis=1);nn[nn==0]=1;n/=nn[:,None]
    sh=0.35+0.6*np.abs(n@Lt);col=np.c_[0.55*sh,0.68*sh,0.58*sh,np.ones(len(sh))]
    ax.add_collection3d(Poly3DCollection(T,facecolors=col,edgecolors='none'))
    ax.add_collection3d(Line3DCollection([np.array(e) for e in edges],colors='k',linewidths=0.7))
    ax.set_xlim(*lim[0]);ax.set_ylim(*lim[1]);ax.set_zlim(*lim[2]);ax.set_box_aspect((1,1,1))
    ax.view_init(elev=elev,azim=azim);ax.set_xlabel('X');ax.set_ylabel('Y');ax.set_zlabel('Z')
    ax.set_title(sub,fontproperties=FP,fontsize=12)
fig=plt.figure(figsize=(19,8),dpi=120)
panel(fig.add_subplot(131,projection='3d'),m['v'],m['f'],m['edges'],((-2.5,6.5),(-2.5,6.5),(H-8.5,H+0.5)),22,-135,'① 外侧轴测（角部 9×9×11）')
panel(fig.add_subplot(132,projection='3d'),m['v2'],m['f2'],m['edges2'],((-2,2.5),(-2,2.5),(H-4,H+0.5)),30,-135,'② 外侧放大（圆角顶点区 4.5×4.5×4.5）')
ax=fig.add_subplot(133)
for w in m['sec']:
    a=np.array(w);ax.fill(a[:,0],a[:,1],color=(0.62,0.75,0.65),ec='k',lw=1.0)
ax.set_xlim(-2.2,2.0);ax.set_ylim(-2.2,2.0);ax.set_aspect('equal');ax.grid(True,lw=0.3)
ax.axvline(-1.5,color='r',lw=0.6,ls='--');ax.axvline(XE,color='b',lw=0.6,ls='--');ax.axhline(-0.5,color='g',lw=0.6,ls='--')
ax.annotate(f'长裙端 X={XE:g}',(XE,-1.5),(-1.15,-2.05),fontproperties=FP,fontsize=10,color='b',arrowprops=dict(arrowstyle='->',color='b'))
ax.annotate(f'短裙外面 X=-1.5\n(盖外形 {LO})',(-1.5,0.6),(-2.15,1.3),fontproperties=FP,fontsize=10,color='r',arrowprops=dict(arrowstyle='->',color='r'))
ax.annotate('短裙端顶死长裙内面\nY=-0.5（0缝）',(-1.0,-0.5),(-0.3,0.3),fontproperties=FP,fontsize=10,color='g',arrowprops=dict(arrowstyle='->',color='g'))
ax.annotate(f'退{SB:g}' if SB else '齐平（不退让）',(-1.5+SB/2,-1.0),(-2.15,-0.6),fontproperties=FP,fontsize=11,color='darkred',arrowprops=dict(arrowstyle='->',color='darkred'))
ax.set_title(f'③ 水平剖面 Z={H-8:g}（裙直段，俯视）',fontproperties=FP,fontsize=12);ax.set_xlabel('X (mm)');ax.set_ylabel('Y (mm)')
fig.suptitle(title,fontproperties=FP,fontsize=13)
for i,t in enumerate(notes):fig.text(0.02,0.04-0.03*i,t,fontproperties=FP,fontsize=11,color='darkred' if i==0 else 'black')
plt.savefig(out,bbox_inches='tight');plt.close(fig)
