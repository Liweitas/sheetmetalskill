# v2.8.2 pipeline u_l_t7u (DEFAULT structure): vendored from 干画图3's /workspace/orders/box-180x420x175/addendum-tools/cfg.py (S-201-1-20261021-007-v1).
# single source of the release prefix, folders and job features. v2.8.2: order folder from env SM_ORDER (was hardcoded),
# job features (roof holes / handles) from release_config.json "features" - absent = NONE (never invent holes).
import json, os
from pathlib import Path
B = Path(os.environ['SM_ORDER'])
_C = json.load(open(B / 'release_config.json'))
VER = _C['VER']                              # used exactly as given
W = B / 'work_main'; P = B / 'post_out'
_rr = B / 'logs/rev_root.env'
REV_ROOT = open(_rr).read().strip().split('=', 1)[1] if _rr.exists() else str(B)
MATERIAL_CN = _C.get('material_cn', '201不锈钢'); MATERIAL_EN = _C.get('material_en', '201 stainless')
_F = _C.get('features', {})
_R = _F.get('roof_holes')                    # e.g. 007: {"d":12,"pitch":30,"centre_to_lid_edge":50,"pts":[[48.5,75],[48.5,105]],"axis":"Y"}
ROOF_D = float(_R['d']) if _R else 0.0
ROOF_PITCH = float(_R['pitch']) if _R else 0.0
ROOF_CENTRE_TO_LID_EDGE = float(_R['centre_to_lid_edge']) if _R else 0.0   # hole CENTRE to lid outer edge (record which reading was used!)
ROOF_EDGE_TO_LID_EDGE = ROOF_CENTRE_TO_LID_EDGE - ROOF_D / 2
LID_OUTER_OFFSET = float(_C.get('lid_outer_offset', 1.5))   # g + t
# user t16u 2026-10-26: U+L -> L盖U, 不留缝隙, 不退让0.2mm. Old 007/003 value was 0.2; non-zero only if the user asks in this job.
L_COVER_SETBACK = float(_C.get('l_cover_setback_mm', 0.0))          # L exposed edges vs U outer faces
LID_LONG_SKIRT_SETBACK = float(_C.get('lid_long_skirt_setback_mm', 0.0))  # t7u long (covering) skirt exposed end
ROOF_PTS = [tuple(p) for p in _R['pts']] if _R else []
ROOF_AXIS = _R.get('axis', 'Y') if _R else None
HANDLE_CENTRES = [tuple(p) for p in _F.get('handle_centres', [])]
