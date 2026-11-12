# v2.7.2 R09 齐套文件与单包投递契约

当前发布入口和最终门禁另强制[R10发布契约](R10-publication.md)；R09规则/目录是基础，原R09独立失败不改写为通过。

R09沿用R08制造校验，新增最终默认一个完整ZIP消息计划。最终发送前必须读[统一投递约定](message-delivery.md)。下文R07字段/布局是历史起点，当前新生成契约为2.7.2-R09；只读兼容R07/R08，不改其冻结包。R08独立验收为限定通过，R09本次窄修复须另测。

本契约针对受支持的新尺寸矩形钣金箱体。用户显式结构和参数优先，不修改旧客户模型。完整数字交付不等于生产放行。R07候选等待独立复验，不能宣称所有agent/模型/宿主必定成功。

## 身份、修订和输入

`build_package.py job.json --output ARCHIVE_BASE` 强制写入：

```text
ARCHIVE_BASE/
  customer_C10/ 或 requirement_REQ003/
    revisions/
      R03/                       # 一修订一完整输出；已存在立即阻断
        STEP/                    # 每件成形、总装、爆炸
        DXF/                     # 每件真展开CUT
        NEST/                    # 按实际板号集中套料CUT、layout
        PDF/                     # 完整工艺图册、套料预览
        evidence/ preview/       # 原生平坯、CAD门禁、逐页渲染
        source_job_STAMP.json project_STAMP.json manifest_STAMP.json
        holes_STAMP.csv BOM_STAMP.json BOM_STAMP.csv
        DELIVERY_SPEC_STAMP.json ACCEPTANCE_STAMP.json
        FILE_SHA256_STAMP.json ENTITY_REV_DELIVERY_STAMP.zip
        DELIVERY_ENVELOPE_STAMP.json
```

客户与需求分开命名。job.id是本次设计ID，未提供delivery身份时仅作requirement ID，不猜客户编号。未指定revision时使用北京时间到秒+输入哈希后缀，避免分钟重名；工程文件仍使用同一北京时间分钟STAMP。历史修订原地保留，不覆盖/删除。发布ZIP是当前修订完整副本，不把旧修订混入。

确认稿 ZIP 版本（用户 t69u / v2.8.8；t40u / v2.8.10；**t43u/t44u / v2.8.11 升版默认**）：**凡用户将下载的新 CONFIRM_DRAFT 默认升工厂 vN**（含 PDF/打包/README 及几何变更；废止「仅几何才升 v」）。旧厂版 live zip(+sha256) 进 `SUPERSEDED/`；CHANGELOG 写原因；`production_release=false` 除非用户另说。revN 仅内部快照，对外以工厂 vN 为准。对外只信 live `{VER}_CONFIRM_DRAFT.zip`+.sha256。对外 zip **文件名必须以 VER 开头**（`{VER}_CONFIRM_DRAFT.zip` / `{VER}_CONFIRM_DRAFT_revN.zip` / `{VER}_OPEN_ME.zip`）；**禁止**裸名 `CONFIRM_DRAFT*.zip` / `CONFIRM_DRAFT_current.zip`；zip 内有且仅有一个顶层目录 `{VER}/`，CHANGELOG 放目录内。见[确认稿版本规则](confirm-draft-versioning.md)。

可选job.delivery由references/job.schema.json验证：

```json
{
  "namespace":"requirement",
  "entity_id":"REQ003",
  "revision":"R03",
  "sets":1,
  "stock":{
    "length_mm":2440,"width_mm":1220,
    "edge_margin_mm":10,"part_gap_mm":10,
    "status":"assumed",
    "source":"本次明确采用的试折板幅候选，现场待核"
  }
}
```

板材字段显式带mm，与job模型单位转换分开。未给板幅时只采用带来源的2440×1220、边距10、件距10试折候选，不标confirmed；未给sets时仅假设1试折套，不等于订单数量。所需板数由真实展开排布算出；若提供available_sheets且不足则阻断。材料/厚度继承本次job及其来源，BOM、PDF、参数与输入交叉核对，不能以STEP颜色推材料。

## 必交文件与程序检查

所有计划钣金件必须各有成形STEP、真实展开STEP及单件mm/CUT DXF；还须有装配/爆炸STEP、确认PNG、完整工艺PDF、套料DXF和预览PDF、BOM双格式、参数、源job、孔表、验收记录、哈希和ZIP。必交类型由代码固定推导，不信任调用方删除后的formats或一份自行缩短的文件清单。

`scripts/validate_manifest.py`在R07声明下追加齐套检查，保留R06实际CAD原生方向和BODY/LID权威干涉口径门禁。`scripts/validate_delivery.py REVISION_ROOT`进一步强制身份/修订目录、R07声明及继承R06核心契约、全文件哈希、ZIP成员覆盖/CRC/字节。缺ZIP或任何必交类型不能声明齐套。仅旧manifest/参数检查通过不等于R07齐套。

成功的DELIVERY_ENVELOPE中`digital_deliverables_complete=true`只指数字文件契约，`production_release=false`，人工逐页视觉复核和独立复验仍单列待完成。正干涉须保留实数和本项目专项授权，不能把现场修配接受改成零干涉。失败记录阶段及现存部分文件，未验收ZIP和RUN_RESULT隔离为UNACCEPTED/GEOMETRY_ONLY，不作正式齐套交付。

## 集中套料

发布默认（用户 t62u 2026-10-28 / v2.8.7）：**一盒一个 NEST DXF**（`{主码}_NEST_2440x1220_1BOX.dxf`）。先读取各实际单件DXF，只放 **1 套**完整盒体零件（各件×1）；订单套数写在 README/BOM/确认稿，**不**按套数复制进 NEST，**不**按物理板拆 `SHEETnn`（现场师傅自调套料）。当前采用保守外包矩形逐行排布，仅0°平移，不缩放、不改变轮廓、不擅自旋转纹向。不追求批量最优。一盒装不下单板立即阻断，提示选合适板幅，不静默缩件。

发布 NEST 由 `release_dxf.write_nests(nest_mode='kit')` 写出：CUT + SHEET（原点闭合 2440×1220 板框）、INSUNITS4、Z0、1:1毫米、CONTINUOUS、边距10、件距10；无折弯线/无文字。原生 `delivery_contract` 无板框套料仍只作证据。回读以实际分件DXF实体多重集及各实例平移逐一对照，防漏件、两倍尺度或重复线。实际外包矩形之间满足正件距、在板内满足边距。套料预览 PDF/PNG 对应 1 页/1 张（1BOX），仍须目视。旧按板 `NEST_SHEETxx` 仅内部/证据可选。

单件CUT与对应套料CUT是替代加工输入，避免重复切割。材料库存、板幅实物、纹向、激光切缝、热变形、桥接和机台CAM均未因此获确认。

## 工艺PDF

首页明确身份/修订/STAMP、材料牌号/t、体外长宽和含盖/无盖高度口径、状态、件号数量、Ri/K/BA/BD与来源状态、板幅候选/套数及试折注意。所有图页显示当前技能版本。实际成形三视、轴测斜视、原生展开、孔表、03细节保持原CAD来源；零折端板也补实际斜视。

逐件工艺页列原生B编号、展开中心线两端坐标、原生UP/DOWN及signed angle、所选根面、成形参考点。靠边候选从实际CUT外圈寻找覆盖至少半条实际弯长的平行直边，排除03短释放边，给实体索引/端点和几何距离；不是机床BG。盖裙给外高、自由直段、弯带和中心距离。无明确自由直边时只用X0/Y0几何基准，靠边待核。顺序标NATIVE_ID_ORDER_CANDIDATE_NOT_TOOL_VALIDATED，未知实际刀模/定位/退刀/回弹不伪造机床程序。现场记录栏保持待填写。

## 既有STEP限制

`audit_step.py SOURCE --output ARCHIVE_BASE --entity-id ASM0027 --revision R01`同样隔离身份/修订，仍保留原结构、角型、真实BOP/厚度/R/孔/干涉与受支持展开，不自动重拆件、开接缝或改参数。当前源审计模式**不声称完整制造齐套**，即使部分件成功展开也只出`SOURCE_AUDIT_ONLY_PARTIAL_HOLD`审核ZIP并退出2。

SOURCE_DELIVERY_STATUS逐一列原件/确认图/STEP、每件展开状态、套料/预览、完整制造工艺图册、BOM/参数、哈希/ZIP的PRESENT/AUDIT_ONLY/BLOCKED_UNSUPPORTED状态和原因。未知材料/K、诊断K、缺平坯/拆件确认不可升级生产数据。`validate_delivery.py`对这种审核根目录明确拒绝齐套声明。用户要求实质重建/制造补齐时需明确参数与结构授权，选择受支持重建路径另出新版本，而非伪造本模式支持。

## 复现与证据

`python3 -B -m unittest discover -s tests -v`；`python3 -B scripts/selftest_delivery_contract.py --output /ABS/NEW_TEST`会从包内纯合成raw job执行两种尺寸结构、未知材料/K源审计、必交缺件、错版本/材料/t、套料漏件/重叠/尺度、ZIP缺失及实际原生方向伪报反例。模拟授权明确标SYNTHETIC，绝非客户许可。作者结果与R06历史独立验收分别保存；R07须另由独立agent前向复验。


## 对外交付落盘（Mac · 规则27）

数字齐套 zip 生成后，执行方还必须将 `{VER}_CONFIRM_DRAFT.zip`（及折弯 PDF、sha256）同步到 Harry Mac 路径 `…/骊臻/客户图纸/YYYYMMDD/`（订单日码）。只写 box/Downloads/聊天不算本契约下的完成交付。
