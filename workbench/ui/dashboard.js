import {weeklyChart} from './qa-chart.js';
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

const rendered = new WeakMap();

export function systemCards(systems) {
  return `<section class="system-overview" aria-label="Three-system workflow">${systems.map(s=>`
    <article class="system-card" aria-labelledby="overview-${esc(s.key)}">
      <div class="system-card-top"><span class="eyebrow">${esc(s.label)}</span><span class="system-status ${esc(s.availability)}">${esc(s.status)}</span></div>
      <h2 id="overview-${esc(s.key)}">${esc(s.title)}</h2><p class="system-purpose">${esc(s.purpose)}</p>
      <div class="system-pending"><b class="${s.pending.value===null?'unavailable':''}">${s.pending.value===null?'Not connected':esc(s.pending.value)}</b><span>${esc(s.pending.label)}</span></div>
      <dl class="system-metrics">${s.metrics.map(m=>`<div><dt>${esc(m.label)}</dt><dd>${m.value===null?'<span aria-label="Not connected">–</span>':esc(m.value)}</dd></div>`).join('')}</dl>
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
  const c=data.counts, total=c.sources;
  let offset=0;
  const segments=data.selection.map(row=>{
    const percent=total?row.count/total*100:0;
    const circle=`<circle class="selection-${row.key.toLowerCase()}" cx="70" cy="70" r="53" pathLength="100" fill="none" stroke-width="13" stroke-dasharray="${percent} ${100-percent}" stroke-dashoffset="${-offset}" transform="rotate(-90 70 70)"/>`;
    offset+=percent; return circle;
  }).join('');
  const maxIssue=Math.max(1,...data.issues.map(row=>row.count));
  const maxCategory=Math.max(1,...data.categories.map(row=>row.count));
  container.innerHTML=`<div class="requirement-overview"><div class="dashboard-meta"><span>Sources → Extraction → Semantic enrichment</span><small>Data read at ${esc(stamp)}</small></div>
    <p class="overview-intro">One workspace for the complete requirement workflow.</p>
    ${systemCards(data.systems || [])}
    ${weeklyChart(data.weekly_qa,data.qa_schedule)}
    <details class="source-dashboard"><summary><strong>System1 details</strong><span>Source selection, originals and review priorities</span></summary>
    <section class="metrics" aria-label="System1 source metrics">${[['Total sources',c.sources],['Pending sources',c.pending],['Originals stored',c.stored],['Included sources',c.included]].map(([label,count])=>`<div class="metric"><span>${label}</span><b>${count}</b></div>`).join('')}</section>
    <div class="dashboard-grid">
      <section class="panel"><h2>Source selection</h2><div class="selection-chart"><svg viewBox="0 0 140 140" role="img" aria-label="${esc(data.selection.map(x=>x.label+' '+x.count+' sources').join(', '))}"><circle class="ring-background" cx="70" cy="70" r="53" fill="none" stroke-width="13"/>${segments}<text x="70" y="69" text-anchor="middle" class="ring-count">${total}</text><text x="70" y="88" text-anchor="middle" class="ring-label">sources</text></svg><ul class="chart-legend">${data.selection.map(x=>`<li><span class="legend-label"><i class="selection-${x.key.toLowerCase()}"></i>${x.label}</span><b>${x.count}</b><small>${total?(x.count/total*100).toFixed(1):'0.0'}%</small></li>`).join('')}</ul></div></section>
      <section class="panel"><h2>Review reasons</h2><div class="issue-bars">${data.issues.map(x=>`<button type="button" class="chart-row" data-issue="${x.key}" ${x.count?'':'disabled'}><span>${x.label}</span><b>${x.count}</b><progress class="chart-track" value="${x.count}" max="${maxIssue}" aria-hidden="true"></progress></button>`).join('')}</div><p class="muted chart-note">A source can have several issues. Select a bar to open the matching tasks.</p></section>
      <section class="panel"><h2>Source types and originals</h2>${data.categories.map(x=>`<div class="category-row"><span>${esc(x.label)}</span><progress class="category-track" value="${x.count}" max="${maxCategory}" aria-label="${esc(x.label)}: ${x.count} sources"></progress><b>${x.count}</b></div>`).join('')}<div class="snapshot-summary"><span>Local originals</span><b>${c.stored} / ${total}</b><progress value="${c.stored}" max="${Math.max(1,total)}" aria-label="Originals stored ${c.stored} of ${total} sources"></progress><small>${c.missing} sources have no local original. Storage does not mean the content is verified.</small></div></section>
      <section class="panel"><div class="dashboard-panel-heading"><h2>Priority review</h2><button type="button" id="dashboard-all">Review ${c.pending} sources</button></div><div class="priority-list">${data.priority.map(x=>`<button type="button" data-priority="${esc(x.source_id)}"><span class="source-id">${esc(x.source_id)}</span><span>${esc(x.title)}</span>${x.human_issue?'<small>Reviewer feedback to verify</small>':''}</button>`).join('')||'<p class="muted">No pending reviews.</p>'}</div></section>
    </div></details><details class="dashboard-definitions"><summary>Metric definitions and data sources</summary><p>Each system reports its own units: sources in System1, extraction review items in System2 and enrichment items in System3. Counts are not added across stages. Not connected means unavailable, not zero or complete. Demo reviews are excluded from live metrics and weekly accuracy.</p><p>System1 reads the governed source registry. Pending counts use unique unresolved source IDs, and review reasons can overlap. Stored originals are not necessarily verified. The overview refreshes after an applied decision; source trends are not inferred from current counts.</p></details></div>`;
  rendered.set(container,signature);
  if(definitionsOpen)container.querySelector('.dashboard-definitions').open=true;
  if(sourcesOpen)container.querySelector('.source-dashboard').open=true;
  container.querySelectorAll('[data-open-system]').forEach(button=>button.onclick=()=>button.dataset.openSystem==='system1'?openTasks(null,''):navigate(button.dataset.openSystem));
  container.querySelectorAll('[data-issue]').forEach(button=>button.onclick=()=>{const group=data.issues.find(x=>x.key===button.dataset.issue);openTasks(group.source_ids,group.label)});
  container.querySelectorAll('[data-priority]').forEach(button=>button.onclick=()=>openTasks([button.dataset.priority],'Priority review'));
  if(container.querySelector('#qa-open'))container.querySelector('#qa-open').onclick=()=>openTasks(data.weekly_qa.open_source_ids,'Weekly random checks');
  container.querySelector('#dashboard-all').onclick=()=>openTasks(null,'');
}
