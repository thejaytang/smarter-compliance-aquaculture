
import {MarkdownNotebook,blockMarkdown,insertedDocumentBlock,updateMarkdownBlock} from '../../ui/markdown-content.js';
const out=document.querySelector('#results'),fixture=document.querySelector('#fixture');
let n,m,errors=[];
const base=()=>[
 {id:'h',type:'heading',level:1,text:'Original heading',source_refs:[{scope_id:'p1',anchor:'h'}]},
 {id:'a',type:'text',text:'Alpha bold 鱼 æ tail.',markdown_source:'Alpha **bold** 鱼 æ tail.',parent_id:'h',source_refs:[{scope_id:'p1',anchor:'a'}]},
 {id:'b',type:'text',text:'Repeat text.',parent_id:'h',source_refs:[{scope_id:'p2',anchor:'b'}]},
 {id:'c',type:'text',text:'Repeat text.',parent_id:'h',source_refs:[{scope_id:'p3',anchor:'c'}]}
];
function setup(blocks=base()){
 errors=[];m={draft:{blocks:structuredClone(blocks)},collaboration:{readonly:false},root:fixture,dirty:false,q:s=>fixture.querySelector(s),changed(){this.dirty=true;},message:s=>errors.push(s),renderContent(){fixture.innerHTML=n.documentMarkup();n.bind();},requirements:{start(id){m.intake=id;}}};n=new MarkdownNotebook(m);m.renderContent();return n.writer;
}
const check=(yes,message)=>{if(!yes)throw Error(message);};
const block=id=>fixture.querySelector(`[data-writing-block="${id}"]`);
function textNode(id,word){const w=document.createTreeWalker(block(id),NodeFilter.SHOW_TEXT);let node;while(node=w.nextNode())if(node.textContent.includes(word))return node;throw Error('Text not found: '+word);}
function select(a,ao,z=a,zo=ao){const r=document.createRange();r.setStart(a,ao);r.setEnd(z,zo);const s=getSelection();s.removeAllRanges();s.addRange(r);n.writer.root.focus();}
const tests=[];function test(name,run){tests.push([name,run]);}
test('Opening and no-op sync preserve Markdown byte for byte',()=>{const w=setup(),before=JSON.stringify(m.draft.blocks);w.sync();check(JSON.stringify(m.draft.blocks)===before,'No-op changed original');check(!m.dirty,'No-op dirtied draft');});
test('Replacement preserves bold, Unicode, baseline and source',()=>{const w=setup(),node=textNode('a','tail');select(node,node.textContent.indexOf('tail'),node,node.textContent.indexOf('tail')+4);w.remember();w.replaceText('中文 æ');check(blockMarkdown(m.draft.blocks[1])==='Alpha **bold** 鱼 æ 中文 æ.','Formatting/text lost');check(m.draft.blocks[1].markdown.baseline==='Alpha **bold** 鱼 æ tail.','Baseline lost');check(m.draft.blocks[1].source_refs[0].anchor==='a','Wrong source');});
test('Cross-paragraph deletion keeps prefix/suffix, original IDs and deleted baselines',()=>{const w=setup(),a=textNode('a','Alpha'),c=textNode('c','Repeat');select(a,3,c,7);w.remember();w.replaceText('JOIN');check(m.draft.blocks[1].text==='AlpJOINtext.','Wrong merged text: '+m.draft.blocks[1].text);check(m.draft.blocks[2].text===''&&m.draft.blocks[3].text==='','Removed passages not tombstones');check(m.draft.blocks[2].markdown.original.text==='Repeat text.','History missing');check(m.draft.blocks[1].source_refs.length===3,'Combined source context missing');w.travel(false);check(JSON.stringify(m.draft.blocks)===JSON.stringify(base()),'Undo did not restore exact blocks');w.travel(true);check(m.draft.blocks[1].text==='AlpJOINtext.','Redo failed');});
test('Enter splits a heading and keeps the new body paragraph under it',()=>{const w=setup(),node=textNode('h','Original');select(node,8);w.remember();w.split();check(m.draft.blocks[0].text==='Original','Heading split prefix');check(m.draft.blocks[1].text==='heading','Heading split suffix');check(m.draft.blocks[1].type==='text','New paragraph still heading');check(m.draft.blocks[1].parent_id==='h','Heading parent lost');check(m.draft.blocks[1].markdown.added,'New paragraph not marked added');});
test('Backspace joining paragraphs keeps source contexts and exact undo',()=>{const w=setup();w.remember();w.join(block('b'),block('c'));check(m.draft.blocks[2].text==='Repeat text.Repeat text.','Joined text incorrect');check(m.draft.blocks[3].text==='','Deleted block identity lost');check(m.draft.blocks[2].source_refs.length===2,'Joined source link missing');w.travel(false);check(JSON.stringify(m.draft.blocks)===JSON.stringify(base()),'Join undo lost evidence');});
test('Joining a list and paragraph preserves every list item and remaining paragraph text',()=>{
 const list={id:'l',type:'text',text:'- first\n- second',source_refs:[{scope_id:'p1'}]},w=setup([list,...base()]);w.remember();w.join(block('l'),block('h'));
 check(m.draft.blocks[0].text.includes('first')&&m.draft.blocks[0].text.includes('secondOriginal heading'),'List boundary lost text');check(blockMarkdown(m.draft.blocks[0]).includes('- secondOriginal heading'),'List marker lost');
 w.travel(false);select(textNode('l','second'),3,textNode('a','tail'),5);w.remember();w.replaceText('JOIN');check(m.draft.blocks[0].text.includes('secJOINtail.'),'Cross-list selection lost replacement or suffix: '+m.draft.blocks[0].text);
});
test('Select-all deletion remains editable and reversible',()=>{const w=setup(),r=document.createRange();r.selectNodeContents(w.root);getSelection().removeAllRanges();getSelection().addRange(r);w.remember();w.replaceText('');check(m.draft.blocks.every(b=>b.text===''),'Some body survived');check(w.root.children.length===1,'No editable empty paragraph');w.replaceText('Replacement');check(m.draft.blocks[0].text==='Replacement','Cannot type after whole deletion');w.travel(false);check(JSON.stringify(m.draft.blocks)===JSON.stringify(base()),'Select all undo lost original');});
test('A deleted document remains editable after a mode rerender',()=>{
 const w=setup(),r=document.createRange();r.selectNodeContents(w.root);getSelection().removeAllRanges();getSelection().addRange(r);w.remember();w.replaceText('');m.renderContent();
 const b=block('h');select(b,0);n.writer.replaceText('Restored typing');check(m.draft.blocks[0].text==='Restored typing','Empty body failed after rerender');
});
test('A metadata-only document starts a new source-bound body on first input only',()=>{
 const info={id:'info',role:'document_information',type:'text',text:'Document title',source_refs:[{scope_id:'p1'}]},w=setup([info]);w.sync();check(m.draft.blocks.length===1&&!m.dirty,'Opening created a body write');
 select(w.root.firstElementChild,0);w.remember();w.replaceText('New body');check(m.draft.blocks.length===2&&m.draft.blocks[1].text==='New body','First typing lost');check(m.draft.blocks[1].markdown.added,'Body not marked as human addition');
});
test('Insertion choices are ordered before/after and remain unsaved',async()=>{const w=setup();w.showTools(block('b'));await w.action('above');await w.action('insert-h2');check(m.draft.blocks[2].type==='heading'&&m.draft.blocks[2].level===2,'H2 not inserted before');check(m.draft.blocks[3].id==='b','Original order changed');check(m.dirty,'Insertion not dirty');check(!m.intake,'Implicit intake occurred');});
test('Table edits preserve captions and notes, add/delete rows and columns without merges',async()=>{
 const table={id:'t',type:'table',text:'Caption',table:{rows:[['A','B'],['one','two']],notes:['Note'],merges:[]},source_refs:[{scope_id:'p1',anchor:'table'}]};let w=setup([...base(),table]);
 const use=()=>{w=n.writer;w.showTools(block('t'),block('t').querySelector('td'));};
 use();check(parseFloat(getComputedStyle(w.controls.querySelector('.md-table-row')).top)>0,'Row controls blocked by CSP');check(parseFloat(getComputedStyle(w.controls.querySelector('.md-table-column')).left)>0,'Column controls blocked by CSP');await w.action('row-after');check(m.draft.blocks.at(-1).table.rows.length===3,'Row not added');
 use();await w.action('col-after');check(m.draft.blocks.at(-1).table.rows[0].length===3,'Column not added');
 use();await w.action('row-delete');use();await w.action('col-delete');
 const b=m.draft.blocks.at(-1);check(b.table.rows.length===2&&b.table.rows[0].length===2,'Dimensions incorrect');check(blockMarkdown(b).includes('Caption')&&blockMarkdown(b).includes('Note'),'Caption/notes lost');check(!b.table.merges.length,'Merged cell introduced');check(b.markdown.original.table.rows[1][0]==='one','Original table lost');
});
test('Text selection across table cells leaves a rectangular source table',()=>{
 const table={id:'t',type:'table',text:'',table:{rows:[['A','B'],['one','two'],['three','four']],notes:[],merges:[]},source_refs:[{scope_id:'p1'}]},w=setup([...base(),table]);
 const cells=block('t').querySelectorAll('td');select(cells[0].firstChild,1,cells[3].firstChild,2);w.remember();w.replaceText('X');
 const b=m.draft.blocks.at(-1);check(b.type==='table'&&b.table.rows.every(row=>row.length===2),'Non-rectangular table');check(!b.table.merges.length,'Merge created');w.travel(false);check(JSON.stringify(m.draft.blocks.at(-1))===JSON.stringify(table),'Table selection undo changed original');
});
test('Dirty intake is blocked; clean intake uses the source block ID',async()=>{const w=setup();w.showTools(block('a'));m.dirty=true;await w.action('requirement');check(!m.intake&&errors.at(-1).includes('Save content first'),'Unsaved intake not guarded');m.dirty=false;await w.action('requirement');check(m.intake==='a','Wrong intake ID');});
test('Save/loading lock prevents browser edits and table actions',async()=>{const w=setup();w.showTools(block('b'));m.busy=true;let prevented=false;w.beforeInput({inputType:'insertText',preventDefault(){prevented=true;}});await w.action('below');check(prevented&&!w.insertAt,'In-flight mutation allowed');});
test('Unsafe pasted-looking text stays inert after rendering',()=>{const w=setup(),node=textNode('b','Repeat');select(node,0,node,node.length);w.remember();w.replaceText('<img src=x onerror=alert(1)> 鱼');m.renderContent();check(!fixture.querySelector('img,script'),'Executable element created');check(m.draft.blocks[2].text.includes('<img'),'Literal text lost');});
test('Missing structural IDs fail closed instead of overwriting another source',()=>{const w=setup(),before=JSON.stringify(m.draft.blocks);block('b').removeAttribute('data-writing-block');w.sync();check(errors.length===1,'Missing identity not reported');check(JSON.stringify(m.draft.blocks)===before,'Wrong source overwritten');});
document.querySelector('#run').onclick=async()=>{const lines=[];for(const [name,run] of tests){try{await run();lines.push('PASS '+name);}catch(e){lines.push('FAIL '+name+': '+e.message);}}out.textContent=lines.join('\n')+'\n'+lines.filter(s=>s.startsWith('PASS')).length+'/'+tests.length+' passed';setup();};
setup();
