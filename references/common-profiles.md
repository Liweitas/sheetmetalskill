# 显式常用配置与来源状态

所有配置随完整包提供于assets/profiles/。只选择所需功能；未声明把手/周边孔时不增加孔，无盖也不会被配置变成有盖。

## 工程试折候选

job写workflow_profile="common_review_v1"时，缺失或null的K_ANSI可采用trial-review-v1中的ANSI K0.4；有盖且缺失/null的lid.corner_gap可采用0.2mm。来源为获授权的工程试折候选，无标定和生产放行。resolved_job列candidate_resolutions，canonical均assumed。数值明确给出则不替换。未选择profile的未知K/角缝阻断。g的单边0.5与03条件政策不变；q、Ri、裙高、拼缝等不得静默补值。

## 双把手安装孔

```json
{"handles":{"profile":"handle-85-62-30-v1","centers":[[118,130],[342,130]]}}
```

中心按job单位输入，孔型尺寸为配置定义的mm。85/62沿Y、两排间距30沿X，宽排朝箱体X中心；每把手四个M6参考Φ6.6安装通孔。中心恰在箱体X中线时可指定center_wide_towards（positive_x/negative_x），省略采用positive_x候选约定。安装界面参考源来自用户授权规范，不等于特定厂家把手型号、公差、包络或承载已确认；不生成未知实体。实际核STEP孔面中心、轴、径、中心位置、朝向及STEP/DXF的85/62/30，不能改标签冒充几何。

## 周边盖/体固定孔

```json
{"fixings":{"profile":"perimeter-m4-trial-v1"}}
```

候选体孔Φ3.3后攻M4，盖通孔Φ4.5；无真实线程模型或强度认证。默认离角40mm、相邻间距不超过200mm、孔高从盖外顶向下裙高一半；可显式给edge_offset/max_spacing/distance_from_lid_top，按job单位。460×260自动生成长侧X40/230/420、短侧Y40/220，总10对。U+两端板时短边体孔归端板；U围+L时前侧归L、其它归U。每对在装配基准内实际同轴验证，报告绑定所有STEP/DXF SHA。孔落弯根/外轮廓、结构缺件或实际孔对不成立均阻断。薄板攻M4强度、工厂底孔/螺钉配合保持HOLD，不能称制造放行。

## 端板轮廓退让

**默认 end_inset=0、seam_gap=0：端板盖U，不留缝隙，不退让0.2mm（用户 t16u，2026-10-26）。** 只有本单用户明确给非0值时：end_inset仅用于u_external_ends，在YZ轮廓向内退让：两侧和底边各退该值，底圆角半径Ri+t−inset，圆心与U外圆相同。默认上边也退；需要齐口须显式end_top_flush=true。沿X的seam_gap是另一个独立值，0.2轮廓退让不能当0.2轴向缝。CAD回读验证实际边界、圆心、半径与轴向间距。

## 每字段来源

job数字默认requested需求，不自动成为confirmed。K/拼缝/盖角缝无逐字段证据时assumed；可用以下形式保留真实来源：
```json
{"input_provenance":{"K_ANSI":{"status":"assumed","source_kind":"engineering_assumption","source":"本次工程试折假设，未标定"},"lid.corner_gap":{"status":"requested","source_kind":"user","source":"本次明确需求编号"}}}
```

支持material/thickness/Ri/K_ANSI/seam_gap/end_inset、dimensions.length/width/height、lid.g/skirt_height/corner_gap/roof_gap/corner_scheme。点式和斜线式字段路径均可。assumed必须工程假设；measured需工厂实测来源；confirmed需用户、工厂实测或厂家图纸来源。自动候选不能通过metadata升为confirmed/measured。无法验证来源文档真实性的数值仍不能自动工厂放行。
