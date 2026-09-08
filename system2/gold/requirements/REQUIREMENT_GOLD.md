# Requirement Gold v2 / v3

该目录是 Requirement-first 解析的独立验收真相源。它不从当前 parser 输出反向生成，也不评价 Markdown 是否“看起来正确”，而是逐页记录来源文件中完整的规范单元及其证据。

## 核心约定

- `schema-v2.json` 保留历史 Gold 契约；`schema-v3.json` 在相同 Requirement 结构上增加不可变 revision metadata。
- `manifest.json` 固定 active sample 与 frozen holdout。
- `annotations/` 保存人工核对后的样本标注。
- `sample-history.json` 是不可逆样本状态 registry；holdout 一经评分差异揭盲或参与诊断，永久转为 active，不能再次计入 untouched holdout。
- PDF 页码 `page_number` 为读者看到的 1-based 页码，`page_index` 为程序使用的 0-based 索引。
- `bbox` 使用 PDF points、左上角原点，顺序为 `x0, y0, x1, y1`。
- `normative_text` 只保留来源中表达规范内容的原文，不把 guidance、rationale、client action 或 auditor action 拼入其中。
- legacy 两列表格中的完整 direct core 由 `indicator_text + "\n" + requirement_value` 按来源阅读顺序组成。`Yes`、`None` 或数值不得丢弃，也不得添加来源中不存在的 `Indicator:` / `Requirement:` 标签。
- `source_segment_ids` 明确指向构成 Requirement 的页面证据。跨页 Requirement 必须有多个有序 segment。
- direct Requirement、related context、client action 和 auditor action 使用互斥 provenance bucket；不能用 Criterion heading 或 action 段伪造 formal evidence。
- `client_actions` 与 `auditor_actions` 是独立关联字段，不属于 `normative_text`。
- `clauses[].joins_next` 显式保留 `and/or`，不能仅靠 Markdown 列表顺序推断。
- 自动修复不能修改 Gold。Gold 发现错误或契约升级时必须创建新 revision，记录 predecessor path、predecessor SHA256 和 revision reason；历史 annotation 与 manifest 不得原位覆盖。

## 冻结流程

1. 选取不超过约 12 页的风险窗口。
2. 对照 PDF 可见页面和 native text 双重核对。
3. 写入 annotation，运行 schema 与引用完整性检查。
4. 将 `annotation.status` 设为 `frozen`，再运行或修改 parser。
5. active sample 可用于诊断和修复；holdout 只用于验证，不参与规则设计。
6. 首次盲测后立即在 `sample-history.json` 记录 `first_scored_round`；一旦查看差异，状态永久改为 `active_regression`。

Manifest gate 会核对 round、样本页、Gold revision、PDF 文件名和 SHA256；prediction 还必须绑定相同 `document_id`。新 manifest 可对单个 item 指定 `schema`，因此 v2 历史 Gold 与 v3 revision 可以共同回归。matched 数为 0 时，matched-only accuracy 必须为 `null`，不能用空分母得到 `1.0`。

`accepted_id_*` 只说明编号命中；完成门使用 `accepted_result_*`。只有唯一 identity、direct text、所有关键语义字段、actions 和 page/segment/bbox provenance 同时正确，才计为一个完整 accepted result。当前轮次、已揭盲样本和下一实验以 `sample-history.json` 与 `docs/reports/04-requirement-convergence-ledger.md` 为准。
