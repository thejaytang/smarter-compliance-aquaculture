# Excel / HTML 内容映射收尾 | 2026-09-07

决策：`CONTINUE`。用户本轮指定先推进 Excel/HTML。当前五类 HTML 模板的原文内容
映射与 GLOBALG.A.P. 参考 XLSX 验收已完成；7 个 INCLUDE 来源的全文获取仍需要
上游修复。本轮未扩大至非 INCLUDE 来源、工作台决定接口或 PDF 精度实验。

## 实现与真实原件验证

新增 [source-records/2](../contracts/source-records-v2.md)，覆盖 ASC 原字段、政府指南
段落/标题、章节外文字和 Lovdata 附件表格。保留 v1 模型和显式入口，Canonical
未迁移，旧条款 ID 与字段未变。结构引用回溯 Canonical 的 DOM、表格、单元格、
列表及链接；图像和未解析脚注保持问题，全部结果仍为 `review_required`。

当前 System1 INCLUDE 的 37 份 HTML 通过正式只读 bridge 显式重跑：30 份有正文
的源核查与映射核查通过，7 份空正文失败，批次准确返回 `completed_with_issues`。

- 7 份此前未支持的非 Lovdata 投影现已生成内容记录：CS001、CS002、PA024、PA025、
  PA026、PA027、PA043。ASC CS001 的 454 条 Indicator 包括 14 条附录替代布局，
  1,362 个原字段与原 HTML 的独立 lxml 选择结果逐项一致。
- 36 条源 `not in use` 标记保留；13 条附录没有独立声明 applicability，明确 missing，
  没有从 CSS 过滤条件猜测适用范围。已有 1,096 条 Lovdata clause 的 ID/字段/问题与 v1 一致。
- 30 份 HTML 共 8,352 个 table cell 记录；PA047 的附件等剩余内容新增 5,438 个 cell
  记录，其 residual 从 6,328 降至 126，剩余为源元数据或控件。空格、空单元格和
  嵌套几何继续保存在 Canonical 及其结构引用中。
- 独立原件逐项核对 86,252 个映射文字引用，零差异；10 个此前冻结的源窗口通过。
  所有 30 份 HTML 的非空内容文字均已映射，剩余 1,009 个元数据引用和 2,732 个
  控件/导航引用明确保留。这不代表图像已转录或法律语义已接受。
- GLOBALG.A.P. 参考 XLSX 重新解析及源核查通过。257 条、2,313 个原字段与原工作簿
  一致，与 v1 字段一致；源 SHA-256 为
  `ba3ff6d7f9b5141dc90cb7447c61792c08b1ee82af5705330ffcfca5688077f3`，原件未变。
  仍标为 `local_diagnostic / production_eligible=false`。

## 7 个空正文的根因

PA011、PA012、PA039、PA041、PA042、PA044、PA058 均为 INCLUDE。逐个检查保存的
原 HTML，正文都是 `<div id="documentBody"></div>`；页面保存了元数据和目录，
并另有 `Vis hele dokumentet` 全文链接，指向原文档路径后加 `/*`。文件 hash 与登记
一致。失败来自抓取到目录页，不能由解析器从空容器恢复条文。

原件提供的明确修复方向：System1 保持 `official_url` 来源身份，使用已知全文链接
获取这些 INCLUDE 来源的完整快照，走其受控版本保存，再交 System2 重跑。无需
重新评分或判断来源资格。本轮没有下载、改写来源 URL、替换快照或创建上游人工待办；
全文入口的实际网络返回尚未验证。

## INCLUDE 范围

用户再次明确只处理 INCLUDE 来源。非 INCLUDE 项目的接入拒绝是边界检查，不是本轮
解析失败或新增业务待办。当前没有有效 INCLUDE 的 XLSX；不要求补齐未纳入的 Excel，
不将其列入本轮完成条件。本地参考 Excel 只提供现有模板工程证据。

## 验证和证据

证据目录：`outputs/runs/nonpdf-content-20260907/`。

- `live-html/`：37 个明确 ID 的正式 bridge 批处理、源 hash、Canonical、核查与投影。
- `excel/`：参考原件的新一轮只读解析、独立源核查和 v2 映射。
- `raw-source-acceptance.json`：独立原文字段对照、十个窗口、残余类型及 v1 一致性，passed。
- `empty-body-diagnosis.json`：七个实际空容器、原文件 hash 及页内全文链接。
- `regression.xml`：完整 System2 回归 **529 passed、1 skipped**，无失败；20 个新增
  用例覆盖字段、条件显示、附录布局、嵌套表格、图片/空链接、遗漏、乱序和错误引用。

原件验收可通过 `scripts/validate_source_content.py` 重放；它只读当前 bridge、快照
和指定历史结果，使用新输出文件，不下载或写入 System1。System1 在本轮期间有其他
任务更新登记簿布局；各运行保留自己的 registry hash，原快照 hash 和已纳入范围须
在最终交接时重新核对，不覆盖历史凭证。

## 下一步

本次内容映射实现完成。INCLUDE 全文获取问题继续显式保留；工作台队列、证据读取、
版本化决定应用与回执仍是下一阶段。PDF accuracy 继续 pending。旧 XLS、未知模板、
动态页面和图像文字不冒充已支持，也不因非 INCLUDE 来源产生额外工作。
