"""Explicit URL/file inspection. Results are editable suggestions, not registration."""
from hashlib import sha256
import http.client
import ipaddress
import json
from pathlib import Path
import socket
import ssl
from urllib.parse import urlsplit, urljoin, unquote
import uuid

MAX_BYTES=25*1024*1024
INSPECTION_FIELDS=('source_title','official_url','retrieval_url','issuer','version','folder_code','file_format','jurisdiction','document_type','source_family','requirement_role','authoritative_language','effective_date','inclusion_rationale','authority_quality','scope_relevance','version_currency','traceability','access_permission','automation_readiness','acquisition_channel','provenance_status','update_model','applicability_reference','primary_source_id','source_notes')


def public_address(url):
    p=urlsplit(url)
    if p.scheme not in ('http','https') or not p.hostname or p.username or p.password or p.port not in (None,80,443):
        raise ValueError('Use a public HTTP or HTTPS URL without credentials or a custom port.')
    addresses=socket.getaddrinfo(p.hostname,p.port or (443 if p.scheme=='https' else 80),type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
        raise ValueError('Only public website addresses can be inspected.')
    return p,addresses[0][4][0]


def fetch_public(url):
    for _ in range(6):
        p,address=public_address(url);port=p.port or (443 if p.scheme=='https' else 80)
        connection=http.client.HTTPConnection(p.hostname,port,timeout=15)
        sock=socket.create_connection((address,port),timeout=15)
        try:
            if p.scheme=='https':sock=ssl.create_default_context().wrap_socket(sock,server_hostname=p.hostname)
            connection.sock=sock
            connection.request('GET',(p.path or '/')+('?' + p.query if p.query else ''),headers={'User-Agent':'SmarterCompliance/1.0 source-inspection','Accept-Encoding':'identity'})
            response=connection.getresponse()
            if response.status in (301,302,303,307,308):
                target=response.getheader('Location')
                if not target:raise ValueError('The website returned an invalid redirect.')
                url=urljoin(url,target);continue
            if response.status!=200:raise ValueError(f'The website returned HTTP {response.status}. Upload the original file instead.')
            raw=response.read(MAX_BYTES+1)
            if len(raw)>MAX_BYTES:raise ValueError('The original exceeds the 25 MB inspection limit. Upload a smaller original.')
            return raw,response.getheader('Content-Type',''),url
        finally:connection.close();sock.close()
    raise ValueError('The website redirected too many times. Upload the original file instead.')


def staged(app,actor,uid):
    uid=str(uuid.UUID(uid));root=(app.runtime/'uploads').resolve();meta=json.loads((root/(uid+'.json')).read_text())
    path=Path(meta['path']).resolve()
    if meta.get('actor_name')!=actor or path.parent!=root or path.stem!=uid or not path.is_file() or sha256(path.read_bytes()).hexdigest()!=meta['hash']:
        raise ValueError('The staged original is unavailable, changed or belongs to another reviewer.')
    return path,meta


def inspect_source(app,actor,request):
    if not isinstance(request,dict) or set(request)-{'official_url','upload_id','filename'}:raise ValueError('Unsupported inspection fields.')
    if bool(request.get('official_url'))==bool(request.get('upload_id')):raise ValueError('Provide one official URL or one uploaded file.')
    app.collaboration.coordinator(actor)
    uid=request.get('upload_id');url=request.get('official_url','').strip();final=url
    if uid:
        path,meta=staged(app,actor,uid);url=meta.get('official_url','');final=meta.get('retrieval_url',url)
    else:
        try:raw,mime,final=fetch_public(url)
        except OSError as exc:raise ValueError('The website could not be reached. Try again or upload the original file.') from exc
        suffix='.pdf' if raw.startswith(b'%PDF-') else '.xlsx' if raw.startswith(b'PK') and (urlsplit(final).path.lower().endswith('.xlsx') or 'spreadsheetml' in mime) else '.html' if 'html' in mime or b'<' in raw[:1000] else ''
        if not suffix:raise ValueError('This link did not return a PDF, HTML or XLSX original. Upload the file instead.')
        uid=str(uuid.uuid4());root=app.runtime/'uploads';root.mkdir(exist_ok=True);path=root/(uid+suffix);path.write_bytes(raw)
        meta={'actor_name':actor,'path':str(path),'hash':sha256(raw).hexdigest(),'official_url':url,'retrieval_url':final};(root/(uid+'.json')).write_text(json.dumps(meta))
    result=app.system2.call('source_metadata',path=str(path),filename=request.get('filename') or unquote(urlsplit(final).path.rsplit('/',1)[-1]),official_url=url,retrieved=bool(meta.get('retrieval_url')))
    if url:result['fields'].update(official_url=url,retrieval_url=final)
    result={**result,'upload_id':uid,'hash':meta['hash'],'inspection_id':str(uuid.uuid4())}
    from datetime import datetime, timezone
    result['inspection']={**result.get('inspection',{}),'content_hash':meta['hash'],'inspected_at':datetime.now(timezone.utc).isoformat(),'official_url':url,'retrieval_url':final}
    app.collaboration.put('source_inspection',result['inspection_id'],{'actor':actor,'result':result})
    return result


def verified_inspection(app,actor,request):
    # Resolve server-held evidence or run mandatory inspection before intake.
    identity=request.get('inspection_id')
    if not identity:
        query={'upload_id':request['upload_id']} if request.get('upload_id') else {'official_url':request.get('official_url','')}
        return inspect_source(app,actor,query)
    record=app.collaboration.get('source_inspection',str(uuid.UUID(identity)))
    if not record or record.get('actor')!=actor:raise ValueError('This inspection is unavailable or belongs to another reviewer. Parse the original again.')
    result=record['result'];uid=result['upload_id'];_,meta=staged(app,actor,uid)
    if request.get('upload_id') and request['upload_id']!=uid or meta['hash']!=result['hash']:raise ValueError('The original changed after inspection. Parse it again.')
    inspected_url=result['fields'].get('official_url','')
    if inspected_url and request.get('official_url',inspected_url)!=inspected_url:raise ValueError('The website URL changed after inspection. Inspect the new URL first.')
    return result
