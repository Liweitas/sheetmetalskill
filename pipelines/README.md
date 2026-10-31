# v2.8.2 生产管线（两种结构变体，由 brief 选择）

解释器：`FC=/opt/freecad-dl/FreeCAD-1.1.1/usr/bin/python`（FreeCAD+SheetMetal），`AV=/workspace/addendum-venv/bin/python`（ezdxf/matplotlib/fontTools），
`SV=/workspace/sm-venv/bin/python`（reportlab/pypdf），`python3`（标准库）。没有 zip 命令，打包一律 Python zipfile。
所有输出目录必须是新的（脚本拒绝覆盖）；任何管线都**不发送**任何东西，确认稿只是文件。

## A. u_l_t7u（U + L：L 盖 U，0缝不退让 + t7u 盖；brief 未写结构且 max(L,W)<H 时用，或用户明确选 U+L）

> 用户 t16u（2026-10-26）：不留缝、不退让0.2。`release_config.json` 可选键 `l_cover_setback_mm`（L外露边退让）与 `lid_long_skirt_setback_mm`（t7u 长裙外露端退让），缺省都为 0；只有用户本单明确要求才设非0并写来源。

来源：干画图3 `/workspace/orders/box-180x420x175/addendum-tools/`（007），见 `/workspace/shared/sheetmetal_lessons_干画图3.md` §1.3–1.5。
v2.8.2 改动：订单目录取 `SM_ORDER`，开孔/把手只从 `release_config.json.features` 读（缺省=无），007 的顶孔断言只在配置了顶孔时运行。

```bash
export SM_ORDER=/workspace/orders/box-<W>x<L>x<H>       # 新单新目录；先查重名
mkdir -p $SM_ORDER/{briefs,evidence_src,logs}
cat > $SM_ORDER/release_config.json <<'J'
{"VER":"<用户给的发布名，原样>","note":"","history":[],
 "features":{}}            # 要顶孔/把手时才写: {"roof_holes":{"d":12,"pitch":30,"centre_to_lid_edge":50,"pts":[[48.5,75],[48.5,105]],"axis":"Y"},"handle_centres":[[..]]}
J
# 1) 原生技能出确认稿候选，只取 resolved_job + LID 证据
$SV -B scripts/build_general_package.py $SM_ORDER/briefs/X.brief.json --output $SM_ORDER/skill_R01 > $SM_ORDER/briefs/build.stdout.json
cp $R/evidence/*resolved_job_*.json $SM_ORDER/evidence_src/resolved_job.json; cp $R/STEP/*LID*.step $SM_ORDER/evidence_src/skill_LID.step
# 2) 管线（在 pipelines/u_l_t7u 下）
$FC build_main.py $SM_ORDER/evidence_src/resolved_job.json $SM_ORDER/evidence_src/skill_LID.step $SM_ORDER/work_main
$FC verify.py > $SM_ORDER/logs/verify.json; $FC views.py
$FC corner_probe.py $SM_ORDER/work_main/LID.step > $SM_ORDER/logs/corner_probe_t7u.json   # v2.8.2: H 取盖顶 ZMax（原默认133只对003有效）
$FC corner_mesh.py $SM_ORDER/work_main/LID.step $SM_ORDER/work_main/corner_mesh.json <H>
$AV clearance.py $SM_ORDER/work_main $SM_ORDER/logs/clearance.json
$AV post.py $SM_ORDER/work_main $SM_ORDER/post_out
$AV corner_png.py $SM_ORDER/work_main/corner_mesh.json $SM_ORDER/post_out/LID_CORNER_closeup.png '盖角 t7u 局部' '注1|注2' <H> 0 [长裙退让，缺省0]
$AV nest_png.py $SM_ORDER/work_main/NEST_SHEET01.dxf $SM_ORDER/post_out/NEST_preview.png 'NEST 2440x1220'
$SV make_bend_pdf.py            # 4 页 A3；字体自动子集嵌入（logs/cjk-sub.ttf）；逐页 pdftoppm -r 100 目视
# README/NAMING_NOTE：make_readme.py 是 007 文本模板（含客户原话/Ø12顶孔），只在 SM_README_TEMPLATE=007 时运行；
# 新单手写 README/NAMING_NOTE（每个文件 <VER> 开头），确认稿用 scripts/confirm_draft.py 生成 <VER>_CONFIRMATION_DRAFT.txt
python3 release.py              # STEP头/DXF 999注释写入发布名；几何哈希 = STEP DATA / DXF ENTITIES
# 3) v2.8.2 门禁：对 OPEN_ME.zip 解包副本跑（发布目录里另有中文名 PDF，会被 ASCII 检查拦下，属预期）
T=$(mktemp -d); python3 -c "import zipfile,sys;zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])" $SM_ORDER/named_release/<VER>/<VER>_OPEN_ME.zip $T
python3 ../../scripts/release_package.py package $T/<VER> <VER> --pdf-pages 4 --orders /workspace/orders
# 改名：python3 rename_release.py NEWVER   （几何 sha256 必须不变，失败自动回滚）
```
冒烟实测（2026-10-26）：`/workspace/skilltest/u_l_007/`（007 输入的拷贝）全流程 → U 774.57×172.8、L 419.6×351.685、LID 449.57×209.57；12 个 STEP/DXF 几何哈希与 007 交付一致；verify / corner_probe JSON 与 007 相同；PDF 文字逐词相同、字体全部嵌入、碰撞 0；v2.8.2 门禁全 PASS（007 原交付包在门禁里有 2 项 FAIL：STEP/DXF 内无发布名、PDF 字体未嵌入）；rename_release v1→v2test→v1 几何哈希不变。

## B. u_endplates（brief `"structure":"u_endplates"`：U + 两外封端板（平板零折弯、缝0、退让0、顶齐平，全盖U）+ 可拆盖，盖角=技能03方案）

来源：`/workspace/orders/box-400x220x150/tools/`（S-201-1-20261021-001-v1，t46u 版）。一条命令跑完：

```bash
source /workspace/sheetmetal-env.sh
SM_FC=$FREECAD_PYTHON python3 pipelines/u_endplates/run.py assets/examples/S-201-1-20261021-001-v1.release.json /workspace/skilltest/<VER>
```
步骤：build(FC，03盖角；gap=0 时另存未裁 native_untrimmed/) → project03 / corner_slice03 / corner_probe03（成形后闭合）
→ post(AV, release_dxf：CUT/BEND/NEST+SHEET，全部 CONTINUOUS) → STEP 头写发布名（BODY.step 不入 STEP，仅作 native03 输入）
→ **corner03（必跑，FAIL 即停）** → **native03（必跑，FAIL 即停；gap=0 时另跑未裁 native 证据）** → pdf（改名 `<VER>_BEND_PDF_A3_CN.pdf`）
→ docs(cwd=out) → confirm_draft → EVIDENCE（含 03 证据 JSON + src 快照）→ PREVIEW（含盖角03特写、展开角细节）→ release_package（`--pdf-max-pages 4`，门禁 + ASCII 单 zip + .sha256）。

brief 键：`seam_gap`/`end_inset`（缺省 0）、`end_top_flush`（缺省 true）、`corner_scheme` 必须 `"03"`、`corner_gap` + `corner_gap_source`（用户值标 user；未给则 0.2 标 candidate 候选）。`end_flange` 已废弃（出现即报错）。

gap=0 已知结论：熔合盖角有 1×1×13.2 共享柱，SheetMetal native 展开把它同时给两片折边 → 展开多 52.8 mm²（每角 13.2 mm³ 正体积干涉）。build 裁掉 4×(13.2×1.0) 使展开符合03定义，因此 native03 对裁后展开必 FAIL（差 52.8 mm² > 1e-5）；未裁 native 通过。
此时须 `SM_ACCEPT_NATIVE03_FAIL=1` 才继续，且报告必须如实写出并交用户选：A 接受裁后展开 / B 改候选 gap 0.2 / C native 展开带每角 13.2 mm³ 干涉。禁止静默改 0.2/0.4。

限制：`pdf.py`/`docs.py` 是手排模板，只对 400×220×150、gap 0 那组参数验证过，其他尺寸会拒绝（`cfg.TEMPLATE_OK`，run.py 在 PDF/DOC 前退出；强制 `SM_PDF_TEMPLATE_FORCE=1` 也只能当草稿）。
其他尺寸先用 A 管线或原生入口出 PDF。
复核（2026-10-26 12:53 Asia/Shanghai）：示例 brief 跑出 `/workspace/skilltest/u_endplates_v283_125328`，门禁 0 FAIL，9 个 DXF 几何与实单 named_release 逐实体一致。
