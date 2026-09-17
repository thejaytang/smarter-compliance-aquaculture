import {weeklyChart} from './qa-chart.js';
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

const rendered = new WeakMap();

export function materialSystems(data) {
  const connection=data.material_workbench||{status:'loading'};
  const ready=connection.status==='ready'&&Array.isArray(connection.data?.materials)&&Array.isArray(connection.data?.sources);
  const materials=ready?connection.data.materials:[];
  const current=materials.filter(m=>!m.source_stale);
  const reviewed=current.filter(m=>m.content_status==='content_review_complete'&&!m.source_check_error&&!(m.source_issues||[]).length&&!(m.candidates||[]).some(c=>['running','ready','partial'].includes(c.status))).length;
  const counts=ready?connection.data.counts:null;
  const total=counts?.total??materials.length,reviewedTotal=counts?.current_reviewed??reviewed,historical=counts?.historical??(materials.length-current.length);
  const awaiting=counts?(counts.total-counts.historical-counts.current_reviewed):(current.length-reviewed);
  const unavailable=connection.status==='select_reviewer'?'Select reviewer':connection.status==='error'?'Unavailable':'Loading…';
  const sourceCard=(data.systems||[]).find(s=>s.key==='system1');
  const materialCard={key:'system2',label:'Human content review',availability:ready?'live':'unavailable',status:ready?'Human review available':connection.status==='select_reviewer'?'Select reviewer':connection.status==='error'?'Read failed':'Loading materials',title:'Requirement Extraction System',purpose:'Read, correct, save and confirm one source material at a time.',
    pending:{value:ready?awaiting:null,display:unavailable,label:'Current materials awaiting content review'},
    metrics:[{label:'Opened material snapshots',value:ready?total:null},{label:'Current content reviews complete',value:ready?reviewedTotal:null},{label:'Registered sources available to open',value:ready?connection.data.sources.length:null},{label:'Historical source snapshots',value:ready?historical:null}],
    unavailable_label:unavailable,
    note:ready?'Counts are materials, not content blocks or legacy review items. Saving a draft does not confirm its review. Requirement structuring remains unconnected.':connection.status==='select_reviewer'?'Choose your name above to open personal material work.':connection.status==='error'?'Material counts could not be read: '+(connection.error||'The material service did not return a usable response.'):'Reading saved material versions and their human review states.',
    action:{view:'system2',label:'Open materials'}};
  return [...(sourceCard?[{...sourceCard,label:'Source governance',title:'Source Management System'}]:[]),materialCard];
}

export function systemCards(systems) {
  return `<section class="system-overview" aria-label="Source management and material review">${systems.map(s=>`
    <article class="system-card" aria-labelledby="overview-${esc(s.key)}">
      <div class="system-card-top"><span class="eyebrow">${esc(s.label)}</span><span class="system-status ${esc(s.availability)}">${esc(s.status)}</span></div>
      <h2 id="overview-${esc(s.key)}">${esc(s.title)}</h2><p class="system-purpose">${esc(s.purpose)}</p>
      <div class="system-pending"><b class="${s.pending.value===null?'unavailable':''}">${s.pending.value===null?esc(s.pending.display||'Not connected'):esc(s.pending.value)}</b><span>${esc(s.pending.label)}</span></div>
      <dl class="system-metrics">${s.metrics.map(m=>`<div><dt>${esc(m.label)}</dt><dd>${m.value===null?'<span aria-label="'+esc(s.unavailable_label||'Not connected')+'">–</span>':esc(m.value)}</dd></div>`).join('')}</dl>
      <p class="system-note">${esc(s.note)}</p><button type="button" data-open-system="${esc(s.action.view)}">${esc(s.action.label)}</button>
    </article>`).join('')}</section>`;
}

export function renderDashboard(container, data, openTasks, navigate) {
  if (!data) { container.innerHTML='<p>Loading Dashboard…</p>'; return; }
  const stamp=new Date(data.as_of*1000).toLocaleString('en-GB',{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'});
  const signature=JSON.stringify({...data,as_of:null});
  if(rendered.get(container)===signature && container.querySelector('.requirement-overview')){
    container.querySelector('.dashboard-meta small').textContent='Data read at '+stamp;
    return;
  }
  const definitionsOpen=container.querySelector('.dashboard-definitions')?.open;
  const sourcesOpen=container.querySelector('.source-dashboard')?.open;
  const inspectionsOpen=container.querySelector('.legacy-inspection')?.open;
  const c=data.counts, total=c.sources;
  let offset=0;
  const segments=data.selection.map(row=>{
    const percent=total?row.count/total*100:0;
    const circle=`<circle class="selection-${row.key.toLowerCase()}" cx="70" cy="70" r="53" pathLength="100" fill="none" stroke-width="13" stroke-dasharray="${percent} ${100-percent}" stroke-dashoffset="${-offset}" transform="rotate(-90 70 70)"/>`;
    offset+=percent; return circle;
  }).join('');
  const maxIssue=Math.max(1,...data.issues.map(row=>row.count));
  const maxCategory=Math.max(1,...data.categories.map(row=>row.count));
  container.innerHTML=`<div class="requirement-overview"><div class="dashboard-meta"><span>Sources → Material workbench</span><small>Data read at ${esc(stamp)}</small></div>
    <p class="overview-intro">Read the saved original, correct extracted content and explicitly confirm each material. The third pane inside each material is reserved for Requirement structuring; Process is not connected.</p>
    ${systemCards(materialSystems(data))}<p class="muted chart-note">${data.material_workbench?.read_at?'Material states read at '+esc(new Date(data.material_workbench.read_at*1000).toLocaleTimeString('en-GB'))+'. ':''}Historical extraction records remain available in <button type="button" data-legacy-view="legacyReview">Legacy review</button> and <button type="button" data-legacy-view="legacyHistory">Legacy history</button>.</p>
    <details class="legacy-inspection"><summary>Retained weekly inspection records</summary><p class="muted">These scoped source and legacy extraction checks are separate from whole-material human content confirmation. Viewing them starts no sampling.</p>${weeklyChart(data.weekly_qa,data.qa_schedule)}</details>
    <details class="source-dashboard"><summary><strong>Source Management System details</strong><span>Source selection, originals and review priorities</span></summary>
    <section class="metrics" aria-label="Source Management System source metrics">${[['Total sources',c.sources],['Pending sources',c.pending],['Originals stored',c.stored],['Included sources',c.included]].map(([label,count])=>`<div class="metric"><span>${label}</span><b>${count}</b></div>`).join('')}</section>
    <div class="dashboard-grid">
      <section class="panel"><h2>Source selection</h2><div class="selection-chart"><svg viewBox="0 0 140 140" role="img" aria-label="${esc(data.selection.map(x=>x.label+' '+x.count+' sources').join(', '))}"><circle class="ring-background" cx="70" cy="70" r="53" fill="none" stroke-width="13"/>${segments}<text x="70" y="69" text-anchor="middle" class="ring-count">${total}</text><text x="70" y="88" text-anchor="middle" class="ring-label">sources</text></svg><ul class="chart-legend">${data.selection.map(x=>`<li><span class="legend-label"><i class="selection-${x.key.toLowerCase()}"></i>${x.label}</span><b>${x.count}</b><small>${total?(x.count/total*100).toFixed(1):'0.0'}%</small></li>`).join('')}</ul></div></section>
      <section class="panel"><h2>Review reasons</h2><div class="issue-bars">${data.issues.map(x=>`<button type="button" class="chart-row" data-issue="${x.key}" ${x.count?'':'disabled'}><span>${x.label}</span><b>${x.count}</b><progress class="chart-track" value="${x.count}" max="${maxIssue}" aria-hidden="true"></progress></button>`).join('')}</div><p class="muted chart-note">A source can have several issues. Select a bar to open the matching tasks.</p></section>
      <section class="panel"><h2>Source types and originals</h2>${data.categories.map(x=>`<div class="category-row"><span>${esc(x.label)}</span><progress class="category-track" value="${x.count}" max="${maxCategory}" aria-label="${esc(x.label)}: ${x.count} sources"></progress><b>${x.count}</b></div>`).join('')}<div class="snapshot-summary"><span>Local originals</span><b>${c.stored} / ${total}</b><progress value="${c.stored}" max="${Math.max(1,total)}" aria-label="Originals stored ${c.stored} of ${total} sources"></progress><small>${c.missing} sources have no local original. Storage does not mean the content is verified.</small></div></section>
      <section class="panel"><div class="dashboard-panel-heading"><h2>Priority review</h2><button type="button" id="dashboard-all">Review ${c.pending} sources</button></div><div class="priority-list">${data.priority.map(x=>`<button type="button" data-priority="${esc(x.source_id)}"><span class="source-id">${esc(x.source_id)}</span><span>${esc(x.title)}</span>${x.human_issue?'<small>Reviewer feedback to verify</small>':''}</button>`).join('')||'<p class="muted">No pending reviews.</p>'}</div></section>
    </div></details><details class="dashboard-definitions"><summary>Metric definitions and data sources</summary><p>Source Management System counts governed sources. The material workspace counts saved source-bound materials, including separately identified historical source snapshots; content blocks and legacy review items are not material counts. Current content review totals exclude changed sources, unresolved source problems and unadopted candidates. Available registered sources may not yet have an opened material. Counts are not added across these units. Requirement structuring is not connected, which means unavailable rather than zero or complete.</p><p>Source Management System reads the governed source registry. Pending counts use unique unresolved source IDs, and review reasons can overlap. Stored originals are not necessarily verified. The overview refreshes after an applied decision; source trends are not inferred from current counts.</p></details></div>`;
  rendered.set(container,signature);
  if(definitionsOpen)container.querySelector('.dashboard-definitions').open=true;
  if(sourcesOpen)container.querySelector('.source-dashboard').open=true;
  if(inspectionsOpen)container.querySelector('.legacy-inspection').open=true;
  container.querySelectorAll('[data-legacy-view]').forEach(button=>button.onclick=()=>navigate(button.dataset.legacyView));
  container.querySelectorAll('[data-open-system]').forEach(button=>button.onclick=()=>button.dataset.openSystem==='system1'?openTasks(null,''):navigate(button.dataset.openSystem));
  container.querySelectorAll('[data-issue]').forEach(button=>button.onclick=()=>{const group=data.issues.find(x=>x.key===button.dataset.issue);openTasks(group.source_ids,group.label)});
  container.querySelectorAll('[data-priority]').forEach(button=>button.onclick=()=>openTasks([button.dataset.priority],'Priority review'));
  if(container.querySelector('#qa-open'))container.querySelector('#qa-open').onclick=()=>openTasks(data.weekly_qa.open_source_ids,'Weekly random checks');
  container.querySelector('#dashboard-all').onclick=()=>openTasks(null,'');
}
