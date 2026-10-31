# 四孔梯形把手：宽排两安装孔圆心距85.00mm

> 用户 t16u，2026-10-26：默认把手 = 原技能默认尺寸 `assets/profiles/handle-85-62-30-v1.json`（宽排85/窄排62/排距30，4×Φ6.6 = M6 过孔）；已是则保持。

只对已明确启用且布局为four_hole_trapezoid的新项目，缺失的wide_row_pitch激活85.00mm条件默认，status=default、source=workflow-handle85-2.2；policies只声明政策，不擅自增加把手或选择布局。示例命令：

```bash
python3 scripts/create_intake.py --output project.json --handle-layout four_hole_trapezoid
```

85.00指较宽那一排两个安装孔的实际圆心距，不能用旧84mm、孔边净距、四孔对角距离、安装座外宽或文字标注代替。宽排不因窄排、排距或孔径未知而改用历史数字。未选择具名孔型配置时，窄排、排距、孔径、数量、位置、方向、型号和公差没有新增默认；保持各自来源/状态，未知保持null。实际孔心测得的其它距离可在回读报告中记录，不自动提升为用户批准尺寸。

客户明确其它值保留原来源并显式覆盖，不能伪标default。既有项目迁移保留包括原84在内的明确记录，不自动改CAD；这不允许把旧值作为新项目默认。范围/布局未定时不从四孔数量推定梯形或把手数量。本次更新不声称任何历史客户CAD由84改85，也不确认未归属截图的文件身份。

## 参数与实例

handles包含layout、wide_row_pitch、narrow_row_pitch、row_spacing和patterns。每个pattern明确id、所属part_id、wide_hole_ids两个、narrow_hole_ids两个。四孔必须属于已声明的handle-purpose孔组、同一零件且不复用；实例数对已明确数量校验。没有足够的孔ID/孔中心/轴向时依赖步骤阻断，不按全局最小最大X猜孔对。

validate_project的model/cut阶段用当前实际记录的中心坐标核每一实例：共面、孔轴垂直、两排平行、宽排确实较宽，宽排圆心距符合本件参数。已明确的窄排和排距独立核对；未知时仅记录测得数值并HOLD。布局非此类型保持独立路径。

## 真实导出文件回读

handle_readback.py只读FreeCAD导出的真实STEP与实际CUT DXF；宿主预先具备FreeCAD/Part，未具备就BLOCK，不安装或伪通过。

```bash
<configured-FreeCAD-python> scripts/handle_readback.py project.json \
  --step exported.step --dxf cut.dxf --part 01 \
  --flat-maps actual-cad-flat-maps.json --output handle-check.json
```

flat-maps为每个pattern的明确CAD展开刚体映射，例如软件夹具的XY面用`{"handle-A":[1,0,0,0,0,1,0,0]}`，八值分别为a,b,c,tx,d,e,f,ty，映射x'=aX+bY+cZ+tx，y'=dX+eY+fZ+ty。要求单位正交、法向与孔轴平行；禁止用缩放/剪切将84伪装85。真实项目从CAD展开关系取得，不直接复制示例。

当前适配器每次只检查一个分件STEP、一个有效实体；装配/爆炸文件须按所属零件另行回读，不能混池借用其它零件的孔。STEP适配器读取有效实体平面上的圆形内环，回读孔径和实际孔轴，与明确基准上的中心核对；上/下表面的同轴圆视为同孔。DXF读取CIRCLE实际圆心及直径，与CAD映射逐孔配对，重新计算两排圆心距。坐标在孔轴方向的投影只用于相同轴线的表面圈归并，不是任意三维投影展开。椭圆、槽孔、不共面的四孔、非圆内环或其它不支持形态必须另用CAD适配器，不静默通过。报告的1e-5mm为计算对照阈值，不是制造公差或首件验收值。

每个包含此把手的DXF清单artifact增加formed_step与handle_geometry_report。validate_manifest对实际DXF再次读圆心，并绑定实际STEP/DXF SHA、当前参数hash、完整pattern覆盖；缺失/失败/过期报告阻断。报告绑定不是再次运行CAD；真实STEP孔轴检查须由handle_readback先执行。

PDF实际尺寸/孔表明确标85.00宽排圆心距与来源，图形必须来自同版几何，不能只改标注。原生03与把手孔心报告分别说明范围；孔心通过不代表真实展开、其它孔或生产放行。

## 显式常用安装孔型

新箱体入口支持选用assets/profiles/handle-85-62-30-v1.json：宽85、窄62沿Y、两排相距30沿X，M6参考通孔Φ6.6；每个中心分别声明，宽排朝箱体X中心。此配置是工程参考候选，不是全局默认或厂家型号确认。X恰位于中心时center_wide_towards可选方向，未写采用positive_x的候选约定。入口实际核STEP中心/方向和STEP/DXF85/62/30，不生成未知把手实体。见[常用配置](common-profiles.md)。
