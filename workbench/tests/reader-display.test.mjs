import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {Materials} from '../ui/materials.js';

function fixture(){
 const x=new Materials(),nodes=new Map(),image={src:'old-image',style:{width:'100%'},naturalWidth:675,getBoundingClientRect:()=>({width:f.cssWidth})},host={scrollTop:143,scrollLeft:31},f={x,cssWidth:600,calls:[],image,host};
 x.q=s=>s==='.mw-pdf-page-image'?image:s==='.mw-pdf-image-scroll'?host:nodes.get(s)||nodes.set(s,{innerHTML:'',textContent:'',hidden:true,style:{},classList:{toggle(){},remove(){}}}).get(s);
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
 f.x.reader={kind:'html'};f.x.renderReader({kind:'html',anchors:[],navigation_anchors:[]});assert.match(f.x.q('#mw-reader').innerHTML,/Offline HTML · reflowed reading view/);assert.match(f.x.q('#mw-reader').innerHTML,/sandbox=""/);assert.doesNotMatch(f.x.q('#mw-reader').innerHTML,/mw-reader-notice/);assert.doesNotMatch(f.x.q('#mw-original-toolbar').innerHTML,/<button|<summary/);assert.equal(typeof f.x.q('#mw-html-anchor').onchange,'function');
});

test('document CSS gives remaining space to one evidence viewport and keeps compact original controls',async()=>{
 const css=await readFile(new URL('../ui/materials.css',import.meta.url),'utf8');assert.match(css,/#mw-reader\.mw-reader-document\{[^}]*display:flex;[^}]*overflow:hidden;[^}]*min-height:0/);assert.match(css,/\.mw-reader-document>\.mw-html,\.mw-reader-document>\.mw-pdf-image-scroll\{[^}]*flex:1 1 0;min-height:0;height:auto/);assert.match(css,/\.mw-original>header\{min-height:54px;margin:0;/);assert.match(css,/\.mw-reader-toolbar\.mw-document-toolbar \.mw-reader-secondary button\{min-height:26px;padding:2px 4px/);assert.match(css,/\.mw-reader-secondary\{margin-top:4px;gap:6px/);assert.match(css,/\.mw-document-toolbar \.mw-pdf-page-control input\{width:48px/);
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
  const accept=listeners.get('message'),valid={origin:'http://local',source:frame.contentWindow,data:{type:'saved-pdf-page',id:f.x.id,view:'personal',page:3}};
  for(const change of [{origin:'https://foreign.example'},{source:{}},{data:{...valid.data,id:'other'}},{data:{...valid.data,view:'master'}},{data:{...valid.data,page:6}},{data:{...valid.data,page:2.5}}]){accept({...valid,...change});assert.equal(f.x.reader.page,2);}
  accept(valid);assert.equal(f.x.reader.page,3);assert.match(f.x.q('.mw-open-pdf-reader').href,/page=3/);assert.equal(f.x.material.source.content_hash,'source-hash');
  f.x.stopPdfDisplay();assert.equal(listeners.size,0);
 }finally{for(const [key,value] of Object.entries(saved))if(value===undefined)delete globalThis[key];else globalThis[key]=value;}
});

test('switching reader modes explicitly reloads only the currently selected page',async()=>{
 const f=fixture(),draft={blocks:[{text:'Keep this work'}]};f.x.draft=draft;const pages=[];f.x.loadReader=async options=>pages.push(options);
 await f.x.readerAction('reader-pdf-mode');assert.equal(f.x.pdfImageFallback,true);
 await f.x.readerAction('reader-pdf-mode');assert.equal(f.x.pdfImageFallback,false);
 assert.deepEqual(pages,[{page:2},{page:2}]);assert.equal(f.x.draft,draft);assert.equal(f.calls.length,0);
});
