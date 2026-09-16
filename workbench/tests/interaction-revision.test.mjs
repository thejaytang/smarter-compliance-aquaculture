import test from 'node:test';
import assert from 'node:assert/strict';
import {resizePair} from '../ui/pane-layout.js';
import {versionComparison,versionTextDiff} from '../ui/version-comparison.js';
import {sourcePreview} from '../ui/requirement-source.js';
test('dragging either side near zero snaps, normal movement preserves pair width and other panes',()=>{
 const widths=[300,400,350,500];assert.deepEqual(resizePair(widths,0,1,80),{widths:[380,320,350,500],collapse:null});assert.equal(resizePair(widths,0,1,-230).collapse,0);assert.equal(resizePair(widths,2,3,430).collapse,3);assert.deepEqual(widths,[300,400,350,500]);
});
test('comparison hides unchanged passages and escapes source HTML while distinguishing additions and deletions',()=>{
 const shared={id:'same',text:'Unchanged',type:'text'},old={id:'x',text:'The fish is hot.',type:'text'},next={...old,text:'The fish is cold.'};const html=versionComparison({blocks:[shared,old]},{blocks:[shared,next]});assert.match(html,/1 changed passages/);assert.doesNotMatch(html,/Unchanged/);assert.match(html,/<del[^>]*>hot/);assert.match(html,/<ins[^>]*>cold/);assert.doesNotMatch(versionTextDiff('','<script>x</script>'),/<script>/);
});
test('long unchanged runs fold without losing their content',()=>{const html=versionTextDiff('x'.repeat(900)+' one','x'.repeat(900)+' two');assert.match(html,/unchanged characters/);assert.equal((html.match(/x/g)||[]).length,900);});
test('source overview preserves repeated Unicode text and nested relation colours',()=>{
 const text='鱼 shall check if warm and if cold';const d={text,units:{r:{conditions:[2,'a','b']},a:{},b:{}},spans:{r:[0,33],a:[14,21],b:[26,33]},field_spans:{r:{Subject:[0,1]},a:{'Main Verb':[3,7]}},labels:{r:'R1',a:'C1',b:'C2'}};
 const html=sourcePreview(d);assert.match(html,/semantic-0/);assert.match(html,/semantic-4/);assert.match(html,/annotation-outer/);assert.match(html,/C1 in R1/);assert.match(html,/C2 in R1/);
});
