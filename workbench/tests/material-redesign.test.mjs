import test from 'node:test';
import assert from 'node:assert/strict';
import {Materials} from '../frontend/components/materials.js';
function workspace(){
 const w=new Materials();w.requirements={render(){}};const classes=new Set(['detail-mode']);const nodes=new Map();
 const shell={classList:{add:v=>classes.add(v),remove:v=>classes.delete(v)}};
 nodes.set('.material-workbench',shell);nodes.set('.mw-library',{scrollTop:120});nodes.set('[data-action="resume-material"]',{});
 w.root={querySelectorAll:()=>[]};w.q=s=>nodes.get(s)||null;w.state={actor:{id:'a'}};w.material={id:'m',revision:4,scope:[{id:'page:1'}],source:{source_id:'s'},collaboration:{view:'personal'}};w.id='m';w.draft={blocks:[{text:'unsaved original text'}],checked_scope:['page:1'],association_reviewed:true,issues:[]};w.dirty=true;w.message=()=>{};
 return {w,classes,nodes};
}
test('temporary material list requires an explicit unsaved decision before leaving',async()=>{
 const {w,classes}=workspace(),draft=w.draft;let calls=0;w.api=async()=>calls++;
 let warned=0;w.unsavedDialog=()=>warned++;w.showList();assert.equal(warned,1);assert.equal(classes.has('list-mode'),false);assert.equal(w.dirty,true);assert.equal(w.draft,draft);w.dirty=false;w.showList();assert.equal(classes.has('list-mode'),true);
 await w.action('open',{dataset:{id:'m'}});assert.equal(classes.has('detail-mode'),true);assert.equal(w.draft,draft);assert.equal(calls,0);
});
test('archive waits for saved page and all three completed panes before preview',async()=>{
 const {w}=workspace(),calls=[];w.collaboration.state={mode:'coordinator'};w.reviewReady=()=>true;
 w.pageWorkflow={dirty:()=>w.dirty,refresh:async()=>{},state:{archive_ready:false}};
 w.collaboration.runPreview=async(path,body)=>calls.push({path,body});w.collaboration.confirmMaster=()=>calls.push('confirm');
 await w.archiveContent();assert.equal(calls.length,0);
 w.dirty=false;await w.archiveContent();assert.equal(calls.length,0);
 w.pageWorkflow.state.archive_ready=true;await w.archiveContent();assert.deepEqual(calls[0],{path:'/api/collaboration/prepare-own',body:{source_id:'s',material_id:'m'}});assert.equal(calls.length,1);assert.equal(w.finishIntent,'m');
});
test('unsaved material prevents the archive preparation request',async()=>{
 const {w}=workspace();w.collaboration.state={mode:'coordinator'};let previews=0;w.collaboration.runPreview=async()=>previews++;
 await w.archiveContent();assert.equal(previews,0);assert.equal(w.dirty,true);
});
test('reviewer finish cannot invoke master archive preparation',async()=>{
 const {w}=workspace();w.dirty=false;w.collaboration.state={mode:'reviewer'};w.reviewReady=()=>true;w.pageWorkflow={dirty:()=>false,refresh:async()=>{},state:{archive_ready:true}};let reviews=0,previews=0;w.reviewDialog=()=>reviews++;w.collaboration.runPreview=async()=>previews++;
 await w.archiveContent();assert.equal(reviews,1);assert.equal(previews,0);
});
test('master archive opens explicit confirmation and does not repeat adoption',async()=>{
 const {w}=workspace();w.dirty=false;w.collaboration.state={mode:'coordinator'};w.reviewReady=()=>true;w.pageWorkflow={dirty:()=>false,refresh:async()=>{},state:{archive_ready:true}};w.material.collaboration.view='master';let confirmations=0,previews=0;w.collaboration.confirmMaster=()=>confirmations++;w.collaboration.runPreview=async()=>previews++;
 await w.archiveContent();assert.equal(confirmations,1);assert.equal(previews,0);
});
