# Excel / HTML 条款映射与来源承接 | 2026-09-07

决策：`CONTINUE`。已完成两类真实模板的只读条款映射、独立映射核查和 System1
现有选择接口承接。当前优先级仍为 Excel/HTML → 系统侧工作台接入 → PDF accuracy pending。

## 条款映射

新增 `source-records/1`：字段文字逐项指向 Canonical 标量及原 cell/DOM locator；
未映射文字保留在 residual，重复编号、缺失字段和公式原文问题显式保留。
该投影只表示源结构，不推断法律效力或 Requirement 语义。Canonical 与
`source-parse-result/1` 不迁移，映射产物通过 companion 索引发现和校验。

- GLOBALG.A.P. 参考 XLSX：257 条 Principle，九列共 2,313 个字段与原工作簿逐项一致。
  正文、Criteria、Level 等与审计回答/Justification/Site 信息分开；2,338 个残余引用
  保留。参考原件 hash 为 `ba3ff6d7f9b5141dc90cb7447c61792c08b1ee82af5705330ffcfca5688077f3`，
  未改变，仍为 local_diagnostic。
- 30 份历史已通过源核查的 HTML Canonical：23 份 Lovdata 生成 1,096 条源条款，
  映射核查全部通过；其余 7 份明确 `not_supported`，完整原文仍在 Canonical/residual。
  这是历史 Canonical 的映射回归，不自动证明最新来源资格。
- PA001 的 §1、§2、§6 另用原 HTML 独立对照编号、标题、正文及脚注，全部一致。
  §34 的 `(Opphevet)` 标题保留，正文为空继续报告问题，没有自行补写效力结论。
- 负对照覆盖删条款、换字段、改字、改定位、正文乱序、漏脚注、漏残余和旧 hash。
  映射 verifier 从 Canonical 重建归属，不调用 mapper；它是投影一致性核查，
  不冒充新的原件独立 evidence。

## 来源审核与接入

用户明确来源管理及相关人工判断已由 System1 完成。原离线入口依赖工作簿缓存，
当前版本曾出现 `selection_status=None`，但 System1 的正式 `read` 接口仍返回有效
选择。该问题不是“没有人工审核”。新 `--system1` 入口调用 System1 自身环境中的
既有 bridge，直接承接 `effective_selection`，绑定配置、registry 和 source revisions。
接口不下载、不运行周期、不写决定、不重复评分。

用户随后要求审核完成后同步 Excel 缓存，已由 System1 保存层修复并完成当前登记簿
缓存同步；原公式与人工历史不变。精确验证及正式同步回执唯一归属
[System1 缓存报告](../../../system1/Code/runtime/formula-cache-20260907/report.md)。

System2 在同步后的正式来源上重跑 PA001、PA002、PA047：共 88 条，原件核查及
映射核查通过，全部保留解析待审状态。读取接口与工作簿缓存生成的当前 HTML
manifest 已逐项一致；未绕过尚未纳入的来源。

## 可复核证据

本轮目录：`outputs/runs/nonpdf-records-20260907/`。

- `raw-source-field-checks.json`：XLSX 全字段和原 HTML 窗口对照。
- `historical-html-summary.json`、`historical-html/`：30 份历史投影及覆盖。
- `current-intake-gate.json`：修复前的缓存缺失失败证据。
- `live-system1/`：缓存未同步前，通过正式接口的三个来源解析。
- `live-after-cache-sync/`：当前登记版本的重新接入、Canonical、源核查和映射产物。
- `final-intake.json`：接口/缓存一致性与当前来源 hash 检查。
- `regression-final.xml`、`completion-summary.json`：完整回归 **509 passed、1 skipped**。
  唯一跳过沿用既有环境边界；既有 Starlette/httpx 弃用提示未影响结果。

## 剩余范围

先检查非 Lovdata 模板的可消费段落/表格字段及章节/附件残余，再收敛待审项、证据、
版本化决定应用和回执。旧 XLS、图像文字、动态 HTML 和通用表头推断仍明确未支持；
7 份空正文仍保留此前来源完整性失败。现有本地工作台负责入口，System2 只负责系统
侧接入，当前尚无正式审查决定联调验收。没有进行新的 PDF 精度实验、Gold 修改、
历史覆盖、提交或推送。
