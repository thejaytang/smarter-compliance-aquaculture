import test from 'node:test';
import assert from 'node:assert/strict';
import {emptyDesign,setDesign,setHandoff,filterPreview,designMarkup,ruleMarkup,conceptIssues,designNode,ruleValue,bindDesign} from '../frontend/components/check-design.js';
test('unmapped groups remain explicit rather than invented filters',()=>{const d=emptyDesign();assert.equal(d.groups.scope,null);assert.match(designMarkup(d),/Empty groups remain unmapped/);assert.doesNotMatch(designMarkup(d),/Satisfied/);});
test('typed comparison inputs reject coercion and preserve lists',()=>{assert.equal(ruleValue('4','integer','greater_or_equal'),4);assert.throws(()=>ruleValue('','integer','equal'));assert.throws(()=>ruleValue('yes','boolean','equal'));assert.deepEqual(ruleValue('north\nsouth','string','in'),['north','south']);assert.equal(ruleValue('','string','is_null'),null);});
test('nested groups retain path ownership and escape source text',()=>{const d=emptyDesign();d.groups.scope={id:'g',condition:'OR',rules:[{id:'a',field:'table.kind',operator:'equal',type:'string',value:'<script>',interpretation_field:'scope'}]};assert.equal(designNode(d,'scope.0').id,'a');const markup=ruleMarkup(d,'scope');assert.match(markup,/any \(OR\)/);assert.match(markup,/&lt;script&gt;/);assert.doesNotMatch(markup,/<script>/);});

test('changing the value type clears obsolete validation errors on the value control',()=>{
 const d=emptyDesign();d.groups.scope={id:'g',condition:'AND',rules:[{id:'r',field:'staff.role',operator:'equal',type:'integer',value:'manager',interpretation_field:'scope'}]};
 const value={value:'manager',dataset:{rdProp:'value'},setCustomValidity(v){this.error=v;}};
 const type={value:'integer',dataset:{rdProp:'type'},setCustomValidity(v){this.error=v;}};
 const controls=[value,type],el={dataset:{rdPath:'scope.0'},querySelector:()=>value,querySelectorAll:()=>controls};controls.forEach(x=>x.closest=()=>el);
 const error={},preview={},host={querySelectorAll:s=>s==='[data-rd-prop]'?controls:[],querySelector:s=>s==='.rd-error'?error:preview};
 bindDesign(host,d,()=>{},()=>{});value.oninput();assert.match(value.error,/valid number/);
 type.value='string';type.oninput();assert.equal(value.error,'');assert.equal(d.groups.scope.rules[0].value,'manager');
});

test('unsupported OR and NOT predicates block the complete filter without dropping meaning',()=>{
 const d=setDesign(),comparison={id:'r',field:'component.kind',type:'string',operator:'equal',value:'chain',interpretation_field:'scope'};
 d.groups.scope={id:'g',condition:'OR',rules:[comparison,{id:'p',expression:'partOf some Anchor Line',interpretation_field:'scope'}]};
 assert.equal(filterPreview(d).scope,null);assert.match(JSON.stringify(d),/partOf some Anchor Line/);
 d.groups.scope.rules=[comparison];d.groups.scope.not=true;assert.equal(filterPreview(d).scope,null);
 d.groups.scope.not=false;assert.equal(filterPreview(d).scope.rules[0].value,'chain');
 d.groups.scope.rules=[];assert.equal(filterPreview(d).scope,null);
 const h=setHandoff({},d);assert.equal(h.sets.B.input,'A');assert.equal(h.sets.B.resolved,false);assert.equal(h.executable,false);
 assert.equal(h.mapping_status,'incomplete');assert.deepEqual(h.composition,{operator:'subset_of',left:'B',right:'C'});
});
