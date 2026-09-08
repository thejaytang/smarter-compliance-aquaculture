"""Requirement workstream overview, with metrics scoped to their owning system."""
from collections import Counter
from .qa import weekly_dashboard


def build_dashboard(snapshot, as_of):
    sources = snapshot["sources"]
    tasks = snapshot["tasks"]
    source_ids = {s["source_id"] for s in sources}
    pending_ids = sorted({t["source_id"] for t in tasks})
    selections = Counter(s.get("effective_selection", "UNKNOWN") for s in sources)
    folders = Counter(s.get("folder_code") or "Other" for s in sources)
    folder_names = {"A_Public_Authority":"Public authorities", "B_Standards_Body":"Standards bodies", "C_Certification_Scheme":"Certification schemes"}
    reasons = [
        ("scores", "Source ratings needed", lambda t: "SELECTION_PENDING" in (t.get("trigger") or "")),
        ("files", "Original needed", lambda t: "PAYWALL_BLOCKED" in (t.get("trigger") or "") or t.get("source", {}).get("snapshot_status") != "STORED"),
        ("human", "Reviewer feedback to verify", lambda t: bool(t.get("human_issue"))),
        ("links", "Duplicate source links", lambda t: "DUPLICATE_OFFICIAL_URL" in (t.get("trigger") or "")),
    ]
    issue_groups = []
    for key, label, predicate in reasons:
        ids = sorted({t["source_id"] for t in tasks if predicate(t)})
        issue_groups.append({"key":key, "label":label, "count":len(ids), "source_ids":ids})
    stored = sum(s.get("snapshot_status") == "STORED" for s in sources)
    return {
        "scope": "requirement_workstream",
        # These are the current workbench connections, not parser capability claims.
        # Demo activity never becomes a production metric or a completed review.
        "systems": [
            {"key": "system1", "label": "System1", "title": "Source management",
             "purpose": "Select and maintain trustworthy original sources.",
             "availability": "live", "status": "Live review", "review_connected": True,
             "pending": {"label": "Sources awaiting review", "value": len(pending_ids)},
             "metrics": [{"label": "Registered sources", "value": len(source_ids)},
                         {"label": "Included sources", "value": selections["INCLUDE"]}],
             "note": "Review source ratings, original files and reported issues.",
             "action": {"label": "Review sources", "view": "system1"}},
            {"key": "system2", "label": "System2", "title": "Extraction review",
             "purpose": "Check extracted requirements against the original document.",
             "availability": "demo", "status": "Review demo", "review_connected": False,
             "pending": {"label": "Review items awaiting review", "value": None},
             "metrics": [{"label": "Documents parsed", "value": None},
                         {"label": "Requirements extracted", "value": None}],
             "note": "Live results are not connected here yet. Demo activity stays separate.",
             "action": {"label": "Open review demo", "view": "system2"}},
            {"key": "system3", "label": "System3", "title": "Semantic enrichment",
             "purpose": "Prepare source-backed requirements for the Site Model.",
             "availability": "design", "status": "In design", "review_connected": False,
             "pending": {"label": "Enrichment items awaiting review", "value": None},
             "metrics": [{"label": "Requirements enriched", "value": None},
                         {"label": "Ready for Site Model", "value": None}],
             "note": "The review workflow is in design. Live results are not connected.",
             "action": {"label": "View System3", "view": "system3"}},
        ],
        "as_of": as_of,
        "weekly_qa": weekly_dashboard(snapshot, as_of),
        "counts": {"sources":len(source_ids), "pending":len(pending_ids), "stored":stored,
                   "included":selections["INCLUDE"], "missing":len(sources)-stored},
        "selection": [{"key":key,"label":label,"count":selections[key]}
                      for key,label in [("INCLUDE","Included"),("PENDING","Pending"),("EXCLUDE","Excluded")]]
                     + ([{"key":"UNKNOWN","label":"Unclassified","count":sum(v for k,v in selections.items() if k not in {"INCLUDE","PENDING","EXCLUDE"})}]
                        if any(k not in {"INCLUDE","PENDING","EXCLUDE"} for k in selections) else []),
        "categories":[{"key":key,"label":folder_names.get(key,key),"count":count}
                      for key,count in sorted(folders.items())],
        "issues":issue_groups,
        "priority":[{"source_id":t["source_id"],"title":t.get("source_title") or t["source_id"],
                     "task_id":t["operation_id"],"human_issue":bool(t.get("human_issue"))}
                    for t in sorted(tasks,key=lambda t: (not bool(t.get("human_issue")),t.get("created_at") or ""))[:5]],
        "notes":["Counts use source IDs. Stored originals are not necessarily verified.", "Review reasons overlap and cannot be added to obtain a source total."],
    }
