# Requirement Convergence Ledger

本文件只记录会影响下一轮决策的证据、诊断和验收结果，不记录逐条操作。

## Round 1：跨结构 baseline

### 假设

当前 parser 对 Requirement 的主要问题可能是页面布局错误，也可能是 Requirement 数据模型和抽取边界不足。本轮在修改 parser 前，用四种结构族的 9 个页面冻结 Gold，并区分这两类解释。

### 样本与 Gold

| 样本 | 分工 | 页面 | Gold Requirements | 关键结构 |
|---|---|---:|---:|---|
| Farm Standard | active | 28–29 | 6 | `Indicators:` 单栏、ID 与规范正文分 band |
| Interpretation Manual | active | 19–21 | 3 | ID/Requirement 两列、长列表、跨页 continuation、guidance 隔离 |
| Audit Manual | active | 1–3 | 12 | Requirement metadata、client actions、CAB actions 三语义区 |
| Salmon/Cod Standard | baseline holdout | 18 | 4 | Indicator 长文本加右侧短值 `Yes` |

合计 25 个 Requirement。全部 annotation 已冻结并通过 JSON Schema、segment reference、bbox、provenance bucket 和 summary count 校验。

Salmon/Cod 第 18 页在 baseline 运行时未参与旧 parser 规则，但其失败现已用于下一轮架构诊断，因此不能再作为 Round 2 的 untouched holdout。下一轮必须另行冻结未查看窗口。

### 可信 baseline

结果文件：`outputs/runs/goal04-round1/requirement-baseline.json`

Evaluator 已修复空分母虚高：matched 为 0 时，matched-only accuracy 记为 `null`，并额外报告以全部 Gold 为分母的 end-to-end recall。总体采用 count-based micro 指标，macro 仅用于诊断。

| 指标 | Round 1 |
|---|---:|
| Requirement recall | 12.0% |
| Requirement precision | 7.32% |
| Accepted Requirement recall | 12.0% |
| Accepted Requirement precision | 7.32% |
| Formal inventory recall | 12.0% |
| Critical-field recall | 8.0% |
| Critical non-empty field recall | 0.0% |
| Exact native segment recall | 0.0% |
| Exact bbox provenance recall | 0.0% |
| Action separation recall | 0.0% |

逐文档结果：

- Farm：`0/6`，6 条规范句均被抽成无 ID modal statement，6 个 Gold ID 静默遗漏。
- Interpretation：`3/3` ID 命中，但另有 5 条 guidance modal false positives，precision 为 `37.5%`；旧 IR 无法证明 exact normative text、bbox 和完整关键字段。
- Audit：`0/12`，产生 26 条无 ID modal statements；Requirement、instruction、client action 和 CAB action 没有形成独立语义区。
- Salmon/Cod：`0/4`，右侧 `Yes` 因无 modal 全部被丢弃，另将 Rationale 中的 `must` 误识别为 formal statement。

### Diagnosis

原生文字证据并未丢失。四个样本的 raw native words/lines 均保留了 ID、正文、短值、applicability 和动作列，问题集中在结构建模与组装：

1. Canonical `Document` 没有 Requirement-level 真相层，旧 `RegulatoryStatement` 无法表达 Indicator 加短值、多个 modality/threshold、scope、logic、actions 和 field provenance。
2. 全文 profile 只识别精确 `Indicator:` 加 `Requirement:` 的 Interpretation 模板；其余三类 profile 为 `null`。
3. 旧 extractor 假设 semantic header 必须是 table row 0，且右列必须含 modal。装饰空行和 `Yes`/数值短值因此造成全漏。
4. 对所有 paragraph/list 做 modal 扫描，把 guidance、rationale、instruction 和 actions 当成 formal Requirement。
5. Farm 与 Audit 的 canonical layout blocks 不可靠，但 native geometry 足以稳定恢复列 band 和 row ownership；继续只修 Markdown/table appearance 不能解决 Requirement recall。

对应 error taxonomy：1、2、4、5、6、7、8、9、10、11、13。当前没有 Norwegian 样本，类别 12 未验证。

### Checkpoint

`ADJUST`

方向成立：保留 native-first 和 document-level learning，但 Requirement 抽取必须从“modal statement on layout blocks”调整为“template-bounded Requirement assembly on native evidence”。不需要 PIVOT 到 OCR、VLM 或全文大模型复查。

### Round 2 最小判别实验

验证假设：如果使用全文学习到的通用 role/x-band 模板，在 selected pages 上按 native geometry 组装 Requirement，并将结果写入 canonical `Document.requirements[]`，则可以同时恢复 formal inventory、短值和 action role separation，而不再依赖 layout table 是否正确。

本轮实现范围：

1. Canonical schema 1.3 增加 provenance-bound `RequirementUnit`；
2. 全文阶段学习四类 template family，只保存统计，不生成实例；
3. selected-page 阶段按 template 和相邻页 halo 组装 Requirement；
4. `regulatory-ir.json` 从 canonical Requirements 派生，停止全局 modal 扫描；
5. evaluator 校验完整 critical signature、source text/role/bbox alignment、accepted recall 和 client/CAB confusion；
6. 只重跑当前小窗口，不执行全文 parsing、OCR、LLM 或 VLM。

Round 2 的 untouched holdout 应从尚未查看的 Salmon/Cod 19–20 页或其他同等高信息窗口中独立冻结；在规则完成前，主 agent 不读取其 Gold 内容。当前第 18 页只作 diagnostic regression，不再宣称 unseen holdout。

进入下一 checkpoint 的最低证据：

- Farm `6/6`、Interpretation `3/3`、Audit `12/12`、Salmon/Cod diagnostic `4/4` formal IDs；
- formal context 外的 unscoped modal false positive 为 0；
- `Yes` 等无 modal 的短值不遗漏；
- client/CAB 不跨列、不串入 normative text；
- 每个 accepted Requirement 有可与 Gold 对齐的 page、role、source text 和 bbox；
- 新 untouched holdout 未通过时状态只能为 `ADJUST`，不能标记本轮完成。

## Round 2：Template-bounded native assembly

### 验证假设

使用全文学习到的 Requirement template family、横向 role band 和编号 inventory，只在 selected pages 上按 native geometry 组装 Requirement，可以恢复正式 Requirement inventory，并阻断全局 modal scan 造成的 guidance/action 误报。

### Active regression

使用 Round 1 冻结的 Farm 28–29、Interpretation 19–21、Audit 1–3，共 21 条 active Gold。另保留 Salmon/Cod 18 页 4 条作为 diagnostic regression，但不再视为 untouched。

当前结果文件：`outputs/runs/goal04-round2/requirement-regression.json`。

- Requirement recall：`100%`
- Requirement precision：`100%`
- accepted recall / precision：`100% / 100%`
- formal inventory recall：`100%`
- normative text exact：`96%`
- requirement value exact：`100%`
- unscoped modal false positives：`0`
- Farm `6/6`、Interpretation `3/3`、Audit `12/12`、Salmon/Cod diagnostic `4/4`
- Audit client/CAB 数量均为 `50`，但 action exact 与 footnote provenance 仍未完成收敛

这证明 schema 1.3、四类 native assembler、Canonical adapter 和 Regulatory IR v2 的主方向成立。剩余 critical-field、footnote provenance、action typography/boundary 不能被这一 inventory 结果掩盖。

### Untouched holdout

独立冻结 Farm Standard 64–65 页，共 10 条 Requirement；规则实现前主流程未读取其 Gold 内容。首次运行只预测 3 条，holdout Requirement recall 为 `30%`、precision 为 `100%`。结果保存在 `outputs/runs/goal04-round2/requirement-round2.json`。

视觉与 native geometry 检查表明：第 64 页有 `Indicators:` 模板头，第 65 页继续相同单栏 Requirement 表，但不重复模板头。旧 profile 只允许 `ID_NORMATIVE_WITH_CONTEXT` 继承无头 continuation，因此第 65 页 7 个 dotted ID 虽存在于原生文字层，却未获得 family hint，也未进入 assembler。

对应 error taxonomy：1、10、11。文字层完整，不需要 OCR、VLM 或全文重跑。

### Checkpoint

`ADJUST`

下一轮的最小判别实验是：对所有 template family，仅当相邻 headerless page 的 candidate ID inventory 与用前一 family 做出的结构探针一致时，才逐页继承 continuation family；不得仅凭相邻页关系传播。修复后先重跑已转为 active 的 64–65 页，再另选新的 untouched holdout。Round 2 的 30% 结果永久保留，不能由重跑覆盖为 unseen 成绩。

## Round 3：跨文档 headerless continuation

### 验证假设

只在以下两个独立证据同时成立时，把相邻无表头页继承为上一页的 template family：

1. 当前页存在独立 dotted-ID candidate inventory；
2. 使用上一 family 做结构探针时，恢复出的 ID 与该 inventory 完全一致。

这应修复跨页 continuation，同时避免仅凭相邻页关系把普通正文误判为 Requirement 表格。

### Active regression

Farm Standard 64–65 页在 Round 2 揭盲后已永久转为 active。修复后恢复 `10/10` IDs，两个页面的 template family 均有证据，missing inventory 为 `0`。进一步修复了四条 `Indicator applicability:` 对正文的污染，并使上标脚注 marker 与列表 glyph 不再进入 semantic `normative_text`，但仍保留在原生 evidence 中。

当前重新评分结果：

- Requirement recall / precision：`100% / 100%`；
- formal inventory recall：`100%`；
- accepted ID coverage：`70%`；
- strict accepted result precision / coverage：`0% / 0%`；
- normative text exact：`90%`；
- provenance page exact：`100%`；
- exact segment / bbox coverage：`80%`。

inventory failure 已修复，但脚注 definition linkage、完整 logical structure 与严格 accepted correctness 尚未收敛，因此 active 成绩不能视为完成。

### Untouched holdout

在任何 Round 3 规则读取其 Gold 内容前，独立冻结 Salmon/Cod Standard 27–28 页，共 6 条 Requirement。该窗口同样包含第一页有模板、第二页无重复表头的跨页结构。首次盲测结果保存在 `outputs/runs/goal04-round3/requirement-round3.json`：

- Requirement recall / precision：`100% / 100%`；
- formal inventory recall：`100%`；
- accepted ID coverage：`66.67%`；
- strict accepted result precision / coverage：`0% / 0%`；
- normative text exact：`0%`；
- indicator text exact：`33.33%`；
- requirement value exact：`66.67%`；
- provenance page exact：`83.33%`；
- exact segment / bbox coverage：`16.67%`。

这证明 headerless continuation 的 inventory 修复跨文档泛化，但完整 Requirement fields 没有通过完成门。该样本在首次评分后已揭盲并永久转为 active，不能再计入后续 untouched holdout。

### 已修复的验收风险

旧 evaluator 的 `accepted_requirement_precision` 主要按 accepted ID 是否命中 Gold 计数，且 manifest 中把旧 Gold 重新声明为 active 时，report split 没有覆盖 Gold 的历史 split。现已新增严格的 `accepted_result_precision / recall / coverage`：只有唯一 identity、direct text、全部关键语义字段、actions 和 page/segment/bbox provenance 同时正确，才计为完整 accepted result；旧 ID-only 指标明确更名为 `accepted_id_*`，兼容别名不再作为完成门。report split 现在由本轮 manifest 决定，并单独保留 `gold_split`。Round 3 重新评分后 active 与 holdout 的 strict accepted result 均为 `0%`，真实地暴露了尚未解决的字段缺口。

### Checkpoint

`ADJUST`

下一轮按以下顺序推进：

1. 对 Round 3 已揭盲样本的 superscript host binding 与 legacy row ownership 做通用修复；
2. 建立 exact-marker Requirement footnote linker，脚注无法唯一关联时 fail closed；
3. 合成 `indicator + value + normative qualifier`，并把语义完整性纳入 accepted status；
4. 在这些规则读取任何新窗口前冻结 Round 4 untouched holdout；
5. 只重跑 active 小窗口与一个新 untouched holdout，不执行全文 parsing。

所有样本的不可逆状态保存在 `gold/requirements/sample-history.json`。

## Round 4：证据绑定、严格评分与跨页首行

### 本轮先修复的基础设施

- Gold manifest 与 prediction SHA-256 已进入校验链；同一 holdout 不能在揭盲后改写预测再冒充首次成绩。
- Gold v3 支持不可变 revision chain；Salmon/Cod 第 18 页的 annotation 修订保留 predecessor hash 与 revision reason。
- evaluator 将 ID 命中与完整结果分开：`accepted_id_*` 只描述 identity，`accepted_result_*` 要求正文、全部关键语义字段、actions 与 page/segment/bbox provenance 同时正确。
- Canonical Requirement 增加 deterministic `semantic_input`，将 core 与 qualifier source fragments 分开并保留 fingerprint。
- Salmon/Cod legacy 表格的 superscript marker 30–36 现在按 host geometry 绑定；marker 不再污染 semantic text，普通数字与编号步骤保留。
- exact-marker footnote linker 已能区分 direct、inherited、semantic 与冲突候选；证据冲突继续 fail closed。

### 首个 Round 4 候选 holdout 的处理

Interpretation Manual 103–106 页最初被独立冻结，但首次 parser run 在评分前因 duplicate `2.6.13` 失败。该 failure 随后被用于诊断，因此样本立即、永久转为 `active_diagnostic`，没有记录伪造的 blind score。

根因不是跨页合并，而是第 106 页 guidance 中换行开头的 regular-font `2.6.13` cross-reference 被弱 left-band regex 当成新的 bold Requirement ID。修复采用文档级 two-pass anchor proof：

1. 只从有显式 `Indicator` / `Requirement` header 的 direct rows 学习 ID x/height、font style 与右列起点；
2. headerless candidate 必须同时满足 robust geometry 与 row-pair，或 geometry、style 与 isolated-ID-line；
3. profile mapping 传给 assembler 后具有 authoritative 语义，缺失页面不能再次被 assembler 无条件继承。

修复后的 4 页 active run 恢复 `4/4` IDs，duplicate 为 `0`，normative text exact 与 page provenance 均为 `100%`。同时暴露下一层问题：footnote exemption、condition/negation、threshold scope、dates 与 logical structure 尚未达到严格 Gold。

### 真正的 untouched holdout

替代 holdout 在任何 prediction 生成前独立冻结 Audit Manual 11–12 页，共 7 条 Requirement，并通过 schema、integrity 与 source identity 校验。prediction hash 在评分前锁定；首次盲测结果保存在 `outputs/runs/goal04-round4/requirement-round4.json`。

| Holdout 指标 | Round 4 |
|---|---:|
| Requirement recall | 85.71% |
| Requirement precision | 100% |
| Formal inventory recall | 85.71% |
| Accepted ID coverage | 28.57% |
| Strict accepted result coverage | 0% |
| Normative text exact | 0% |
| Indicator text exact | 100% |
| Requirement value exact | 83.33% |
| Page provenance exact | 100% |
| Action-bearing recall | 20% |

漏项是页 11 顶部承接上一页版面的 `3.4.4`。其 ID、Indicator/Requirement/Applicability 与动作列都在本页，但 `Indicator:` 与正文处于同一 native line，旧 row-start 只接受独立 label，导致整行静默漏检。其他主要差异是 Audit `normative_text` 未包含 Applicability、standalone `-` 被拼入最后一个 action、多个 actions 共用一个 provenance span。

这些差异揭盲后，样本已转为 active diagnostic。已完成的通用修复包括：inline `Indicator:` row-start、按页面比例回看 row top、Audit formal metadata 包含 Applicability、placeholder dash 删除、每个 client/CAB action 独立 source span，以及 action 与 span 的 one-to-one binding。修复只在新的 Round 5 active output 中验证，不覆盖 Round 4 首次盲测文件。

### Checkpoint

`ADJUST`

Inventory 已接近收敛，但“近乎完美 Requirement 提取”仍未达到。Round 5 的最高信息增益任务是：

1. 在已揭盲 active 小样本验证跨页首条与 action-level provenance；
2. 系统修复 conditions、negations、footnote exemption、dates、threshold unit/scope 与 logical structure，而不是降低严格 evaluator；
3. 在修复前独立冻结新的 1–2 页 untouched holdout；
4. 继续保持每轮小窗口，不执行常规全文 parsing。

## Round 5：语义字段、动作证据与单页盲测

### 本轮冻结与运行边界

- 解析器状态在盲测前冻结为 SHA-256 `378eb696d4fc2056c83db3049ecdd9405d54e363c9f8df8db353d222e0c5407d`，指纹覆盖 94 个代码、配置和依赖锁定文件。
- active 只重跑 Audit Manual 11–12、Interpretation Manual 103–106、Salmon/Cod Standard 27–28，共 8 页。
- untouched holdout 只运行 Audit Manual 第 5 页，共 1 页；prediction 在读取 Gold 差异前锁定为 SHA-256 `d94cb1dfffda04793931b2e2922acfb7f4c2eddefcb72452cdcced5834e2582f`。
- 本轮没有全文 parsing、LLM 或 VLM。全文阶段只使用廉价 native heading/template profile 作为文档级支持证据。

### 通用修复

- Audit 页首 inline `Indicator:` continuation 已恢复，11–12 页从 `6/7` 提升为 `7/7` Requirement IDs。
- Indicator、Requirement value、Applicability、action 均有字段级 source span；placeholder `-` 不再成为 action，`Note:` 不再黏入前一 action。
- bracketed table footnote definitions 与 exact marker linker 已建立基础检测；脚注 source span 不再被 Canonical adapter 丢弃。
- conditions、negations、thresholds、dates、exemption 的 English 规则扩展，并保持 source-backed、无大型模型推断。
- Requirement `clauses[]` 现在对无列表使用 exact 单根，对明确 marker 列表恢复父子、顺序与显式 `and/or`；歧义结构 fail closed。
- 全文 native Principle/Criterion profile 恢复 source-backed hierarchy；partial-page run 只允许 `criterion_heading` 作为窗口外 supporting evidence，Requirement 直接证据仍必须位于当前处理窗口。
- 完整自动化回归通过，1 项环境相关测试跳过。

### Active regression

三个已揭盲窗口共 17 条 Requirement：

- Requirement recall / precision：`100% / 100%`；
- normative text exact：`88.24%`；
- Indicator / Requirement value exact：`94.12% / 94.12%`；
- page provenance exact：`100%`；
- action separation 与 action-bearing recall：`100% / 100%`；
- strict accepted result：`0%`。

严格结果为 0 并不表示主体都错。源文核验表明，主要混合了三类差异：真实 parser gap、typography/segment evaluator contract、旧 Gold 非 source-faithful 表示。代表性真实 gap 包括 Audit instruction/Note 未进入 Requirement 语义、裸 `0` 未结合 Indicator 生成计量阈值、脚注 qualifier 未提升、subject 与 composite cross-reference 缺失。代表性 contract/Gold 差异包括完整 source hierarchy 与旧紧凑路径、源 bullet/标点与人工改写、`applies_to` 的等义摘要，以及 bbox 被文本 exact 失败连带判错。

### Untouched holdout

Audit Manual 第 5 页独立 source-only 标注并二次复核，共 3 条 Requirement。首次盲测结果保存在 `outputs/runs/goal04-round5/requirement-round5.json`：

| Holdout 指标 | Round 5 |
|---|---:|
| Requirement recall / precision | 100% / 100% |
| Formal inventory recall | 100% |
| Normative text exact | 100% |
| Indicator text exact | 100% |
| Requirement value exact | 100% |
| Page provenance exact | 100% |
| Action separation / action-bearing recall | 100% / 100% |
| Critical field exact | 66.67% |
| Exact segment / bbox coverage | 66.67% / 66.67% |
| Accepted ID coverage | 33.33% |
| Strict accepted result coverage | 0% |

3/3 IDs 和直接文本证明 inventory 与 Audit matrix 主体装配已经跨页型泛化，但尚未达到近乎完美字段恢复。揭盲后的主要 failure family 是：

1. `Requirement: 0` 与 `0 (zero)` 没有结合 Indicator 形成 `eq 0 days` / `eq 0 mortalities`；
2. `[22]` 中的 modality、negation、三条 exception、内部 conditions 和 logical tree 未提升；
3. `[20]/[21]/[22]/[23]/[25]/[26]` bracketed footnote ownership 与定义边界不稳定；
4. p5 唯一 segment/bbox 失败实际由 curly quote/em dash 与 native ASCII glyph 差异触发，几何 IoU 正确；
5. acceptance 没有发现“短数值 Requirement 缺少对应 threshold”这一静默字段错误。

该样本已在首次分数记录后永久转为 `active_diagnostic`，不能再次计入 untouched holdout。

### Checkpoint

`ADJUST`

Round 6 不再优化已经达到 100% 的 ID inventory。最高信息增益顺序为：

1. 修复 bracketed footnote definition、ownership 与 exact linking；
2. 将 role-aware `semantic_input` 真正用于字段语义，补计量型裸 `0`、footnote/instruction qualifier 和 acceptance sentinel；
3. 将 bbox 几何评分与 typography text exact 分离，同时保持严格完整结果门；
4. 统一 source-backed hierarchy、clause、subject、`applies_to` 与 cross-reference contract，并对不忠实 Gold 使用可追溯 revision；
5. 修复后只重跑已揭盲 active，再冻结新的 document-disjoint 小样本 holdout。

## Round 6：脚注语义、证据契约与 Farm 单页盲测

- 解析器指纹：`567925f3712233a452781de85d4822cc1644e6d3836a30d3e6fbd85d9fec54a3`。
- active 共 9 页、20 条 Requirement，ID recall/precision、page/bbox/action 均为 `100%`；p5 除 `logical_structure` 外的 critical fields 全部 exact。
- typography normalization 后 direct text coverage 提升，bbox 改为独立几何评分，但 strict accepted 仍未放松。
- bracketed footnote ownership、计量型裸 `0`、source-explicit subject、field-boundary threshold、linked-footnote modality/condition/exception/reference/instruction 均已实现并通过完整回归：`294 passed, 1 skipped`。

新的 source-only holdout 为 Farm Standard 第 55 页，共 6 条。prediction 在揭盲前锁定为 `640c2484bcf16ad8c9ecad47334dff6ae510f0b66bae273c69d5a83fa25c569b`。首次盲测：

- Requirement recall / precision：`83.33% / 100%`；
- 命中 `5/6`，漏掉页首跨页 continuation `2.6.13`；
- Requirement value 与 page provenance 在已命中项均为 `100%`；
- strict accepted result 仍为 `0%`。

Checkpoint：`ADJUST`。下一轮首先诊断并修复“selected window 从 continuation 页开始时，前一页 Requirement 身份没有进入输出”的通用 halo/assembly 问题，然后统一 source-backed Gold v4 contract；不再扩大并发。

## Round 7：selected-window 前页 halo 与 continuation identity

### Root cause 与通用修复

Round 6 的 `2.6.13` 漏项并非文字层、OCR 或 template-family 识别失败。主流程已读取全文 native objects，但 assembler 在组装前按 `selected_indices` 删除第 54 页，因此第 55 页可见的 `c–e` 子项失去 Requirement identity。

Round 7 改为只给每个 selected run 增加一个真实、连续的前页 halo。单栏 continuation 只有在以下独立证据同时成立时才续接：上一 Requirement 的 formal span 到达页底、当前首个 Requirement ID 是其数值后继、当前页首字母 marker 连续承接上一页 marker。输出随后投影回 selected pages：窗口外只保留真实 ID object 形成的 supporting `continuation_anchor`，不复制窗口外 normative text，直接 provenance 仍只计 selected page。

### Active evidence

- Farm Standard 第 55 页从 `5/6` 恢复为 `6/6`，precision 与 page provenance 均为 `100%`。
- `2.6.13` 的 `normative_text`、`indicator_text`、3 个 direct continuation segments 及 bbox 均与 frozen Gold 精确一致。
- 因 governing modal clause 和可见 ID 在窗口外，`2.6.13` 保持 `review_required`，没有用 halo 制造虚假 accepted。
- Farm 64–65 页 `10/10`、Salmon/Cod 27–28 页 `6/6`、Interpretation 103–106 页 `4/4`；三个窗口 requirement precision 与 page provenance 均为 `100%`，未出现 `continuation_anchor` 扩散。
- 完整回归 `297` 项：`296 passed, 1 skipped`。解析器指纹为 `55d489e3a2913216daef4d5278839b71d9b9c39d4ad46e02c600647345f2bd76`。

详细证据保存在 `outputs/runs/goal04-round7/active-regression-summary.json` 和各 active 输出目录。

### Checkpoint

`ADJUST`

当前 hypothesis 已被 active 与跨文档回归支持，但 Round 7 尚未运行新的 untouched holdout，不能记为一轮完成门成功。下一实验是在上述 parser state 冻结后选择并双重复核一个新的小窗口 Gold，再首次盲测；同时只能通过 immutable revision 修复旧 Gold 中不忠实的 indicator/source-segmentation/logical contract，不能原位改写历史评分。

## Round 7 holdout：Audit Manual 17–18 页

### 冻结与首次盲测

- 在 prediction 前冻结 `audit-manual-p017-p018-round7-holdout`，共 13 条 Requirement、34 个 client actions、35 个 CAB actions；Gold SHA-256 为 `863987077dc2e1ae8023a9a2f50fc1cb90fd1ea0e30e166cf976cb8152d19e61`。
- 首次 prediction SHA-256 为 `da6c5b6e3851fd293d692a83c3319bb4bde7a3428142b97dca0786266d2948ee`，结果为 `0/13`，13 条均为 silent omission。
- 揭盲后确认根因不是 Audit template 或 source text，而是 `docling-parse` 初始化失败后旧 `pypdf` fallback 将每页降为一个无内部 geometry 的整页对象。文档 profile 因此得到 `support_rows=0`，无法发现 Audit Matrix。

### 通用修复与 active 验证

1. 新增基于既有 `pypdfium2` 依赖的 character-box fallback；按真实坐标恢复行和列，不依赖外部 AFM font resources。`pypdf` positioned visitor 仅作为最后兜底。
2. partial window 允许显式链接的窗口外 footnote 作为 supporting evidence；窗口外 direct Requirement evidence 仍被拒绝。
3. Audit CAB action 以列 geometry 为主，允许源文偶发的小写 marker；`Note Indicator ...` 整行及其换行 URL 不再污染上一条 client action。

修复后 active 输出位于 `outputs/runs/goal04-round7/audit-manual-p017-p018-active3/`：

| 指标 | Blind baseline | Active repair |
|---|---:|---:|
| Requirement recall / precision | 0% / N/A | 100% / 100% |
| Formal inventory recall | 0% | 100% |
| Normative / Indicator / value exact | N/A | 100% / 100% / 100% |
| Segment / bbox coverage | N/A | 100% / 100% |
| Page provenance exact | N/A | 92.31% |
| Action separation / action-bearing recall | N/A | 100% / 100% |
| Critical field exact | N/A | 81.20% |
| Strict accepted result | N/A | 0% |

唯一 page provenance 差异来自 selected window 前一页显式链接的 supporting footnote，不是 direct text 越界。`5.2.1` 的 nested bullet 现在保留在 source segment/native refs，同时 action 的平坦语义比较忽略纯 glyph 差异，因此 actions 已达到 `13/13`。其余未通过严格门的主要原因是 dates、threshold scope/operator、condition、modality scope 与 logical structure 尚未完全 source-exact。

本轮 194 个 Requirement 专项测试全部通过，action contract 的新增定向测试也通过。全套测试没有出现失败，但两个与本次修复无关的集成测试在导入大型图像/科学依赖时长期等待，因此完整回归尚未形成新的通过证据。当前修复后 parser state 为 `8f5e5c5f6ab210ea78654555f5fc0dc45e26ca91e0083a08c05da6faa1f35953`。

### Checkpoint

`ADJUST`

Inventory、direct source recovery 与 actions 已在本轮新 holdout 达到 100%，但严格语义和 acceptance 尚未完成。下一实验以小型可判别测试修复 dates、threshold relation/scope、condition、modality scope 和 logical structure；随后在文档不同位置冻结新的 holdout。不得把本次揭盲后的 active 结果重新计为 holdout。

### Round 7 semantic follow-up

- 日期识别新增 production-cycle、frequency、`per N years` 与 source-explicit deadline，已在本窗口找回 7 条 Requirement 的真实日期短语，并避免把 `2 years` 重复作为 quantity threshold。
- Audit 的 role-aware semantic input 现在优先绑定独立 `indicator_text` / `requirement_value` regions，不再无条件退回宽泛 `normative_text` region。
- 结构化 Requirement value cell 中的 bare quantity 现在具有 `eq` 语义；`5.2.3` 的 `100%` 从 ambiguous `other` 修复为 source-backed `eq 100%`，provenance 指向 value cell，该 Requirement 从 `review_required` 变为 `accepted`。
- 138 个 semantic、Gold、assembler、model 跨文档专项测试通过。当前 parser state 为 `fa4549fd84fe13650f1608572a813bedcdf2c8667a17f9bb64f08964286b3e2e`。

现有 Round 7 Gold 的多项 `applies_to` 是人工语义摘要，并非源文 substring；因此上述真实修复不会自动提高 strict exact 分数。下一步必须先定义 source-backed v4 scope contract，再用 immutable Gold revision 评估，不能把解析器硬编码成 Gold 摘要生成器。

### Round 7 semantic scope v4 checkpoint

- 新增 `docs/contracts/requirement-semantic-scope-v4.md`，将 semantic value 与其作用对象分离。作用对象由受控 `target` 与 source-exact `anchors` 共同证明；历史 v2/v3 Gold 不得原位修改。
- Canonical model 新增 `RequirementTextAnchor` 与 `RequirementScopeRef`。旧记录允许缺省；新记录一旦带 `scope_ref`，validator 会检查 segment identity、字符边界、逐字 substring，以及同 segment anchor 的顺序与重叠。
- parser 现在为正文 modality/negation/condition/date、普通 threshold、Indicator/Requirement value 表格 threshold，以及显式链接 footnote qualifier 生成 exact scope refs。
- 真实 active 输出 `outputs/runs/goal04-round7/audit-manual-p017-p018-active9-scope-v4/` 保持 13/13 Requirement。modalities、negations、conditions、thresholds、dates 共 25 个 semantic items，`25/25` 具有 scope refs，Canonical validation 为 0 errors。
- Requirement models、canonical adapter、footnote linker、semantic active、Gold/manifest、assembler 与 template-profile 专项回归全部通过。冻结 parser state 为 `51519ef2fb5e77373c273efe4b586c6ae81f8570c1ac4cff160f9a71aab7c8f4`。

Checkpoint：`ADJUST`。v4 目前已成为可执行 Canonical contract，但 Gold schema、immutable v4 revision 和 v4 evaluator 尚未完成，因此不能据此重算 strict score。下一步先完成评价闭环，再继续 qualitative threshold、condition/modality semantics 与 logical structure；不得用旧自由摘要字段作为新 parser 的目标。

### Round 7 v4 evaluator 与 active semantic acceptance checkpoint

- 新增 Gold schema v4、immutable revision integrity 和 v4 evaluator。v4 对 modality、condition、threshold 等字段比较 source-backed `scope_ref`，对 subject/applicability 比较 text evidence；旧 v2/v3 评分行为保持不变。
- qualitative threshold 现在支持 `at or below the country Entry Level`、`at or below the Global Level` 和 `25% per 2 years`；同时恢复 `until` condition、`need to` obligation，并修复多 modal clause 的 source boundary。
- CAB action 的大小写异常改为 geometry-aware：Audit Matrix 中 auditor column 已确定且 action text 完整时，lowercase marker 作为可审计源异常保留，不单独阻断 Requirement；缺 marker、错列或证据不完整仍 fail closed。
- 诊断发现 `5.2.1`、`5.2.2`、`5.2.11` 的 `normative_text_provenance_mismatch` 是校验顺序错误。原逻辑在 exact source 比较前删除所有已链接 footnote number，使源文中合法的 bracketed `[84]` 等 marker 被破坏。现改为先验证原始 source-exact evidence，仅在失败后才执行 attached-number fallback。
- 最新 active 输出 `outputs/runs/goal04-round7/audit-manual-p017-p018-active15-footnote-provenance/` 中 13/13 Requirement 为 `accepted`、0 `review_required`、0 `abstain`，Canonical validation 为 0 errors。`5.2.9` 仍保留 `auditor_action_marker_case:1:a` 作为非阻断审计信息。
- 六个 Requirement model、Gold、semantic 与 Canonical 定向测试套件全部通过。当前 parser state 为 `c0477449a70c26725c7f77e6365bc5b1b5beb55f57e4dee94f35a6eedb23ceef`。

Checkpoint：`ADJUST`。这是揭盲后的 active acceptance，不是新的 holdout 成功。页面级 completeness gate 仍因整页 visual-region 启发式产生 2 个 page review items，但不再污染 Requirement status；下一实验先完成 immutable Round 7 Gold v4 revision 和 v4 评分，再冻结新的 document-position-disjoint 小窗口 holdout。

### Round 7 immutable Gold v4 与第一轮 source-backed 评分

- 新增 `audit-manual-p017-p018-round7-holdout-v4.json`，作为原 revision 1 的 immutable revision 2。predecessor path/SHA-256 已绑定，source、sample window、133 个 frozen segments 与 excluded regions 保持不变；integrity gate 新增对 segment/exclusion 漂移的拒绝。
- v4 adjudication 纠正了 predecessor 中已确认的语义边界：`5.1.6` 不重复计算两次 `> 6%` 法律阈值；`5.2.4` 的 `after treatments` 不作为条件；`5.2.5` 保留两个 production-cycle 时间范围并把主 clause 恢复为 source-exact；`5.2.11` 删除 complement-clause false condition，保留 footnote 88 的 `before prescribing medication` 时间范围。
- 新增 `active_diagnostic` manifest 模式。它允许揭盲后的 active-only 诊断，但报告固定为 `completion_gate_eligible: false`；正式 round 仍强制同时具备 active 与 frozen holdout，完成门没有降低。
- v4 active report 位于 `outputs/runs/goal04-round7/requirement-evaluation-v4-active15.json`。Requirement recall/precision、direct text、segment/bbox 与 action separation 保持 100%；critical-field exact 为 `88.89%`、critical-nonempty exact 为 `75%`，strict accepted-result 仍为 `0%`。
- field-level 结果：modalities `92.31%`、negations `100%`、thresholds `76.92%`、applicability `100%`、conditions `84.62%`、exceptions/exemptions `100%`、dates `53.85%`、logical structure `92.31%`。这成为下一轮修复的可执行差异清单，避免以 13/13 accepted 掩盖语义错误。
- 八个 Requirement Gold revision/manifest/model/semantic/Canonical 定向套件全部通过。当前 parser state 为 `28f942e47e11a9f43296fa489384543930cfc07e8573680c6613b07a234e899c`。

Checkpoint：`ADJUST`。v4 评价闭环已成立，但结果明确否定当前 active output 的严格正确性。下一实验按信息增益顺序处理 dates、thresholds、conditions，再处理 `5.2.5` logical structure 与 strict subject/context 差异；修复后才选择新的 document-position-disjoint holdout。

### Round 7 v4 semantic exact active checkpoint

- 在不修改 frozen Gold 的前提下，修复了四类通用语义边界：数值 applicability 条件与 postnominal `after` 的区分；Requirement value / applicability 重复阈值的角色化去重和字段级 source anchor；production-cycle、annual、frequency 与 footnote date 的谓词作用域；qualitative threshold 的主语及 governing action 作用域。
- linked-footnote scope 统一使用受控 `kind=footnote`；Audit action 中的 actor 不再被提升为 Requirement subject，显式 subject 保留 source case。
- Audit Indicator 内联编号列表现在只从 `indicator_text` 构造 clauses，不再吞入 `Requirement:` / `Applicability:`；`Appendix VI)` / `VII)` 不再误判为 Roman list marker。Evaluator 对 source-equivalent `1` / `1.` marker 使用同一逻辑签名。
- 最新 active 输出为 `outputs/runs/goal04-round7/audit-manual-p017-p018-active18-logical/`。13/13 Requirement 为 `accepted`，Canonical validation 0 errors；v4 九类 critical fields 与 nonempty critical fields 均达到 `100% exact`，Requirement/direct text/segment/bbox/action 仍为 `100%`。
- strict accepted-result 仍为 `0%`。当前差异已集中到 compact/full criterion path contract、cross-reference / footnote / instruction ownership，以及 1 条窗口外 supporting footnote 导致的 page-set 差异；这些不能用 critical-field 成绩替代。
- 10 个 Requirement 定向与跨结构测试文件共 204 项通过。parser fingerprint 为 `361ed934830355daf0e9ef70a1d38725bc6341d844817cdd77b0df9e259ab9dd`；fingerprint artifact SHA-256 为 `bee1303d4416942fd77420a5cafe36434121d615d0d02d6bbb149dc9b96517a1`；prediction SHA-256 为 `5ff5736b296a364c728a89a325c316412595bb5a82d8109a5f5157cd1a335263`。

Checkpoint：`ADJUST`。本轮 hypothesis 已完成 active 修复与跨结构定向回归，但样本已揭盲且 `completion_gate_eligible=false`。下一实验先统一 hierarchy 与 linked-context 的 strict source-backed contract，并把 direct page provenance 与 supporting evidence page 分开评价；达到 strict exact 后再冻结新的 position-disjoint holdout。

### Round 7 hierarchy 与脚注归属 checkpoint

- `criterion_path` 改为语言稳定的语义标识，如 `Principle 5 > Criterion 5.2`；完整英文或挪威语标题仍保留在 source-backed `criterion_heading` regions。
- 脚注明确列出 Requirement ID 时统一标为 `semantic`；`inherited` 仅描述相邻页物理续接。Appendix reference 已排除句末标点。
- 17–18 页 active19 仍为 13/13 `accepted`，critical fields 保持 100%；strict accepted-result 从 0% 提升至 `38.46%`（5/13）。63 个 hierarchy、footnote 与 semantics 定向测试通过。
- 剩余 8 条差异全部可解释为 cross-reference / associated-instruction ownership，另有 `5.1.6` 的窗口外 supporting footnote page 边界；未通过降低阈值或修改 frozen Gold 消除。

Checkpoint：`ADJUST`。下一轮只实现通用的 inline reference 与 instruction-block 绑定，再重评同一窗口；暂不进入新 holdout。

### Round 7 linked context strict exact checkpoint

- Audit `Note:` / `Note Indicator` / `Instruction to Clients and CABs` 现在由版面边界与显式 Indicator owner 绑定为独立 `instruction` evidence，不进入 `normative_text`、client actions 或 CAB actions。
- resolved footnote marker 被保存为 exact cross-reference；明确依赖语句（如 `after achieving Indicator 5.2.6`）单独恢复，普通数字不会被提升。Cross-reference 与 footnote relation 采用集合语义比较，条款和 action 顺序仍保持严格。
- rendered page 16 与 native text 共同确认 Criterion 5.1 footnote `[77]` 明确列出 `5.1.6`。新增 immutable Gold revision 3，将 page 16 证据标为 supporting segment；17–18 direct sample window、direct segments 与 exclusions 未改变。Evaluator 分开计算 direct sample provenance 与 supporting evidence。
- active22 报告 `requirement-evaluation-v4-active22-v5gold.json` 达到 13/13 strict accepted-result；Requirement、全部 critical/strict semantic fields、actions、page/segment/bbox provenance 均为 100%。完整测试套件通过，只有 1 个既有环境相关 skip。

Checkpoint：`CONTINUE`。该结果证明 active failure 已闭环，但不提供新的 holdout 证据。下一实验冻结 position-disjoint 小窗口，再运行当前 parser；若揭盲失败则按新 error class 继续诊断。

### Round 8 holdout selection checkpoint

- 在读取页面内容或生成 prediction 前，冻结选择 `interpretation-manual-p080-p082-round8-holdout`，页面 80–82，parser fingerprint 为 `02fe91e7c754a73e044e1039c8ce65e8ec02b44bbe29c6f40146c0e14a74536c`。
- 该窗口来自不同于 Round 7 Audit Matrix 的 Interpretation Manual 结构族，检验 Requirement/interpretation 分离、局部 heading、跨页续接与 references；sample history 当前保持 `holdout`。
- 已生成 source-only native evidence，来源 SHA-256 为 `804ead3d1d1a53019869b5385dabfb86356b8276b990538c0d782e750167777e`；尚未生成 parser prediction，也未揭盲差异。

Checkpoint：`CONTINUE`。下一步只做 source-only Gold annotation 与复核；Gold 冻结和哈希登记完成前不得运行 parser。

### Round 8 Interpretation Manual 首次盲测与 Gold adjudication

- 页面 80–82 的 source-only Gold revision 1 在 prediction 前冻结，SHA-256 为 `3eccab23059f67e8520950486efe2014c40db17fea4422fbd73cd0b80f98b543`；当前 parser prediction SHA-256 为 `0ef007a41d5638ec6f03e2e6fd0584f9cc044db85ab56774bf834dd42b841c56`。
- 首次盲测恢复正式 Requirement `2.5.1`、`2.5.2`、`2.5.3`，inventory recall/precision 与 direct page/bbox provenance 均为 `100%`，且没有把 81–82 页 modal-bearing interpretation 误增为 Requirement。
- 揭盲后的严格结果未通过：仅 `1/3` 为 accepted，strict accepted-result 为 `0/3`，critical-field exact 为 `59.26%`。主要 failure 是 `The UoC` subject 未恢复、`'Acceptable'` 引号边界粘连、footnote 11 的 negation/date/exemption scope、`In cases where` condition 作用于错误 clause、双 modal sentence 未拆成两个 clauses，以及 Appendix section / Indicator reference 未按 canonical contract 恢复。
- source adjudication 同时发现初版 Gold 把 modality anchor 锚到完整字段、Requirement exemption 锚到正文、criterion path 使用完整标题等 v4 contract 错误。原始 Gold 和盲测报告保持不变；新增 immutable revision 2，SHA-256 为 `6519c2e6587c07aa793d0459ba41b5bc0c21235913393e42a24430ef62fc7670`，source segments、selected pages 和 exclusions 未改变。
- 用同一冻结 prediction 对 revision 2 重新诊断后，inventory/direct page/bbox 仍为 `100%`；critical-field exact 为 `62.96%`、critical-nonempty exact 为 `35.71%`、strict accepted-result 仍为 `0/3`。该报告为 post-reveal `active_diagnostic`，不具备 completion gate 资格。

Checkpoint：`ADJUST`。Round 8 样本已永久转为 active diagnostic。下一实验按信息增益依次修复 native quote spacing 与 explicit subject、footnote qualifier semantics、condition/clause boundary 和 composite cross-reference，并回归 Round 7 strict-exact active 样本；不得把修复后结果重新计为 holdout。

### Round 8 attached footnote marker evidence checkpoint

- Canonical source region 现在分离语义视图与原生证据：`source_text` / `resolved_text` 仅在正式 normative roles 中删除已明确链接且附着于词尾的数字脚注标记，`native_text` 保留原始 `shall10` / `status11`。脚注定义与 `[22]` 等 bracketed reference 不做改写。
- 新增定向测试覆盖 modal 后脚注、predicate 内脚注及 bracketed reference，Requirement assembler 与 Canonical adapter 共 72 项通过。
- 80–82 页 active2 输出中 `2.5.1`、`2.5.2` 的 modality scope 均恢复 source-exact anchor；3/3 normative text exact。对 immutable Gold revision 2 的 critical-field exact 从 `62.96%` 提升至 `74.07%`，critical-nonempty exact 从 `35.71%` 提升至 `57.14%`。
- inventory/direct page/bbox 继续为 `100%`；`2.5.2` 仍因 footnote 11 qualifier ambiguity 为 review，`2.5.3` 仍因 `In cases where` condition boundary 为 review，strict accepted-result 仍为 `0/3`。

Checkpoint：`ADJUST`。本轮 hypothesis 已被真实小样本验证。下一实验只处理 footnote 11 的 exemption、negation、date 与 false quantity threshold，不与 condition/clause 或 composite reference 修复混在同一轮。

### Round 8 footnote qualifier final checkpoint and user review run

- footnote 11 的 explicit exemption、passive negation、first-N-years date 与 false quantity threshold 已按 source-backed contract 修复。bare superscript label 从 semantic source view 分离并保留于 `native_text`；bracketed footnote label 继续保留。
- 96 项 Requirement semantics/Canonical 定向测试与 footnote linker 回归通过。Round 7 Audit 17–18 页新输出 SHA-256 与 13/13 strict-exact 基线完全一致。
- Round 8 active4 中 `2.5.2` 变为 accepted，critical-field exact 为 `85.19%`，critical-nonempty exact 为 `71.43%`，direct page/segment/bbox provenance 均为 `100%`。剩余差异集中于 `2.5.3` condition/clause、composite reference 与 shared context。
- 按用户要求暂停继续优化，并对 `data/inputs/` 四份 PDF 做完整解析。四份均完成全部页面并生成 Markdown、Canonical JSON、Requirement IR 和 quality report；统一索引位于 `outputs/runs/four-file-review-20260828/REVIEW_INDEX.md`。
- 两份输出为 `failed`：Salmon and Cod Standard 存在重复 `5.1.5`；Interpretation Manual 存在多个重复 Requirement identity 和 `4.4.12` context/formal native-evidence reuse。另两份为 `review_required`。这些状态保留供人工核验，未通过降低质量门转为通过。

Checkpoint：`STOP`（用户要求的人工核验暂停点）。目标未完成；Round 8 未达到 strict exact，四文件全文仍有 review/validation failure，且尚无真实 Norwegian document-disjoint holdout。

## 2026-08-31 Smarter Compliance document-disjoint sample

用户明确要求恢复小样本测试，从 `smarter-compliance-aquaculture` 的 Requirement source library 选择新 PDF，不批量解析全部文件。本轮没有修改 parser 代码。

### Sample 与 observed failure

- `CS005-001_ASC_Farm_and_Feed_Certification_and_Accreditation_Requirements.pdf`，PDF 20-22 页。源页包含两张多列认证类型 Requirement 表：Table 1 有 Requirement 1-7，Table 2 有 Requirement 1-5。环境恢复后的 authoritative 输出仍把两张表都解析为 `2 x 3` 表头片段，表体拆成 paragraphs；Canonical Requirements 为 `0`，Regulatory IR Requirements 为 `0`，仅产生 21 条无 `requirement_id` 的 modal statements。Markdown 丢失 applicability column binding，并把 Requirement row `5` 误作 `[^5]` footnote。quality gate 未报告 table-body truncation 或 Requirement omission。
- `PA057-001_Guidance_for_condition_assessment_of_land-based_aquaculture_facilities.pdf`，PDF 8-11 页。native text、bbox 与 Markdown 可读，包含 `§ 22`、`skal`、`må` 和 `a-d` 列表；但 Canonical Requirements 与 Regulatory IR statements 均为 `0`，section headings 也未形成 heading blocks。4 个 review items 只指向小型 footer/visual regions，没有暴露 Norwegian Requirement omission。
- `CS010` 的 3-4 页尝试在安全预检被 `encrypted PDF requires an explicit decryption workflow` 阻断；`CS011` 也确认带 AES permission encryption，因此未进入内容解析。source library 中 6 份 GLOBALG.A.P. PDF 均带 encryption 标记。

### Runtime diagnosis

首轮运行暴露 `.venv` 内 macOS `compressed,dataless` 文件。按原版本恢复直接阻塞的 runtime packages 后，imports 通过；`numba 0.67.0` 与 `llvmlite 0.49.0` 恢复后重新运行 CS005，`img2table` 已实际进入 fallback route，但 header-only failure 仍复现，因此最终结论不归因于未恢复环境。

定向回归首次为 73 passed、2 个历史 fixture 读取超时、1 skipped；恢复该 fixture 后 `test_requirement_template_profile.py` 为 13/13 passed。现有模板断言仍成立，但没有覆盖本轮新结构与 Norwegian semantics。

完整证据与输出索引见 `outputs/runs/smarter-compliance-requirement-sample-20260831/TEST_REPORT.md`。

Checkpoint：`ADJUST`。下一最小实验是分别验证两项 hypothesis：`Req. + multi-applicability columns` 的表格/Requirement 组装，以及 Norwegian `§/skal/må/kan` 的 hierarchy 和 modality 提取。encrypted-input workflow 作为独立安全决策，不通过隐式放宽预检处理。
