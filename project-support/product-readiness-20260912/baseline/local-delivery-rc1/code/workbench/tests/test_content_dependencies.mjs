import {test} from 'node:test';
import assert from 'node:assert/strict';
import {dependencyMarkup} from '../ui/extraction.js';

test('prerequisites expose safe navigation and do not claim approval',()=>{
 const html=dependencyMarkup([{unit_id:'x" onclick="bad',title:'<original>',available:true,scope:['whole parsed range'],reason:'<missing>'},{unit_id:'missing',title:'Missing source dependency',available:false,reason:'Repair required'}]);
 assert.match(html,/2 pending content checks/);
 assert.match(html,/whole parsed range/);
 assert.match(html,/&lt;original&gt;/);
 assert.match(html,/x&quot; onclick=&quot;bad/);
 assert.equal((html.match(/data-content-dependency=/g)||[]).length,1);
 assert.match(html,/Confirming this item alone does not complete them/);
 assert.equal(dependencyMarkup(), '');
});
