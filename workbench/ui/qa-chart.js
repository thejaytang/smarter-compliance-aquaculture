const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const label=week=>new Date(week+'T12:00:00Z').toLocaleDateString('en-GB',{day:'numeric',month:'short',timeZone:'UTC'});
const status=p=>p.status==='not_connected'?'Not connected':p.status==='no_eligible'?'No eligible items':p.status==='no_batch'?'No batch':p.accuracy===null?`${p.reviewed}/${p.sampled} reviewed`:`${p.accuracy}% · ${p.correct}/${p.sampled} correct`;
export function weeklyChart(data,schedule={}){
  if(!data)return '';
  const x=i=>60+i*145, y=accuracy=>185-accuracy*1.5;
  const lines=data.series.map(s=>{
    let path='',previous=false;
    s.points.forEach((p,i)=>{if(p.accuracy===null){previous=false;return}path+=(previous?' L':' M')+x(i)+' '+y(p.accuracy);previous=true});
    return `<g class="qa-${s.key}"><path d="${path}" fill="none" stroke-width="2.5"/>${s.points.map((p,i)=>p.accuracy===null?'':`<circle cx="${x(i)}" cy="${y(p.accuracy)}" r="4"><title>${s.label}, week of ${label(p.week)}: ${status(p)}</title></circle>`).join('')}</g>`;
  }).join('');
  const hasValues=data.series.some(s=>s.points.some(p=>p.accuracy!==null));
  return `<section class="panel weekly-qa"><div class="dashboard-panel-heading"><div><h2>Weekly random-check accuracy</h2><p class="muted">Every Monday · 5 items per system · Last 5 weeks</p></div><button type="button" id="qa-open" ${data.open_source_ids.length?'':'disabled'}>System1 checks · ${data.open_source_ids.length}</button></div>
    ${schedule.status==='WAITING'?`<p class="issue">Weekly sampling is waiting: ${esc(schedule.message)}. It will retry automatically.</p>`:''}<ul class="qa-legend">${data.series.map(s=>`<li class="qa-${s.key}"><i></i>${s.label}<small>${status(s.points.at(-1))}</small></li>`).join('')}</ul>
    <svg class="qa-chart" viewBox="0 0 690 235" role="img" aria-label="Weekly random-check accuracy from 0 to 100 percent. Exact results appear in the weekly results table below.">${[0,50,100].map(v=>`<line class="qa-grid" x1="60" y1="${y(v)}" x2="640" y2="${y(v)}"/><text x="48" y="${y(v)+4}" text-anchor="end">${v}%</text>`).join('')}${data.weeks.map((w,i)=>`<text x="${x(i)}" y="212" text-anchor="middle">${label(w)}</text>`).join('')}${lines}${hasValues?'':'<text x="350" y="107" text-anchor="middle">No completed weekly checks yet</text>'}</svg>
    <p class="muted chart-note">Accuracy = correct ÷ sampled, after every item in the batch is reviewed. Pending or missing weeks have gaps. A sample below 5 is shown at its actual size. Equal results overlap on the chart.</p>
    <details><summary>Weekly results and coverage</summary><div class="history-wrap"><table class="history"><thead><tr><th>Week of (Oslo)</th>${data.series.map(s=>`<th>${s.label}</th>`).join('')}</tr></thead><tbody>${data.weeks.map((w,i)=>`<tr><td>${esc(w)}</td>${data.series.map(s=>`<td>${status(s.points[i])}</td>`).join('')}</tr>`).join('')}</tbody></table></div></details></section>`;
}
