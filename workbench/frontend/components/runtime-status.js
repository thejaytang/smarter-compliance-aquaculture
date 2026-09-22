const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export function runtimeMarkup(result){return `<h2>Runtime status</h2><p>Checked ${esc(result.checked_at||'time unavailable')}. This reports service operation; it does not certify content quality.</p>${result.persistence_error?`<p class="mw-runtime-error">Status history could not be saved: ${esc(result.persistence_error.message)}</p>`:''}${(result.components||[]).map(c=>`<section class="mw-runtime-component"><strong>${esc(c.name)} · ${esc(c.state)}</strong><small>Last success: ${esc(c.last_success||'Not yet recorded')}</small>${c.unavailable_reason?`<p>${esc(c.unavailable_reason)}</p>`:''}${c.current_task?`<p>Current task: ${esc(c.current_task)} · ${Math.round(c.duration||0)} seconds</p>`:''}${c.error?`<p class="mw-runtime-error">${esc(c.error.message)}${c.retry_seconds?` · next automatic service check in ${Math.ceil(c.retry_seconds)} seconds`:''}</p><small>Reference ${esc(c.error.event_id||c.error.code)}</small><p>Saved work is retained. For failed extraction, open the material, inspect its failure and choose Extract to start a new candidate when ready.</p>`:''}${c.last_error?`<details data-runtime-component="${esc(c.id)}"><summary data-runtime-focus="history:${esc(c.id)}">Previous failure retained</summary><p>${esc(c.last_error.at)} · ${esc(c.last_error.message)}</p><small>${esc(c.last_error.event_id||c.last_error.code)}</small></details>`:''}</section>`).join('')}<p>Refresh reads status only. It does not start conversion or apply business decisions.</p>`;}
export function installRuntimeStatus({api,button,dialog}) {
  let pending=false,lastRead=0,result=null,error='';
  const loading=()=>{dialog.setAttribute('aria-busy',String(pending));const control=dialog.querySelector('[data-runtime-refresh]');if(control){control.setAttribute('aria-disabled',String(pending));control.textContent=pending?'Reading status…':error?'Retry status':'Refresh status';}};
  const draw=()=>{
    const active=dialog.ownerDocument.activeElement,focus=dialog.contains(active)?active.dataset.runtimeFocus:null,scroll=dialog.scrollTop;
    const open=new Set([...dialog.querySelectorAll('details[open]')].map(node=>node.dataset.runtimeComponent));
    dialog.innerHTML=(result?runtimeMarkup(result):'<h2>Runtime status</h2><p>No successful status read yet.</p>')+
      `<p role="status">${error?`Unable to read current runtime status: ${esc(error)}${result?' The checked report above is the last successful read and may be out of date.':''}`:''}</p><button data-runtime-refresh data-runtime-focus="refresh">Refresh status</button> <button data-runtime-close data-runtime-focus="close">Close</button>`;
    dialog.querySelectorAll('details').forEach(node=>{node.open=open.has(node.dataset.runtimeComponent);});
    dialog.querySelector('[data-runtime-close]').onclick=()=>dialog.close();dialog.querySelector('[data-runtime-refresh]').onclick=()=>refresh(true);loading();
    if(focus)([...dialog.querySelectorAll('[data-runtime-focus]')].find(node=>node.dataset.runtimeFocus===focus)||dialog.querySelector('[data-runtime-close]')).focus({preventScroll:true});
    dialog.scrollTop=scroll;
  };
  async function refresh(force=false){
    if(pending||(!force&&Date.now()-lastRead<15000))return;pending=true;if(dialog.open)loading();
    try{result=await api('/api/runtime-status');error='';button.dataset.state=result.status;button.textContent=result.status==='healthy'?'Runtime status':result.status==='starting'?'Runtime starting':'Runtime needs attention';}
    catch(failure){error=failure.message;button.dataset.state='degraded';button.textContent='Runtime status unavailable';}
    finally{pending=false;lastRead=Date.now();if(dialog.open)draw();}
  }
  button.onclick=async()=>{draw();dialog.showModal();await refresh(true);};return {refresh};
}
