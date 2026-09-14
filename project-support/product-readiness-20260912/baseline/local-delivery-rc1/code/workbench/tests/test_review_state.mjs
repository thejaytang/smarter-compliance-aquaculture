import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const source = await readFile(new URL('../ui/review-state.js', import.meta.url), 'utf8');
const {restoreDraft, scoresComplete, sameRevision, pendingReceipt, scoreFields, historyRows, importedReview, previousImportedReview} = await import('data:text/javascript;base64,' + Buffer.from(source).toString('base64'));
const task = {revision:'task-v2', source_revision:'snapshot-v2'};
const scores = Object.fromEntries(scoreFields.map(key => [key,'HIGH']));
test('old scores are evidence, not confirmation of the new version', () => {
  const draft = restoreDraft({revision:'task-v1',source_revision:'snapshot-v1',scores,note:'Keep this note',urls:{retrieval_url:'https://example.org/source'},issueVerified:true},task);
  assert.equal(draft.note,'Keep this note');assert.equal(draft.urls.retrieval_url,'https://example.org/source');
  assert.equal(draft.issueVerified,false);assert.equal(scoresComplete(draft.scores),false);
  assert.deepEqual(draft.previousScores,scores);assert.equal(draft.stale,true);
});
test('same version retains explicit clicks, and one missing dimension is incomplete', () => {
  const draft = restoreDraft({...task,scores,stale:true},task);
  assert.equal(draft.stale,false);
  assert.equal(sameRevision(draft,task),true);assert.equal(scoresComplete(draft.scores),true);
  delete draft.scores.traceability;assert.equal(scoresComplete(draft.scores),false);
  assert.equal(sameRevision(draft,{...task,source_revision:'new-file'}),false);
});
test('unacknowledged request retains identity across draft reload and source change', () => {
  const pending={request_id:'stable-id',revision:'old',source_revision:'old',action:'assess',scores};
  const draft=restoreDraft({pending,scores},task);
  assert.deepEqual(draft.pending,pending);
  assert.equal(pendingReceipt(draft,[{id:'different',status:'applied'}]),undefined);
  assert.equal(pendingReceipt(draft,[{id:'stable-id',status:'waiting'}]).status,'waiting');
});
test('applied browser receipt and workbook application appear once in history', () => {
  const history=[{operation_id:'task',source_id:'A',operator:'Ana',application_request_id:'done',program_status:'APPLIED'},
                 {operation_id:'old',source_id:'B',operator:'DR',program_status:'APPLIED'}];
  const requests=[{id:'done',task_id:'task',actor:'Ana',status:'applied',created:0},
                  {id:'waiting',task_id:'task',actor:'Ana',status:'waiting',created:1}];
  const rows=historyRows({history,tasks:[],requests});
  assert.equal(rows.length,3);assert.equal(rows.filter(row=>row.program_status==='APPLIED').length,2);
  assert.equal(rows[0].source_id,'A');assert.equal(rows[0].program_status,'waiting');
});

test('Excel verdict and original note are displayed without changing the application record', () => {
  const record={source_id:'A',operator:'Ana',decision:'APPLY',external_review:{reviewer:'Ana',verdict:'INCORRECT',row:55,review_date:null},
    operator_note:'Imported human review: INCORRECT. Wrong URL. [Review evidence: Code/runtime/review_import_20260907/reviews.json; source row 55; actual review date not supplied.]'};
  const before=structuredClone(record), review=importedReview(record);
  assert.equal(review.verdict,'INCORRECT');assert.equal(review.note,'Wrong URL.');
  assert.equal(review.review_date,null);assert.deepEqual(record,before);
  assert.equal(importedReview({operator_note:record.operator_note}),null);
  assert.equal(importedReview({...record,operator_note:'Later note, keep verbatim'}).note,'Later note, keep verbatim');
});

test('previous Excel review remains source-specific and does not become a new score confirmation', () => {
  const old={source_id:'A',operator:'Ana',program_operated_at:'2026-09-01',external_review:{reviewer:'Ana',verdict:'ACCEPT'}};
  const newer={...old,program_operated_at:'2026-09-07',external_review:{reviewer:'DR',verdict:'REJECT'}};
  const state={history:[old,newer],tasks:[{source_id:'B',operator:'Ana',external_review:old.external_review}]};
  assert.equal(previousImportedReview(state,'A').verdict,'REJECT');
  assert.equal(previousImportedReview(state,'B').verdict,'ACCEPT');
  assert.equal(previousImportedReview(state,'C'),null);
  assert.equal(scoresComplete(previousImportedReview(state,'B').scores),false);
});
