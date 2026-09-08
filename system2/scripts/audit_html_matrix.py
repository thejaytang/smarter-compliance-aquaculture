"""Audit an explicitly selected, completed HTML batch against unchanged local snapshots.
No downloads, browser execution, source updates, PDF calls, or directory discovery.
"""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from pdf_extraction.contracts.source import HtmlStructure, Snapshot
from pdf_extraction.intake.registry import read_registry, read_snapshot
from pdf_extraction.orchestration.source_batch import write_json
from pdf_extraction.formats.html_rules import clean


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--system1',type=Path,required=True)
    parser.add_argument('--run',type=Path,required=True)
    parser.add_argument('--report',type=Path,required=True)
    args=parser.parse_args()
    records,digest=read_registry(args.system1/'Requirement_Source_Registry.xlsx')
    manifest=json.loads((args.run/'manifest.json').read_text())
    assert manifest['registry_sha256']==digest, 'registry_changed_since_batch'
    results=json.loads((args.run/'batch.json').read_text())['results']
    assert len(results)==len(manifest['items'])
    samples=[]
    for result in results:
        source=Snapshot(**result['source'])
        assert source.model_dump() in manifest['items']
        record=next(r for r in records if r['source_id']==source.source_id)
        raw=read_snapshot(source,args.system1/'Data')
        soup=BeautifulSoup(raw,'lxml')
        body=soup.select_one('#documentBody')
        main=soup.find('main') or soup.find('article') or soup.body
        region=body if body is not None else main
        region_text=clean(region.get_text(' ',strip=True)) if region is not None else ''
        hostname=urlparse(record.get('official_url') or '').hostname
        if body is not None:
            family='lovdata_empty_document_body' if not region_text else 'lovdata_statute'
        elif hostname and 'asc-aqua.org' in hostname:
            family='asc_programme_centre'
        elif hostname and 'fiskeridir.no' in hostname:
            family='fiskeridirektoratet_guide'
        elif hostname and 'miljodirektoratet.no' in hostname:
            family='miljodirektoratet_guidance'
        else:
            family='mattilsynet_guidance_or_hub'
        tables=region.find_all('table') if region is not None else []
        item={'source':source.model_dump(),'title':record.get('source_title'),'host':hostname,
              'family':family,'bytes':len(raw),'region_text_characters':len(region_text),
              'dom_paragraph_divs':len(region.select('div.paragraf')) if region is not None else 0,
              'dom_tables':len(tables),'status':result['status'],
              'failure_reasons':result['reason_codes'] if result['status']=='failed' else [],
              'region_excerpt':region_text[:300],
              'table_excerpts':[clean(t.get_text(' ',strip=True))[:300] for t in tables[:2]],
              'source_unchanged':True}
        if result['canonical_path']:
            p=args.run/source.snapshot_id/result['canonical_path']
            assert sha256(p.read_bytes()).hexdigest()==result['canonical_sha256']
            doc=HtmlStructure.model_validate_json(p.read_text())
            assert doc.source==source
            paragraphs=[n for n in doc.nodes if n.kind=='paragraph']
            assert len(paragraphs)==item['dom_paragraph_divs']
            ids={n.id for n in doc.nodes};assert len(ids)==len(doc.nodes)
            for n in doc.nodes:
                elements=soup.select(n.locator)
                assert len(elements)==1,(source.source_id,n.id)
                assert n.parent_id is None or n.parent_id in ids
                assert n.confidence is None and n.review_policy=='review_required'
                if n.kind=='paragraph':
                    assert n.data['visible_text']==clean(elements[0].get_text(' ',strip=True))
            examples=[]
            for issue in doc.issues:
                if issue.startswith('unrepresented_body_text:') and len(examples)<3:
                    locator=issue.split(':',1)[1]
                    elements=soup.select(locator); assert len(elements)==1
                    examples.append({'locator':locator,'text':clean(elements[0].get_text(' ',strip=True))[:220]})
            item.update(parser_version=doc.parser_version,canonical_paragraphs=len(paragraphs),
                        node_locator_checks=len(doc.nodes),paragraph_text_checks=len(paragraphs),
                        issue_counts=dict(Counter(i.split(':',1)[0] for i in doc.issues)),
                        issue_examples=examples,
                        explicit_table_nodes=sum(n.kind=='table' for n in doc.nodes))
        else:
            assert not (args.run/source.snapshot_id/'canonical.json').exists()
        samples.append(item)
        print(source.source_id,family,result['status'],flush=True)
    assert sha256((args.system1/'Requirement_Source_Registry.xlsx').read_bytes()).hexdigest()==digest
    for item in samples:
        read_snapshot(Snapshot(**item['source']),args.system1/'Data')
    report={'scope':'explicit existing HTML snapshots only; no PDF or network',
            'registry_sha256':digest,'samples':samples,'rejected':manifest['rejected'],
            'status_counts':dict(Counter(s['status'] for s in samples)),
            'family_counts':dict(Counter(s['family'] for s in samples)),
            'canonical_paragraph_total':sum(s.get('canonical_paragraphs',0) for s in samples),
            'limitation':'DOM checks demonstrate localization and supported structure consistency, not independent semantic or full-document completeness acceptance.'}
    write_json(args.report,report)

if __name__=='__main__':
    main()
