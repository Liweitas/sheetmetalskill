本版新箱体使用scripts/build_package.py，强制真实CAD/03/完整交付门禁；下面的独立参数命令不构成出图完成。详见box-generation.md。

# 可执行校验用法与限制

参数检查需Python3.10+及jsonschema；PDF生成/回读需ReportLab和pypdf，完整测试包含PDF。具体依赖见下方清单。依赖清单见[runtime-requirements.txt](runtime-requirements.txt)。缺失时清楚报未执行，不静默降级；需要安装依赖时在获授权的隔离环境处理，不修改其他agent全局配置。

- `create_intake.py --output project.json`：创建业务值为空的表；只明确写入本流程北京时间编号政策，不填设计默认值。
- `validate_project.py project.json --schema-only`：结构检查。空表可结构通过，但不代表有足够数据建模。
- `validate_project.py project.json --stage audit|model|cut|release`：阶段与跨字段检查。退出0表示指定参数检查无错误；PASS_WITH_HOLD仍不能生产。退出2表示阻断该依赖步骤；可继续附件审计和无关草案。输出是结构化errors/holds/computed，不把“通过”文字当认证。
- `validate_manifest.py project.json manifest.json --root dir`：对实际文件做参数hash/版本/SHA、基础DXF实体、外圈闭合、自交/零面积、圆孔越界/相交与激光孔数/径检查。不回读STEP，不验证实际空间孔轴，不等于CAM。
- `compare_change.py`：依赖计划或窄改契约检查，详见[changes.md](changes.md)。

清单格式：version、timezone=`Asia/Shanghai`、parameter_hash（`validate_project.parameter_hash`生成），artifacts数组。每项包含path、kind、sha256、parameter_version、parameter_hash。DXF项另给stage=`laser`、part_ids和可选outer_boundary_entity_indices（从0编号）。普通LINE/ARC外圈可自动分组；圆形毛坯外圈须明确indices。当前适配器只验证圆形内部孔，槽/任意内切口需真实CAD适配器，不能冒称已覆盖。

示例结构（值必须从本次实际文件生成，不复制示意字符串）：
```json
{"version":"20400102_1015","timezone":"Asia/Shanghai","parameter_hash":"<本次canonical SHA256>","artifacts":[{"path":"part_20400102_1015.dxf","kind":"dxf","stage":"laser","part_ids":["01"],"sha256":"<实际文件SHA256>","parameter_version":"20400102_1015","parameter_hash":"<同源参数SHA256>","outer_boundary_entity_indices":[0,1,2,3]}]}
```

测试：从Skill目录运行`python3 -m unittest discover -s tests -v`。测试虚构A/B参数夹具及缺参/矛盾/孔用途/半径直径/边距/补偿/时区/材料失效、实际临时DXF字节、窄改证据绑定。合成临时几何文件不当作CAD；真正的实体、孔轴、展开、工艺与PDF验证仍按[检查清单](checks-and-release.md)执行。

平面适配器用解析交点/距离检查LINE、ARC、CIRCLE。圆弧绕数判断离散最大弓高0.001mm，孔靠边0.002mm保护带内保守阻断，重合圆弧等复杂边界也阻断后交给CAD适配器；不把近似检查标成精确加工验收。本版清单不接受省略计划钣金件的DXF，也检查全部请求格式；局部审计应建立明确限定范围的独立审核项目，不能拿完整项目的子集宣称完整交付。new_design还强制逐件原生展开/STEP/DXF面积报告绑定；03强制本次原生重展开与盒体核验。

虚构夹具中的audit_passed、measured、confirmed、授权记录是软件模拟输入，不是实际CAD核读、工厂测量或真实批准。其attachment SHA只对应随包合成文本，不对应STEP；不要把这些模拟字段复制到真实订单。

CUT实体只接受默认挤出方向(0,0,1)和零实体厚度；其它OCS方向/非零厚度不在基础二维适配器支持范围，明确阻断并转CAD适配器，不静默按XY处理。

新项目默认解析、旧项目迁移及实际03/CAD/PDF门禁见[lid-defaults03](lid-defaults03.md)。`create_intake.py --lid yes`激活g/03；`--lid no`标不适用；未指定范围只声明条件政策。

四孔梯形把手宽排条件默认85.00mm，未显式选具名孔型配置时其他孔距/排距/孔径不推定。参数实例、导出STEP/DXF真实孔心回读和报告绑定见[handle85](handle85.md)。

R02自测及来源规则见[常用配置](common-profiles.md)和[厚度根因](thickness-measurement.md)。完整门禁还要求确认PNG；启用安装孔时强制实际STEP/DXF把手报告；启用周边孔时强制10对或本件计划的全部同轴配对报告。缺失任何报告仍BLOCKED。

既有STEP使用audit_step.py与validate_source_manifest.py，契约见existing-step.md；与new_design参数/manifest路径分开。源件审计门禁通过不代表全部平坯或制造完成，必须查看PARTIAL_HOLD、diagnostic_parts及逐件失败。

R04既有STEP最终门禁强制实际源/成形/展开STEP/DXF独立回读和重新原生展开，核最终AUDIT_RESULT与全部派生状态。依赖不可用时阻断，不能用旧报告值代替。详见existing-step.md。
