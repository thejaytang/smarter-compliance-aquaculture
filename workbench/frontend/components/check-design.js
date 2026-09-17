// Optional explicit Site Model mapping, independent of the six prose fields.
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const groups=['scope','condition','demand'];
export const ruleOperators={equal:'equals',not_equal:'does not equal',less:'less than',less_or_equal:'at most',greater:'greater than',greater_or_equal:'at least',in:'is one of',not_in:'is not one of',between:'is between',not_between:'is outside',is_null:'is missing',is_not_null:'is present',contains:'contains',not_contains:'does not contain',begins_with:'begins with',ends_with:'ends with',is_empty:'is empty',is_not_empty:'is not empty'};
export const emptyDesign=()=>({schema:'requirement-check-design/1',groups:Object.fromEntries(groups.map(k=>[k,null]))});
export function designNode(design,path){const parts=path.split('.');let n=design.groups[parts.shift()];for(const i of parts)n=n.rules[Number(i)];return n;}
export function ruleValue(text,type,operator){
 if(['is_null','is_not_null','is_empty','is_not_empty'].includes(operator))return null;
 const scalar=x=>{if(type==='string')return x;if(type==='boolean'){if(!['true','false'].includes(x))throw Error('Use true or false for a yes/no value.');return x==='true';}const n=Number(x);if(!x.trim()||!Number.isFinite(n)||(type==='integer'&&!Number.isSafeInteger(n)))throw Error('Enter a valid number.');return n;};
 return ['in','not_in','between','not_between'].includes(operator)?text.split('\n').map(scalar):scalar(text);
}
export function filterPreview(design){
 const project=n=>n?.rules?{condition:n.condition,rules:n.rules.map(project)}:n?{field:n.field,operator:n.operator,value:n.value}:null;
 return Object.fromEntries(groups.map(k=>[k,project(design.groups[k])]));
}
export function designMarkup(design,disabled='',catalog={fields:[],revision:0}){
 const options=(values,current)=>Object.entries(values).map(([v,label])=>`<option value="${v}" ${v===current?'selected':''}>${label}</option>`).join('');
 const node=(n,path)=>n.rules?`<div class="rd-group" data-rd-path="${path}"><label>Match <select data-rd-prop="condition" ${disabled}>${options({AND:'all of these (AND)',OR:'any of these (OR)'},n.condition)}</select></label>${n.rules.map((x,i)=>node(x,path+'.'+i)).join('')}<div class="rd-actions"><button data-rd="add-rule" ${disabled}>Add comparison</button><button data-rd="add-group" ${disabled}>Add group</button><button data-rd="remove" ${disabled}>Remove group</button></div></div>`:
 `<div class="rd-rule" data-rd-path="${path}"><label>Site Model field<select data-rd-prop="field" ${disabled}>${!catalog?.fields?.some(f=>f.field===n.field)?`<option value="${esc(n.field)}">${esc(n.field?'Unlisted: '+n.field:'Choose a field')}</option>`:''}${(catalog?.fields||[]).map(f=>`<option value="${esc(f.field)}" ${f.field===n.field?'selected':''}>${esc(f.label)}</option>`).join('')}</select></label><label>Comparison<select data-rd-prop="operator" ${disabled}>${options(Object.fromEntries(Object.entries(ruleOperators).filter(([k])=>(catalog?.fields?.find(f=>f.field===n.field)?.operators||[n.operator]).includes(k))),n.operator)}</select></label><label>Value type<select data-rd-prop="type" disabled>${options({string:'Text',integer:'Whole number',double:'Number',boolean:'Yes / no'},n.type)}</select></label><label>Value<textarea data-rd-prop="value" rows="2" ${disabled}>${esc(Array.isArray(n.value)?n.value.join('\n'):n.value===null?'':String(n.value))}</textarea></label><p class="ip-caption">For a list or range, use one value per line. For yes/no, use true or false.</p><label>Based on<select data-rd-prop="interpretation_field" ${disabled}>${options({scope:'Scope',scope_information:'Scope information',condition:'Condition',condition_information:'Condition information',demand:'Demand',verification:'Verification'},n.interpretation_field)}</select></label><button data-rd="remove" ${disabled}>Remove comparison</button></div>`;
 return `<details class="ip-rule-design"><summary>Site Model mapping · optional</summary><p>${catalog?.fields?.length?'Choose from the configured Site Model field catalog.':'No fields configured. Add agreed fields in Settings → Site Model fields.'} Empty groups remain unmapped. These filters do not run a compliance check.</p>${groups.map(k=>`<section><h5>${k[0].toUpperCase()+k.slice(1)}</h5>${design.groups[k]?node(design.groups[k],k):`<button data-rd="start" data-rd-path="${k}" ${disabled}>Map ${k}</button>`}</section>`).join('')}<p role="alert" class="rd-error"></p><details><summary>QueryBuilder handoff</summary><p>The saved design retains links to interpretation fields and their sources. SQLAlchemy must supply the allowed fields, joins and evaluation context.</p><pre class="rd-preview">${esc(JSON.stringify(filterPreview(design),null,2))}</pre></details></details>`;
}
export function bindDesign(host,design,changed,render,catalog={fields:[]}){
 const makeGroup=()=>({id:crypto.randomUUID(),condition:'AND',rules:[]});
 const makeRule=group=>({id:crypto.randomUUID(),field:'',operator:'equal',value:'',type:'string',interpretation_field:group});
 host.querySelectorAll('[data-rd]').forEach(b=>b.onclick=e=>{e.stopPropagation();if(b.disabled)return;const path=b.closest('[data-rd-path]').dataset.rdPath,root=path.split('.')[0];const n=designNode(design,path),action=b.dataset.rd;
  if(action==='start'){design.groups[root]=makeGroup();design.groups[root].rules.push(makeRule(root));}
  else if(action==='remove'){const parts=path.split('.');if(parts.length===1)design.groups[root]=null;else {const index=Number(parts.pop());designNode(design,parts.join('.')).rules.splice(index,1);}}
  else if(action==='add-rule')n.rules.push(makeRule(root));else {const group=makeGroup();group.rules.push(makeRule(root));n.rules.push(group);}
  changed();render();
 });
 host.querySelectorAll('[data-rd-prop]').forEach(input=>input.oninput=()=>{const el=input.closest('[data-rd-path]'),n=designNode(design,el.dataset.rdPath),prop=input.dataset.rdProp;
  try{if(prop==='value')n.value=ruleValue(input.value,n.type,n.operator);else {n[prop]=input.value;if(prop==='field'){const f=catalog?.fields?.find(f=>f.field===input.value);if(f){n.type=f.type;n.operator=f.operators[0];n.value=['is_null','is_not_null','is_empty','is_not_empty'].includes(n.operator)?null:n.type==='boolean'?false:n.type==='string'?'':0;}changed();render();return;}if(['type','operator'].includes(prop))n.value=ruleValue(el.querySelector('[data-rd-prop="value"]').value,n.type,n.operator);}el.querySelectorAll('[data-rd-prop]').forEach(control=>control.setCustomValidity(''));host.querySelector('.rd-error').textContent='';}
  catch(e){n.value=el.querySelector('[data-rd-prop="value"]').value;input.setCustomValidity(e.message);host.querySelector('.rd-error').textContent=e.message;}
  host.querySelector('.rd-preview').textContent=JSON.stringify(filterPreview(design),null,2);changed();
 });
}
