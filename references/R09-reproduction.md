# R09 最小复现与独立复验交接

在新解压的step-sheetmetal-delivery目录中使用公开依赖（Python3.10+及requirements、FreeCAD/SheetMetal、Poppler/CJK字体），先verify_install和discover_runtime --probe。不要安装全局。

```bash
python3 scripts/verify_install.py
python3 -B -m unittest discover -s tests -v
python3 scripts/build_package.py /ABS/raw.job.json --output /ABS/new_archive --naming /ABS/actual-naming.json
```

命名JSON见references/factory-naming.md/schema；合成测试自行提供明确SYNTHETIC编号，不借用BOX530编号。省略--naming或输入空字段时输出未命名待确认，code=null。只用返回的公开revision_root，不把.R09-unpublished-engineering当最终目录；重复目录不覆盖。

```bash
python3 scripts/validate_delivery.py /ABS/returned_revision_root
python3 scripts/prepare_delivery_message.py /ABS/returned_revision_root
python3 scripts/selftest_dispatch.py /ABS/returned_revision_root --output /ABS/new_dispatch_cases
python3 scripts/selftest_receipt_authority.py /ABS/returned_revision_root --output /ABS/new_receipt_cases
```

selftest_dispatch只检查运输/消息，不重建CAD，不将其单独称为实际CAD通过；完整门禁和prepare CLI另实际读取CAD。旧R08完整包更名用publish_named_delivery.py SOURCE_ROOT --output NEW_ARCHIVE --naming NAMING_JSON；它保留原件且重新执行目的门禁。

独立检查：同一正式前缀覆盖套料DXF、套料预览、完整折弯PDF、CUT/BEND（存在时）、STEP、BOM/参数/验收及唯一ZIP；ZIP只有修订目录一个顶层。确认文件的字节与更名前模型相同，FILE_NAMING记录/manifest/参数引用/清单/ZIP一致；升版v2需要previous_code，前五段不变，编号/日期不得从内部R修订或当前时钟猜测。更改材质/t或非法日期/0/10000/字符串v需拒绝。

检查整次消息计划：默认只能一个ZIP；多个附件/多条默认散发拒绝；当前明确单件或先确认图可带真实证据作本项目例外，旧要求不得冒充当前授权。测试JSON不能证明真实用户授权，程序不实际发送。

作者实际证据在修复目录：BOX530_READONLY_AUDIT.json；BOX530_dispatch_tests/DISPATCH_TEST_RESULTS.json；final_naming_tests/{NAMING_AUTHOR_RESULTS.json,first.json,upgrade.json,BOX530_pending.json}；final_dispatch_tests/DISPATCH_TEST_RESULTS.json；final_naming_negative_tests/NAMING_NEGATIVE_RESULTS.json；final_receipt_regression_attempt2/RECEIPT_AUTHORITY_RESULTS.json；final_prepare_message_cli.json；EXECUTE_CACHED_GEOMETRY_RESULT.json；unit-R09-final-259.log。全部作者限定测试，R09独立复验待完成。
