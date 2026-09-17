import test from 'node:test';
import assert from 'node:assert/strict';
import {blockMarkdown,markdownText,renderMarkdown,renderChanges,updateMarkdownBlock,formatSelection,MarkdownNotebook} from '../frontend/components/markdown-content.js';
const paragraph=()=>({id:'p',type:'text',text:'The fish shall swim.',source_refs:[{scope_id:'page:2',page:2}],parent_id:'h',dependencies:[]});
const heading=()=>({id:'h',type:'heading',text:'Chapter 2',level:1,source_refs:[{scope_id:'page:2',page:2}]});
test('saved cells render as source-ordered headings, lists and simple tables',()=>{
 assert.equal(blockMarkdown(heading()),'# Chapter 2');
 assert.match(renderMarkdown(blockMarkdown({...paragraph(),text:'- Alpha\n- Beta'})),/<ul>/);
 const table={id:'t',type:'table',text:'',table:{rows:[['A','B'],['x | y','z']],notes:['Note']}};
 const source=blockMarkdown(table);assert.match(source,/x \\\| y/);assert.match(renderMarkdown(source),/<table>/);assert.match(renderMarkdown(source),/>x \| y</);
});
test('text replacement uses inline added and removed marks and preserves bold',()=>{
 const html=renderChanges('The **fish** shall swim.','The **fish** shall wait.');
 assert.match(html,/<strong>fish<\/strong>/);assert.match(html,/<del class="md-removed"[^>]*>swim<\/del>/);assert.match(html,/<ins class="md-added"[^>]*>wait<\/ins>/);
 assert.doesNotMatch(html,/md-whole/);
});
test('table cell difference retains one table and unchanged neighbours',()=>{
 const before='| A | B |\n| --- | --- |\n| 10 | keep |',after=before.replace('10','20');
 const html=renderChanges(before,after);assert.equal((html.match(/<table>/g)||[]).length,1);assert.match(html,/md-removed/);assert.match(html,/>keep<\/td>/);
});
test('whole deletion remains visible and additions have their own mark',()=>{
 assert.match(renderChanges('## Removed',''),/md-removed md-whole/);assert.match(renderChanges('','New paragraph'),/md-added md-whole/);
});
test('raw HTML, script URLs and remote images do not execute or load',()=>{
 for(const src of ['<script>alert(1)</script>','<img src=x onerror=alert(1)>','[x](javascript:alert(1))','![secret](https://outside.invalid/track)']){
 const html=renderChanges('safe',src);assert.doesNotMatch(html,/<script|<img|href="javascript:/i);
 }
 assert.match(renderMarkdown('~~original strike~~'),/<s>original strike<\/s>/);assert.doesNotMatch(renderMarkdown('~~original strike~~'),/md-removed/);
});
test('Markdown conversion preserves source links and baseline across saves',()=>{
 const original=[heading(),paragraph()];let blocks=updateMarkdownBlock(original,'p','The **fish** shall wait.');
 assert.equal(blocks[1].text,'The fish shall wait.');assert.deepEqual(blocks[1].source_refs,original[1].source_refs);assert.deepEqual(blocks[1].markdown.original,original[1]);assert.equal(original[1].text,'The fish shall swim.');
 blocks=updateMarkdownBlock(JSON.parse(JSON.stringify(blocks)),'p','The **fish** shall sleep.');assert.equal(blocks[1].markdown.baseline,'The fish shall swim.');assert.equal(blocks[1].text,'The fish shall sleep.');
});
test('deleted text is excluded from requirement intake; changed headings repair parent links',()=>{
 const deleted=updateMarkdownBlock([heading(),paragraph()],'p','');assert.equal(deleted[1].text,'');assert.equal(deleted[1].markdown.baseline,'The fish shall swim.');
 const result=updateMarkdownBlock([heading(),paragraph()],'h','Plain heading');assert.equal(result[0].type,'text');assert.equal(result[1].parent_id,null);
});
test('plain output retains Unicode, negation, list numbers and table values',()=>{
 assert.equal(markdownText('The **鱼🐟** shall **not remove** fish.'),'The 鱼🐟 shall not remove fish.');
 assert.match(markdownText('3. Three\n4. Four'),/^3\. Three\n+4\. Four$/);
 assert.match(markdownText('| A | B |\n| --- | --- |\n| 10 | 20 |'),/A\tB\n10\t20/);
});
test('formatting touches only the selected text or selected lines',()=>{
 assert.equal(formatSelection('one two three',4,7,'bold').source,'one **two** three');
 assert.equal(formatSelection('one\ntwo',0,7,'numbered').source,'1. one\n2. two');
});
test('document blocks open as rendered Markdown without editor forms',()=>{
 const m={collaboration:{readonly:false},draft:{blocks:[paragraph()]},root:{querySelectorAll:()=>[]}};const nb=new MarkdownNotebook(m);
 const html=nb.markup(paragraph(),0);assert.match(html,/data-md-cell="p"/);assert.doesNotMatch(html,/<textarea|<select|mw-block-fields|md-cell-tools/);
 nb.editing='p';assert.match(nb.markup(paragraph(),0),/<textarea[^>]+aria-label="Markdown block 1"/);
 m.collaboration.readonly=true;assert.doesNotMatch(nb.markup(paragraph(),0),/<textarea|data-md-action="edit"/);
});
test('change guards and undo keep editor text and draft synchronized',()=>{
 let changes=0;const area={focus(){},value:''};const m={collaboration:{readonly:false},draft:{blocks:[paragraph()]},changed:()=>changes++,q:()=>area};const nb=new MarkdownNotebook(m);nb.editing='p';
 nb.change('p','Changed once.');nb.change('p','Changed twice.');nb.travel(-1);assert.equal(m.draft.blocks[0].text,'Changed once.');assert.equal(area.value,'Changed once.');nb.travel(1);assert.equal(m.draft.blocks[0].text,'Changed twice.');
 m.busy=true;nb.change('p','Lost?');assert.equal(m.draft.blocks[0].text,'Changed twice.');assert.equal(changes,4);
});

test('complete Markdown renders every block with nested sections and in-place diffs',()=>{
 const blocks=[heading(),{...heading(),id:'sub',text:'Scope',level:2},...Array.from({length:90},(_,i)=>({...paragraph(),id:'p'+i,text:'Paragraph '+i,parent_id:'sub'})),{...heading(),id:'next',text:'Next chapter',level:1}, {...paragraph(),id:'end',text:'Final paragraph',parent_id:'next'}];
 const m={collaboration:{readonly:false},draft:{blocks:updateMarkdownBlock(blocks,'p89','Edited paragraph 89')}};const nb=new MarkdownNotebook(m);nb.mode="changes";nb.showChanges=true;const html=nb.documentMarkup();
 assert.equal((html.match(/data-md-cell=/g)||[]).length,blocks.length);assert.match(html,/Final paragraph/);
 assert.match(html,/<section[^>]+data-section="h"[\s\S]*<section[^>]+data-section="sub"/);
 assert.match(html,/<\/section><\/section><section[^>]+data-section="next"/);
 assert.match(html,/class="md-removed"/);assert.match(html,/class="md-added"/);
 assert.doesNotMatch(html,/Previous blocks|Next blocks|md-cell-number/);
 assert.equal((html.match(/Complete extracted Markdown/g)||[]).length,1);
});
