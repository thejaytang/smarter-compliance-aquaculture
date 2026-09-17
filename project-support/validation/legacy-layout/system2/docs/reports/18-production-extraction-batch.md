# Production System1 to System2 batch | 2026-09-09

Status: RUNNING. This record does not assert completion of extraction or review.

The user requested: “可以，现在运行这个项目，从system1里面提取到system2”. The governed intake adapter read effective INCLUDE selections and verified all 38 local source snapshots. There are 37 HTML sources and one 134-page PDF (CS004); no effectively included XLSX sources. Two explicit start requests queued HTML followed by PDF, attributed to agent execution authorized by the user, without manufacturing a human content or Requirement decision.

Batch directory: `runtime/workflow/batches/production-20260909T123536Z/`. It retains `batch.json`, `html-request.json`, `pdf-request.json` and a timestamped `progress.json` readback. Workflow SQLite is the live state authority; progress.json is a snapshot. Original sources and the System1 registry remain unchanged.

The active workbench and the bounded batch driver share the worker file lock, so at most one parser executes at a time. Already-started jobs persist and resume from checked page windows. First-stage outputs enter human review; no local result bypasses acceptance or automatically becomes a System3-ready Requirement.

Large-source Excel synchronization is slow: many repeated evidence locators and structure/dependency references produced a workbook exceeding 100 MB before all sources were parsed. The populated browser queue and a completed register refresh were observed; further refreshes can lag. Preserve evidence and correct the read-model performance separately. This run is not a completed performance acceptance.

Latest observed snapshot: `{"as_of": "2026-09-09T12:41:50.205326+00:00", "states": {"queued": 25, "waiting_review": 11, "failed": 2}, "content_units": 17450, "published": 0}`.

Registry SHA256: `7beb2c9d63afcf693f41b3440b3ed3bb3cb7dd350b149480957d4f2901b8d041`.
