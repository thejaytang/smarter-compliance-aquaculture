import test from 'node:test';
import assert from 'node:assert/strict';
import {MaterialInspection} from '../ui/material-inspection.js';
import {Materials} from '../ui/materials.js';
test('spot-check submission reads displayed fields even if edit events were not delivered',async()=>{
 let sent;const task={id:'task',material_id:'material',revision:2,status:'pending',checked_scope:[]};
 const panel={querySelector:s=>s.includes('note')?{value:'Explicit displayed evidence'}:{checked:true},querySelectorAll:()=>[{dataset:{inspectionScope:'page:1'}}]};
 const w={busy:false,q:()=>panel,collaboration:{mutationRequest:async(path,body)=>{sent=body;return{inspection:{...task,status:'passed'}};}},renderContent(){},async loadList(){},message(){}};
 const inspector=new MaterialInspection(w);inspector.selected=task;inspector.checked=[];inspector.note='';inspector.explicit=false;
 await inspector.action('pass',{});assert.equal(sent.note,'Explicit displayed evidence');assert.deepEqual(sent.checked_scope,['page:1']);assert.equal(sent.explicit_confirmation,true);assert.equal(sent.expected_revision,2);assert.equal(inspector.dirty,false);
});
test('inspection note changes remain editable while the archived body stays read-only',()=>{
 const w=new Materials();w.inspections.selected={id:'task'};w.inspections.checked=[];w.material={collaboration:{view:'inspection'}};
 w.editInput({target:{dataset:{inspectionField:'note'},value:'Saved later'}});assert.equal(w.inspections.note,'Saved later');assert.equal(w.inspections.dirty,true);assert.equal(w.collaboration.readonly,true);
 w.editChange({target:{dataset:{inspectionScope:'page:1'},checked:true}});assert.deepEqual(w.inspections.checked,['page:1']);assert.equal(w.readerView(),'archive');
});
