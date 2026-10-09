const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const stages=['content','requirements','interpretation'];
const hosts=['#mw-content','#mw-requirement-content','#mw-interpretation-content'];

// Save existing source-bound revisions before their edited upstream source.
// Each owning API retains its exact retry receipt; never silently rebind S/C/D.
export async function savePage(m){
  if(m.pageSaving||m.busy||m.opening||m.requirements?.pending||m.interpretations?.pending)return false;
  if(m.collaboration.readonly)return false;
  m.pageSaving=true;m.updateBar();
  const ip=m.interpretations,active=ip.active,selected=m.requirements?.selected;
  try{
    for(const [key,draft] of ip.drafts){
      if(!key.startsWith(ip.owner()+':')||(!draft.dirty&&!draft.retry&&!ip.hasQuotation(draft)))continue;
      ip.active=key;if(m.requirements)m.requirements.selected=draft.unit_id;ip.render();
      await ip.save(draft.retry?'retry':'save',{});
      const current=ip.drafts.get(key);
      if(current?.dirty||current?.retry||ip.hasQuotation(current))throw Error(ip.notice||'Interpretation changes remain unsaved.');
    }
    if(m.requirements?.retryRequest)await m.requirements.step('',{},m.requirements.retryRequest);
    if(m.requirements?.retryRequest)throw Error(m.requirements.notice||'Resolve the Requirement save result.');
    if(m.requirements?.hasUnsaved?.()||m.requirements?.dirty){
      await m.requirements.saveAll();
      if(m.requirements.hasUnsaved())throw Error(m.requirements.notice||'Requirement changes remain unsaved.');
    }
    if(m.dirty||m.initialCandidate){if(!await m.saveContent())throw Error('Content changes remain unsaved. Review the save message.');}
    if(ip.hasUnsaved())throw Error('An interpretation operation or an unadded quotation still needs attention.');
    await m.pageWorkflow.refresh();
    m.message('All page changes saved. Processing completion and Archive remain separate.');
    return true;
  }catch(error){m.message(`Page save is incomplete: ${error.message} Saved parts are retained; remaining edits stay on this page. Retry Save after resolving the problem.`,'error');return false;}
  finally{if(m.requirements)m.requirements.selected=selected;ip.active=active;ip.render();m.pageSaving=false;m.updateBar();}
}

export class PageWorkflow{
  constructor(m){this.m=m;this.state=null;this.ticket=0;}
  dirty(){const m=this.m;return !!(m.dirty||m.requirements?.hasUnsaved?.()||m.requirements?.dirty||m.interpretations?.hasUnsaved());}
  stageDirty(stage){const m=this.m;return !!(m.dirty||(stage!=='content'&&(m.requirements?.hasUnsaved?.()||m.requirements?.dirty))||(stage==='interpretation'&&m.interpretations?.hasUnsaved()));}
  completed(){return stages.filter(s=>this.state?.stages[s]?.complete&&!this.stageDirty(s)).length;}
  async refresh(){
    const m=this.m,id=m.id,token=m.token,ticket=++this.ticket;
    if(!id)return;
    try{
      const mode=m.material?.collaboration?.view,view=['master','archive'].includes(mode)?mode:'personal';
      const state=await m.api('/api/material-progress?'+new URLSearchParams({material_id:id,view,...(view==='archive'?{revision:m.material.revision}:{})}));
      if(id!==m.id||token!==m.token||ticket!==this.ticket)return;
      this.state=state;this.error='';this.draw();m.updateBar();
    }catch(error){if(id===m.id&&token===m.token&&ticket===this.ticket){this.state=null;this.error=error.message;this.draw();m.updateBar();}}
  }
  draw(){
    const m=this.m,state=this.state?.material_id===m.id?this.state:null,dirty=this.dirty();
    for(let i=0;i<stages.length;i++){
      const host=m.q(hosts[i]);if(!host?.querySelector)continue;
      let footer=host.querySelector('[data-processing-footer]');
      if(!footer){footer=document.createElement('section');footer.dataset.processingFooter=stages[i];footer.className='mw-processing-footer';host.append(footer);}
      const item=state?.stages[stages[i]],complete=item?.complete&&!this.stageDirty(stages[i]);
      footer.innerHTML=`<strong>${i+2}. ${['Content','Requirements','Interpretation'][i]} · ${complete?'Complete':'In progress'}</strong><p>${dirty?'Save the whole page before confirming completion.':this.error?esc(this.error):item?.problems?.length?esc(item.problems.join(' ')):'Confirm that this entire pane is complete, including entries that are not currently expanded.'}</p>${!m.collaboration.readonly?`<button type="button" data-stage-confirm="${stages[i]}" ${!item||dirty||m.pageSaving||m.busy||m.opening||(!complete&&item.problems.length)?'disabled':''}>${complete?'Reopen this stage':'Confirm complete'}</button>`:''}${complete?`<small>${esc(item.confirmation.actor)} · ${esc(item.confirmation.at)}</small>`:''}`;
      const button=footer.querySelector('button');if(button)button.onclick=()=>void this.confirm(stages[i]);
    }
  }
  async confirm(stage){
    const m=this.m;if(this.dirty()||m.busy||m.pageSaving||m.collaboration.readonly)return;
    const before=this.state;if(!before||before.material_id!==m.id)return;
    const item=before.stages[stage],signature=JSON.stringify([m.id,stage,before.revision,before.version,item.signature,!item.complete]);
    this.requests??=new Map();
    const request=this.requests.get(signature)||{material_id:m.id,stage,expected_revision:before.revision,expected_progress:before.version,signature:item.signature,complete:!item.complete,request_id:crypto.randomUUID()};
    this.requests.set(signature,request);m.busy=true;m.updateBar();this.draw();
    try{
      const result=await m.api('/api/material-progress',request);
      this.requests.delete(signature);
      this.state=result.progress;this.draw();m.message(`Processing progress: ${result.progress.completed}/3 stages complete.`);
    }catch(error){if(error.definitive)this.requests.delete(signature);m.message(error.message,'error');await this.refresh();}
    finally{m.busy=false;m.updateBar();this.draw();}
  }
  leaveDialog(){
    if(this.leaving)return this.leaving;
    const m=this.m;
    this.leaving=new Promise(resolve=>{
      const deadline=performance.now()+3000;let saving=false,finished=false,timer;
      const cancel=event=>{if(saving)event.preventDefault();};
      const finish=allowed=>{if(finished)return;finished=true;clearInterval(timer);dialog.removeEventListener?.('cancel',cancel);this.leaving=null;resolve(allowed);};
      const dialog=m.dialog('<h2>Unsaved changes</h2><p role="alert">Leaving without saving will lose your unsaved changes across this page.</p><p data-leave-status role="status" aria-live="polite"></p><div class="mw-tools"><button data-leave="save" class="primary">Save and leave</button><button data-leave="stay">Continue editing</button><button data-leave="discard" disabled>Leave without saving (3)</button></div>',d=>{
        const discard=d.querySelector('[data-leave="discard"]'),status=d.querySelector('[data-leave-status]');
        const tick=()=>{const seconds=Math.max(0,Math.ceil((deadline-performance.now())/1000));discard.disabled=saving||seconds>0;discard.textContent=seconds?`Leave without saving (${seconds})`:'Leave without saving';};
        timer=setInterval(tick,100);tick();
        d.querySelector('[data-leave="stay"]').onclick=()=>{if(!saving)d.close();};
        discard.onclick=async()=>{
          if(saving||performance.now()<deadline)return;
          saving=true;d.querySelectorAll('button').forEach(b=>b.disabled=true);
          try{await m.discardPage();finish(true);d.close();}
          catch(error){saving=false;status.textContent=error.message;d.querySelectorAll('button').forEach(b=>b.disabled=false);tick();}
        };
        d.querySelector('[data-leave="save"]').onclick=async()=>{
          if(saving)return;saving=true;d.querySelectorAll('button').forEach(b=>b.disabled=true);status.textContent='Saving the whole page…';
          if(await m.save()){finish(true);d.close();return;}
          saving=false;status.textContent='Save did not finish. Your remaining edits are retained. Resolve the save message or continue editing.';d.querySelectorAll('button').forEach(b=>b.disabled=false);tick();
        };
      });
      dialog.addEventListener('cancel',cancel);
      dialog.addEventListener('close',()=>finish(false),{once:true});
    });
    return this.leaving;
  }
}
