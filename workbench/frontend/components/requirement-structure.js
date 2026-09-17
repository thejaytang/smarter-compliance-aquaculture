import {semanticClass} from './markdown-content.js';
import {quantityPreset,quantityMode,quantityPreview,quantityRange} from './quantity.js';
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const roles=['Subject','Modal Verb','Main Verb','Object','conditions','exceptions','subrequirement'];
export function treeNodes(tree){return [tree,...(tree.children||[]).flatMap(treeNodes)];}
export function sourceBounds(node){const spans=node.span?[node.span]:(node.children||[]).map(sourceBounds).filter(Boolean);return spans.length?[Math.min(...spans.map(s=>s[0])),Math.max(...spans.map(s=>s[1]))]:null;}
export function relationshipSides(node){
 const before=[],after=[],crossing=[];
 if(node.relationship)for(const child of node.children||[]){const span=sourceBounds(child);(span&&span[1]<=node.relationship.span[0]?before:span&&span[0]>=node.relationship.span[1]?after:crossing).push(child);}
 const order=(a,b)=>(sourceBounds(a)?.[0]??Infinity)-(sourceBounds(b)?.[0]??Infinity);
 return {before:before.sort(order),after:after.sort(order),crossing};
}
export const transparentGroup=n=>n.kind==='group'&&!n.span&&!n.relationship&&!n.negated&&(n.quantity===1||JSON.stringify(n.quantity)==='[1,1]')&&n.children.length===1&&((n.role==='requirements'&&n.children[0].kind==='clause')||(!['exceptions','subrequirement'].includes(n.role)&&n.children[0].kind==='group'&&n.children[0].role===n.role));
export function treeText(node,units={},trees={},seen=new Set()){
 if(node.kind==='fragment')return node.text;
 if(node.kind==='reference'){
  const u=units[node.target_id];if(!u)return `Unresolved reference ${node.target_id}`;
  if(seen.has(node.target_id))return u.text;
  return trees[node.target_id]?.children?.length?u.text+' [ '+treeText(trees[node.target_id],units,trees,new Set([...seen,node.target_id]))+' ]':u.text;
 }
 if(node.relationship){const sides=relationshipSides(node),part=items=>items.map(n=>treeText(n,units,trees,seen)).join(' | ')||'Unmarked';return `${node.negated?'NOT ':''}{ before: ${part(sides.before)}; relationship: ${node.relationship.text}; after: ${part(sides.after)}${node.kind==='group'?`; quantity: ${node.quantity===null?'unresolved':quantityPreview(node.quantity)} of ${node.children.length}`:''} }`;}
 const parts=node.children.map(n=>treeText(n,units,trees,seen));
 if(node.kind==='clause')return '{ '+node.children.map((n,i)=>`${n.role}: ${parts[i]}`).join('; ')+' }';
 const q=node.quantity===null?'QC unresolved':quantityPreview(node.quantity);
 return `${node.negated?'NOT ':''}(${q} of ${node.children.length}: ${parts.join(' | ')})`;
}
export function treeSource(tree,text,bounds,referenceSpans={}){
 const chars=Array.from(text),[a,b]=bounds||[0,chars.length];
 const spans=treeNodes(tree).flatMap(n=>[n.kind==='reference'&&referenceSpans[n.target_id]?{...n,span:referenceSpans[n.target_id]}:n,...(n.relationship?[{id:n.id,role:'relationship',span:n.relationship.span}]:[])]).filter(n=>n.role&&n.role!=='requirements'&&n.span&&n.span[0]>=a&&n.span[1]<=b);
 const stops=[...new Set([a,b,...spans.flatMap(n=>n.span)])].sort((x,y)=>x-y);
 return stops.slice(0,-1).map((start,i)=>{
  const end=stops[i+1],active=spans.filter(n=>n.span[0]<=start&&n.span[1]>=end),word=esc(chars.slice(start,end).join(''));
  if(!active.length)return word;
  const nested=active.slice().sort((x,y)=>(y.span[1]-y.span[0])-(x.span[1]-x.span[0]));
  const overlap=nested.some((n,j)=>j&&!(n.span[0]>=nested[j-1].span[0]&&n.span[1]<=nested[j-1].span[1]));
  return `<span class="semantic ${overlap?'semantic-overlap':semanticClass(nested.at(-1).role)}" title="${esc(active.map(n=>n.role+' · '+n.id).join('; '))}">${word}</span>`;
 }).join('');
}
export const plainField=n=>n.kind==='group'&&!n.span&&!n.relationship&&(!n.negated||n.role==='conditions')&&n.role!=='requirements'&&n.quantity===1&&n.children.length===1&&['fragment','reference'].includes(n.children[0].kind);
export function structureLabels(doc,unitLabels={}){let g=Object.keys(doc.units||{}).length,f=0;const labels={};for(const t of Object.values({...doc.structure_views,...doc.structures}))for(const n of treeNodes(t))labels[n.id]=n.kind==='fragment'?`F${++f}`:n.kind==='reference'?(unitLabels[n.target_id]||n.target_id):plainField(n)?n.role:`G${++g}`;return labels;}
const control=(action,text,attrs='')=>`<button type="button" data-straction="${action}" ${attrs}>${text}</button>`;
export class StructureEditor{
 constructor(editor){this.e=editor;this.closed=new Set();this.qcOpen=new Set();this.rangeModes=new Map();this.selection=null;this.linkOpen=new Set();}
 tree(uid){return this.e.doc.structures?.[uid]||this.e.doc.structure_views?.[uid];}
 labels(tree){const unitLabels=Object.fromEntries(Object.keys(this.e.doc.units||{}).map(id=>[id,this.e.internalLabel?.(id)||this.e.label(id)]));return structureLabels({...this.e.doc,structure_views:{...this.e.doc.structure_views,...(!Object.values({...this.e.doc.structure_views,...this.e.doc.structures}).some(t=>t.id===tree.id)?{fallback:tree}:{})}},unitLabels);}

 unitMarkup(u,complete,inline){
  const e=this.e,done=e.doc.done.includes(u.id),tree=this.tree(u.id),disabled=e.locked;
  const root= !inline && e.rootIds?.(e.doc)?.length===1 && e.rootIds(e.doc)[0]===u.id;
  const body=`<div class="rq-unit-body rq-structure-editor">${this.nodeMarkup(tree,u,tree,this.labels(tree),disabled,true)}</div>`;
  if(root)return `<section class="rq-unit rq-entry-root" data-unit="${esc(u.id)}" aria-current="${u.id===e.selected}">${body}</section>`;
  return `<details class="rq-unit${inline?' rq-inline-condition':''}" data-unit="${esc(u.id)}" aria-current="${u.id===e.selected}" ${!e.closedUnits.has(u.id)?'open':''}><summary data-rq="select-unit" data-id="${esc(u.id)}" data-toggle="true"><strong>${esc(e.internalLabel?.(u.id)||e.label(u.id))}</strong><span class="rq-unit-preview">${esc(u.text.slice(0,100))}</span></summary>${body}</details>`;
 }
 toolsMarkup(allowed=roles){return `<div class="rq-selection-tools" data-selection-tools hidden role="toolbar" aria-label="Assign selected source text"><label class="rq-tool-target">Add to <select data-selection-target aria-label="Add selected text to"></select></label><span class="rq-tool-section">${control('add-group','Group')}${control('relationship','Relationship','class="semantic semantic-7" disabled title="Select a connector inside a Group"')}</span><span class="rq-tool-divider" aria-hidden="true"></span><span class="rq-tool-section">${allowed.filter(role=>!['exceptions','subrequirement','requirements'].includes(role)).map(role=>control('add',esc(role),`data-field="${role}" class="semantic ${semanticClass(role)}"`)).join('')}</span></div>`;}
 sourceMarkup(node,u,tree,disabled){
  const span=node.span||[0,Array.from(u.text).length],allowed=node.kind==='clause'?(this.e.doc.roles?.[u.id]==='condition'?['conditions']:roles):[node.role];
  const offset=this.e.doc.spans?.[u.id]?.[0]||0,referenceSpans=Object.fromEntries(Object.entries(this.e.doc.spans||{}).map(([id,span])=>[id,span.map(n=>n-offset)]));
  return `<div class="rq-group-source" data-source-node="${esc(node.id)}" data-source-owner="${esc(u.id)}" data-source-start="${span[0]}"><div class="rq-selectable-source" data-structure-source tabindex="0" contenteditable="true" spellcheck="false" role="textbox" aria-readonly="true" aria-label="Original text for ${esc(node.id)}">${treeSource(tree,u.text,span,referenceSpans)}</div>${!disabled?this.toolsMarkup(allowed):''}</div>`;
 }
 nodeMarkup(node,u,tree,labels,disabled,root=false,suppressRemove=false){
  if(transparentGroup(node))return this.nodeMarkup(node.children[0],u,tree,labels,disabled);
  const removable=!root&&!suppressRemove&&!this.e.locked,removeLabel=!plainField(node)&&(node.kind==='group'||node.kind==='clause')?'Remove group and all items':'Remove item';
  const remove=removable?control('remove','×',`class="rq-node-remove" aria-label="${removeLabel}" title="${removeLabel}"`):'';
  const id=esc(node.id),label=labels[node.id],text=node.span?Array.from(u.text).slice(...node.span).join(''):'';
  if(node.kind==='fragment')return `<div class="rq-tree-leaf semantic ${semanticClass(node.role)}" data-structure-node="${id}" data-owner="${u.id}"><span class="rq-tree-id">${label}</span><span>${esc(node.text)}</span>${!disabled?control('decompose','Split',`title="Split into nested ${esc(node.role)} items" ${node.span?'':'disabled'}`) :''}${remove}</div>`;
  if(node.kind==='reference'&&['exceptions','subrequirement'].includes(node.role)){
   if(this.e.doc.units[node.target_id])return '';
   const linked=this.e.completeRequirements(u.id).find(v=>v.id===node.target_id),label=this.e.label(node.target_id),wording=linked?.text||this.e.unitText(node.target_id);
   return `<div class="rq-linked-requirement" data-structure-node="${id}" data-owner="${u.id}"><button type="button" class="rq-linked-target" data-rq="select-unit" data-id="${esc(node.target_id)}" title="${esc(wording)}"><strong>${esc(label)}</strong><span>${esc(wording)}</span></button>${!this.e.locked?control('remove','×',`class="rq-node-remove" aria-label="Remove link to ${esc(label)}" title="Remove this link only; keep ${esc(label)}"`):''}</div>`;
  }
  if(node.kind==='reference'&&this.e.doc.units[node.target_id])return `<div class="rq-tree-reference" data-structure-node="${id}" data-owner="${u.id}">${this.unitMarkup(this.e.doc.units[node.target_id],disabled,true)}${!disabled?control('remove','Remove reference'):''}</div>`;
  if(node.kind==='reference')return `<div class="rq-tree-leaf rq-tree-reference" data-structure-node="${id}" data-owner="${u.id}"><button type="button" data-rq="decompose" data-id="${esc(node.target_id)}">${esc(this.e.label(node.target_id))}</button><span>${esc(this.e.unitText(node.target_id))}</span>${!disabled?control('remove','Remove'):''}</div>`;
  if(node.kind==='group'&&['exceptions','subrequirement'].includes(node.role)){
   const legacy=this.hasInlineRelation(node),children=node.children.filter(child=>this.hasExternalRelation(child)),locked=this.e.locked;
   const nested=treeNodes(tree).some(parent=>parent.kind==='group'&&parent.role===node.role&&parent.children.some(child=>child.id===node.id));
   const rows=children.map(child=>`<li>${!locked&&!legacy?`<input type="checkbox" data-structure-pick="${esc(child.id)}" aria-label="Select ${esc(child.kind==='reference'?this.e.label(child.target_id):labels[child.id])} for grouping">`:''}${this.nodeMarkup(child,u,tree,labels,locked)}</li>`).join('');
   return `<section class="rq-reference-picker rq-relation-group semantic ${semanticClass(node.role)}" data-structure-node="${id}" data-owner="${u.id}"><strong>${node.role==='exceptions'?'Exception':'Subrequirement'}${nested?' · '+esc(labels[node.id]):''}</strong>${remove}<div class="rq-tree-body">${!legacy&&children.length?this.qcMarkup(node,locked):''}${!locked&&!legacy&&(children.length>1||nested)?`<div class="rq-tree-actions">${children.length>1?control('group','Group selected','disabled title="Select at least two direct items"'):''}${this.canUngroup(node,tree)?control('ungroup','Ungroup','title="Remove this grouping and keep its links"'):''}</div>`:''}<ol class="rq-tree-children rq-linked-list">${rows}</ol>${this.linkMarkup(u,node,locked||legacy,true)}</div></section>`;
  }
  if(plainField(node))return `<div class="rq-plain-field semantic ${semanticClass(node.role)}" data-structure-node="${id}" data-owner="${u.id}"><div class="rq-plain-field-title"><strong>${esc(node.role)}</strong>${node.negated?'<small>Saved NOT annotation · read-only</small>':''}</div>${remove}${node.children.map(child=>this.nodeMarkup(child,u,tree,labels,disabled,false,true)).join('')}</div>`;
  const group=node.kind==='group',kind=group?'Group · '+node.role:'Group',summary=`<strong>${label}</strong><span>${esc(kind)}</span>${node.negated?'<small class="rq-not-label">Saved NOT annotation · read-only</small>':''}${group?`<span class="rq-tree-count" title="Quantity of direct items">${node.quantity===null?'Choose quantity':quantityPreview(node.quantity)}</span>`:''}${!root&&text?`<span class="rq-tree-summary">${esc(text)}</span>`:''}`;
  const childMarkup=child=>`<li>${group&&!disabled?`<input type="checkbox" data-structure-pick="${esc(child.id)}" aria-label="Select ${labels[child.id]} in ${label}">`:''}${this.nodeMarkup(child,u,tree,labels,disabled)}</li>`;
  const sides=relationshipSides(node),relationship=node.relationship?`<li class="rq-relationship-row"><div class="rq-relationship semantic semantic-7"><strong>Relationship</strong><span>${esc(node.relationship.text)}</span>${!this.e.locked?control('remove-relationship','×','class="rq-node-remove" aria-label="Remove relationship" title="Remove this relationship; keep both parts"'):''}</div></li>`:'';
  const children=relationship?sides.before.map(childMarkup).join('')+relationship+sides.after.map(childMarkup).join('')+sides.crossing.map(childMarkup).join(''):node.children.map(childMarkup).join('');
  const relationGap=node.relationship&&(!sides.before.length||!sides.after.length)?'<p class="rq-hint" role="status">Mark the content before and after this relationship.</p>':'';
  return `<${root?'section':'details'} class="rq-tree-node ${group?'rq-tree-group semantic '+semanticClass(node.origin_role||node.role):'rq-tree-clause'}" data-structure-node="${id}" data-owner="${u.id}" ${!root&&!this.closed.has(node.id)?'open':''}>${root?'':`<summary>${summary}${remove}</summary>`}<div class="rq-tree-body">${root&&this.e.rootIds?.(this.e.doc)?.length>1?this.sourceMarkup(node,u,tree,disabled):''}${root&&!disabled?'<p class="rq-hint">Select the original text above to mark fields or groups.</p>':''}${group&&(node.children.length>1||node.quantity!==1||this.qcOpen.has(node.id))?this.qcMarkup(node,disabled):''}${group?`<div class="rq-tree-actions">${!disabled&&!['exceptions','subrequirement'].includes(node.role)?(node.children.length>1?control('group','Group selected','disabled title="Select at least two direct items"'):'')+(this.canUngroup(node,tree)?control('ungroup','Ungroup',`title="Remove this grouping and keep its items"`):''):''}</div>`:''}<ol class="rq-tree-children">${children}</ol>${relationGap}${!node.children.length?'<p class="rq-blank">Select wording above to add items.</p>':''}${this.e.doc.roles?.[u.id]!=='condition'&&node.kind==='clause'?this.clauseLinks(u,node,disabled,root):''}</div></${root?'section':'details'}>`;
 }
 canUngroup(node,tree){
  const parent=treeNodes(tree).find(p=>p.children?.some(n=>n.id===node.id));
  const all=n=>n?.kind==='group'&&!n.negated&&!n.relationship&&(n.quantity===n.children.length||JSON.stringify(n.quantity)===JSON.stringify([n.children.length,n.children.length]));
  return all(node)&&all(parent)&&parent.quantity===parent.children.length;
 }
 clauseLinks(u,node,disabled,root){
  const fields=this.linkMarkup(u,node,disabled);
  if(!fields)return '';
  if(root)return `<div class="rq-entry-links">${fields}</div>`;
  const open=this.linkOpen.has(node.id);
  return `<div class="rq-nested-links">${control('show-link',open?'Hide link options':'Link requirement…',`aria-expanded="${open}" ${disabled?'disabled':''}`)}${open?fields:''}</div>`;
 }
 async apply(request){
  const e=this.e;
  if(e.doc.phase==='complete'){if(!(await e.step('phase',{phase:'fields'})))return false;}
  else if(e.doc.done.includes(request.unit_id)){if(!(await e.step('reopen',{unit_id:request.unit_id})))return false;}
  return e.step('structure',request);
 }
 updateSelectionTools(bar,uid,node){
  const tree=this.tree(uid),restricted=node.kind==='group'&&!['requirements','exceptions','subrequirement'].includes(node.role)?node.role:this.e.doc.roles?.[uid]==='condition'?'conditions':null;
  bar.querySelectorAll('[data-straction="add"]').forEach(button=>{button.hidden=!!restricted&&button.dataset.field!==restricted;});
  const relation=bar.querySelector('[data-straction="relationship"]');
  if(relation){relation.disabled=node===tree||!node.span||['exceptions','subrequirement'].includes(node.role);relation.title=relation.disabled?'Create a Group around both parts first':'Mark the connector for this Group; AND / OR use quantity';}
 }
 hasExternalRelation(node){return node.kind==='reference'?!this.e.doc.units[node.target_id]:node.kind==='group'&&(node.children||[]).some(child=>this.hasExternalRelation(child));}
 hasInlineRelation(node){return node.kind==='reference'?!!this.e.doc.units[node.target_id]:node.kind==='group'?(node.children||[]).some(child=>this.hasInlineRelation(child)):true;}
 historyMarkup(){
  const e=this.e,rows=[];
  for(const u of Object.values(e.doc.units||{}))for(const node of treeNodes(this.tree(u.id)||{children:[]})){
   if(node.kind!=='group'||!['exceptions','subrequirement'].includes(node.role)||!this.hasInlineRelation(node))continue;
   rows.push(`<section class="rq-legacy-relation"><strong>${node.role==='exceptions'?'Exception':'Subrequirement'} · ${esc(e.internalLabel?.(u.id)||e.label(u.id))}</strong><p>${esc(treeText(node,e.doc.units,{...e.doc.structure_views,...e.doc.structures}))}</p></section>`);
  }
  return rows.length?`<details class="rq-legacy-relations"><summary>Earlier inline relationships · ${rows.length}</summary><p>Retained saved relationships and quantities. These are not links to other Requirement entries.</p>${rows.join('')}</details>`:'';
 }
 linkMarkup(u,node={},disabled=false,inline=false){
  const fields=node.kind==='group'?[node.role]:['subrequirement','exceptions'].filter(role=>!node.children?.some(n=>n.role===role));
  return fields.map(role=>{const linked=new Set(treeNodes(node).filter(n=>n.kind==='reference'&&n.role===role).map(n=>n.target_id)),choices=this.e.completeRequirements(u.id).filter(v=>!linked.has(v.id));
   const title=role==='exceptions'?'Exception':'Subrequirement';
   const content=`<div class="rq-tree-link" data-reference-role="${role}"><label><select data-structure-reference aria-label="${title} Requirement" ${disabled||!choices.length?'disabled':''}><option value="">Choose a Requirement…</option>${choices.map(v=>`<option value="${esc(v.id)}">${esc(this.e.label(v.id))} · ${esc(v.text.slice(0,90))}</option>`).join('')}</select></label>${control('link','Link','disabled')}</div>${!choices.length?'<small>No other available Requirement.</small>':''}`;
   return inline?content:`<section class="rq-reference-picker semantic ${semanticClass(role)}"><strong>${title}</strong>${content}</section>`;
  }).join('');
 }
 qcMarkup(node,disabled){
  const count=node.children.length,q=node.quantity,mode=quantityMode(q,count),custom=this.rangeModes.get(node.id)??(q!==null&&mode==='custom'),values=Array.isArray(q)?q:[q??'',q??''];
  return `<div class="rq-qc-row" data-rq-qc data-structure-qc data-count="${count}"><output data-rq-preview class="rq-qc-preview" aria-live="polite">${q===null?'Choose quantity':quantityPreview(q)}</output><div class="rq-quantity-presets">${[['all','All'],['any','Any'],['one','Only'],['not-all','Not All']].map(([preset,label])=>control('preset',label,`data-preset="${preset}" title="${preset==='not-all'?'At least one, fewer than all':preset==='all'?`K = ${count}`:preset==='any'?`[1, ${count}]`:'K = 1'}" aria-pressed="${!custom&&mode===preset}" ${disabled||!count||(preset==='not-all'&&count<2)?'disabled':''}`)).join('')}${control('range-mode','MIN–MAX',`aria-pressed="${custom}" ${disabled||!count?'disabled':''}`)}</div><input data-rq-min aria-label="Minimum" inputmode="numeric" pattern="[0-9]*" value="${values[0]}" ${disabled||!count||!custom?'disabled':''}><span>-</span><input data-rq-max aria-label="Maximum" inputmode="numeric" pattern="[0-9]*" value="${values[1]}" ${disabled||!count||!custom?'disabled':''}></div><small class="rq-qc-error" data-qc-error hidden role="status"></small>`;
 }
 bind(host){
  host.querySelectorAll?.('[data-entry-source] > .rq-source-preview').forEach(source=>{source.setAttribute('data-structure-source','');source.setAttribute('contenteditable','true');source.setAttribute('role','textbox');source.setAttribute('aria-readonly','true');source.setAttribute('aria-label','Requirement original text');source.setAttribute('spellcheck','false');});
  host.querySelectorAll?.('[data-structure-source]').forEach(source=>{
   source.onbeforeinput=event=>event.preventDefault();source.onpaste=event=>event.preventDefault();source.oncut=event=>event.preventDefault();source.ondrop=event=>event.preventDefault();
   const capture=event=>{
    if(this.e.locked){this.selection=null;host.querySelectorAll('[data-selection-tools]').forEach(n=>n.hidden=true);return;}
    const selection=window.getSelection();if(!selection?.rangeCount||selection.isCollapsed){host.querySelectorAll('[data-selection-tools]').forEach(n=>n.hidden=true);return;}
    const range=selection.getRangeAt(0);if(!source.contains(range.startContainer)||!source.contains(range.endContainer))return;
    if(!range.toString().trim()){this.selection=null;host.querySelectorAll('[data-selection-tools]').forEach(n=>n.hidden=true);return;}
    const prefix=range.cloneRange();prefix.selectNodeContents(source);prefix.setEnd(range.startContainer,range.startOffset);
    const entry=source.closest('[data-entry-source]'),container=entry||source.closest('[data-source-node]');
    let start=Number(container.dataset.sourceStart||0)+Array.from(prefix.toString()).length,end=start+Array.from(range.toString()).length,uid=container.dataset.sourceOwner,id=container.dataset.sourceNode;
    if(entry){const candidates=Object.entries(this.e.doc.spans).filter(([,s])=>s[0]<=start&&s[1]>=end).sort((a,b)=>(b[1][1]-b[1][0])-(a[1][1]-a[1][0]));if(!candidates.length)return;uid=candidates[0][0];start-=candidates[0][1][0];end-=candidates[0][1][0];id=this.tree(uid).id;}
    const tree=this.tree(uid),containers=treeNodes(tree).reverse().filter(n=>['clause','group'].includes(n.kind)&&n.span&&n.span[0]<=start&&n.span[1]>=end).sort((a,b)=>(a.span[1]-a.span[0])-(b.span[1]-b.span[0]));
    if(containers.length)id=containers[0].id;
    this.selection={unit_id:uid,node_id:id,start,end};
    host.querySelectorAll('[data-selection-tools]').forEach(n=>n.hidden=n.parentElement!==container);
    const bar=container.querySelector('[data-selection-tools]');if(bar){
      const owners=[...containers.filter(n=>n!==tree&&!transparentGroup(n)),tree];
      const owner=owners[0],labels=this.labels(tree);this.selection.node_id=owner.id;
      const target=bar.querySelector('[data-selection-target]');
      if(target){target.innerHTML=owners.map(n=>`<option value="${esc(n.id)}">${esc(n===tree?this.e.label(uid):labels[n.id])}${n===tree?' · Requirement':' · Group'}</option>`).join('');
        target.onchange=()=>{const next=owners.find(n=>n.id===target.value);if(!next)return;this.selection={unit_id:uid,node_id:next.id,start,end};this.updateSelectionTools(bar,uid,next);};}
      this.updateSelectionTools(bar,uid,owner);
      const rect=range.getBoundingClientRect();bar.style.left=Math.max(8,Math.min(event?.clientX??rect.left,window.innerWidth-bar.offsetWidth-8))+'px';bar.style.top=Math.max(8,Math.min((event?.clientY??rect.bottom)+10,window.innerHeight-bar.offsetHeight-8))+'px';
    }

   };source.onmouseup=capture;source.onkeyup=capture;
  });
  host.onmousedown=event=>{if(!event.target.closest('[data-selection-tools],[data-structure-source]'))host.querySelectorAll('[data-selection-tools]').forEach(n=>n.hidden=true);};
  host.onkeydown=event=>{if(event.key==='Escape')host.querySelectorAll('[data-selection-tools]').forEach(n=>n.hidden=true);};
  host.querySelectorAll?.('[data-selection-tools]').forEach(toolbar=>toolbar.onmousedown=e=>{if(e.target.closest('button'))e.preventDefault();});
  host.querySelectorAll?.('details[data-structure-node]').forEach(node=>node.ontoggle=()=>{if(!node.isConnected)return;if(node.open)this.closed.delete(node.dataset.structureNode);else this.closed.add(node.dataset.structureNode);});
  host.querySelectorAll?.('[data-structure-reference]').forEach(select=>select.onchange=()=>{select.closest('.rq-tree-link').querySelector('[data-straction="link"]').disabled=this.e.locked||!select.value;});
  host.querySelectorAll?.('[data-structure-pick]').forEach(pick=>pick.onchange=()=>{
    const owner=pick.closest('[data-structure-node]'),picks=owner.querySelectorAll(':scope > .rq-tree-body > .rq-tree-children > li > [data-structure-pick]:checked');
    const button=owner.querySelector(':scope > .rq-tree-body > .rq-tree-actions > [data-straction="group"]');
    if(button){button.disabled=this.e.locked||picks.length<2;button.textContent=picks.length?`Group selected (${picks.length})`:'Group selected';}
  });
  host.querySelectorAll?.('[data-structure-qc]').forEach(row=>this.bindQC(row));
 }
 bindQC(row){
  const e=this.e,node=row.closest('[data-structure-node]'),uid=node.dataset.owner,id=node.dataset.structureNode,key='tree:'+uid+':'+id;
  const model=treeNodes(this.tree(uid)).find(n=>n.id===id),inputs=[row.querySelector('[data-rq-min]'),row.querySelector('[data-rq-max]')],output=row.querySelector('[data-rq-preview]'),error=row.parentElement.querySelector('[data-qc-error]'),count=model.children.length;
  const validate=()=>{try{quantityRange(...inputs.map(i=>i.value),count);error.hidden=true;inputs.forEach(i=>i.removeAttribute('aria-invalid'));return true;}catch(err){error.textContent=err.message;error.hidden=false;inputs.forEach(i=>i.setAttribute('aria-invalid','true'));return false;}};
  const preview=()=>{output.textContent=`[${inputs[0].value||'…'}, ${inputs[1].value||'…'}]`;validate();};
  if(e.quantityDrafts.has(key)){inputs.forEach((n,i)=>n.value=e.quantityDrafts.get(key)[i]);preview();}
  row.commitQuantity=async()=>{
   if(!e.quantityDrafts.has(key))return true;
   if(e.locked||!validate())return false;
   const value=quantityRange(...inputs.map(i=>i.value),count);
   if(JSON.stringify(value)!==JSON.stringify(model.quantity)){
    const ok=await this.apply({unit_id:uid,node_id:id,operation:'quantity',quantity:value});if(!ok)return false;
   }
   e.quantityDrafts.delete(key);e.render(true);return true;
  };
  inputs.forEach(input=>{input.dataset.previous=input.value;input.onbeforeinput=event=>{if(event.data&&!/^\d+$/.test(event.data))event.preventDefault();};input.oninput=()=>{if(!/^\d*$/.test(input.value)){input.value=input.dataset.previous;return;}if(input.value!=='')input.value=String(Math.min(count,Number(input.value)));input.dataset.previous=input.value;e.quantityDrafts.set(key,inputs.map(i=>i.value));preview();e.m.updateNavigationLock?.();};input.onkeydown=event=>{if(event.key==='Enter'){event.preventDefault();void row.commitQuantity();}if(event.key==='Escape'){event.preventDefault();e.quantityDrafts.delete(key);e.render(true);}};});
  row.onfocusout=event=>{if(row.contains(event.relatedTarget)||event.relatedTarget?.closest('[data-rq],[data-straction],summary'))return;void row.commitQuantity();};
 }
 async action(button){
  const e=this.e;if(button.disabled)return;
  if(button.dataset.straction==='not')throw Error('Explicit NOT editing is unavailable. Keep negation in the original wording.');
  const element=button.closest('[data-structure-node]'),action=button.dataset.straction,fromSelection=['add','add-group','relationship','degroup-range','clear-range'].includes(action),uid=fromSelection?this.selection?.unit_id:element?.dataset.owner,id=fromSelection?this.selection?.node_id:element?.dataset.structureNode;
  if(!uid||!id)throw Error('Select original wording first.');
  if(action==='show-link'){if(this.linkOpen.has(id))this.linkOpen.delete(id);else this.linkOpen.add(id);e.render(true);return;}
  if(action==='show-qc'){if(this.qcOpen.has(id))this.qcOpen.delete(id);else this.qcOpen.add(id);e.render(true);return;}
  if(e.locked)return;
  if(action==='range-mode'){this.rangeModes.set(id,true);e.render(true);e.host.querySelector(`[data-structure-node="${id}"] [data-rq-min]`)?.focus();return;}
  if(action==='remove')for(const n of treeNodes(this.tree(uid)).filter(n=>n.id===id).flatMap(treeNodes))e.quantityDrafts.delete('tree:'+uid+':'+n.id);
  for(const row of e.host.querySelectorAll('[data-rq-qc]')){if(action==='remove'&&element.contains?.(row))continue;if(action==='preset'&&row.contains(button))continue;if(row.commitQuantity&&!(await row.commitQuantity()))return;}
  const model=treeNodes(this.tree(uid)).find(n=>n.id===id);if(!model)return;
  let request={unit_id:uid,node_id:id,operation:action};
  if(fromSelection){
   if(!this.selection||this.selection.unit_id!==uid||this.selection.node_id!==id)throw Error('Select the original wording in this group first.');
   request={...request,...this.selection,field:button.dataset.field};
  }
  if(action==='preset'){this.rangeModes.set(id,false);request.operation='quantity';request.quantity=quantityPreset(button.dataset.preset,model.children.length);e.quantityDrafts.delete('tree:'+uid+':'+id);}
  if(action==='group')request.selected=[...element.querySelectorAll(':scope > .rq-tree-body > .rq-tree-children > li > [data-structure-pick]:checked')].map(n=>n.dataset.structurePick);
  if(action==='link'){const link=button.closest('.rq-tree-link');request.target_id=link.querySelector('[data-structure-reference]').value;request.field=link.dataset.referenceRole;if(!request.target_id)throw Error('Choose another Requirement to link.');}
  e.selected=uid;await this.apply(request);this.selection=null;
 }
}
