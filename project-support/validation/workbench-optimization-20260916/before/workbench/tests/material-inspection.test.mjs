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

function comparisonFixture({closed=false,readFailure=false}={}){
 const original={id:'task',material_id:'material',revision:2,status:'pending',assignee:'Reviewer',checked_scope:['page:1']};
 const latest={...original,revision:3,status:closed?'passed':'pending',note:'Saved by the other tab',history:[]};
 const material={id:'material',revision:7,scope:[{id:'page:1'}],collaboration:{view:'inspection'}};
 const nodes={'#inspection-combined-open':{disabled:true},'#inspection-combined-confirm':{checked:false},'#inspection-combined-note':{value:'Both notes explicitly combined'},'#inspection-comparison-status':{textContent:''}};
 const calls=[],messages=[];let html='';
 const dialog={querySelector:s=>nodes[s],close(){calls.push('close');}};
 const w={token:{},state:{actor:{name:'Reviewer'}},material,busy:false,q:()=>null,collaboration:{state:{coordinator:'Coordinator'}},updateBar(){},message:m=>messages.push(m),async api(url,body){calls.push([url,body]);if(readFailure)throw Error('Offline');return{inspection:latest,material,latest_archive_revision:7};},dialog(markup,init){html=markup;init(dialog);},fromMaterial:m=>({...m}),clearReader(){},renderMaterial(){calls.push('render');},async loadReader(){calls.push('reader');}};
 const inspector=new MaterialInspection(w);inspector.selected=original;inspector.note='My <unsaved> note';inspector.checked=['page:1'];inspector.explicit=true;inspector.dirty=true;
 return {inspector,w,original,latest,nodes,calls,messages,get html(){return html;}};
}
test('stale inspection comparison requires an explicit choice and opens unsaved progress with fresh version guards',async()=>{
 const f=comparisonFixture();await f.inspector.compareSaved();
 assert.match(f.html,/Saved by the other tab/);assert.match(f.html,/My &lt;unsaved&gt; note/);assert.match(f.html,/checked ranges/);assert.equal(f.nodes['#inspection-combined-open'].disabled,true);
 await f.nodes['#inspection-combined-open'].onclick();assert.equal(f.inspector.selected,f.original);
 f.nodes['#inspection-combined-confirm'].checked=true;f.nodes['#inspection-combined-confirm'].onchange();await f.nodes['#inspection-combined-open'].onclick();
 assert.equal(f.inspector.selected.revision,3);assert.equal(f.inspector.note,'Both notes explicitly combined');assert.deepEqual(f.inspector.checked,[]);assert.equal(f.inspector.explicit,false);assert.equal(f.inspector.dirty,true);
 assert.equal(f.calls.filter(x=>Array.isArray(x)).length,1);assert.equal(f.calls[0][1],undefined);assert.match(f.messages.at(-1),/not saved/);
});
test('failed inspection comparison and completed checks preserve local input without reopening a writable result',async()=>{
 const offline=comparisonFixture({readFailure:true});await offline.inspector.compareSaved();assert.equal(offline.inspector.note,'My <unsaved> note');assert.equal(offline.inspector.selected,offline.original);assert.equal(offline.inspector.dirty,true);assert.equal(offline.w.busy,false);
 const closed=comparisonFixture({closed:true});await closed.inspector.compareSaved();assert.doesNotMatch(closed.html,/id="inspection-combined-open"/);assert.match(closed.html,/complete or assigned to another reviewer/);assert.equal(closed.inspector.selected,closed.original);
});
test('a comparison from an abandoned task cannot apply to the next task',async()=>{
 const f=comparisonFixture();await f.inspector.compareSaved();f.nodes['#inspection-combined-confirm'].checked=true;f.nodes['#inspection-combined-confirm'].onchange();f.w.token={};await f.nodes['#inspection-combined-open'].onclick();assert.equal(f.inspector.selected,f.original);assert.equal(f.inspector.note,'My <unsaved> note');
});
test('same-material reload cannot bypass unsaved inspection protection',async()=>{
 const w=new Materials();let warning='';w.message=m=>warning=m;w.inspections.dirty=true;w.inspections.note='Do not discard';w.id='material';
 await w.open('material');assert.equal(w.inspections.note,'Do not discard');assert.equal(w.inspections.dirty,true);assert.match(warning,/Save the spot-check progress/);
});
