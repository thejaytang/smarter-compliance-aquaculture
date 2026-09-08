# 非 PDF 模块专项测试与调整

日期：2026-09-07。范围仅本工作树 System2 的 HTML、Excel 格式识别/未实现出口、登记清单、批处理和 JSON 写出。未运行 PDF 解析或真实 PDF 质量验证，未修改 PDF adapter 或既有 PDF 解析算法。没有运行 System1 生产周期。

结论：需要调整。本轮用失败测试复现并修复 9 个缺陷；Excel 内容解析与 HTML 未覆盖结构仍是明确的功能缺口。

## 复现与修复

初始 10 个追加测试中 8 failed、2 passed。随后独立复现 1 个批处理失败回执缺失问题。

| 模块 | 观察到的错误 | 已完成调整 |
| --- | --- | --- |
| HTML 完整性提示 | 章节内但不属于条款/已提取标题的文字被视为已覆盖 | 标记 `unrepresented_body_text`，保留具体 DOM 定位 |
| HTML 章节 | 父章节无标题时错误借用子章节标题 | 标题限定为当前章节自己的标题 |
| HTML 配置 | 使用自定义 metadata 选择器后元数据仍按写死的旧 ID 提取 | 从实际匹配的 metadata 元素解析 |
| HTML 嵌套条款 | 子条款正文、列表、引用和脚注被父条款重复吸收 | 各条款独立拥有数据，节点保留真实父子归属 |
| HTML 嵌套列表 | 外层列表文本重复包含内层列表文本 | 分离当前表格单元格和嵌套列表内容 |
| Excel 格式识别 | `.xlsx` 文件登记为 `xls` 仍放行 | 区分 XLS 与 XLSX，不因同属 Excel 就视为格式一致 |
| JSON 写出 | 序列化失败留下半截结果文件 | 先序列化，再写临时文件并独占发布；失败清理临时文件，不覆盖既有结果 |
| 批处理启动 | 从其他目录启动时强制寻找相对 HTML 配置，Excel-only 批次也失败 | 默认配置不依赖当前目录；只有显式配置路径才读取对应文件 |
| 批处理失败 | 登记表读取失败只抛异常，没有批次回执 | 在可写的新输出目录中写 `status=failed` 的 batch 回执并返回非零退出码 |

HTML parser version 从 `lovdata-html/0.1.0` 升至 `lovdata-html/0.1.1`。公共结果仍保持原 schema，旧字段名未改动。列表文本保留原有空白规范，避免为修复嵌套结构引入标点前空格。

## 回归验证

命令（从 System2 目录）：

```sh
PYTHONPATH=src .venv/bin/python -m pytest tests/contracts \
  -k 'not test_pdf_adapter_preserves_pipeline_call_and_artifact and not test_excel_and_pdf_explicit_boundaries' \
  -o addopts='' -q
```

结果：**48 passed, 2 deselected**。覆盖 HTML 缺陷复现、真实生成的 XLSX 容器与公式文件只读保护、Excel 未实现状态、路径与 hash、重复/缺失来源、格式签名、schema、JSON 序列化/发布失败及不同工作目录下的 CLI。公共合同测试不调用 PDF 解析；两项直接涉及 PDF adapter 的测试未运行。此数值不可与上一轮 78 项跨模块测试直接作增减比较，测试集合不同。

## 真实 HTML 对照

仅从正式登记表显式选取 PA001、PA002、PA003、PA004、CS001，没有扫描其他历史文件。原件仍只读。

| 来源 | 条款数 | 原脚本字段差异 | DOM 文字定位检查 | 复查提示数 |
| --- | ---: | ---: | ---: | ---: |
| PA001-001 | 42 | 0 | 42/42 | 5 |
| PA002-001 | 20 | 0 | 20/20 | 173 |
| PA003-001 | 91 | 0 | 91/91 | 12 |
| PA004-001 | 50 | 0 | 50/50 | 0 |
| CS001-001 | 不适用 | 模板不匹配 | 不生成 Canonical | 明确失败 |

合计 203 条款。详细来源 hash、对照差异、定位和提示见 [真实来源对照](nonpdf-source-comparison-20260907.json)。复查提示是 DOM 位置数量，不是独立 Requirement 数量；同一注释可能有多个位置。零差异仅证明受支持字段的行为兼容，不能证明全文结构完整。

现场检查发现 PA001 的章节修订注释、PA002 附件中的地理边界坐标列表等内容尚未进入专门结构字段。新增提示已揭示这些缺口，但尚未恢复章节脚注、附件表格/列表的完整结构。旧 `visible_text` 保留原 DOM 文字，只用于原文核查，不是已净化的要求文本。

本轮运行保留于 `outputs/runs/nonpdf-regression-20260907`（中间诊断）和 `outputs/runs/nonpdf-regression-20260907-v2`（最终对照）。CS001 作为预期负对照使 CLI 返回 1，批次为 `completed_with_issues`，不影响其余四份产物。原脚本对照报告使用独占创建，避免覆盖历史证据。

## 仍需开发的范围和建议顺序

1. HTML：下一步先处理章节修订说明及附件表格/列表的归属、类型和定位，沿用本轮已发现的真实窗口。当前已经从静默遗漏改为显式复查，但还不能称为全文结构解析完成。
2. Excel：当前只识别 XLS/XLSX 并返回 `not_implemented`。它还没有 sheet/cell、合并单元格、表头、公式表达式/缓存值的内容解析功能，不能当作已完成解析器。
3. HTML Requirement 提取与字段审查仍未实现；本轮不把法规结构解析等同于 Requirement 语义提取，也不开发统一工作台。

## 交付与保护

本轮变更集中于 `formats/html.py`、`formats/html_rules.py`、`formats/router.py`、`orchestration/source_batch.py`、非 PDF 回归测试及来源对照脚本；状态与合同已同步。见更新后的 [回合并清单](source-intake-handoff.json)。保存项目及其正式工作簿/原件未写入，PDF 文件未解析；没有 commit/push、外部调用或自动化。
