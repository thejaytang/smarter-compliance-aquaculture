# Material idle dispatch: partial performance fix

Date: 2026-09-17. Baseline: `6808e30e91d048eb076bddf8925b7be65c97caa3` on `developing-only-jay`.

Historical result, superseded on 2026-09-18 by the Windows implementation integrated through `main`. The original helper and checks are retained in `retired-source/` for reproduction only; they are no longer active application modules or default tests. Current validation is in [Windows/Mac synchronization](../windows-sync-20260918/RESULTS.md).

## 1. Status and scope

The supplied Windows handoff describes uncommitted fixes, 14-second material opens and repeated component process starts. The user confirmed that those code changes still exist only on Windows. This Mac checkout has neither `operation_gate.py` nor the named Windows diagnostic reports. Those changes have not been merged or reimplemented.

Host inspection found Darwin arm64, no Parallels/UTM/VMware/VirtualBox/QEMU/Wine installation in the checked locations or executable paths, and no connected Windows execution tool. Docker CLI is present but its daemon is unavailable. There is no Windows run result for this patch. Platform simulation is not labelled Windows acceptance.

## 2. Implemented locally

- A standard-library, read-only System2 activity contract reads the durable candidate table through the existing personal-branch storage mapping.
- Verified empty/finished queues skip both `material_tick` and `material_repeat-resolution` component processes.
- Running candidates retain the original extraction path; ready/partial candidates retain resolution checks without launching an idle parser. Newly produced candidates can be resolved in the same tick.
- Missing schema is unknown and falls back to System2. Read/corruption errors propagate. No boolean memory flag can hide a later durable submission or resumed job.
- No schema migration, seed import, business-file rewrite, threshold change or lock removal. Normal service has not been restarted onto this partial patch.

## 3. Actual validation

65 focused unittest checks pass on macOS: activity scheduling, material queue categories, runtime status, material HTTP boundaries, inspection scheduling, collaboration identity, SQLite lifecycle, imports and application file boundaries.

The additional real-component profile creates its own temporary material database. Across three rounds, the prior idle dispatch made six component calls; the guarded dispatch made zero. Median round duration was 335.403 ms before and 0.211 ms after on this Mac. Both fixture database hashes remained unchanged. See [macos-idle-profile.json](macos-idle-profile.json).

These timings measure idle scheduling only. They do not measure browser opens, Windows performance, long parsing, contention or complete Collaboration acceptance.

## 4. Windows handoff and remaining work

First obtain the Windows code diff, all new source files (particularly `operation_gate.py`), and the named diagnostic reports. Integrate from the shared baseline while preserving both sides' changes. Do not replace whole source files over Windows modifications, restore initial data, replace a database or clear runtime state.

The source handoff archive contains the baseline and changed collaboration file, the new helper and tests, the portable isolated profiler, a contract diff, checksums and instructions. It contains no workspace database, source original, secret, environment or runtime state.

Then run the native Windows isolated checks and measure real browser list/open/reopen/save/reopen operations with background jobs. Record lock waiting, component round trips, process counts and original-preview latency separately. Persistent component processes, combined version-bound reads and asynchronous preview loading remain pending measurements and integration. No commit or push was performed for this task.
