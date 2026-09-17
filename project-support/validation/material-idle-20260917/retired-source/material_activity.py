"""Read-only System2 queue contract for the application scheduler.

This is a scheduling hint, never authority to execute or resolve a candidate.
System2 rechecks the durable candidate and its source before doing any work.
No parser imports, environment startup, schema creation or business writes occur.
"""
from pathlib import Path

from backend.shared.sqlite_support import connect


def material_activity(runtime):
    """Skip only a verified idle queue; leave uninitialized stores to System2.

    Routed personal branches use the existing storage mapping. Errors reading an
    existing store propagate to runtime monitoring rather than hiding saved jobs.
    A submission immediately after this read is discovered on the next tick.
    """
    runtime = Path(runtime).resolve()
    path = runtime / 'workflow.sqlite'
    if not path.exists() and not (runtime / '.storage.json').is_file():
        return {'known': False, 'extract': False, 'resolve': False}
    with connect(path.as_uri() + '?mode=ro', uri=True, timeout=1) as db:
        db.execute('PRAGMA query_only=ON')
        if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                          ('material_candidates',)).fetchone():
            return {'known': False, 'extract': False, 'resolve': False}
        # Read the owning table, not a possibly absent/stale display projection.
        extract = db.execute("SELECT 1 FROM material_candidates WHERE "
                             "json_extract(data,'$.status')='running' LIMIT 1").fetchone()
        resolve = db.execute("SELECT 1 FROM material_candidates WHERE "
                             "json_extract(data,'$.status') IN ('ready','partial') LIMIT 1").fetchone()
        return {'known': True, 'extract': bool(extract), 'resolve': bool(resolve)}
