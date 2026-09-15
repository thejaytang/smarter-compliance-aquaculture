import test from 'node:test';
import assert from 'node:assert/strict';
import {Materials} from '../ui/materials.js';

function fixture(){
 const x=new Materials();x.requirements={render(){}};const nodes=new Map(),source={disabled:false},opener={disabled:false};let nav=[],html='';
 const list={set innerHTML(value){html=value;nav=[...value.matchAll(/<button\b[^>]*data-action="(open|open-source|inspection-open)"[^>]*>/g)].map(([tag,action])=>({dataset:{action},disabled:/\bdisabled\b/.test(tag)}));},get innerHTML(){return html;}};
 x.q=selector=>selector==='#mw-material-list'?list:selector==='#mw-source'?source:selector==='[data-action="open-source"]'?opener:nodes.get(selector)||nodes.set(selector,{disabled:false}).get(selector);
 x.root={querySelectorAll(selector){const actions=[...selector.matchAll(/data-action="([^"]+)"/g)].map(m=>m[1]);return nav.filter(n=>actions.includes(n.dataset.action));}};
 x.state={actor:{id:'fixture'}};x.id='current';x.material={id:'current',revision:1,content_revision:1,blocks:[],source:{source_id:'local'}};x.draft=x.fromMaterial(x.material);x.token={};x.dirty=false;x.sources=[];
 x.items=[{id:'saved',title:'Saved',queue:{open_inspections:[{id:'check1',assignee:'Person',status:'pending'},{id:'check2',assignee:'Person',status:'pending'}]}},{id:'unopened1',queue:{unopened:true}},{id:'unopened2',queue:{unopened:true}}];x.message=(message)=>{x.lastMessage=message;};x.renderList();
 return {x,source,opener,nav:()=>nav};
}

test('delayed material reads disable every material, source and inspection opener then restore after an error',async()=>{
 const f=fixture();let reject,requests=0;f.x.api=()=>{requests++;return new Promise((_,fail)=>reject=fail);};const oldDraft=f.x.draft;
 assert.equal(f.nav().filter(n=>n.dataset.action==='open-source').length,2);assert.equal(f.nav().filter(n=>n.dataset.action==='inspection-open').length,2);
 const preDisabled=f.nav().find(n=>n.dataset.action==='inspection-open');preDisabled.disabled=true;
 const pending=f.x.open('next');assert.equal(f.x.opening,true);assert.ok([...f.nav(),f.source,f.opener].every(n=>n.disabled));
 await f.x.open('another');assert.equal(requests,1);f.x.updateBar();reject(Error('Unavailable fixture read'));await pending;
 assert.equal(f.x.opening,false);assert.equal(f.x.id,'current');assert.equal(f.x.draft,oldDraft);assert.equal(preDisabled.disabled,true);assert.ok(f.nav().filter(n=>n!==preDisabled).every(n=>!n.disabled));assert.equal(f.source.disabled,false);assert.equal(f.opener.disabled,false);assert.match(f.x.lastMessage,/Unavailable/);
});

test('list redraw during a delayed read keeps all new navigation rows locked until recovery',async()=>{
 const f=fixture();let reject;f.x.api=()=>new Promise((_,fail)=>reject=fail);const request=f.x.open('next'),old=f.nav();f.x.renderList();assert.notEqual(f.nav(),old);assert.ok(f.nav().every(n=>n.disabled));
 reject(Error('Fixture failure'));await request;assert.ok(f.nav().every(n=>!n.disabled));
});

test('busy navigation lock preserves pre-existing disabled permissions through repeated updates',()=>{
 const f=fixture(),restricted=f.nav()[0];restricted.disabled=true;f.source.disabled=true;f.x.busy=true;f.x.updateBar();f.x.updateBar();assert.ok(f.nav().every(n=>n.disabled));
 f.x.busy=false;f.x.updateBar();assert.equal(restricted.disabled,true);assert.equal(f.source.disabled,true);assert.equal(f.opener.disabled,false);assert.ok(f.nav().slice(1).every(n=>!n.disabled));
 f.x.updateBar();assert.equal(restricted.disabled,true);
});
