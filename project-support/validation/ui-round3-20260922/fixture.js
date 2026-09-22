
import {showEvidence} from '/workbench/frontend/components/evidence-viewer.js';
import {Materials} from '/workbench/frontend/components/materials.js';
const q=s=>document.querySelector(s),info=await fetch('/fixture-info').then(r=>r.json()),events=[];
const api=async(path,body)=>{events.push({path,body});const response=await fetch(path,{...(body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{})});const result=await response.json();if(!response.ok)throw Error(result.error);return result;};
let material,regionFails=true;
const worksheet=(row,column,material=false)=>({kind:'spreadsheet',label:'Synthetic worksheet',sheet:'Worksheet Æ',sheets:material?[{name:'Worksheet Æ',state:'visible'}]:['Worksheet Æ'],row,column,row_count:40,column_count:12,rows:200,columns:40,state:'visible',merged:[],cells:Array.from({length:Math.min(40,201-row)},(_,r)=>Array.from({length:Math.min(12,41-column)},(_,c)=>({address:String.fromCharCode(65+(column+c-1)%26)+(row+r),value:`row ${row+r}, col ${column+c}`})))});
async function open(){material?.stopPdfDisplay();material=null;q('#stage').replaceChildren();q('#fixture-status').textContent='';const mode=q('#mode').value;
 if(['html','sheet','region'].includes(mode)){const host=document.createElement('section');host.className='source-original-body';q('#stage').append(host);
  if(mode==='html')return showEvidence(host,'FXHTML',path=>api(path+'&expected_hash='+info.hash));
  if(mode==='sheet')return showEvidence(host,'FXSHEET',async path=>{events.push({path});const p=new URL(path,location.origin).searchParams;return worksheet(Number(p.get('row')),Number(p.get('column')));});
  regionFails=true;return showEvidence(host,'FXREGION',async path=>{events.push({path});const fail=regionFails;regionFails=false;return {kind:'html_region',label:'Synthetic bound region · page 2',image:fail?'data:image/png;base64,broken':'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jlp8AAAAASUVORK5CYII=',html:'<!doctype html><html><head><meta http-equiv="Content-Security-Policy" content="default-src \'none\'"></head><body><p>Independent sanitized markup remains readable when the image fails.</p></body></html>'};},{documentId:'synthetic-document',unitId:'page2',page:2});
 }
 const root=document.createElement('section');root.className='mw-original';root.innerHTML='<header><strong>Saved synthetic original</strong></header><div id="mw-original-toolbar" class="mw-reader-toolbar"></div><div id="mw-reader"></div>';q('#stage').append(root);const x=material=new Materials();x.root=root;x.q=s=>root.querySelector(s);x.id=info.id;x.material={id:info.id,source:{content_hash:'synthetic'},collaboration:{view:'personal'}};x.draft={blocks:[]};x.token={};x.message=text=>q('#fixture-status').textContent=text;
 x.loadReader=async(options={})=>{events.push({reader:options});x.stopPdfDisplay();x.reader=mode==='cells'?worksheet(options.row||121,options.column||25,true):{kind:'pdf',page:options.page||3,pages:4,width:595,height:842,...(mode==='pdf'?{interactive_pdf_reader:'pdfjs-6.3.289'}:{})};x.renderReader(x.reader);};
 root.addEventListener('click',event=>{const target=event.target.closest('[data-action]');if(target&&!target.disabled)x.readerAction(target.dataset.action);});await x.loadReader();
}
q('#open').onclick=open;q('#mode').onchange=open;
q('#changed').onclick=async()=>{await api('/fixture-hash',{changed:true});q('#fixture-status').textContent='Synthetic file changed. Reopen Registered HTML to verify the bound hash fails.';};
q('#restore').onclick=async()=>{await api('/fixture-hash',{changed:false});q('#fixture-status').textContent='Synthetic original restored.';};
q('#log').onclick=async()=>{q('#local-log').textContent=JSON.stringify({local:events,http:await api('/fixture-events'),scriptRan:window.FIXTURE_SCRIPT_RAN===true},null,2);q('#logs').open=true;};await open();
