/** Pure reading helpers. They never change saved content or review state. */
export function searchBlocks(blocks,query='') {
  const needle=query.trim().toLocaleLowerCase();
  return blocks.flatMap((b,i)=>!needle||[b.numbering,b.text,...(b.table?.notes||[]),...(b.table?.rows||[]).flat()].join('\n').toLocaleLowerCase().includes(needle)?[i]:[]);
}
export function tableWindow(table,position={}) {
  const rows=table.rows||[],columns=rows.reduce((n,r)=>Math.max(n,r.length),1);
  const row=Math.max(0,Math.min(Math.max(0,rows.length-1),Number(position?.row)||0));
  const column=Math.max(0,Math.min(columns-1,Number(position?.column)||0));
  return {row,column,endRow:Math.min(rows.length,row+40),endColumn:Math.min(columns,column+10),columns};
}
export function regionFromPoints(start,end,rect) {
  if(!(rect.width>0&&rect.height>0))return null;
  const x=v=>Math.round(Math.max(0,Math.min(100,(v-rect.left)*100/rect.width))*10)/10;
  const y=v=>Math.round(Math.max(0,Math.min(100,(v-rect.top)*100/rect.height))*10)/10;
  const region={x0:Math.min(x(start.x),x(end.x)),y0:Math.min(y(start.y),y(end.y)),x1:Math.max(x(start.x),x(end.x)),y1:Math.max(y(start.y),y(end.y))};
  return region.x1>region.x0&&region.y1>region.y0?region:null;
}
function cellRange(value) {const m=String(value||'').match(/^([A-Z]+)(\d+)(?::([A-Z]+)(\d+))?$/i);if(!m)return null;const col=v=>[...v.toUpperCase()].reduce((n,c)=>n*26+c.charCodeAt(0)-64,0);return {x0:col(m[1]),y0:+m[2],x1:col(m[3]||m[1]),y1:+(m[4]||m[2])};}
export function refsForLocation(blocks,location) {
  return blocks.flatMap((block,index)=>{
    const refs=[...(block.source_refs||[]),...(block.image?.source_ref?[block.image.source_ref]:[])];
    const matches=refs.some(ref=>{
      if(location.page!=null)return (ref.page??(ref.page_index!=null?ref.page_index+1:null))===location.page;
      if(location.sheet){if(ref.sheet!==location.sheet)return false;if(!location.cell_range)return true;const a=cellRange(ref.cell_range),b=cellRange(location.cell_range);return !!a&&!!b&&a.x0<=b.x1&&a.x1>=b.x0&&a.y0<=b.y1&&a.y1>=b.y0;}
      if(location.anchor||location.locator)return !!((location.anchor&&ref.anchor===location.anchor)||(location.locator&&ref.locator===location.locator));
      return false;
    });return matches?[index]:[];
  });
}

let draftDatabase;
function openDraftDatabase(){
  if(!globalThis.indexedDB)return Promise.reject(Error('Browser recovery storage is unavailable.'));
  if(!draftDatabase)draftDatabase=new Promise((resolve,reject)=>{const request=indexedDB.open('material-drafts-v2',1);request.onupgradeneeded=()=>request.result.createObjectStore('drafts');request.onsuccess=()=>{const db=request.result;db.onversionchange=()=>{db.close();draftDatabase=null;};resolve(db);};request.onerror=()=>{draftDatabase=null;reject(Error('Browser recovery storage could not be opened.'));};request.onblocked=()=>{draftDatabase=null;reject(Error('Browser recovery storage is blocked by another page.'));};});
  return draftDatabase;
}
async function draftTransaction(mode,work){let timer;return Promise.race([(async()=>{const db=await openDraftDatabase();return new Promise((resolve,reject)=>{const tx=db.transaction('drafts',mode),store=tx.objectStore('drafts'),result={};work(store,result);tx.oncomplete=()=>resolve(result);tx.onerror=()=>reject(Error('Browser recovery storage write or read failed.'));tx.onabort=()=>reject(Error('Browser recovery storage operation was interrupted.'));});})(),new Promise((_,reject)=>{timer=setTimeout(()=>reject(Error('Browser recovery storage timed out.')),3000);})]).finally(()=>clearTimeout(timer));}
export const readDraftRecords=keys=>draftTransaction('readonly',(store,result)=>keys.forEach(key=>{const request=store.get(key);request.onsuccess=()=>result[key]=request.result;}));
export const writeDraftRecords=entries=>draftTransaction('readwrite',store=>Object.entries(entries).forEach(([key,value])=>store.put(value,key)));
export const deleteDraftRecords=keys=>draftTransaction('readwrite',store=>keys.forEach(key=>store.delete(key)));

// sessionStorage is copied by Duplicate Tab/window.open. A live document must
// claim its owner key before it can write a per-tab recovery journal.
export async function claimDraftOwner(storage,locks,uuid=()=>crypto.randomUUID()){
  let inherited;try{inherited=storage.getItem('material-draft-tab');}catch{}
  const remember=owner=>{try{storage.setItem('material-draft-tab',owner.id);}catch{}return owner;};
  if(locks?.request){
    const claim=id=>new Promise((resolve,reject)=>{locks.request('material-draft-owner:'+id,{ifAvailable:true},lock=>{if(!lock){resolve(null);return;}resolve({id,recoveryOwner:null});return new Promise(()=>{});}).catch(reject);});
    try{const owner=await claim(inherited||uuid());if(owner)return remember(owner);const fresh=await claim(uuid());if(fresh)return remember(fresh);}catch{}
  }
  // Without a live-owner primitive, never reuse a writable owner key. The prior
  // document's key remains a read-only recovery source until this document edits.
  return {id:uuid(),recoveryOwner:inherited||null};
}
let documentDraftOwner;
export function getDocumentDraftOwner(){return documentDraftOwner??=claimDraftOwner(globalThis.sessionStorage,globalThis.navigator?.locks);}
