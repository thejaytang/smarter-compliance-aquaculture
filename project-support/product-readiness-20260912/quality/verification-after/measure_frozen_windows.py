"""One-shot isolated measurement using a previously frozen matching policy.

Source annotations and product code are read-only. No fuzzy acceptance or repair.
"""
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import re
import xml.etree.ElementTree as ET

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[3]
ANN=OUT.parent/'verification-annotations'
def read(path):return json.loads(path.read_text())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(name,value):(OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def norm(text):return ' '.join(text.split())


def block_text(block):
    if block['type']=='table':return '\n'.join('\n'.join(row) for row in block['table']['rows'])
    return block.get('text','')


def page_of(block):
    return {ref['page_index']+1 for ref in block.get('source_refs',[]) if type(ref.get('page_index')) is int}


def original_lines(sample,page):
    stem=f'{sample}-p{page:03}'
    if sample.startswith('pa057'):
        tree=ET.parse(ANN/(stem+'.xhtml'))
        return [' '.join(w.text or '' for w in line.findall('{*}word')) for line in tree.findall('.//{*}line')]
    return (ANN/(stem+'.pdfium.txt')).read_text().splitlines()


def assess(annotation,candidate):
    units=annotation['units']; by_id={u['id']:u for u in units}
    pages={p:[b for b in candidate['blocks'] if p in page_of(b)] for p in annotation['scope']['page_numbers']}
    raw={p:'\n'.join(block_text(b) for b in blocks) for p,blocks in pages.items()}
    normalized={p:norm(text) for p,text in raw.items()}
    lines={p:original_lines(annotation['sample_id'],p) for p in pages}
    results=[]; matches={}; positions={}
    for u in units:
        p=u['page_number']; target=norm(u['text']); text=normalized[p]
        occurrences=[m.start() for m in re.finditer(re.escape(target),text)]
        positions[u['id']]=occurrences
        whole=[b for b in pages[p] if target in norm(block_text(b))]
        matches[u['id']]=whole
        fragments=[lines[p][i] for i in u['source_assistance_lines']] if u['source_assistance_lines'] else [u['text']]
        detail=[dict(text=norm(f),matched=norm(f) in text) for f in fragments]
        evidence=[dict(block_id=b['id'],type=b['type'],source_refs=b['source_refs']) for b in whole]
        results.append(dict(unit_id=u['id'],page_number=p,kind=u['kind'],visual_only=not bool(u['source_assistance_lines']),
                            strict_full_containment=u['text'] in raw[p],normalized_full_containment=target in text,
                            complete_occurrences=len(occurrences),fragments_matched=sum(d['matched'] for d in detail),
                            fragments_total=len(detail),all_fragments_present=all(d['matched'] for d in detail),
                            fragment_evidence=detail,single_block_evidence=evidence))
    critical=[]
    for u in units:
        for span in u['critical_spans']:
            target=norm(span['text']);p=u['page_number']
            evidence=[dict(block_id=b['id'],source_refs=b['source_refs']) for b in pages[p] if target in norm(block_text(b))]
            critical.append(dict(unit_id=u['id'],page_number=p,span=span,matched_on_source_page=target in normalized[p],
                                 single_block_evidence=evidence,association_verified=False))
    relations=[]
    def unique(identity):
        found=matches[identity]
        return found[0] if len(found)==1 else None
    def table_cells_match(specs):
        page=by_id[specs[0][0]]['page_number']
        return [b['id'] for b in pages[page] if b['type']=='table' and all(
            row<len(b['table']['rows']) and col<len(b['table']['rows'][row]) and norm(b['table']['rows'][row][col])==norm(by_id[identity]['text'])
            for identity,row,col in specs)]
    for rel in annotation['structural_relations']:
        kind=rel['kind'];status='FAIL';reason='Expected relation is not represented by uniquely matching product blocks.';evidence=[]
        if kind=='precedes':
            a,b=positions[rel['first']],positions[rel['second']]
            if len(a)==len(b)==1:
                status='PASS' if a[0]<b[0] else 'FAIL';reason='Same-page normalized complete text occurrence order.';evidence=[a[0],b[0]]
            elif len(a)>1 or len(b)>1:status='UNMEASURED';reason='Ambiguous repeated complete unit text.'
            else:reason='At least one complete unit is not contained in same-page ordered output.'
        elif kind in ('under_heading','heading_parent','list_member'):
            parent=unique(rel['parent']);child=unique(rel['child'])
            if parent and child:
                correct_type=kind=='list_member' or parent['type']=='heading'
                if correct_type and child.get('parent_id')==parent['id']:status='PASS';reason='Explicit matching parent_id.'
                evidence=[parent['id'],child['id']]
        elif kind=='note_attached_to_definition':
            parent=unique(rel['definition']);child=unique(rel['note'])
            if parent and child:
                if child.get('parent_id')==parent['id'] or parent['id'] in child.get('dependencies',[]):status='PASS';reason='Explicit note association.'
                evidence=[parent['id'],child['id']]
        elif kind=='table_cell_position':
            evidence=table_cells_match([(rel['unit'],rel['row'],rel['column'])]);status='PASS' if len(evidence)==1 else 'UNMEASURED' if len(evidence)>1 else 'FAIL';reason='Exact normalized text at expected row/column.'
        elif kind=='column_header':
            header=by_id[rel['header']]['table_cell'];cell=by_id[rel['cell']]['table_cell']
            evidence=table_cells_match([(rel['header'],header['row'],header['column']),(rel['cell'],cell['row'],cell['column'])]);status='PASS' if len(evidence)==1 else 'UNMEASURED' if len(evidence)>1 else 'FAIL';reason='Same product table has header-row and data-row cells at expected coordinates; visual header styling not verified.'
        relations.append(dict(relation=rel,status=status,reason=reason,evidence=evidence))
    strata={}
    for label,selection in [('all',results),('native_assisted',[r for r in results if not r['visual_only']]),('visual_only',[r for r in results if r['visual_only']])]:
        strata[label]=dict(denominator=len(selection),strict_full=sum(r['strict_full_containment'] for r in selection),
                           whitespace_normalized_full=sum(r['normalized_full_containment'] for r in selection),
                           all_source_fragments_present=sum(r['all_fragments_present'] for r in selection))
    return dict(sample_id=annotation['sample_id'],parser_version=candidate['parser_version'],candidate_status=candidate['status'],
                blocks=len(candidate['blocks']),block_types=dict(Counter(b['type'] for b in candidate['blocks'])),
                covered_scope=candidate['covered_scope'],unprocessed_scope=candidate['unprocessed_scope'],warnings=candidate['warnings'],unresolved=candidate['unresolved'],
                content_strata=strata,unit_results=results,critical_results=critical,
                critical_summary=dict(matched=sum(c['matched_on_source_page'] for c in critical),denominator=len(critical),association_accuracy='UNMEASURED'),
                structural_results=relations,structure_by_type={kind:dict(Counter(r['status'] for r in relations if r['relation']['kind']==kind)) for kind in sorted({r['relation']['kind'] for r in relations})},
                interpretation='Strict and whitespace-normalized containment and fragment coverage are separate source-text diagnostics. They do not certify extraction quality, full structure, business acceptance or independent all-history generalization.')


def main():
    assert not (OUT/'run-start.json').exists(),'One-shot frozen run; preserve prior evidence.'
    before=read(OUT/'measurement-freeze.json')
    for name,digest in before['measurement_files'].items():assert sha(OUT/name)==digest,(name,'measurement changed after freeze')
    freeze=read(ANN/'annotation-freeze.json')
    for name,digest in freeze['artifacts'].items():assert sha(ANN/name)==digest,(name,'annotation artifact changed')
    manifest=read(OUT.parent/'manifest.json'); samples={s['id']:s for s in manifest['samples']}
    code=ROOT/'system2/src/pdf_extraction/orchestration/material_parser.py'
    classifier=ROOT/'system2/src/pdf_extraction/domains/requirements/classification.py'
    started=dict(started_at=datetime.now(timezone.utc).isoformat(),parser_file_sha256=sha(code),classifier_file_sha256=sha(classifier),measurement_freeze_sha256=sha(OUT/'measurement-freeze.json'),annotation_freeze_sha256=sha(ANN/'annotation-freeze.json'))
    for identity in ('pa057-reserved','cs010-reserved'):assert sha(ROOT/samples[identity]['path'])==samples[identity]['sha256']
    save('run-start.json',started)
    from pdf_extraction.orchestration.material_parser import parse_material
    from pdf_extraction.domains.requirements.classification import propose
    all_results=[];oracle=[]
    for identity in ('pa057-reserved','cs010-reserved'):
        sample=samples[identity]; path=ROOT/sample['path'];sid=sample['engineering_source_id']
        source=dict(source_id=sid,snapshot_id=sid+'-001',relative_path=path.name,content_hash=sample['sha256'],file_format='pdf',
                    operator_selection_decision='INCLUDE',selection_status='INCLUDE',snapshot_status='STORED',source_status='CURRENT',download_status='SUCCESS',registry_sha256='0'*64)
        # Synthetic transport identity for an isolated source test, never a real
        # INCLUDE decision or a write to any business/material workflow store.
        candidate=parse_material(source,path.parent,OUT/identity,page_indices=sample['page_indices'])
        annotation=read(ANN/(identity+'-source-annotation.json'))
        result=assess(annotation,candidate);save(identity+'-measurement.json',result);all_results.append(result)
        by_id={u['id']:u for u in annotation['units']}; entries=[]
        for unit in annotation['requirement_evaluation_units']:
            refs=[dict(page_index=by_id[uid]['page_number']-1,bbox=by_id[uid]['bbox']) for uid in unit['content_unit_ids']]
            kind='source_heading' if all(by_id[uid]['kind']=='heading' for uid in unit['content_unit_ids']) else 'source_text'
            proposal=propose(dict(kind=kind,fields={'body':unit['text']},references=refs))
            entries.append(dict(id=unit['id'],reference=unit['classification'],proposal=proposal['classification'],method=proposal['method'],rule=proposal['rule'],content_unit_ids=unit['content_unit_ids']))
        matrix={label:dict(Counter(e['proposal'] for e in entries if e['reference']==label)) for label in sorted({e['reference'] for e in entries})}
        oracle.append(dict(sample_id=identity,reference_to_prediction=matrix,entries=entries,
                           boundary='Source-oracle unit diagnostic only. No product unit assembly or completeness tested; no end-to-end precision/recall claim. Zero positive reference means recall undefined; uncertain reference separately retained.'))
    save('oracle-classifier-diagnostic.json',oracle)
    save('summary.json',dict(samples=[{k:r[k] for k in ('sample_id','parser_version','candidate_status','blocks','block_types','content_strata','critical_summary','structure_by_type')} for r in all_results],
                              finished_at=datetime.now(timezone.utc).isoformat(),parser_file_unchanged=sha(code)==started['parser_file_sha256'],classifier_file_unchanged=sha(classifier)==started['classifier_file_sha256'],
                              source_inputs_unchanged=all(sha(ROOT/samples[i]['path'])==samples[i]['sha256'] for i in ('pa057-reserved','cs010-reserved')),
                              annotation_freeze_unchanged=sha(ANN/'annotation-freeze.json')==started['annotation_freeze_sha256']))
    print(json.dumps(read(OUT/'summary.json'),ensure_ascii=False,indent=2))
    print(json.dumps([dict(sample_id=o['sample_id'],matrix=o['reference_to_prediction']) for o in oracle],indent=2))

if __name__=='__main__':main()
