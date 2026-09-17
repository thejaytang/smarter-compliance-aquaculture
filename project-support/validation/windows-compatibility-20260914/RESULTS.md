# Windows compatibility verification, 2026-09-14

## Scope

Portable fixes were prepared on Windows with Python 3.12.10, based on source commit `5f01f1a0611c207567a22e395ccbf33be9b3315f`. Runtime databases, reviewer records, source originals, environment binaries and migration helpers are not part of this change. Setup instructions belong to [ENVIRONMENT.md](../../ENVIRONMENT.md).

## Failures and corrections

- SQLite context managers commit or roll back but do not close connections. Component-owned closing connections now release handles deterministically, including backup readers, so Windows can rename/delete temporary stores without changing transaction semantics. Regression tests check persisted commits, rollback, closed handles and file removal.
- The Unix-only `resource` import blocked System2 startup. A platform helper uses Windows process-memory counters and retains the macOS/Linux unit conversions and peak-memory budget checks.
- Windows drive anchors, snapshot backslashes and relative launcher paths caused validation or child-process lookup failures. Drive roots are recognized, snapshot identifiers use POSIX separators, and launcher roots resolve before changing directory.
- Flushing a generated workbook from a read-only descriptor failed on Windows. The existing temporary workbook is opened read/write before `fsync` and atomic replacement.
- Windows socket reuse could bind the same local port twice. The Windows server now requests exclusive address use and retains the existing fallback-port behavior.
- Windows lacks the system timezone database used on macOS. Workbench declares a Windows-only pinned `tzdata` dependency. Launch/setup scripts use UTF-8 and discover component-owned portable tools.
- Large review lists exceeded the existing latency check. Covering/partial indexes and bounded ancestor query join order avoid repeatedly scanning large JSON records. Existing legacy stores receive the indexes when opened; human records are not rewritten by this index upgrade.
- Git newline conversion changed hash-bound originals and bundled reader assets. Attributes preserve those bytes and define Python/shell LF and Windows batch CRLF checkout rules. Existing affected checkouts need verified original-byte recovery separately.

## Evidence and limits

The migrated deployment completed these suites before publication; the publication copy retains the same executable code and existing tests, with line endings normalized:

| Check | Windows result |
| --- | --- |
| System1 full suite | 168 passed |
| Workbench full suite | 209 passed |
| Frontend state suite | 238 passed |
| System2 full suite | 1,136 passed, 1 skipped |
| Restored historical fixture subset | 99 passed (overlaps System2 coverage) |

System2 reported one existing Starlette/httpx deprecation warning. The restored-workspace browser check loaded Source review and a material original, waited for actual iframe content, and recorded no JavaScript errors or failed HTTP responses. Runtime workers were paused for that restored-data inspection; it does not establish scheduled-worker acceptance. Detailed migration logs and screenshots remain local because they reference the restored workspace and business data.

Publication additionally passed 105 focused checks against the isolated source copy: 81 System2, 23 Workbench and one System1 check. These include five new platform-memory tests covering native Windows counters, query failure and macOS/Linux units. The published Python fixes match the full-suite-tested deployment byte-for-byte after newline normalization. This is Windows engineering evidence. It is not a fresh macOS test, multi-computer reviewer round trip, universal extraction-accuracy acceptance, or proof that the still-incremental historical data release is complete. Keep prior scoped acceptance records and reviewer protections in force.
