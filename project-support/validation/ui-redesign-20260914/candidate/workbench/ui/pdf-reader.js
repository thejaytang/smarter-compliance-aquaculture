// Read-only PDF.js component integration. Source bytes and review state are never edited.
const $ = id => document.getElementById(id);
const query = new URLSearchParams(location.search);
const id = query.get('id'), view = query.get('view') || 'personal';
document.body.dataset.embedded=String(parent!==window);
history.scrollRestoration='manual';
let loadingTask, viewer, bus, documentPdf;
const pageStates = new Map();
function keepReadingPosition() {
  if (!documentPdf || !viewer?.pagesCount) return;
  const url = new URL(location.href);
  url.searchParams.set('page', String(viewer.currentPageNumber));
  url.searchParams.set('zoom', $('zoom').value);
  url.searchParams.set('rotation', String(viewer.pagesRotation));
  history.replaceState(null, '', url);
}
function status(text, error = false) {
  $('status').textContent = text;
  $('status').parentElement.dataset.error = String(error);
  $('retry').hidden = !error;
}
function notify(page) {
  if (parent !== window) parent.postMessage({type:'saved-pdf-page',id,view,page},location.origin);
}
function pageStatus() {
  if(!documentPdf||!viewer)return;
  const page=viewer.currentPageNumber,state=pageStates.get(page)||{};
  if(state.error)return status('Page '+page+': '+state.error+' Retry or use Page image / Open original.',true);
  if(!state.rendered)return status('Rendering original page '+page+'…');
  status('Page '+page+' of '+documentPdf.numPages+' · '+(state.selectable===false?'No selectable text; read the page image':state.selectable?'Select original text to copy':'Preparing text selection…'));
}
function find(again = false) {
  if (!bus || !documentPdf) return;
  bus.dispatch('find',{source:window,type:again?'again':'',query:$('query').value,
    caseSensitive:false,entireWord:false,highlightAll:true,findPrevious:false,matchDiacritics:false});
}
$('retry').onclick = () => location.reload();
$('search').onsubmit = event => {event.preventDefault();find();};
$('find-next').onclick = () => find(true);
$('previous').onclick = () => {if(viewer)viewer.currentPageNumber=Math.max(1,viewer.currentPageNumber-1);};
$('next').onclick = () => {if(viewer)viewer.currentPageNumber=Math.min(documentPdf.numPages,viewer.currentPageNumber+1);};
$('page').onchange = () => {
  const page=Number($('page').value);
  if(viewer&&Number.isInteger(page)&&page>=1&&page<=documentPdf.numPages)viewer.currentPageNumber=page;
  else if(viewer)$('page').value=viewer.currentPageNumber;
};
$('zoom').onchange = () => {if(viewer){const page=viewer.currentPageNumber;viewer.currentScaleValue=$('zoom').value;viewer.currentPageNumber=page;keepReadingPosition();}};
$('rotate').onclick = () => {if(viewer){const page=viewer.currentPageNumber;viewer.pagesRotation=(viewer.pagesRotation+90)%360;viewer.currentPageNumber=page;keepReadingPosition();}};
async function open() {
  let originalURL;
  if(query.has('source')){
    const sourceURL=new URL(query.get('source'),location.origin);
    if(sourceURL.origin!==location.origin||!(sourceURL.pathname.startsWith('/api/pdf/')||sourceURL.pathname==='/api/sources/intake-original'))throw Error('Choose a saved material from the workbench.');
    originalURL=sourceURL.pathname+sourceURL.search;
  }else{
    if(!/^[0-9a-f]{32}$/.test(id||'')||!['personal','master','archive'].includes(view))throw Error('Choose a saved material from the workbench.');
    originalURL='/api/material/original?'+new URLSearchParams({id,view});
  }
  $('original').href=originalURL;
  $('original').hidden=false;
  const zoom=query.get('zoom');
  if([...$('zoom').options].some(option=>option.value===zoom))$('zoom').value=zoom;
  const pdf = await import('/vendor/pdfjs/build/pdf.mjs');
  const components = await import('/vendor/pdfjs/web/pdf_viewer.mjs');
  pdf.GlobalWorkerOptions.workerSrc='/vendor/pdfjs/build/pdf.worker.mjs';
  bus=new components.EventBus();
  const linkService=new components.PDFLinkService({eventBus:bus});
  linkService.externalLinkEnabled=false;
  const findController=new components.PDFFindController({eventBus:bus,linkService});
  viewer=new components.PDFViewer({container:$('viewerContainer'),eventBus:bus,linkService,findController,
    annotationMode:pdf.AnnotationMode.ENABLE,enablePermissions:true,
    maxCanvasPixels:12000000,maxCanvasDim:4096,imageResourcesPath:'/vendor/pdfjs/web/images/'});
  linkService.setViewer(viewer);
  bus.on('pagesinit',()=>{
    const rotation=Number(query.get('rotation')||0);
    if([0,90,180,270].includes(rotation))viewer.pagesRotation=rotation;
    viewer.currentScaleValue=$('zoom').value;
    const requested=Number(query.get('page')||1);
    viewer.currentPageNumber=Number.isInteger(requested)?Math.max(1,Math.min(documentPdf.numPages,requested)):1;
    for(const element of document.querySelectorAll('header [disabled]'))element.disabled=false;
    $('pages').textContent='of '+documentPdf.numPages;
    updatePage(viewer.currentPageNumber);
  });
  function updatePage(page) {
    $('page').value=page;$('page').max=documentPdf.numPages;
    $('previous').disabled=page<=1;$('next').disabled=page>=documentPdf.numPages;
    keepReadingPosition();
    notify(page);
    pageStatus();
  }
  bus.on('pagechanging',event=>{if(documentPdf)updatePage(event.pageNumber);});
  bus.on('pagerendered',event=>{
    const state=pageStates.get(event.pageNumber)||{};
    state.rendered=!event.error;if(event.error)state.error='Could not render the complete page.';
    pageStates.set(event.pageNumber,state);pageStatus();
  });
  bus.on('textlayerrendered',event=>{
    const state=pageStates.get(event.pageNumber)||{};
    if(event.error)state.error='Text selection is unavailable.';
    else state.selectable=!!viewer.getPageView(event.pageNumber-1)?.textLayer?.div?.textContent?.trim();
    pageStates.set(event.pageNumber,state);pageStatus();
  });
  bus.on('annotationlayerrendered',event=>{if(event.error){const state=pageStates.get(event.pageNumber)||{};state.error='Some PDF annotations could not be displayed.';pageStates.set(event.pageNumber,state);pageStatus();}});
  bus.on('updatefindmatchescount',event=>{
    const count=event.matchesCount;$('matches').textContent=count.total?count.current+' / '+count.total:'No matches';
  });
  bus.on('updatefindcontrolstate',event=>{
    if(event.state===1)$('matches').textContent='No matches';
    else if(event.state===3)$('matches').textContent='Searching…';
    else if(event.matchesCount)$('matches').textContent=event.matchesCount.total?event.matchesCount.current+' / '+event.matchesCount.total:'';
  });
  loadingTask=pdf.getDocument({url:originalURL,
    cMapUrl:'/vendor/pdfjs/cmaps/',cMapPacked:true,standardFontDataUrl:'/vendor/pdfjs/standard_fonts/',
    wasmUrl:'/vendor/pdfjs/wasm/',iccUrl:'/vendor/pdfjs/iccs/',
    isEvalSupported:false,enableXfa:false,useWasm:false,stopAtErrors:true,
    disableAutoFetch:true,disableStream:true});
  loadingTask.onProgress=({loaded,total})=>{if(!documentPdf)status(total?'Reading saved PDF · '+Math.round(loaded/1024)+' / '+Math.round(total/1024)+' KB':'Reading saved PDF…');};
  documentPdf=await loadingTask.promise;
  documentPdf.getMetadata().then(metadata=>{
    const filename=metadata.contentDispositionFilename;
    if(filename){$('source').textContent=filename+' · saved original';document.title=filename+' · Original PDF';}
  }).catch(()=>{$('source').textContent='Saved original PDF · material '+id;});
  if(documentPdf.isPureXfa)throw Error('This PDF uses an unsupported XFA form. Open the original in a compatible reader.');
  linkService.setDocument(documentPdf,null);viewer.setDocument(documentPdf);
  const resize=new ResizeObserver(()=>{if(viewer?.pagesCount&&$('zoom').value.startsWith('page-'))viewer.currentScaleValue=$('zoom').value;});
  resize.observe($('viewerContainer'));
  window.addEventListener('pagehide',()=>resize.disconnect(),{once:true});
}
open().catch(error=>{
  const message=error.name==='PasswordException'?'This PDF needs a password. Open the original in a PDF reader.':
    error.message==='Choose a saved material from the workbench.'?error.message:
    error.message.includes('unsupported XFA')?'This PDF form needs a compatible reader. Open the original file.':
    'The saved PDF could not be loaded. Retry or open the original file.';
  status(message,true);
});
window.addEventListener('pagehide',()=>{loadingTask?.destroy();},{once:true});
