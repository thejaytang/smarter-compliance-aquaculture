import {test} from 'node:test';
import assert from 'node:assert/strict';
import {sourceCheckMarkup,wireSourceFindings} from '../frontend/components/source-check.js';

const report={stale:false,signals:{original_lines:3},elapsed_seconds:.01,findings:[{
 code:'source_occurrence_shortfall',severity:'major',source_text:'or,\nor,\nor,',page_index:18,
 bbox:[20,30,40,90],unit_ids:['merged'],evidence_origin:'poppler',
 occurrence_checks:[{token:'or',required_occurrences:3,matched_occurrences:1}],
 reverse_comparisons:[{output_text:'<not markup>'}],
}],unverified:[{code:'output_spatial_ownership_ambiguous',page_index:18,bbox:[20,30,400,50],unit_ids:['left','right'],basis:'Verify both columns.'},{code:'shared_extraction_engine',engine:'poppler'}]};

test('discrepancy evidence exposes occurrence counts and escapes compared text',()=>{
 const html=sourceCheckMarkup(report);
 assert.match(html,/3 occurrences in the original; 1 can be matched/);
 assert.match(html,/&lt;not markup&gt;/);
 assert.doesNotMatch(html,/<not markup>/);
 assert.match(html,/No calibrated accuracy score is available/);
});

test('located unverified scope offers original and each affected content item',()=>{
 const html=sourceCheckMarkup(report);
 assert.match(html,/data-source-scope-region="0"/);
 assert.doesNotMatch(html,/data-source-scope-region="1"/);
 const selected=[];
 const buttons=[0,1].map(i=>({dataset:{sourceScopeContent:'0',sourceScopeUnit:String(i)}}));
 const panel={querySelectorAll:selector=>selector==='[data-source-scope-content]'?buttons:[]};
 wireSourceFindings(panel,report,{select:item=>selected.push(item.id)});
 buttons.forEach(button=>button.onclick());
 assert.deepEqual(selected,['left','right']);
});

test('structure conflicts show claims and remain readable without a located region',()=>{
 const f={code:'output_table_cell_outside_grid',severity:'critical',page_index:18,unit_ids:['table'],
  evidence_origin:'output_structure_and_claimed_positions',basis:'Cell exceeds declared dimensions.',
  source_text:'INDICATOR',compared_structure:[{id:'cell',row:0,column:2,row_span:1,column_span:2}]};
 const html=sourceCheckMarkup({...report,findings:[f],stale:true});
 assert.match(html,/Row 1, column 3; spans 1 row\(s\) and 2 column\(s\)/);
 assert.match(html,/Cell exceeds declared dimensions/);
 assert.match(html,/Original region not located/);
 assert.doesNotMatch(html,/data-source-region=/);
 assert.match(html,/data-source-finding="0"/);
 assert.match(html,/Content, structure or the comparison method changed/);
});
