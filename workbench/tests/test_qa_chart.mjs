import {test} from 'node:test';
import assert from 'node:assert/strict';
import {weeklyChart} from '../ui/qa-chart.js';
const weeks=['2026-08-10','2026-08-17','2026-08-24','2026-08-31','2026-09-07'];
const fixture=()=>({weeks,open_source_ids:[],series:['system1','system2','system3'].map(key=>({key,label:key,points:weeks.map(week=>({week,accuracy:100,correct:5,sampled:5,reviewed:5,status:'complete'}))}))});
test('three perfect five-week series occupy the same 100 percent line',()=>{
 const html=weeklyChart(fixture());
 const paths=[...html.matchAll(/<path d="([^"]+)"/g)].map(m=>m[1]);
 assert.equal(paths.length,3);assert.equal(new Set(paths).size,1);
 assert.equal((html.match(/5\/5 correct/g)||[]).length,33);
 assert.ok(!html.includes('No completed weekly checks yet'));
});
test('missing week breaks the line, without fabricating zero or completion',()=>{
 const data=fixture();data.series[0].points[2]={week:weeks[2],accuracy:null,reviewed:1,sampled:5,status:'pending'};
 const html=weeklyChart(data),path=html.match(/<path d="([^"]+)"/)[1];
 assert.equal((path.match(/M/g)||[]).length,2);
 assert.ok(html.includes('1/5 reviewed'));
});
