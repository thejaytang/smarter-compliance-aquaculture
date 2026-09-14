import test from 'node:test';
import assert from 'node:assert/strict';
import {sourceListRows,SourceWorkspace} from '../ui/source-workspace.js';
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
