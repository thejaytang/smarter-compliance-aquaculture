"""One local, server-only provider configuration shared by workbench features."""
import json
import os
import tempfile
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, build_opener
from .collaboration import named

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('Provider redirects are not accepted.')

provider_opener = build_opener(NoRedirect)

def validate_endpoint(endpoint):
    p = urlparse(endpoint)
    if not p.hostname or p.username or p.password or p.query or p.fragment or (p.scheme != 'https' and not (p.scheme == 'http' and p.hostname in ('localhost', '127.0.0.1', '::1'))):
        raise ValueError('Enter the complete HTTPS Chat Completions URL, or a local test service URL. Do not put credentials in the address.')
    return endpoint

class AISettings:
    def __init__(self, app):
        self.app = app
        self.path = Path(app.runtime) / 'ai-provider.json'

    def config(self):
        return json.loads(self.path.read_text(encoding='utf-8')) if self.path.exists() else {'revision': 0, 'enabled': False, 'endpoint': '', 'model': '', 'max_bytes': 500000, 'timeout': 90}

    def public(self):
        c = self.config()
        available = bool(c.get('enabled') and c.get('endpoint') and c.get('model'))
        return {k:c.get(k) for k in ('revision','enabled','endpoint','model','max_bytes','timeout')} | dict(
            has_key=bool(c.get('api_key') or os.environ.get('WORKBENCH_AI_API_KEY')),
            available=available,status='Configured · not connection-tested' if available else 'Not connected',
            destination=c.get('endpoint',''),reason='' if available else 'Set up the shared API in Settings → AI service. Manual editing remains available.')

    def save(self, actor, request):
        named(actor)
        with self.app.collaboration.lock:
            old = self.config()
            if request.get('revision') != old['revision']:
                raise ValueError('API settings changed in another window. Reopen Settings before saving.')
            endpoint = str(request.get('endpoint','')).strip()
            model = str(request.get('model','')).strip()
            if endpoint: validate_endpoint(endpoint)
            if len(endpoint)>2000 or len(model)>200 or any(ord(x)<32 for x in model): raise ValueError('Invalid API address or model.')
            enabled = request.get('enabled') is True
            if enabled and not (endpoint and model): raise ValueError('Enter both a service address and model before enabling the API.')
            key = request.get('api_key','')
            if not isinstance(key,str) or len(key)>8192 or any(ord(x)<32 for x in key): raise ValueError('Invalid API key.')
            limit = request.get('max_bytes',500000)
            if type(limit) is not int or not 1000<=limit<=10000000: raise ValueError('Context limit must be between 1,000 and 10,000,000 UTF-8 bytes.')
            c = dict(revision=old['revision']+1,enabled=enabled,endpoint=endpoint,model=model,
                api_key='' if request.get('clear_key') else key or old.get('api_key',''),max_bytes=limit,timeout=90)
            self.path.parent.mkdir(parents=True,exist_ok=True)
            fd, temporary = tempfile.mkstemp(prefix='.ai-provider-',suffix='.tmp',dir=self.path.parent)
            try:
                with os.fdopen(fd,'w',encoding='utf-8') as stream:
                    json.dump(c,stream);stream.flush();os.fsync(stream.fileno())
                os.replace(temporary,self.path)
            finally:
                if os.path.exists(temporary):os.unlink(temporary)
            return self.public()
