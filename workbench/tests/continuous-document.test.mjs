import test from 'node:test';
import assert from 'node:assert/strict';
import {MarkdownNotebook,blockMarkdown,reconcileDocument,insertedDocumentBlock,editableMarkdown} from '../ui/markdown-content.js';
const blocks=()=>[
 {id:'info',role:'document_information',type:'text',text:'Identity',source_refs:[]},
 {id:'h',type:'heading',level:1,text:'Heading',source_refs:[{scope_id:'page:1'}]},
 {id:'a',type:'text',text:'Repeat 鱼 æ',parent_id:'h',source_refs:[{scope_id:'page:1',anchor:'a'}]},
 {id:'b',type:'text',text:'Repeat 鱼 æ',parent_id:'h',source_refs:[{scope_id:'page:2',anchor:'b'}]}
];
test('continuous edits retain removed IDs and original baselines without confusing repeated text',()=>{
 const original=blocks();const next=reconcileDocument(original,[{id:'h',source:'# Heading'},{id:'b',source:'Changed **鱼 æ**'}]);
 assert.deepEqual(next.map(b=>b.id),original.map(b=>b.id));assert.equal(next[2].text,'');assert.equal(next[3].text,'Changed 鱼 æ');
 assert.deepEqual(next[2].markdown.original,original[2]);assert.deepEqual(next[3].source_refs,original[3].source_refs);
 assert.deepEqual(next[0],original[0]);assert.equal(original[2].text,'Repeat 鱼 æ');
 assert.throws(()=>reconcileDocument(original,[{id:'a',source:'a'},{id:'a',source:'b'}]),/structure changed/);
 assert.throws(()=>reconcileDocument(original,[{id:'other',source:'oops'}]),/structure changed/);
});
test('empty document is reversible and preserves all original locations',()=>{
 const original=blocks(),next=reconcileDocument(original,[]);
 assert.deepEqual(next[0],original[0]);
 for(let i=1;i<next.length;i++){assert.equal(next[i].text,'');assert.deepEqual(next[i].source_refs,original[i].source_refs);assert.equal(next[i].markdown.baseline,blockMarkdown(original[i]));}
});
test('inserted Context, H1, H2 and Table retain context without pretending to be original',()=>{
 for(const kind of ['text','h1','h2','table']){
  const near=blocks()[1],b=insertedDocumentBlock(near,kind,'new-'+kind);
  assert.equal(b.parent_id,'h');assert.deepEqual(b.source_refs,near.source_refs);assert.equal(b.markdown.baseline,'');assert.equal(b.markdown.added,true);
  if(kind==='table'){assert.deepEqual(b.table.rows,[['Column 1','Column 2'],['','']]);assert.deepEqual(b.table.merges,[]);}
  if(kind==='h1'||kind==='h2')assert.equal(b.level,Number(kind[1]));
 }
});
test('default document is one editing surface and excludes metadata and controls from editable text',()=>{
 const nb=new MarkdownNotebook({draft:{blocks:blocks()},collaboration:{readonly:false}}),html=nb.documentMarkup();
 assert.match(html,/contenteditable="true"/);assert.match(html,/data-writing-block="a"/);assert.doesNotMatch(html,/data-writing-block="info"|<textarea|Select passages/);
 assert.match(html,/<\/div><div class="md-writing-controls"/);
 nb.m.collaboration.readonly=true;assert.doesNotMatch(nb.documentMarkup(),/contenteditable="true"/);
});
// Small DOM-shaped fixtures exercise serialization without a browser dependency.
const text=s=>({nodeType:3,nodeValue:s,textContent:s});
const el=(tag,...nodes)=>({nodeType:1,nodeName:tag.toUpperCase(),childNodes:nodes,children:nodes.filter(n=>n.nodeType===1),textContent:nodes.map(n=>n.textContent).join(''),getAttribute:()=>null});
test('editable serialization retains formatting, Unicode, literal HTML and explicit list ordering',()=>{
 assert.equal(editableMarkdown(el('p',text('魚 æ '),el('strong',text('must')),text(' <script>'))).trim(),'魚 æ **must** \\<script\\>');
 assert.equal(editableMarkdown(el('h2',text('Heading'))).trim(),'## Heading');
 assert.equal(editableMarkdown(el('ul',el('li',text('one')),el('li',text('two')))).trim(),'- one\n- two');
 const anchor=el('a',text('safe'));anchor.getAttribute=()=> 'javascript:alert(1)';assert.equal(editableMarkdown(anchor),'safe');
 assert.equal(editableMarkdown(el('script',text('attack()'))),'');
});
