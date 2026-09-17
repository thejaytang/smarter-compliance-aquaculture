const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

export async function showOutline(ex){
 const doc=ex.doc(),token=ex.token,ticket=ex.queueTicket,root=ex.container;
 const valid=()=>ex.token===token&&ex.queueTicket===ticket&&ex.discovery==='outline'&&ex.docId===doc.id;
 const list=root.querySelector('#ex-list'),panel=root.querySelector('#ex-detail');
 list.innerHTML='<p role="status">Loading source outline…</p>';
 const params=new URLSearchParams({view:'outline',document_id:doc.id,offset:ex.outlineOffset||0});if(ex.outlineParent)params.set('parent_id',ex.outlineParent);
 const data=await ex.api('/api/system2/state?'+params);if(!valid())return;
 list.innerHTML=`<p>${esc(data.warning)}</p><button id="outline-root">Document outline</button>${data.trail.map((n,i)=>`<button data-outline-trail="${i}">${esc(n.title)}</button>`).join('')}<p>${data.total} children in this range</p>${data.items.map((n,i)=>`<div><button class="task" data-outline-node="${i}"><strong>${esc(n.title)}</strong><span>${esc(n.type)}${n.heading_level?' · level '+n.heading_level:''}</span><small>${n.origin==='human'?'Human structure correction':n.origin==='canonical'?'From saved parser structure':'Structure unassigned'}</small></button>${n.children&&!n.container?`<button data-outline-children="${i}">Browse ${n.children} child items</button>`:''}</div>`).join('')}<button id="outline-prev" ${!data.offset?'disabled':''}>Previous outline items</button><button id="outline-next" ${data.offset+50>=data.total?'disabled':''}>Next outline items</button>`;
 const open=id=>{ex.outlineParent=id;ex.outlineOffset=0;ex.queue();};
 list.querySelector('#outline-root').onclick=()=>open(null);
 list.querySelectorAll('[data-outline-trail]').forEach(b=>b.onclick=()=>open(data.trail[Number(b.dataset.outlineTrail)].id));
 list.querySelectorAll('[data-outline-node]').forEach(b=>b.onclick=()=>{const n=data.items[Number(b.dataset.outlineNode)];if(n.container)open(n.id);else ex.select(n);});
 list.querySelectorAll('[data-outline-children]').forEach(b=>b.onclick=()=>open(data.items[Number(b.dataset.outlineChildren)].id));
 list.querySelector('#outline-prev').onclick=()=>{ex.outlineOffset=Math.max(0,(ex.outlineOffset||0)-50);ex.queue();};list.querySelector('#outline-next').onclick=()=>{ex.outlineOffset=(ex.outlineOffset||0)+50;ex.queue();};
 ex.detailTicket={};panel.innerHTML='<h2>Inspect source hierarchy</h2><p>Select original content to compare its text and repair its type, heading level, parent or reading order. Parsed containers group existing Canonical evidence and do not invent chapter titles.</p>';
}

export async function showPages(ex){
 const doc=ex.doc(),token=ex.token,ticket=ex.queueTicket,root=ex.container;
 const valid=()=>ex.token===token&&ex.queueTicket===ticket&&ex.discovery==='pages'&&ex.docId===doc.id;
 const list=root.querySelector('#ex-list'),panel=root.querySelector('#ex-detail');
 const p=Math.max(0,Math.min(doc.total_pages-1,ex.pdfPage||0));ex.pdfPage=p;
 const pageOffset=Math.floor(p/50)*50;
 list.innerHTML='<p role="status">Loading original pages…</p>';
 const summary=await ex.api('/api/system2/state?'+new URLSearchParams({view:'pages',document_id:doc.id,offset:pageOffset}));
 if(!valid())return;
 list.innerHTML=`<p>Inspect any original page, including pages without reported issues.</p><label>PDF page<input id="pdf-page-number" type="number" min="1" max="${summary.total}" value="${p+1}"></label><button id="pdf-go">Open page</button><div><button id="pdf-prev" ${p===0?'disabled':''}>Previous page</button><button id="pdf-next" ${p+1>=summary.total?'disabled':''}>Next page</button></div>${summary.items.map(r=>`<button class="task" data-pdf-page="${r.page_index}"><strong>PDF page ${r.page_index+1}</strong><span>${r.processed?'Processed':'Not processed'} · ${r.mapped_units} mapped units</span><small>${r.accepted_content} content checks accepted</small></button>`).join('')}`;
 const go=n=>{if(!Number.isInteger(n)||n<0||n>=summary.total)return;ex.pdfPage=n;ex.queue();};
 list.querySelector('#pdf-go').onclick=()=>go(Number(list.querySelector('#pdf-page-number').value)-1);
 list.querySelector('#pdf-prev').onclick=()=>go(p-1);list.querySelector('#pdf-next').onclick=()=>go(p+1);
 list.querySelectorAll('[data-pdf-page]').forEach(b=>b.onclick=()=>go(Number(b.dataset.pdfPage)));
 let offset=0;
 const render=async()=>{
  const detailTicket=ex.detailTicket={};
  const current=()=>valid()&&ex.detailTicket===detailTicket;
  panel.innerHTML='<p role="status">Loading page mappings…</p>';
  const data=await ex.api('/api/system2/state?'+new URLSearchParams({view:'page',document_id:doc.id,page_index:p,offset}));
  if(!current())return;
  panel.innerHTML=`<h2>Inspect PDF page ${p+1}</h2><p>${esc(data.warning)}</p>${!data.processed?'<p role="alert">This page has not been processed. No absence of findings can establish completeness.</p>':''}<a href="/api/original/${encodeURIComponent(doc.source.source_id)}?expected_hash=${doc.source.content_hash}">Open full original</a><div id="pdf-page-original"><p role="status">Rendering the bound original page…</p></div><p>Highlights show the ${data.items.length} units listed below; they do not show all possible omissions. A table and its rows can share a region.</p><div id="pdf-page-units">${data.items.map((u,i)=>`<button class="task" data-page-unit="${i}"><strong>${i+1}. ${esc(u.title)}</strong><span>${u.content_ok?'Content accepted':'Content needs review'}${u.waiting?' · Waiting for related content':''}</span></button>`).join('')||'<p>No mapped content on this page. Inspect the original for missing text, tables or images.</p>'}</div><p>${data.total?offset+1:0}–${Math.min(offset+50,data.total)} / ${data.total} mapped units</p><button id="pdf-units-prev" ${!offset?'disabled':''}>Previous mapped units</button><button id="pdf-units-next" ${offset+50>=data.total?'disabled':''}>Next mapped units</button>${data.coverage?'<button id="pdf-completeness">Review this page’s completeness / add missing content</button>':'<p>Page completeness task is not available yet. Original problems can be reported to Source Management System above.</p>'}`;
  panel.querySelectorAll('[data-page-unit]').forEach(b=>b.onclick=()=>ex.select(data.items[Number(b.dataset.pageUnit)]));
  panel.querySelector('#pdf-units-prev').onclick=()=>{offset-=50;render().catch(error);};panel.querySelector('#pdf-units-next').onclick=()=>{offset+=50;render().catch(error);};
  if(data.coverage)panel.querySelector('#pdf-completeness').onclick=()=>ex.select(data.coverage);
  const check=document.createElement('button'),status=document.createElement('p');
  check.textContent='Check this original page';check.id='pdf-verify-original';status.setAttribute('role','status');
  panel.querySelector('h2').after(check,status);
  if(data.source_verification)status.textContent=`Saved check: ${data.source_verification.findings.length} findings. ${data.source_verification.stale?'Content changed; recheck required.':'Open page completeness to inspect findings and unverified scope.'}`;
  check.onclick=async()=>{
   check.disabled=true;status.textContent='Checking this original page locally. Other review work can continue.';
   // Retain the UUID after an uncertain response, so a retry cannot duplicate a run.
   const key=doc.id+':'+p+':'+data.revision;
   ex.pageCheckRequests??=new Map();
   if(!ex.pageCheckRequests.has(key))ex.pageCheckRequests.set(key,crypto.randomUUID());
   try{
    const receipt=await ex.api('/api/system2/verify-page',{request_id:ex.pageCheckRequests.get(key),document_id:doc.id,revision:data.revision,source_sha256:doc.source.content_hash,page_index:p});
    if(!current())return;
    ex.pageCheckRequests.delete(key);doc.revision=receipt.revision;
    await ex.select({id:receipt.unit_id});
   }catch(e){if(current()){status.textContent='Page check was not confirmed saved: '+e.message;check.disabled=false;}}
  };
  ex.api('/api/system2/preview?'+new URLSearchParams({document_id:doc.id,page_index:p,full:true})).then(image=>{
   if(!current())return;
   const region=panel.querySelector('#pdf-page-original');
   region.innerHTML=`<img src="${esc(image.image)}" alt="Bound original PDF page ${p+1}"><svg aria-label="Mapped source regions" viewBox="0 0 ${image.width} ${image.height}"></svg>`;
   const svg=region.querySelector('svg');
   data.items.forEach((u,i)=>(u.regions||[]).forEach(r=>{
    let b=Array.isArray(r.bbox)?r.bbox:[r.bbox.x0,r.bbox.y0,r.bbox.x1,r.bbox.y1];
    if(b.some(v=>!Number.isFinite(v)))return;
    if(Math.max(b[2],b[3])<=1)b=[b[0]*image.width,b[1]*image.height,b[2]*image.width,b[3]*image.height];
    if(r.coord_origin==='bottom_left')b=[b[0],image.height-b[3],b[2],image.height-b[1]];
    const rect=document.createElementNS('http://www.w3.org/2000/svg','rect');
    Object.entries({x:b[0],y:b[1],width:Math.max(0,b[2]-b[0]),height:Math.max(0,b[3]-b[1]),fill:'#3478da18',stroke:'#3478da','stroke-width':1,tabindex:0,role:'button','aria-label':`Open mapped unit ${i+1}: ${u.title}`}).forEach(([k,v])=>rect.setAttribute(k,v));
    rect.onclick=()=>ex.select(u);rect.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();ex.select(u);}};svg.append(rect);
   }));
  }).catch(e=>{if(current())panel.querySelector('#pdf-page-original').textContent='Original image unavailable: '+e.message;});
 };
 const error=e=>{if(valid())panel.textContent=e.message;};
 await render();
}
