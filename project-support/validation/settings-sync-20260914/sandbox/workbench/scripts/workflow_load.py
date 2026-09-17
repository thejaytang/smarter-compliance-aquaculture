"""Controlled normal-service stop and preservation check for the approved UI load."""
import http.cookiejar
import json
from pathlib import Path
import sys
import time
import urllib.request
ROOT=Path(__file__).resolve().parents[2]
url='http://127.0.0.1:62742'
jar=http.cookiejar.CookieJar();http=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
def read(path):
 with http.open(url+path,timeout=20) as response:return json.load(response)
health=read('/health')
if Path(health['root']).resolve()!=ROOT/'workbench':raise ValueError('Unexpected normal service root; no action taken.')
state=read('/api/state')
def post(path,body):
 req=urllib.request.Request(url+path,data=json.dumps(body).encode(),headers={'Content-Type':'application/json','X-CSRF-Token':state['csrf'],'Origin':url})
 with http.open(req,timeout=20) as response:return json.load(response)
post('/api/actor',{'name':'Weijie Tang'});result=post('/api/stop',{})
print(json.dumps({'prior_instance':health['instance'],'stop':result}),flush=True)
