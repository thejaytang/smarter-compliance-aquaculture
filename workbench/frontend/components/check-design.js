// One rule tree per card; source explanations and data bindings remain attached.
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const groups=['scope','condition','demand'];
export const ruleOperators={equal:'equals',not_equal:'does not equal',less:'less than',less_or_equal:'at most',greater:'greater than',greater_or_equal:'at least',in:'is one of',not_in:'is not one of',between:'is between',not_between:'is outside',is_null:'is missing',is_not_null:'is present',contains:'contains',not_contains:'does not contain',begins_with:'begins with',ends_with:'ends with',is_empty:'is empty',is_not_empty:'is not empty'};
export const emptyDesign=()=>({schema:'requirement-check-design/1',groups:Object.fromEntries(groups.map(k=>[k,null]))});
export const setDesign=(design=emptyDesign())=>design.schema==='requirement-check-design/2'?design:{...design,schema:'requirement-check-design/2',object_type:'',identity_field:'',assessment_context:'',based_on:null};
export function unmappedNodes(n){return !n||n.rules?.length===0?['No rules defined.']:'expression' in n?['Unmapped predicate: '+n.expression]:[...(n.not?['Group negation needs a consumer mapping.']:[]),...(n.rules||[]).flatMap(unmappedNodes)];}
export function designNode(design,path){const parts=path.split('.');let n=design.groups[parts.shift()];for(const i of parts)n=n.rules[Number(i)];return n;}
export function ruleValue(text,type,operator){
 if(['is_null','is_not_null','is_empty','is_not_empty'].includes(operator))return null;
 const scalar=x=>{if(type==='string')return x;if(type==='boolean'){if(!['true','false'].includes(x))throw Error('Use true or false for a yes/no value.');return x==='true';}const n=Number(x);if(!x.trim()||!Number.isFinite(n)||(type==='integer'&&!Number.isSafeInteger(n)))throw Error('Enter a valid number.');return n;};
 const value=['in','not_in','between','not_between'].includes(operator)?text.split('\n').map(scalar):scalar(text);
 const greater=(a,b)=>{if(type!=='string')return a>b;const left=Array.from(a),right=Array.from(b),i=left.findIndex((c,i)=>c!==right[i]);return i<0?left.length>right.length:(left[i]?.codePointAt(0)??-1)>(right[i]?.codePointAt(0)??-1);};
 if(['between','not_between'].includes(operator)&&(value.length!==2||type==='boolean'||greater(value[0],value[1])))throw Error('Use exactly two ordered values, one per line; boolean ranges are unsupported.');
 return value;
}
export function filterPreview(design){
 const project=n=>n?.rules?{condition:n.condition,rules:n.rules.map(project)}:n?{field:n.field,operator:n.operator,value:n.value}:null;
 return Object.fromEntries(groups.map(k=>[k,unmappedNodes(design.groups[k]).length?null:project(design.groups[k])]));
}
export function setHandoff(fields,design,contextFingerprint='',catalog={fields:[],revision:0}){
 const originalFields=fields;fields=logicFields(fields,design);
 const sets={},gaps=[],keys=['scope','scope_information','condition','condition_information','demand','verification'];
 groups.forEach((key,i)=>{const f=fields[key]||{},letter='ABC'[i],resolved=(f.state||(f.value?.trim()&&f.basis!=='unresolved'?'specified':'unresolved'))==='specified'&&!!f.value?.trim()&&f.basis!=='unresolved'&&!f.gaps?.length;
  sets[letter]={input:i===1?'A':'U',interpretation_field:key,definition:'concepts' in design&&design.groups[key]?logicText(design.groups[key]):f.value||'',resolved,rules:structuredClone(design.groups[key]),references:structuredClone(f.references||[])};
  if(!resolved)gaps.push('Set '+letter+' definition needs review.');gaps.push(...unmappedNodes(design.groups[key]).map(g=>key+': '+g));
 });
 for(const key of ['object_type','identity_field','assessment_context'])if(!design[key]?.trim()){const label=key.replaceAll('_',' ');gaps.push(label[0].toUpperCase()+label.slice(1)+' is not specified.');}
 for(const key of ['scope_information','condition_information','verification']){const f=fields[key]||{};if((f.state&&f.state!=='specified')||!f.value?.trim()||f.basis==='unresolved'||f.gaps?.length){const label=key.replaceAll('_',' ');gaps.push(label[0].toUpperCase()+label.slice(1)+' needs review.');}}
 if(design.identity_field&&!catalog.fields?.some(f=>f.field===design.identity_field))gaps.push('Object identity is not in the Site Model catalog.');
 const inspect=n=>{if(n?.rules)n.rules.forEach(inspect);else if(n&&!('expression' in n)){const f=catalog.fields?.find(f=>f.field===n.field);if(!f||f.type!==n.type||!f.operators.includes(n.operator))gaps.push('Mapping is absent from the current catalog or its type/operator changed.');}};
 Object.values(design.groups).forEach(inspect);
 const canonical=v=>JSON.stringify(v,(_,item)=>item&&typeof item==='object'&&!Array.isArray(item)?Object.fromEntries(Object.entries(item).sort(([a],[b])=>a.localeCompare(b))):item);
 gaps.push(...conceptIssues(design));
 const basis=design.based_on,confirmed=basis&&basis.context_fingerprint===contextFingerprint&&basis.catalog_revision===(catalog.revision||0)&&keys.every(k=>basis.fields[k]===(originalFields[k]?.value||''))&&canonical(basis.design)===canonical(Object.fromEntries(Object.entries(design).filter(([k])=>k!=='based_on')));
 if(!confirmed)gaps.push('Confirm mappings against the current Logic, source context and catalog.');
 return {schema:'requirement-set-handoff/1',object_type:design.object_type,identity_field:design.identity_field,assessment_context:design.assessment_context,sets,...('concepts' in design?{concepts:structuredClone(design.concepts)}:{}),composition:{operator:'subset_of',left:'B',right:'C'},querybuilder:filterPreview(design),mapping_status:gaps.length?'incomplete':'ready_for_consumer_validation',gaps:[...new Set(gaps)],executable:false};
}
export const logicText=n=>!n?'':n.rules?`${n.not?'NOT ':''}(${n.rules.map(logicText).join(' '+n.condition+' ')})`:'expression' in n?n.expression:`${n.field} ${n.operator} ${JSON.stringify(n.value)}`;
export function logicFields(fields,design){const result=structuredClone(fields);if(design&&'concepts' in design)for(const [key,node] of Object.entries(design.groups))if(node)result[key]={...result[key],value:logicText(node),basis:'interpretation',state:'specified',absence_reason:''};return result;}
export function pruneConcepts(design){const used=new Set();const collect=n=>{if(n?.rules)n.rules.forEach(collect);else n?.concept_ids?.forEach(id=>used.add(id));};Object.values(design.groups).forEach(collect);if(design.concepts)design.concepts=design.concepts.filter(c=>used.has(c.id));}
export function conceptIssues(design){
 if(!('concepts' in design))return [];
 const gaps=design.concepts.filter(c=>c.status!=='confirmed').map(c=>c.label+': concept meaning needs confirmation.');
 const walk=n=>{if(n?.rules)n.rules.forEach(walk);else if(n&&!n.concept_ids?.length)gaps.push('Link concepts to rule: '+logicText(n));};
 Object.values(design.groups).forEach(walk);return gaps;
}
const options=(values,current)=>Object.entries(values).map(([v,label])=>`<option value="${esc(v)}" ${v===current?'selected':''}>${esc(label)}</option>`).join('');
const kinds={concept:'Concept',relation:'Relation',property:'Property',event:'Event',action:'Action'};
// Quote exact linked terms without guessing synonyms or changing saved expressions.
export function setDefinitionMarkup(design,key,field={},inspect=true){
 const termMarkup=(terms,label,rule)=>`<span class="ip-concept-term" ${inspect&&rule.id?`role="button" tabindex="0" data-concept-nav="${esc(JSON.stringify(terms.map(t=>t.id)))}" data-rule-id="${esc(rule.id)}"`:''} title="${terms.length===1?esc(kinds[terms[0].kind]||'Concept')+' · '+(terms[0].status==='confirmed'?'Confirmed':'Unconfirmed'):terms.length+' linked concepts'} · Inspect meaning">“${esc(label)}”</span>`;
 const predicate=n=>{
  const text=logicText(n),terms=(design.concepts||[]).filter(t=>n.concept_ids?.includes(t.id)&&t.label.trim());
  const labels=[...new Set(terms.map(t=>t.label))].sort((a,b)=>b.length-a.length).map(s=>s.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')).join('|');
  if(!labels)return esc(text);
  const pattern=new RegExp(`(?<![\\p{L}\\p{N}_])(?:“(${labels})”|"(${labels})"|(${labels}))(?![\\p{L}\\p{N}_])`,'giu');
  let html='',offset=0;
  for(const match of text.matchAll(pattern)){const label=match[1]||match[2]||match[3],matched=terms.filter(t=>t.label.toLowerCase()===label.toLowerCase());html+=esc(text.slice(offset,match.index))+(matched.length?termMarkup(matched,label,n):esc(match[0]));offset=match.index+match[0].length;}
  html+=esc(text.slice(offset));
  return html;
 };
 const node=n=>n.rules?(n.rules.length?`${n.not?'NOT ':''}(${n.rules.map(node).join(' '+esc(n.condition)+' ')})`:'Not yet defined'):predicate(n);
 if(!design.groups?.[key]&&field.state==='not_stated'&&!field.value?.trim())return `<span class="ip-set-expression">${'ABC'[groups.indexOf(key)]} · Not stated in the source</span>`;
 const definition=design.groups?.[key]?node(design.groups[key]):esc(field.value||'Not yet defined');
 return `<span class="ip-set-expression">${'ABC'[groups.indexOf(key)]} = { x${key==='condition'?' ∈ A':''} | ${definition} }</span>`;
}
function conceptMarkup(n,design,disabled,fields={}){
 const terms=(n.concept_ids||[]).map(id=>design.concepts?.find(c=>c.id===id)).filter(Boolean);
 return `<div class="rd-concepts">${terms.map(c=>`<details data-concept="${esc(c.id)}" data-disclosure="concept:${esc(n.id)}:${esc(c.id)}"><summary><span class="rd-chip">${esc(c.label)}</span> <small>${kinds[c.kind]} · ${c.status==='confirmed'?'Confirmed':'Unconfirmed'}</small></summary><label>Name<input data-concept-prop="label" value="${esc(c.label)}" maxlength="200" required ${disabled}></label><label>Type<select data-concept-prop="kind" ${disabled}>${options(kinds,c.kind)}</select></label><label><input data-concept-prop="status" type="checkbox" ${c.status==='confirmed'?'checked':''} ${disabled}> Meaning checked in this context</label>${c.references.map(ref=>`<blockquote>${esc(ref.quote)}<small>${esc(ref.id)}</small></blockquote>`).join('')||'<p>No source quotation attached. Keep inferred meaning explicit in the card’s supporting information.</p>'}<button data-rd="cite-concept" ${disabled||!(fields[n.interpretation_field]?.references||[]).some(ref=>!c.references.some(r=>r.id===ref.id&&r.quote===ref.quote))?'disabled':''}>Use card citations</button><button data-rd="unlink-concept" ${disabled}>Unlink from rule</button></details>`).join('')}<details data-disclosure="link:${esc(n.id)}"><summary>${terms.length?'Link another concept':'Concepts & relations · none linked'}</summary><select data-concept-choice aria-label="Existing concept" ${disabled}><option value="">Choose existing concept</option>${(design.concepts||[]).filter(c=>!n.concept_ids?.includes(c.id)).map(c=>`<option value="${esc(c.id)}">${esc(c.label)} · ${kinds[c.kind]}</option>`).join('')}</select><button data-rd="link-concept" disabled>Link concept</button><button data-rd="add-concept" ${disabled}>New concept</button></details></div>`;
}
export function ruleMarkup(design,key,disabled='',catalog={fields:[]},fields={},ui={}){
 const node=(n,path)=>n.rules?`<div class="rd-group" data-rd-path="${path}" data-rd-id="${esc(n.id)}"><div class="rd-group-heading"><label>Match <select data-rd-prop="condition" ${disabled}>${options({AND:'all (AND)',OR:'any (OR)'},n.condition)}</select></label><label><input type="checkbox" data-rd-prop="not" ${n.not?'checked':''} ${disabled}> NOT</label></div>${n.rules.map((x,i)=>node(x,path+'.'+i)).join('')}<div class="rd-actions"><button data-rd="add-predicate" ${disabled}>Add rule</button><button data-rd="add-group" ${disabled}>Add group</button><button data-rd="remove" ${disabled}>Remove group</button></div></div>`:
 `<div class="rd-rule" data-rd-path="${path}" data-rd-id="${esc(n.id)}">${'expression' in n?`<label>Logic rule<textarea data-rd-prop="expression" aria-label="Logic rule" rows="3" maxlength="4000" required ${disabled}>${esc(n.expression)}</textarea></label>`:`<p class="rd-comparison">${esc(logicText(n))}</p><details data-disclosure="comparison:${esc(n.id)}"><summary>Data comparison</summary><label>Site Model field<select data-rd-prop="field" ${disabled}>${!catalog.fields?.some(f=>f.field===n.field)?`<option value="${esc(n.field)}">${esc(n.field||'Choose a field')}</option>`:''}${(catalog.fields||[]).map(f=>`<option value="${esc(f.field)}" ${f.field===n.field?'selected':''}>${esc(f.label)}</option>`).join('')}</select></label><label>Comparison<select data-rd-prop="operator" ${disabled}>${options(Object.fromEntries(Object.entries(ruleOperators).filter(([k])=>(catalog.fields?.find(f=>f.field===n.field)?.operators||[n.operator]).includes(k))),n.operator)}</select></label><label>Value<textarea data-rd-prop="value" rows="2" ${disabled}>${esc(ui.values?.[n.id]??(Array.isArray(n.value)?n.value.join('\n'):n.value===null?'':String(n.value)))}</textarea></label><p class="ip-caption">${esc(n.type)} · ${['between','not_between'].includes(n.operator)?'Exactly two ordered values, one per line.':['in','not_in'].includes(n.operator)?'One list item per line.':'One value.'}</p></details>`}${conceptMarkup(n,design,disabled,fields)}<button data-rd="remove" ${disabled}>Remove rule</button></div>`;
 return design.groups[key]?node(design.groups[key],key):`<button data-rd="start" data-rd-path="${key}" ${disabled}>Define ${key} logic</button>`;
}
export function domainMarkup(design,disabled=''){
 return `<div class="rd-metadata">${[['object_type','Check object'],['assessment_context','Assessment period / event']].map(([key,label])=>`<label>${label}<textarea data-rd-meta="${key}" rows="2" maxlength="4000" ${disabled}>${esc(design[key])}</textarea></label>`).join('')}</div>`;
}
export function designMarkup(design,disabled='',catalog={fields:[],revision:0},handoff=null){
 return `<details class="ip-rule-design" data-disclosure="integration"><summary>Data integration · ${handoff?.mapping_status==='ready_for_consumer_validation'?'ready for consumer validation':'mapping incomplete'}</summary><p>${catalog.fields?.length?'Use the configured Site Model catalog.':'Not connected · no Site Model fields configured.'} Empty groups remain unmapped. These filters do not run a compliance check.</p><label>Object identity field<input data-rd-meta="identity_field" value="${esc(design.identity_field)}" placeholder="table.column" pattern="[A-Za-z_][A-Za-z0-9_]*\\.[A-Za-z_][A-Za-z0-9_]*" ${disabled}></label>${groups.map(k=>`<button data-rd="add-mapping" data-rd-path="${k}" ${disabled||!catalog.fields?.length?'disabled':''}>Add ${k} data comparison</button>`).join('')}<p>Concept confirmation records an agreed meaning. Data bindings require separate validation against the same object, event and period.</p><button data-ip="confirm-mappings" ${disabled}>Confirm data mappings</button><details><summary>QueryBuilder filters</summary><p>Unmapped predicates or NOT block the complete affected filter. No inferred SQL is emitted.</p><pre class="rd-preview">${esc(JSON.stringify(filterPreview(design),null,2))}</pre></details>${handoff?`<details><summary class="rd-mapping-summary">Set handoff &amp; mapping questions (${handoff.gaps.length})</summary><ul class="rd-mapping-gaps">${handoff.gaps.map(x=>`<li>${esc(x)}</li>`).join('')}</ul><pre class="rd-handoff-preview">${esc(JSON.stringify(handoff,null,2))}</pre></details>`:''}</details>`;
}
export function revealDesign(host,ruleId,conceptIds=[]){
 const rule=[...(host.querySelectorAll?.('[data-rd-id]')||[])].find(n=>n.dataset.rdId===ruleId);if(!rule)return false;
 for(let el=rule.parentElement;el;el=el.parentElement)if(el.tagName==='DETAILS')el.open=true;
 const concepts=[...rule.querySelectorAll('[data-concept]')].filter(n=>conceptIds.includes(n.dataset.concept));concepts.forEach(n=>n.open=true);
 const name=concepts[0]?.querySelector('[data-concept-prop="label"]');
 const target=conceptIds.length===1?(name&&!name.disabled?name:concepts[0]?.querySelector('summary')):conceptIds.length?rule:rule.querySelector('[data-rd-prop="expression"],[data-rd-prop="value"],[data-rd-prop="field"]');
 const focus=target||rule;if(!['INPUT','TEXTAREA','SELECT','BUTTON','SUMMARY','A'].includes(focus.tagName)&&!focus.hasAttribute?.('tabindex'))focus.setAttribute('tabindex','-1');focus.scrollIntoView({block:'nearest'});focus.focus();return true;
}
export function bindDesign(host,design,changed,render,catalog={fields:[]},fields={},ui={}){
 const makeGroup=()=>({id:crypto.randomUUID(),condition:'AND',rules:[]});
 const makePredicate=group=>({id:crypto.randomUUID(),expression:'',interpretation_field:group,concept_ids:[]});
 const makeRule=group=>({id:crypto.randomUUID(),field:'',operator:'equal',value:'',type:'string',interpretation_field:group,concept_ids:[]});
 const notify=()=>{design.concepts||=[];ui.undo=null;ui.error='';const error=host.querySelector('.rd-error');if(error)error.textContent='';changed();};
 const feedback=message=>{ui.error=message;const error=host.querySelector('.rd-error');if(error)error.textContent=message;};
 host.querySelectorAll('[data-rd]').forEach(b=>b.onclick=e=>{
  e.stopPropagation();if(b.disabled)return;
  const el=b.closest('[data-rd-path]'),path=el.dataset.rdPath,root=path.split('.')[0],n=designNode(design,path),action=b.dataset.rd;let destination,undo;
  try{
   if(action==='undo-remove'){
    if(ui.undo?.root!==root)return;const previous=ui.undo;design.groups[root]=structuredClone(previous.group);design.concepts=structuredClone(previous.concepts);notify();render();return;
   }
   if(action==='start'){design.groups[root]=makeGroup();const p=makePredicate(root);p.expression=fields[root]?.value||'';design.groups[root].rules.push(p);destination={ruleId:p.id};}
   else if(action==='remove'){
    undo={root,group:structuredClone(design.groups[root]),concepts:structuredClone(design.concepts||[])};
    const parts=path.split('.');if(parts.length===1)design.groups[root]=null;else {const index=Number(parts.pop());designNode(design,parts.join('.')).rules.splice(index,1);}
   }
   else if(action==='add-mapping'){design.groups[root]||=makeGroup();const rule=makeRule(root);design.groups[root].rules.push(rule);destination={ruleId:rule.id};}
   else if(action==='add-predicate'){const p=makePredicate(root);n.rules.push(p);destination={ruleId:p.id};}
   else if(action==='add-group'){const g=makeGroup(),p=makePredicate(root);g.rules.push(p);n.rules.push(g);destination={ruleId:p.id};}
   else if(action==='add-concept'){const c={id:crypto.randomUUID(),label:'New concept',kind:'concept',status:'proposed',references:[]};design.concepts||=[];design.concepts.push(c);n.concept_ids=[...(n.concept_ids||[]),c.id];destination={ruleId:n.id,conceptIds:[c.id]};}
   else if(action==='link-concept'){
    const id=b.parentElement.querySelector('[data-concept-choice]').value;if(!id||n.concept_ids?.includes(id)||!design.concepts?.some(c=>c.id===id))return;
    n.concept_ids=[...(n.concept_ids||[]),id];
   }
   else {
    const id=b.closest('[data-concept]').dataset.concept,c=design.concepts?.find(c=>c.id===id);if(!c)return;
    if(action==='unlink-concept')n.concept_ids=n.concept_ids.filter(x=>x!==id);
    else if(action==='cite-concept'){
     const additions=(fields[root]?.references||[]).filter((ref,i,all)=>!c.references.some(r=>r.id===ref.id&&r.quote===ref.quote)&&all.findIndex(r=>r.id===ref.id&&r.quote===ref.quote)===i);
     if(!additions.length)return;if(c.references.length+additions.length>100)throw Error('A concept supports at most 100 citations. Keep the existing evidence and choose fewer card citations.');
     c.references=[...c.references,...additions.map(({id,quote})=>({id,quote}))];
    }else return;
   }
   pruneConcepts(design);notify();if(undo)ui.undo=undo;render(destination);
  }catch(error){feedback(error.message);}
 });
 host.querySelectorAll('[data-concept-choice]').forEach(select=>select.onchange=()=>{
  const n=designNode(design,select.closest('[data-rd-path]').dataset.rdPath),button=select.parentElement.querySelector('[data-rd="link-concept"]');
  button.disabled=select.disabled||!select.value||n.concept_ids?.includes(select.value)||!design.concepts?.some(c=>c.id===select.value);
 });
 const validateValue=(el,n)=>{
  const input=el.querySelector('[data-rd-prop="value"]');if(!input)return true;
  try{ruleValue(input.value,n.type,n.operator);input.setCustomValidity('');input.removeAttribute?.('aria-invalid');return true;}
  catch(error){input.setCustomValidity(error.message);input.setAttribute?.('aria-invalid','true');return false;}
 };
 host.querySelectorAll('[data-rd-prop]').forEach(input=>{
  const el=input.closest('[data-rd-path]'),n=designNode(design,el.dataset.rdPath),prop=input.dataset.rdProp;
  if(prop==='value')validateValue(el,n);
  input.oninput=()=>{
   const value=el.querySelector('[data-rd-prop="value"]');let error='';
   try{
    if(prop==='value'){ui.values||={};ui.values[n.id]=input.value;n.value=ruleValue(input.value,n.type,n.operator);}
    else {
     n[prop]=prop==='not'?input.checked:input.value;
     if(prop==='field'){
      const f=catalog.fields?.find(f=>f.field===input.value);if(f){n.type=f.type;n.operator=f.operators[0];n.value=['is_null','is_not_null','is_empty','is_not_empty'].includes(n.operator)?null:n.type==='boolean'?false:n.type==='string'?'':0;delete ui.values?.[n.id];}
      notify();render();return;
     }
     if(['type','operator'].includes(prop)){ui.values||={};ui.values[n.id]=value.value;n.value=ruleValue(value.value,n.type,n.operator);}
    }
    el.querySelectorAll('[data-rd-prop]').forEach(control=>control.setCustomValidity(''));
   }catch(e){n.value=value.value;error=e.message;}
   validateValue(el,n);const preview=host.querySelector('.rd-preview');if(preview)preview.textContent=JSON.stringify(filterPreview(design),null,2);notify();feedback(error);
  };
 });
 host.querySelectorAll('[data-concept-prop]').forEach(input=>input.oninput=()=>{
  const c=design.concepts.find(c=>c.id===input.closest('[data-concept]').dataset.concept),prop=input.dataset.conceptProp;c[prop]=prop==='status'?(input.checked?'confirmed':'proposed'):input.value;if(prop!=='status')c.status='proposed';notify();
  host.querySelectorAll('[data-concept]').forEach(el=>{
   if(el.dataset.concept!==c.id)return;el.querySelector('.rd-chip').textContent=c.label;el.querySelector('summary small').textContent=kinds[c.kind]+' · '+(c.status==='confirmed'?'Confirmed':'Unconfirmed');
   for(const key of ['label','kind','status']){const control=el.querySelector(`[data-concept-prop="${key}"]`);if(!control||control===input)continue;if(key==='status')control.checked=c.status==='confirmed';else control.value=c[key];}
  });
 });
 host.querySelectorAll('[data-rd-meta]').forEach(input=>input.oninput=()=>{design[input.dataset.rdMeta]=input.value;notify();});
}
