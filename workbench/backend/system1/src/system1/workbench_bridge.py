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
from system1.source_assessment import Assessments, ConfiguredProvider


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def read(config_path):
    cfg = u.read_config(config_path)
    from .governance_store import authority_version
    version = authority_version(cfg) if cfg.get('governance_db') else None
    wb = u.open_registry(cfg, data_only=bool(cfg.get('governance_db')))
    database_revision = getattr(wb, '_governance_revision', None)
    src = wb[cfg["sheet_name"]]
    sh = u.workbook_headers(src, 2)
    sources = {}
    for r in range(3, src.max_row + 1):
        rec = u.record_from_row(src, r, sh)
        if rec.get("source_id"):
            rec["effective_selection"] = u.selection_from_scores(rec)
            from .source_integrity import original_ready
            if rec["effective_selection"]=="INCLUDE" and not original_ready(cfg,rec):rec["effective_selection"]="PENDING"
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
        if payload.get('basic_inspection'):
            op['basic_inspection']=payload['basic_inspection']
            if op.get('source_id') in sources and payload['basic_inspection'].get('content_hash')==sources[op['source_id']].get('content_hash'):
                sources[op['source_id']]['intake_inspection']=payload['basic_inspection']
        if op["operation_type"]=="NEW_SOURCE_CANDIDATE":op["candidate_fields"]={k:op.get(k) or payload.get(h.OPERATION_SOURCE_FIELD_MAP.get(k,k)) or "" for k in h.EDITABLE_CANDIDATE_FIELDS}
        op["is_open"] = op.get("program_status") in h.OPEN_STATUSES
        (tasks if op["is_open"] else history).append(op)
    wb.close()
    assessment_path = cfg.get('assessment_db', cfg['log_root'] / 'source-assessments.sqlite')
    if assessment_path.is_file():
        Assessments(assessment_path).project(list(sources.values()), tasks, history)
    from .selection_gate import project
    project(list(sources.values()),tasks)
    if version is not None and authority_version(cfg) != version:
        raise ValueError('STALE: governance or assessment changed during the read; retry.')
    return {"sources": list(sources.values()), "tasks": tasks, "history": history,
            "authority": {"kind": "sqlite" if database_revision is not None else "workbook",
                          "revision": database_revision,
                          "version": version,
                          "state_sha256": digest({"revision": database_revision, "sources": sources, "tasks": tasks, "history": history})},
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


def apply(config_path, req, *, scoped=False):
    actor = str(req.get("actor", "")).strip()
    if not actor or len(actor) > 100:
        raise ValueError("请先选择操作人。")
    request_id = str(req["request_id"])
    cfg = u.read_config(config_path)
    # Durably stage in the configured authority. A retry finds the same request ID.
    with exclusive_process_lock(cfg["log_root"] / ".system1-run.lock"):
        with u.registry_lock(cfg, 12):
            wb = u.open_registry(cfg)
            wb._governance_actor = actor
            ops = wb[h.human_sheet_name(cfg)]
            oh = h.operation_headers(ops)
            staged = None
            for row in range(3, h.last_operation_row(ops, oh) + 1):
                existing = h.operation_record(ops, row, oh)
                ep = h.parse_payload(existing.get("payload_json"))
                if request_id in ep.get("workbench_receipts", []) or ep.get("workbench_applied") == request_id:
                    if ep.get("workbench_request_digest") and ep["workbench_request_digest"] != digest(req):
                        raise ValueError("Request identity was reused for different content.")
                    staged = row
                    break
                if ep.get("workbench_request") == request_id:
                    if ep.get("workbench_request_digest") and ep["workbench_request_digest"] != digest(req):raise ValueError("Request identity was reused for different content.")
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
                request_digest = digest(req)
                note = str(req.get("note", "")).strip()
                if len(note) > 10000:
                    raise ValueError("备注过长。")
                fields = {"operator": actor, "operator_note": note, "checked_at": None}
                payload["workbench_request"] = request_id
                payload["workbench_request_digest"] = request_digest
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
                elif action == "retry":
                    if old["operation_type"] not in {"SOURCE_REVIEW", "SELECTION_REVIEW"} or not req.get('explicit_confirmation'):
                        raise ValueError("Explicit source retrieval confirmation is required.")
                    fields['decision']='ACCEPT';payload['action']='RETRY_SOURCE'
                elif action in {'candidate_accept','candidate_reject','task_defer','replacement_accept','replacement_reject'}:
                    expected='NEW_SOURCE_CANDIDATE' if action.startswith('candidate_') else 'MANUAL_FILE_REPLACEMENT'
                    if action!='task_defer' and old['operation_type']!=expected: raise ValueError('Action does not match this task.')
                    if not note: raise ValueError('Record the decision reason.')
                    fields['decision']='PENDING' if action=='task_defer' else ('ACCEPT' if action.endswith('accept') else 'REJECT')
                    if action=='task_defer':
                        fields['program_status']='WAITING_FOR_HUMAN';payload['workbench_applied']=request_id
                    updates=req.get('candidate_fields',{})
                    if not isinstance(updates,dict) or set(updates)-set(h.EDITABLE_CANDIDATE_FIELDS): raise ValueError('Unsupported candidate fields.')
                    for key,value in updates.items():
                        if not isinstance(value,str) or len(value)>4000 or value.startswith('='): raise ValueError('Invalid candidate field.')
                        if key.endswith('_url') and value:safe_url(value)
                    fields.update(updates)
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
                u.backup_registry(cfg, u.local_now(cfg))
                u.save_registry(wb, cfg, u.registry_revision(cfg))
            wb.close()
    # Explicit browser action applies automatically, with no full source check.
    with contextlib.redirect_stdout(io.StringIO()):
        if scoped:
            # Only this explicitly submitted operation is eligible to run.
            with exclusive_process_lock(cfg['log_root'] / '.system1-run.lock'):
                current = read(config_path)
                selected_ids = {op['operation_id'] for op in [*current['tasks'],*current['history']]
                    if h.parse_payload(op.get('payload_json')).get('workbench_request') == request_id}
                result = h.process_decisions(config_path, operation_ids=selected_ids)
            code = 0
        else:
            code, result = run_cycle(config_path, full=False)
    if code:
        return {"status": "blocked", "message": result["message"]}
    wb = u.open_registry(cfg)
    ops = wb[h.human_sheet_name(cfg)]
    oh = h.operation_headers(ops)
    for r in range(3, h.last_operation_row(ops, oh) + 1):
        op = h.operation_record(ops, r, oh)
        payload = h.parse_payload(op.get("payload_json"))
        if payload.get("workbench_request") == request_id:
            wb.close()
            if payload.get("workbench_applied") == request_id:
                return {"status": "applied", "message": (
                    "Decision saved. This source remains pending because unresolved checks still need attention."
                    if op.get("program_status") in h.OPEN_STATUSES else "决定已写入，来源待办及统计已更新。")}
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
        elif message['command'] == 'authority_version':
            from .governance_store import authority_version
            result = authority_version(u.read_config(config))
        elif message['command'] == 'export_status':
            cfg=u.read_config(config)
            if cfg.get('governance_db'):
                from .governance_export import status
                result=status(cfg)
            else:
                result={'status':'legacy_workbook','decisions':'workbook_owned'}
        elif message['command'] == 'export_snapshot':
            from .governance_export import cached
            result=cached(u.read_config(config))
        elif message["command"] == "random_qa":
            cfg = u.read_config(config)
            with exclusive_process_lock(cfg["log_root"] / ".system1-run.lock"):
                result = h.generate_random_qa(config)
        elif message["command"] == "artifact":
            result = artifact(config, message["source_id"])
        elif message['command'] == 'spreadsheet_preview':
            original=artifact(config,message['source_id']);path=Path(original['path'])
            if path.suffix.lower()!='.xlsx' or u.sha256_file(path)!=original['hash']:
                raise ValueError('The registered spreadsheet fingerprint is invalid.')
            formula=load_workbook(path,data_only=False);cached=load_workbook(path,data_only=True)
            try:
                sheet=formula[message.get('sheet') or formula.sheetnames[0]]
                row=max(1,int(message.get('row',1)));col=max(1,int(message.get('column',1)))
                cells=[]
                for rr in sheet.iter_rows(min_row=row,max_row=min(sheet.max_row,row+39),min_col=col,max_col=min(sheet.max_column,col+11)):
                    cells.append([{'address':c.coordinate,'value':c.value,'cached':cached[sheet.title][c.coordinate].value,
                        'hidden_row':bool(sheet.row_dimensions[c.row].hidden),
                        'hidden_column':any(d.hidden and (d.min or 0)<=c.column<=(d.max or 0) for d in sheet.column_dimensions.values())} for c in rr])
                result={'kind':'spreadsheet','sheet':sheet.title,'sheets':formula.sheetnames,'state':sheet.sheet_state,
                    'row':row,'column':col,'rows':sheet.max_row,'columns':sheet.max_column,'cells':cells,
                    'merged':[str(r) for r in sheet.merged_cells.ranges],
                    'label':'Original cells, formulas and saved caches. Hidden regions are included; this view does not recalculate formulas.'}
            finally:
                formula.close();cached.close()
        elif message['command']=='confidence_export':
            from .review_sync import confidence
            result=confidence(config)
        elif message['command']=='source_issue':
            from .review_sync import source_issue
            result=source_issue(config,message['request'])
        elif message['command']=='source_snapshot_apply':
            from .source_snapshot import apply as source_snapshot_apply
            result=source_snapshot_apply(config,message['request'])
        elif message['command']=='collaboration_apply':
            from .collaboration_review import collaboration_apply
            result=collaboration_apply(config,message['request'])
        elif message['command'] == 'workflow_apply':
            if message['request'].get('actor') != 'Weijie Tang' and not (message['request'].get('peer_sync') is True and message['request'].get('actor') in {'Ana Jokic','Daniel Restad'}): raise ValueError('Only the coordinator may apply source operations.')
            result = apply(config,message['request'],scoped=True)
        elif message['command'] == 'intake_original':
            from .source_workflow import intake_original
            result = intake_original(config,message['operation_id'])
        elif message['command'] == 'workflow_intake':
            from .source_workflow import intake
            result = intake(config,message['request'])
        elif message['command'] == 'workflow_reopen':
            from .source_workflow import reopen
            result = reopen(config,message['request'])
        elif message['command'] == 'source_review_preview':
            from .source_workflow import preview
            result = preview(config,message['request'])
        elif message["command"] == "apply":
            result = apply(config, message["request"])
        elif message['command'] == 'assessment_policy':
            cfg = u.read_config(config)
            result = Assessments(cfg.get('assessment_db', cfg['log_root'] / 'source-assessments.sqlite')).policy(message['revision'], message['threshold'])
        elif message['command'] == 'assessment_hold':
            cfg=u.read_config(config)
            result=Assessments(cfg.get('assessment_db', cfg['log_root']/'source-assessments.sqlite')).hold(message['source_id'],message['actor'])
        elif message['command'] == 'assess_sources':
            cfg = u.read_config(config)
            rules_path = config.parent / 'machine-assessment-rules.local.json'
            rules = json.loads(rules_path.read_text()) if rules_path.exists() else []
            records = read(config)['sources']
            owner = Assessments(cfg.get('assessment_db', cfg['log_root'] / 'source-assessments.sqlite'))
            provider_path=config.parent/'model-provider.local.json'
            try:
                provider_config=json.loads(provider_path.read_text()) if provider_path.exists() else {}
                provider=ConfiguredProvider(provider_config) if provider_config.get('enabled') else None
            except (ValueError,OSError,AttributeError):
                class InvalidProvider:
                    def assess(self,source):raise ValueError('provider_configuration_invalid')
                provider=InvalidProvider()
            selected = set(message['source_ids'])
            if not selected or selected - {s['source_id'] for s in records}:
                raise ValueError('Choose registered sources for assessment.')
            results=[]
            for source in records:
                if source['source_id'] not in selected:continue
                try:
                    original=artifact(config,source['source_id'])
                    source['_snapshot_verified']=u.sha256_file(Path(original['path']))==source.get('content_hash')
                except (ValueError,OSError):
                    source['_snapshot_verified']=False
                results.append(owner.evaluate(source,rules,provider))
            result = {'status':'applied','assessments':results}
        else:
            raise ValueError("Unknown bridge command")
        print(json.dumps({"ok": True, "data": result}, default=str))
    except Exception as exc:
        # All human errors are retained by the workbench request journal.
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
