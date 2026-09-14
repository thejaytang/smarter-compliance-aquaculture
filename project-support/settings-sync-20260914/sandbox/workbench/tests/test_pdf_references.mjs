import {test} from 'node:test';
import assert from 'node:assert/strict';
import {archiveDraft,drawnBox,referenceStatus} from '../ui/pdf-references.js';
test('dragged original regions preserve reverse direction, precision and page bounds',()=>{
 assert.deepEqual(drawnBox([600,800],[-5,10.123],{width:612,height:792}),[0,10.12,600,792]);
});
test('reference saving does not claim assessment completion',()=>{
 assert.match(referenceStatus('draft'),/not confirmed/);
 assert.match(referenceStatus('reference_saved'),/assessment pending/);
});

test('a stale local draft survives edits to the current server version',()=>{
 const data=new Map(),storage={getItem:k=>data.get(k)??null,setItem:(k,v)=>data.set(k,v)};
 const draft={guard:'old',body:{note:'irreplaceable unsaved text'},pending:{request_id:'retry-same'}};
 const archive=archiveDraft(storage,'reference',draft,'new');
 storage.setItem('reference',JSON.stringify({guard:'new',body:{note:'current edit'}}));
 assert.deepEqual(JSON.parse(storage.getItem(archive)),draft);
 archiveDraft(storage,'reference',{...draft,body:{note:'replacement'}},'new');
 assert.deepEqual(JSON.parse(storage.getItem(archive)),draft);
 assert.equal(archiveDraft(storage,'reference',draft,'old'),null);
});
