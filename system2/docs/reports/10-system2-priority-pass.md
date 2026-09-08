# System2 按优先级完善：第一轮工程与真实样本验证

日期：2026-09-07。决策：`ADJUST`，整个 System2 尚未完成。
计划见 [优先级与完成门](../plans/03-system2-completion.md)，机器证据见
[本轮结果](system2-priority-20260907.json)。所有新运行位于 `outputs/runs/system2-priority-20260907/`。

## 本轮修复

- reject/unreadable 保留源忠实度待办，block/span/cell 均有负对照。文字确认不关闭结构问题，重复或重叠 span token 不猜测位置；明确确认更新关联文字冲突。
- 修改源文字后，已有 Requirement 保守进入语义重核。状态聚合保留失败、页面问题和未解决证据；导出不再把 failed 提升为 accepted。
- 第二路原生证据发现 critical mismatch 后清空 resolved_text，保留原生文字和两路候选，修复真实表格的自相矛盾状态。
- PDF batch 索引保留 Canonical schema、核查报告和 hash，传播失败及缺失核查。
- guarded 审查入口提供版本绑定、请求重放、锁、旧 Canonical 备份、独立版本产物和原子发布。旧接口保留兼容，不宣称同等保障。
- System2 自带审查页使用新入口和具名操作；修正稀疏页码与非文字容器目标，避免将源字符串作为 HTML 插入。
- 恢复锁定的 docling-parse 7.15.0，增加显式本地坐标配置，不下载模型。旧 pypdf 配置保留。
- 保留 In cases where 完整条件并绑定同句后续动作；在明确句界和义务动词支持下拆分条件句；保留完整豁免句标点与 Appendix 复合引用。

## 测试和浏览器

初始两个跨目录 CLI 测试失败来自相对 PYTHONPATH 被子进程重新解释，已修复测试环境。七个新增负对照先复现假通过，再修复。最终回归：**439 passed、1 skipped**，另有现有 Starlette/httpx 弃用提示。JUnit 位于新运行根的 `regression.xml`。

事务测试覆盖 stale revision/hash/source、重放、同 ID 不同内容、锁、发布/导出失败及跨后续版本重放。浏览器仅使用合成数据：page_index 79 显示 Page 80 与红框；Unreadable 后 revision 1 仍 review_required；明确纠正后 revision 2 回读新文字，同时保留原文。这不是正式来源的人工验收。

## PDF 实测

Interpretation Manual 80–82 页使用同一已揭盲 Gold v4 revision 2，每次输出单独保存：

| 配置/修复 | ID 恢复 | 正文 exact | 关键字段 exact | 严格结果 |
| --- | --- | --- | --- | --- |
| pypdf 低成本路线 | 1/3 | 0% | 33.33%（仅匹配项） | 0/3 |
| PDFium | 3/3 | 33.33% | 62.96% | 0/3 |
| 恢复 docling-parse | 3/3 | 100% | 85.19% | 0/3 |
| 条件与句界修复 | 3/3 | 100% | 92.59% | 0/3 |
| 完整豁免句与复合引用修复 | 3/3 | 100% | 100% | 0/3 |

最终 page/segment/bbox、非空关键字段、动作分离均为 100%，Canonical validation 为 0 errors。源页图已检查。
机器结果 accepted，但 strict 整体仍为 0/3：shared context 尚未表达、脚注在 associated_instructions 的归属和 Indicator 引用 text/target 表示仍不一致。不能作为发布验收。
始终按 active diagnostic 评价，未修改 Gold 或历史首次盲测。

Audit Manual 17–18 页新运行的 13 条 Requirement 与历史 active22 对象完全一致。当前 evaluator 对新旧均为 12/13 strict exact、关键字段 100%。不沿用历史 13/13 声明；既有 5.1.6 strict 差异待追溯。证据为 `audit-regression-comparison.json`。

## HTML 与来源

只读登记表检查：PA001 当前有效；CS003、CS005、PA057 的人工/有效选择不满足 INCLUDE，正确拒绝，未绕过选择门。
PA001 新运行包含 1,045 nodes、632 atoms，DOM 与独立原始文字核查通过，产物 hash 一致，保留 review_required。
运行后核对所用两个 PDF 与 PA001 HTML 原件 hash 一致。System1 工作簿未写入。

## 后续

先完成 P1/P2 剩余合同：统一工作台操作人绑定、旧写入口迁移策略，以及 shared context、footnote instruction、reference identity。随后是 HTML Requirement 接口、完整结构审查、Excel 和模块收敛。
当前未选择来源、Norwegian 文档外验证与消费方接受仍需各自证据。
本轮未修改 Gold、原始 PDF、历史 baseline、System1 数据或统一工作台，未提交、推送、外部文档发送或全量解析。
