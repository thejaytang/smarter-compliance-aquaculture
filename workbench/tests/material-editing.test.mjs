import test from 'node:test';import assert from 'node:assert/strict';
import {changeHeadingLevel,reconstructTable,tableAxis} from '../frontend/components/material-editing.js';
test('hierarchy shift retains subtree and rejects an orphan indent',()=>{
 const blocks=[{id:'a',type:'heading',level:1},{id:'b',type:'heading',level:1},{id:'c',type:'heading',level:2,parent_id:'b'},{id:'d',type:'text',parent_id:'c'}];
 const after=changeHeadingLevel(blocks,'b',1);assert.equal(after[1].parent_id,'a');assert.equal(after[2].level,3);assert.equal(after[3].parent_id,'c');assert.equal(blocks[1].level,1);assert.throws(()=>changeHeadingLevel(blocks,'a',1));
});
test('table repair retains original text, people, refs and external dependencies',()=>{
 const blocks=[{id:'a',type:'text',text:'A\tB',source_refs:[{scope_id:'p1'}]},{id:'b',type:'text',text:'C\tD',source_refs:[{scope_id:'p2'}]},{id:'c',type:'text',text:'note',dependencies:['b']}];
 const next=reconstructTable(blocks,['a','b'],[['A','B'],['C','D']],'Ana');assert.equal(next.length,2);assert.equal(next[0].human_transforms[0].actor,'Ana');assert.equal(next[0].human_transforms[0].original_blocks[1].text,'C\tD');assert.equal(next[0].source_refs.length,2);assert.deepEqual(next[1].dependencies,['a']);assert.equal(blocks.length,3);assert.throws(()=>reconstructTable(blocks,['a','c'],[['x']],'Ana'));
});
test('insertion and removal retain surviving cells and adjust merged spans',()=>{
 const t={rows:[['A','B'],['C','D'],['E','F']],merges:[{row:0,col:0,rowspan:2,colspan:2}]};
 const added=tableAxis(t,'row',1);assert.deepEqual(added.rows[2],['C','D']);assert.equal(added.merges[0].rowspan,3);assert.deepEqual(tableAxis(added,'row',1,true),t);assert.deepEqual(tableAxis(t,'column',1,true).rows,[['A'],['C'],['E']]);assert.throws(()=>tableAxis({rows:[['x']]},'row',0,true));
});
