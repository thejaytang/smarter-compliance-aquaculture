import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import vm from 'node:vm';
const source=await readFile(new URL('../ui/pdf-reader.js',import.meta.url),'utf8');
async function reader(href,{fail=false}={}){
 const nodes=new Map();const node=id=>nodes.get(id)||nodes.set(id,{value:id==='zoom'?'page-width':'',hidden:id==='retry'||id==='original',disabled:true,textContent:'',parentElement:{dataset:{}},options:['page-width','page-fit','0.75','1','1.25','1.5','2'].map(value=>({value}))}).get(id);
 const f={nodes,node,href,reloads:0,requests:[],events:[]};
 const location={href,search:new URL(href).search,origin:new URL(href).origin,reload(){f.reloads++;}};
 class EventBus{constructor(){this.events=new Map();f.bus=this;}on(name,handler){this.events.set(name,handler);}dispatch(name,value){f.events.push(name);this.events.get(name)?.(value);}}
 class Viewer{
  constructor({eventBus}){this.bus=eventBus;this.pagesCount=0;this.page=1;this.pagesRotation=0;f.viewer=this;}
  setDocument(doc){this.pagesCount=doc.numPages;this.bus.dispatch('pagesinit',{});}
  get currentScaleValue(){return this.scale;}
  set currentScaleValue(value){this.scale=value;if(this.pagesCount)this.currentPageNumber=1;} // PDF.js may restore an older visible location during scale changes.
  get currentPageNumber(){return this.page;}
  set currentPageNumber(value){this.page=value;this.bus.dispatch('pagechanging',{pageNumber:value});}
  getPageView(){return {textLayer:{div:{textContent:'source words'}}};}
 }
 const pdf={GlobalWorkerOptions:{},AnnotationMode:{ENABLE:1},getDocument(options){f.requests.push(options.url);return {promise:fail?Promise.reject(Error('503 unavailable')):Promise.resolve({numPages:4,getMetadata:async()=>({contentDispositionFilename:'Source.pdf'})}),destroy(){}};}};
 const components={EventBus,PDFViewer:Viewer,PDFLinkService:class{setViewer(){}setDocument(){}},PDFFindController:class{}};
 const window={addEventListener(){}};
 vm.runInNewContext(source.replace("import('/vendor/pdfjs/build/pdf.mjs')",'Promise.resolve(pdfModule)').replace("import('/vendor/pdfjs/web/pdf_viewer.mjs')",'Promise.resolve(componentModule)'),{
  URL,URLSearchParams,location,history:{replaceState(state,title,url){location.href=String(url);location.search=new URL(url).search;f.href=location.href;}},
  window,parent:window,document:{getElementById:node,body:{dataset:{}},querySelectorAll:()=>[...nodes.values()],title:''},
  ResizeObserver:class{observe(){}disconnect(){}},pdfModule:pdf,componentModule:components,
 });
 await new Promise(resolve=>setImmediate(resolve));return f;
}
const base='http://127.0.0.1:60905/pdf-reader.html?id='+'a'.repeat(32)+'&view=personal&page=3';
test('page, zoom and rotation remain bound to this original across reload and Retry',async()=>{
 const f=await reader(base);assert.equal(f.viewer.currentPageNumber,3);
 f.node('next').onclick();f.node('zoom').value='1.5';f.node('zoom').onchange();f.node('rotate').onclick();
 const url=new URL(f.href);assert.equal(url.searchParams.get('page'),'4');assert.equal(url.searchParams.get('zoom'),'1.5');assert.equal(url.searchParams.get('rotation'),'90');
 const resumed=await reader(f.href);assert.equal(resumed.viewer.currentPageNumber,4);assert.equal(resumed.viewer.currentScaleValue,'1.5');assert.equal(resumed.viewer.pagesRotation,90);
 resumed.node('retry').onclick();assert.equal(resumed.reloads,1);assert.deepEqual(resumed.requests,['/api/material/original?id='+'a'.repeat(32)+'&view=personal']);
});
test('failed loading has a real original link, disabled editing controls and same-source Retry',async()=>{
 const f=await reader(base,{fail:true});assert.match(f.node('status').textContent,/could not be loaded/);assert.doesNotMatch(f.node('status').textContent,/503|http:/);assert.equal(f.node('retry').hidden,false);
 assert.equal(f.node('original').hidden,false);assert.equal(f.node('original').href,'/api/material/original?id='+'a'.repeat(32)+'&view=personal');
 assert.equal(f.node('next').disabled,true);assert.equal(f.node('zoom').disabled,true);f.node('retry').onclick();assert.equal(f.href,base);assert.equal(f.reloads,1);
});
test('invalid identity never requests source; invalid display settings use safe defaults',async()=>{
 const invalid=await reader(base.replace('a'.repeat(32),'bad'));assert.equal(invalid.requests.length,0);assert.equal(invalid.node('original').hidden,true);
 const f=await reader(base+'&zoom=999&rotation=17');assert.equal(f.viewer.currentScaleValue,'page-width');assert.equal(f.viewer.pagesRotation,0);
});
test('another page rendering successfully cannot erase the visible page failure',async()=>{
 const f=await reader(base);f.bus.dispatch('pagerendered',{pageNumber:3,error:Error('failed')});assert.equal(f.node('retry').hidden,false);
 f.bus.dispatch('pagerendered',{pageNumber:2});assert.equal(f.node('retry').hidden,false);assert.match(f.node('status').textContent,/Page 3: Could not render/);
});

test('source PDFs use only the governed local original routes',async()=>{
 const local='/api/pdf/TS003/'+'a'.repeat(64)+'/original.pdf';
 const r=await reader('http://127.0.0.1:60905/pdf-reader.html?'+new URLSearchParams({source:local,page:2}));
 assert.deepEqual(r.requests,[local]);assert.equal(r.viewer.currentPageNumber,2);
 for(const target of ['https://outside.invalid/file.pdf','/api/state','/api/pdf/../../api/state']){
  const denied=await reader('http://127.0.0.1:60905/pdf-reader.html?'+new URLSearchParams({source:target}));
  assert.equal(denied.requests.length,0);assert.equal(denied.node('retry').hidden,false);
 }
});
