// Browser-only practice records. This module never writes a System2 decision.
export const DEMO_VERSION = 'source-review-20260907-v1';
export function newSession() { return {version: DEMO_VERSION, items: {}, events: [], selected: null}; }
export function restoreSession(raw) {
  if (!raw) return newSession();
  const saved = JSON.parse(raw);
  if (saved.version !== DEMO_VERSION || !saved.items || !Array.isArray(saved.events)) {
    throw Error('This saved demo uses a different version. Its records have been preserved.');
  }
  return saved;
}
export function reviewCounts(session, cases) {
  const counts = {pending: 0, reviewed: 0, followup: 0};
  for (const item of cases) counts[session.items[item.id]?.status || 'pending']++;
  return counts;
}
export function nextPending(session, cases, current) {
  const start = cases.findIndex(item => item.id === current);
  for (let step = 1; step <= cases.length; step++) {
    const item = cases[(start + step) % cases.length];
    if (item.id !== current && (session.items[item.id]?.status || 'pending') === 'pending') return item.id;
  }
  return null;
}
export function recordReview(session, item, actor, action, draft = {}, at = new Date().toISOString()) {
  if (!actor?.id || !actor.name) throw Error('Select a reviewer at the top first.');
  const current = session.items[item.id] || {};
  if (current.status === 'reviewed' && action !== 'reopen') throw Error('Reopen this sample before changing its decision.');
  const note = String(draft.note || '').trim();
  let status = 'reviewed', after = structuredClone(current.result || {text: item.text}), label;
  if (action === 'accept' && item.kind === 'text') label = 'Text confirmed';
  else if (action === 'correct' && ['text', 'join'].includes(item.kind)) {
    if (!draft.text?.trim()) throw Error('Enter the corrected text before saving.');
    after.text = draft.text.trim(); label = 'Text corrected';
  } else if (action === 'merge' && item.kind === 'join') {
    after.text = item.pieces.join(' '); label = 'Paragraphs merged';
  } else if (action === 'separate' && item.kind === 'join') { after.text = item.pieces.join('\n'); label = 'Separate paragraphs confirmed'; }
  else if (action === 'list' && item.kind === 'html') {
    if (!['siblings','nested'].includes(draft.choice)) throw Error('Choose the relationship shown in the source.');
    after.relationship = draft.choice; label = draft.choice === 'siblings' ? 'Parallel list items confirmed' : 'Nested list recorded';
  } else if (action === 'columns' && item.kind === 'excel') {
    if (!['B','C'].includes(draft.recordColumn) || !['B','C'].includes(draft.fieldsColumn) || draft.recordColumn === draft.fieldsColumn) {
      throw Error('Choose a different source column for each field.');
    }
    after.columns = {record: draft.recordColumn, requiredFields: draft.fieldsColumn}; label = 'Column mapping confirmed';
  } else if (action === 'reopen') { status = 'pending'; after = current.result || after; label = 'Reopened'; }
  else if (['reparse','unreadable','missing','pending'].includes(action)) {
    if (!note) throw Error('Add a short note so the next reviewer knows what to check.');
    status = 'followup'; after = current.result || after;
    label = {reparse:'Reprocessing requested',unreadable:'Source unreadable',missing:'Missing content reported',pending:'Kept pending'}[action];
  } else throw Error('This action does not resolve this type of review.');
  const next = structuredClone(session);
  next.items[item.id] = {status, result: after, draft: action === 'reopen' ? {note, text: after.text} : {}};
  next.events.push({itemId: item.id, actor: {...actor}, at, action, label, status, note,
    before: current.result || {text: item.text}, after, demo: true});
  return next;
}
