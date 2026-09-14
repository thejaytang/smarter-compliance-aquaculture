// Human structural edits operate on copies and retain conversion evidence.
const copy=x=>JSON.parse(JSON.stringify(x));
const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export function changeHeadingLevel(blocks,id,direction){
 const result=copy(blocks),index=result.findIndex(b=>b.id===id),root=result[index];
 if(!root||root.type!=='heading')throw Error('Choose a heading.');
 const old=root.level||1,next=old+direction;if(next<1||next>6)throw Error('Heading levels range from 1 to 6.');
 let end=index+1;while(end<result.length&&!(result[end].type==='heading'&&(result[end].level||1)<=old))end++;
 const descendants=result.slice(index,end).filter(b=>b.type==='heading');
 if(descendants.some(b=>(b.level||1)+direction>6))throw Error('A child heading would exceed level 6.');
 const parent=result.slice(0,index).reverse().find(b=>b.type==='heading'&&(b.level||1)<next);
 if(next>1&&!parent)throw Error('Create or select a preceding parent heading first.');
 root.parent_id=parent?.id||null;for(const b of descendants)b.level=(b.level||1)+direction;
 return result;
}
export function reconstructTable(blocks,ids,rows,actor){
 if(!Array.isArray(rows)||!rows.length||!rows[0].length||rows.length*rows[0].length>100000||rows.some(r=>r.length!==rows[0].length))throw Error('Enter a rectangular table with at most 100,000 cells.');
 const selected=blocks.filter(b=>ids.includes(b.id));if(!selected.length||selected.some(b=>!['text','table'].includes(b.type)))throw Error('Select text or table blocks.');
 const indices=selected.map(b=>blocks.indexOf(b));if(indices.at(-1)-indices[0]+1!==selected.length)throw Error('Select adjacent blocks so their order and associations remain clear.');
 const result=copy(blocks),first=copy(selected[0]),removed=new Set(selected.slice(1).map(b=>b.id));
 first.type='table';first.text='';first.table={rows:copy(rows),merges:[],notes:[]};
 first.source_refs=[...new Map(selected.flatMap(b=>b.source_refs||[]).map(r=>[JSON.stringify(r),r])).values()];
 first.dependencies=[...new Set(selected.flatMap(b=>b.dependencies||[]))].filter(id=>!ids.includes(id));
 first.human_transforms=[...(first.human_transforms||[]),{kind:'rebuild_table',actor,at:new Date().toISOString(),original_blocks:copy(selected.map(({human_transforms,...block})=>block))}];
 result.splice(indices[0],selected.length,first);
 for(const b of result){if(removed.has(b.parent_id))b.parent_id=first.parent_id||null;b.dependencies=[...new Set((b.dependencies||[]).map(id=>removed.has(id)?first.id:id))].filter(id=>id!==b.id);}
 return result;
}
export function tableAxis(table,axis,index,remove=false){
 const t=copy(table),row=axis==='row',size=row?t.rows.length:t.rows[0].length;
 if(!Number.isInteger(index)||index<0||index>(remove?size-1:size))throw Error('Choose an existing position.');
 if(remove&&size<=1)throw Error('A table must retain at least one row and column.');
 if(row)t.rows.splice(index,remove?1:0,...(remove?[]:[Array(t.rows[0].length).fill('')]));else t.rows.forEach(r=>r.splice(index,remove?1:0,...(remove?[]:[''])));
 const start=row?'row':'col',span=row?'rowspan':'colspan';
 for(const m of t.merges||[]){if(index<m[start]||(!remove&&index===m[start]))m[start]+=remove?-1:1;else if(index<m[start]+m[span])m[span]+=remove?-1:1;}
 t.merges=(t.merges||[]).filter(m=>m.rowspan>0&&m.colspan>0&&(m.rowspan>1||m.colspan>1));return t;
}
export function rebuildTableDialog(w){
 const eligible=w.draft.blocks.filter(b=>['text','table'].includes(b.type));
 w.dialog(`<h2>Rebuild a table</h2><p>Select adjacent blocks. Their original text and links stay in conversion history. Paste tab-separated cells or enter the dimensions.</p>${eligible.map(b=>`<label class="mw-check"><input type="checkbox" data-rebuild-id="${esc(b.id)}">${esc((b.text||b.type).slice(0,110))}</label>`).join('')}<label>Rows<input id="rebuild-rows" type="number" min="1" max="1000" value="2"></label><label>Columns<input id="rebuild-cols" type="number" min="1" max="100" value="2"></label><label>Tab-separated cells<textarea id="rebuild-text" rows="5"></textarea></label><button id="rebuild-preview">Preview</button><div id="rebuild-result"></div><button id="rebuild-apply" disabled>Use this table in my draft</button><p id="rebuild-error" role="status"></p>`,d=>{
  let next;const invalid=()=>{next=null;d.querySelector('#rebuild-apply').disabled=true;};d.oninput=invalid;
  d.querySelector('#rebuild-preview').onclick=()=>{try{const ids=[...d.querySelectorAll('[data-rebuild-id]:checked')].map(n=>n.dataset.rebuildId),raw=d.querySelector('#rebuild-text').value;let rows;
   if(raw.trim()){rows=raw.replace(/\r/g,'').replace(/\n$/,'').split('\n').map(r=>r.split('\t'));const width=Math.max(...rows.map(r=>r.length));rows=rows.map(r=>[...r,...Array(width-r.length).fill('')]);}
   else{const n=+d.querySelector('#rebuild-rows').value,m=+d.querySelector('#rebuild-cols').value;if(!Number.isInteger(n)||!Number.isInteger(m)||n<1||m<1||n*m>100000)throw Error('Enter valid dimensions.');rows=Array.from({length:n},()=>Array(m).fill(''));}
   next=reconstructTable(w.draft.blocks,ids,rows,w.state.actor.name);d.querySelector('#rebuild-result').innerHTML=`<p>${rows.length} rows × ${rows[0].length} columns</p><table>${rows.slice(0,20).map(r=>'<tr>'+r.slice(0,12).map(c=>'<td>'+esc(c)+'</td>').join('')+'</tr>').join('')}</table><p>Preview shows up to 20 rows and 12 columns. All cells will be retained.</p>`;d.querySelector('#rebuild-apply').disabled=false;d.querySelector('#rebuild-error').textContent='';
  }catch(e){invalid();d.querySelector('#rebuild-error').textContent=e.message;}};
  d.querySelector('#rebuild-apply').onclick=()=>{if(!next)return;w.draft.blocks=next;w.changed(true);d.close();w.renderContent();};
 });
}
