import test from 'node:test';
import assert from 'node:assert/strict';
import {requirementComparison} from '../frontend/components/requirement-comparison.js';
import {previewMarkup} from '../frontend/components/global-settings.js';
const bundle=version=>({schema:`requirement-delivery/${version}`,actor:'shared',sessions:[{document:{id:'s1',revision:2,text:'Animals, including origin and destination.',units:{u1:{}},structures:{u1:{children:[{kind:'group',role:'Object',quantity:[1,2],relationship:{text:'including'},children:[{kind:'fragment',role:'Object',text:'<img src=x onerror=alert(1)>'},{kind:'reference',role:'subrequirement',target_id:'u2'}]}]}}}},{document:{id:'s2',revision:1,text:'Second source',units:{u2:{}}}}],interpretations:[]});
for(const version of [1,2,3,4])test(`Readable Requirement delivery ${version}`,()=>{
 const html=requirementComparison(bundle(version));
 assert.match(html,/Quantity \[1, 2\]/);assert.match(html,/Relationship: including/);assert.match(html,/Link|subrequirement → R2/);
 assert.match(html,/&lt;img/);assert.doesNotMatch(html,/<pre|<img/);
});
test('Full conflict preview renders both group quantities before choosing',()=>{
 const incoming=bundle(4);incoming.sessions[0].document.structures.u1.children[0].quantity=2;
 const html=previewMarkup({status:'preview',sender:'Ana Jokic',items:[],validation_errors:[],conflicts:[{current:bundle(3),incoming,reviewer:'Ana Jokic'}]});
 assert.match(html,/Quantity \[1, 2\]/);assert.match(html,/Quantity 2/);assert.match(html,/Keep this version/);assert.match(html,/Use imported version/);assert.doesNotMatch(html,/<pre/);
});
