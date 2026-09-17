# Engineering overview illustration

Date: 2026-09-09. Scope: the local Requirement Workstream as inspected on this date.

[Open the diagram](engineering-overview-20260909.png).
Generated with the built-in imagegen tool. The delivered raster is 1536 × 1024 pixels; the requested larger canvas was not returned by the tool. [Initial prompt](engineering-overview-20260909-prompt.txt) and [connector correction prompts](engineering-overview-20260909-edits.txt) preserve the generation specification.

## Reading the diagram

Read System1 to System2 to System3 for the data path. The lower amber strip is the shared operational human-review loop. The upper violet strip is a proposed multi-agent engineering improvement design, with suggested coordinator, builder, independent reviewer and human-checkpoint roles. It is not an implemented autonomous service. System1's deterministic Leader and three bounded modules are separate from this proposal.

Implemented System2 intake routes HTML, XLSX and PDF independently, preserving format-specific Canonical and evidence. Shared acceptance first covers full text, structure and dependencies, then Requirement classification and coverage. Incremental delivery reports accepted ranges and unfinished scope. Unsupported-original parsing copies preserve their original lineage and return to intake; they do not bypass gates.

System3's input feed exists; semantic runtime and Site Model consumer acceptance do not. The candidate semantic fields and human semantic review are design elements. Optional API assistance is a separate suggestions-only capability; no real provider or production calibration was configured in the inspected implementation.

## Evidence used

Current dated state takes precedence over older checkpoints or earlier diagrams.

| Diagram claim | Inspected source |
| --- | --- |
| Current integration and boundaries | [Root state](../../../PROJECT_STATE.md), [project contract](../../../AGENTS.md) |
| System1 Leader, bounded modules and ownership | [Engineering guide](../../../system1/Code/ENGINEERING.md), [System1 state](../../../system1/PROJECT_STATE.md) |
| Five evidence dimensions | [Source assessment implementation](../../../system1/Code/src/system1/source_assessment.py) |
| Format branches and detailed PDF routing | [Format architecture](../../../system2/docs/architecture/06-format-pipelines-and-human-conversion.md) |
| Current conversion, gate sequence and delivery | [Two-stage contract](../../../system2/docs/contracts/two-stage-review.md), [System2 current state](../../../system2/PROJECT_STATE.md) |
| Explicit jobs, conversion and source reconciliation | [Orchestration implementation](../../../system2/src/pdf_extraction/orchestration/workflow.py) |
| Guarded decisions, overlays and incremental feed | [Review workflow implementation](../../../system2/src/pdf_extraction/review/workflow.py) |
| Optional assistance and calibration boundaries | [Assistance contract](../../../system2/docs/contracts/optional-assistance.md) |
| Shared human interface and connected operations | [Workbench state](../../PROJECT_STATE.md) |
| System3 candidate fields and unconnected consumer | [System3 design](../../../system3/DESIGN.md), [System3 state](../../../system3/PROJECT_STATE.md) |
| Component environment ownership | [Environment guide](../../../ENVIRONMENT.md) |

The older format architecture contains superseded conversion/integration status prose. The 2026-09-09 state and two-stage contract govern those current-status claims in this diagram.

## Visual validation and limits

The generated first draft incorrectly connected System1 storage to System2 delivery and included an intake-to-System3 shortcut. Two imagegen editing passes corrected the source intake and System3 handoff, separated conversion from PDF intake, completed the history/reopen arrow, and simplified the outer engineering feedback labels. The selected final image was visually inspected for these paths and the main labels.

This is a human-facing engineering map, not an exhaustive code dependency graph or independent runtime acceptance test. Some fine print requires zoom. Implemented paths do not imply calibrated source accuracy, complete current-source processing, enabled optional PDF backends, or accepted System3 consumption. No parsing job, source decision, provider, automation, release or external publication was started by creating this artifact. Project code, Canonical, workbook and operational state were not changed.

