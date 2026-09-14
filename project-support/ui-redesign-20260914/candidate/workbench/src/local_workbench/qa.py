"""Read-only weekly QA projection from each system's governed audit evidence."""
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

SYSTEMS = (("system1", "System1"), ("system2a", "System2 A"), ("system2b", "System2 B"), ("system3", "System3 · off"))


def weekly_dashboard(snapshot, as_of):
    today = datetime.fromtimestamp(as_of, ZoneInfo("Europe/Oslo")).date()
    monday = today - timedelta(days=today.weekday())
    weeks = [(monday - timedelta(weeks=n)).isoformat() for n in range(4, -1, -1)]
    groups = {week: {} for week in weeks}
    sizes = {}
    findings=set()
    for record in snapshot.get('tasks',[]):
        try:payload=json.loads(record.get('payload_json') or '{}')
        except (ValueError,TypeError):continue
        evidence=payload.get('human_reported_issue',{}).get('evidence_id')
        if evidence:findings.add(evidence)
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
            open_findings=sum(r['operation_id'] in findings for r in rows)
            shortfall=max(0,5-sampled)
            complete = sampled==5 and len(reviewed) == sampled and len(rows) == sampled and not open_findings
            points.append({"week": week, "sampled": sampled, "reviewed": len(reviewed), "correct": correct,
                           "accuracy": round(correct / sampled * 100, 1) if complete else None,
                           'shortfall':shortfall,'open_findings':open_findings,
                           "status": "not_connected" if key != "system1" else "complete" if complete else "pending" if rows else "no_eligible" if week in sizes else "no_batch"})
        series.append({"key": key, "label": label, "connected": key == "system1", "points": points})
    return {"weeks": weeks, "series": series, "target_size": 5, "timezone": "Europe/Oslo",
            "open_source_ids": sorted({r["source_id"] for r in snapshot.get("tasks", [])
                                       if r.get("operation_type") == "RANDOM_QA_CHECK"})}


def with_sampling(chart, sampling):
    """A/B share the Monday axis; legacy machine-only data stay in history."""
    for stage,key in [('A','system2a'),('B','system2b')]:
        series=next(s for s in chart['series'] if s['key']==key)
        enabled=bool(sampling.get('schedule',{}).get('enabled'))
        series['connected']=enabled
        batches={b['week']:b for b in sampling.get('batches',[]) if b['stage']==stage}
        for point in series['points']:
            batch=batches.get(point['week'])
            if batch:
                items=batch['items']
                point.update(sampled=batch['sampled'],reviewed=sum(i['status']=='complete' for i in items),
                    correct=sum(i['verdict']=='CORRECT' for i in items),shortfall=batch['shortfall'],
                    open_findings=sum(i['status']=='finding_open' for i in items),missing_strata=batch['missing_strata'],
                    accuracy=round(batch['agreement']*100,1) if batch['agreement'] is not None else None,
                    status='complete' if batch['complete'] else 'pending')
            else:point['status']='no_batch' if enabled else 'not_enabled'
    chart['targets']={'system1':5,'system2a':20,'system2b':5,'system3':0}
    return chart
