"""Explicitly started, single-worker source processing with resumable PDF windows."""
from __future__ import annotations

import contextlib
from hashlib import sha256
import io
import json
from pathlib import Path
import sys
import uuid

from ..contracts.source import Snapshot
from ..platform_support import lock_file
from ..intake.system1 import read_system1
from ..intake.registry import build_manifest, read_snapshot
from ..review.workflow import Workflow
from ..contracts.hashing import digest
from ..domains.requirements.review_projection import content_units
def run_item(*args, **kwargs):
    from .source_batch import run_item as parse
    return parse(*args, **kwargs)


class Runner:
    def __init__(self, root, system1, system1_config=None):
        self.root = Path(root).resolve()
        self.system1 = Path(system1).resolve()
        self.system1_config = Path(system1_config) if system1_config else None
        self.store = Workflow(self.root)

    def handoff(self):
        return read_system1(self.system1, self.system1_config)

    def sampling_config(self):
        path=self.root/'weekly-sampling.json'
        if not path.is_file():path=Path(__file__).resolve().parents[3]/'config/weekly-sampling.json'
        config=json.loads(path.read_text())
        from ..review.weekly_sampling import SCHEMA, TARGETS
        if config.get('schema')!=SCHEMA or config.get('targets')!=TARGETS or not isinstance(config.get('enabled'),bool):
            raise ValueError('invalid_weekly_sampling_configuration')
        return config

    def sampling_tick(self):
        from ..review import weekly_sampling
        config=self.sampling_config()
        if not config['enabled']:return {'status':'disabled','targets':config['targets']}
        handoff=self.reconcile()
        return weekly_sampling.create_due(self.store,handoff.source_root,enabled=True,
            zone=config['timezone'],assert_current=handoff.assert_current)

    def workbook(self):
        from ..delivery.requirement_workbook import NAME, sync_workbook
        handoff = self.reconcile()
        component = Path(__file__).resolve().parents[3]
        target = (component if self.root == component / 'runtime/workflow' else self.root) / NAME
        return sync_workbook(self.store, handoff.records, handoff.registry_sha256, target, handoff.assert_current,
                             registry_kind=getattr(handoff,'evidence',{}).get('registry_kind','workbook'))

    def start(self, request):
        handoff = self.handoff()
        ids = request.get('source_ids', [])
        if not ids:
            raise ValueError('select_at_least_one_source')
        manifest = build_manifest(handoff.records, handoff.registry_sha256, handoff.source_root, set(ids))
        if manifest['rejected']:
            raise ValueError('source_intake_rejected:' + json.dumps(manifest['rejected']))
        handoff.assert_current()
        return self.store.enqueue(manifest['items'], request)

    def suggest(self, request):
        from ..domains.suggestions import Suggestions
        self.reconcile()
        with self.store.transaction() as db:
            replay=self.store._request(db,request)
            if replay is not None:return replay
            doc=self.store._load(db,request['document_id'])
            if doc['revision']!=request['revision'] or not doc['eligible']:
                raise ValueError('stale_or_ineligible_suggestion_target')
            unit=next((u for u in doc['units'] if u['id']==request['unit_id']),None)
            if unit is None:raise ValueError('unit_not_found')
        # No network operation holds the review write lock.
        path=Path(__file__).resolve().parents[3]/'config/model-provider.local.json'
        try:
            config=json.loads(path.read_text()) if path.is_file() else {'enabled':False}
            capability='requirement_candidates' if unit['content_status'] in {'human_accepted','machine_accepted'} else 'structure_review'
            result=Suggestions(config).propose(capability,[{'id':doc['id']+':'+unit['id'],
                'source_sha256':doc['source']['content_hash'],'content':self.store.resolved(unit,{u['id']:u for u in doc['units']})}])
        except (ValueError,OSError):
            result={'mode':'NO_API_FALLBACK','suggestions':[],'error_type':'configuration_invalid'}
        with self.store.transaction() as db:
            replay=self.store._request(db,request)
            if replay is not None:return replay
            current=self.store._load(db,doc['id'])
            if current['revision']!=request['revision']:
                raise ValueError('suggestion_result_stale')
            target=next(u for u in current['units'] if u['id']==unit['id'])
            target['suggestions']=result
            self.store._event(db,doc['id'],'suggestions',{'actor':request['actor'],'unit_id':unit['id'],**result})
            self.store._save(db,current)
            from ..review.browser_view import guard
            from ..review import row_store
            return self.store._receipt(db,request,{'status':'applied',**result,**({'guard':guard(db,current,unit['id'])} if row_store.enabled(db) else {})})

    def verify_page(self, request):
        from ..review.source_verification import verify_page
        with self.store.connect() as db:
            doc = self.store._load(db, request['document_id'])
        handoff = self.reconcile(doc['source']['source_id'])
        source = Snapshot(**doc['source'])
        read_snapshot(source, handoff.source_root)
        handoff.assert_current()
        # Historical results do not yet carry complete verifier-engine lineage.
        # Unknown is explicit; no invented claim of engine independence.
        return verify_page(self.store, handoff.source_root/source.relative_path, request)

    def assessment_decision(self, request):
        return self.reference_decision(request, assessment=True)

    def reference_decision(self, request, *, assessment=False):
        from ..review import source_references
        with self.store.connect() as db:
            replay=self.store._request(db,request)
            if replay is not None:return replay
            row=db.execute('SELECT data FROM documents WHERE id=?',(request['document_id'],)).fetchone()
            if not row:raise ValueError('document_not_found')
            doc=json.loads(row[0])
        handoff=self.handoff()
        manifest=build_manifest(handoff.records,handoff.registry_sha256,handoff.source_root,{doc['source']['source_id']})
        if manifest['rejected'] or len(manifest['items'])!=1:raise ValueError('reference_source_not_in_governed_scope')
        source=manifest['items'][0]
        read_snapshot(Snapshot(**source),handoff.source_root)
        path=handoff.source_root/source['relative_path']
        dimensions=None
        if not assessment and request['action']=='create':
            support=request.get('supporting_pages',[])
            if not isinstance(support,list):raise ValueError('choose_valid_bounded_reference_pages')
            pages=[request.get('page_index'),*support]
            if len(pages)>3 or any(type(p) is not int or not 0<=p<doc.get('total_pages',0) for p in pages) or len(set(pages))!=len(pages):raise ValueError('choose_valid_bounded_reference_pages')
            import pypdfium2 as pdfium
            pdf=pdfium.PdfDocument(path)
            try:
                dimensions={}
                for p in pages:
                    page=pdf[p]
                    try:width,height=page.get_size()
                    finally:page.close()
                    dimensions[str(p)]={'width':width,'height':height}
            finally:pdf.close()
        def current():
            handoff.assert_current()
            if sha256(path.read_bytes()).hexdigest()!=source['content_hash']:raise ValueError('reference_original_changed')
        current()
        context=self.root/'reference-study.json'
        origin=json.loads(context.read_text()).get('origin') if context.is_file() else 'operator_submission'
        if origin not in {'operator_submission','engineering_fixture'}:raise ValueError('invalid_reference_study_context')
        if assessment:
            from ..review import source_assessments
            study=json.loads(context.read_text()) if context.is_file() else {}
            evidence_class=study.get('evidence_class','synthetic') if origin=='engineering_fixture' else 'natural'
            return source_assessments.apply(self.store,request,source=source,study_origin=origin,evidence_class=evidence_class,assert_current=current)
        return source_references.apply(self.store,request,source=source,dimensions=dimensions,study_origin=origin,assert_current=current)

    def reconcile(self, source_id=None):
        from ..delivery.source_status import publish
        try:
            handoff = self.handoff()
        except Exception:
            publish(self.root,error=True)
            raise
        current = {r['source_id']: dict(r) for r in handoff.records}
        with self.store.connect() as db:
            documents=[json.loads(r[0]) for r in db.execute('SELECT data FROM documents')]
        for issue in getattr(handoff,'evidence',{}).get('original_issues',[]):
            matched=next((d for d in documents if d['id']==issue.get('system2_document_id')),None)
            record=current.get(matched['source']['source_id']) if matched else None
            if record and record.get('content_hash')==issue.get('source_sha256'):record.setdefault('_original_issues',[]).append(issue)
        for doc in documents:
            if source_id and doc['source']['source_id']!=source_id:continue
            try:
                read_snapshot(Snapshot(**doc['source']), handoff.source_root)
            except (ValueError,OSError):
                if doc['source']['source_id'] in current:
                    current[doc['source']['source_id']]['selection_status'] = 'PENDING'
        self.store.reconcile_sources(current, source_id)
        try:
            handoff.assert_current()
        except Exception:
            publish(self.root,error=True)
            raise
        publish(self.root,handoff.registry_sha256,getattr(handoff,'evidence',{}).get('registry_kind','workbook'))
        return handoff

    def conversion(self, request):
        """Only a server-owned, actor-bound staging path reaches this method."""
        from ..formats.router import route_format
        self.reconcile()
        staged=Path(request['staged_path']).resolve();stage_root=Path(request['staged_root']).resolve()
        if not staged.is_relative_to(stage_root) or not staged.is_file():
            raise ValueError('conversion_staging_path_invalid')
        raw=staged.read_bytes();extension=staged.suffix.lower().lstrip('.')
        if sha256(raw).hexdigest()!=request['staged_hash']:
            raise ValueError('staged_conversion_changed')
        if extension not in {'html','htm','xlsx','pdf'}:
            raise ValueError('unsupported_conversion_target')
        route_format(staged.name,extension,raw)
        if request.get('complete') is not True or not request.get('method','').strip() or not request.get('note','').strip():
            raise ValueError('conversion_method_and_completeness_confirmation_required')
        with self.store.transaction() as db:
            replay=self.store._request(db,request)
            if replay is not None:return replay
            doc=self.store._load(db,request['document_id'])
            if not doc['eligible'] or doc['revision']!=request['revision'] or doc['state']!='conversion_required':
                raise ValueError('conversion_task_stale_or_not_applicable')
            if doc['source']['file_format'] in {'html','htm','xlsx','pdf'}:
                raise ValueError('supported_format_errors_are_not_conversion_tasks')
            target=self.root/'conversions'/doc['id']/(request['request_id']+'.'+extension)
            target.parent.mkdir(parents=True,exist_ok=True)
            if target.exists() and target.read_bytes()!=raw:raise ValueError('conversion_artifact_collision')
            if not target.exists():target.write_bytes(raw)
            doc['conversion']={'relative_path':target.relative_to(self.root).as_posix(), 'content_hash':sha256(raw).hexdigest(),
                'file_format':'html' if extension=='htm' else extension,
                'parsing_copy_of':{'original_sha256':doc['source']['content_hash'],'original_format':doc['source']['file_format'],
                    'conversion_id':request['request_id'],'operator':request['actor'],'method':request['method'],
                    'completeness_note':request['note']}}
            doc['state']='queued';doc['issues']=[];doc['revision']+=1
            self.store._save(db,doc);self.store._event(db,doc['id'],'conversion',doc['conversion'])
            return self.store._receipt(db,request,{'status':'applied','revision':doc['revision']})

    def tick(self):
        """One bounded unit of work. No discovery or implicit new jobs."""
        with (self.root / '.worker.lock').open('a+b') as lock:
            try:
                lock_file(lock)
            except BlockingIOError:
                return {'status': 'busy'}
            handoff = self.reconcile()
            with self.store.transaction() as db:
                documents = [json.loads(r[0]) for r in db.execute('SELECT data FROM documents ORDER BY rowid')]
                doc = next((d for d in documents if d['eligible'] and d['state'] in {'queued', 'running'}), None)
                if doc is None:
                    return {'status': 'idle'}
                doc=self.store._load(db,doc['id'])
                doc['state'] = 'running'; doc['attempt'] += 1
                self.store._save(db, doc)
            try:
                source = Snapshot(**doc['source'])
                source_root=handoff.source_root
                if doc.get('conversion'):
                    source=Snapshot(**dict(doc['source'],**doc['conversion']))
                    source_root=self.root
                raw = read_snapshot(source, source_root)
                output = self.root / 'artifacts' / doc['id'] / ('attempt-' + str(doc['attempt']))
                config = None; pages = None; complete = True; cursor = 0; total = None
                if source.file_format == 'pdf':
                    from pypdf import PdfReader
                    from ..config import AppConfig
                    total = len(PdfReader(io.BytesIO(raw)).pages)
                    start = doc['cursor']
                    pages = set(range(max(0, start - 1), min(total, start + 3)))
                    if not pages:
                        raise ValueError('pdf_has_no_pages')
                    cursor = min(total, start + 3); complete = cursor == total
                    config = AppConfig.from_yaml(Path(__file__).resolve().parents[3] / 'config/pdf-intake-positioned.yaml')
                # Converted inputs live under runtime/conversions; output is a separate sibling.
                # run_item's source-root boundary therefore uses the conversion directory itself.
                if doc.get('conversion'):
                    copy_path=self.root/source.relative_path
                    source_root=copy_path.parent
                    source=source.model_copy(update={'relative_path':copy_path.name})
                result = run_item(source, source_root, output, {}, config, pages)
                handoff.assert_current()
                self.reconcile()
                if result.canonical_path:
                    units, refs = content_units(output, result, source)
                    if source.file_format == 'pdf':
                        # Windows retain a halo as evidence, but never offer that page twice
                        # as an independently publishable Requirement.
                        for unit in units:
                            refs_for_unit = unit['original']['references']
                            page_ids = {r.get('page_index') for r in refs_for_unit if 'page_index' in r}
                            if doc['cursor'] and page_ids and max(page_ids) < doc['cursor']:
                                unit['kind'] = 'context'
                                unit['evidence_only'] = True
                                unit['blockers'].append('overlap_evidence_only')
                            if unit['kind'] == 'coverage' and unit.get('coverage_scope') != 'pdf_page':
                                unit['original']['references'][0]['locator'] = 'PDF pages ' + ', '.join(str(p+1) for p in sorted(pages))
                                if doc['cursor'] or not complete:
                                    unit['blockers'].append('cross_window_relationship_review_required')
                    source_issues=['upstream_full_text_required'] if any('empty' in r and 'body' in r for r in result.reason_codes) else []
                    from ..verification.calibration import apply_calibrated_rules
                    try:
                        apply_calibrated_rules(units,source,Path(__file__).resolve().parents[3]/'config')
                    except (ValueError,OSError,KeyError,TypeError):
                        for unit in units:
                            unit.update(content_parts=[],requirement_parts=[],scoring_status='invalid_calibration_manual_review')
                    self.store.install(doc['id'], units, refs, complete=complete, cursor=cursor,issues=source_issues,
                                       generation=doc.get('generation',0),total_pages=total,pages=pages or ())
                else:
                    with self.store.transaction() as db:
                        current = self.store._load(db, doc['id'])
                        if current.get('generation',0)!=doc.get('generation',0):return {'status':'superseded'}
                        current['state'] = 'conversion_required' if source.file_format not in {'pdf','html','htm','xlsx'} else 'failed'
                        current['issues'] = list(dict.fromkeys(current['issues']+result.reason_codes))
                        current['processing_failure_codes'] = result.reason_codes
                        current['revision'] += 1
                        from ..review.processing_failure import retain
                        retain(self.store,db,current)
                        self.store._save(db, current)
                return {'status': 'processed', 'document_id': doc['id']}
            except Exception as exc:
                with self.store.transaction() as db:
                    current = self.store._load(db, doc['id'])
                    if current.get('generation',0)!=doc.get('generation',0):return {'status':'superseded'}
                    if current['state'] != 'paused':
                        current['state'] = 'failed'
                    current['error'] = str(exc); current['revision'] += 1
                    from ..review.processing_failure import retain
                    retain(self.store,db,current)
                    self.store._save(db, current)
                return {'status': 'failed', 'document_id': doc['id'], 'error': str(exc)}


def main():
    request = json.load(sys.stdin)
    try:
        runner = Runner(request['root'], request['system1'], request.get('system1_config'))
        command = request['command']; payload = request.get('request', {})
        with contextlib.redirect_stdout(io.StringIO()):
            if command == 'start':
                result = runner.start(payload)
            elif command == 'tick':
                result = runner.tick()
            elif command == 'workbook':
                result = runner.workbook()
            elif command == 'preview':
                from ..review.browser_view import browser_state
                from ..evidence.review_preview import preview
                detail=browser_state(runner.store,'unit',request['document_id'],request['unit_id']) if request.get('unit_id') else None
                with runner.store.connect() as db:
                    source=json.loads(db.execute('SELECT data FROM documents WHERE id=?',(request['document_id'],)).fetchone()[0])['source']
                if source['content_hash']!=request['expected_hash']:raise ValueError('source_version_changed')
                if request.get('cell_id') is not None:
                    from ..review.table_cells import preview_regions
                    if not detail:raise ValueError('table_unit_required')
                    refs=preview_regions(detail,request['cell_id'],request.get('region_index'),request.get('guard'))
                elif request.get('page_index') is not None:
                    if source.get('file_format')!='pdf':raise ValueError('pdf_source_required')
                    refs=[{'page_index':int(request['page_index'])}]
                elif detail:refs=detail['effective']['references']
                else:raise ValueError('unit_or_page_required')
                if detail and detail.get('processing_failure') and source.get('file_format') in {'html','htm'}:
                    from ..review.processing_failure import html_observations
                    from ..evidence.review_preview import sanitized_region, VERSION
                    raw=Path(request['path']).read_bytes()
                    if sha256(raw).hexdigest()!=request['expected_hash']:raise ValueError('original_version_changed')
                    observations=html_observations(raw)
                    markup,warnings=sanitized_region(raw,observations['references'],request.get('full',False))
                    result={'schema_version':VERSION,'kind':'html_region','html':markup,'warnings':warnings,
                        'source_sha256':request['expected_hash'],'processing_observations':observations,
                        'label':'Original metadata and content region from the saved local HTML. No links or scripts are executed.'}
                else:
                    result=preview(request['path'],request['expected_hash'],refs,runner.store.root/'preview-cache',request.get('full',False))
            elif command == 'reconcile':
                runner.reconcile();result={'status':'applied'}
            elif command == 'state':
                if request.get('view'):
                    from ..review.browser_view import browser_state
                    result = browser_state(runner.store, request['view'], request.get('document_id'), request.get('unit_id'), **{k:request[k] for k in ('offset','query','chapter','task_type','include_reviewed','stage','page_index','parent_id') if k in request})
                else:
                    runner.reconcile(); result = runner.store.snapshot()
            elif command == 'decision':
                with runner.store.connect() as db:
                    doc=json.loads(db.execute('SELECT data FROM documents WHERE id=?',(payload['document_id'],)).fetchone()[0])
                runner.reconcile(doc['source']['source_id']); result = runner.store.decision(payload)
            elif command == 'suggest':
                result = runner.suggest(payload)
            elif command == 'verify_page':
                result = runner.verify_page(payload)
            elif command == 'references':
                from ..review.source_references import view
                result=view(runner.store,document_id=request.get('document_id'),reference_id=request.get('reference_id'))
            elif command == 'assessments':
                from ..review.source_assessments import view
                result=view(runner.store,reference_id=request.get('reference_id'),assessment_id=request.get('assessment_id'))
            elif command == 'assessment_decision':
                result=runner.assessment_decision(payload)
            elif command == 'reference_decision':
                result=runner.reference_decision(payload)
            elif command == 'control':
                runner.reconcile();result = runner.store.control(payload)
            elif command == 'policy':
                result = runner.store.set_policy(payload['policy'], payload)
            elif command == 'feed':
                runner.reconcile(); result = runner.store.feed(request.get('after', 0))
            elif command == 'conversion':
                result = runner.conversion(payload)
            elif command == 'qa':
                result = runner.store.weekly_qa(create=not runner.sampling_config()['enabled'])
            elif command == 'qa_history':
                result = runner.store.weekly_qa(create=False)
            elif command == 'qa_decision':
                result = runner.store.qa_decision(payload)
            elif command == 'weekly_tick':
                result=runner.sampling_tick()
            elif command == 'weekly':
                from ..review import weekly_sampling
                result=weekly_sampling.read(runner.store,request.get('item_id'))
                result['schedule']=runner.sampling_config()
            elif command == 'weekly_decision':
                from ..review import weekly_sampling
                handoff=runner.reconcile()
                item=weekly_sampling.read(runner.store,payload['item_id'])
                if payload.get('verdict')!='UNVERIFIED':
                    path=(handoff.source_root/item['source']['relative_path']).resolve()
                    if not path.is_relative_to(handoff.source_root.resolve()) or sha256(path.read_bytes()).hexdigest()!=item['source']['content_hash']:
                        raise ValueError('sample_original_changed_or_unavailable')
                handoff.assert_current()
                result=weekly_sampling.decide(runner.store,payload)
            elif command == 'weekly_preview':
                from ..review import weekly_sampling
                from ..evidence.review_preview import preview
                item=weekly_sampling.read(runner.store,request['item_id'])
                refs=item['scope']['references'] if item['stage']=='A' else item['effective']['references']
                result=preview(request['path'],item['source']['content_hash'],refs,runner.store.root/'preview-cache',False)
            else:
                raise ValueError('unknown_workflow_command')
        print(json.dumps({'ok': True, 'data': result}, ensure_ascii=False))
    except Exception as exc:
        print(json.dumps({'ok': False, 'error': str(exc)}, ensure_ascii=False))
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
