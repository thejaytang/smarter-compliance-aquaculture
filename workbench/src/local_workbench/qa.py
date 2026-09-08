"""Read-only weekly QA projection from each system's governed audit evidence."""
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

SYSTEMS = (("system1", "System1"), ("system2", "System2"), ("system3", "System3"))


def weekly_dashboard(snapshot, as_of):
    today = datetime.fromtimestamp(as_of, ZoneInfo("Europe/Oslo")).date()
    monday = today - timedelta(days=today.weekday())
    weeks = [(monday - timedelta(weeks=n)).isoformat() for n in range(4, -1, -1)]
    groups = {week: {} for week in weeks}
    sizes = {}
    for record in snapshot.get("tasks", []) + snapshot.get("history", []):
        if record.get("operation_type") not in {"RANDOM_QA_CHECK", "RANDOM_QA_BATCH_SUMMARY"}:
            continue
        try:
            payload = json.loads(record.get("payload_json") or "{}")
        except (ValueError, TypeError):
            continue
        week = payload.get("batch_week")
        if week in groups and record.get("operation_type") == "RANDOM_QA_BATCH_SUMMARY":
            sizes[week] = payload.get("sampled_count", 0)
            continue
        if week in groups:
            groups[week][record["operation_id"]] = record
    series = []
    for key, label in SYSTEMS:
        points = []
        for week in weeks:
            rows = list(groups[week].values()) if key == "system1" else []
            reviewed = [r for r in rows if r.get("operator") and r.get("program_status") == "APPLIED"
                        and r.get("decision") in {"CORRECT", "INCORRECT"}]
            correct = sum(r["decision"] == "CORRECT" for r in reviewed)
            sampled = sizes.get(week, len(rows)) if key == "system1" else 0
            complete = bool(sampled) and len(reviewed) == sampled and len(rows) == sampled
            points.append({"week": week, "sampled": sampled, "reviewed": len(reviewed), "correct": correct,
                           "accuracy": round(correct / sampled * 100, 1) if complete else None,
                           "status": "not_connected" if key != "system1" else "complete" if complete else "pending" if rows else "no_eligible" if week in sizes else "no_batch"})
        series.append({"key": key, "label": label, "connected": key == "system1", "points": points})
    return {"weeks": weeks, "series": series, "target_size": 5, "timezone": "Europe/Oslo",
            "open_source_ids": sorted({r["source_id"] for r in snapshot.get("tasks", [])
                                       if r.get("operation_type") == "RANDOM_QA_CHECK"})}
