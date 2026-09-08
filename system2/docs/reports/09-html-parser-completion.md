# HTML 解析器完成报告（2026-09-07）

结论：冻结语料范围内的静态 HTML 解析程序与校验目标完成。版本 `html-dom/2.0.0`，仅在本工作树，尚未回合并保存项目。覆盖 Lovdata、ASC 和三个政府机构页面族；以前模板不支持的实际样本已纳入 v2。

## 验证结果

| 检查 | 结果 |
|---|---|
| 冻结 System1 HTML 快照 | 37 份 |
| 有正文快照 | 30 份通过结构和原始文字校验 |
| 空正文快照 | 7 份正确拒绝 |
| 开发组 | 14 份通过，1 份预声明负对照 |
| 文件留出组 | 16 份通过，6 份失败后独立确认为空正文 |
| 预选原文结构窗口 | 10/10 通过 |
| 非 PDF/公共合同测试 | 75 passed，2 个 PDF 测试 deselected |

表格网格、合并单元格、列表、标题上下文、脚注和链接均有独立核查；文字同时经过 DOM 与标准库原始 token 检查。原文窗口包括 Aceton 数值行、ASC 版本日期、坐标列表、标题和脚注。机器检查不替代人工语义验收。

空正文来源为 PA011、PA012、PA039、PA041、PA042、PA044、PA058。原始 `documentBody` 均为空，独立复查未发现 iframe。保持明确失败，不补造正文、不重新下载、不更改 System1 状态。原留出报告中的 `requires_diagnosis` 原样保留，诊断见 [输入例外证据](html-v2-input-exceptions-20260907.json)。最终复测是在已揭盲样本上的回归，不作为新的盲测成绩。

## 可追溯证据

- [机器完成报告](html-v2-completion-20260907.json)：逐来源分类、产物 hash、最终来源状态。
- [开发组最终报告](../../outputs/runs/html-v2-development-03/validation-summary.json)。
- [留出组最终报告](../../outputs/runs/html-v2-holdout-02/validation-summary.json)。
- [冻结来源](../../tests/fixtures/html/source-manifest-20260907.json) 与 [原文窗口](../../tests/fixtures/html/source-windows-20260907.json)。
- [数据合同](../contracts/html-document-v2.md) 与 [回合并清单](source-intake-handoff.json)。

## 收尾时的上游状态变化

最终两组运行时登记表 hash 为 `b41a03571e60ad799f5f88c74d77d44317514e70df1cdb11fa1c7ec54aa82941`，37 份来源的业务字段已与冻结清单重新核对。收尾时登记表变为 `a59891eb2b709e39b96c148f3bd80fbfa3de5039f6ab29afa622bd4e221472d6`；37 条 `selection_status` 均无法通过接入门。抽查 PA001 公式仍在，但缓存值为 None，人工 INCLUDE 仍在。此任务未写入登记表，不能确定外部修改原因。

37 份源文件 hash 再次检查全部未变，30 对 Canonical/验证文件物理摘要全部匹配，已完成的解析证据有效。当前新接入运行会正确阻断；需由 System1 恢复有效公式缓存和业务状态后再正常入队，不能用历史 manifest 绕过。此上游运行条件不属于解析器代码缺陷。

## 重现与边界

从 System2 独立环境运行：

```sh
PYTHONPATH=src .venv/bin/python -m pytest tests/contracts \
  -k 'not test_pdf_adapter_preserves_pipeline_call_and_artifact and not test_excel_and_pdf_explicit_boundaries' \
  -o addopts='' -q
PYTHONPATH=src .venv/bin/python scripts/validate_html_goal.py \
  --system1 /path/to/system1 --stage development --output outputs/runs/html-new-development
PYTHONPATH=src .venv/bin/python scripts/validate_html_goal.py \
  --system1 /path/to/system1 --stage holdout --output outputs/runs/html-new-holdout
```

复测脚本要求当前登记状态有效且与冻结来源一致；当前缓存缺失会先拒绝。输入例外诊断保存在单独证据文件，原 holdout 脚本遇到六个未预声明负对照会返回非零，不将它们伪装为解析成功。

保留动态筛选条件但不执行，未读取外部资源或图片文字，缺失的弹窗脚注保留待复查。所有机器结果仍需人工复查。PDF 解析/质量验证、Excel 内容解析、Requirement 语义提取和工作台不在本目标内。
