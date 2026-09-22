import test from 'node:test';
import assert from 'node:assert/strict';
import {showEvidence} from '../frontend/components/evidence-viewer.js';
class Element{
 constructor(tag){this.tag=tag;this.children=[];this.style={};this.attributes={};this.isConnected=true;}
 append(...items){this.children.push(...items);}
 replaceChildren(){this.children=[];}
 setAttribute(k,v){this.attributes[k]=v;}
 cloneNode(){return Object.assign(new Element(this.tag),{src:this.src,alt:this.alt});}
 showModal(){this.open=true;}
 close(){this.open=false;}
}
async function withDocument(run){const previous=globalThis.document;globalThis.document={createElement:tag=>new Element(tag)};try{await run();}finally{globalThis.document=previous;}}
const all=element=>[element,...element.children.flatMap(all)];
const find=(host,tag,text)=>all(host).find(e=>e.tag===tag&&(text===undefined||e.textContent===text));
const sheet=(row=1,column=1,rows=90,columns=30)=>({kind:'spreadsheet',label:'Cells',sheets:['Æ worksheet'],sheet:'Æ worksheet',row,column,rows,columns,state:'visible',merged:[],cells:[]});
test('registered HTML uses the returned complete safe document in an isolated frame',()=>withDocument(async()=>{
 const host=new Element('main'),html='<!doctype html><html><body><h1>Preserved</h1><ul><li>Scope</li></ul><table><tr><td>1</td></tr></table></body></html>',calls=[];
 await showEvidence(host,'FX001',async url=>{calls.push(url);return {kind:'html',html,label:'Simplified HTML',source_sha256:'a'.repeat(64)};});
 const frame=find(host,'iframe');assert.equal(frame.srcdoc,undefined);assert.equal(frame.src,'/api/preview/FX001?view=html&expected_hash='+'a'.repeat(64));assert.equal(frame.attributes.sandbox,'');assert.equal(frame.attributes.referrerpolicy,'no-referrer');assert.equal(frame.title,'Simplified HTML reading view');assert.match(calls[0],/^\/api\/preview\/FX001\?/);
}));
test('shared spreadsheet bounds prevent no-op reads and preserve the selected source and worksheet',()=>withDocument(async()=>{
 const host=new Element('main'),calls=[];let result=sheet();const api=async url=>{calls.push(url);return result;};
 await showEvidence(host,'FX Æ',api);
 for(const name of ['Previous rows','Previous columns']){const button=find(host,'button',name);assert.equal(button.disabled,true);await button.onclick();}assert.equal(calls.length,1);
 result=sheet(41,13);await find(host,'button','Next rows').onclick();assert.equal(new URL(calls.at(-1),'http://local').searchParams.get('row'),'41');assert.equal(new URL(calls.at(-1),'http://local').searchParams.get('sheet'),'Æ worksheet');assert.match(calls.at(-1),/FX%20%C3%86/);
 assert.equal(find(host,'button','Previous rows').disabled,false);assert.equal(find(host,'button','Next columns').disabled,false);
 result=sheet(81,25);await showEvidence(host,'FX Æ',api);assert.equal(find(host,'button','Next rows').disabled,true);assert.equal(find(host,'button','Next columns').disabled,true);
 result=sheet(1,1,10,5);await showEvidence(host,'FX Æ',api);assert.equal(all(host).filter(e=>e.tag==='button'&&e.disabled).length,4);
}));
test('failed region images retain independent HTML and retry the same binding, rejecting late events',()=>withDocument(async()=>{
 const host=new Element('main'),calls=[],options={documentId:'document-r3',unitId:'unit-r3',references:[{page:2}],full:false,locator:'page 2',page:2};
 const api=async url=>{calls.push(url);return {kind:'html_region',image:'data:image/png;base64,broken',html:'<p>Independent assistance</p>',label:'Bound page 2'};};
 await showEvidence(host,'FX003',api,options);const oldImage=find(host,'img'),enlarge=find(host,'button','Enlarge original region');assert.equal(enlarge.disabled,true);
 oldImage.onerror();assert.equal(enlarge.disabled,true);assert.equal(find(host,'iframe').srcdoc,'<p>Independent assistance</p>');const alert=all(host).find(e=>e.attributes.role==='alert');assert.equal(alert.hidden,false);
 await enlarge.onclick();assert.equal(find(host,'dialog').open,undefined);
 await find(host,'button','Retry original region').onclick();assert.equal(calls.length,2);assert.equal(calls[0],calls[1]);assert.equal(new URL(calls[1],'http://local').searchParams.get('unit_id'),'unit-r3');
 const newImage=find(host,'img');newImage.onload();assert.equal(find(host,'button','Enlarge original region').disabled,false);
 const currentChildren=host.children;oldImage.onerror();assert.equal(host.children,currentChildren);assert.equal(find(host,'button','Enlarge original region').disabled,false);
 await showEvidence(host,'FX004',async()=>({kind:'text',text:'Other source',label:'Other source'}));newImage.onerror();assert.equal(find(host,'p').textContent,'Other source');assert.equal(find(host,'button','Retry original region'),undefined);
}));

test('registered HTML without an exact original hash cannot create a frame',()=>withDocument(async()=>{
 const host=new Element('main');await showEvidence(host,'FX001',async()=>({kind:'html',html:'<p>Unbound</p>'}));
 assert.equal(find(host,'iframe'),undefined);assert.match(find(host,'p').textContent,/version is missing/);
}));
