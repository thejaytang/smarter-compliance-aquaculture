# 非 PDF 优先级调整与 XLSX 实施记录

日期：2026-09-07。用户要求 PDF 精度 pending，先 Excel/HTML，后 human in the loop，最后共同改善 PDF。决策 ADJUST。

## 实现与核查

新增 `contracts/excel.py`、`formats/excel.py`、`verification/excel.py`、发布 schema 与专项测试，既有 source_batch 支持 XLSX Canonical 和 verification 产物。lxml 提取与 ElementTree 独立校验分离。主值保留源词法，不计算、不访问外链、不重写工作簿；XLS 和超出范围的输入明确拒绝或未实现。

测试覆盖稀疏单元格、隐藏页行列、合并、公式缓存缺失/存在/空字符串、共享字符串/富文本、shared formula、错误值、批注、表格头部件、来源 hash、删除/重排/改写/隐藏审查问题与失败传播。VML 实测暴露源 XML 未被归入 XML 清单，已修正为结构证据保留。

## 真实证据

- 当前有效 HTML 37 份，30 份通过 DOM 与原始文字核查，7 份 source `documentBody` 空而失败；既有 10 个原文窗口全部通过。失败来源为 PA011/PA012/PA039/PA041/PA042/PA044/PA058；其他 26 个不合格来源未处理。
- 参考工作簿：项目 `03_GLOBALGAP_Standards/IFA v6 Smart _ AQ_en_20240827 - Prefilled_00.xlsx`，SHA-256 `ba3ff6d7f9b5141dc90cb7447c61792c08b1ee82af5705330ffcfca5688077f3`。
- 6 sheets、11,561 cells、8 merges、1,838 formulas，独立核查通过。逐格 openpyxl 检查 2,556 文本、1,586 显式公式、252 共享公式从属格通过。最初直接比较共享从属格公式文本失败，诊断为源文件仅存空 f/si 而 openpyxl 展开相对引用；独立 anchor translation 对 252 格全部一致，无需改写原公式。
- OfficeCLI 只读 outline 与 `CL - IFA v6 Smart - AQ/A1:F8` 原文窗口核对。没有编辑或交付新的生产工作簿，因此没有 Excel 原生视觉验收声明。

## 产物与结果

运行目录为 [本轮证据](../../outputs/runs/nonpdf-priority-20260907/)。`html/` 保存每项 result/Canonical/verification；`html-window-checks.json` 保存文字窗口；`excel-globalgap-final/` 保存最终真实 Excel Canonical、verification、source-comparison 和 OfficeCLI 窗口；`excel-globalgap/` 保留 VML 修正前产物；`excel-synthetic/` 是合成工程样本。

完整最终回归 `regression-completed.xml`：459 passed、1 skipped；一个既有 Starlette/httpx 弃用提示。输入 hash 不变；未运行 PDF 精度实验、下载、外部模型、Full Source Check、工作台写入或发布。

## 完成边界

这是 XLSX 结构实现和当前 HTML 源核查的工程 checkpoint。旧 XLS、图片文字、通用业务表头推断、Requirement 语义消费映射和人工审查闭环没有完成。所有机器结构继续待审。该 Excel 使用 local_diagnostic 来源模型明确不具备生产接入资格，未伪造 System1 选择记录。下一步继续非 PDF 结构到条款消费字段映射与真实验收，再共同设计人工审查。
