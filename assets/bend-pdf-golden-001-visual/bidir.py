# Rule 9 bidirectional flat dims from bend_records (same as 005 tools/bidir.py).
EDGE_CN = {
    'U': {'X': ('左边A(X=0)', '右边B'), 'Y': ('下边A(Y=0)', '上边B')},
    'L': {'X': ('左边A(X=0)', '右边B'), 'Y': ('下边A(Y=0)', '上边B')},
    'LID': {'X': ('左边A(X0裙)', '右边B'), 'Y': ('下边A(Y0裙)', '上边B')},
}

def bidir(rep, n):
    p = rep['parts'][n]
    fx, fy = p.get('flat_size_mm') or p['flat_size']
    out = {'flat': (fx, fy), 'X': [], 'Y': []}
    for b in p['bend_records']:
        (x1, y1), (x2, y2) = b['flat_line_mm']
        bid = b.get('id') or 'B?'
        if abs(y1 - y2) < 1e-4:  # horizontal bend -> Y axis position
            out['Y'].append(dict(id=bid, pos=y1, a=y1, b=fy - y1,
                                 span=(min(x1, x2), max(x1, x2)),
                                 dir=b.get('direction') or '—',
                                 ang=b.get('angle_signed_deg') or b.get('angle_deg') or 90,
                                 R=b.get('radius_on_selected_skin_mm')))
        else:  # vertical bend -> X axis position
            out['X'].append(dict(id=bid, pos=x1, a=x1, b=fx - x1,
                                 span=(min(y1, y2), max(y1, y2)),
                                 dir=b.get('direction') or '—',
                                 ang=b.get('angle_signed_deg') or b.get('angle_deg') or 90,
                                 R=b.get('radius_on_selected_skin_mm')))
    for ax, tot in (('X', fx), ('Y', fy)):
        L = sorted(out[ax], key=lambda d: d['pos'])
        out[ax] = L
        pts = [0.0] + [round(d['pos'], 3) for d in L] + [round(tot, 3)]
        out[ax + '_seg'] = [(pts[i], pts[i + 1], pts[i + 1] - pts[i]) for i in range(len(pts) - 1)]
        for i, d in enumerate(L):
            d['seg_prev'] = pts[i + 1] - pts[i]
            d['seg_next'] = pts[i + 2] - pts[i + 1]
            d['a'] = pts[i + 1]
            d['b'] = pts[-1] - pts[i + 1]
    return out

def f3(v):
    s = f'{round(float(v), 3):.3f}'.rstrip('0').rstrip('.')
    return '0' if s in ('-0', '') else s

def table_rows(B, n):
    E = EDGE_CN.get(n, EDGE_CN['U'])
    rows = []
    for ax in ('X', 'Y'):
        L = B[ax]
        for i, d in enumerate(L):
            prev = E[ax][0][:2] if i == 0 else L[i - 1]['id']
            nxt = E[ax][1][:2] if i == len(L) - 1 else L[i + 1]['id']
            rows.append(dict(
                id=d['id'], axis=ax, a=f3(d['a']), b=f3(d['b']),
                seg_prev=f"{prev}->{d['id']} {f3(d['seg_prev'])}",
                seg_next=f"{d['id']}->{nxt} {f3(d['seg_next'])}",
                dir=d.get('dir') or '—', ang=abs(float(d.get('ang') or 90)),
            ))
    return rows
