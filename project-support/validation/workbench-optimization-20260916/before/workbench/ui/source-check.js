const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

function comparisonEvidence(f){
 const outputs=[f.output_text,...(f.reverse_comparisons||[]).map(r=>r.output_text)].filter(Boolean);
 const text=[...new Set(outputs)];
 const occurrences=(f.occurrence_checks||[]).map(c=>`<p>${esc(c.token)}: ${c.required_occurrences} occurrences in the original; ${c.matched_occurrences} can be matched in the extraction.</p>`).join('');
 const structure=(f.compared_structure||[]).map(c=>`<p>Row ${esc(c.row+1)}, column ${esc(c.column+1)}; spans ${esc(c.row_span)} row(s) and ${esc(c.column_span)} column(s).</p>`).join('');
 return (f.unverified_scope?`<p>${esc(f.unverified_scope)}</p>`:'')+occurrences+(text.length?`<details><summary>Compared extraction</summary>${text.map(t=>`<p>${esc(t)}</p>`).join('')}</details>`:'')+(structure?`<details><summary>Compared structure</summary>${structure}</details>`:'');
}

export function sourceCheckMarkup(report){
 if(!report)return '';
 const findings=report.findings.map((f,i)=>`<article><strong>${esc(f.severity)} · ${esc(f.code.replaceAll('_',' '))}</strong><p>${esc(f.source_text||f.basis)}</p>${(f.compared_structure?.length||f.note_marker||f.reading_order_keys)&&f.source_text?`<p>${esc(f.basis)}</p>`:''}${comparisonEvidence(f)}<p>PDF page ${f.page_index+1} · ${f.bbox?f.bbox.map(v=>v.toFixed(1)).join(', '):'Original region not located'} · ${esc(f.evidence_origin)}</p>${f.bbox?`<button type="button" data-source-region="${i}">Locate original region</button>`:''}${(f.unit_ids.length||(f.source_text&&f.bbox))?`<button type="button" data-source-finding="${i}">${f.unit_ids.length?'Open mapped content':'Prepare missing-content correction'}</button>`:''}</article>`).join('');
 const scopes=report.unverified.map((u,i)=>`<li>${esc(u.code.replaceAll('_',' '))}${u.engine?' · '+esc(u.engine):''}${u.basis?`<p>${esc(u.basis)}</p>`:''}${u.bbox&&Number.isInteger(u.page_index)?`<button type="button" data-source-scope-region="${i}">Locate unchecked source region</button>`:''}${(u.unit_ids||[]).map((id,j)=>`<button type="button" data-source-scope-content="${i}" data-source-scope-unit="${j}">Open mapped content ${j+1}</button>`).join('')}</li>`).join('');
 return `<section class="source-check"><h3>Original-page check</h3><p>${report.stale?'Content, structure or the comparison method changed. Run this page check again.':'Saved comparison for this content version.'} No calibrated accuracy score is available.</p><p>${report.signals.original_lines} original lines compared · ${report.findings.length} findings · ${report.elapsed_seconds}s comparison phase; save time is separate</p>${findings}<details><summary>Unverified scope (${report.unverified.length})</summary><ul>${scopes}</ul><p>These checks require source inspection. Matching text does not establish correct table structure, reading order or footnote ownership.</p></details></section>`;
}

export function wireSourceFindings(panel,report,ex){
 if(!report)return;
 panel.querySelectorAll('[data-source-region], [data-source-scope-region]').forEach(button=>button.onclick=async()=>{
  const f=button.dataset.sourceRegion!==undefined?report.findings[Number(button.dataset.sourceRegion)]:report.unverified[Number(button.dataset.sourceScopeRegion)],original=panel.querySelector('#ex-evidence');
  if(!original)return;
  button.disabled=true;
  try{
   const doc=ex.doc();
   const result=await ex.api('/api/system2/preview?'+new URLSearchParams({document_id:doc.id,page_index:f.page_index,full:true,expected_hash:doc.source.content_hash}));
   if(!panel.isConnected||!button.isConnected)return;
   original.evidenceRequest=null;
   original.innerHTML=`<p>PDF page ${f.page_index+1}. Highlight: ${esc(f.source_text||f.basis||'Unverified original region.')}</p><div class="original-check-region"><img src="${esc(result.image)}" alt="Original PDF page ${f.page_index+1}"><svg aria-label="Original region under inspection" viewBox="0 0 ${report.dimensions.width} ${report.dimensions.height}">${(f.source_regions||[{bbox:f.bbox}]).filter(r=>r.page_index===undefined||r.page_index===f.page_index).map(r=>`<rect x="${r.bbox[0]}" y="${r.bbox[1]}" width="${r.bbox[2]-r.bbox[0]}" height="${r.bbox[3]-r.bbox[1]}" fill="#f39b1922" stroke="#b75d00" stroke-width="2"></rect>`).join('')}</svg></div>`;
   const enlarge=document.createElement('button');enlarge.type='button';enlarge.textContent='Enlarge highlighted original';
   const dialog=document.createElement('dialog');dialog.className='original-evidence-dialog';dialog.setAttribute('aria-label','Highlighted original region');
   const close=document.createElement('button');close.type='button';close.textContent='Close highlighted original';close.onclick=()=>dialog.close();
   dialog.append(close,original.querySelector('.original-check-region').cloneNode(true));
   enlarge.onclick=()=>dialog.showModal();original.prepend(enlarge);original.append(dialog);
   original.scrollIntoView({block:'start'});
  }catch(e){button.textContent='Could not locate original: '+e.message;}
  finally{button.disabled=false;}
 });
 panel.querySelectorAll('[data-source-scope-content]').forEach(button=>button.onclick=()=>{
  const scope=report.unverified[Number(button.dataset.sourceScopeContent)];
  ex.select({id:scope.unit_ids[Number(button.dataset.sourceScopeUnit)]});
 });
 panel.querySelectorAll('[data-source-finding]').forEach(button=>button.onclick=()=>{
  const f=report.findings[Number(button.dataset.sourceFinding)];
  if(f.unit_ids.length){ex.select({id:f.unit_ids[0]});return;}
  const action=panel.querySelector('#ex-action');
  if(!action)return;
  action.value='supplement';action.dispatchEvent(new Event('change'));
  const locator=`page ${f.page_index+1}: ${f.bbox.map(v=>v.toFixed(2)).join(',')}`;
  panel.querySelector('#ex-locator').value=locator;
  panel.querySelectorAll('#ex-fields textarea').forEach(t=>t.value='');
  panel.querySelector('textarea[name="body"]').value=f.source_text||'';
  panel.querySelector('#ex-note').value='';
  panel.querySelector('#ex-range').checked=false;
  panel.querySelector('#ex-decision-message').textContent='Correction draft only. Compare the original, correct the suggested text and provide your evidence before submitting.';
  action.scrollIntoView({block:'center'});
 });
}
