# 通用输入、来源与交付等级 R11

入口：`python3 scripts/build_general_package.py brief.json --output /absolute/customer-archive`。依赖与旧入口相同；`--resolve-only`只解析、不启动 CAD。原完整显式 job 入口继续可用，既有 STEP 仍使用 audit_step.py，不自动套新订单默认。

最少 brief：
```json
{"input_contract":"general-process-v1","id":"NEW_REQUIREMENT","units":"mm","dimension_basis":"outer","height_basis":"including_lid","lid_required":true,"material":"201","thickness":1.2,"dimensions":{"length":376,"width":224,"height":142}}
```
以上尺寸是纯合成调用示例，不是默认客户参数。尺寸和板厚必须正数；units支持mm/cm/m/inch。dimension_basis为inner/outer，height_basis为including_lid/bare_body。长宽是箱体口径，盖外尺寸另算；孔采用装配XYZ毫米（输入时随units换算），当前盒体长X、宽Y、高Z。源文件坐标系不同须先实测并显式映射，不能猜。

必须核实：三尺寸及口径/含盖、单位、板厚、是否有盖；缺少则无CAD假模型，只生成缺参确认PDF。材料牌号缺失可生成成形确认，不生成制造展开。接口/把手应提供实物孔型图、方向、包络/承载需求；异形须尺寸图或实际STEP并批准拆件。

四层来源：通用数学/结构规则；assets/process中的条件化经验候选；本款尺寸计算；用户明确覆盖或工厂记录。每行包含value/unit/origin/source/note/needs_confirmation；不将经验值标客户confirmed。默认策略文件哈希与原brief随包。完整job不可只手改编译结果/来源/等级，必须改原brief重新编译。

经验值不是标准：Ri .8、盖单边 .5、外封端轮廓退 .2（圆角同心配套）、拼缝候选0、03盖角和角缝候选.2、未标定K ANSI .4。K只作确认稿参考，不是材质或机床校准值；explicit值优先。03不是0.3mm。K实折记录须同时绑定material/t/Ri/K/刀模来源，不能从别款挪用。

结构：max(L,W)>=闭合H取侧底侧U+两外端板+盖，否则三面U围+底侧L+盖；用户显式structure优先，无盖不加盖。用户最新默认盖裙固定15mm，不按板厚/尺寸推高到16/17/20。显式其它值精确保留；15不满足Ri+t<裙高<体高或当前固定孔完整圆落在直壁等约束时，生成NEEDS_PROCESS_DECISION确认清单和冲突/建议，不自动提高或移动孔。刀模未知继续HOLD，不假称15已机台验证。

Ri/g给出理想盖根包络必要顶隙，未给q时加候选余量后向上取0.1mm，闭合H保持、体高=H-t-q。显式q不会被改；冲突输出调整建议和真实成形确认，不伪装零交叠或现场授权。实际BRep检查仍权威，公式不替代实际装配。

roof_ports默认two_reference，两孔直径候选18、沿宽中心对称、位置依本款尺寸；不是PG规格认证。`roof_ports:{"mode":"none"}`完全禁默认顶孔；`fixings:{"mode":"none"}`禁周边孔；`handles:{"mode":"none"}`禁把手。把手opt-in模式single/double/auto，当前85/62/30四孔参考，宽排沿Y朝盒中心，当前L推算中心；并不提供把手实物模型/活动包络/承载保证。周边M4候选3.3/4.5、距边与最大间距依跨度算，数量逐轴核验；薄板攻丝强度待核。

等级由原brief复算：默认confirmation_draft；requested_stage=trial加当前材料/t/Ri/K及刀模实折来源，且无未决输入，才为evidence_based_trial；production_record需同一physical_design_sha256的首件、装配、刀模与尺寸记录及工厂签署。工厂记录的真实性由提交方负责，软件不见证实物、不验签、不自动生产放行。真实刀模/后挡料/工序/回弹未知不能写机床可执行程序。

完整几何确认候选可包含所有真实制造格式，但文件名、首页、来源页与封套必须标确认稿候选；manufacturing_delivery_complete=false。源参数不足或配合冲突的formed_confirmation不含CUT/BEND/套料，用validate_general_review.py核资料完整性；validate_delivery.py明确拒绝制造齐套声明。

完整路径：原始brief+编译job+参数来源CSV/JSON；确认PNG；同件装配/爆炸/分件STEP；分件真实展开CUT及独立BEND层DXF；集中套料CUT/预览PDF；三视、成形斜视、展开、材料板厚、基准、逐弯位置方向角度顺序与Ri/K来源的中文工艺PDF；BOM/验收/哈希；同一修订目录、唯一完整ZIP。爆炸件只能平移同一实际成形零件。CUT禁止折弯线，BEND逐原生弯线回读。正式命名缺字段不猜，工厂v不等于内部R。

支持边界：当前两类矩形等厚直角结构与圆通孔；小尺寸孔/裙/圆角冲突阻断。异形、非90度、沉座、翻孔、压铆、内折边、焊接工艺及机台访问须实际适配，不声称全支持。工厂签署记录不会绕过BRep/原生方向/03/干涉与范围校验。
