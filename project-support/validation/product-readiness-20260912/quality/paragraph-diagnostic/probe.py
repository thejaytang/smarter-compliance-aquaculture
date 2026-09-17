"""DEV-only source-preserving grouping proposal, never a product parser or metric gate."""
from pathlib import Path
from collections import Counter
from copy import deepcopy
import json,re,hashlib
from pdf_extraction.models import Block,BlockType,Segment,BoundingBox,TextContent,Resolution,Page
from pdf_extraction.assemble.paragraph_assembler import _score
from pdf_extraction.types import NativePage,NativeObject
from pdf_extraction.domains.requirements.native_assembler import NativeRequirementAssembler
HERE=Path(__file__).resolve().parent; Q=HERE.parent
ROOT=Q.parents[2]
MARKER=re.compile(r'(?:\d+(?:\.\d+)+[.)]?|\d+[.)]|[a-z][.)]|[•●▪◦])')
def norm(s):return re.sub(r'\s+',' ',s).strip()
def ref(b):return b['source_refs'][0]
def model(b):
 r=ref(b)
 return Block(id=b['id'],type=BlockType.PARAGRAPH,segments=[Segment(id=b['id'],page_index=r['page_index'],bbox=BoundingBox(**dict(zip(('x0','y0','x1','y1'),r['bbox']))))],content=TextContent(native_text=b['text'],resolved_text=b['text'],resolution=Resolution(selected_source='native',reason='diagnostic',confidence=0)))
def grouping(blocks,pages):
 groups=[]; operations=[]; i=0
 while i<len(blocks):
  b=blocks[i]; members=[b]; number=None; i+=1
  if b['type']=='text' and MARKER.fullmatch(b['text'].strip()) and i<len(blocks):
   body=blocks[i]
   if body['type']=='text' and ref(body)['page_index']==ref(b)['page_index'] and not MARKER.fullmatch(body['text'].strip()):
    x,y,xx,yy=ref(b)['bbox']; a,c,aa,cc=ref(body)['bbox']
    overlap=max(0,min(yy,cc)-max(y,c))/max(.1,min(yy-y,cc-c))
    if overlap>=.7 and 0<=a-xx<=min(pages[ref(b)['page_index']].width*.12,max(18,6*(cc-c))):
     members.append(body); number=b['text'];i+=1
  if b['type']=='text' and (len(members)>1 or not MARKER.fullmatch(b['text'].strip())):
   while i<len(blocks):
    last=members[-1]; right=blocks[i]
    if right['type']!='text' or ref(right)['page_index']!=ref(last)['page_index'] or MARKER.fullmatch(right['text'].strip()):break
    # Reuse existing same-page geometry/punctuation score, preserve page/explicit-block barriers.
    if _score(model(last),model(right),pages)<.9:break
    members.append(right);i+=1
  groups.append({'type':b['type'],'text':'\n'.join(m.get('text','') for m in members),'numbering':number,'members':members})
  if len(members)>1:operations.append({'ids':[m['id'] for m in members],'numbering':number,'texts':[m['text'] for m in members]})
 return groups,operations
output=[]
for sid,gn in [('asc-farm','farm-standard-p028-p029'),('asc-interpretation','interpretation-manual-p019-p021')]:
 directory=Q/'after-v3-pdf'/sid
 cand=json.loads((directory/'candidate.json').read_text()); blocks=cand['blocks']; native=[]
 for p in sorted(directory.glob('pdf-native-*.json')):
  e=json.loads(p.read_text())
  for idx,raw in zip(e['original_page_indices'],e['pages']):
   raw['page_index']=idx
   for k in ('words','text_lines','characters'):raw[k]=[NativeObject(**w) for w in raw[k]]
   native.append(NativePage(**raw))
 pages={p.page_index:Page(page_index=p.page_index,width=p.width_points,height=p.height_points,rotation=0,image_ref='',native_text_coverage=0,image_coverage=0,page_kind='born_digital') for p in native}
 grouped,ops=grouping(blocks,pages)
 goldpath=ROOT/'system2/gold/requirements/annotations'/f'{gn}.json'; gold=json.loads(goldpath.read_text())
 checks=[]
 for req in gold['requirements']:
  # All formal normative text plus every annotated clause, predefined by existing active engineering annotations.
  for id_,text in [(req['requirement_id'],req['normative_text'])]+[(c['clause_id'],c['text']) for c in req['clauses']]:
   checks.append({'id':id_,'text':text,'before':any(norm(text) in norm(b.get('text','')) for b in blocks),'after':any(norm(text) in norm(g['text']) for g in grouped)})
 legacy=NativeRequirementAssembler().assemble(native,include_preceding_context=False)
 result={'id':sid,'gold_sha256':hashlib.sha256(goldpath.read_bytes()).hexdigest(),'before_blocks':len(blocks),'after_groups':len(grouped),'operations':ops,'checks':checks,'content_and_order_preserved':blocks==[m for g in grouped for m in g['members']],'groups':grouped,'legacy_formal_candidates':[r.to_dict() for r in legacy]}
 output.append(result)
 print(sid,'groups',len(blocks),'->',len(grouped),'checks',sum(c['before'] for c in checks),'->',sum(c['after'] for c in checks),'/',len(checks),'legacy',[r.requirement_id for r in legacy])
 for c in checks:
  if not c['after']:print(' FAIL',c['id'])
 for op in ops:print(' GROUP',op['numbering'],repr('\n'.join(op['texts'])[:140]))
with (HERE/'proposal-results.json').open('x') as f:json.dump(output,f,ensure_ascii=False,indent=2)
