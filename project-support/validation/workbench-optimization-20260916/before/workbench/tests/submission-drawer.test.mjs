import test from 'node:test';
import assert from 'node:assert/strict';
import {SubmissionDrawer,receiptMarkup} from '../ui/submission-drawer.js';
const receipt=()=>({item_type:'adoption_receipt',receipt:{status:'adopted',actor:'Coordinator',contributor:'<Colleague>',at:'2026-09-13T10:00:00Z',material:{title:'Material A',revision:4,content_status:'draft',source:{source_id:'PA001'},blocks:[{text:'<script>PAYLOAD_SENTINEL</script>'}]}}});
test('received receipt summary separates adoption, content review and immutable folded payload',()=>{
 const input=receipt(),before=structuredClone(input),html=receiptMarkup(input),summary=html.split('<details>')[0];
 assert.match(summary,/Material A/);assert.match(summary,/PA001/);assert.match(summary,/&lt;Colleague&gt;/);assert.match(summary,/Master revision/);assert.match(summary,/>4</);assert.match(summary,/Adoption decision/);assert.match(summary,/Adopted/);assert.match(summary,/Content review at receipt/);assert.match(summary,/Draft/);
 assert.doesNotMatch(summary,/PAYLOAD_SENTINEL|<script>/);assert.match(html,/<details><summary>Original receipt details<\/summary>/);assert.doesNotMatch(html,/<details open|<script>/);assert.match(html,/&lt;script&gt;PAYLOAD_SENTINEL/);assert.deepEqual(input,before);
});
test('task receipt distinguishes kept-current decision, archive check and unknown master review',()=>{
 const html=receiptMarkup({item_id:'task-result',status:'adopted',choice:'current',actor:'Coordinator',contributor:'Reviewer',result:{inspection:{title:'Check A',archive_revision:9,status:'passed'}}},[{id:'task-result',base:{source_id:'PA002'}}]);
 const summary=html.split('<details>')[0];assert.match(summary,/Kept current/);assert.match(summary,/Checked archive revision/);assert.match(summary,/>9</);assert.match(summary,/Not recorded in this receipt/);assert.match(summary,/Master revision<\/dt><dd><span class="collab-value">Not recorded/);assert.match(summary,/Spot-check status/);assert.match(summary,/Passed/);assert.match(summary,/PA002/);
});
test('unknown receipt fields remain explicitly missing, without an inferred adoption or review',()=>{
 const html=receiptMarkup({receipt:{status:'pending'}}).split('<details>')[0];assert.match(html,/Pending/);assert.match(html,/Not recorded/);assert.doesNotMatch(html,/Content Review Complete|>Adopted</);
});
test('both drawer routes render receipt cards with only second-level details for raw payload',async()=>{
 const received=receipt(),data={items:[],received_receipts:[received],receipts:[received.receipt],inbox:[]},w={api:async()=>data,dialog:html=>w.html=html};
 const drawer=new SubmissionDrawer(w);await drawer.open();assert.match(w.html,/<summary>Received adoption receipts<\/summary><article/);assert.match(w.html,/<summary>Original receipt details<\/summary>/);
 await drawer.inbox();assert.match(w.html,/<summary>Per-item adoption receipts<\/summary><article/);assert.match(w.html,/Content review at receipt/);
});
