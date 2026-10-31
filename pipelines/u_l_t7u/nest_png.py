# render NEST DXF to PNG (addendum-venv: ezdxf + matplotlib)
import sys,ezdxf,matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
from ezdxf.addons.drawing import RenderContext,Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
from ezdxf.addons.drawing.config import Configuration,BackgroundPolicy
src,out,title=sys.argv[1],sys.argv[2],sys.argv[3]
doc=ezdxf.readfile(src);aud=doc.audit();assert len(aud.errors)==0
assert 'BEND' not in doc.layers and not [e for e in doc.modelspace() if e.dxf.layer.upper()=='BEND']
fig=plt.figure(figsize=(16,8.6),dpi=110);ax=fig.add_axes([0.02,0.03,0.96,0.9])
Frontend(RenderContext(doc),MatplotlibBackend(ax),config=Configuration(background_policy=BackgroundPolicy.WHITE)).draw_layout(doc.modelspace())
ax.set_aspect('equal');fig.suptitle(title,fontsize=13);fig.savefig(out,facecolor='white');print(out)
