# Excel / HTML 结构关系与核查修复

日期：2026-09-07。决策 CONTINUE。范围为非 PDF 源结构与独立核查；人工审查入口归现有本地合规工作台，PDF 精度 pending。

## 观察、诊断与修复

第一组 14 个失败用例复现：Excel 共享字符串按固定路径读取，可能取错无关同名部件，缺失/非法 relationship 不阻断；HTML document/table/cell/list 的部分 confidence 和 document issues 不受核查，删除问题会通过；合法 rowspan=0 被当作无效，重叠跨度反而使忠实保留的待审产物核查失败，无效跨度的部分未知字段可被篡改。

修复后 Excel 主解析和独立核查分别按真实关系定位字符串，仅 si 占用索引，保留注释证据；HTML 正确恢复当前行组剩余跨度，按源结构重建表格几何、问题与逐项审查策略。行组范围使用线性扫描，不在大型表格中反复扫描所有后续行。

第二组 4 个失败用例复现 Excel 共享公式主引用缺失/范围越界及合并范围越界/重叠均未提示。新增独立双实现分别从提取单元格与源 XML 检查结构关系；保留源值和 source_xml，只增加可定位问题，不重算或修正原件。

这些为错误检测与合法结构恢复改进，不代表现有真实语料的 Requirement 指标提升。

## 验证

- 初始失败证据：`before.xml` / `before.txt`，14 failed；`before-relations.xml` / `before-relations.txt`，4 failed。
- 定向三组测试 65 passed，新增 18 用例全部通过。完整回归 477 passed、1 skipped，一个既有 Starlette/httpx 弃用提示。
- 最后行组扫描实现调整后 45 项相关测试通过，并重跑 PA047；与本轮前一产物完全相同，耗时见 `group-range-check.json`。
- 当前 37 份有效 HTML，30 核查通过、7 空正文失败；10 个固定文字窗口通过。30 份 Canonical 除版本号外与上轮完全一致。
- GLOBALG.A.P. 参考 XLSX：6 sheets、11,561 cells、1,838 formulas，独立核查通过；最终源结构问题为 0。Canonical 除版本号外与上轮相同，不复算公式。参考源仍 local_diagnostic。
- 原 HTML、Excel 与登记表 hash 检查见 `real-source-comparison.json`，未改写 System1、来源选择、原件、Gold 或历史产物。

所有证据位于 [本轮运行目录](../../outputs/runs/nonpdf-structure-20260907/)。`html/` 保存完整 HTML 重跑；`excel-final/` 是最终真实 Excel；`excel-globalgap/` 是增加公式/合并关系检查前的本轮中间产物。

## 版本、依据与边界

HTML parser `html-dom/2.1.0` / verifier `html-source/2.1.0`；Excel parser `xlsx-ooxml/1.1.0` / verifier `stdlib-ooxml/1.1.0`。Canonical schema 保持 html-document/2 与 excel-document/1，历史产物不迁移。

行组跨度依据 [HTML Standard](https://html.spec.whatwg.org/multipage/tables.html#attr-tdth-rowspan)。共享字符串的 workbook part 关系依据 [Microsoft OOXML Fundamentals](https://download.microsoft.com/download/e/1/4/e14fb96f-83b8-4a2a-84db-7fa8acbe061a/Office%20Open%20XML%20Part%201%20-%20Fundamentals.pdf) 与 [Microsoft SpreadsheetML 结构说明](https://learn.microsoft.com/en-us/office/open-xml/spreadsheet/structure-of-a-spreadsheetml-document)。

仍未完成旧 XLS、图像文字、通用业务表头推断、Requirement 字段映射和工作台正式决定接入。通过源结构核查仍为 review_required；不据此声明业务、语义或发布验收。
