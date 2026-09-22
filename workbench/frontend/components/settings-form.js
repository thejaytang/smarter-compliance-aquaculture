// Shared native form guards. These helpers never save or compare secret values.
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pending=new WeakSet();
export const settingsPending=form=>pending.has(form);
export function lockSettingsControls(root){const states=[...root.querySelectorAll('input,select,textarea,button,fieldset')].map(node=>[node,node.disabled]);for(const [node]of states)node.disabled=true;return ()=>{for(const [node,disabled]of states)node.disabled=disabled;};}
export async function settingsOperation(form,run,work){if(pending.has(form))return;pending.add(form);try{return await run(async()=>{const restore=lockSettingsControls(form);try{return await work();}finally{restore();}});}finally{pending.delete(form);}}
export function settingsFailure(host,error,{read,local,saved,stamp,useSaved,useLocal,run=fn=>fn()}){
 host.textContent=error.message;
 if(!error.definitive||!/(?:settings|catalog).*changed/i.test(error.message))return;
 const button=host.ownerDocument.createElement('button');button.type='button';button.textContent='Compare current saved settings';host.appendChild(button);
 button.onclick=()=>run(async()=>{
  try{const current=await read();if(host.isConnected===false)return;const original=stamp();
   host.innerHTML=`<p>Review the latest saved configuration and your retained proposal. Neither choice saves settings or starts processing.</p><div class="sync-choices"><section><h4>Current saved configuration</h4><pre>${esc(JSON.stringify(saved(current),null,2))}</pre></section><section><h4>Your retained proposal</h4><pre>${esc(JSON.stringify(local(),null,2))}</pre></section></div><button type="button" data-settings-version="saved">Use current saved values</button><button type="button" data-settings-version="local">Continue retained proposal</button>`;
   host.querySelectorAll('[data-settings-version]').forEach(choice=>choice.onclick=()=>{
    if(stamp()!==original){host.textContent='Your proposal changed. Compare current saved settings again before choosing.';host.appendChild(button);return;}
    if(choice.dataset.settingsVersion==='saved')useSaved(current);else useLocal(current);
    host.textContent='Selected configuration is in the form. Use Save explicitly when ready.';
   });
  }catch(e){host.textContent=e.message+' Your entered settings are retained.';host.appendChild(button);}
 });
}
