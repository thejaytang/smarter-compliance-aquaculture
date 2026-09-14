"""Run the frozen HTML completion corpus without scanning, fetching, or source writes."""
import argparse
from hashlib import sha256
import json,time
from pathlib import Path
from pdf_extraction.contracts.source import Snapshot
from pdf_extraction.contracts.html import HtmlDocument
from pdf_extraction.intake.registry import read_registry,build_manifest
from pdf_extraction.orchestration.source_batch import run_item,write_json


def check_windows(document,windows):
    # Assertions are literal source expectations selected before running holdouts.
    nodes={n.id:n for n in document.nodes};children={n.id:[] for n in document.nodes};text={n.id:[] for n in document.nodes}
    for n in document.nodes:
        if n.parent_id in children:children[n.parent_id].append(n.id)
    for a in document.atoms:text[a.node_id].append(a.text)
    def content(nid):
        # Source raw atom order gives the accurate mixed-inline ordering.
        descendants={nid};stack=[nid]
        while stack:
            for child in children[stack.pop()]:descendants.add(child);stack.append(child)
        return ' '.join(' '.join(a.text for a in document.atoms if a.node_id in descendants).split())
    results=[]
    for w in windows:
        candidates=[n for n in document.nodes if n.kind==w['kind'] or (w['kind']=='navigation' and n.role=='navigation')]
        matched=[]
        for n in candidates:
            if 'heading_level' in w and n.heading_level!=w['heading_level']:continue
            if 'cells' in w:
                values=[content(c) for c in children[n.id] if nodes[c].tag in ('td','th')]
                ok=values==w['cells']
            elif 'text' in w:ok=content(n.id)==w['text']
            else:ok=w['contains'] in content(n.id)
            if ok:matched.append(n.id)
        results.append({'window':w,'status':'passed' if matched else 'failed','node_ids':matched})
    return results


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--system1',type=Path,required=True)
    p.add_argument('--stage',choices=['development','holdout'],required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();manifest=json.loads(Path('tests/fixtures/html/source-manifest-20260907.json').read_text())
    records,digest=read_registry(args.system1/'Requirement_Source_Registry.xlsx')
    current=build_manifest(records,digest,args.system1/'Data',{x['source_id'] for x in manifest['items']})
    if current['rejected']:raise ValueError('frozen_source_no_longer_eligible')
    for frozen in manifest['items']:
        fresh=next(x for x in current['items'] if x['source_id']==frozen['source_id'])
        if any(v!=fresh.get(k) for k,v in frozen.items() if k!='registry_sha256'):
            raise ValueError('frozen_source_material_fields_changed:'+frozen['source_id'])
    if args.output.resolve().is_relative_to(args.system1.resolve()):raise ValueError('output_must_be_outside_system1')
    args.output.mkdir(parents=True,exist_ok=False)
    windows=json.loads(Path('tests/fixtures/html/source-windows-20260907.json').read_text())
    selected=set(manifest[args.stage+'_ids']); results=[]
    for item in current['items']:
        if item['source_id'] not in selected:continue
        start=time.perf_counter();s=Snapshot(**item);out=args.output/s.snapshot_id
        result=run_item(s,args.system1/'Data',out,{'template':'auto','encoding':'utf-8-sig'})
        record={'source':item,'status':result.status,'reason_codes':result.reason_codes,'seconds':round(time.perf_counter()-start,3)}
        if result.status=='review_required':
            d=HtmlDocument.model_validate_json((out/'canonical.json').read_text())
            v=json.loads((out/'verification.json').read_text());record['verification']=v
            checks=check_windows(d,[w for w in windows['windows'] if w['source_id']==s.source_id]);record['windows']=checks
            record['gate']='passed' if v['status']=='passed' and all(w['status']=='passed' for w in checks) else 'failed'
            record['counts']={'nodes':len(d.nodes),'atoms':len(d.atoms),'tables':len(d.tables),'cells':sum(len(t.cells) for t in d.tables),'lists':len(d.lists),'links':len(d.links)}
        else:
            expected=next((w for w in windows['negative_windows'] if w['source_id']==s.source_id),None)
            record['gate']='expected_input_rejection' if expected and any(expected['expected_reason'] in r for r in result.reason_codes) else 'requires_diagnosis'
        results.append(record);print(s.source_id,record['gate'],record['seconds'],flush=True)
    write_json(args.output/'validation-summary.json',{'stage':args.stage,'registry_sha256':digest,'frozen_registry_sha256':manifest['registry_sha256'],'frozen_source_fields_revalidated':True,'results':results})
    return int(any(r['gate'] not in ('passed','expected_input_rejection') for r in results))

if __name__=='__main__':raise SystemExit(main())
