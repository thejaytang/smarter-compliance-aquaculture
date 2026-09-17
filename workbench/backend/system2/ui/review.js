const jobId = location.pathname.split('/').pop();
let doc, context, selected, selectedType = 'block', pageIndex = 0, allChoices = [], pendingRequest = null;
const $ = id => document.getElementById(id);

async function load() {
  const response = await fetch(`/jobs/${jobId}/review-context`);
  if (!response.ok) throw new Error(await response.text());
  context = await response.json();
  doc = context.document;
  if (!doc.pages.some(page => page.page_index === pageIndex)) pageIndex = doc.pages[0]?.page_index;
  $('status').textContent = `${doc.quality.status} · revision ${doc.revision}`;
  const criticalTargets = new Set(doc.review_items.filter(item => item.severity === 'critical').map(item => item.target_id));
  const choices = [];
  Object.values(doc.blocks).forEach(block => {
    if (block.content) choices.push({key:`block:${block.id}`, label:`block · ${block.id} · ${block.type}`, review:block.quality.requires_review || doc.review_queue.includes(block.id), critical:criticalTargets.has(block.id), ambiguous:block.content.resolution_status === 'ambiguous', unknown:block.type === 'unknown', low:block.quality.layout_confidence < .35 || block.quality.ocr_confidence < .25});
    if (block.table) block.table.cells.forEach(cell => choices.push({key:`cell:${cell.id}`, label:`cell · ${cell.id}`, review:cell.content.requires_human_review, critical:criticalTargets.has(block.id), ambiguous:cell.content.resolution_status === 'ambiguous', unknown:false, low:cell.content.resolution.confidence < .8}));
  });
  Object.values(doc.evidence_spans).forEach(span => choices.push({key:`span:${span.id}`, label:`span · ${span.id} · ${span.criticality}`, review:span.requires_human_review, critical:span.criticality !== 'general', ambiguous:span.resolution_status === 'ambiguous', unknown:false, low:span.confidence < .8}));
  allChoices = choices.sort((a,b) => Number(b.review)-Number(a.review));
  applyFilters();
  if ($('targets').options.length) { $('targets').selectedIndex = 0; choose(); }
}

function choose() {
  let id;
  const key = $('targets').value, separator = key.indexOf(':');
  selectedType = key.slice(0, separator); id = key.slice(separator + 1);
  if (selectedType === 'block') selected = doc.blocks[id];
  if (selectedType === 'span') selected = doc.evidence_spans[id];
  if (selectedType === 'cell') selected = Object.values(doc.blocks).flatMap(block => block.table ? block.table.cells : []).find(cell => cell.id === id);
  if (!selected) return;
  const c = selected.content || selected;
  $('native').value = c.native_text || '';
  $('ocr').value = c.ocr_text || '';
  $('review-value').value = c.review_text || c.resolved_text || '';
  $('resolved').value = c.resolved_text || '';
  const issues = selected.quality ? selected.quality.issues : [];
  const links = selected.content_links || [];
  const operations = selected.operations || [];
  $('metadata').replaceChildren();
  for (const [label, value] of [['Target',selectedType], ['Issues',issues.join(', ') || 'none'], ['Links',links.map(x => x.target_id).join(', ') || 'none'], ['Assembly / checks',operations.map(x => x.operation).join(', ') || 'none']]) {
    const term = document.createElement('dt'), detail = document.createElement('dd');
    term.textContent = label; detail.textContent = value; $('metadata').append(term, detail);
  }
  if (selected.segments && selected.segments.length) pageIndex = selected.segments[0].page_index;
  else if (Number.isInteger(selected.page_index)) pageIndex = selected.page_index;
  draw();
}

function applyFilters() {
  const enabled = ['critical','ambiguous','unknown','low-confidence'].filter(id => $(id).checked);
  const property = {'critical':'critical','ambiguous':'ambiguous','unknown':'unknown','low-confidence':'low'};
  const visible = enabled.length ? allChoices.filter(item => enabled.some(id => item[property[id]])) : allChoices;
  $('targets').replaceChildren(...visible.map(item => new Option(item.label, item.key)));
  if ($('targets').options.length) { $('targets').selectedIndex = 0; choose(); }
}

async function draw() {
  const page = doc.pages.find(item => item.page_index === pageIndex);
  if (!page) return;
  const image = new Image();
  image.src = `/jobs/${jobId}/pages/${pageIndex}`;
  image.onload = () => {
    const canvas = $('page'), ctx = canvas.getContext('2d');
    canvas.width = image.naturalWidth; canvas.height = image.naturalHeight; ctx.drawImage(image, 0, 0);
    const segments = selected && selected.segments ? selected.segments : selected && selected.bbox ? [{page_index:selected.page_index, bbox:selected.bbox}] : [];
    if (selected) segments.filter(s => s.page_index === pageIndex).forEach(s => {
      const [x0,y0,x1,y1] = [s.bbox.x0,s.bbox.y0,s.bbox.x1,s.bbox.y1];
      ctx.strokeStyle = '#e31a1c'; ctx.lineWidth = 4;
      ctx.strokeRect(x0 * canvas.width/page.width, y0 * canvas.height/page.height, (x1-x0)*canvas.width/page.width, (y1-y0)*canvas.height/page.height);
    });
  };
  $('page-label').textContent = `Page ${pageIndex + 1} · label ${page.page_label_correction || page.printed_page_label || page.pdf_page_label || 'none'}`;
}

async function decide(action) {
  const actor = $('actor').value.trim();
  if (!actor || !selected) { alert('Enter your name and select a target.'); return; }
  const decision = {actor, action, target_type:selectedType, target_id:selected.id, new_value:action === 'modify' ? $('review-value').value : null, reason:$('reason').value || null};
  const payload = {expected_revision:context.revision, expected_canonical_sha256:context.canonical_sha256, expected_source_sha256:context.source_sha256, decision};
  const fingerprint = JSON.stringify(payload);
  if (pendingRequest && pendingRequest.fingerprint !== fingerprint) {
    alert('Retry the previous decision first; its response was not confirmed.'); return;
  }
  if (!pendingRequest) pendingRequest = {fingerprint, body:JSON.stringify({...payload, request_id:crypto.randomUUID()})};
  document.querySelectorAll('[data-action]').forEach(button => button.disabled = true);
  try {
    const response = await fetch(`/jobs/${jobId}/reviews/guarded`, {method:'POST', headers:{'Content-Type':'application/json'}, body:pendingRequest.body});
    if (!response.ok) {
      const message = await response.text();
      if (response.status < 500) pendingRequest = null;
      alert(message);
      if (response.status === 409) await load();
      return;
    }
    pendingRequest = null;
    await load();
  } catch (error) { alert(`Response not confirmed. Retry the same decision. ${error.message}`); }
  finally { document.querySelectorAll('[data-action]').forEach(button => button.disabled = false); }
}

$('targets').addEventListener('change', choose);
function movePage(delta) {
  const position = doc.pages.findIndex(page => page.page_index === pageIndex);
  pageIndex = doc.pages[Math.max(0, Math.min(doc.pages.length - 1, position + delta))].page_index;
  draw();
}
$('prev').onclick = () => movePage(-1);
$('next').onclick = () => movePage(1);
document.querySelectorAll('[data-action]').forEach(button => button.onclick = () => decide(button.dataset.action));
['critical','ambiguous','unknown','low-confidence'].forEach(id => $(id).addEventListener('change', applyFilters));
load();
