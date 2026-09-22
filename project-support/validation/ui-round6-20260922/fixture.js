import {InterpretationEditor} from '/workbench/frontend/components/interpretations.js';
const q=s=>document.querySelector(s),info=await fetch('/fixture-info').then(r=>r.json()),log=[];
const record=value=>{log.push(value);q('#log').textContent=JSON.stringify(log,null,2);};
const requirements={selected:info.units[0],doc:info.sessions[0],dirty:false,orderedSessions:()=>info.sessions,rootIds:doc=>Object.keys(doc.units),label:id=>'R'+(info.units.indexOf(id)+1),internalLabel:()=> 'G1',async selectFromInterpretation(id){this.selected=id;await editor.open(id);}};
const m={id:info.material.id,state:{actor:{id:'fixture'}},material:info.material,draft:structuredClone(info.material),collaboration:{readonly:false},requirements,q,updateNavigationLock(){},message(text){q('#message').textContent=text;},unsavedDialog(){q('#message').textContent='Unsaved page work remains. Add the quotation or save the edited fields before leaving.';},revealPane(){},
 dialog(html,bind){const dialog=q('#mw-dialog'),trigger=document.activeElement;dialog.innerHTML=html;bind?.(dialog);dialog.showModal();dialog.onclose=()=>trigger?.isConnected&&trigger.focus();},
 api:async(path,body)=>{record({path,body});const response=await fetch(path,body?{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':info.csrf},body:JSON.stringify(body)}:{}),result=await response.json();if(!response.ok)throw Object.assign(Error(result.error||'Fixture request failed'),{status:response.status,definitive:response.status<500});return result;}
};
const editor=new InterpretationEditor(m);m.interpretations=editor;
const open=async index=>{requirements.selected=info.units[index];requirements.doc=info.sessions[index];await editor.open(info.units[index]);};
q('#source').textContent=info.material.blocks.map(b=>b.text).join('\n\n');q('#primary').onclick=()=>open(0);q('#other').onclick=()=>open(1);q('#redraw').onclick=()=>editor.render();q('#evidence').onclick=async()=>record(await fetch('/fixture-evidence').then(r=>r.json()));
q('#reopen').onclick=()=>editor.action('reload',q('#reopen')).catch(error=>m.message(error.message));await open(0);window.fixture={editor,info,m};
