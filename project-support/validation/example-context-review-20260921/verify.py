"""Offline checks of the model-prepared full-law example and fresh API readback."""
from pathlib import Path
from hashlib import sha256
from itertools import product
import json,re
from bs4 import BeautifulSoup
HERE=Path(__file__).resolve().parent
def read(name):return json.loads((HERE/name).read_text())
m=read('full-law-material.json');recipe=read('full-law-review-recipe.json');docs=read('full-law-requirements.json');logic=read('full-law-interpretations.json');sources=read('full-law-source-readback.json');coverage=read('full-law-extraction-coverage.json')
original=BeautifulSoup((HERE/'PA015-original.html').read_bytes(),'html.parser')
normal=lambda text:re.sub(r'\s+','',text)
for record in coverage:
 element=original.select_one(record['locator'])
 assert element is not None and normal(element.get_text())==normal(record['text']),record['block_id']
body_elements=[element for section in original.select('#documentBody > div') for element in section.find_all(['h2','p','table'],recursive=False)]
covered_elements={id(original.select_one(c['locator'])) for c in coverage}
assert all(id(e) in covered_elements for e in body_elements)
blocks={b['id']:b for b in m['blocks']}
assert len(blocks)==85 and len(recipe)==len(docs)==len(logic)==35
assert sha256((HERE/'PA015-original.html').read_bytes()).hexdigest()==sources['PA015']['content_hash']==sources['PE002']['content_hash']
assert sources['PE002']['source_title']=='Example：Forskrift om bekjempelse av lakselus i akvakulturanlegg'
assert sources['PE002']['primary_source_id']=='PA015' and sources['PE002']['effective_selection']=='INCLUDE'
assert sources['PE001']['effective_selection']=='EXCLUDE'
assert not m['confirmation'] and m['checked_scope']==[]
assert {int(i.split('-')[0][1:]) for i in blocks if re.fullmatch(r's\d+-0',i)}==set(range(1,17))
covered={bid for e in recipe for bid in e['blocks']}
content={b['id'] for b in m['blocks'] if (b['id'].startswith('s') or b['id'].startswith('annex-')) and b['type']=='text' and not b['text'].startswith('0 ')}
assert not content-covered,content-covered
assert set(blocks)=={c['block_id'] for c in coverage if c['block_id']!='law-title' and not c['block_id'].startswith('meta-')}
for c in coverage:
 if c['block_id'] not in blocks:continue
 assert blocks[c['block_id']]['text']==c['text']
 assert blocks[c['block_id']]['source_refs'][0]['anchor']==c['anchor']
def walk(n):
 yield n
 for c in n.get('children',[]):yield from walk(c)
for e in recipe:
 d=docs[e['key']];v=logic[e['key']];uid=next(iter(d['units']));text='\n\n'.join(blocks[i]['text'] for i in e['blocks'])
 assert d['text']==text and d['material_id']==m['id'] and not d['stale']
 for n in walk(d['structures'][uid]):
  if n['kind']=='fragment':a,z=n['span'];assert text[a:z]==n['text']
  if n['kind']=='group':assert n['quantity'] is not None and n['children']
 assert not v['stale'] and not v['reviewed'] and v['session_revision']==d['revision']
 assert v['logic']['handoff']['mapping_status']=='incomplete' and not v['logic']['handoff']['executable']
 assert len(v['context']['materials'][0]['blocks'])==85
 citations={x['id']:x['text'] for x in v['context']['citations']}
 for f in v['fields'].values():
  for ref in f['references']:assert citations[ref['id']][ref['start']:ref['end']]==ref['quote']
 if e['demand'] is None:assert v['fields']['demand']['state']=='not_stated' and v['check_design']['groups']['demand'] is None
# Evaluate the saved Boolean tree on explicit synthetic facts, not a production site.
def evaluate(n,facts):
 if 'expression' in n:return facts[n['id']]
 values=[evaluate(r,facts) for r in n['rules']];value=all(values) if n['condition']=='AND' else any(values)
 return not value if n.get('not') else value
count=logic['counting']['check_design']['groups']['condition'];cases=[]
for temp,brood,slaughter in product((3.99,4.0,4.01),(False,True),(False,True)):
 actual=evaluate(count,{'count-slaughter':slaughter,'count-ge4':temp>=4,'count-lt4':temp<4,'count-broodstock':brood})
 expected=not slaughter and not (brood and temp<4)
 assert actual==expected
 cases.append(dict(temperature=temp,broodstock=brood,all_fish_slaughter_exemption=slaughter,applicable=actual))
# Weekly temperature duty has no borrowed counting threshold or exemption.
assert evaluate(logic['temperature']['check_design']['groups']['condition'],{'temp-no-trigger':True})
for key,numbers in [('limit-south',(16,21,22,15)),('limit-north',(21,26,27,20)),('annex-south',(14,21,22,13)),('annex-north',(19,26,27,18))]:
 text=logic[key]['fields']['condition']['value']
 assert all('week '+str(n) in text for n in numbers)
assert 'strictly below 0.2' in logic['limit-south']['fields']['demand']['value']
assert 'unweighted' in logic['annex-averages']['fields']['verification']['value']
assert '2013' in logic['transition']['fields']['condition']['value']
report=dict(blocks=85,document_information_fields=12,sections=16,annexes=1,entries=35,interpretations=35,statutory_body_blocks_covered=len(content),source_span_and_citation_checks='passed',original_html_character_coverage='passed',counting_boundary_cases=cases,human_review_completed=False,site_compliance_executed=False,unresolved_items={k:v['fields']['verification']['gaps'] for k,v in logic.items() if v['fields']['verification']['gaps']})
(HERE/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print('PASS: full-law coverage, source spans, citations, current bindings, pending human review, 12 counting boundary/exemption cases, regional periods and non-executable handoff.')
