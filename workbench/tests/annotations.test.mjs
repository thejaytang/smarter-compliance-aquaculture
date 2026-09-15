import test from 'node:test';
import assert from 'node:assert/strict';
import {renderAnnotations,markdownText,updateMarkdownBlock} from '../ui/markdown-content.js';
import {checkingLogic} from '../ui/interpretations.js';
const span=(text,start,end,field='Subject',unit_id='u1')=>({source_text:text,start,end,field,unit_id,session_id:'s',label:'R1'});
test('Unicode repeated text maps by codepoint range, without changing source or Markdown',()=>{
 const source='鱼🐟 **检查** and 检查 æøå [link](https://example.org)\nnext';const text=markdownText(source),pos=Array.from(text).join('').lastIndexOf('检查');
 const start=Array.from(text.slice(0,pos)).length;const html=renderAnnotations(source,text,[span(text,start,start+2)]);
 assert.match(html,/<strong>检查<\/strong>/);assert.equal((html.match(/class="annotation-mark/g)||[]).length,1);assert.match(html,/>检查<\/span>/);assert.match(html,/href="https:\/\/example.org"/);assert.match(html,/next/);
});
test('lists, nested Markdown and line breaks keep exact display ranges',()=>{
 const source='1. **Første**\n2. 第二\n\nlast\nline';const text=markdownText(source),p=Array.from(text).indexOf('第');
 const html=renderAnnotations(source,text,[span(text,p,p+2,'Object')]);assert.match(html,/<ol>/);assert.match(html,/<strong>Første<\/strong>/);assert.match(html,/>第二<\/span>/);assert.doesNotMatch(html,/cannot be mapped/);
});
test('nested spans keep inner field and outer relations, conflicting overlaps stay neutral',()=>{
 const text='A must check B';const a=span(text,0,text.length,'conditions'),b=span(text,7,12,'Main Verb','u2');
 assert.match(renderAnnotations(text,text,[a,b]),/annotation-outer semantic-4/);
 assert.match(renderAnnotations(text,text,[a,b]),/semantic-2/);
 const conflict=renderAnnotations(text,text,[b,{...b,field:'Object',unit_id:'u3'}]);assert.match(conflict,/semantic-overlap/);assert.match(conflict,/Overlapping references/);
});
test('stale/unmappable annotation never guesses a substring and source remains unchanged',()=>{
 const blocks=[{id:'b',type:'text',text:'same same',source_refs:[]}],before=JSON.stringify(blocks);const html=renderAnnotations('same same','same same',[span('changed',5,9)]);assert.match(html,/cannot be mapped reliably/);assert.doesNotMatch(html,/class="annotation-mark/);assert.equal(JSON.stringify(blocks),before);
});
test('draft checking chain retains gaps and never returns a site result',()=>{
 const fields={condition:{value:'after a storm',gaps:['Deadline not specified']},demand:{value:'must be checked',gaps:[]}};const logic=checkingLogic(fields);assert.equal(logic.steps[1].description,'after a storm');assert.ok(logic.gaps.includes('Deadline not specified'));assert.equal(logic.executable,false);assert.doesNotMatch(JSON.stringify(logic),/integrity|within one day|Satisfied/);
});
