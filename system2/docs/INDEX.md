# Project Document Index

## Architecture

- [Full engineering design](architecture/00-full-engineering-design.md): overall architecture and data model.
- [Phase one](architecture/01-core-parsing-workflow.md): core parsing pipeline.
- [Phase two](architecture/02-capabilities-and-accuracy.md): evidence, conflicts and accuracy.
- [Phase three](architecture/03-complete-product-implementation.md): complete product capabilities.
- [Document adaptation and text routing](architecture/04-document-adaptation-and-text-routing.md): lightweight document learning, native/scanned routing and template-guided repair.
- [Module boundaries and engineering structure](architecture/05-module-boundaries-and-directory-layout.md): modular monolith, dependencies, contracts and fact ownership.

- [Format pipelines and human conversion](architecture/06-format-pipelines-and-human-conversion.md): independent branches and the conversion channel awaiting integration.

## Execution plans

- [System2 completion priorities](plans/03-system2-completion.md): Excel/HTML, workbench integration, pending PDF accuracy and near-term experiments.

- [Modular migration](plans/01-modular-migration-plan.md): checkpoints, success gates and stop conditions.

## Phase objectives

- [`02-phase-two-goal.md`](goals/02-phase-two-goal.md)
- [`03-phase-three-goal.md`](goals/03-phase-three-goal.md)

## Acceptance records

- [First priority-completion round](reports/10-system2-priority-pass.md): failure propagation, review transactions, environment recovery and real-window semantic repairs.

- [Phase three implementation and acceptance record](reports/03-方案三实施与验收记录.md)
- [Modular refactoring record](reports/05-模块化重构实施记录.md): boundaries, compatible migration, validation and environment blockers.

Current engineering state and the next experiment belong to [PROJECT_STATE.md](../PROJECT_STATE.md).

- [Governed source-intake contract](contracts/source-intake.md)
- [PDF review transaction contract](contracts/review-transactions.md)
- [Near-term engineering plan](plans/02-source-intake-engineering.md)
- [Validation and merge handoff](reports/06-source-intake-engineering.md)

- [Non-PDF targeted regression](reports/07-nonpdf-module-regression.md)

- [System1 multi-template HTML experiment](reports/08-html-template-matrix.md)


The HTML v2 implementation target is complete across five families with independent verification. Evidence, upstream intake state and boundaries belong to the [completion report](reports/09-html-parser-completion.md).

- [Excel Canonical v1](contracts/excel-document-v1.md): original XLSX values, formulas, hidden structure and independent checks.

- [Non-PDF priority implementation](reports/11-nonpdf-priority-pass.md).

- [Excel/HTML relationship and verification repairs](reports/12-nonpdf-structure-integrity.md).

- [Source-clause projection contract](contracts/source-records-v1.md): read-only fields, locations, residual content and version binding.
- [Clause mapping and System1 intake acceptance](reports/13-nonpdf-source-records.md).

- [Source-content projection v2](contracts/source-records-v2.md): ASC, five HTML families and annex structure; v1 remains compatible.
- [Excel/HTML content completion](reports/14-nonpdf-content-completion.md): INCLUDE scope, original comparisons and seven directory-page failures.
- [Canva flowchart delivery](reports/15-system2-canva-flowchart.md): editable process diagram, detailed PDF branches and verified delivery boundaries.
