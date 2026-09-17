import test from 'node:test';
import assert from 'node:assert/strict';
import {sourceListRows,SourceWorkspace,sourceVersion,sourceDecision} from '../ui/source-workspace.js';
test('pending groups tasks by source without mutating source records, excludes completed tasks',()=>{
 const data={sources:[{source_id:'S10',source_title:'Ten',effective_selection:'INCLUDE'},{source_id:'S2',source_title:'Two',effective_selection:'PENDING'}],tasks:[{source_id:'S10',operation_id:'a',trigger:'Version',is_open:true},{source_id:'S10',operation_id:'b',trigger:'Original',is_open:true},{source_id:'S2',operation_id:'c',trigger:'Review',is_open:true},{source_id:'S2',operation_id:'d',is_open:false},{operation_id:'candidate',source_title:'New',is_open:true}]};
 const before=structuredClone(data),rows=sourceListRows(data,'pending');assert.deepEqual(rows.map(r=>r.source_id),['S2','S10',undefined]);assert.equal(rows[1].pending_tasks.length,2);assert.equal(rows[1].effective_selection,'INCLUDE');assert.deepEqual(data,before);assert.equal(sourceListRows(data,'pending','original')[0].source_id,'S10');
});
test('register includes pending with numeric IDs and applies query and selection together',()=>{
 const data={sources:[{source_id:'S10',source_title:'Water',effective_selection:'INCLUDE'},{source_id:'S2',source_title:'Water',effective_selection:'PENDING'}]};assert.deepEqual(sourceListRows(data,'records').map(s=>s.source_id),['S2','S10']);assert.equal(sourceListRows(data,'records','water','PENDING')[0].source_id,'S2');
});
test('history retains distinct actions for one source and orders newest first',()=>{
 const data={history:[{source_id:'S1',action:'first',at:'2026-01-01'},{source_id:'S1',action:'second',at:'2026-02-01'}]};assert.deepEqual(sourceListRows(data,'history').map(s=>s.action),['second','first']);assert.equal(sourceListRows(data,'history','first').length,1);assert.equal(sourceListRows(data,'history','2026-01')[0].action,'first');
});

test('registered source detail renders ratings and authoritative read-only values without a personal-draft leak',()=>{
 const view=Object.create(SourceWorkspace.prototype),host={innerHTML:''};
 Object.assign(view,{category:'records',data:{tasks:[],can_apply:true},detail:{source:{source_id:'S1',source_title:'Original',issuer:'Publisher',effective_selection:'INCLUDE',authority_quality:'HIGH'},fields:[{key:'issuer',label:'Publisher'}],score_fields:['authority_quality'],issues:[]},request:{source_review:{scores:{authority_quality:'LOW'},fields:{issuer:'Unadopted'},selection:'EXCLUDE'}},q:()=>host,showDetail(){},loadOriginal(){},wireResize(){}});
 view.renderDetail();assert.match(host.innerHTML,/Read only/);assert.match(host.innerHTML,/value="HIGH" checked/);assert.doesNotMatch(host.innerHTML,/Unadopted/);assert.match(host.innerHTML,/Request review/);
});

test('navigation can deactivate source workspace before its first mount',()=>{const view=Object.create(SourceWorkspace.prototype);view.token=0;view.leave();assert.equal(view.active,false);assert.equal(view.token,1);});

test('file inspection fills suggestions without overwriting human edits',async()=>{
 const view=Object.create(SourceWorkspace.prototype),file={name:'law.html'};
 Object.assign(view,{intakeFile:file,intakeDraft:{source_title:'Human title'},intakeEdited:new Set(['source_title']),drawIntake(){},protectIntake(){}});
 view.api=async()=>({fields:{source_title:'Machine title',issuer:'Publisher'},warnings:[]});view.api.upload=async()=>({upload_id:'upload'});
 await view.parseIntake();assert.equal(view.intakeDraft.source_title,'Human title');assert.equal(view.intakeDraft.issuer,'Publisher');assert.equal(view.busy,false);assert.equal(view.uploadedIntakeFile,file);
});
test('failed inspection keeps manual details editable and releases navigation lock',async()=>{
 const view=Object.create(SourceWorkspace.prototype);
 Object.assign(view,{intakeFile:{name:'scan.pdf'},intakeDraft:{},drawIntake(){},api:{upload:async()=>{throw Error('Unreadable file');}}});
 await view.parseIntake();assert.equal(view.busy,false);assert.equal(view.intakeDetails,true);assert.match(view.intakeParseStatus,/Unreadable file/);
});

test('review type filter matches a secondary check and sorts by waiting time',()=>{
 const data={sources:[{source_id:'S1'},{source_id:'S2'}],tasks:[{source_id:'S1',trigger:'FILE',created_at:'2026-01-01'},{source_id:'S1',trigger:'VERSION; FILE',created_at:'2026-02-01'},{source_id:'S2',trigger:'VERSION',created_at:'2026-03-01'}]};
 assert.deepEqual(sourceListRows(data,'pending','','',{reviewType:'VERSION',sort:'oldest'}).map(s=>s.source_id),['S1','S2']);
 assert.deepEqual(sourceListRows(data,'pending','','',{reviewType:'VERSION',sort:'newest'}).map(s=>s.source_id),['S2','S1']);
});
test('register retains semantic versions and otherwise shows the last check as DD-MM-YY',()=>{
 assert.equal(sourceVersion({version:'V1.0.1',publication_date:'2000-07-18'}),'V1.0.1');assert.equal(sourceVersion({publication_date:'2000-07-18',last_checked_at:'2026-09-14T10:20:00+02:00'}),'14-09-26');assert.equal(sourceVersion({version:'2024-10-11',last_attempt_at:'2026-09-13T12:30:00'}),'13-09-26');assert.equal(sourceVersion({publication_date:'2000-07-18'}),'Not checked');assert.equal(sourceVersion({}),'Not checked');
 assert.equal(sourceDecision({effective_selection:'PENDING',operator_selection_decision:'INCLUDE'}),'Pending-Include');assert.equal(sourceDecision({effective_selection:'INCLUDE',operator_selection_decision:'INCLUDE'}),'INCLUDE');
});

test('leaving intake clears unsubmitted file, metadata and expanded fields without touching review drafts',()=>{
 const view=Object.create(SourceWorkspace.prototype),review={source_review:{note:'Keep my reviewed evidence'}};
 Object.assign(view,{active:true,category:'intake',token:0,dirty:true,intakeFile:{name:'old.pdf'},intakeFileName:'old.pdf',intakeUpload:{upload_id:'old'},uploadedIntakeFile:{},intakeDraft:{source_title:'Old'},intakeDetails:true,intakeEdited:new Set(['source_title']),intakeParseStatus:'ready',intakeURL:'https://old.example',urlInspection:{url:'old'},request:review});
 assert.equal(view.canLeave(),true);view.leave();
 assert.equal(view.intakeFile,null);assert.equal(view.intakeUpload,null);assert.equal(view.intakeDetails,false);assert.deepEqual(view.intakeDraft,{});assert.equal(view.intakeURL,'');assert.equal(view.dirty,false);assert.equal(view.request,review);
});
test('remove file returns upload form to its empty state without submitting anything',async()=>{
 const view=Object.create(SourceWorkspace.prototype);let rendered=0,focused=0;
 Object.assign(view,{intakeFile:{name:'old.pdf'},intakeDraft:{source_title:'Old'},intakeDetails:true,drawIntake(){rendered++;},q(){return {focus(){focused++;}};}});
 await view.command('intake-remove');assert.equal(view.intakeFile,null);assert.equal(view.intakeDetails,false);assert.equal(rendered,1);assert.equal(focused,1);
});

function intakeView(){const v=Object.create(SourceWorkspace.prototype);Object.assign(v,{intakeDraft:{},intakeEdited:new Set(),pending:new Map(),state:{actor:{id:'test'}},drawIntake(){},protectIntake(){},q(){return {textContent:''};}});return v;}
test('URL inspection displays generated results before any intake write and exposes the real loading phase',async()=>{
 const v=intakeView(),calls=[];v.intakeURL='https://example.org/law';let finish;v.api=(path,body)=>{calls.push({path,body});return new Promise(resolve=>finish=resolve);};
 const pending=v.inspectURL();assert.equal(v.busy,true);assert.match(v.intakePhase,/Retrieving original/);assert.equal(calls[0].path,'/api/sources/inspect');
 finish({inspection_id:'i',upload_id:'u',fields:{source_title:'A law',scope_relevance:'HIGH'},inspection:{dimensions:{}},warnings:[]});await pending;
 assert.equal(v.busy,false);assert.equal(v.intakeDraft.scope_relevance,'HIGH');assert.equal(calls.length,1);assert.equal(v.urlInspection.inspection_id,'i');
 v.api=async(path,body)=>{calls.push({path,body});return {status:'pending_review'};};await v.submitURL();assert.equal(calls[1].path,'/api/sources/intake');assert.equal(calls[1].body.inspection_id,'i');assert.equal(calls[1].body.scope_relevance,'HIGH');
});
test('file submission cannot bypass inspection, retains human edits and sends the server inspection identity',async()=>{
 const v=intakeView(),calls=[];v.intakeFile={name:'law.html'};v.intakeDraft={source_title:'My title'};v.intakeEdited.add('source_title');
 v.api=async(path,body)=>{calls.push({path,body});return path.endsWith('/inspect')?{inspection_id:'i',upload_id:'u',fields:{source_title:'Program title',issuer:'Publisher'},warnings:[]}:{status:'pending_review'};};v.api.upload=async()=>({upload_id:'u'});
 await v.submitIntake();assert.deepEqual(calls.map(c=>c.path),['/api/sources/inspect','/api/sources/intake']);assert.equal(calls[1].body.source_title,'My title');assert.equal(calls[1].body.inspection_id,'i');assert.equal(calls[1].body.issuer,'Publisher');
});
test('failed URL or file parsing leaves input in place and makes no intake write',async()=>{
 const v=intakeView(),calls=[];v.intakeURL='https://example.org/denied';v.intakeFile={name:'bad.pdf'};v.api=async path=>{calls.push(path);throw Error('Not a readable original');};v.api.upload=async()=>({upload_id:'u'});
 await v.inspectURL();assert.equal(v.intakeURL,'https://example.org/denied');assert.equal(v.urlInspection,null);assert.equal(v.busy,false);
 await v.submitIntake();assert.ok(calls.every(p=>p==='/api/sources/inspect'));assert.equal(v.intakeFile.name,'bad.pdf');assert.equal(v.intakeInspection,null);assert.equal(v.busy,false);
});
test('program review rendering escapes document data and labels unknown ratings as needing review',async()=>{
 const {inspectionMarkup}=await import('../ui/source-workspace.js');const html=inspectionMarkup({summary:'<script>bad</script>',dimensions:{access_permission:{rating:'UNKNOWN',reason:'Verify permission',evidence:'<img>'}},coverage:{total_units:9,inspected_units:9,units:'pages'},flags:['No version found']});assert.match(html,/Needs review/);assert.match(html,/Read 9 \/ 9 pages/);assert.doesNotMatch(html,/<script>|<img>/);assert.match(html,/&lt;script&gt;/);
});
