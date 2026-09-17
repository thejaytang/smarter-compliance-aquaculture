"""Read-only scheduling hint from System2's authoritative candidate states.

The owning System2 service rechecks all state before processing or resolution.
Read failures propagate to runtime status; they never mean there is no work.
"""
from pathlib import Path
from backend.shared.sqlite_support import connect


def pending_work(runtime):
    path = (Path(runtime) / 'workflow.sqlite').resolve()
    with connect(path.as_uri() + '?mode=ro', uri=True, timeout=1) as db:
        states = {row[0] for row in db.execute(
            "SELECT DISTINCT json_extract(data,'$.status') FROM material_candidates "
            "WHERE json_extract(data,'$.status') IN ('running','ready','partial')")}
    return {'run': 'running' in states, 'resolve': bool(states & {'ready', 'partial'})}
