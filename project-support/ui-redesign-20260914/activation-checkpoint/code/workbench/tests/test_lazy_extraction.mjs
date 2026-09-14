import {test} from 'node:test';
import assert from 'node:assert/strict';
import {Extraction} from '../ui/extraction.js';
function fixture(result){
 const x=new Extraction(),panel={dataset:{},innerHTML:'',textContent:'',querySelector:()=>null};
 x.token={};x.data={policy:{revision:1},documents:[{id:'doc',revision:2}]};x.docId='doc';x.cache=new Map();
 x.container={querySelector:()=>panel,querySelectorAll:()=>[]};x.api=async()=>result;
 const rendered=[];x.detail=(...args)=>rendered.push(args);return {x,panel,rendered};
}
const item={id:'unit',fingerprint:'v1'};
test('detail binds an exact unit guard, independent of unrelated source revision',async()=>{
 const result={revision:3,policy_revision:1,guard:'unit-and-dependency-guard',unit:{id:'unit'}};
 const {x,rendered}=fixture(result);await x.select(item);assert.equal(rendered[0][1],result);
});
test('cached unit renders immediately and refreshes a changed dependency guard',async()=>{
 const old={guard:'old',unit:{id:'unit'}},fresh={guard:'fresh',unit:{id:'unit'}};
 const {x,rendered}=fixture(fresh);x.cache.set('doc:unit:v1:1',old);await x.select(item);
 assert.equal(rendered[0][1],old);assert.equal(rendered[1][1],fresh);
});
test('navigation prevents an older detail request from creating a form',async()=>{
 const {x,rendered}=fixture();let resolve;x.api=()=>new Promise(r=>resolve=r);
 const pending=x.select(item);x.leave();resolve({guard:'g',unit:{id:'unit'}});await pending;assert.equal(rendered.length,0);
});
