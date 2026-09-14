import {test} from 'node:test';
import assert from 'node:assert/strict';
import {cp, mkdtemp, rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {pathToFileURL} from 'node:url';

test('ordinary extraction remains loadable when a newer optional reference module is unavailable', async()=>{
 const directory=await mkdtemp(join(tmpdir(),'workbench-extension-'));
 try{
  // This import check needs source modules, not the unrelated binary demo fixtures.
  await cp(new URL('../ui/',import.meta.url),directory,{recursive:true,filter:source=>!source.includes('demo-assets')});
  await rm(join(directory,'pdf-references.js'));
  const module=await import(pathToFileURL(join(directory,'extraction.js')).href);
  assert.equal(typeof module.Extraction,'function');
 }finally{await rm(directory,{recursive:true,force:true});}
});
