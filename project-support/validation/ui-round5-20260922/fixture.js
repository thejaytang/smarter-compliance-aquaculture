import {RequirementsEditor} from '/workbench/frontend/components/requirements.js';
import {treeNodes} from '/workbench/frontend/components/requirement-structure.js';
const q=s=>document.querySelector(s),info=await fetch('/fixture-info').then(r=>r.json()),log=[];
const record=value=>{log.push(value);q('#log').textContent=JSON.stringify(log,null,2);};
const m={id:info.material.id,state:{actor:{id:'fixture'}},material:info.material,draft:structuredClone(info.material),collaboration:{readonly:false},q,
 updateNavigationLock(){},revealPane(){},unsavedDialog(){q('#message').textContent='Unsaved Requirement work: save or discard it before opening another entry.';},
 interpretations:{pending:false,sourceChanged(){record({fixtureAssociationSourceChanged:true});},canLeave(){return true;},async open(id){q('#association').textContent=id;},render(){q('#association').textContent='No selection';}},
 dialog(html,bind){const d=q('#mw-dialog'),trigger=document.activeElement;d.innerHTML=html;bind?.(d);d.showModal();d.onclose=()=>trigger?.isConnected&&trigger.focus();},
 api:async(path,body)=>{
  record({path,body});
  if(path.startsWith('/api/requirements/session')&&q('#delay-read').checked){q('#delay-read').checked=false;await new Promise(resolve=>setTimeout(resolve,3000));}
  if(path.startsWith('/api/requirements/session')&&q('#fail-read').checked){q('#fail-read').checked=false;throw Object.assign(Error('Synthetic session read failure'),{definitive:true});}
  if(body?.action==='preview'&&q('#reject').checked){q('#reject').checked=false;throw Object.assign(Error('Synthetic definitive annotation rejection. Keep the exact source selection.'),{definitive:true});}
  if(body?.action==='preview'&&q('#uncertain').checked){q('#uncertain').checked=false;throw Error('Synthetic transport interruption');}
  const response=await fetch(path,body?{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':info.csrf},body:JSON.stringify(body)}:{}),result=await response.json();
  if(!response.ok)throw Object.assign(Error(result.error||'Fixture request failed'),{status:response.status,definitive:response.status<500});return result;
 }};
const editor=new RequirementsEditor(m);editor.context=editor.key();editor.render();await editor.loadList();if(editor.doc?.id!==info.sessions.main)await editor.open(info.sessions.main);
q('#source').textContent=info.material.blocks[0].text;
q('#open').onclick=()=>editor.open(info.sessions[q('#session').value]);
q('#collapse').onclick=()=>{for(const uid of Object.keys(editor.doc.units))for(const node of treeNodes(editor.groupEditor.tree(uid)))if(['group','clause'].includes(node.kind))editor.groupEditor.closed.add(node.id);editor.render(true);};
q('#jump-object').onclick=()=>editor.navigateAnnotation([{session_id:info.sessions.main,unit_id:info.nodes.main_unit,node_id:info.nodes.object,field:'Object'}]);
q('#jump-relationship').onclick=()=>editor.navigateAnnotation([{session_id:info.sessions.main,unit_id:info.nodes.main_unit,node_id:info.nodes.relationship,relationship:true,field:'relationship'}]);
q('#intake').onclick=()=>editor.start('main');q('#combine').onclick=()=>editor.start('main',true);
// Fixture-only helpers live inside the modal so they work without bypassing native focus containment.
const originalDialog=m.dialog;m.dialog=(html,bind)=>originalDialog(html,d=>{bind?.(d);if(!d.querySelector('[data-source-block]'))return;for(const [label,count] of [['Select 101 fixture passages',101],['Clear fixture picks',0]]){const b=document.createElement('button');b.textContent=label;b.onclick=()=>{d.querySelectorAll('[data-source-block]').forEach((n,i)=>n.checked=i<count);d.querySelector('[data-source-block]').onchange();};d.prepend(b);}});
q('#evidence').onclick=async()=>record(await fetch('/fixture-evidence').then(r=>r.json()));
window.fixture={editor,info,m};
