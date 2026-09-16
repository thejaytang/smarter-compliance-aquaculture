import test from 'node:test';
import assert from 'node:assert/strict';
import {MarkdownNotebook,updateMarkdownBlocks,blockMarkdown} from '../ui/markdown-content.js';
const blocks=()=>[
 {id:'info',role:'document_information',type:'text',text:'Document title',source_refs:[]},
 {id:'intro',type:'text',text:'Introduction 鱼 æ',source_refs:[{scope_id:'p1',anchor:'intro'}]},
 {id:'table',type:'table',text:'Limits',table:{rows:[['Name','Value'],['X','4']],merges:[],notes:[]},source_refs:[{scope_id:'p1',anchor:'t'}]},
 {id:'section',type:'heading',level:1,text:'Section 1',source_refs:[{scope_id:'p1',anchor:'s1'}]},
 {id:'body',type:'text',text:'Keep this requirement.',parent_id:'section',dependencies:[],source_refs:[{scope_id:'p1',anchor:'body'}]}
];
function harness(){
 const controls=new Map(),calls=[];let dialog;
 const m={id:'one',collaboration:{readonly:false},draft:{blocks:blocks()},root:{querySelectorAll:()=>[]},changed:v=>calls.push(v),renderContent(){},message:t=>calls.push(t),dialog(html,wire){dialog={html,closed:false,querySelector:k=>{if(!controls.has(k))controls.set(k,{});return controls.get(k);},querySelectorAll:()=>[],close(){this.closed=true;}};wire(dialog);}};
 return {m,n:new MarkdownNotebook(m),controls,calls,get dialog(){return dialog;}};
}
test('section shortcut selects only preceding body passages; bulk delete stays unsaved and can be undone',async()=>{
 const h=harness(),original=structuredClone(h.m.draft.blocks);
 await h.n.action('select-before',{closest:()=>({dataset:{mdCell:'section'}})});
 assert.deepEqual([...h.n.selectedBlocks],['intro','table']);assert.equal(h.calls.length,0);
 await h.n.action('bulk-delete',{});assert.deepEqual(h.m.draft.blocks,original);
 h.controls.get('[data-bulk-apply]').onclick();assert.equal(h.calls.length,1);
 assert.equal(h.m.draft.blocks[1].text,'');assert.equal(h.m.draft.blocks[2].text,'');
 assert.deepEqual(h.m.draft.blocks.slice(3),original.slice(3));assert.deepEqual(h.m.draft.blocks[0],original[0]);
 for(const i of [1,2]){assert.deepEqual(h.m.draft.blocks[i].source_refs,original[i].source_refs);assert.deepEqual(h.m.draft.blocks[i].markdown.original,original[i]);}
 h.n.showChanges=false;assert.doesNotMatch(h.n.documentMarkup(),/data-md-cell="intro"/);h.n.showChanges=true;assert.match(h.n.documentMarkup(),/Introduction 鱼 æ/);
 await h.n.action('undo-bulk',{});assert.deepEqual(h.m.draft.blocks,original);
});
test('shift selection includes table and headings, in either direction, and excludes document metadata',()=>{
 const {n}=harness();n.pick('body',true);n.pick('info',true,true);assert.deepEqual([...n.selectedBlocks].sort(),['body','intro','section','table']);n.pick('table',false,true);assert.deepEqual([...n.selectedBlocks].sort(),['body','section']);
});
test('batch editing preserves separate identities and source references, including table metadata and Unicode',()=>{
 const original=blocks(),next=updateMarkdownBlocks(original,new Map([['intro','New **鱼 æ** text.'],['table','| Name | Value |\n| --- | --- |\n| X | 5 |']]));
 assert.equal(next[1].text,'New 鱼 æ text.');assert.equal(next[2].table.rows[1][1],'5');assert.deepEqual(next[2].source_refs,original[2].source_refs);assert.deepEqual(next[2].markdown.original.table,original[2].table);assert.equal(original[2].table.rows[1][1],'4');assert.equal(next[2].markdown.baseline,blockMarkdown(original[2]));
 assert.throws(()=>updateMarkdownBlocks(original,new Map([['missing','new']])),/no longer exists/);
});
test('bulk confirmation rejects changed material, changed draft and read-only or in-flight operations',async()=>{
 for(const mutate of [h=>h.m.id='another',h=>h.m.draft.blocks[1].text='Concurrent edit',h=>h.m.busy=true,h=>h.m.collaboration.readonly=true]){
  const h=harness();h.n.selectedBlocks.add('intro');await h.n.action('bulk-delete',{});mutate(h);const before=structuredClone(h.m.draft.blocks);h.controls.get('[data-bulk-apply]').onclick();assert.deepEqual(h.m.draft.blocks,before);assert.equal(h.calls.length,0);assert.equal(h.dialog.closed,false);assert.ok(h.controls.get('[data-bulk-status]').textContent);
 }
});
test('bulk edits can change non-adjacent passages without merging their source ownership',async()=>{
 const h=harness();h.n.selectedBlocks=new Set(['intro','body']);await h.n.action('bulk-edit',{});
 h.dialog.querySelectorAll=()=>[{dataset:{bulkText:'intro'},value:'New introduction'},{dataset:{bulkText:'body'},value:'New body'}];
 h.controls.get('[data-bulk-apply]').onclick();assert.equal(h.m.draft.blocks[1].text,'New introduction');assert.equal(h.m.draft.blocks[4].text,'New body');assert.equal(h.m.draft.blocks[4].source_refs[0].anchor,'body');assert.equal(h.m.draft.blocks[4].parent_id,'section');assert.equal(h.calls.length,1);
});

test('selection mode exposes checkboxes and stops cleanly without edits',async()=>{
 const h=harness();await h.n.action('select-range',{});assert.equal(h.n.selecting,true);assert.match(h.n.documentMarkup(),/data-md-select="intro"/);h.n.pick('intro',true);await h.n.action('select-range',{});assert.equal(h.n.selecting,false);assert.equal(h.n.selectedBlocks.size,0);assert.equal(h.calls.length,0);
});
