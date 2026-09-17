import test from 'node:test';
import assert from 'node:assert/strict';
import {Materials} from '../frontend/components/materials.js';
function fixture(){
 const w=new Materials();w.requirements={render(){}};const elements=new Map();let focused=0,scrolled=0;
 const checklist={open:false,scrollIntoView(){scrolled++;},querySelector(){return {focus(){focused++;}};}};
 const f={w,elements,requests:[],checklist,get focused(){return focused;},get scrolled(){return scrolled;}};
 w.material={content_revision:7,scope:[{id:'page:1',label:'Page 1'},{id:'page:2',label:'Page 2 · scan'}],candidates:[]};
 w.draft={checked_scope:['page:1','page:2'],issues:[],association_reviewed:true};w.state={actor:{name:'Engineering reviewer'}};w.collaboration={enabled:true};
 w.q=()=>checklist;w.dialog=(html,wire)=>{f.html=html;const d={close(){f.closed=true;},querySelector:s=>elements.get(s)||elements.set(s,{checked:false}).get(s)};wire(d);};
 w.mutate=async(...args)=>{f.requests.push(args);return true;};w.message=t=>{f.message=t;};return f;
}
test('unchecked empty/scan scope is named and checklist navigation cannot mark or save it',()=>{
 const f=fixture();f.w.draft.checked_scope=['page:1'];const before=structuredClone(f.w.draft);f.w.reviewDialog();
 assert.match(f.html,/Page 2 · scan/);assert.match(f.html,/id="mw-confirm-submit"[^>]*disabled/);
 f.elements.get('#mw-open-checklist').onclick();assert.equal(f.checklist.open,true);assert.equal(f.focused,1);assert.equal(f.scrolled,1);assert.equal(f.closed,true);
 assert.deepEqual(f.w.draft,before);assert.equal(f.requests.length,0);
});
test('all checked ranges cannot bypass a pending candidate or unavailable source',async()=>{
 for(const change of [w=>w.material.candidates=[{status:'running'}],w=>w.material.candidates=[{status:'ready'}],w=>w.material.candidates=[{status:'partial'}],w=>w.material.source_stale=true,w=>w.material.source_check_error='unavailable',w=>w.material.source_issues=[{message:'missing original'}]]){
  const f=fixture();change(f.w);f.w.reviewDialog();assert.match(f.html,/id="mw-confirm-submit"[^>]*disabled/);
  f.elements.set('#mw-final-confirm',{checked:true});await f.elements.get('#mw-confirm-submit').onclick();assert.equal(f.requests.length,0);
 }
});
test('completed checklist still requires explicit final confirmation and exact saved revision context',async()=>{
 const f=fixture();f.w.material.candidates=[{status:'failed'},{status:'adopted'}];f.w.reviewDialog();
 assert.match(f.html,/saved content revision 7/);assert.match(f.html,/personal content work only/);assert.match(f.html,/id="mw-confirm-submit"[^>]*disabled/);
 await f.elements.get('#mw-confirm-submit').onclick();assert.equal(f.requests.length,0);
 f.elements.get('#mw-final-confirm').checked=true;f.elements.get('#mw-final-confirm').onchange();assert.equal(f.elements.get('#mw-confirm-submit').disabled,false);await f.elements.get('#mw-confirm-submit').onclick();assert.equal(f.requests.length,1);assert.equal(f.requests[0][1].explicit_confirmation,true);assert.deepEqual(f.requests[0][1].checked_scope,['page:1','page:2']);
});
test('unsaved changes cannot enter confirmation',()=>{
 const f=fixture();f.w.dirty=true;f.w.reviewDialog();assert.match(f.message,/Save the material first/);assert.equal(f.html,undefined);assert.equal(f.requests.length,0);
});
