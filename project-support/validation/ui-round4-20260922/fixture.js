import {MarkdownNotebook,blockMarkdown} from '/workbench/frontend/components/markdown-content.js';
const q=s=>document.querySelector(s),info=await fetch('/fixture-info').then(r=>r.json());
const api=async(path,body)=>{const response=await fetch(path,{...(body?{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':info.csrf,'X-Material-API-Version':'3'},body:JSON.stringify(body)}:{})});const result=await response.json();if(!response.ok)throw Error(result.error||'Fixture request failed');return result;};
const m={id:info.id,state:{actor:{id:'fixture',name:'Synthetic Reviewer'}},root:q('#workspace'),q,collaboration:{readonly:false,blockMarkup:()=>''},dirty:false,
 message(text){q('#message').textContent=text;},changed(){this.dirty=true;receipt();},requirements:{start(){m.message('This fixture does not create Requirements.');}},locateBlock(block){m.message('Synthetic source-bound passage: '+block.id);},
 dialog(html,bind){const d=document.createElement('dialog');d.innerHTML=html+'<button data-close>Close</button>';document.body.append(d);d.querySelector('[data-close]').onclick=()=>d.close();d.onclose=()=>d.remove();bind?.(d);d.showModal();},
 renderContent(){const scroll=q('#mw-content').scrollTop;q('#mw-content').innerHTML=n.documentMarkup();n.bind();q('#mw-content').scrollTop=scroll;receipt();}
};
const n=new MarkdownNotebook(m);
function receipt(){q('#receipt').textContent=`Saved revision ${m.material?.revision??'…'} · ${m.dirty?'Unsaved draft':'Saved'} · Undo ${n.writer.undo.length}, Redo ${n.writer.redo.length}`;}
async function reopen(){m.material=await api('/api/material?id='+info.id);m.draft={blocks:structuredClone(m.material.blocks)};m.dirty=false;n.reset();m.renderContent();m.message('Opened the saved synthetic material through a fresh owning service instance.');}
q('#mode').onchange=()=>{n.mode=q('#mode').value;n.showChanges=n.mode==='changes';m.renderContent();};
q('#undo').onclick=()=>{n.writer.travel(false);receipt();};q('#redo').onclick=()=>{n.writer.travel(true);receipt();};
q('#save').onclick=async()=>{try{const result=await api('/api/material/save',{request_id:crypto.randomUUID(),material_id:info.id,expected_revision:m.material.revision,blocks:m.draft.blocks,issues:[],checked_scope:[],association_reviewed:false});m.material=result.material;m.dirty=false;receipt();m.message('Draft saved. This is not content review confirmation.');}catch(e){m.message(e.message);}};
q('#reopen').onclick=reopen;
q('#evidence').onclick=async()=>{q('#metadata').textContent=JSON.stringify({current:m.draft.blocks,saved:await api('/fixture-evidence'),markdown:m.draft.blocks.map(b=>({id:b.id,source:blockMarkdown(b)}))},null,2);q('#details').open=true;};
await reopen();
