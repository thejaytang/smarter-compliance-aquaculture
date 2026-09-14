"""Freeze historical development source units, never reserved samples."""
from pathlib import Path
from copy import deepcopy
from datetime import datetime, timezone
import hashlib,json

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[3]
SAMPLES=['farm-standard-p028-p029','salmon-cod-standard-p018-v2','interpretation-manual-p019-p021']

def ref(s):return dict(locator=s['segment_id'],page_index=s['page_index'],bbox=s['bbox'])
def cell(s,row,col,span=1,header=False):
    return dict(id=s['segment_id'],row=row,column=col,row_span=1,column_span=span,is_header=header,
                page_index=s['page_index'],bbox=s['bbox'],content={'resolved_text':s['source_text']})


def main():
    target=OUT/'frozen-inventory.json';assert not target.exists()
    examples=[];provenance=[]
    for name in SAMPLES:
        path=ROOT/'system2/gold/requirements/annotations'/(name+'.json');d=json.loads(path.read_text())
        seg={s['segment_id']:s for s in d['segments']};seen=set()
        source=ROOT/'system2/data/inputs'/d['source']['file_name'];assert hashlib.sha256(source.read_bytes()).hexdigest()==d['source']['sha256']
        provenance.append(dict(annotation=str(path.relative_to(ROOT)),annotation_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                               source_sha256=d['source']['sha256'],page_numbers=d['sample']['page_numbers'],source_segment_count=len(seg),
                               trust='Historical source-backed engineering development annotations, not business Gold or independent validation.'))
        table=None
        if name.startswith('salmon-cod'):
            table=dict(row_count=5,column_count=3,cells=[cell(seg['p018-column-header-indicator'],0,0,2,True),cell(seg['p018-column-header-requirement'],0,2,1,True)])
            for row in range(1,5):
                for col,suffix in enumerate(['id','indicator','value']):table['cells'].append(cell(seg[f'p018-r{row}-{suffix}'],row,col))
        for r in d['requirements']:
            members=sorted((seg[sid] for sid in r['source_segment_ids']),key=lambda s:s['segment_order'])
            source_ids=[s['segment_id'] for s in members];assert not seen.intersection(source_ids);seen.update(source_ids)
            entry=dict(id=name+':'+r['requirement_id'],reference='requirement',source_segment_ids=source_ids,
                       text_only=dict(kind='source_text',fields={'body':'\n'.join(s['source_text'] for s in members)},references=[ref(s) for s in members]))
            entry['source_structured']=deepcopy(entry['text_only'])
            if table:
                entry['table_oracle']=dict(table=table,selected_cell_ids=source_ids,
                                           boundary='Header/row/cell positions assembled from frozen source annotation, not product parser output. Gold classification label never enters the resolver/classifier.')
            examples.append(entry)
        for s in d['segments']:
            if s['segment_id'] in seen:continue
            seen.add(s['segment_id'])
            entry=dict(id=name+':'+s['segment_id'],reference='context',source_segment_ids=[s['segment_id']],
                       text_only=dict(kind='source_text',fields={'body':s['source_text']},references=[ref(s)]))
            entry['source_structured']=deepcopy(entry['text_only'])
            if s['role'] in ('criterion_heading','header','footer'):
                entry['source_structured']['kind']='source_heading' if s['role']=='criterion_heading' else 'source_text'
            if s.get('continues_segment_id'):
                previous=seg[s['continues_segment_id']]
                literal='How do I interpret this requirement?'
                if previous['source_text'].startswith(literal):
                    entry['source_structured']['ancestors']=[dict(id=previous['segment_id'],type='heading',title=literal,version=1)]
                    entry['ancestry_oracle']='Explicit source continuation in frozen annotation supplies heading ancestry. This is not an independently recovered parser hierarchy.'
            examples.append(entry)
        assert seen==set(seg)
    frozen=dict(version='requirement-development-inventory/1',frozen_at=datetime.now(timezone.utc).isoformat(),samples=provenance,examples=examples,
                policy='Complete inventory of provided source segments: formal source groups are reference positives; every remaining source segment is context. Source labels are evaluation-only. Text-only and source-structure-assisted oracle tracks reported separately; never end-to-end quality. No reserved windows used.',
                uncertainty='Historical annotation inventories are complete over supplied segments, not newly proven page-complete negatives or business Gold. Cross-page source assembly remains oracle-supplied.')
    target.write_text(json.dumps(frozen,ensure_ascii=False,indent=2)+'\n')
    print('Examples',len(examples),'positive',sum(e['reference']=='requirement' for e in examples),'context',sum(e['reference']=='context' for e in examples))

if __name__=='__main__':main()
