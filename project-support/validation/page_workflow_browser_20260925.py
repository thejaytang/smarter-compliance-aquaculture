"""Native Edge smoke against an isolated restored Example; no model calls."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'workbench'),str(ROOT/'workbench/backend/application'),str(ROOT/'workbench/deployment'),str(ROOT/'workbench/tests/integration')]
import deployment
from backend.shared.filesystem import temporary_directory
from restore_initial_data import restore
from colleague_handoff import Peer,ACTORS,run

OUTPUT=ROOT/'workbench/runtime/backups/developing-sync-20260925/page-workflow'
OUTPUT.mkdir(exist_ok=True)
SCRIPT=r'''
import fs from 'node:fs';
const [wsurl,base,cookie,output]=process.argv.slice(2);
const ws=new WebSocket(wsurl),pending=new Map(),errors=[],responses=[];let next=0;
ws.onmessage=event=>{const m=JSON.parse(event.data);if(m.id){const p=pending.get(m.id);pending.delete(m.id);m.error?p.reject(Error(JSON.stringify(m.error))):p.resolve(m.result);}else if(m.method==='Runtime.exceptionThrown')errors.push(m.params.exceptionDetails.text);else if(m.method==='Network.responseReceived')responses.push(m.params.response);};
await new Promise((resolve,reject)=>{ws.onopen=resolve;ws.onerror=reject;});
const call=(method,params={})=>new Promise((resolve,reject)=>{const id=++next;pending.set(id,{resolve,reject});ws.send(JSON.stringify({id,method,params}));});
const evaluate=async expression=>(await call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true})).result.value;
async function until(expression){for(let i=0;i<200;i++){if(await evaluate(expression))return;await new Promise(r=>setTimeout(r,200));}throw Error('Timed out: '+expression);}
try {
 await call('Runtime.enable');await call('Page.enable');await call('Network.enable');
 const index=cookie.indexOf('=');await call('Network.setCookie',{name:cookie.slice(0,index),value:cookie.slice(index+1),url:base});
 await call('Emulation.setDeviceMetricsOverride',{width:1600,height:1000,deviceScaleFactor:1,mobile:false});
 await call('Page.navigate',{url:base});
 await until(`document.querySelector('#workspace-selector') && document.body.innerText.includes('Weijie Tang')`);
 await evaluate(`(()=>{const s=document.querySelector('#workspace-selector');s.value='materials';s.dispatchEvent(new Event('change',{bubbles:true}));return true;})()`);
 await until(`!!document.querySelector('[data-action="open"]')`);
 await evaluate(`document.querySelector('[data-action="open"]').click()`);
 await until(`document.querySelector('#mw-title')?.textContent.includes('lakselus') && document.querySelector('#mw-content')?.innerText.length>100`);
 await until(`!!document.querySelector('#mw-reader iframe.mw-html') && !!document.querySelector('button[data-rq="open-session"]') && !document.querySelector('#mw-requirement-content').innerText.includes('Opening saved')`);
 await evaluate(`document.querySelector('button[data-rq="open-session"]').click()`);
 await until(`document.querySelector('[data-pane="interpretation"]').innerText.includes('R1 ·') && document.querySelector('[data-pane="interpretation"]').innerText.includes('Scope') && !document.querySelector('#mw-requirement-content').innerText.includes('Opening saved')`);
 if(!responses.some(r=>r.url.includes('/api/material/html?')&&r.status===200))throw Error('Original HTML did not load successfully');
 await until(`document.querySelectorAll('[data-processing-footer]').length===3 && document.querySelector('#mw-version').textContent.includes('Processing')`);
 if(await evaluate(`!!document.querySelector('[data-rq="save-draft"],[data-rq="save-close"],[data-ip="save"]')`))throw Error('Per-pane Save still visible');
 await evaluate(`(()=>{for(const id of ['#mw-complete-original','#mw-associations']){const c=document.querySelector(id);if(!c.checked)c.click();}document.querySelector('[data-action="save"]').click();})()`);
 await until(`document.querySelector('#mw-message').textContent.includes('All page changes saved') && !document.querySelector('[data-stage-confirm="content"]').disabled`);
 await evaluate(`document.querySelector('[data-stage-confirm="content"]').click()`);
 await until(`document.querySelector('#mw-message').textContent.includes('1/3 stages complete')`);
 const bypass=await evaluate(`(async()=>{const state=await (await fetch('/api/state')).json();const mid=document.querySelector('[data-action="open"]').dataset.id;const p=await (await fetch('/api/material-progress?material_id='+mid)).json();const r=await fetch('/api/material/confirm',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':state.csrf,'X-Material-API-Version':'3'},body:JSON.stringify({request_id:crypto.randomUUID(),material_id:mid,expected_revision:p.revision,explicit_confirmation:true})});return {status:r.status,body:await r.json()};})()`);
 if(bypass.status!==400||!bypass.body.error.includes('bottom'))throw Error('Archive bypass not rejected: '+JSON.stringify(bypass));
 await evaluate(`document.querySelector('#mw-associations').click()`);
 await evaluate(`document.querySelector('[data-action="back-list"]').click()`);
 await until(`!!document.querySelector('dialog[open] [data-leave="discard"]')`);
 if(!await evaluate(`document.querySelector('[data-leave="discard"]').disabled`))throw Error('Discard unlocked early');
 await new Promise(r=>setTimeout(r,3200));
 if(!await evaluate(`document.querySelector('dialog[open]') && !document.querySelector('[data-leave="discard"]').disabled`))throw Error('Countdown auto-left or failed to unlock');
 await evaluate(`document.querySelector('[data-leave="stay"]').click()`);
 await evaluate(`document.querySelector('[data-action="save"]').click()`);
 await until(`document.querySelector('#mw-message').textContent.includes('All page changes saved')`);
 await evaluate(`document.querySelector('#mw-associations').click()`);
 await evaluate(`document.querySelector('[data-action="back-list"]').click()`);
 await until(`!!document.querySelector('dialog[open] [data-leave="save"]')`);
 await evaluate(`document.querySelector('[data-leave="save"]').click()`);
 await until(`document.querySelector('.material-workbench').classList.contains('list-mode')`);
 await evaluate(`document.querySelector('[data-action="resume-material"]').click()`);
 await until(`document.querySelector('.material-workbench').classList.contains('detail-mode')`);
 const state=await evaluate(`({title:document.title,material:document.querySelector('#mw-title').textContent,panes:[...document.querySelectorAll('[data-pane]')].map(p=>p.dataset.pane),contentLength:document.querySelector('#mw-content').innerText.length})`);
 if(state.panes.length!==4 || errors.length)throw Error(JSON.stringify({state,errors}));
 fs.writeFileSync(output+'/browser.png',Buffer.from((await call('Page.captureScreenshot',{format:'png'})).data,'base64'));
 fs.writeFileSync(output+'/browser-result.json',JSON.stringify({status:'passed',...state,errors},null,2));
 console.log(JSON.stringify(state));
} catch(error) {
 fs.writeFileSync(output+'/browser-result.json',JSON.stringify({status:'failed',error:String(error),errors,responses:responses.map(r=>({url:r.url,status:r.status})),body:await evaluate('document.body.innerText')},null,2));
 fs.writeFileSync(output+'/browser-failure.png',Buffer.from((await call('Page.captureScreenshot',{format:'png'})).data,'base64'));
 throw error;
} finally {await call('Browser.close');ws.close();}
'''

with temporary_directory(prefix='wb-browser-') as temp:
    shutil.copytree(ROOT/'workbench/config',temp/'workbench/config')
    archive=ROOT/'workbench/resources/examples/example-seed-20260922.zip'
    restore(temp,archive,hashlib.sha256(archive.read_bytes()).hexdigest())
    peer=Peer(temp,ACTORS[0]);browser=None
    try:
        run([deployment.interpreter(ROOT/'workbench'),ROOT/'deployment.py','start','--root',temp/'workbench','--no-browser'],env=deployment.environment())
        peer.port=json.loads(peer.state_file.read_text())['port']
        peer.csrf=peer.call('/api/state')['csrf'];peer.call('/api/actor',dict(name=peer.actor))
        profile=temp/'edge-profile'
        browser=subprocess.Popen([r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe','--headless=new','--disable-gpu','--no-first-run','--remote-debugging-port=0','--user-data-dir='+str(profile),'about:blank'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW)
        deadline=time.monotonic()+30
        while not (profile/'DevToolsActivePort').exists():
            if time.monotonic()>deadline:raise RuntimeError('Edge debugger did not start')
            time.sleep(.2)
        port=(profile/'DevToolsActivePort').read_text().splitlines()[0]
        with urllib.request.urlopen('http://127.0.0.1:'+port+'/json/list') as response:page=next(p for p in json.load(response) if p['type']=='page')
        script=temp/'smoke.mjs';script.write_text(SCRIPT,encoding='utf-8')
        subprocess.run([str(ROOT/'workbench/runtime/cache/tools/node-v22.20.0-win-x64/node.exe'),str(script),page['webSocketDebuggerUrl'],f'http://127.0.0.1:{peer.port}/',peer.cookie,str(OUTPUT)],check=True,timeout=150)
    finally:
        if browser:
            try:browser.wait(timeout=10)
            except subprocess.TimeoutExpired:browser.terminate();browser.wait(timeout=10)
        peer.stop()
