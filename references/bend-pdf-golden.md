# 折弯 PDF 金样与一致性（v2.8.45 / 用户 t43u + t61u + Harry t59u/t60u）

## 金样（只读公共库）

**视觉权威（Harry t59u，2026-11-06）**：用户评价 `S-201-1-20261031-001-v1`（kit `box-320x155x105-inner`）折弯 PDF「生成效果非常好」——字号、尺寸位置、标注效果为后续标准。拥挤可接受；**不要硬卡 4 页**；为卡页缩小文字/把尺寸挤难看 = 不合格（规则6 / 规则32）。

- 参考 PDF：`orders/box-320x155x105-inner/…/S-201-1-20261031-001-v1_完整折弯工艺PDF_折弯师傅作业图_4页.pdf`
- **权威目录（自 2.8.45）**：`assets/bend-pdf-golden-001-visual/`
- **锁定五文件**：`make_bend_pdf.py`、`pdf_common.py`、`bidir.py`、`views.py`、`engine_u_endplates.py`（哈希 `GOLDEN_SCRIPTS.sha256`）
- **旧金样（历史）**：`assets/bend-pdf-golden-004-v2/`（t43u 配色认可；但其 `engine_u_endplates` 默认 dim≈5–6.5pt，是后期 PDF 字小主因，**新单勿再 cp**）

### 根因摘要（t59u 对照）

| 路径 | 栈 | 尺寸字号 | 页数 |
|------|----|----------|------|
| 001-v1（好） | reportlab `make_bend_pdf`+`pdf_common` | MINPT=9.4；dim≈9.5；视图 sc≈0.55–1.1 | 4（拥挤可接受） |
| 004-v2 门禁四文件 | reportlab（U+L+LID） | MINPT=9.4，但部分 bidir 曾写 size=8.5 | 4 |
| 后期 u_endplates 实单 | **matplotlib** `engine_u_endplates.py`（由 make_bend_pdf 分发；**旧门禁未校验**） | 默认 fs=6.5，展开常 5–5.5 | 硬编码 `/4` |

2.8.45 合并：matplotlib 路径强制 ≥9.4pt、默认拆 U/END 页（≥5 页）、五文件哈希门禁；保留重叠避让、规则9、页眉出图时间、处理面朝外（规则31）、海军蓝+红条。

### 规则26：哈希门禁（硬）

出确认稿前必须：

```bash
cp -a $SKILL/assets/bend-pdf-golden-001-visual/{make_bend_pdf.py,pdf_common.py,bidir.py,views.py,engine_u_endplates.py} \
  "$ORDER/addendum-tools/"
# 或 ln -s 到上述五文件（内容 sha256 必须与金样一致）
python3 $SKILL/scripts/check_bend_pdf_golden.py "$ORDER" \
  --overlap "$ORDER/logs/bend_pdf_overlap.json" --strict-overlap
```

- **MATCH** → 继续；**MISMATCH / MISSING** → **BLOCK**，禁止把订单内「改完的引擎」当交付。
- 灰框 `tools/pdf.py` / `pipelines/*/pdf.py` **禁止**作确认稿外观外发（规则12）。
- 几何/孔位/零件表仍在订单 `tools/cfg.py`、brief、CAD；**不得**为改几何而 fork 金样五文件。

### 尺寸避让（原型）

`pdf_common` 的 `dim`/`dimA`（及 u_endplates `dimh`/`dimv`）维护 text/dim bbox；碰撞时沿边 lane 外推或换侧，并累计：

| 字段 | 含义 |
|------|------|
| attempted | 参与避让检测的尺寸文字数 |
| resolved_by_nudge | 外推成功 |
| resolved_by_flip | 换侧成功 |
| remaining | 仍重叠（应力争 0） |

`remaining=0` → PDF 布局 **PASS**；否则 WARN（`--strict-overlap` 时 BLOCK）。报告：`logs/bend_pdf_overlap.json`。

2026-11-10：`u_endplates` 金样引擎另用实际渲染文字边界检查整页标题、说明框、孔号引线和跨视图文字；`page_checks` 按页列问题，`dimension_remaining` 保留原尺寸避让计数，`remaining` 合计两类问题。说明框按实际字宽换行，装不下时报 `PDF_LAYOUT`；文字重叠或超页时入口失败，不将临时 PDF 改名为正式输出。孔组只在图中标主孔号，固定小孔的完整孔径和坐标保留在第4页孔表。

自动检查覆盖矢量文字边界，不能代替图线、引线及嵌入轴测图片的逐页目视核验。

## 一致性清单（出图后门禁自检）

| # | 项 | 不合格表现 |
|---|----|------------|
| 1 | 海军蓝页眉 + 红条材料栏（规则12） | 灰框/另套配色 |
| 2 | 每页 `出图 YYYY-MM-DD HH:MM Asia/Shanghai`（规则15） | 仅页脚或元数据 |
| 3 | 红条/页眉一眼可读：**材料、板厚、外形尺寸、工厂编号 VER、出图日期**（规则18 / ERP） | 缺任一 |
| 4 | 总装页：**三视图 + 斜视图**（绿盖褐箱）（规则18） | 只有展开或只有照片感轴测无三视 |
| 5 | 展开双向尺寸（规则9） | 单向或只标总长 |
| 6 | 去冗余（规则18） | 大段重复说明挤占视图 |
| 7 | 脚本血统：addendum 五文件 sha256 = 金样（规则26） | fork / 灰框 tools/pdf.py 外发 / 仍用 004-v2 旧 engine |
| 8 | dim overlap `remaining=0`（规则26） | 尺寸字压字未处理 |
| 9 | **001 视觉字号**（规则32）：尺寸/注记 ≥约 9.4pt；不为卡 4 页缩字 | 展开 dim≈5–6.5pt；硬编码 n/4 |

几何与孔位随本单；**版式与必填栏不得回退**。旧参考 `box-550x195x150` / `bend-pdf-golden-004-v2` 仅历史；**自 2.8.45 起以 001-visual 金样为准**。

## 稳定出 PDF 目视门禁（t106u / v2.8.28）

规则9(b) 必须是尺寸线。`check_bend_pdf_golden.py` 不 OCR 尺寸线；出图后须导出补件/SIDE 展开 PREVIEW PNG，确认每折有「距A/距B」尺寸线，不得只剩总长宽或折旁文字。
