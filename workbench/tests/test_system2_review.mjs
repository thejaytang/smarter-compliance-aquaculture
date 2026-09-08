import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const importFile=async path=>import('data:text/javascript;base64,'+Buffer.from(await readFile(new URL(path,import.meta.url),'utf8')).toString('base64'));
const {newSession,restoreSession,reviewCounts,nextPending,recordReview}=await importFile('../ui/system2-review-state.js');
const {demoCases,pdfSource}=await importFile('../ui/system2-demo-data.js');
const actor={id:'demo-actor',name:'Ana Jokic'};
const [text,join,table,html,excel]=demoCases;
test('a named reviewer is required, and accepting text cannot approve a table',()=>{
 assert.throws(()=>recordReview(newSession(),text,{},'accept'),/reviewer/);
 assert.throws(()=>recordReview(newSession(),table,actor,'accept'),/type/);
 const s=recordReview(newSession(),text,actor,'accept');
 assert.deepEqual(reviewCounts(s,demoCases),{pending:4,reviewed:1,followup:0});
 assert.equal(nextPending(s,demoCases,text.id),join.id);
 assert.equal(s.events[0].demo,true);
});
test('correction preserves original, reviewer, note and timestamp; draft reload is not acceptance',()=>{
 const start=newSession();start.items[text.id]={status:'pending',draft:{text:'Draft correction',note:'Check this',editing:true}};
 const restored=restoreSession(JSON.stringify(start));
 assert.equal(restored.items[text.id].draft.text,'Draft correction');assert.equal(restored.events.length,0);
 const result=recordReview(restored,text,actor,'correct',{text:'Corrected source text',note:'Compared with PDF'},'2026-09-07T12:00:00Z');
 assert.equal(result.events[0].before.text,text.text);assert.equal(result.events[0].after.text,'Corrected source text');
 assert.equal(result.events[0].actor.name,'Ana Jokic');assert.equal(result.events[0].note,'Compared with PDF');
 assert.equal(result.events[0].at,'2026-09-07T12:00:00Z');assert.equal(start.events.length,0);
 assert.throws(()=>recordReview(start,text,actor,'correct',{text:'  '}),/corrected text/);
});
test('merge preserves footnote marker, and each decision type needs explicit input',()=>{
 const merged=recordReview(newSession(),join,actor,'merge');
 assert.equal(merged.items[join.id].result.text,join.pieces.join(' '));
 assert.ok(merged.items[join.id].result.text.includes('[^6]'));
 assert.throws(()=>recordReview(newSession(),html,actor,'list'),/Choose/);
 assert.equal(recordReview(newSession(),html,actor,'list',{choice:'siblings'}).items[html.id].result.relationship,'siblings');
 assert.throws(()=>recordReview(newSession(),excel,actor,'columns',{recordColumn:'B',fieldsColumn:'B'}),/different/);
 assert.deepEqual(recordReview(newSession(),excel,actor,'columns',{recordColumn:'B',fieldsColumn:'C'}).items[excel.id].result.columns,{record:'B',requiredFields:'C'});
});
test('missing content and unreadable sources remain unresolved; reopening retains all history',()=>{
 for(const action of ['reparse','missing','unreadable','pending']){
  assert.throws(()=>recordReview(newSession(),table,actor,action),/note/);
  const next=recordReview(newSession(),table,actor,action,{note:'Table body missing'});
  assert.equal(next.items[table.id].status,'followup');assert.equal(reviewCounts(next,demoCases).reviewed,0);
 }
 let s=recordReview(newSession(),text,actor,'accept');
 assert.throws(()=>recordReview(s,text,actor,'correct',{text:'change'}),/Reopen/);
 s=recordReview(s,text,actor,'reopen');s=recordReview(s,text,actor,'correct',{text:'Corrected after reopening'});
 assert.equal(s.events.length,3);assert.equal(s.events[0].label,'Text confirmed');assert.equal(s.events[2].before.text,text.text);
});
test('five-case walkthrough leaves the missing table open and never manufactures live QA',()=>{
 let s=newSession();
 for(const [item,action,draft] of [[text,'accept',{}],[join,'merge',{}],[table,'reparse',{note:'Missing seven rows'}],[html,'list',{choice:'siblings'}],[excel,'columns',{recordColumn:'B',fieldsColumn:'C'}]])s=recordReview(s,item,actor,action,draft);
 assert.deepEqual(reviewCounts(s,demoCases),{pending:0,reviewed:4,followup:1});
 assert.equal(nextPending(s,demoCases,excel.id),null);assert.ok(s.events.every(e=>e.demo===true));
 assert.equal(pdfSource.sourceHash,'77e1d87383382fda4f27dc9be79937cc3017ce350b8b1d436a74500561083838');
 assert.equal(text.page+1,20);assert.equal(join.page+1,21);
});
test('accept after reopening a correction keeps the corrected text',()=>{
 let s=recordReview(newSession(),text,actor,'correct',{text:'Previously corrected text'});
 s=recordReview(s,text,actor,'reopen');
 s=recordReview(s,text,actor,'accept');
 assert.equal(s.items[text.id].result.text,'Previously corrected text');
 assert.equal(s.events.at(-1).before.text,'Previously corrected text');
});
