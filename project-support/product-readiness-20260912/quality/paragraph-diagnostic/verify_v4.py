from pathlib import Path
import json,re,hashlib,sys
from pdf_extraction.review.materials import validate_blocks
HERE=Path(__file__).resolve().parent;Q=HERE.parent;ROOT=HERE.parents[3]
mode=sys.argv[1] if len(sys.argv)>1 else 'after-v4-pdf'
report_name=sys.argv[2] if len(sys.argv)>2 else 'v4-verification.json'
manifest=json.loads((Q/'manifest.json').read_text());results=[]
for s in manifest['samples']:
 if s['split']=='reserved_do_not_parse' or not s['path'].endswith('.pdf'):continue
 before=json.loads((Q/'after-v3-pdf'/s['id']/'candidate.json').read_text());after=json.loads((Q/mode/s['id']/'candidate.json').read_text())
 evidence=json.loads((Q/mode/s['id']/'pdf-paragraph-groups.json').read_text())
 lookup={o['group_block_id']:o for o in evidence['groups']}
 flat=[f for b in after['blocks'] for f in lookup.get(b['id'],{'fragments':[b]})['fragments']]
 validate_blocks(after['blocks'],after['scope'])
 r={'id':s['id'],'original_sha256_unchanged':hashlib.sha256((ROOT/s['path']).read_bytes()).hexdigest()==s['sha256'],'before_blocks':len(before['blocks']),'after_blocks':len(after['blocks']),'groups':len(lookup),'all_original_fragment_payload_order_exact':flat==before['blocks'],'all_group_text_exact_newline_join':all(b['text']=='\n'.join(f['text'] for f in lookup[b['id']]['fragments']) for b in after['blocks'] if b['id'] in lookup),'all_group_refs_exact':all(b['source_refs']==[ref for f in lookup[b['id']]['fragments'] for ref in f['source_refs']] for b in after['blocks'] if b['id'] in lookup),'status_unchanged':after['status']==before['status'],'scope_fields_unchanged':all(after[k]==before[k] for k in ['scope','processed_scope','usable_scope','unprocessed_scope','unresolved']),'validator_pass':True}
 if s['id'] in {'asc-farm','asc-interpretation'}:
  gname='farm-standard-p028-p029' if s['id']=='asc-farm' else 'interpretation-manual-p019-p021'
  gp=ROOT/'system2/gold/requirements/annotations'/f'{gname}.json';gold=json.loads(gp.read_text())
  norm=lambda t:re.sub(r'\s+',' ',t).strip()
  r['engineering_annotation_sha256']=hashlib.sha256(gp.read_bytes()).hexdigest();r['checks']=[]
  for req in gold['requirements']:
   for kind,identity,text in [('formal',req['requirement_id'],req['normative_text'])]+[('clause',c['clause_id'],c['text']) for c in req['clauses']]:
    r['checks'].append({'kind':kind,'id':identity,'before_single_unit':any(norm(text) in norm(b['text']) for b in before['blocks']),'after_single_unit':any(norm(text) in norm(b['text']) for b in after['blocks'])})
 results.append(r)
 print(s['id'],r['before_blocks'],'->',r['after_blocks'],'groups',r['groups'],'invariants',all(v for k,v in r.items() if type(v)==bool))
 if r.get('checks'):
  for kind in ('formal','clause'):
   checks=[x for x in r['checks'] if x['kind']==kind];print(kind,sum(c['before_single_unit'] for c in checks),'->',sum(c['after_single_unit'] for c in checks),'/',len(checks))
with (HERE/report_name).open('x') as f:json.dump({'parser_sha256':hashlib.sha256((ROOT/'system2/src/pdf_extraction/orchestration/material_parser.py').read_bytes()).hexdigest(),'results':results},f,indent=2)
assert all(v for r in results for k,v in r.items() if type(v)==bool)
