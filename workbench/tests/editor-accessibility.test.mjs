import test from 'node:test';
import assert from 'node:assert/strict';
import {Materials} from '../frontend/components/materials.js';

function fixture(){const x=new Materials();x.material={scope:[{id:'page:1',label:'Page 1'}]};x.draft={blocks:[{id:'heading-1',type:'heading',level:1,numbering:'1',text:'Heading',source_refs:[]},{id:'text-1',type:'text',numbering:'TEST1.1',text:'Retained <manual text>',parent_id:'heading-1',dependencies:['heading-1'],source_refs:[{scope_id:'page:1',locator:'/body/p[1]'}]}]};return x;}
function fields(html){const labels=new Map([...html.matchAll(/<label\b([^>]*)>([^<]*)/g)].flatMap(([,attributes,text])=>{const id=attributes.match(/\bfor="([^"]+)"/);return id?[[id[1],text]]:[]}));return [...html.matchAll(/<(input|select|textarea)\b([^>]*)>/g)].map(([,tag,attributes])=>{const field=attributes.match(/data-field="([^"]+)"/),id=attributes.match(/\bid="([^"]+)"/),aria=attributes.match(/aria-label="([^"]+)"/);return {tag,field:field?.[1],id:id?.[1],label:labels.get(id?.[1]),aria:aria?.[1]};}).filter(item=>item.field);}

test('editor controls have explicit unique label associations and exact text/heading accessible names',()=>{
 const x=fixture(),before=structuredClone(x.draft),text=x.editBlockMarkup(x.draft.blocks[1],1),heading=x.editBlockMarkup(x.draft.blocks[0],0),expected={type:'Type',numbering:'Original number',parent_id:'Under heading',text:'Original text',scope:'Original range','location-detail':'Location detail',dependencies:'Related blocks'};
 for(const field of fields(text)){assert.ok(field.id,field.field);assert.equal(field.label,expected[field.field]);if(field.field==='text')assert.equal(field.aria,'Original text');}
 const headingFields=fields(heading);assert.equal(headingFields.find(f=>f.field==='text').aria,'Heading text');assert.equal(headingFields.find(f=>f.field==='text').label,'Heading text');assert.equal(headingFields.find(f=>f.field==='level').label,'Level');const all=[...fields(text),...headingFields];assert.equal(new Set(all.map(f=>f.id)).size,all.length);assert.deepEqual(x.draft,before);
 assert.match(text,/data-field="text"[^>]*>Retained &lt;manual text&gt;<\/textarea>/);assert.match(text,/data-field="numbering" value="TEST1\.1"/);assert.match(text,/data-field="location-detail" value="\/body\/p\[1\]"/);
});

test('label IDs stay stable after reorder and encode hostile block IDs without injecting attributes',()=>{
 const x=fixture(),block=x.draft.blocks[1];block.id='a" onfocus="bad <tag> / 中文';const first=x.editBlockMarkup(block,1);x.draft.blocks.reverse();const reordered=x.editBlockMarkup(block,0);assert.deepEqual(fields(first).map(f=>f.id),fields(reordered).map(f=>f.id));assert.ok(fields(first).every(f=>f.id&&!/\s|<|>/.test(f.id)));assert.doesNotMatch(first,/<tag>|\sonfocus="bad/);assert.ok(fields(first).every(f=>f.label));
});

test('explicit label IDs do not change original data-field editing or source-location writes',()=>{
 const x=fixture(),block=x.draft.blocks[1];let changes=0;x.changed=()=>changes++;const node={tagName:'TEXTAREA',id:'mw-block-text-1-text',dataset:{field:'text'},value:'Corrected clause',closest:()=>({dataset:{block:block.id}})};x.editInput({target:node});assert.equal(block.text,'Corrected clause');assert.equal(block.numbering,'TEST1.1');node.tagName='INPUT';node.id='mw-block-text-1-location-detail';node.dataset.field='location-detail';node.value='/body/p[2]';x.editInput({target:node});assert.equal(block.source_refs[0].locator,'/body/p[2]');assert.equal(block.text,'Corrected clause');assert.equal(changes,2);
});
