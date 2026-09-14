"""Optional bounded JSON suggestion service. No model writes or acceptance authority."""
import json
import os
import urllib.request
from urllib.parse import urlsplit


class Suggestions:
    def __init__(self, config):
        self.config=config
        self.calls=0

    def propose(self, capability, evidence):
        cfg=self.config
        if not cfg.get('enabled',False):
            return {'mode':'NO_API','suggestions':[]}
        try:
            endpoint=cfg['endpoint'];url=urlsplit(endpoint)
            if url.scheme!='https' or url.username or url.password or not cfg.get('model'):
                raise ValueError('explicit_https_endpoint_and_model_required')
            if capability not in cfg.get('allowed_capabilities',[]):
                raise ValueError('capability_not_authorized')
            if self.calls >= cfg.get('max_calls',0):
                raise ValueError('call_budget_exhausted')
            permitted=set(cfg.get('allowed_evidence_ids',[]))
            selected=[e for e in evidence if e['id'] in permitted]
            if not selected:
                raise ValueError('no_authorized_evidence')
            sent={e['id'] for e in selected}
            body=json.dumps({'schema_version':'evidence-suggestions/1','model':cfg['model'],
                             'capability':capability,'evidence':selected}).encode()
            if len(body)>cfg.get('max_bytes',0):
                raise ValueError('evidence_size_limit')
            headers={'Content-Type':'application/json'}
            if cfg.get('api_key_env'):
                key=os.environ.get(cfg['api_key_env'])
                if not key:raise ValueError('credential_not_configured')
                headers['Authorization']='Bearer '+key
            self.calls+=1
            req=urllib.request.Request(endpoint,data=body,headers=headers,method='POST')
            # Reject redirects: authorization never follows an unapproved target.
            class NoRedirect(urllib.request.HTTPRedirectHandler):
                def redirect_request(self,*args,**kwargs):return None
            with urllib.request.build_opener(NoRedirect).open(req,timeout=min(60,cfg.get('timeout',20))) as response:
                raw=response.read(1_000_001)
            if len(raw)>1_000_000:raise ValueError('response_size_limit')
            suggestions=json.loads(raw)['suggestions']
            if not isinstance(suggestions,list):raise ValueError('invalid_suggestions')
            for item in suggestions:
                if not isinstance(item,dict) or not item.get('evidence_ids') or set(item['evidence_ids'])-sent:
                    raise ValueError('suggestion_without_authorized_evidence')
            return {'mode':'API_CONNECTED','suggestions':suggestions,'accepted':False}
        except Exception as exc:
            return {'mode':'NO_API_FALLBACK','suggestions':[],'error_type':type(exc).__name__}
