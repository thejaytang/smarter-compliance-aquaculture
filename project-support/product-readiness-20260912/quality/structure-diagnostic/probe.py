"""Read frozen development evidence through existing pure structure primitives."""
from pathlib import Path
from dataclasses import asdict
from collections import Counter
import json,re
from pdf_extraction.types import NativePage,NativeObject,LayoutRegion,PixelBox
from pdf_extraction.domains.requirements.hierarchy import learn_requirement_hierarchy_profile
from pdf_extraction.layout.marginals import detect_repeating_marginals
from pdf_extraction.layout.reading_order import repair_fragmented_column_runs
from pdf_extraction.routing.text_layer import _merge_adjacent_line_fragments
from pdf_extraction.assemble.paragraph_assembler import _score
from pdf_extraction.models import Block,BlockType,Segment,BoundingBox,TextContent,Resolution,Page

HERE=Path(__file__).resolve().parent
QUALITY=HERE.parent
manifest=json.loads((QUALITY/'manifest.json').read_text())
output=[]
for sample in manifest['samples']:
    if sample['split']=='reserved_do_not_parse' or not sample['path'].endswith('.pdf'):continue
    directory=QUALITY/'after-pdf'/sample['id']
    candidate=json.loads((directory/'candidate.json').read_text())
    pages=[]
    for path in sorted(directory.glob('pdf-native-*.json')):
        evidence=json.loads(path.read_text())
        for index,raw in zip(evidence['original_page_indices'],evidence['pages'],strict=True):
            raw['page_index']=index
            for key in ('words','text_lines','characters'):raw[key]=[NativeObject(**v) for v in raw[key]]
            pages.append(NativePage(**raw))
    profile=learn_requirement_hierarchy_profile(pages)
    marginals=detect_repeating_marginals(pages)
    diagnostic={'id':sample['id'],'existing_candidate_types':dict(Counter(b['type'] for b in candidate['blocks'])),'existing_native_heading_profile':profile.to_dict(),'repeating_marginals':{p:[asdict(a) for a in annotations] for p,annotations in marginals.items()},'page_experiments':[]}
    page_models={p.page_index:Page(page_index=p.page_index,width=p.width_points,height=p.height_points,rotation=0,image_ref='',native_text_coverage=0,image_coverage=0,page_kind='born_digital') for p in pages}
    for p in pages:
        blocks=[b for b in candidate['blocks'] if b['source_refs'][0].get('page_index')==p.page_index and b['type'] in {'text','table'}]
        text_blocks=[b for b in blocks if b['type']=='text']
        experiment={'page_index':p.page_index,'page_number':p.page_index+1,'marker_body_inversions':[],'existing_column_repair_changed':False,'line_fragment_merges':[],'existing_paragraph_score_pairs':[]}
        regions=[LayoutRegion(id=b['id'],label='paragraph' if b['type']=='text' else 'table',bbox=PixelBox(*[round(v) for v in b['source_refs'][0]['bbox']]),confidence=0,text=b['text']) for b in blocks]
        reordered=repair_fragmented_column_runs(regions,round(p.width_points))
        experiment['existing_column_repair_changed']=[r.id for r in reordered]!=[r.id for r in regions]
        for position,b in enumerate(text_blocks):
            if not re.fullmatch(r'(?:\d+(?:\.\d+)+|[a-z][.)])',b['text'].strip()):continue
            x0,y0,x1,y1=b['source_refs'][0]['bbox']
            for j,other in enumerate(text_blocks):
                if j>=position:continue
                bx0,by0,bx1,by1=other['source_refs'][0]['bbox']
                overlap=max(0,min(y1,by1)-max(y0,by0))/max(.1,min(y1-y0,by1-by0))
                if .7<=overlap and 0<bx0-x1<p.width_points*.15:
                    experiment['marker_body_inversions'].append({'marker':b['text'],'marker_id':b['id'],'marker_bbox':[x0,y0,x1,y1],'body':other['text'],'body_id':other['id'],'body_bbox':[bx0,by0,bx1,by1],'vertical_overlap_ratio':overlap})
        # Probe the existing fragment helper outside retained table geometry.
        table_boxes=[b['source_refs'][0]['bbox'] for b in blocks if b['type']=='table']
        lines=[line for line in p.text_lines if not any(x0<=line.bbox_points[0] and y0<=line.bbox_points[1] and x1>=line.bbox_points[2] and y1>=line.bbox_points[3] for x0,y0,x1,y1 in table_boxes)]
        for merged in _merge_adjacent_line_fragments(lines,p.width_points):
            x0,y0,x1,y1=merged.bbox_points
            members=[line for line in lines if x0<=line.bbox_points[0] and y0<=line.bbox_points[1] and x1>=line.bbox_points[2] and y1>=line.bbox_points[3]]
            if len(members)>1:experiment['line_fragment_merges'].append({'output':merged.text,'inputs':[line.text for line in members],'native_ids':[line.id for line in members]})
        models=[]
        for b in blocks:
            bbox=BoundingBox(**dict(zip(('x0','y0','x1','y1'),b['source_refs'][0]['bbox'],strict=True)))
            models.append(Block(id=b['id'],type=BlockType.PARAGRAPH if b['type']=='text' else BlockType.TABLE,segments=[Segment(id=b['id'],page_index=p.page_index,bbox=bbox)],content=TextContent(native_text=b['text'],resolved_text=b['text'],resolution=Resolution(selected_source='native',reason='diagnostic only',confidence=0))))
        for left,right in zip(models,models[1:]):
            if left.type!=BlockType.PARAGRAPH or right.type!=BlockType.PARAGRAPH:continue
            score=_score(left,right,page_models)
            if score>=.9:experiment['existing_paragraph_score_pairs'].append({'left':left.content.resolved_text,'right':right.content.resolved_text,'score':score,'left_id':left.id,'right_id':right.id})
        diagnostic['page_experiments'].append(experiment)
    output.append(diagnostic)
with (HERE/'results.json').open('x') as f:json.dump(output,f,ensure_ascii=False,indent=2)
for d in output:
    print(d['id'],'headings',len(d['existing_native_heading_profile']['headings']),'marginals',sum(map(len,d['repeating_marginals'].values())),'marker inversions',sum(len(p['marker_body_inversions']) for p in d['page_experiments']),'paragraph pairs',sum(len(p['existing_paragraph_score_pairs']) for p in d['page_experiments']),'column repair pages',sum(p['existing_column_repair_changed'] for p in d['page_experiments']))
    for h in d['existing_native_heading_profile']['headings']:print(' HEAD',h['page_number'],h['text'])
