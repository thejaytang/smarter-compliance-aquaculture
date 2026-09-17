# Two-stage review and incremental delivery contract

Version: `system2-workflow/1`, implemented 2026-09-09. This contract governs the shared workbench path. Existing parser CLI, Canonical schemas, diagnostic review APIs and historical artifacts remain compatible.

## Ownership and acceptance

System1 owns the registry, original snapshots and effective source admission. Workbench owns the single editable threshold policy, named sessions and browser interactions. System2 owns parser generations, review overlays, gate decisions, receipts, downstream events and weekly QA. System3 owns future semantic enrichment; its service and consumer acceptance remain absent.

`INCLUDE → original text and structure → content acceptance → Requirement classification and coverage acceptance → incremental System3 input` is the production order. Existing PDF domain products are diagnostic proposals; they do not constitute workflow acceptance. Original Canonical artifacts are immutable. The workflow's field index is a read-only projection plus separately recorded human corrections, referenced by source hash, Canonical hash and unit version. Corrections never overwrite source files or Canonical.

Every parsed range has a coverage unit. Unmapped text stays visible as residual content; it is never silently dropped. HTML retains its existing DOM, lists, notes, tables and attachment facts; XLSX retains cells, formulas/caches, merged regions and hidden state; PDF retains pages, segments, crops, table geometry and reading-order facts. PDF numbered table rows derive from source cells, not already inferred semantic fields. Coverage and related context must pass content review across the complete dependency graph before dependent Requirement classification. Missing or cyclic dependencies remain blocked. Coverage checklists and superseded source fragments cannot be delivered as Requirements. Substantive parser warnings remain explicit coverage blockers. Missing full text remains a source-level blocker. A human format conversion cannot clear a supported-format parsing failure.

Classification records every unit as `requirement`, `context`, `non_requirement`, or `undetermined`. Excluding content requires a reason. Full source completion requires every gate and every coverage unit to pass and the parser to have reached the end. Accepted ranges may publish while other ranges remain unfinished. Preserve source clause boundaries and numbering; split/merge actions correct extraction boundaries, not minimal obligations or semantic enrichment.

## Durable jobs and evidence

`runtime/workflow/workflow.sqlite` owns jobs, receipts, immutable policy mirrors and append-only events. Workbench runs one parser worker guarded by a file lock. Viewing starts no new jobs. An explicitly queued job resumes after service restart, with artifact hashes rechecked. PDF processing advances three pages per checkpoint with one previous page of context; the halo is evidence, not another independent Requirement. Cross-window relationships require explicit review.

States: `queued`, `running`, `waiting_review`, `paused`, `failed`, `conversion_required`, `partial`, `complete`. `parser_complete`, `source_complete`, `eligible`, pending unit counts and current published items are distinct. Pause stops at the current bounded window. Retry resumes a failed checkpoint. Reprocessing retains the retired generation in the event ledger, suspends its deliveries and produces new artifacts. No parser attempt overwrites an earlier attempt.

Source identity uses source ID, snapshot ID and file hash. A new version requires an explicit start and invalidates older eligibility. Loss of INCLUDE stops processing and suspends delivery; regaining eligibility does not implicitly create a new job. Reads of state/feed reconcile current source bytes and eligibility. Local polling also detects changes while the workbench is running.

## Policy and confidence

Workbench `review_policies` is the only editable policy store. Defaults are 0.95 for System1, System2 content and System2 Requirement gates. System3's stored setting is inactive. Each revision records actor and time. Components apply the revisions in order and return receipts; a failed application is retried and must not display stale live progress as current.

Each necessary score part has confidence, evidence, scoring method, calibration version and applicable scope. The minimum necessary score controls routing. Missing or uncalibrated scores, conflicts, structural blockers and unfinished human follow-up remain pending. OCR scores and model self-reports are not acceptance scores. Human acceptance is separately recorded and does not rewrite a historical score to 100%.

Required parts are explicit: A uses `text`, `coverage`, `structure` and `order`; B uses `classification`, `association` and `subdivision`. The latter includes whether retaining the complete parent without subdivision is correct. Exactly one supported part per required dimension is necessary. Missing, repeated or unknown dimensions keep automatic acceptance pending. An invalid/uncalibrated score or missing/conflicting evidence produces no overall supported percentage. Original score records remain preserved.

Persisted B scores also need the current method/original/proposal binding described in [optional assistance and calibration](optional-assistance.md). A classifier change cannot reuse an old score to release a new proposal. Reconciliation retains score history and human decisions, while withdrawing unsupported machine acceptance and its downstream delivery.

The current gate version is `required-confidence-dimensions/1`. Reconciliation refreshes older cached machine acceptances and records the upgrade before downstream delivery. Already pending items and named-human confirmations do not become a new blanket review solely because the gate code changed. Relevant original/content/dependency changes still use normal invalidation. The browser exposes the seven dimensions and recorded evidence. Calibration artifacts and provenance remain separate acceptance obligations; [checkpoint 36](../reports/36-confidence-dimensions.md) records current evidence and gaps.

Raising the threshold reopens affected machine decisions and suspends their deliveries. Lowering it can restore only untouched, low-score-only items; drafts, human reports, rejected results and unresolved structure remain protected. A valid human confirmation survives policy changes but is invalidated by relevant source/content/dependency changes. Re-evaluation changes no original parser artifacts. Stable unit IDs and transactional recomputation prevent duplicate tasks.

## Browser and bridge operations

The loopback service validates Host, Origin, CSRF and server-bound reviewer identity. System2 runs through its own environment using the JSON bridge `pdf_extraction.orchestration.workflow`. Successful envelopes contain `ok: true` and `data`; business rejections never imply application.

| Browser route | Owner operation | Result |
| --- | --- | --- |
| `GET /api/system2/state` | persisted compatibility/read views | Use the indexed queries below for the normal browser |
| `POST /api/system2/start` | start | explicit registered source IDs, receipt |
| `POST /api/system2/control` | pause/resume/retry/reprocess | new job revision |
| `POST /api/system2/decision` | guarded review | receipt and resulting revision/state |
| `POST /api/system2/suggest` | optional suggestions | separate evidence-cited proposals; no acceptance authority |
| `POST /api/system2/conversion` | register parsing copy | original/copy lineage and queued receipt |
| `GET /api/settings`, `POST /api/settings` | policy history / revision update | thresholds, audit and application outcome |
| `GET /api/system2/qa`, `POST /api/system2/qa` | weekly QA | frozen samples and named findings |
| `GET /api/system3/input?after=N` | incremental feed | `system3-input/1`, events, cursor and incomplete scopes |

Review writes bind canonical UUID request ID, named actor, document ID, unit ID, source SHA-256 and policy revision. Current clients use a unit/dependency guard; legacy clients retain the expected document revision. Each request is recorded atomically with its decision and output events. Repeating the identical request returns the original receipt; reusing its ID with changed content or submitting stale versions is rejected. Browser drafts are not decisions. Transport failures keep the request identity for retry.

Actions: confirm content, explicitly resolve listed issues with an evidence note, correct text/fields, correct structure roles at source locations, classify, report/reject/unreadable, reopen, save draft, supplement omitted source content, split, merge. Structure-only corrections are supported without changing text. Corrections trigger a new content check and invalidate all direct and indirect dependent Requirement decisions. Drafts are separate audit events; old draft rows are not formal review history. The browser requires explicit comparison of stale drafts and refuses to confirm edited text before its correction is applied. Split preserves all source text in order; merge retains all parent locations. Supplement needs source position and an evidence note. Reviewed items can be reopened using “Include reviewed content”.

Unsupported originals may receive an actor-bound uploaded HTML/XLSX/PDF parsing copy. Registration verifies staged bytes, source revision, conversion method and completeness confirmation, stores the copy immutably, and retains the original hash/format/operator/method in `parsing_copy_of`. Supported-format empty bodies or parser failures must be repaired/reprocessed, not marked converted.

## System3 input

The cursor is a monotonically increasing event sequence; read pages until no further events arrive. Consumers must apply events by sequence and requirement identity, deduplicate sequence numbers, and persist their cursor only with applied state. `add`/`replace` carry source version, unit version, original-supported fields, source positions, Canonical references and separate decision origins. `suspend` means stop using an item until a later accepted delivery; `withdraw` records explicit exclusion. Policy, eligibility and retired-generation events retain their history. Requirement identity is interpreted together with document/source version.

Each response includes up to 1,000 events and `has_more`; the browser follows every page. `current_requirements` is a current accepted snapshot, not a historical count. The response always includes per-source eligibility, completion, state and remaining reviewed scope. A delivered subset is not a complete source. The interface explicitly reports `consumer_connected: false`; it does not claim System3 enrichment has run or that a consumer acknowledged delivery.

## QA and acceptance limits

The [weekly original-sampling contract](weekly-original-sampling.md) owns the current System1 5, A 20 and B 5 monitoring rules, activation boundary, original-side population, positive/negative judgments, shortfalls and explicit repair follow-up. Earlier machine-only five-item batches remain historical records. Monitoring does not establish independent acceptance accuracy.

Engineering regression, complete processing of current INCLUDE sources, independently calibrated real-language accuracy, external API effectiveness and System3 consumer acceptance are separate gates. See [current state](../../PROJECT_STATE.md), [execution plan](../plans/03-system2-completion.md) and [implementation evidence](../reports/15-two-stage-workflow.md).


## Browser read projections

The normal browser uses the [indexed review contract](review-workbench-v2.md): separate Content proofreading and Requirement judgment queues, paginated summaries, guarded single-unit reads and paged history. Whole-document compatibility responses are retained for older clients only. Review writes with a unit guard are independent of unrelated unit revisions; source/policy and real dependency changes still reject stale requests. Read projections never apply policies, reconcile sources or generate Excel synchronously.

## Independent B subdivision operation

The [provisional subdivision contract](requirement-subdivision.md) defines B parent/subitems separately from A structural split/merge. Full accepted A source items remain intact; exact B spans, shared context and temporary counting decisions are versioned in the workflow database. A/context changes require B rechecking; an unfinished stage draft cannot remain accepted solely because of an older human decision.
