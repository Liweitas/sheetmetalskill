# R10 复现与交接

解压完整包后在skill根运行verify_install、discover_runtime --probe及普通Python依赖。必须有公开FreeCAD/SheetMetal/Poppler/CJK字体，不跳过CAD门禁。

```bash
python3 scripts/verify_install.py
python3 -B -m unittest discover -s tests -v
python3 scripts/validate_delivery.py /ABS/original-R08/customer_ID/revisions/R01
python3 scripts/publish_named_delivery.py /ABS/original-R08/customer_ID/revisions/R01 --output /ABS/new-test-archive --naming /ABS/SYNTHETIC-naming.json
python3 scripts/validate_delivery.py /ABS/returned_named_root
```

原R08纯校验应0/LEGACY_UNPUBLISHED_READ_ONLY，正式/待命名输出应0/CURRENT_NAMED_PUBLICATION，并保留源制造契约R08、绑定named-single-zip-v2/2.7.3-R10三处。命名必须用真实提供字段或明确SYNTHETIC；不能给BOX530假编号。升版从首次返回目录发布，previous_code保留前五段，factory_version=2；缺正式字段命名JSON可仅含渠道，code应null。

原R09独立失败的精确根由 /Users/harryma/Documents/Codex/2026-10-21/task-6/acceptance_R09/failure_proof.json 的failure_root读取。对该原目录只读运行新validate_delivery，预期2/DISPATCH_REQUIRED_PUBLISHED；不得改原证据。合法R09命名目录可通过publish_named_delivery升级，缺计划的失败目录作为发布源仍必须拒绝。

反例只在新副本：正式、待命名、升版分别删final_message_plan/message_dispatch_contract；修改封套/manifest/命名记录的publication_contract或publisher_release并同步SHA清单ZIP；删全部发布标识甚至命名描述后删计划；默认加PDF到同条或下一条消息，均应拒绝。合法例外放修订目录外，提供当前本项目TEST ONLY请求证据，不替换封套默认计划。

```bash
python3 scripts/prepare_delivery_message.py /ABS/current_named_root
python3 scripts/prepare_delivery_message.py /ABS/current_named_root --plan /ABS/explicit-message-plan.json
```

作者完整实测脚本位于修复项目根：author_publication_R10.py（7项，含原失败/两原R08/四发布）；author_publication_negative_R10.py（19反例及同步重绑）；author_message_cli_R10.py（4公开消息CLI）。这些脚本指向当前真实独立输入目录，未作为通用包运行依赖；重跑需新输出目录，原样读取现存证据即可复核。包内新publication_contract模块和test_publication_contract.py可独立使用。作者自测不等于独立R10通过；工程production_release始终false。
