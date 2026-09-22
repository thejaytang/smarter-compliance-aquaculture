import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {Materials} from '../frontend/components/materials.js';

function fixture(){
 const x=new Materials(),nodes=new Map(),image={src:'old-image',style:{width:'100%'},naturalWidth:675,getBoundingClientRect:()=>({width:f.cssWidth})},host={scrollTop:143,scrollLeft:31},f={x,cssWidth:600,calls:[],image,host};
 x.q=s=>s==='.mw-pdf-page-image'?image:s==='.mw-pdf-image-scroll'?host:nodes.get(s)||nodes.set(s,{innerHTML:'',textContent:'',hidden:true,attributes:{},setAttribute(k,v){this.attributes[k]=v;},focus(){this.focused=true;},insertAdjacentHTML(where,html){this.innerHTML+=html;},style:{},classList:{toggle(){},remove(){}}}).get(s);
 x.root={querySelectorAll:()=>[]};x.material={id:'material-1',source:{content_hash:'source-hash'},collaboration:{view:'personal'}};x.id='material-1';x.token={};x.readerTicket={};x.pdfDisplaySession={};x.reader={kind:'pdf',page:2,pages:5,width:600,height:800,source_sha256:'source-hash',image:'old-image',image_width:675,image_height:900};
 f.result=(width,overrides={})=>({...x.reader,image:'new-image',image_width:width,image_height:Math.round(width*4/3),render_width_requested:width,render_limited:false,...overrides});
 x.openingRequest=async url=>{f.calls.push(url);return f.result(Number(new URL(url,'http://local').searchParams.get('render_width')));};
 x.decodePdfImage=async()=>({width:f.decodedWidth||Number(new URL(f.calls.at(-1),'http://local').searchParams.get('render_width')),height:f.decodedHeight||Math.round(Number(new URL(f.calls.at(-1),'http://local').searchParams.get('render_width'))*4/3)});
 return f;
}

async function withDpr(value,fn){const descriptor=Object.getOwnPropertyDescriptor(globalThis,'devicePixelRatio');Object.defineProperty(globalThis,'devicePixelRatio',{configurable:true,value});try{return await fn();}finally{if(descriptor)Object.defineProperty(globalThis,'devicePixelRatio',descriptor);else delete globalThis.devicePixelRatio;}}
async function withClock(fn){const set=globalThis.setTimeout,clear=globalThis.clearTimeout,queue=new Map();let serial=0;globalThis.setTimeout=(callback)=>{const id=++serial;queue.set(id,callback);return id;};globalThis.clearTimeout=id=>queue.delete(id);try{return await fn({queue,run:async()=>{const tasks=[...queue.values()];queue.clear();for(const task of tasks)await task();}});}finally{globalThis.setTimeout=set;globalThis.clearTimeout=clear;}}

test('physical render requests follow displayed width and DPR with bounded 64-pixel steps',async()=>withDpr(2,async()=>{
 const f=fixture();f.cssWidth=1200;assert.equal(f.x.pdfDesiredWidth(),2432);f.cssWidth=50000;assert.equal(f.x.pdfDesiredWidth(),32768);f.cssWidth=0;assert.equal(f.x.pdfDesiredWidth(),0);
}));

test('detail update preserves displayed page and latest user scroll while pending and sends only a reader request',async()=>withDpr(2,async()=>{
 const f=fixture();let finish;f.x.openingRequest=url=>{f.calls.push(url);return new Promise(resolve=>finish=resolve);};const oldReader=f.x.reader,pending=f.x.refreshPdfResolution();
 assert.equal(f.image.src,'old-image');assert.equal(f.x.reader,oldReader);assert.match(f.x.q('#mw-pdf-render-status').textContent,/Current page remains available/);assert.equal(f.calls.length,1);const url=new URL(f.calls[0],'http://local');assert.equal(url.pathname,'/api/material/reader');assert.deepEqual(Object.fromEntries(url.searchParams),{id:'material-1',view:'personal',page:'2',render_width:'1216'});
 f.host.scrollTop=271;f.host.scrollLeft=49;finish(f.result(1216));await pending;assert.equal(f.image.src,'new-image');assert.equal(f.host.scrollTop,271);assert.equal(f.host.scrollLeft,49);assert.equal(f.x.reader.page,2);assert.equal(f.x.reader.source_sha256,'source-hash');assert.equal(f.x.reader.image_width,1216);
 await f.x.refreshPdfResolution();assert.equal(f.calls.length,1);
}));

test('late responses after material, page, view, reader ticket or source changes cannot replace the displayed image',async()=>withDpr(2,async()=>{
 for(const change of [f=>f.x.id='other',f=>f.x.reader.page=3,f=>f.x.material.collaboration.view='archive',f=>f.x.readerTicket={},f=>f.x.reader.source_sha256='other-source',f=>f.x.token={}]){
  const f=fixture();let finish;f.x.openingRequest=url=>{f.calls.push(url);return new Promise(resolve=>finish=resolve);};const response=f.result(1216),pending=f.x.refreshPdfResolution();change(f);finish(response);await pending;assert.equal(f.image.src,'old-image');
 }
}));

test('source mismatch, failed fetch and failed image decode retain the old image with actionable retry',async()=>withDpr(2,async()=>{
 for(const mode of ['source','fetch','decode','dimensions']){
  const f=fixture();if(mode==='source')f.x.openingRequest=async()=>f.result(1216,{source_sha256:'different'});if(mode==='fetch')f.x.openingRequest=async()=>{throw Error('unavailable');};if(mode==='decode')f.x.decodePdfImage=async()=>{throw Error('bad image');};if(mode==='dimensions'){f.decodedWidth=17;f.decodedHeight=19;}
  await f.x.refreshPdfResolution();assert.equal(f.image.src,'old-image');assert.equal(f.x.q('[data-action="reader-pdf-retry"]').hidden,false);assert.match(f.x.q('#mw-pdf-render-status').textContent,/Current page retained; Retry or use Open original/);assert.equal(f.x.pdfResolutionUnavailable,true);
 }
}));

test('an old backend that ignores render_width is detected once and cannot trigger an automatic refresh storm',async()=>withDpr(2,async()=>withClock(async clock=>{
 const f=fixture();f.x.openingRequest=async url=>{f.calls.push(url);const response=f.result(675);delete response.image_width;delete response.image_height;delete response.render_width_requested;return response;};await f.x.refreshPdfResolution();assert.equal(f.image.src,'old-image');assert.match(f.x.q('#mw-pdf-render-status').textContent,/unavailable in this session/);
 f.cssWidth=1200;f.x.schedulePdfResolution();await clock.run();await f.x.refreshPdfResolution();assert.equal(f.calls.length,1);assert.equal(clock.queue.size,0);
}))); 

test('reported physical limit is retained honestly and repeated requests at that target stop',async()=>withDpr(2,async()=>{
 const f=fixture();f.cssWidth=2400;f.decodedWidth=3000;f.decodedHeight=4000;f.x.openingRequest=async url=>{f.calls.push(url);return f.result(4800,{image_width:3000,image_height:4000,render_limited:true});};await f.x.refreshPdfResolution();assert.equal(f.image.src,'new-image');assert.equal(f.x.reader.image_width,3000);assert.match(f.x.q('#mw-pdf-render-status').textContent,/Available page detail reached/);await f.x.refreshPdfResolution();assert.equal(f.calls.length,1);
}));

test('resize bursts debounce and at most one resolution request runs for the current page',async()=>withDpr(2,async()=>withClock(async clock=>{
 const f=fixture();let finish;f.x.openingRequest=url=>{f.calls.push(url);return new Promise(resolve=>finish=resolve);};f.x.schedulePdfResolution();f.cssWidth=700;f.x.schedulePdfResolution();f.cssWidth=800;f.x.schedulePdfResolution();assert.equal(clock.queue.size,1);
 const first=clock.run();assert.equal(f.calls.length,1);f.cssWidth=1000;await f.x.refreshPdfResolution();assert.equal(f.calls.length,1);finish(f.result(1600));await first;assert.equal(clock.queue.size,1);
 const next=clock.run();assert.equal(f.calls.length,2);finish(f.result(2048));await next;assert.equal(f.x.reader.image_width,2048);assert.equal(clock.queue.size,0);
}))); 

test('observer and DPR listeners request refresh and disconnect with the reader session',async()=>withDpr(2,async()=>withClock(async clock=>{
 const saved={ResizeObserver:globalThis.ResizeObserver,window:globalThis.window,matchMedia:globalThis.matchMedia},listeners=new Map(),queries=[];let observer;
 globalThis.ResizeObserver=class{constructor(callback){this.callback=callback;observer=this;}observe(host){this.host=host;}disconnect(){this.disconnected=true;}};globalThis.window={addEventListener:(name,callback)=>listeners.set(name,callback),removeEventListener:(name,callback)=>{if(listeners.get(name)===callback)listeners.delete(name);}};globalThis.matchMedia=query=>{const media={query,addEventListener(name,fn){this.callback=fn;},removeEventListener(){this.removed=true;}};queries.push(media);return media;};
 try{const f=fixture();f.x.watchPdfDisplay();assert.equal(observer.host,f.host);observer.callback();listeners.get('resize')();queries[0].callback();assert.equal(queries[0].removed,true);assert.equal(queries.length,2);assert.equal(clock.queue.size,1);await clock.run();assert.equal(f.calls.length,1);f.x.stopPdfDisplay();assert.equal(observer.disconnected,true);assert.equal(listeners.size,0);assert.equal(queries[1].removed,true);assert.equal(clock.queue.size,0);}finally{for(const [key,value] of Object.entries(saved))if(value===undefined)delete globalThis[key];else globalThis[key]=value;}
}))); 

test('reading details remain available outside the PDF viewport and HTML names its reflowed rendering',()=>{
 const f=fixture(),page=f.x.pdfMarkup({...f.x.reader,native_text:'<Original>'}),info=f.x.pdfInfoMarkup({...f.x.reader,native_text:'<Original>'});assert.match(page,/mw-pdf-image-scroll/);assert.doesNotMatch(page,/<details|<pre|mw-reader-notice/);assert.match(info,/&lt;Original&gt;/);assert.match(info,/separate from the page image|Optional browser PDF viewer/);
 f.x.reader={kind:'html'};f.x.renderReader({kind:'html',anchors:[],navigation_anchors:[]});assert.match(f.x.q('#mw-reader').innerHTML,/Simplified HTML · original website formatting is not preserved/);assert.match(f.x.q('#mw-reader').innerHTML,/sandbox=""/);assert.doesNotMatch(f.x.q('#mw-reader').innerHTML,/mw-reader-notice/);assert.doesNotMatch(f.x.q('#mw-original-toolbar').innerHTML,/<button|<summary/);assert.equal(typeof f.x.q('#mw-html-anchor').onchange,'function');
});

test('document CSS gives remaining space to one evidence viewport and keeps compact original controls',async()=>{
 const css=await readFile(new URL('../frontend/assets/materials.css',import.meta.url),'utf8');assert.match(css,/#mw-reader\.mw-reader-document\{[^}]*display:flex;[^}]*overflow:hidden;[^}]*min-height:0/);assert.match(css,/\.mw-reader-document>\.mw-html,\.mw-reader-document>\.mw-pdf-image-scroll\{[^}]*flex:1 1 0;min-height:0;height:auto/);assert.match(css,/\.mw-original>header\{min-height:54px;margin:0;/);assert.match(css,/\.mw-reader-toolbar\.mw-document-toolbar \.mw-reader-secondary button\{min-height:26px;padding:2px 4px/);assert.match(css,/\.mw-reader-secondary\{margin-top:4px;gap:6px/);assert.match(css,/\.mw-document-toolbar \.mw-pdf-page-control input\{width:48px/);
});

test('explicit Retry recovers an image-detail failure without clearing the current page',async()=>withDpr(2,async()=>{
 const f=fixture();f.x.openingRequest=async()=>{throw Error('offline');};await f.x.refreshPdfResolution();assert.equal(f.x.pdfResolutionUnavailable,true);assert.equal(f.image.src,'old-image');
 f.x.openingRequest=async url=>{f.calls.push(url);return f.result(1216);};await f.x.readerAction('reader-pdf-retry');assert.equal(f.image.src,'new-image');assert.equal(f.x.pdfResolutionUnavailable,false);assert.equal(f.x.q('[data-action="reader-pdf-retry"]').hidden,true);assert.equal(f.host.scrollTop,143);
}));

test('known malformed PDF open failure gives recovery guidance and preserves the prior draft without masking unknown errors',async()=>{
 const f=fixture(),draft={blocks:[{text:'Retained manual correction'}]};f.x.draft=draft;f.x.dirty=false;f.x.updateBar=()=>{};f.x.message=text=>f.message=text;f.x.openingRequest=async()=>{throw Error('Failed to load document (PDFium: Data format error).');};
 await f.x.open('broken');assert.equal(f.x.draft,draft);assert.equal(f.x.id,'material-1');assert.equal(f.x.opening,false);assert.match(f.message,/saved PDF could not be read/);assert.match(f.message,/current work is retained/);assert.doesNotMatch(f.message,/PDFium/);
 f.x.openingRequest=async()=>{throw Error('Different diagnostic retained');};await f.x.open('unknown');assert.equal(f.message,'Different diagnostic retained');
});

test('interactive PDF page messages cannot change source, view or page through another frame',()=>{
 const saved={window:globalThis.window,location:globalThis.location},listeners=new Map();
 globalThis.window={addEventListener:(kind,fn)=>listeners.set(kind,fn),removeEventListener:(kind,fn)=>{if(listeners.get(kind)===fn)listeners.delete(kind);}};globalThis.location={origin:'http://local'};
 try{
  const f=fixture(),frame=f.x.q('.mw-interactive-pdf');frame.contentWindow={};f.x.reader.interactive_pdf_reader='pdfjs-6.3.289';
  f.x.renderReader(f.x.reader);assert.match(f.x.q('#mw-reader').innerHTML,/Original PDF reader/);assert.equal(f.calls.length,0);
  const accept=listeners.get('message'),valid={origin:'http://local',source:frame.contentWindow,data:{type:'saved-pdf-page',id:f.x.id,view:'personal',page:3,zoom:'1.5',rotation:90}};
  for(const change of [{origin:'https://foreign.example'},{source:{}},{data:{...valid.data,id:'other'}},{data:{...valid.data,view:'master'}},{data:{...valid.data,page:6}},{data:{...valid.data,page:2.5}},{data:{...valid.data,zoom:'javascript:bad'}},{data:{...valid.data,rotation:'90'}},{data:{...valid.data,rotation:45}}]){accept({...valid,...change});assert.equal(f.x.reader.page,2);}
  accept(valid);assert.equal(f.x.reader.page,3);assert.match(f.x.q('.mw-open-pdf-reader').href,/page=3&zoom=1.5&rotation=90/);assert.equal(f.x.material.source.content_hash,'source-hash');
  f.x.stopPdfDisplay();assert.equal(listeners.size,0);
 }finally{for(const [key,value] of Object.entries(saved))if(value===undefined)delete globalThis[key];else globalThis[key]=value;}
});

test('switching reader modes explicitly reloads only the currently selected page',async()=>{
 const f=fixture(),draft={blocks:[{text:'Keep this work'}]};f.x.draft=draft;const pages=[];f.x.loadReader=async options=>pages.push(options);
 await f.x.readerAction('reader-pdf-mode');assert.equal(f.x.pdfImageFallback,true);
 await f.x.readerAction('reader-pdf-mode');assert.equal(f.x.pdfImageFallback,false);
 assert.deepEqual(pages,[{page:2},{page:2}]);assert.equal(f.x.draft,draft);assert.equal(f.calls.length,0);
});

test('horizontal worksheet navigation preserves its row, source and sheet',async()=>{
 const f=fixture(),reads=[];f.x.reader={kind:'spreadsheet',sheet:'Æ test',row:121,column:25,row_count:80,column_count:24,rows:200,columns:60};f.x.loadReader=async args=>reads.push(args);
 await f.x.readerAction('reader-left');await f.x.readerAction('reader-right');assert.deepEqual(reads,[{sheet:'Æ test',row:121,column:1},{sheet:'Æ test',row:121,column:49}]);assert.equal(f.x.material.source.content_hash,'source-hash');
});
test('explicit material page and cell jumps reject invalid values without a read',async()=>{
 const f=fixture(),reads=[];f.x.loadReader=async args=>reads.push(args);
 for(const value of ['', '0', '-1', '2.5', '6']){f.x.q('#mw-page').value=value;await f.x.readerAction('reader-page');assert.equal(reads.length,0);assert.equal(f.x.reader.page,2);assert.equal(f.x.q('#mw-page').focused,true);assert.match(f.x.q('#mw-reader-location-error').textContent,/1 to 5/);}
 for(const value of ['1','5']){f.x.q('#mw-page').value=value;await f.x.readerAction('reader-page');}assert.deepEqual(reads,[{page:1},{page:5}]);reads.length=0;
 f.x.reader={kind:'spreadsheet',row:121,column:25,rows:200,columns:60};f.x.q('#mw-sheet').value='Sheet Æ';
 for(const key of ['row','column'])for(const value of ['', '0', '-1', '2.5', '201']){f.x.q('#mw-row').value='121';f.x.q('#mw-column').value='25';f.x.q('#mw-'+key).value=value;await f.x.readerAction('reader-cells');assert.equal(reads.length,0);assert.equal(f.x.q('#mw-'+key).focused,true);assert.equal(f.x.reader.row,121);}
 for(const [row,column] of [[1,1],[200,60]]){f.x.q('#mw-row').value=String(row);f.x.q('#mw-column').value=String(column);await f.x.readerAction('reader-cells');}
 assert.deepEqual(reads,[{sheet:'Sheet Æ',row:1,column:1},{sheet:'Sheet Æ',row:200,column:60}]);assert.equal(f.x.q('#mw-reader-location-error').hidden,true);
});

function sheetFixture(){
 const x=new Materials(),nodes=new Map(),root={querySelectorAll:()=>[]},node=()=>({innerHTML:'',scrollTop:170,scrollLeft:20,disabled:false,hidden:false,classList:{toggle(){},remove(){}},insertAdjacentHTML(_,html){this.innerHTML+=html;},remove(){this.removed=true;}});
 x.q=s=>s==='#mw-document-information'?null:nodes.get(s)||null;for(const s of ['#mw-reader','#mw-original-toolbar','#mw-sheet-window','#mw-next-rows','#mw-reader-location-error'])nodes.set(s,node());
 x.root=root;x.id='sheet-material';x.token={};x.material={source:{content_hash:'sheet-hash'},collaboration:{view:'personal'}};x.reader={kind:'spreadsheet',sheet:'Water',row:1,column:1,row_count:80,column_count:4,rows:160,columns:4,cells:[],source_sha256:'sheet-hash'};x.readerTicket={};x.captureDisclosures=()=>{};const rendered=[];x.renderReader=(reader,append)=>{rendered.push({reader,append});if(append)nodes.get('#mw-reader').innerHTML+=' rows '+reader.row;else nodes.get('#mw-reader').innerHTML='rows '+reader.row;};nodes.get('#mw-reader').innerHTML='rows 1–80';return {x,nodes,rendered};
}
test('worksheet append failure retains rows scroll selection and exact append retry without duplicate reads',async()=>{
 const {x,nodes,rendered}=sheetFixture();x.selectedCell='C23';const original=x.reader;let finish,calls=0;x.openingRequest=()=>{calls++;return new Promise((_,reject)=>finish=reject);};const pending=x.readerAction('reader-next-rows');await x.readerAction('reader-next-rows');assert.equal(calls,1);nodes.get('#mw-sheet-window').scrollTop=250;finish(Error('Offline'));await pending;
 assert.equal(nodes.get('#mw-reader').innerHTML,'rows 1–80');assert.equal(nodes.get('#mw-sheet-window').scrollTop,250);assert.equal(nodes.get('#mw-sheet-window').scrollLeft,20);assert.equal(x.selectedCell,'C23');assert.equal(x.reader,original);assert.match(nodes.get('#mw-sheet-window').innerHTML,/Already-read rows remain/);assert.equal(x.readerRetry.append,true);
 x.openingRequest=async url=>{calls++;assert.equal(new URL(url,'http://local').searchParams.get('row'),'81');return {...original,row:81};};await x.readerAction('reader-retry');assert.equal(calls,2);assert.equal(rendered.length,1);assert.equal(rendered[0].append,true);assert.equal(x.reader.row,81);assert.equal(x.selectedCell,'C23');assert.equal(x.readerRetry,null);
});
test('late or mismatched worksheet continuation cannot append into another bound window',async()=>{
 for(const change of [x=>x.id='other',x=>x.token={},x=>x.material.collaboration.view='archive',x=>x.readerTicket={}]){
  const {x,rendered}=sheetFixture(),reader=x.reader;let finish;x.openingRequest=()=>new Promise(r=>finish=r);const pending=x.readerAction('reader-next-rows');change(x);finish({...reader,row:81});await pending;assert.equal(rendered.length,0);
 }
 for(const fields of [{sheet:'Other'},{column:2},{source_sha256:'changed'},{row:1},{column_count:2}]){
  const {x,rendered}=sheetFixture(),reader=x.reader;x.openingRequest=async()=>({...reader,row:81,...fields});await x.readerAction('reader-next-rows');assert.equal(rendered.length,0);assert.equal(x.reader,reader);assert.equal(x.readerRetry.append,true);x.reader={...reader,sheet:'Other'};let called=false;x.openingRequest=async()=>called=true;await x.readerAction('reader-retry');assert.equal(called,false);
 }
});
test('selected original cell remains an exact linked scope after continuation and clears when no longer visible',()=>{
 const {x}=sheetFixture(),classes=new Map(),cells=['C23','C81'].map(id=>({dataset:{originalCell:id},classList:{toggle(_,value){classes.set(id,value);}}}));x.root.querySelectorAll=()=>cells;x.selectedCell='C23';x.syncSelectedCells();assert.equal(classes.get('C23'),true);assert.equal(classes.get('C81'),false);x.draft={blocks:[{text:'Selected cell only',source_refs:[{sheet:'Water',cell_range:'C23'}]},{text:'Other cell',source_refs:[{sheet:'Water',cell_range:'C81'}]}]};let html;x.dialog=value=>html=value;x.reader={...x.reader,row:81};x.showLinkedBlocks();assert.match(html,/Selected cell only/);assert.doesNotMatch(html,/Other cell/);
 x.reader={...x.reader,sheet:'Other'};x.root.querySelectorAll=()=>[];x.syncSelectedCells();assert.equal(x.selectedCell,null);
});
test('absolute A1 range parser rejects partial or reversed references and exact matching retains saved wording',async()=>{
 const {cellRange,refsForLocation}=await import('../frontend/components/material-navigation.js');for(const [raw,range]of [['C121',{x0:3,y0:121,x1:3,y1:121}],['$C$121:$D122',{x0:3,y0:121,x1:4,y1:122}],['AA$2:$AB3',{x0:27,y0:2,x1:28,y1:3}]])assert.deepEqual(cellRange(raw),range);
 for(const raw of ['A0','C3:A1','A3:A2','A1 trailing','$A$$1','A1:B2:Z9','1A','A01','A999999999999999999999'])assert.equal(cellRange(raw),null,raw);
 const refs=[{source_refs:[{sheet:'Water',cell_range:'$C$121:$D$122'}]}],before=structuredClone(refs);assert.deepEqual(refsForLocation(refs,{sheet:'Water',cell_range:'D122'}),[0]);assert.deepEqual(refs,before);
});
test('valid absolute locations navigate precisely while malformed and known out-of-bounds ranges keep the reader',async()=>{
 const savedWindow=globalThis.window;globalThis.window={innerWidth:1200};try{
  const {x,nodes}=sheetFixture(),reads=[];x.reader.rows=150;x.reader.columns=30;x.root.querySelectorAll=()=>[{dataset:{originalCell:'C121'},classList:{toggle(){}}}];x.loadReader=async(params,append,options)=>{reads.push({params,options});x.reader={...x.reader,sheet:params.sheet};return true;};
  const ref={sheet:'Water',cell_range:'$C$121:$D$122'},before=structuredClone(ref);await x.locate(ref);assert.deepEqual(reads[0].params,{sheet:'Water',row:121,column:3});assert.equal(x.selectedCell,'$C$121:$D$122');assert.deepEqual(ref,before);
  for(const value of ['C121junk','A0','D4:C5','A151','$AE$1',12]){const count=reads.length;await x.locate({sheet:'Water',cell_range:value});assert.equal(reads.length,count);assert.equal(nodes.get('#mw-reader-location-error').hidden,false);assert.equal(x.selectedCell,'$C$121:$D$122');}
  await x.locate({sheet:'Water'});assert.deepEqual(reads.at(-1).params,{sheet:'Water',row:1,column:1});assert.equal(x.selectedCell,null);
 }finally{globalThis.window=savedWindow;}
});
test('authoritative dimensions reject an unknown-sheet range without clearing an already visible original',async()=>{
 const {x,nodes,rendered}=sheetFixture(),old=x.reader;x.openingRequest=async()=>({...old,sheet:'Other',row:1,column:1,rows:10,columns:2});const result=await x.loadReader({sheet:'Other',row:121,column:3},false,{locationRange:{x0:3,y0:121,x1:4,y1:122}});assert.equal(result,false);assert.equal(x.reader,old);assert.equal(nodes.get('#mw-reader').innerHTML,'rows 1–80');assert.equal(rendered.length,0);assert.match(nodes.get('#mw-reader-location-error').textContent,/outside/);
});

test('failed location retaining a sheet releases its superseded continuation without appending a late response',async()=>{
 const {x,nodes,rendered}=sheetFixture(),original=x.reader,responses=[];x.selectedCell='C23';x.openingRequest=()=>new Promise((resolve,reject)=>responses.push({resolve,reject}));const append=x.readerAction('reader-next-rows');assert.equal(nodes.get('#mw-next-rows').disabled,true);const locate=x.loadReader({sheet:'Unknown',row:1,column:1},false,{locationRange:{x0:1,y0:1,x1:1,y1:1}});responses[1].reject(Error('New location unavailable'));await locate;responses[0].resolve({...original,row:81});await append;assert.equal(x.reader,original);assert.equal(x.selectedCell,'C23');assert.equal(rendered.length,0);assert.equal(x.readerAppendPending,null);assert.equal(nodes.get('#mw-next-rows').disabled,false);assert.equal(nodes.get('#mw-reader').innerHTML,'rows 1–80');
});
