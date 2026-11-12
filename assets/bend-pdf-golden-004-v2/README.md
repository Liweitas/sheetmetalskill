# 折弯确认稿 PDF 金样（用户 t43u 认可；v2.8.27 哈希门禁 + 尺寸避让）

- **金样订单**：`S-201-0.8-20261030-004-v2`
- **金样 PDF**：`/workspace/orders/box-180x160x325/named_release/S-201-0.8-20261030-004-v2/S-201-0.8-20261030-004-v2_BEND_PDF_A3_CN.pdf`
- **认可**：用户 t43u（2026-10-31）「这一版本就很好」；要求 skill 后续一致。
- **本目录权威四文件**（只读公共库）：`make_bend_pdf.py` / `pdf_common.py` / `bidir.py` / `views.py`
  哈希见 `GOLDEN_SCRIPTS.sha256`。订单 **不得**把改完的副本当交付引擎；只许 `cp`/`symlink` 后 **sha256 与金样一致**，否则 `check_bend_pdf_golden.py` **BLOCK**。
- **辅引擎**：`engine_u_endplates.py`（由 `make_bend_pdf.py WORK STAGE` 分发；u_endplates 结构）。

## 新单必须

1. `cp` 或 `ln -s` 本目录四文件到订单 `addendum-tools/`（再改 **cfg/孔位/零件列表**，不改这四文件）。
2. 出确认稿前跑：`python3 scripts/check_bend_pdf_golden.py $ORDER [--overlap $ORDER/logs/bend_pdf_overlap.json --strict-overlap]`
3. 对照规则 12 + 15 + 18 + 9 + **26**：海军蓝页眉、出图时间、红条 ERP、三视+斜视、双向折弯尺寸、去冗余、**金样哈希**、**dim overlap→0**。
4. **禁止**灰框 `tools/pdf.py` / `pipelines/*/pdf.py` 当确认稿外观外发。
5. 目视对照 `PAGE1_ASSEMBLY_REFERENCE*`。

## 尺寸避让

`pdf_common.dim` / `dimA` 与 u_endplates `dimh`/`dimv` 记录 text bbox；碰撞时按边 lane 外推或换侧；`logs/bend_pdf_overlap.json` 报 `remaining`。`remaining=0` → PDF 布局 PASS。

详见 `references/bend-pdf-golden.md`。


> **历史（v2.8.45）**：新单请改用 `assets/bend-pdf-golden-001-visual/`。本目录保留作 t43u 配色考古；其 matplotlib engine 默认字号过小，是 t59u 回归主因。
