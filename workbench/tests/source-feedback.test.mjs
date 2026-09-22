import test from 'node:test';
import assert from 'node:assert/strict';
import {SourceWorkspace} from '../frontend/components/source-workspace.js';

function node(id=''){
 return {id,innerHTML:'',textContent:'',hidden:false,disabled:false,inert:false,value:'',attributes:{},isConnected:true,dataset:{},focusCount:0,
 setAttribute(k,v){this.attributes[k]=v;},removeAttribute(k){delete this.attributes[k];},focus(){this.focusCount++;},scrollIntoView(){this.scrolled=true;},closest(){return null;}};
}
function fixture(){
 const v=Object.create(SourceWorkspace.prototype),nodes=new Map();
 Object.assign(v,{active:true,token:0,category:'pending',query:'',selection:'',dirty:false,data:{sources:[{source_id:'S1',source_title:'One'},{source_id:'S2',source_title:'Two'}],tasks:[{source_id:'S1',operation_id:'t1',trigger:'FILE'},{source_id:'S2',operation_id:'t2',trigger:'VERSION'}]},q(s){if(!nodes.has(s))nodes.set(s,node(s.replace(/^#/,'')));return nodes.get(s);},canLeave(){return true;},renderDetail(){this.q('#sw-detail').innerHTML=this.record.source_id;},showDetail(){this.q('#sw-browser').hidden=true;this.q('#sw-detail').hidden=false;}});
 v.renderList();return {v,nodes};
}
const detail=sid=>({source:{source_id:sid,source_revision:'source-1'},draft_revision:2,source_review:{note:'Saved '+sid,fields:{},scores:{}}});
const deferred=()=>{let resolve,reject;const promise=new Promise((yes,no)=>{resolve=yes;reject=no;});return {promise,resolve,reject};};

test('filtered empty queues offer clear filters without claiming the queue is complete',async()=>{
 const {v}=fixture();v.query='Missing';v.reviewSort='newest';v.renderList();
 assert.match(v.q('#sw-list').innerHTML,/No matching sources/);assert.doesNotMatch(v.q('#sw-list').innerHTML,/No sources need review/);
 await v.command('clear-filters');assert.equal(v.rows.length,2);assert.equal(v.reviewSort,'newest');assert.equal(v.q('#sw-search').focusCount,1);
 v.data.tasks=[];v.renderList();assert.match(v.q('#sw-list').innerHTML,/No sources need review/);assert.doesNotMatch(v.q('#sw-list').innerHTML,/Clear filters/);
});

test('source refresh deduplicates pending reads and retains previous rows and filters after failure',async()=>{
 const {v}=fixture(),load=deferred();v.query='One';v.renderList();const before=v.q('#sw-list').innerHTML;let calls=0;v.api=()=>{calls++;return load.promise;};
 const one=v.refresh(),two=v.refresh();assert.equal(calls,1);assert.equal(v.q('#sw-list').attributes['aria-busy'],'true');assert.match(v.q('#sw-list-status').textContent,/Refreshing/);
 load.reject(Error('<offline>'));assert.equal(await one,false);await two;
 assert.equal(v.q('#sw-list').innerHTML,before);assert.equal(v.query,'One');assert.match(v.q('#sw-list-status').innerHTML,/previous list is retained/);assert.match(v.q('#sw-list-status').innerHTML,/Retry/);assert.doesNotMatch(v.q('#sw-list-status').innerHTML,/<offline>/);assert.equal(v.q('#sw-list').attributes['aria-busy'],undefined);
 v.api=async()=>v.data;await v.command('refresh');assert.equal(v.q('#sw-list-status').hidden,true);assert.equal(v.q('[data-source-command="refresh"]').disabled,false);
});

test('failed detail selection keeps previous identity and draft; a retry commits only the requested source',async()=>{
 const {v}=fixture();v.category='records';const first=v.rows[0],next=v.rows[1];v.record=first;v.detail=detail('S1');v.request={source_id:'S1',source_review:{note:'Keep my note'}};v.q('#sw-detail').innerHTML='S1';v.q('#sw-browser').hidden=true;
 const prior=v.request,load=deferred();v.api=()=>load.promise;const opening=v.openRecord(next,'next');
 assert.equal(v.record,first);assert.equal(v.request,prior);assert.equal(v.q('#sw-detail').innerHTML,'S1');assert.equal(v.q('#sw-detail').inert,true);
 load.reject(Error('Offline'));await opening;assert.equal(v.record,first);assert.equal(v.request,prior);assert.match(v.q('#sw-status').innerHTML,/previous source remains open/);assert.equal(v.q('#sw-detail').inert,false);
 v.api=async()=>detail('S2');await v.command('detail-retry');assert.equal(v.record.source_id,'S2');assert.equal(v.request.source_id,'S2');assert.equal(v.q('[data-source-command="next"]').focusCount,1);
});

test('a late source detail read never replaces the latest selection',async()=>{
 const {v}=fixture(),first=deferred(),second=deferred();v.category='records';v.api=path=>path.endsWith('S1')?first.promise:second.promise;
 const a=v.openRecord(v.rows[0]),b=v.openRecord(v.rows[1]);second.resolve(detail('S2'));await b;first.resolve(detail('S1'));await a;
 assert.equal(v.record.source_id,'S2');assert.equal(v.request.source_id,'S2');assert.equal(v.q('#sw-detail-title').focusCount,1);
});

test('rebuilt review filters keep focus only when they previously had it; Back uses the stable source ID',()=>{
 const {v}=fixture(),prior=globalThis.document;globalThis.document={activeElement:{id:'sw-review-type'}};
 try{v.reviewType='FILE';v.renderList();assert.equal(v.q('#sw-review-type').focusCount,1);assert.match(v.q('#sw-list').innerHTML,/value="FILE" selected/);
 globalThis.document.activeElement={id:'some-other-control'};v.renderList();assert.equal(v.q('#sw-review-type').focusCount,1);
 v.reviewType='';v.renderList();v.record={source_id:'S2'};v.listScroll=83;v.backToList();assert.equal(v.q('[data-source-command="open"][data-index="1"]').focusCount,1);assert.equal(v.q('#sw-list').scrollTop,83);
 }finally{globalThis.document=prior;}
});

test('empty confirmation note is linked to a focused error and sends no preview request',async()=>{
 const {v}=fixture();v.request={source_review:{note:'  '}};let calls=0;v.api=async()=>{calls++;return {};};
 await v.preview();assert.equal(calls,0);assert.equal(v.q('#sw-note').attributes['aria-invalid'],'true');assert.equal(v.q('#sw-note').focusCount,1);assert.equal(v.q('#sw-note-error').hidden,false);
 v.request.source_review.note='Exact evidence';v.dialog=()=>{};let sent;v.api=async(path,body)=>{sent={path,body};return {};};await v.preview();assert.equal(sent.body.source_review.note,'Exact evidence');assert.equal(sent.path,'/api/source-workspace/preview');
});

test('invalid problem reports retain exact input, and valid reports only enter an unsaved proposal',async()=>{
 const {v}=fixture(),field=node('source-problem'),error=node('source-problem-error'),add=node();let closed=0,protectedCount=0,html='';
 v.record={source_id:'S1'};v.request={source_review:{new_issues:[]}};v.protect=()=>{v.dirty=true;protectedCount++;};v.dialog=(markup,bind)=>{html=markup;bind({querySelector:s=>s==='#source-problem'?field:s==='#source-problem-error'?error:add,close:()=>closed++});};
 await v.command('report-issue');assert.match(html,/Up to 4000 characters/);field.value=' ';add.onclick();assert.equal(closed,0);assert.equal(v.request.source_review.new_issues.length,0);assert.match(error.textContent,/Describe/);
 field.value='x'.repeat(4001);add.onclick();assert.equal(field.value.length,4001);assert.equal(closed,0);assert.match(error.textContent,/4000/);
 field.value='A specific problem';add.onclick();assert.equal(v.request.source_review.new_issues[0].note,field.value);assert.equal(closed,1);assert.equal(protectedCount,1);assert.equal(v.dirty,true);
});

test('shared source dialogs use their heading and restore a recreated trigger',()=>{
 const {v}=fixture(),priorDocument=globalThis.document,priorCSS=globalThis.CSS,trigger=node('report-button'),replacement=node('report-button'),d=node(),heading=node(),close=node();
 globalThis.document={activeElement:trigger};globalThis.CSS={escape:s=>s};d.querySelector=s=>s==='h2'?heading:close;d.showModal=()=>d.open=true;d.close=()=>{d.open=false;d.onclose();};v.q=s=>s==='#sw-dialog'?d:s==='#report-button'?replacement:null;
 try{v.dialog('<h2>Report a source problem</h2>');assert.equal(d.attributes['aria-labelledby'],'sw-dialog-title');trigger.isConnected=false;close.onclick();assert.equal(replacement.focusCount,1);assert.equal(trigger.focusCount,0);}
 finally{globalThis.document=priorDocument;globalThis.CSS=priorCSS;}
});

test('source combined edit reopens actual preview and preserves typed corrections when its identity changes',async()=>{
 const {v}=fixture(),diff={id:'d',path:'/source_review/fields/title',resolution:'edit',current:'Current',incoming:'Submitted',base:'Base'};v.merge={merge_id:'source-merge',source_id:'S1',actor:'Author',unresolved:[],differences:[diff],source_review:{fields:{title:'Human edited'}}};let dialog,markup,calls=0;
 const controls=new Map(),input={value:'Further correction',dataset:{valuePath:'[]',valueType:'string'}},edit={querySelectorAll:()=>[input]};v.dialog=(html,bind)=>{markup=html;dialog={querySelector(s){if(s==='#sw-value')return edit;if(!controls.has(s))controls.set(s,{disabled:false,textContent:''});return controls.get(s);},close(){this.closed=true;}};bind(dialog);};v.api=async(_,body)=>{calls++;assert.equal(body.decisions.d.value,'Further correction');return {...v.merge,source_review:{fields:{title:body.decisions.d.value}}};};v.renderMerge();assert.match(v.q('#sw-detail').innerHTML,/Edited combined result[\s\S]*Human edited/);
 const click=()=>v.q('#sw-detail').onclick({target:{closest:()=>({dataset:{action:'collab-edit-difference',diff:'d'}})}});click();assert.match(markup,/Human edited/);assert.doesNotMatch(markup,/Submitted/);v.token++;await controls.get('#sw-value-save').onclick();assert.equal(calls,0);assert.equal(dialog.closed,undefined);assert.equal(input.value,'Further correction');assert.match(controls.get('#sw-value-error').textContent,/changed/);
 v.renderMerge();click();await controls.get('#sw-value-save').onclick();assert.equal(calls,1);assert.equal(dialog.closed,true);assert.equal(v.merge.source_review.fields.title,'Further correction');assert.equal(diff.incoming,'Submitted');
});
