# 工厂编码与文件命名（R09）

当前发布入口和最终门禁另强制[R10发布契约](R10-publication.md)；R09规则/目录是基础，原R09独立失败不改写为通过。

正式主码使用 ASCII 连字符：`渠道-材质-板厚-YYYYMMDD-四位编号-vN`。例如 `S-Q235-1.0-20261019-0001-v1` 只是格式示例，不授权把当前201改Q235、给BOX530分配0001或把内部R02当成v2。

渠道S=线上，X=线下。材质和毫米厚度须匹配本次实际源需求；厚度规范如1.0、1.2。日期必须输入并为有效日历日期，支持2026/10/19、2026-10-19或20261019，不能每次升版取今天。编号1显示0001，范围1–9999；编号唯一性、每组是否重置由工厂管理，程序不分配、不自动重置、不从客户编号推断；同目标目录存在即拒绝，不覆盖或自行加号。v为正整数，独立于内部R修订及软件版本。

换工厂版本时输入 previous_code；前五段必须与其一致，仅增加v后数字，不重新取日期、编号、材质或板厚。改变前五段须明确新工厂身份/规则，不能通过“升版”入口偷偷迁移；先保留旧包，另行取得新身份输入。既有客户10线上0010不是BOX530编号。

## 确认稿工厂 vN 升版（用户 t43u/t44u / v2.8.11；取代 t69u「PDF/打包不升 v」）

**凡用户将下载/解压的新 CONFIRM_DRAFT 默认升工厂尾缀 vN**（含 PDF 版式/布局、打包/README、以及几何/孔/结构变更）。同单修订保留前五段，只升 `-vN`；完整更名（zip 名、单顶层 `{NEW_VER}/`、内文件前缀）后，旧厂版 live zip(+sha256) 进 `SUPERSEDED/`，CHANGELOG 写升版原因。几何未变用 `release_package.py rename`（几何哈希不变）并重渲 PDF。**revN** 仅作*当前*工厂 VER 下的可选内部快照，**不是**对外区分主路径。完整配方见[确认稿版本规则](confirm-draft-versioning.md)。

## 命名输入独立于几何输入

按 [naming.schema.json](naming.schema.json) 提供单独JSON，避免改原始设计job而使现场专项授权设计哈希变化。生成器支持 `--naming /ABS/actual-factory-naming.json`。字段缺失时只输出 `UNNAMED_PENDING_CONFIRMATION`、缺项清单及“未命名待确认_需求或客户_内部修订”临时前缀，code=null；绝不补猜正式码。BOX530本次渠道已明确S，编号尚待工厂，示例0001不可采纳。

```json
{
  "channel":"S","material":"201","thickness":"1.0",
  "date":"20261023","number":1,"factory_version":1,
  "source":"替换为本次实际工厂分配或用户确认来源，不可照抄本示例"
}
```

```bash
python3 scripts/build_package.py /ABS/current.job.json --output /ABS/archive --naming /ABS/actual-factory-naming.json

# 已有齐套包只更名发布副本；不改原CAD/DXF、原始job或现场授权
python3 scripts/publish_named_delivery.py /ABS/original/revision_root \
  --output /ABS/new_archive --naming /ABS/actual-factory-naming.json
```

生成器先在 `.R09-unpublished-engineering/` 保留工程阶段，公开最终门禁不把此阶段当命名发布完成。之后发布新副本至 `customer_ID或requirement_ID/revisions/主码_内部R修订/`，ZIP只有该修订单一顶层。主码为正式码或明确“未命名待确认”前缀；所有文件同此前缀，唯一ZIP为`主码_完整资料.zip`。正式码前五段与v由工厂命名输入决定，R02仅作内部归档。

每个文件在主码后追加中文用途/零件后缀，并保留原零件名/板号/STAMP避免冲突。例如主码后：

- `_装配STEP_ASSEMBLY_STAMP.step`、`_爆炸STEP_EXPLODED_STAMP.step`、`_成形STEP_U_STAMP.step`；
- `_激光CUT_U_STAMP.dxf`、`_折弯BEND_U_BEND_ONLY_STAMP.dxf`；
- `_NEST_2440x1220_1BOX.dxf`（发布默认，用户 t62u：一盒一文件；旧 `_套料CUT_NEST_SHEET01_STAMP.dxf` 仅证据）、`_套料预览PDF_NEST_PREVIEW_…_1BOX.pdf`（1页）；
- `_完整折弯工艺PDF_需求ID_THREE_VIEWS_BENDING_HOLD_STAMP.pdf`；
- `_BOM_BOM_STAMP.json/csv`、`_参数_project_STAMP.json`、验收/哈希/命名更名映射及交付封套。

NEST_PREVIEW、THREE_VIEWS、时间戳仅是后缀，不能取代完整主码。公开门禁实际核主码、材料/t来源、目录、所有文件前缀及关键用途标签，重新读取本次CAD、源/实际图纸/展开、清单和ZIP。更名记录包含旧新相对路径、原始包/设计job哈希及制造文件逐个前后SHA；manifest相对引用、参数引用哈希、JSON依赖、清单与ZIP按新路径重绑。只改变文件路径及引用元数据，不改变STEP/DXF或原始job字节，不把参数引用哈希变化冒充几何变化。

## 不扩大工程或发送授权

命名记录不能证明工厂分号/确认文字真实，执行方须核实实际来源；同目录冲突检查也不代替工厂全局编号管理。原件、历史正式码/失败记录保留。材料、K、刀模/试折、现场修配/干涉、生产放行仍按原记录。命名后的最终默认消息仍只有一个完整ZIP；只有当前用户明确索要单件或确认图时才按[投递约定](message-delivery.md)例外。
