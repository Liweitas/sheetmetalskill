#!/usr/bin/env python3
"""v2.8.2: build an embeddable TrueType (glyf) subset of Noto Sans CJK SC for reportlab PDFs.
Method from 干画图3 lessons §3.6 (/workspace/shared/sheetmetal_lessons_干画图3.md): reportlab cannot embed the CFF .ttc,
so subset to the characters actually used, convert CFF outlines to quadratic glyf with Cu2QuPen, save TTF.
usage (AV python, needs fontTools):  build_cjk_subset_ttf.py OUT.ttf SRC [SRC ...]   (SRC = .py/.txt/.json files whose text is used)
Rebuild whenever new Chinese literals are added (missing glyphs render as blanks)."""
import sys
from pathlib import Path
from fontTools.ttLib import TTFont, TTCollection, newTable
from fontTools.subset import Subsetter, Options
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.ttGlyphPen import TTGlyphPen

TTC = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'


def pick_sc(path=TTC):
    for f in TTCollection(path).fonts:
        if 'Sans CJK SC' in f['name'].getDebugName(1) and 'Mono' not in f['name'].getDebugName(1): return f
    raise SystemExit('Noto Sans CJK SC not found in ' + path)


def build(out, texts):
    chars = set(''.join(texts)) | set(map(chr, range(0x20, 0x7f))) | set('×Ø±°≤≥→←↑↓·—–“”‘’（）：；，。、？！【】《》①②③④⑤⑥⑦⑧⑨⑩')
    f = pick_sc(); o = Options(); o.layout_features = []; o.name_IDs = ['*']; o.notdef_outline = True; o.hinting = False
    s = Subsetter(o); s.populate(unicodes=[ord(c) for c in chars]); s.subset(f)
    gs = f.getGlyphSet(); order = f.getGlyphOrder(); glyf = newTable('glyf'); glyf.glyphOrder = order; glyf.glyphs = {}
    for g in order:
        p = TTGlyphPen(gs); gs[g].draw(Cu2QuPen(p, max_err=1.0, reverse_direction=True)); glyf.glyphs[g] = p.glyph()
    del f['CFF ']
    if 'VORG' in f: del f['VORG']
    f['glyf'] = glyf; f['loca'] = newTable('loca'); f['head'].indexToLocFormat = 0; f['head'].glyphDataFormat = 0
    mp = newTable('maxp'); mp.tableVersion = 0x00010000
    for k in ('maxZones', 'maxTwilightPoints', 'maxStorage', 'maxFunctionDefs', 'maxInstructionDefs', 'maxStackElements', 'maxSizeOfInstructions', 'maxComponentElements'): setattr(mp, k, 0)
    mp.maxZones = 1; mp.numGlyphs = len(order); f['maxp'] = mp; f.sfntVersion = '\x00\x01\x00\x00'
    f['post'].formatType = 2.0; f['post'].extraNames = []; f['post'].mapping = {}; f['post'].glyphOrder = order
    f.save(out); return len(order)


if __name__ == '__main__':
    texts = [Path(p).read_text(encoding='utf-8', errors='ignore') for p in sys.argv[2:]]
    print('glyphs', build(sys.argv[1], texts), '->', sys.argv[1])
