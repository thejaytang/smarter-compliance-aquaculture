"""Geometry-only marker ordering experiment; never rewrites text or source refs."""
from pathlib import Path
from collections import defaultdict
import json,re

MARKER=re.compile(r'(?:\d+(?:\.\d+)+[.)]?|\d+[.)]|[a-z][.)]|[•●▪◦])')

def stabilize(blocks,page_width):
    positions={b['id']:i for i,b in enumerate(blocks)}
    proposals=defaultdict(list)
    tables=[b['source_refs'][0]['bbox'] for b in blocks if b['type']=='table']
    for marker in blocks:
        if marker['type']!='text' or not MARKER.fullmatch(marker['text'].strip()):continue
        mx0,my0,mx1,my1=marker['source_refs'][0]['bbox']
        matches=[]
        for body in blocks:
            if body['type']!='text' or body['id']==marker['id'] or not body['text'].strip() or MARKER.fullmatch(body['text'].strip()):continue
            if positions[body['id']]>=positions[marker['id']]:continue
            x0,y0,x1,y1=body['source_refs'][0]['bbox']
            gap=x0-mx1
            if not 0<=gap<=min(page_width*.12,max(18.,6*(y1-y0))):continue
            overlap=max(0.,min(my1,y1)-max(my0,y0))/max(.1,min(my1-my0,y1-y0))
            if overlap<.7:continue
            if any(tx0<=(mx0+mx1)/2<=tx1 and ty0<=(my0+my1)/2<=ty1 or tx0<=(x0+x1)/2<=tx1 and ty0<=(y0+y1)/2<=ty1 for tx0,ty0,tx1,ty1 in tables):continue
            intervening=blocks[positions[body['id']]+1:positions[marker['id']]]
            if any(b['type'] in {'table','image','heading'} for b in intervening):continue
            matches.append((gap,body,overlap))
        matches.sort(key=lambda x:x[0])
        if not matches or len(matches)>1 and matches[1][0]-matches[0][0]<1:continue
        gap,body,overlap=matches[0]
        proposals[body['id']].append((marker,gap,overlap))
    accepted={body:items[0] for body,items in proposals.items() if len(items)==1}
    moved={marker['id'] for marker,_,_ in accepted.values()}
    output=[];operations=[]
    for block in blocks:
        if block['id'] in moved:continue
        if block['id'] in accepted:
            marker,gap,overlap=accepted[block['id']]
            output.append(marker)
            operations.append({'operation':'marker_before_adjacent_same_row_text','marker_block_id':marker['id'],'body_block_id':block['id'],'horizontal_gap_points':gap,'vertical_overlap_ratio':overlap,'marker_source_refs':marker['source_refs'],'body_source_refs':block['source_refs']})
        output.append(block)
    return output,operations

if __name__=='__main__':
    HERE=Path(__file__).resolve().parent;Q=HERE.parent
    results=[]
    for sample in json.loads((Q/'manifest.json').read_text())['samples']:
        if sample['split']=='reserved_do_not_parse' or not sample['path'].endswith('.pdf'):continue
        d=Q/'after-pdf'/sample['id'];candidate=json.loads((d/'candidate.json').read_text());proposed=[];ops=[]
        for p in sorted(d.glob('pdf-native-*.json')):
            native=json.loads(p.read_text())
            for index,page in zip(native['original_page_indices'],native['pages'],strict=True):
                blocks=[b for b in candidate['blocks'] if b['source_refs'][0]['page_index']==index]
                ordered,changes=stabilize(blocks,page['width_points']);proposed.extend(ordered);ops.extend(changes)
        moved={op['marker_block_id'] for op in ops}
        results.append({'sample_id':sample['id'],'changes':ops,'proposed_order':[b['id'] for b in proposed],'block_payloads_preserved':{b['id']:b for b in proposed}=={b['id']:b for b in candidate['blocks']},'nonmoved_order_preserved':[b['id'] for b in proposed if b['id'] not in moved]==[b['id'] for b in candidate['blocks'] if b['id'] not in moved]})
        print(sample['id'],len(ops))
    relations=json.loads((HERE/'relation-subset-before.json').read_text())
    evaluated=[]
    for relation in relations['relations']:
        result=next(r for r in results if r['sample_id']==relation['sample_id'])
        operations={(op['marker_block_id'],op['body_block_id']) for op in result['changes']}
        paired=(relation['marker_id'],relation['body_id']) in operations
        evaluated.append({**relation,'pair_proposed':paired,'pass':paired==relation['expected_pair']})
    with (HERE/'stabilization-proposal.json').open('x') as f:json.dump({'results':results,'relation_subset':evaluated,'subset_passed':sum(r['pass'] for r in evaluated),'subset_denominator':len(evaluated)},f,indent=2)
    print('subset',sum(r['pass'] for r in evaluated),'/',len(evaluated))
