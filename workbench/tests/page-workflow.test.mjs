import test from 'node:test';
import assert from 'node:assert/strict';
import {PageWorkflow,savePage} from '../frontend/components/page-workflow.js';

function page(){
  const calls=[],m={dirty:true,collaboration:{readonly:false},updateBar(){},message(text){this.notice=text;}};
  m.interpretations={active:'actor:material:one',drafts:new Map(['one','two'].map(id=>['actor:material:'+id,{dirty:true}])),
    owner:()=> 'actor:material',render(){},hasQuotation:d=>!!d?.quotation,
    hasUnsaved(){return [...this.drafts.values()].some(d=>d.dirty||d.retry||d.quotation);},
    async save(action){calls.push(this.active+':'+action);this.drafts.get(this.active).dirty=false;}};
  m.requirements={dirty:true,hasUnsaved(){return this.dirty;},async saveAll(){calls.push('requirements');this.dirty=false;}};
  m.saveContent=async()=>{calls.push('content');m.dirty=false;return true;};
  m.pageWorkflow={async refresh(){calls.push('refresh');}};
  return {m,calls};
}
test('one Save stores every interpretation draft, Requirement draft and content without review actions',async()=>{
  const {m,calls}=page();assert.equal(await savePage(m),true);
  assert.deepEqual(calls,['actor:material:one:save','actor:material:two:save','requirements','content','refresh']);
  assert.equal(m.pageSaving,false);assert.equal(m.interpretations.active,'actor:material:one');
});
test('failed hidden interpretation keeps remaining drafts and prevents upstream writes',async()=>{
  const {m,calls}=page();m.interpretations.save=async function(){calls.push(this.active);if(this.active.endsWith(':one'))this.drafts.get(this.active).dirty=false;else this.notice='Newer saved revision';};
  assert.equal(await savePage(m),false);assert.equal(m.dirty,true);assert.equal(m.requirements.dirty,true);
  assert.equal(m.interpretations.drafts.get('actor:material:two').dirty,true);assert.match(m.notice,/incomplete.*Newer saved revision/);
  assert.equal(m.pageSaving,false);
});
test('uncertain interpretation save uses its exact retry action',async()=>{
  const {m,calls}=page();m.interpretations.drafts.get('actor:material:one').retry={request_id:'retained'};
  const save=m.interpretations.save;m.interpretations.save=async function(action){await save.call(this,action);this.drafts.get(this.active).retry=null;};
  assert.equal(await savePage(m),true);assert.match(calls[0],/:retry$/);
});
test('processing status invalidates only the edited stage and its downstream stages',()=>{
  const {m}=page();m.dirty=false;m.requirements.dirty=false;
  const flow=new PageWorkflow(m);flow.state={stages:Object.fromEntries(['content','requirements','interpretation'].map(k=>[k,{complete:true}]))};
  assert.equal(flow.completed(),2);m.requirements.dirty=true;assert.equal(flow.completed(),1);m.dirty=true;assert.equal(flow.completed(),0);
});

function leaving(t){
  let time=0,tick;const listeners={},nodes=new Map(),button=()=>({disabled:false,textContent:''});
  const selectors=['[data-leave="save"]','[data-leave="stay"]','[data-leave="discard"]','[data-leave-status]'];selectors.forEach(s=>nodes.set(s,button()));
  const dialog={open:true,querySelector:s=>nodes.get(s),querySelectorAll:()=>[...nodes.values()],addEventListener:(type,fn)=>listeners[type]=fn,close(){this.open=false;listeners.close?.();}};
  t.mock.method(performance,'now',()=>time);t.mock.method(globalThis,'setInterval',fn=>{tick=fn;return 42;});t.mock.method(globalThis,'clearInterval',()=>{});
  let saved=0,discarded=0;
  const m={dialog(html,wire){wire(dialog);return dialog;},async save(){saved++;return true;},async discardPage(){discarded++;}};
  const flow=new PageWorkflow(m),result=flow.leaveDialog();
  return {m,flow,result,dialog,nodes,advance(ms){time+=ms;tick();},counts:()=>({saved,discarded})};
}
test('three seconds is a discard lock, never an automatic save or departure',async t=>{
  const f=leaving(t),discard=f.nodes.get('[data-leave="discard"]');
  assert.equal(discard.disabled,true);await discard.onclick();assert.equal(f.counts().discarded,0);
  f.advance(2999);assert.equal(discard.disabled,true);f.advance(1);assert.equal(discard.disabled,false);
  assert.deepEqual(f.counts(),{saved:0,discarded:0});assert.equal(f.dialog.open,true);
  await discard.onclick();assert.equal(await f.result,true);assert.equal(f.counts().discarded,1);
});
test('save can be selected immediately; a failed save keeps the page and draft',async t=>{
  const f=leaving(t);let attempts=0;f.m.save=async()=>++attempts>1;
  await f.nodes.get('[data-leave="save"]').onclick();assert.equal(f.dialog.open,true);
  assert.match(f.nodes.get('[data-leave-status]').textContent,/did not finish/);
  await f.nodes.get('[data-leave="save"]').onclick();assert.equal(await f.result,true);
});
test('continue editing and Escape resolve a blocked departure without saving',async t=>{
  const f=leaving(t);assert.equal(f.flow.leaveDialog(),f.result);f.nodes.get('[data-leave="stay"]').onclick();
  assert.equal(await f.result,false);assert.deepEqual(f.counts(),{saved:0,discarded:0});
});
