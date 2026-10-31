> R07入口--output为归档父目录，自动隔离身份/修订。当前此模式统一给SOURCE_AUDIT_ONLY_PARTIAL_HOLD审核包/退出2，不声称齐套制造；逐项槽位与限制见[delivery-contract.md](delivery-contract.md)。

# 既有 STEP：通用审计、受支持展开与真实 partial/HOLD

使用scripts/audit_step.py；不要把未知既有STEP转成新箱体job再重建。入口读取每个实际Solid，保留原坐标、结构、角部、g/q和孔。该路线不是任意STEP一键制造认证：当前受支持几何为显式毫米STEP、均匀薄板的平面/圆柱弯、圆形通孔与LINE/ARC/CIRCLE平坯。其它曲线/槽、复合成形、表面模型、无法双重测厚、原生算法失败均报告BLOCKED，不换假几何求通过。

## 最小调用

```bash
python3 scripts/audit_step.py /absolute/source.stp --output /absolute/new-source-audit
```

output须不存在。依赖同QUICKSTART，支持相同的只读发现/显式路径参数。前置要求源STEP含SI_UNIT(.MILLI.,.METRE.)，不从包围盒猜单位；其它单位转换需另外已验证路线。--expect-sha256可绑定本次附件身份。

默认材料/K未知，不猜、不添加新订单默认。平板仍可刚体转平；弯件的制造补偿依赖阻断，但全部零件仍出实际三视、圆弯测量和失败说明。若仅为展开算法诊断，可显式--diagnostic-K 0.5；仅改变诊断运算，不把K写成制造值。

复制assets/templates/existing-step-audit.json填写可选配置，--config传入。schema见references/source-audit.schema.json。K_ANSI必须同时给K_source和K_status（requested/assumed/measured）；材料须material_source。diagnostic_K_ANSI始终独立于制造K。工程估计保留assumed。diagnose_invalid=true才允许对严格BOP失败件做诊断展开；即使平坯有效，也保持DIAGNOSTIC_ONLY。

part_roles只为明确来源的语义分类标签，不凭Solid数量恢复装配BOM。可选interface指定body_ids、lid_id和up_axis/up_sign，按实际平面测g/q；选用代表直壁的body件，不能拿不相关底板外伸尺寸替代箱壁。未指定时不猜g/q。实际相邻孔轴报告通过有限厚度/距离筛选排除对侧壁的无限轴线重复匹配，报告仅证明几何相邻，不确认紧固用途或螺纹。

## 同源流程

1. 记录原件字节/SHA，建立自己的源件副本；原件始终只读。逐件导出STEP并回读，记录基础isValid和严格check(True)分别的结果、体积、边界和容差。三件有效不等于装配及制造通过。
2. 记录每面类型、平面皮距离及重叠、圆柱半径/轴/角度、共轴分段面孔分组。没有整圆边也可由同轴半圆柱总角2π、轴向厚度及半径识别圆孔。局部BSpline角面不因此被认证等厚。
3. 支持平板对实际BRep刚体转平；弯件选面积最大的有限个实际根平面，调用同一原生getUnfold和双重测厚。明确记录尝试根面、K来源和异常；闭合围框失败保留原件，不自动开缝，不宣称所有CAD都不能处理。
4. 有效平坯导出STEP回读。共用cad_dxf.write_dxf从该真实平面写INSUNITS4/CUT，整圆分段弧可等几何合并为CIRCLE。实际DXF再重建面，与原生平面做双向面积比较；源孔数量覆盖必须一致。原生Import.writeDXFObject输出另保留为NATIVE_RAW，不能把其缺单位/层说成原共用writer出错。规范化改变文件表达，不改变几何、坐标尺度、原STEP或旧DXF。
5. 逐件成形三视、孔轴表、实际圆弯角/R和补偿状态、已得到的真实展开/折线，以及失败件缺平坯说明，统一纳入SOURCE_REVIEW_BENDING_PARTIAL_HOLD.pdf。图册覆盖全源件，不能称未取得的完整制造折弯图已完成。无确认K时BA/BD未知；显式诊断K算出的值均标diagnostic，几何折线位置不是机台BG。逐页渲染仍需执行agent目视。
6. source_manifest与validate_source_manifest验证实际文件SHA、全部源件记录、每份可支持STEP/DXF绑定及PDF覆盖。AUDIT_RESULT独立报告audit_completed、geometry_delivery_complete和manufacturing_delivery_complete。PARTIAL_HOLD退出2且写BLOCKED_RESULT；没有制造成功RUN_RESULT。AUDIT_COMPLETE_WITH_HOLD退出0只表示支持的全部几何步骤完成，制造和批量放行仍false。

## 角方案与无设计变更试验

既有盖保留原角，不自动套新订单03；8条斜边不证明符合本技能03。需要对照时使用diagnose_corner03.py明确给出t/Ri/裙高/角缝/K假设，对实际DXF比较，输出hypothesis_only；匹配也不能替代成形STEP严格BOP与native03_check。明确原03要求的交付仍须原生03门禁，不能用preserve_source标签把不符03冒充通过。

try_non_design_repair=true仅在副本对同一组面重建shell/solid，记录前后所有几何测量、孔、t/R、体积、边界、顶点距离、容差与BOP；不选择其替换原件。任何容差增加、几何差异或BOP失败都不是可接受修复。removeSplitter在实际失败源试验中会提升内核容差，已排除出源件修复路径；不使用fix()、删面、提高公差等方式凑通过。

切缝、改变拆件、改g/q或改角方案均是设计变更，必须先给方案与影响并取得用户确认；本入口不提供这些动作。原盖BOP错误若API只给类型与数量、不提供子形状编号，必须明确未定位，不虚构错误面号。

## 可复现测试与范围

```bash
python3 -B -m unittest discover -s tests -v
python3 scripts/selftest_existing_step.py --output /absolute/new-source-regression
python3 scripts/validate_source_manifest.py /absolute/run /absolute/run/source_manifest.json
```

selftest_existing_step以公开新箱体示例生成合成STEP，再从导入入口验证支持的弯件和未知K反例；它不替代用户实际STEP测试。作者实际源件试验与合成测试分开记录，完整包不含用户模型或用户目录依赖。生产材料、标定K/BD、BG、回弹、工装、焊接、硬件、强度及首件始终需要独立证据。

## 获授权重建后的先行成形审核

用户明确授权按新结构重建后，可先用review_box.py读取本次尺寸job。其review-job.schema允许material/K保持null，成形生成不使用K，也不出制造DXF或补偿值。实际成形STEP与确认PNG仍做单件严格BOP、孔中心/径/轴和导出回读；proposed角方案/端退等差异应使用--review-note明确写在确认图，并另附前后差异表。该入口不能把未确认的建议当既有设计值，不代替完整制造门禁。

```bash
python3 scripts/review_box.py /absolute/review.job.json --output /absolute/new-formed-review --review-note 'PROPOSED changes and unknown parameters; production HOLD'
```

重建源孔须独立记录刚体坐标矩阵、原实体/孔ID到新零件/孔ID的映射，并在导出件上逆变换回读实际孔心/径/轴；对源孔不能套用未请求的把手或螺纹配置。原坐标STEP和模型坐标STEP应明确区分。包含正交叠的Compound整体BOP与各Solid的BOP分别报告：单件有效不能证明装配零干涉，装配整体失败也不能直接归咎于盖单件。

## R04输出复核门禁（必须实际CAD执行）

validate_source_manifest不再仅核SHA和报告内面积值：它严格比较manifest、最终AUDIT_RESULT及PARTIAL时BLOCKED_RESULT的所有派生状态、逐件覆盖、diagnostic列表与holds；最终结果是清单中的真实绑定文件。修改几何完成标志或最终放行声明不能通过。

通过前置检查后，强制启动独立只读CAD回读进程，读取本次实际源STEP及逐件成形STEP；实际核BOP、体积/边界与对称差、板皮厚和物理孔。对有平坯的件从实际源件重新原生展开，使用独立ASCII DXF读侧解析及闭圈重建，重新算源平坯/展开STEP/DXF双向面积差和厚度，不信任已存面积0。没有CAD依赖/API/权限则BLOCKED，没有跳过或读缓存冒充实际核验的开关。它不修改审核目录；临时文件位于系统临时目录。

CAD/PDF公开依赖路径可经显式同名参数传入，不执行run中任意声明的可执行文件。可用--expect-source-sha256绑定从用户原件取得的可信SHA；否则以本次run保存的源件副本为几何锚。哈希和几何复核不构成对同时任意替换所有输入、可信源和工具程序者的密码学保证。

旧R03产物可以用新门禁复核：即使旧清单尚未列最终AUDIT_RESULT，仍强制读取并核其语义。新R04产物必须绑定最终结果文件；不能只刷新manifest后声称完整交付或制造放行。
