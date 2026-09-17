"""On-demand checks of registered public URLs; stored originals remain untouched."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from hashlib import sha256
import threading
import uuid
from local_workbench.collaboration import now
from local_workbench.source_intake import fetch_public

_active=set()
_guard=threading.Lock()


def get_check(app,actor,rid):
    rid=str(uuid.UUID(rid));run=app.collaboration.get('source_url_check',rid)
    if not run or run['actor']!=actor:raise ValueError('This check is unavailable for the current reviewer.')
    with _guard:active=(str(app.runtime),rid) in _active
    if run['status']=='running' and not active:return {**run,'status':'interrupted','error':'The service restarted before this check finished. Start a new check.'}
    return run


def check_one(source):
    result={'source_id':source.get('source_id',''),'title':source.get('source_title','')}
    url=source.get('retrieval_url')
    if not url:return {**result,'status':'skipped','message':'Not checked: no registered retrieval URL.'}
    if not source.get('content_hash'):return {**result,'status':'skipped','message':'Not checked: no retained file hash to compare.'}
    try:
        raw,mime,final=fetch_public(url)
        if source.get('file_format')=='pdf' and not raw.startswith(b'%PDF-'):raise ValueError('The URL no longer returns a PDF.')
        if source.get('file_format')=='xlsx' and not raw.startswith(b'PK'):raise ValueError('The URL no longer returns an XLSX file.')
        digest=sha256(raw).hexdigest();changed=digest!=source['content_hash']
        return {**result,'status':'changed' if changed else 'unchanged','message':'File changed; review whether a new version exists.' if changed else 'File unchanged at the registered URL.', 'checked_url':final,'observed_hash':digest}
    except OSError:return {**result,'status':'failed','message':'Not checked: the website could not be reached. Try again later.'}
    except Exception as exc:return {**result,'status':'failed','message':'Not checked: '+str(exc)}


def start_check(app,actor,request):
    app.collaboration.coordinator(actor)
    if not isinstance(request,dict) or set(request)!={'request_id'}:raise ValueError('Provide a check request identity.')
    rid=str(uuid.UUID(request['request_id']));key=(str(app.runtime),rid)
    with _guard:
        old=app.collaboration.get('source_url_check',rid)
        if old:
            if old['actor']!=actor:raise ValueError('Request belongs to another reviewer.')
            return old
        if any(root==str(app.runtime) for root,_ in _active):raise ValueError('An update check is already running.')
        run={'id':rid,'actor':actor,'started_at':now(),'status':'running','total':0,'results':[]}
        app.collaboration.put('source_url_check',rid,run);_active.add(key)
    def work():
        try:
            sources=app.adapter.call('read')['sources'];run['total']=len(sources);app.collaboration.put('source_url_check',rid,run)
            with ThreadPoolExecutor(max_workers=3) as pool:
                futures={pool.submit(check_one,s):s for s in sources}
                for future in as_completed(futures):
                    result=future.result();source=futures[future]
                    if result['status']!='skipped':result['checked_at']=now()
                    if result['status']=='changed':
                        try:
                            identity=str(uuid.uuid5(uuid.NAMESPACE_URL,'source-update:'+source['source_id']+':'+str(source.get('content_hash'))+':'+result['observed_hash']))
                            existing=app.collaboration.get('source_update_notice',identity)
                            if not existing:
                                receipt=app.adapter.call('workflow_reopen',request={'actor':actor,'request_id':identity,'source_id':source['source_id'],'expected_source_revision':source['source_revision'],'note':'Registered URL file changed. Verify version and applicability before restoring Include. Observed SHA256: '+result['observed_hash']})
                                app.collaboration.put('source_update_notice',identity,receipt);app.snapshot_time=0
                            result['message']='File changed; source review requested. Original retained.'
                        except Exception:
                            result['message']='File changed, but a review task could not be created. Refresh the source and request review.'
                    run['results'].append(result);app.collaboration.put('source_url_check',rid,run)
            run['results'].sort(key=lambda r:(r['status']!='changed',r['source_id']));run['status']='complete';run['finished_at']=now()
        except Exception:
            run.update(status='failed',error='Could not read the source database. Check Runtime status and retry.')
        finally:
            app.collaboration.put('source_url_check',rid,run)
            with _guard:_active.discard(key)
    threading.Thread(target=work,daemon=True).start()
    return dict(run)
