# 参数、范围与来源

源STEP事实存`step_facts`，用户目标存`requirements`，工程候选用`status=assumed`及独立来源。禁止把用户要求的材料牌号直接写成“源材质实测”，或把旧同名文件当本次附件。先核附件身份、字节数、原件SHA、单位转换与实体，再决定何处重建。没有板厚/Ri圆柱弯面不能猜Ri=0；尖角可能只是名义外观。

每个业务参数是`value/unit/source/status/note`。未知`value=null,status=unknown`；不适用也null但给原因。known/measured/confirmed需来源；历史引用和工程假设不能自己升为confirmed。`source`链接provenance记录，记录真实消息时间（不可得则null）和记录时间。结构ID、列表名、schema版本不是测量参数。严格结构见[project.schema.json](project.schema.json)，不允许多余字段或把数字写成含单位字符串。

`scope=body_only`必须对应`body_only=true,lid_required=false`；`body_and_lid`相反。`nuts_required`单独确认：沉头通孔不隐含螺母或螺纹连接。源有盖、目标不要盖完全可能，保留源事实而过滤目标；不能把两个层次误判为矛盾。显式无盖后，lid设计字段null/not_applicable，计划中不得保留盖件。

尺寸标内/外，长宽高各映射X/Y/Z（不得重复）；定义原点、底外/底内、盒口、盖内顶/外顶、裙底。裸盒高和含盖高分别表达。间隙必须说明单边/双边总值、方向和测量面。盖类型、裙高、角形、落座/承托等仅在有盖时填写。把手数量、型号、每个安装孔数和方位不根据历史或孔数推断；接头位置注明孔心或孔边基准。

输出分钟号`YYYYMMDD_HHmm`，时区固定本流程要求的`Asia/Shanghai`；创建时间显式`+08:00`且分钟一致。原件历史UTC标识不强改为新几何版本；换算关系保留在记录。其他消息可保持真实原时区。材料与实际t不明可审计；建模/下料所需尺寸不明时只阻断依赖项，不能全局停止可做工作。

空模板不擅自添加盖或螺母；范围未定时只声明g/03条件政策，确定新有盖范围后激活。孔径、Ri、K、把手数量和余厚验收没有全局默认值。显式具名试折/孔型配置的候选值、来源与HOLD见common-profiles.md。客户表允许“不知道，请按附件核验”；接图人应回填可实测项并集中询问功能缺口，不让客户重复提供可从本次附件可靠实测的量。

盒盖新增默认与来源/迁移/03实几何定义见[lid-defaults03.md](lid-defaults03.md)，完整条目见[中文规则清单](rules-checklist-cn.md)。

四孔梯形把手宽排条件默认85.00mm，其他孔距/排距/孔径不推定。参数实例、导出STEP/DXF真实孔心回读和报告绑定见[handle85](handle85.md)。

job输入的数字默认是requested要求，不能批量标confirmed。K、角缝、拼缝缺逐字段证据默认assumed；input_provenance保留工程假设/用户确认/工厂实测的区别，见common-profiles.md。
