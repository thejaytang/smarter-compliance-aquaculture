import test from 'node:test';
import assert from 'node:assert/strict';
import {Materials} from '../frontend/components/materials.js';
function peer(){const m=new Materials();m.state={collaboration:{peer_sync:true}};m.material={};m.reviewReady=()=>true;m.dirty=true;m.message=()=>{};m.collaboration.runPreview=()=>{throw Error('Unexpected administrator preview');};return m;}
test('peer archive saves declarations before opening explicit confirmation',async()=>{const m=peer(),calls=[];m.save=async()=>{calls.push('save');m.dirty=false;return true;};m.reviewDialog=()=>calls.push('confirm');await m.archiveContent();assert.deepEqual(calls,['save','confirm']);});
test('peer archive stops after failed save',async()=>{const m=peer();m.save=async()=>false;m.reviewDialog=()=>{throw Error('Unsaved confirmation');};await m.archiveContent();assert.equal(m.dirty,true);});
test('peer archive requires fresh declarations after saved content changes',async()=>{const m=peer();m.save=async()=>{m.dirty=false;m.reviewReady=()=>false;return true;};m.reviewDialog=()=>{throw Error('Invalidated review');};await m.archiveContent();});
