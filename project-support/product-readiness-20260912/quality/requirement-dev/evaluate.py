"""Reproduce both frozen development diagnostics without changing their inputs."""
from pathlib import Path
from copy import deepcopy
from collections import Counter
from datetime import datetime, timezone
import json,sys,hashlib
from pdf_extraction.domains.requirements.classification import propose,VERSION
from pdf_extraction.review.effective import resolve

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[3]


def structured(e):
    if 'table_oracle' not in e:return deepcopy(e['source_structured'])
    spec=e['table_oracle']
    owner=dict(id='source-table',kind='context',version=1,original=dict(fields={'body':json.dumps(spec['table'])},references=[],structure=[spec['table']]))
    selected=[c for c in spec['table']['cells'] if c['id'] in spec['selected_cell_ids']]
    row=dict(id='source-row',kind='source_table_row',version=1,dependencies=[owner['id']],original=dict(fields={},references=[dict(locator=c['id'],page_index=c['page_index'],bbox=c['bbox']) for c in selected],structure=selected))
    return resolve(row,{owner['id']:owner,row['id']:row})


def main():
    stage=sys.argv[1]; assert stage in ('before','after')
    target=OUT/(stage+'.json');assert not target.exists()
    freeze=json.loads((OUT/'freeze.json').read_text())
    for name,digest in freeze['artifacts'].items():assert hashlib.sha256((OUT/name).read_bytes()).hexdigest()==digest
    data=json.loads((OUT/'frozen-inventory.json').read_text());results=[]
    for e in data['examples']:
        for track,unit in [('text_only',deepcopy(e['text_only'])),('source_structure_oracle',structured(e))]:
            proposal=propose(unit)
            results.append(dict(id=e['id'],track=track,reference=e['reference'],prediction=proposal['classification'],proposal=proposal,input=unit))
    summary={track:{sample:{label:dict(Counter(r['prediction'] for r in results if r['track']==track and r['id'].startswith(sample+':') and r['reference']==label)) for label in ('requirement','context')} for sample in sorted({e['id'].split(':')[0] for e in data['examples']})} for track in ('text_only','source_structure_oracle')}
    result=dict(stage=stage,at=datetime.now(timezone.utc).isoformat(),method=VERSION,summary=summary,results=results,
                boundary='Historical engineering development diagnostics only. Correct source-unit assembly/ancestry/header roles supplied from source annotations are ORACLE assistance, not actual parser performance. Reserved windows excluded.')
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
