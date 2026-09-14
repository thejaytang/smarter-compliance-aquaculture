"""Product /7 DEV regression; frozen references remain read-only."""
from pathlib import Path
from hashlib import sha256
from collections import Counter
from datetime import datetime, timezone
import importlib.util,json,subprocess,sys
ROOT=Path.cwd();HERE=Path(__file__).resolve().parent;Q=HERE.parents[1];OUT=HERE/'product-v7';OUT.mkdir(exist_ok=False)
read=lambda p:json.loads(p.read_text());norm=lambda t:' '.join(t.split())
def sha(p):return sha256(p.read_bytes()).hexdigest()
def save(p,v):
    with p.open('x') as f:json.dump(v,f,ensure_ascii=False,indent=2)
def text(b):return '\n'.join('\n'.join(row) for row in b['table']['rows']) if b['type']=='table' else b.get('text','')
def pages(b):return {r['page_index'] for r in b.get('source_refs',[]) if 'page_index' in r}
def primitives(directory,c):
    lookup={g['group_block_id']:g['fragments'] for g in read(directory/'pdf-paragraph-groups.json')['groups']}
    path=directory/'pdf-source-row-groups.json'
    if path.exists():lookup.update({g['row_block_id']:g['fragments'] for p in read(path)['pages'] for g in p['groups']})
    def flatten(b):return [v for f in lookup[b['id']] for v in flatten(f)] if b['id'] in lookup else [b]
    return Counter(json.dumps(b,sort_keys=True) for top in c['blocks'] for b in flatten(top))
manifest=read(Q/'manifest.json');samples=[s for s in manifest['samples'] if s.get('page_indices') is not None and s['id']!='pa057-reserved']
files=[ROOT/'system2/src/pdf_extraction/orchestration/material_parser.py',ROOT/'system2/src/pdf_extraction/assemble/material_rows.py',Q/'manifest.json',Q/'verification-after-v4/measure_frozen_windows.py']+list((ROOT/'system2/tests').glob('test_material*.py'))
files += [ROOT/s['path'] for s in samples]+[ROOT/s['annotation']['path'] for s in samples if 'path' in s['annotation']]
ann=Q/'verification-annotations/cs010-reserved-source-annotation.json';files.append(ann)
freeze={str(p.relative_to(ROOT)):sha(p) for p in files};save(OUT/'freeze.json',{'started_at':datetime.now(timezone.utc).isoformat(),'files':freeze,'classification':'DEV/mechanism regression, including promoted CS010; not independent verification'})
for s in samples:assert sha(ROOT/s['path'])==s['sha256']
from pdf_extraction.orchestration.material_parser import parse_material,VERSION
spec=importlib.util.spec_from_file_location('fixed_assessor',Q/'verification-after-v4/measure_frozen_windows.py');assessor=importlib.util.module_from_spec(spec);spec.loader.exec_module(assessor)
ref=read(Q/'structure-diagnostic/grid-consistency/fallback-experiment/outputs/freeze.json')['reference_denominators']
ref={r['sample']:r for r in ref}
results=[]
for s in samples:
    path=ROOT/s['path'];sid=s['engineering_source_id'];src=dict(source_id=sid,snapshot_id=sid+'-001',relative_path=path.name,content_hash=s['sha256'],file_format='pdf',operator_selection_decision='INCLUDE',selection_status='INCLUDE',snapshot_status='STORED',source_status='CURRENT',download_status='SUCCESS',registry_sha256='0'*64)
    directory=OUT/s['id'];c=parse_material(src,path.parent,directory,page_indices=s['page_indices'])
    before_dir=HERE/'trial2/before'/s['id'];before=read(before_dir/'candidate.json');experiment=read(HERE/'trial2/experiment'/s['id']/'candidate.json')
    row_evidence=read(directory/'pdf-source-row-groups.json');groups=[g for p in row_evidence['pages'] for g in p['groups']]
    r={'id':s['id'],'status':c['status'],'blocks_before':len(before['blocks']),'blocks_after':len(c['blocks']),'joined_rows':len(groups),'member_fragments':sum(len(g['fragments']) for g in groups),'primitives_exact':primitives(directory,c)==primitives(before_dir,before),'experiment_blocks_exact':c['blocks']==experiment['blocks'],'tables_exact':[b for b in c['blocks'] if b['type']=='table']==[b for b in before['blocks'] if b['type']=='table']}
    assert r['primitives_exact'] and r['experiment_blocks_exact'] and r['tables_exact'],r
    for page in row_evidence['pages']:
        for group in page['groups']:
            a,b=group['normalized_native_interval'];assert norm(page['native_text'])[a:b]==group['source_text']
    for n in before_dir.glob('pdf-native-*.json'):
        assert read(n)['pages']==read(directory/n.name)['pages']
    if s['id'] in ref:
        annotation=read(ROOT/s['annotation']['path']);comparisons={}
        for tag,candidate in [('before',before),('after',c)]:
            bypage={p:norm('\n'.join(text(b) for b in candidate['blocks'] if p in pages(b))) for p in s['page_indices']}
            segments=[{'id':seg['segment_id'],'matched':norm(seg['source_text']) in bypage[seg['page_index']]} for seg in annotation['segments']]
            critical=[{'id':v['id'],'status':('PASS' if any(norm(v['text']) in bypage[p] for p in v['expected_page_indices']) else 'FAIL') if v['expected_page_indices'] else 'UNMEASURED'} for v in ref[s['id']]['critical_phrases']]
            comparisons[tag]={'segments':segments,'critical':critical,'segment_summary':{'matched':sum(v['matched'] for v in segments),'denominator':len(segments)},'critical_summary':dict(Counter(v['status'] for v in critical))}
        r['fixed_dev_diagnostics']=comparisons
        r['lost_previous_segments']=[a['id'] for a,b in zip(comparisons['before']['segments'],comparisons['after']['segments']) if a['matched'] and not b['matched']]
        r['lost_previous_critical']=[a['id'] for a,b in zip(comparisons['before']['critical'],comparisons['after']['critical']) if a['status']=='PASS' and b['status']!='PASS']
        assert not r['lost_previous_segments'] and not r['lost_previous_critical']
    if s['id']=='cs010-reserved':
        m=assessor.assess(read(ann),c);save(OUT/'cs010-measurement.json',m)
        r.update(content=m['content_strata'],critical=m['critical_summary'],structure=m['structure_by_type'])
        bm=read(HERE/'trial2/before/cs010-measurement.json')
        r['lost_previous_units']=[a['unit_id'] for a,b in zip(bm['unit_results'],m['unit_results']) if a['normalized_full_containment'] and not b['normalized_full_containment']]
        assert not r['lost_previous_units']
    results.append(r);print(json.dumps({k:v for k,v in r.items() if k!='fixed_dev_diagnostics'}),flush=True)
command=[sys.executable,'-m','pytest',*[str(p.relative_to(ROOT)) for p in sorted((ROOT/'system2/tests').glob('test_material*.py'))],'-q','--junitxml='+str(OUT/'junit.xml')]
save(OUT/'test-command.json',command)
with (OUT/'tests.log').open('x') as log:completed=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=180)
unchanged={n:sha(ROOT/n)==h for n,h in freeze.items()}
save(OUT/'summary.json',{'parser_version':VERSION,'samples':results,'tests_exit_code':completed.returncode,'preservation':unchanged,'finished_at':datetime.now(timezone.utc).isoformat()})
assert completed.returncode==0 and all(unchanged.values())
