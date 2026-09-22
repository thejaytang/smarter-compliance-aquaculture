import test from 'node:test';
import assert from 'node:assert/strict';
import {blockMarkdown,updateMarkdownBlock,updateTableBlock,MarkdownNotebook,ContinuousDocument,editableMarkdown} from '../frontend/components/markdown-content.js';
import {tableAxis,pasteTableCells} from '../frontend/components/material-editing.js';
const image=()=>({id:'image',type:'image',text:'Caption\ncontinued caption',source_refs:[{scope_id:'page:1'}],image:{attachment:'fixture.png',attribution:'Original credit',source_ref:{scope_id:'page:1',bbox:[0,0,40,40]}}});
const table=()=>({id:'table',type:'table',text:'Current caption',source_refs:[{scope_id:'page:1'}],table:{rows:[['A','B','C'],['D','E','F'],['G','H','I']],merges:[{row:0,col:0,rowspan:1,colspan:2}],notes:['Keep note one','Keep note two']}});
test('image caption-only and attribution-only edits retain the current attachment and source range',()=>{
 const before=image(),source=blockMarkdown(before),next=updateMarkdownBlock([before],'image',source.replace('Caption','Corrected caption'))[0];
 assert.equal(next.type,'image');assert.equal(next.text,'Corrected caption\ncontinued caption');assert.deepEqual(next.image,before.image);assert.deepEqual(next.source_refs,before.source_refs);assert.deepEqual(next.markdown.original,before);
 const credited=updateMarkdownBlock([next],'image',blockMarkdown(next).replace('Original credit','Corrected credit'))[0];assert.equal(credited.image.attribution,'Corrected credit');assert.equal(credited.text,next.text);
 const natural=updateMarkdownBlock([before],'image','Imagery of the facility')[0];assert.equal(natural.text,'Imagery of the facility');assert.deepEqual(natural.image,before.image);
 assert.equal(updateMarkdownBlock([before],'image','')[0].type,'text');assert.equal(before.text,'Caption\ncontinued caption');
});
test('cell-only changes keep current table caption, merges, notes and neighbouring values exactly',()=>{
 const before=table(),next=updateMarkdownBlock([before],'table',blockMarkdown(before).replace('| D | E | F |','| D | Fixed | F |'))[0];
 assert.equal(next.text,before.text);assert.deepEqual(next.table,{...before.table,rows:[before.table.rows[0],['D','Fixed','F'],before.table.rows[2]]});assert.deepEqual(next.source_refs,before.source_refs);assert.deepEqual(next.markdown.original,before);
 const later=updateMarkdownBlock([next],'table',blockMarkdown(next).replace('Current caption','Revised caption'))[0];const final=updateMarkdownBlock([later],'table',blockMarkdown(later).replace('Fixed','Again'))[0];assert.equal(final.text,'Revised caption');assert.deepEqual(final.table.notes,before.table.notes);
 assert.throws(()=>updateMarkdownBlock([before],'table','Malformed but nonempty table'),/rectangular rows/);assert.deepEqual(before,table());
});
test('structured row and column edits adjust only merge geometry and undo can restore exact table',()=>{
 const before=table(),added=updateTableBlock([before],'table',tableAxis(before.table,'row',0))[0];assert.equal(added.table.merges[0].row,1);assert.equal(added.table.rows[1][0],'A');assert.equal(added.text,before.text);assert.deepEqual(added.table.notes,before.table.notes);assert.deepEqual(added.markdown.original,before);
 const same=tableAxis(added.table,'row',0,true);assert.deepEqual(same,before.table);
});
test('rectangular TSV paste preserves neighbours and literal script-looking text, rejecting ragged/oversized grids atomically',()=>{
 const before=table().table,next=pasteTableCells(before,1,1,'<script>\tB\tC\nD\tE\tF');assert.deepEqual(next.rows,[['A','B','C',''],['D','<script>','B','C'],['G','D','E','F']]);assert.deepEqual(next.notes,before.notes);assert.deepEqual(next.merges,before.merges);assert.deepEqual(before,table().table);
 assert.throws(()=>pasteTableCells(before,1,1,'x\ty\nz'),/rectangular/);assert.throws(()=>pasteTableCells(before,1,1,Array(100001).fill('x').join('\t')),/100,000/);assert.equal(pasteTableCells(before,0,0,'Ordinary prose\nwith a newline'),null);
});
test('Current and Changes use one chronological in-memory history and mode switches do not add edits',()=>{
 const nodes=new Map(),m={id:'synthetic',collaboration:{readonly:false},draft:{blocks:[{id:'p',type:'text',text:'Original',source_refs:[{scope_id:'p1'}]}]},q:s=>nodes.get(s),changed(){},renderContent(){}};
 const n=new MarkdownNotebook(m);n.writer.remember();m.draft.blocks=updateMarkdownBlock(m.draft.blocks,'p','Current A');n.mode='changes';n.editing='p';n.change('p','Changes B');assert.equal(n.writer.undo.length,2);n.mode='current';assert.equal(n.writer.undo.length,2);n.writer.travel(false);assert.equal(m.draft.blocks[0].text,'Current A');n.writer.travel(true);assert.equal(m.draft.blocks[0].text,'Changes B');assert.deepEqual(m.draft.blocks[0].source_refs,[{scope_id:'p1'}]);n.reset();assert.equal(n.writer.undo.length,0);
});
test('table action uses the source-bound cell destination, preserving scroll and one undo record',async()=>{
 const b=table(),host={scrollTop:240},m={draft:{blocks:[b]},collaboration:{readonly:false},q:()=>host,changed(){},renderContent(){}},w=new ContinuousDocument({m});w.active={dataset:{writingBlock:'table'}};w.tableCell={isConnected:true};w.cellPosition={row:1,col:1};let restored;w.restoreCell=(...args)=>{restored=args;host.scrollTop=0;};
 await w.action('row-after');assert.deepEqual(restored,['table',2,1]);assert.equal(host.scrollTop,240);assert.equal(w.undo.length,1);assert.deepEqual(m.draft.blocks[0].table.notes,b.table.notes);w.travel(false);assert.deepEqual(m.draft.blocks,[b]);
});
function controls(){
 const f={writes:0,menu:null,buttons:new Map(),style:{},hidden:true,focus:null};
 const button=action=>({dataset:{writeAction:action},focus(){f.focus=this;}});
 Object.defineProperty(f,'innerHTML',{set(value){f.writes++;f.html=value;f.menu=null;f.buttons=new Map([...value.matchAll(/data-write-action="([^"]+)"/g)].map(m=>[m[1],button(m[1])]));},get(){return f.html;}});
 f.insertAdjacentHTML=(where,html)=>{assert.equal(f.menu,null);f.menu={html,button:button('insert-text'),remove(){f.menu=null;}};};
 f.querySelector=selector=>selector==='.md-insert-menu'?f.menu:selector==='.md-insert-menu button'?f.menu?.button:f.buttons.get(selector.match(/data-write-action="([^"]+)"/)?.[1]);return f;
}
test('passage controls preserve nodes until their source target or action availability changes',()=>{
 const m={draft:{blocks:[{id:'a',type:'text',text:'A'},{id:'b',type:'text',text:'B'}]},collaboration:{readonly:false}},w=new ContinuousDocument({m}),a={dataset:{writingBlock:'a'}},b={dataset:{writingBlock:'b'}};w.root={contains:()=>true};w.controls=controls();w.positionTools=()=>{};
 w.showTools(a);const trigger=w.controls.querySelector('[data-write-action="above"]');trigger.focus();for(let i=0;i<10;i++)w.showTools(a);assert.equal(w.controls.writes,1);assert.equal(w.controls.focus,trigger);w.showTools(b);assert.equal(w.controls.writes,2);assert.equal(w.active,b);m.dirty=true;w.showTools(b);assert.equal(w.controls.writes,3);
});
test('insertion chooser toggles and switches one position, cancel restores its trigger without any edit',async()=>{
 const m={draft:{blocks:[{id:'a',type:'text',text:'A',source_refs:[{scope_id:'page:1'}]}]},collaboration:{readonly:false}},w=new ContinuousDocument({m});w.root={contains:()=>true};w.controls=controls();w.positionTools=()=>{};w.active={dataset:{writingBlock:'a'}};w.showTools(w.active);
 const before=structuredClone(m.draft.blocks);await w.action('above');assert.equal(w.insertAt.after,false);assert.match(w.controls.menu.html,/Insert above/);await w.action('below');assert.equal(w.insertAt.after,true);assert.match(w.controls.menu.html,/Insert below/);assert.equal(w.controls.writes,1);await w.action('cancel');assert.equal(w.controls.menu,null);assert.equal(w.controls.focus,w.controls.buttons.get('below'));assert.deepEqual(m.draft.blocks,before);assert.equal(w.undo.length,0);
 await w.action('above');await w.action('above');assert.equal(w.controls.menu,null);assert.equal(w.controls.focus,w.controls.buttons.get('above'));
});
test('table Tab walks existing cells and yields at each boundary without draft or history changes',()=>{
 const m={draft:{blocks:[table()]},collaboration:{readonly:false}},w=new ContinuousDocument({m});const t={rows:[]};for(let r=0;r<2;r++){const row={cells:[]};for(let c=0;c<3;c++)row.cells.push({parentElement:row,cellIndex:c,closest:()=>t});t.rows.push(row);}let cell=t.rows[0].cells[0];w.currentCell=()=>cell;w.caret=n=>cell=n;w.block=()=>({});w.showTools=()=>{};const before=structuredClone(m.draft.blocks);
 assert.equal(w.moveCell(true),false);for(let i=1;i<6;i++){assert.equal(w.moveCell(),true);assert.equal(cell,t.rows[Math.floor(i/3)].cells[i%3]);}assert.equal(w.moveCell(),false);for(let i=4;i>=0;i--){assert.equal(w.moveCell(true),true);assert.equal(cell,t.rows[Math.floor(i/3)].cells[i%3]);}assert.equal(w.undo.length,0);assert.deepEqual(m.draft.blocks,before);
});
test('an explicit list value blocks structure changes before draft mutation or an undo entry',()=>{
 const m={draft:{blocks:[]},collaboration:{readonly:false},message(text){this.error=text;}},w=new ContinuousDocument({m});w.range=()=>({collapsed:true,startContainer:{nodeType:1,closest:()=>({parentElement:{querySelector:()=>({value:12})}})}});let prevented=0;w.beforeInput({inputType:'insertParagraph',preventDefault(){prevented++;}});assert.equal(prevented,1);assert.equal(w.undo.length,0);assert.deepEqual(m.draft.blocks,[]);assert.match(m.error,/explicit item numbers/);
});
