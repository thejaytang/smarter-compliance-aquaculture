"""Measured HTTP scale checks and real-time soak; isolated round-two origin only."""
from copy import deepcopy
import argparse
import hashlib
from http.cookiejar import CookieJar
import json
import math
from pathlib import Path
import time
import urllib.error
import urllib.request
import uuid

ROOT=Path(__file__).resolve().parents[2]
FIXTURE=ROOT/'workbench/runtime/round2-acceptance'


class Client:
    def __init__(self):
        self.origin=json.loads((FIXTURE/'server.json').read_text())['url'].rstrip('/')
        self.http=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))
        self.csrf=None
        health=self.get('/health')
        if Path(health['root']).resolve()!=FIXTURE/'workbench':raise ValueError('Refuse non-isolated origin')
        self.login()

    def login(self):
        self.csrf=self.get('/api/state')['csrf']
        self.post('/api/actor',{'name':'Weijie Tang'})

    def call(self,path,body=None,expected=200):
        headers={}
        if body is not None:headers={'Content-Type':'application/json','Origin':self.origin,'X-CSRF-Token':self.csrf,'X-Material-API-Version':'2'}
        request=urllib.request.Request(self.origin+path,data=json.dumps(body).encode() if body is not None else None,headers=headers)
        try:
            response=self.http.open(request,timeout=180)
        except urllib.error.HTTPError as e:response=e
        with response:
            raw=response.read();status=response.status
        if status!=expected:raise AssertionError((path,status,raw[:300].decode(errors='replace')))
        return json.loads(raw)

    def get(self,path):return self.call(path)
    def post(self,path,body,expected=200):return self.call(path,body,expected)
    def material(self,identity):return self.get('/api/material?id='+identity)
    def open(self,sid):
        result=self.post('/api/material/open',dict(source_id=sid,request_id=str(uuid.uuid4())))
        return result.get('material',result)
    def mutate(self,action,m,**kwargs):
        return self.post('/api/material/'+action,dict(request_id=str(uuid.uuid4()),material_id=m['id'],expected_revision=m['revision'],**kwargs))


def measured(fn,count=30):
    values=[]
    for _ in range(count):
        t=time.perf_counter();fn();values.append(time.perf_counter()-t)
    ordered=sorted(values)
    return dict(samples=count,p95_seconds=ordered[math.ceil(count*.95)-1],minimum=min(values),maximum=max(values),seconds=values)


def benchmark():
    client=Client();results={'at':time.time(),'boundary':'actual isolated HTTP; parser throughput excluded'}
    scale=json.loads((FIXTURE/'scale-materials.json').read_text());identity=scale[0]['id']
    results['material_list']=measured(lambda:client.get('/api/materials'))
    results['history_list']=measured(lambda:client.get('/api/material/history?id='+identity))
    for sid in ('TS004','TS005','TS006'):
        t=time.perf_counter();m=client.open(sid);open_elapsed=time.perf_counter()-t
        t=time.perf_counter();view=client.get('/api/material/reader?id='+m['id']);first=time.perf_counter()-t
        results[sid]=dict(open_seconds=open_elapsed,first_reader_seconds=first,first_display_including_open_seconds=open_elapsed+first,kind=view['kind'],repeat=measured(lambda:client.get('/api/material/reader?id='+m['id'])))
    def save_large():
        m=client.material(identity);blocks=deepcopy(m['blocks']);blocks[0]['text']='ENGINEERING save '+str(uuid.uuid4())
        t=time.perf_counter();result=client.mutate('save',m,blocks=blocks);elapsed=time.perf_counter()-t
        assert len(result['material']['blocks'])==10000
        return elapsed
    values=[save_large() for _ in range(30)]
    results['large_save']=dict(samples=30,p95_seconds=sorted(values)[28],seconds=values)
    results['passed']=all(results[k]['p95_seconds']<=1 for k in ('material_list','history_list')) and results['large_save']['p95_seconds']<=5 and all(results[s]['first_display_including_open_seconds']<=5 and results[s]['repeat']['p95_seconds']<=1 for s in ('TS004','TS005','TS006'))
    (FIXTURE/'performance.json').write_text(json.dumps(results,indent=2));print(json.dumps({k:v if k=='passed' else {f:n for f,n in v.items() if f in ('p95_seconds','first_reader_seconds','open_seconds')} for k,v in results.items() if isinstance(v,dict) or k=='passed'}),flush=True)


def soak(minutes=60):
    client=Client();ids={sid:client.open(sid)['id'] for sid in ('TS006','BB099')}
    start=time.monotonic();out=FIXTURE/'soak.jsonl'
    if out.exists():raise ValueError('Preserve existing soak; use a new explicitly named verification run')
    with out.open('x') as log:
        for minute in range(minutes):
            target=start+minute*60
            while time.monotonic()<target:time.sleep(min(1,target-time.monotonic()))
            row={'minute':minute,'at':time.time()}
            try:
                client.login()  # Also reconciles CSRF after intentional service restart.
                sid='BB099' if minute%2==0 else 'TS006';m=client.material(ids[sid])
                scope=m['scope'][0];blocks=deepcopy(m['blocks']) or [dict(id='soak-text',type='text',text='',source_refs=[{'scope_id':scope['id'],**scope.get('location',{})}])]
                blocks[0]['text']=f'ENGINEERING SOAK ONLY / minute {minute}'
                body=dict(request_id=str(uuid.uuid4()),material_id=m['id'],expected_revision=m['revision'],blocks=blocks)
                t=time.perf_counter();saved=client.post('/api/material/save',body)['material'];row['save_seconds']=time.perf_counter()-t
                replay=client.post('/api/material/save',body)['material'];assert replay['revision']==saved['revision']
                stale=dict(body,request_id=str(uuid.uuid4()),blocks=[dict(blocks[0],text='ENGINEERING rejected concurrent draft')])
                conflict=client.post('/api/material/save',stale,expected=409)
                assert conflict['current']['revision']==saved['revision']
                current=client.material(m['id']);assert current['blocks']==blocks
                view=client.get('/api/material/reader?id='+m['id']);assert view['kind'] in ('pdf','html')
                history=client.get('/api/material/history?id='+m['id']);assert history['revisions'][0]['revision']==saved['revision']
                other=client.material(ids['TS006' if sid=='BB099' else 'BB099']);assert other['id']!=m['id']
                row.update(status='passed',revision=saved['revision'],conflict_id=conflict['conflict_id'],kind=view['kind'], resources=client.get('/api/runtime-status').get('resources'))
            except Exception as exc:
                row.update(status='failed',error=str(exc))
            row['elapsed_seconds']=time.monotonic()-start;log.write(json.dumps(row)+'\n');log.flush();print(json.dumps(row),flush=True)
        while time.monotonic()-start<minutes*60:time.sleep(min(1,minutes*60-(time.monotonic()-start)))
    rows=[json.loads(line) for line in out.read_text().splitlines()]
    result=dict(duration_seconds=time.monotonic()-start,groups=len(rows),failed=sum(r['status']!='passed' for r in rows),scope='isolated material route, not multi-day reliability')
    (FIXTURE/'soak-result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['benchmark','soak']);args=parser.parse_args()
    benchmark() if args.action=='benchmark' else soak()
