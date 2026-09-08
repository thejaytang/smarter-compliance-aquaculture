export const scoreFields = ['authority_quality', 'scope_relevance', 'version_currency', 'traceability', 'access_permission'];

export function sameRevision(draft, task) {
  return !!task && draft.revision === task.revision && draft.source_revision === task.source_revision;
}

export function restoreDraft(saved, task) {
  const draft = structuredClone(saved || {});
  if (!task) return {note: draft.note || '', scores: {}};
  draft.stale = false;
  if (!sameRevision(draft, task)) {
    // Preserve typed evidence; a previous click cannot confirm a new snapshot.
    draft.previousScores = draft.scores || {};
    draft.scores = {};
    draft.issueVerified = false;
    draft.identityVerified = false;
    draft.permissionVerified = false;
    draft.stale = !!saved && Object.keys(saved).length > 0;
  }
  draft.revision = task.revision;
  draft.source_revision = task.source_revision;
  draft.scores ||= {};
  return draft;
}

export function scoresComplete(scores) {
  return scoreFields.every(key => ['HIGH', 'MEDIUM', 'LOW'].includes(scores?.[key]));
}

export function pendingReceipt(draft, requests) {
  return draft.pending ? requests.find(r => r.id === draft.pending.request_id) : null;
}

export function historyRows(state) {
  const records=[...state.history,...state.tasks].filter(row=>row.operator);
  const applied=new Set(records.map(row=>row.application_request_id).filter(Boolean));
  const byId=new Map([...state.history,...state.tasks].map(row=>[row.operation_id,row]));
  const requests=state.requests.filter(row=>!applied.has(row.id)).map(row=>({
    source_id:byId.get(row.task_id)?.source_id||row.task_id, operator:row.actor,
    checked_at:new Date(row.created*1000).toLocaleString(), decision:row.action,
    program_status:row.status, operator_note:row.note,
  }));
  return [...requests,...records.reverse()];
}

export function importedReview(record) {
  const review=record.external_review;
  if(!review?.reviewer || !['ACCEPT','REJECT','INCORRECT'].includes(review.verdict))return null;
  let note=record.operator_note||'';
  const prefix='Imported human review: '+review.verdict+'. ';
  const suffix=' [Review evidence: Code/runtime/review_import_20260907/reviews.json; source row '+review.row+'; actual review date not supplied.]';
  // Remove only the known import wrapper for display. The audit record stays intact.
  if(note.startsWith(prefix)&&note.endsWith(suffix))note=note.slice(prefix.length,-suffix.length);
  return {...review,reviewer:record.operator||review.reviewer,note};
}

export function previousImportedReview(state,sourceId) {
  const rows=[...state.history,...state.tasks].filter(row=>row.source_id===sourceId&&row.operator&&importedReview(row));
  rows.sort((a,b)=>String(b.program_operated_at||b.checked_at||'').localeCompare(String(a.program_operated_at||a.checked_at||'')));
  return rows[0]?importedReview(rows[0]):null;
}
