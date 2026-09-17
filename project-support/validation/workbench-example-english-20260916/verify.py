from pathlib import Path
import json,sys,re,hashlib
sys.path.insert(0,'/private/tmp');from example_http import call
ROOT=Path.cwd();out=Path(__file__).parent;s=json.loads((out/'population.json').read_text());receipt=json.loads((out/'source-receipt.json').read_text());mid=receipt['material'].get('material',receipt['material'])['id']
def nodes(n):
 yield n
 for child in n.get('children',[]):yield from nodes(child)
checked=[]
for key,uid in s['units'].items():
 doc=call('/api/requirements/session?id='+s[key]['document']['id']);assert not doc.get('stale') and doc['phase']=='complete';unit=doc['units'][uid];tree=doc['structure_views'][uid]
 for n in nodes(tree):
  if n.get('kind')=='fragment':assert unit['text'][slice(*n['span'])]==n['text'],n
 assert not re.search('driftsjournalen|akvakulturanlegg|opplysninger|dødelighet|prøveuttak',json.dumps(doc,ensure_ascii=False))
 if key in ('R2','R4'):
  k=2 if key=='R2' else 5;assert any(n.get('quantity')==[k,k] and len(n['children'])==k for n in nodes(tree))
 if key=='R1':assert set(n['target_id'] for n in nodes(tree) if n['kind']=='reference')=={s['units'][k] for k in ('R2','R3','R4')}
 x=call('/api/interpretations?unit_id='+uid);assert x['revision']==1 and not x['stale'];assert x['material_id']==mid and x['unit_id']==uid
 assert len(x['fields'])==6 and all(f['value'] for f in x['fields'].values());assert not re.search('tatt inn|minst|driftsjournalen|akvakulturanlegg',json.dumps(x['fields']))
 checked.append(dict(entry=key,session=doc['id'],unit=uid,revision=doc['revision'],source_refs=len(doc['source_refs']),interpretation_revision=x['revision'],lineage=x['lineage']))
# Prior Norwegian source and annotations are still recoverable.
old=json.loads((ROOT/'project-support/workbench-example-adf10-20260916/population.json').read_text())
for k in ['R1','R2','R3','R4']:
 d=call('/api/requirements/session?id='+old[k]['document']['id']);assert 'driftsjournalen' in d['text']
report=dict(material=mid,snapshot=receipt['source']['snapshot_id'],entries=checked,prior_norwegian_preserved=True,english_json_unchanged=hashlib.sha256((ROOT/'workbench/examples/example.json').read_bytes()).hexdigest()==hashlib.sha256((ROOT/'project-support/workbench-example-adf10-20260916/inputs/example 1 2.json').read_bytes()).hexdigest())
assert report['english_json_unchanged'];(out/'verification.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='entries'}));print('Verified all 4 entries, source spans, groups, links and interpretations.')
