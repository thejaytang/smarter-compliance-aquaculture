// Read-only evidence UI. Source identity and version are resolved by the server.
const evidenceCache=new Map();
export async function showEvidence(container, sourceId, api, {page = 1, sheet = '', row = 1, column = 1, locator='', references=[], full=false, documentId='', unitId='', interactivePDF=false} = {}) {
  const request = Symbol('evidence');
  container.evidenceRequest = request;
  container.replaceChildren();
  const status = document.createElement('p');
  status.className = 'muted';
  status.textContent = 'Opening the registered local original…';
  container.append(status);
  try {
    const cell=locator.match(/(?:^|['"]?)([^!]+)['"]?!([$]?[A-Z]+)([$]?\d+)/);
    if(cell){sheet=cell[1].replace(/^['"]|['"]$/g,'');row=Number(cell[3].replace('$',''));column=[...cell[2].replace('$','')].reduce((n,c)=>n*26+c.charCodeAt(0)-64,0);}
    const query=new URLSearchParams({sheet,row,column});
    const cacheKey=documentId&&unitId?JSON.stringify([documentId,unitId,references,full]):null;
    let result=cacheKey?evidenceCache.get(cacheKey):null;
    if(result){ /* The cached image/markup belongs to this exact immutable source range. */ }
    else if(documentId && unitId && !full){
      result=await api('/api/system2/preview?'+new URLSearchParams({document_id:documentId,unit_id:unitId,full}));
    }else{
      result=await api('/api/preview/' + encodeURIComponent(sourceId)+'?'+query);
      if(documentId && unitId && result.kind==='text')result=await api('/api/system2/preview?'+new URLSearchParams({document_id:documentId,unit_id:unitId,full}));
      if(documentId && unitId && result.kind==='spreadsheet')result=await api('/api/system2/preview?'+new URLSearchParams({document_id:documentId,unit_id:unitId,full}));
    }
    if (!container.isConnected || container.evidenceRequest !== request) return;
    if(cacheKey){evidenceCache.set(cacheKey,result);while(evidenceCache.size>8)evidenceCache.delete(evidenceCache.keys().next().value);}
    status.textContent = result.label||result.message;
    if(result.warnings?.length){const details=document.createElement('details'),summary=document.createElement('summary'),p=document.createElement('p');summary.textContent='Original preview limitations';p.textContent=result.warnings.join(' ');details.append(summary,p);container.append(details);}
    if(result.image){
      const img=document.createElement('img');img.src=result.image;img.alt=result.image_label||result.label;img.style.width='100%';
      const enlarge=document.createElement('button');enlarge.type='button';enlarge.textContent='Enlarge original region';
      const dialog=document.createElement('dialog');dialog.className='original-evidence-dialog';dialog.setAttribute('aria-label','Enlarged original region');
      const close=document.createElement('button');close.type='button';close.textContent='Close enlarged original';close.onclick=()=>dialog.close();
      const caption=document.createElement('p');caption.textContent=result.label+(result.warnings?.length?' '+result.warnings.join(' '):'');
      const fullImage=img.cloneNode();fullImage.style.width='100%';dialog.append(close,caption,fullImage);
      enlarge.onclick=()=>dialog.showModal();container.append(enlarge,img,dialog);
    }
    if(result.kind==='html_region'){
      const frame=document.createElement('iframe');frame.setAttribute('sandbox','');frame.setAttribute('referrerpolicy','no-referrer');frame.title='Isolated bound original region';frame.srcdoc=result.html;container.append(frame);return result;
    }
    if(result.kind==='image_region')return result;
    if (result.kind === 'pdf') {
      const url = new URL(result.url, location.origin);
      if (url.origin !== location.origin || !url.pathname.startsWith('/api/pdf/')) throw Error('The original document address is invalid.');
      url.hash = 'page=' + Math.max(1, Math.floor(page));
      const controls = document.createElement('div');
      controls.className = 'row evidence-controls';
      const label = document.createElement('span');
      label.textContent = result.filename;
      const open = document.createElement('a');
      open.href = url.href; open.target = '_blank'; open.rel = 'noopener noreferrer';
      open.textContent = 'Open in new window ↗';
      const close = document.createElement('button');
      close.type = 'button'; close.textContent = 'Close original';
      close.onclick = () => { container.evidenceRequest = null; container.replaceChildren(); };
      controls.append(label, open, close);
      const frame = document.createElement('iframe');
      frame.className = 'pdf-reader'; frame.src = interactivePDF?'/pdf-reader.html?'+new URLSearchParams({source:url.pathname+url.search,page:Math.max(1,Math.floor(page))}):url.href;
      if(interactivePDF){status.hidden=true;controls.hidden=true;}
      frame.title = 'Full local PDF with page, zoom and search controls';
      container.append(controls, frame);
    } else if(result.kind==='spreadsheet') {
      const controls=document.createElement('div');controls.className='row';
      const select=document.createElement('select');select.setAttribute('aria-label','Original worksheet');
      for(const name of result.sheets){const option=document.createElement('option');option.value=name;option.textContent=name;option.selected=name===result.sheet;select.append(option);}
      select.onchange=()=>showEvidence(container,sourceId,api,{sheet:select.value});controls.append(select);
      for(const [name,r,c] of [['Previous rows',Math.max(1,result.row-40),result.column],['Next rows',result.row+40,result.column],['Previous columns',result.row,Math.max(1,result.column-12)],['Next columns',result.row,result.column+12]]) {
        const button=document.createElement('button');button.textContent=name;button.disabled=r>result.rows||c>result.columns;
        button.onclick=()=>showEvidence(container,sourceId,api,{sheet:result.sheet,row:r,column:c});controls.append(button);
      }
      const meta=document.createElement('p');meta.textContent=`${result.sheet} (${result.state}) · ${result.rows} rows × ${result.columns} columns · Merged: ${result.merged.join(', ')||'None'}`;
      const wrap=document.createElement('div');wrap.style.overflow='auto';const table=document.createElement('table');
      for(const cells of result.cells){const tr=document.createElement('tr');for(const cell of cells){const td=document.createElement('td');
        td.textContent=`${cell.address}${cell.hidden_row||cell.hidden_column?' [hidden]':''}\n${cell.value??''}${String(cell.value).startsWith('=')?'\nSaved cache: '+(cell.cached??'unavailable'):''}`;td.style.whiteSpace='pre-wrap';tr.append(td);}table.append(tr);}
      wrap.append(table);container.append(controls,meta,wrap);
    } else if (result.text) {
      const text = document.createElement('div');
      text.className = 'preview'; text.textContent = result.text;
      container.append(text);
    }
    return result;
  } catch (error) {
    if (container.isConnected && container.evidenceRequest === request) {
      status.textContent = error.message;
      status.setAttribute('role', 'alert');
    }
  }
}
