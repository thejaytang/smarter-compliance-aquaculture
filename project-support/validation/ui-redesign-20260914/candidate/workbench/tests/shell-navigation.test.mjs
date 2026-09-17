import test from 'node:test';
import assert from 'node:assert/strict';
import {createNavigation, workspaceFor, workspaceModules, guardedNavigation} from '../ui/shell-navigation.js';

const memory=(value=null)=>({value,getItem(){return this.value;},setItem(key,next){this.value=next;}});

test('first entry uses review; each workspace restores its own last module',()=>{
  const storage=memory(),nav=createNavigation(storage);
  assert.equal(nav.view,'system1');
  nav.commit('sourceRecords');nav.commit('system2History');
  assert.equal(nav.forWorkspace('sources'),'sourceRecords');
  assert.equal(createNavigation(storage).view,'system2History');
  nav.commit(nav.forWorkspace('sources'));
  assert.equal(createNavigation(storage).view,'sourceRecords');
});

test('corrupt, legacy and cross-workspace saved routes never become ordinary modules',()=>{
  for(const stored of ['{broken',JSON.stringify({workspace:'system3',last:{sources:'system2History',materials:'overview'}})]){
    const nav=createNavigation(memory(stored));
    assert.equal(nav.view,'system1');assert.equal(nav.forWorkspace('materials'),'system2');
  }
  assert.deepEqual(Object.values(workspaceModules).flat().map(([id])=>id),['addSources','system1','sourceRecords','history','system2','system2History']);
  assert.equal(workspaceFor('legacyReview'),null);
  assert.equal(createNavigation(memory()).commit('settings'),false);
});

test('storage denial keeps ordinary navigation functional without claiming persistence',()=>{
  const nav=createNavigation({getItem(){throw Error('blocked');},setItem(){throw Error('blocked');}});
  assert.equal(nav.view,'system1');nav.commit('system2');assert.equal(nav.view,'system2');
});

test('unsaved-work refusal prevents preparation, route change and persistence',async()=>{
  const storage=memory(),nav=createNavigation(storage),calls=[];
  const moved=await guardedNavigation({canLeave:()=>false,prepare:async()=>calls.push('save'),commit:()=>{calls.push('mount');nav.commit('system2');}});
  assert.equal(moved,false);assert.deepEqual(calls,[]);assert.equal(nav.view,'system1');assert.equal(storage.value,null);
});

test('a failed draft save preserves the active route and saved return location',async()=>{
  const storage=memory(),nav=createNavigation(storage);
  nav.commit('sourceRecords');const before=storage.value;
  await assert.rejects(guardedNavigation({canLeave:()=>true,prepare:async()=>{throw Error('save failed');},commit:()=>nav.commit('system2')}),/save failed/);
  assert.equal(nav.view,'sourceRecords');assert.equal(storage.value,before);
});

test('successful navigation waits for preparation before committing the new route',async()=>{
  const calls=[];
  assert.equal(await guardedNavigation({canLeave:()=>true,prepare:async()=>{await Promise.resolve();calls.push('saved');},commit:async()=>calls.push('mounted')}),true);
  assert.deepEqual(calls,['saved','mounted']);
});
