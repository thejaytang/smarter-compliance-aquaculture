"""Local JSON bridge. Execute only with System1's own interpreter/environment."""
from __future__ import annotations
import contextlib
import hashlib
import io
import json
import sys
from pathlib import Path
from urllib.parse import urlsplit
from openpyxl import load_workbook
import human_operations as h
import source_updater as u
from system1.workbook_guard import exclusive_process_lock
from system1.cli import run_cycle


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def read(config_path):
    cfg = u.read_config(config_path)
    wb = load_workbook(cfg["workbook"])
    src = wb[cfg["sheet_name"]]
    sh = u.workbook_headers(src, 2)
    sources = {}
    for r in range(3, src.max_row + 1):
        rec = u.record_from_row(src, r, sh)
        if rec.get("source_id"):
            rec["effective_selection"] = u.selection_from_scores(rec)
            rec["source_revision"] = h.source_record_fingerprint(rec)
            sources[rec["source_id"]] = rec
    ops = wb[h.human_sheet_name(cfg)]
    oh = h.operation_headers(ops)
    tasks, history = [], []
    for r in range(3, h.last_operation_row(ops, oh) + 1):
        op = h.operation_record(ops, r, oh)
        if not op.get("operation_id"):
            continue
        payload = h.parse_payload(op["payload_json"])
        op["revision"] = digest(op)
        op["source"] = sources.get(op.get("source_id"), {})
        op["source_revision"] = op["source"].get("source_revision", "")
        op["human_issue"] = payload.get("human_reported_issue")
        op["is_open"] = op.get("program_status") in h.OPEN_STATUSES
        (tasks if op["is_open"] else history).append(op)
    wb.close()
    return {"sources": list(sources.values()), "tasks": tasks, "history": history,
            "revision": digest({"sources": sources, "tasks": tasks}),
            "counts": {"sources": len(sources), "tasks": len(tasks),
                       "snapshots": sum(s.get("snapshot_status") == "STORED" for s in sources.values()),
                       "included": sum(s["effective_selection"] == "INCLUDE" for s in sources.values()),
                       "excluded": sum(s["effective_selection"] == "EXCLUDE" for s in sources.values())}}


def safe_url(value):
    parsed = urlsplit(value)
    if parsed.scheme not in {"https", "http"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("请输入有效的 http(s) 来源链接。")
    return value


def apply(config_path, req):
    actor = str(req.get("actor", "")).strip()
    if not actor or len(actor) > 100:
        raise ValueError("请先选择操作人。")
    request_id = str(req["request_id"])
    cfg = u.read_config(config_path)
    # The request is first durably staged inside the workbook. A retry finds it by ID.
    with exclusive_process_lock(cfg["log_root"] / ".system1-run.lock"):
        with u.updater_lock(cfg["workbook"], 12):
            wb = load_workbook(cfg["workbook"])
            ops = wb[h.human_sheet_name(cfg)]
            oh = h.operation_headers(ops)
            staged = None
            for row in range(3, h.last_operation_row(ops, oh) + 1):
                existing = h.operation_record(ops, row, oh)
                ep = h.parse_payload(existing.get("payload_json"))
                if request_id in ep.get("workbench_receipts", []) or ep.get("workbench_applied") == request_id:
                    staged = row
                    break
                if ep.get("workbench_request") == request_id:
                    staged = row
            if staged is None:
                index = h.operation_index(ops, oh)
                if req["task_id"] not in index:
                    raise ValueError("STALE: 待办已变化，请刷新后重新核对。")
                row = index[req["task_id"]]
                old = h.operation_record(ops, row, oh)
                if digest(old) != req["revision"] or old["program_status"] not in h.OPEN_STATUSES:
                    raise ValueError("STALE: 待办已变化，已保留原决定，请刷新后重新核对。")
                src = wb[cfg["sheet_name"]]
                sh = u.workbook_headers(src, 2)
                sr = h.find_source_row(src, sh, old["source_id"])
                if sr is not None and h.source_record_fingerprint(u.record_from_row(src, sr, sh)) != req["source_revision"]:
                    raise ValueError("STALE: 来源已变化，请刷新后核对原件。")
                payload = h.parse_payload(old.get("payload_json"))
                action = req["action"]
                note = str(req.get("note", "")).strip()
                if len(note) > 10000:
                    raise ValueError("备注过长。")
                fields = {"operator": actor, "operator_note": note, "checked_at": None}
                payload["workbench_request"] = request_id
                payload["retry_after_apply"] = False
                payload["human_reported_issue_resolved"] = req.get("issue_verified") is True
                if sr is not None:
                    payload["source_fingerprint"] = req["source_revision"]
                if action in {"assess", "exclude", "defer", "correct", "verify"}:
                    if old["operation_type"] not in {"SOURCE_REVIEW", "SELECTION_REVIEW"}:
                        raise ValueError("该任务需要专用的人工文件或抽查操作。")
                    fields["decision"] = "APPLY"
                    payload["action"] = "APPLY_FIELD_UPDATES"
                    if action == "assess":
                        scores = req.get("scores", {})
                        if set(scores) != set(u.SCORE_FIELDS) or any(v not in {"HIGH", "MEDIUM", "LOW"} for v in scores.values()):
                            raise ValueError("请明确完成全部五项评分。")
                        fields.update(scores)
                        selection = "EXCLUDE" if "LOW" in scores.values() else ("PENDING" if "MEDIUM" in scores.values() else "INCLUDE")
                        fields["operator_selection_decision"] = selection
                        fields["operator_note"] = note or "Human five-dimension assessment: " + json.dumps(scores)
                    elif action in {"exclude", "defer"}:
                        if not note:
                            raise ValueError("请说明移出或保持待定的原因。")
                        fields["operator_selection_decision"] = "EXCLUDE" if action == "exclude" else "PENDING"
                    elif action == "correct":
                        updates = req.get("updates", {})
                        allowed = {"official_url", "retrieval_url", "issuer", "version", "provenance_status",
                                   "acquisition_channel", "applicability_reference", "inclusion_rationale", "primary_source_id"}
                        if not updates or set(updates) - allowed:
                            raise ValueError("未提供有效的来源纠正字段。")
                        for key, val in updates.items():
                            if not isinstance(val, str) or len(val) > 4000:
                                raise ValueError("字段内容无效。")
                            if key.endswith("_url"):
                                safe_url(val)
                            fields[key] = val
                        fields["operator_note"] = note or "Human source-field correction; existing snapshot retained."
                    else:
                        if not req.get("issue_verified") or not note:
                            raise ValueError("请核对原件，并填写解决问题的依据。")
                        fields["operator_note"] = note
                    if not fields["operator_note"]:
                        fields["operator_note"] = "Human source review completed."
                elif action == "qa":
                    verdict = req.get("verdict")
                    if old["operation_type"] != "RANDOM_QA_CHECK":
                        raise ValueError("该任务不是随机抽查。")
                    if verdict not in {"CORRECT", "INCORRECT"}:
                        raise ValueError("请选择抽查结果。")
                    fields["decision"] = verdict
                    if verdict == "INCORRECT" and not note:
                        raise ValueError("请说明发现的问题。")
                elif action == "manual":
                    if not req.get("identity_verified") or not req.get("permission_verified"):
                        raise ValueError("请确认文件身份、完整性和使用权限。")
                    staged_path = Path(req["upload_path"]).resolve()
                    upload_root = Path(req["upload_root"]).resolve()
                    if staged_path.parent != upload_root or not staged_path.is_file() or u.sha256_file(staged_path) != req["upload_hash"]:
                        raise ValueError("暂存文件已变化，请重新选择。")
                    if sr is None:
                        raise ValueError("当前入口仅接受已登记来源的原件。")
                    extension = staged_path.suffix.lower()
                    size = staged_path.stat().st_size
                    if size > cfg["max_bytes"]:
                        raise ValueError("文件超过来源大小上限。")
                    if extension == ".pdf":
                        u.validate_pdf(staged_path, size, cfg["minimum_pdf_bytes"])
                    elif extension in {".html", ".htm"}:
                        u.validate_html(staged_path, size, cfg["minimum_html_bytes"])
                    elif extension == ".xlsx":
                        u.validate_zip_container(staged_path, size, cfg["minimum_binary_bytes"], require_xlsx=True)
                    else:
                        raise ValueError("支持 PDF、HTML 和 XLSX 原件。")
                    # Stable unique name; intake and historical files are never overwritten.
                    import shutil
                    intake_name = "workbench_" + request_id + extension
                    target = cfg["manual_intake_root"] / intake_name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    if target.exists() and u.sha256_file(target) != req["upload_hash"]:
                        raise ValueError("暂存文件冲突。")
                    if not target.exists():
                        shutil.copy2(staged_path, target)
                    fields.update(operation_type="MANUAL_FILE_REPLACEMENT", decision="APPLY",
                                  intake_file=intake_name, file_format="html" if extension in {".html", ".htm"} else extension[1:])
                    fields["operator_note"] = note or "Human confirmed authorised original, identity and completeness."
                    payload.update(action="APPLY_FIELD_UPDATES", intake_file=intake_name,
                                   manual_file_format=fields["file_format"])
                else:
                    raise ValueError("不支持的操作。")
                fields["payload_json"] = json.dumps(payload, ensure_ascii=False, sort_keys=True)
                h.set_operation_fields(ops, row, oh, fields)
                h.prepare_human_workbook(wb, ops, oh)
                u.create_backup(cfg["workbook"], cfg["backup_root"], u.local_now(cfg))
                u.save_workbook_atomic(wb, cfg["workbook"], u.workbook_mtime(cfg["workbook"]))
            wb.close()
    # Explicit browser action applies automatically, with no full source check.
    with contextlib.redirect_stdout(io.StringIO()):
        code, result = run_cycle(config_path, full=False)
    if code:
        return {"status": "blocked", "message": result["message"]}
    wb = load_workbook(cfg["workbook"])
    ops = wb[h.human_sheet_name(cfg)]
    oh = h.operation_headers(ops)
    for r in range(3, h.last_operation_row(ops, oh) + 1):
        op = h.operation_record(ops, r, oh)
        payload = h.parse_payload(op.get("payload_json"))
        if payload.get("workbench_request") == request_id:
            wb.close()
            if payload.get("workbench_applied") == request_id:
                return {"status": "applied", "message": "决定已写入，来源待办及统计已更新。"}
            return {"status": "blocked", "message": op.get("program_note") or "需要补充人工信息。"}
    wb.close()
    raise ValueError("未找到系统回执；请保留此请求并检查日志。")


def artifact(config_path, source_id):
    cfg = u.read_config(config_path)
    source = next((s for s in read(config_path)["sources"] if s["source_id"] == source_id), None)
    if not source:
        raise ValueError("来源不存在。")
    root = cfg["source_root"].resolve()
    path = (root / str(source["folder_code"]) / str(source["stored_filename"])).resolve()
    if root not in path.parents or not path.is_file():
        raise ValueError("当前没有可用的本地原件。")
    return {"path": str(path), "filename": path.name, "hash": source.get("content_hash")}


def main():
    message = json.load(sys.stdin)
    config = Path(message["config"])
    try:
        if message["command"] == "read":
            result = read(config)
        elif message["command"] == "random_qa":
            cfg = u.read_config(config)
            with exclusive_process_lock(cfg["log_root"] / ".system1-run.lock"):
                result = h.generate_random_qa(config)
        elif message["command"] == "artifact":
            result = artifact(config, message["source_id"])
        elif message["command"] == "apply":
            result = apply(config, message["request"])
        else:
            raise ValueError("Unknown bridge command")
        print(json.dumps({"ok": True, "data": result}, default=str))
    except Exception as exc:
        # All human errors are retained by the workbench request journal.
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
