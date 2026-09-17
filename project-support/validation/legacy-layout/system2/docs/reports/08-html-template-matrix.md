# System1 现有 HTML 多模板实测

日期：2026-09-07。本轮读取 System1 当前登记表和显式选择的本地快照，不下载、不扫描历史、不修改来源选择或原件，不运行 PDF、Excel 内容解析或外部模型。

结论：当前 HTML 解析器只覆盖特定 Lovdata 模板。12 份有效 HTML 中，4 份生成待复查结构，7 份模板不支持，1 份正文区域为空。另 1 条 PENDING 来源在读取原件前被正确拦截。这不是全文解析成功率或准确率统计。

## 样本选择和结果

按来源机构、法规/指南/标准、页面体量、正文/附件/表格结构选择，不做随机代表性推断。登记快照版本、hash、主区域文字/表格计数及具体检查见 [机器可读结果](html-template-matrix-20260907.json)。

| 类型 | 来源 | 结果 | 实际发现 |
| --- | --- | --- | --- |
| Lovdata 分区法规及附件 | PA002 | 待复查，20 条款 | 有 173 个未表示文字定位提示，含章节注释及附件内容 |
| Lovdata 动物福利法 | PA005 | 待复查，43 条款 | 当前提示为 0，仍不构成独立完整性验收 |
| Lovdata 海虱防治法规 | PA015 | 待复查，16 条款 | 1 个无 `<p>` 条款、23 个未表示文字定位提示 |
| Lovdata 限值与表格密集法规 | PA047 | 待复查，26 条款 | DOM 内 124 个表格元素，6,018 个未表示文字定位提示；现有 Canonical 无显式 table 节点 |
| Fiskeridirektoratet 指南 | PA024、PA025 | 模板不支持 | NYTEK23、风险管理指南在快照内有实质文本，需专用正文/层级规则 |
| Miljødirektoratet 指南 | PA026 | 模板不支持 | 快照有养殖管理指导文本，页面结构不同于 Lovdata |
| Mattilsynet 指南/主题页 | PA027、PA043 | 模板不支持 | 主题导航页和生物安全指南应分别处理，不能把导航链接直接当 Requirement |
| ASC 标准与解释手册 | CS001、CS002 | 模板不支持 | 主区域分别有 48、28 个表格元素以及实质正文；不能简单归为无内容落地页 |
| Lovdata 动物健康法规 | PA039 | `html_empty_result` | 实际 `#documentBody` 为 `<div id="documentBody"></div>`，没有 iframe；页面其余位置存在目录，不能用目录冒充正文 |
| 待选择的 EU 法规 | PA010 | 清单拒绝，未解析 | `operator_selection_decision` 与 `selection_status` 不满足 INCLUDE |

表格计数是 DOM 元素计数，包含列表/脚注等布局表格，不是规范语义表格数量。复查提示计数是 DOM 定位数，含同一内容的不同内联位置，不是要求条数或独立审查任务数。

4 份支持模板的文件共 105 条款。对每个节点核查了唯一 DOM 定位、父节点存在、来源绑定、未校准 confidence 和 review policy；105 条款的 `visible_text` 均可回到对应 DOM。其他 8 份没有生成空的“成功” Canonical。所有输出仍为机器产物，未做独立语义完整性验收。

## 真实样本触发的性能修复

PA047 暴露反复查找章节标题的耗时问题：完整性扫描对每个未覆盖文字节点重新调用 `chapter_heading`，每次遍历该章节子树。现在每章节只建立一次已提取标题集合，扫描时按祖先身份查集合。

parser 从 `lovdata-html/0.1.1` 升至 `lovdata-html/0.1.2`。PA047 原运行约 43.509 秒，优化后用单调计时实测为 1.768 秒。原时间来自新输出目录创建时间至 result 文件写入时间，属于近似单机观测，不是严格基准或普遍性能承诺。

对 PA002、PA005、PA015、PA047 各重新运行一次并比较完整 Canonical，**除 parser_version 外完全相等**，包括所有原复查提示。没有通过减少检查或隐藏提示提升速度。优化后的计时和相等性证据见 [性能对照](html-matrix-performance-20260907.json)。

回归测试：`48 passed, 2 deselected`。使用上一轮非 PDF/公共合同测试命令，排除直接调用 PDF adapter 的测试。本轮没有改动 PDF adapter 或配置，没有增删任何模型依赖。

## 下一步判断

1. **先完善已支持的 Lovdata 结构。** 用 PA047 表格区域、PA002 附件列表和章节修订说明建立小窗口结构合同。当前只是将遗漏显式标记，尚未完成结构恢复；不得只根据条款数量判断完成。
2. **新增 ASC 专用模板。** 从 CS001/CS002 已有快照中选少量章节，保留原 ID、标题层级、表格、脚注及筛选条件的原始关系；不得运行页面脚本或假定所有 DOM 内容在每种筛选下同时适用。
3. **政府指南分来源模板接入。** 区分有正文的指南与导航型 hub，沿用 System1 的来源角色，不把网页链接解释成规范要求。
4. **PA039 回到来源完整性复查。** 当前已存储且选定不代表正文完整；应由 System1 后续复查该快照。此次未修改工作簿、重新获取文件或替换当前快照，不能通过宽松解析吞掉该错误。

## 复现与产物

输入清单及原 parser 运行：`outputs/runs/html-template-matrix-20260907/`。
优化后的四份结果：`outputs/runs/html-template-matrix-20260907-optimized/`。
复核工具：`scripts/audit_html_matrix.py`，读取已完成批次，仅对 manifest 内显式来源做检查。该工具中的页面族分类仅用于本测试报告，不是已实现的生产模板路由。

```sh
PYTHONPATH=src .venv/bin/python scripts/audit_html_matrix.py \
  --system1 /path/to/system1 \
  --run outputs/runs/html-template-matrix-20260907 \
  --report /path/to/new-report.json
```

源码、报告和状态只在本工作树更新；保存项目未更新。对应精确差异纳入 [回合并清单](source-intake-handoff.json)。既有输出和前轮报告保留，未 commit/push 或启用自动化。
