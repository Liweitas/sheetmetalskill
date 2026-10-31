# R11 最小调用与复现

在解压的step-sheetmetal-delivery目录：

```sh
python3 scripts/verify_install.py
python3 -B -m unittest discover -s tests
python3 scripts/build_general_package.py assets/examples/general/A.json --output /absolute/new-archive --resolve-only
python3 scripts/build_general_package.py assets/examples/general/A.json --output /absolute/new-archive
python3 scripts/validate_delivery.py /absolute/new-archive/requirement_ID/revisions/实际入口返回的修订目录
```

真实七例作者回归（输出目录必须不存在）：
```sh
python3 scripts/selftest_general.py --output /absolute/new-general-selftest
```

参数来源/等级、工艺PDF及真实展开输出都由同一入口生成，不手工补几何。缺通用必填或显式冲突返回confirmation-only资料，脚本成功仅表示诚实输出确认资料，必须读取状态；不等于制造成功。其检查为：
```sh
python3 scripts/validate_general_review.py /absolute/实际确认修订目录
```

制造validate_delivery对此必须exit2。完整确认几何候选也必须读取general_design_stage与manufacturing_delivery_complete，不只读exit0。

有界反例在真实A输出副本执行，不生成模型、不改原件：
```sh
python3 scripts/selftest_general_integrity.py /absolute/A修订目录 --output /absolute/new-negative-evidence
```

公开外部依赖：Python3 + requirements.txt，FreeCAD及匹配的Python、SheetMetalNewUnfolder及networkx，Poppler pdftoppm。作者实际环境FreeCAD1.1.1、OCCT7.8.1、SheetMetal0.8.21、networkx3.6.1，见R11-evidence/runtime-probe.json。可用--cad-python/--freecad-lib/--sheetmetal-path/--pdf-renderer显式指定。本包不偷偷安装依赖或修改全局；沙箱Qt/NEON失败须取得授权执行环境，不绕过拒绝。

无正式编码字段仍可以解析/建模，标未命名待确认；正式命名规则和默认最终单ZIP沿用R10。测试夹具编号、材料、K和来源不替工厂确认。复现七例约数分钟，具体依机器；不得覆盖已有输出。
