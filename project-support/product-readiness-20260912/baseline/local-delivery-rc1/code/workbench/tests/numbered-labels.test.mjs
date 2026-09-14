import test from 'node:test';
import assert from 'node:assert/strict';
import {numberedText,orderMarkup,orderEditorMarkup,relationshipValueMarkup,relationshipEditor,differenceLabel} from '../ui/collaboration.js';
import {Materials} from '../ui/materials.js';

test('source prefixes suppress only their repeated display prefix and keep original source text byte-for-byte',()=>{
 const cases=[['§ 13 a.Fellesansvar','§ 13'],['§13a.Fellesansvar','§ 13'],['§ 13 a.Fellesansvar','§ 13 a'],['§\u00a0 13 a. <Heading>','§ 13'],['  § 13 a.Title\nMore  text','§13'],['1 Heading','1'],['1. Heading','1'],['1.Title','1.'],['(a)Title','(a)'],['1.1 Water','1.1']];
 for(const [text,number] of cases)assert.equal(numberedText(text,number),text,JSON.stringify([text,number]));
});

test('different human numbers and longer number tokens remain visible',()=>{
 for(const [text,number] of [['10 Heading','1'],['1.2 Heading','1'],['1.2 Heading','1.'],['§ 130 Heading','§ 13'],['§ 13ab Heading','§ 13'],['TEST1.10 Title','TEST1.1'],['§ 13 a.Title','TEST1.1'],['Title § 13','§ 13'],['1st place','1']])assert.equal(numberedText(text,number,' · '),`${number} · ${text}`);
 assert.equal(numberedText('','TEST1.1'),'TEST1.1');assert.equal(numberedText('Exact  text',''),'Exact  text');
});

test('order, related heading and block difference labels use one display rule without changing stored numbers',()=>{
 const heading={id:'h',type:'heading',numbering:'§ 13',text:'§ 13 a.<Fellesansvar>',level:1},child={id:'c',type:'text',text:'Work',parent_id:'h'},blocks=[heading,child],before=structuredClone(blocks),context={h:heading,c:child};
 const outputs=[orderMarkup(['h','c'],context),orderEditorMarkup(['h','c'],blocks),relationshipValueMarkup('h',{kind:'parent_id',context}),relationshipEditor({path:'/blocks/c/parent_id'},'h',blocks)];
 for(const html of outputs){assert.match(html,/§ 13 a\.&lt;Fellesansvar&gt;/);assert.doesNotMatch(html,/§ 13 · § 13|§ 13 § 13|<Fellesansvar>/);}
 assert.equal(differenceLabel({path:'/blocks/h',incoming:heading}),'§ 13 a.<Fellesansvar>');assert.deepEqual(blocks,before);
});

test('actual chapter, reading and parent/dependency option renderers preserve source and editable raw fields',()=>{
 const heading={id:'h',type:'heading',numbering:'§ 13',text:'§ 13 a.<Fellesansvar>',level:1,source_refs:[]},child={id:'c',type:'text',numbering:'TEST1.1',text:'§ 13 a.User note',parent_id:'h',dependencies:['h'],source_refs:[]};
 const x=Object.create(Materials.prototype),nodes=new Map();Object.assign(x,{root:{},collaboration:{readonly:false},material:{scope:[]},draft:{blocks:[heading,child]},updateBar(){},renderList(){},renderContent(){},q(s){if(!nodes.has(s))nodes.set(s,{});return nodes.get(s);}});const before=structuredClone(x.draft);
 x.renderMaterial();assert.match(nodes.get('#mw-content-tools').innerHTML,/<option value="0">§ 13 a\.&lt;Fellesansvar&gt;<\/option>/);
 assert.match(x.blockMarkup(heading,0),/<h4>§ 13 a\.&lt;Fellesansvar&gt;<\/h4>/);assert.match(x.blockMarkup(child,1),/TEST1\.1 § 13 a.User note/);
 const edit=x.editBlockMarkup(child,1);assert.match(edit,/<option value="h"[^>]*>§ 13 a\.&lt;Fellesansvar&gt;<\/option>/);assert.match(edit,/data-field="numbering" value="TEST1\.1"/);assert.match(edit,/>§ 13 a.User note<\/textarea>/);
 const raw=x.editBlockMarkup(heading,0);assert.match(raw,/data-field="numbering" value="§ 13"/);assert.match(raw,/>§ 13 a\.&lt;Fellesansvar&gt;<\/textarea>/);assert.deepEqual(x.draft,before);
});
