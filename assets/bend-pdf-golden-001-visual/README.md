# 折弯 PDF 金样（视觉参考 001-v1 / skill 2.8.45）

- **视觉权威订单（Harry t59u）**：`S-201-1-20261031-001-v1`（kit `box-320x155x105-inner`）
  - PDF：`…_完整折弯工艺PDF_折弯师傅作业图_4页.pdf`；PREVIEW `PAGE-01`…`04`
  - 用户评价：「这个pdf的生成效果非常好」；拥挤可接受；**不要硬卡 4 页**（t59u/t60u）。
- **本目录**：合并 001 视觉语言（字号≥9.4pt、尺寸可读、视图比例）+ 004-v2 后续正确性（重叠避让、规则9双向、页眉出图时间、CJK 子集、海军蓝+红条、规则31 处理面朝外、可加页）。
- **门禁五文件**：`make_bend_pdf.py` / `pdf_common.py` / `bidir.py` / `views.py` / `engine_u_endplates.py`
  - 当前统一服务的 U+端板及 U+L 实单 PDF 均由 `make_bend_pdf WORK STAGE` 分发到 `engine_u_endplates.py`（matplotlib），并追加客户原始需求/后续确认页；历史 reportlab 路径仅保留作参考。
  - 哈希见 `GOLDEN_SCRIPTS.sha256`。订单只许 `cp`/`symlink`，出图前 sha256 必须一致。
- **旧金样**：`assets/bend-pdf-golden-004-v2/` 仅历史（其 engine 默认 dim≈5–6.5pt，是后期 PDF「字小/尺寸差」主因）。

## 新单必须

1. `cp` 或 `ln -s` 本目录五文件到订单 `addendum-tools/`
2. `python3 scripts/check_bend_pdf_golden.py $ORDER [--overlap … --strict-overlap]`
3. 对照规则 12 + 15 + 18 + 9 + 26 + **32**（001 视觉）+ 31（处理面）
4. 拥挤 → 加页；禁止为卡 4 页把字号压到 <9.4pt
