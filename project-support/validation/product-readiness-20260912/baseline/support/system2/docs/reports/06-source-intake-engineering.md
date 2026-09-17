# System2 本地来源接入实施与验收记录

日期：2026-09-07。结论：最小 HTML 接入闭环与 PDF adapter 合同已完成；结果仅在独立工作树，保存项目尚未更新。

## 实现范围

从保存项目导入 198 个根合同与 System2 工程文件，逐文件原始 hash 见 [导入记录](worktree-import-20260907.json)。环境、缓存、原 PDF、Gold、历史输出及运行状态未复制。保存项目仅只读访问，本轮未删除原 `Parser v1.py.txt`。

新增模块分工：`intake/registry.py` 读取与有效性检查；`formats/router.py` 按后缀核对签名；`formats/html_rules.py` 为原脚本纯规则；`formats/html.py` 处理文档结构/定位；`formats/pdf.py` 包装既有入口；`formats/excel.py` 明确未实现；`orchestration/source_batch.py` 管理清单、逐项输出及失败传播；合同和 JSON schema 分别在 `contracts/source.py`、`config/schemas/`。

环境由本工作树 `.venv` 拥有，`pyproject.toml` 和 `uv.lock` 声明 BeautifulSoup、lxml、openpyxl；原 PDF 基础依赖和公共 API 保留。未安装 PDF optional 模型或扩大运行任务。

## 验证证据

| 检查 | 结果 | 证据与界限 |
| --- | --- | --- |
| 本地定向回归 | 78 passed | `tests/contracts`、`tests/unit/test_models_and_validation.py`、`tests/integration/test_text_layout_and_export.py` |
| PA001-001 HTML | 42 条款，8 章节 | 原脚本字段零差异；42/42 DOM 文字检查 |
| PA002-001 HTML | 20 条款，19 章节 | 原脚本字段零差异；20/20 DOM 文字检查 |
| CS001-001 负对照 | 显式 template mismatch | 未产生 Canonical，不伪装空成功 |
| CS003-001 PDF | 30 页文件只处理 index 0 | 1 页原生 Canonical、5 Requirement、2 review items、0 schema errors；仅 adapter 验收 |
| 原件保护 | 通过 | 已处理 HTML/PDF 原件 hash 仍与 manifest 一致；工作簿 hash 固定记录在产物中 |

HTML 具体结果见 [原脚本/DOM 对照](html-source-comparison-20260907.json)。对照脚本为 `scripts/verify_source_intake.py`，它仅在内存运行已检查的旧纯解析行为，未运行其目录批处理入口。旧脚本行为相同证明兼容性，不是独立语义正确性证明。

PA001 的 `PARAGRAF_34` 在源 DOM 中为 `§ 34. (Opphevet)`，无 `<p>` 正文；新结果保留该节点与 DOM 文字并标记复查。`visible_text` 保留 DOM 中的可见控件文字，不能当成已净化的法规正文。章节/条款之外和复杂嵌套结构仍需专门完整性验证，全部 HTML 节点保持 `confidence=null` 和 `review_required`。

PDF 证据见 [单页 adapter 报告](pdf-adapter-window-20260907.json)。已查看原页渲染并对照 Markdown：原页为多列表格，而轻量配置的 Markdown 存在 client/auditor 列混排。`pdftotext` 独立核查进程发生 SIGABRT，原质量报告保留 fallback reason。因此不能以 schema-valid、5 条 Requirement 或自动覆盖率推断 source fidelity。该故障属于后续本机核查后端诊断，本轮不修改原 PDF 算法。

真实运行产物位于本工作树 `outputs/runs/intake-html-20260907` 与 `outputs/runs/intake-pdf-20260907`，不纳入源码回合并；保留上述精简证据。没有运行大型 PDF 全量、Full Source Check、外部模型、工作台服务或自动化；没有 commit/push。

## 回合并清单与操作边界

机器可读清单：[source-intake-handoff.json](source-intake-handoff.json)。`added` 是新增文件；`modified` 是相对导入基线修改的现有文件，含源基线 hash 和工作树 hash。先核对保存项目的当前文件仍等于基线再应用差异；若不同则人工/文本合并。不要整个复制 198 个导入文件覆盖保存项目。

仅将清单内 System2 新增/修改内容合并；根 `AGENTS.md` 的变更仅为本次 HTML/Excel 范围文字，应单独审阅同步，不能覆盖原任务新的根合同。根 README/PROJECT_STATE 是只读导入快照，不应回写。此工作树 System2 状态的新 checkpoint 应作为段落合入保存项目最新状态，不替换全部历史文件。

当前架构仍有边界：统一的是 source/result 索引，HTML 与 PDF 内容 schema 尚未完全统一；HTML Requirement、Excel 解析、字段级审查/决定、完整性补录、拆分合并和工作台 UI 均未实现。下一步按 [近期计划](../plans/02-source-intake-engineering.md) 验证实际结构缺口。
