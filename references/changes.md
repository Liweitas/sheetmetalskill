# 窄变更与证据失效

只改把手孔等窄请求，先确定获授权的孔ID、所属件、尺寸/位置和对应面，再修改该特征及必要下游。原件和无关零件保持，分别核SHA；同一件中的非授权孔、外尺寸/基准、编辑区域外BRep用CAD求差验证。不通过擅自移动其他孔或改外形来掩盖问题。

`compare_change.py --plan`比较参数值并列出依赖失效；材质/t变化要求展开、补偿/硬件/首件等重验。它不自动更新几何。

窄改验证输入两份snapshot：`parts[id]`含相对file、实际sha256、bbox_mm六值、volume_mm3及holes字典。hole含center、axis、diameter_mm、kind=through_circle、local_t_mm。允许的编辑孔用`part:hole`明确列举。提供独立CAD生成的witness：method=`CAD_symmetric_difference_outside_edit_regions`、evidence_ref、allowed_holes、baseline_parts_sha256、candidate_parts_sha256、每个受影响件的outside_edit_regions_symmetric_difference_mm3。

脚本核文件SHA、所有非授权孔记录、无关件字节、外尺寸、CAD证据输入SHA绑定和简单通孔体积差。没有witness或证据对应旧文件即阻断。它**不自行运行CAD求差**，witness必须由实际CAD比较产生；合成测试文件只验证契约，不是客户CAD证据。沉座/相交特征等超出简单通孔模型时应使用相应CAD验证适配器，而不是强行通过公式。

示例CLI：
```bash
python3 scripts/compare_change.py before.json after.json --plan
python3 scripts/compare_change.py before.snapshot.json after.snapshot.json --witness cad-witness.json --root project-directory --allow-hole lid:H37
```

纯排版只更新PDF/页图/清单。孔径/位置更新所属件成形/展开/CUT/孔表/视图、组合、配合轴检查和相应PDF。材料/t/Ri/定位/拆件影响范围扩大；已经失效的首件和量产批准不能继承。异常授权与更改原因保留，不能因新消息谈别的参数而抹掉已有有效决定。
