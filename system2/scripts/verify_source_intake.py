"""Bounded, read-only real-template comparison; run after the sample batch."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
from bs4 import BeautifulSoup
from pdf_extraction.formats.html_rules import clean

p=argparse.ArgumentParser()
p.add_argument('--system1',type=Path,required=True)
p.add_argument('--run',type=Path,required=True)
p.add_argument('--report',type=Path,required=True)
p.add_argument('--snapshot-id', action='append', help='Explicit snapshot IDs; defaults to the original two controls')
a=p.parse_args()
legacy=Path('Parser v1.py.txt')
ns={'__name__':'legacy_behavior_comparison'}
exec(compile(legacy.read_text(),str(legacy),'exec'),ns)
report={'legacy_sha256':sha256(legacy.read_bytes()).hexdigest(),'samples':[]}
for sid in a.snapshot_id or ['PA001-001','PA002-001']:
    canonical=json.loads((a.run/sid/'canonical.json').read_text())
    original=a.system1/'Data'/canonical['source']['relative_path']
    raw=original.read_bytes(); before=sha256(raw).hexdigest()
    assert before==canonical['source']['content_hash']
    old=ns['parse_file'](original)
    paras=[n for n in canonical['nodes'] if n['kind']=='paragraph']
    assert len(paras)==len(old['paragraphs'])
    diffs=[]
    for n,o in zip(paras,old['paragraphs']):
        comparable={k:v for k,v in n['data'].items() if k!='visible_text'}
        if comparable!=o:
            diffs.append({'id':o['paragraph_id'],'fields':[k for k in o if comparable.get(k)!=o[k]]})
    soup=BeautifulSoup(raw,'lxml')
    locator_checks=[]
    for n in canonical['nodes']:
        assert len(soup.select(n['locator']))==1
        if n['kind']=='paragraph':
            el=soup.select_one(n['locator'])
            assert n['data']['visible_text']==clean(el.get_text(' ',strip=True))
            locator_checks.append(n['id'])
    assert sha256(original.read_bytes()).hexdigest()==before
    report['samples'].append({'snapshot_id':sid,'source_sha256':before,
       'paragraphs':len(paras),'chapters':len(old['chapters']),
       'legacy_differences':diffs,'dom_text_checks':len(locator_checks),
       'issues':canonical['issues'], 'source_unchanged':True,
       'spot_checks':[{'paragraph_id':n['data']['paragraph_id'],'text':n['data']['text'][:500]} for n in paras[:2]]})
# All five raw legacy datasets are only in memory; no original files are written.
report['negative_control']=json.loads((a.run/'CS001-001'/'result.json').read_text())['reason_codes']
with a.report.open('x', encoding='utf-8') as stream:
    json.dump(report,stream,indent=2,ensure_ascii=False)
print(json.dumps({'samples':[{'snapshot_id':s['snapshot_id'], 'paragraphs':s['paragraphs'], 'legacy_differences':s['legacy_differences'], 'issue_count':len(s['issues'])} for s in report['samples']], 'negative_control':report['negative_control']},ensure_ascii=False))
