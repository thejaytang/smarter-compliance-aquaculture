import test from 'node:test';
import assert from 'node:assert/strict';
import {requestPackageDownload, showPackageDownload} from '../frontend/components/package-download.js';

const id='d2068ca3-1efe-407e-965e-80510d9e74cd';
const path='/api/collaboration/collection-download?id='+id;
function fixture(){
 const clicks=[],timers=[],revoked=[];
 const doc={baseURI:'http://127.0.0.1:55542/',createElement(tag){return {tag,ownerDocument:doc,children:[],textContent:'',appendChild(child){this.children.push(child);child.parent=this;return child;},replaceChildren(){this.children=[];},remove(){this.parent.children=this.parent.children.filter(child=>child!==this);},click(){assert.equal(this.parent,doc.body);clicks.push({href:this.href,download:this.download});}};}};
 doc.body=doc.createElement('body');
 class Url extends URL{static createObjectURL(){return 'blob:local-test';}static revokeObjectURL(url){revoked.push(url);}}
 return {doc,clicks,timers,revoked,env:{document:doc,URL:Url,setTimeout:(fn,ms)=>timers.push({fn,ms})}};
}
function response(location){
 let cancelled=0,blobs=0;
 return {headers:new Headers({'Content-Disposition':'attachment; filename="receipt.zip"',...(location?{'Content-Location':location}:{})}),body:{async cancel(){cancelled++;}},async blob(){blobs++;return new Blob(['exact saved package']);},counts:()=>({cancelled,blobs})};
}
test('frozen collection requests its authenticated durable URL and releases unused ZIP body',async()=>{
 const f=fixture(),r=response(path);const result=await requestPackageDownload(r,f.env);
 assert.deepEqual(f.clicks,[{href:path,download:'receipt.zip'}]);
 assert.deepEqual(r.counts(),{cancelled:1,blobs:0});
 assert.deepEqual(result,{status:'download_requested',filename:'receipt.zip',downloadUrl:path});
 assert.equal(f.doc.body.children.length,0);assert.equal(f.timers.length,0);
});
test('foreign, unrelated or ambiguous download locations cannot navigate the browser',async()=>{
 for(const target of ['https://outside.invalid'+path,'//outside.invalid'+path,'/api/state?id='+id,path+'&id='+id,path+'&other=1',path+'#hidden','/api/collaboration/collection-download?id=../source']){
  const f=fixture(),r=response(target);await assert.rejects(requestPackageDownload(r,f.env),/download link is invalid/);
  assert.deepEqual(f.clicks,[]);assert.deepEqual(r.counts(),{cancelled:0,blobs:0});
 }
});
test('older servers retain blob download compatibility without promising a durable link',async()=>{
 const f=fixture(),r=response();const result=await requestPackageDownload(r,f.env);
 assert.equal(result.downloadUrl,null);assert.equal(result.status,'download_requested');
 assert.deepEqual(f.clicks,[{href:'blob:local-test',download:'receipt.zip'}]);assert.equal(f.timers[0].ms,30000);
 f.timers[0].fn();assert.deepEqual(f.revoked,['blob:local-test']);
});
test('download feedback distinguishes request from disk delivery and retains a direct retry link',()=>{
 const f=fixture(),container=f.doc.createElement('p');
 showPackageDownload(container,{downloadUrl:path,filename:'receipt.zip'},{frozen:true});
 assert.match(container.children[0].textContent,/Package frozen\. Download requested/);
 assert.doesNotMatch(container.children[0].textContent,/downloaded/i);
 const link=container.children.find(child=>child.tag==='a');assert.equal(link.href,path);assert.equal(link.download,'receipt.zip');assert.equal(link.textContent,'Download this saved package');
 showPackageDownload(container,{downloadUrl:null});assert.equal(container.children.some(child=>child.tag==='a'),false);assert.match(container.children.at(-1).textContent,/retry the download button/);
});
