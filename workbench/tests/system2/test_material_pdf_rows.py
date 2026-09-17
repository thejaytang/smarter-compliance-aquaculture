from copy import deepcopy
from types import SimpleNamespace
from pdf_extraction.assemble.material_rows import join_source_rows


def block(i,text,box,page=2):
    return {'id':str(i),'type':'text','text':text,'numbering':'','level':1,'parent_id':None,
            'source_refs':[{'page_index':page,'page':page+1,'scope_id':f'page:{page+1}','native_id':str(i),'bbox':box}]}


def run(blocks,source,images=(),lines=None):
    lines=lines or [SimpleNamespace(id=b['source_refs'][0]['native_id'],text=b['text']) for b in blocks if b['type']=='text']
    return join_source_rows(blocks,595,source,lines,images)


def test_source_exact_row_restores_condition_despite_different_glyph_heights():
    items=[block(0,'If wild-caught brood',[72,420.24,170,430.58]),
           block(1,'stock is used, it shall originate',[176,420.37,331,430.58]),
           block(2,'from a fishery',[337,420.24,400,428.40])]
    before=deepcopy(items);source='If wild-caught brood stock is used, it shall originate from a fishery'
    rows,evidence=run(items,source)
    assert len(rows)==1 and rows[0]['text']==source
    assert evidence[0]['fragments']==before and items==before
    assert rows[0]['source_refs'][0]['bbox']==[72,420.24,400,430.58]
    assert rows[0]['source_refs'][1:]==[b['source_refs'][0] for b in before]
    original_lines=[SimpleNamespace(id=b['source_refs'][0]['native_id'],text=b['text']) for b in before]
    assert run(rows,source,lines=original_lines)==(rows,[])


def test_joiner_is_read_from_source_including_no_space_inside_a_word():
    items=[block(0,'Aqua',[10,20,35,30]),block(1,'culture',[35.2,20,66,30])]
    rows,_=run(items,'Aquaculture')
    assert rows[0]['text']=='Aquaculture'
    rows,_=run(items,'Aqua culture')
    assert rows[0]['text']=='Aqua culture'


def test_unrepresented_source_content_is_never_deleted_to_make_a_row():
    items=[block(0,'shall',[10,20,35,30]),block(1,'discharge',[40,20,90,30])]
    assert run(items,'shall not discharge')==(items,[])


def test_adjacent_source_index_is_required_even_for_nearby_boxes():
    items=[block(0,'shall',[10,20,35,30]),block(2,'discharge',[40,20,90,30])]
    lines=[SimpleNamespace(id='0',text='shall'),SimpleNamespace(id='1',text='not'),SimpleNamespace(id='2',text='discharge')]
    assert run(items,'shall not discharge',lines=lines)==(items,[])


def test_different_rows_columns_pages_and_overlapping_layers_stay_separate():
    for box,page in [([10,40,60,50],2),([200,20,260,30],2),([40,20,90,30],3),([20,20,80,30],2)]:
        items=[block(0,'left content',[10,20,35,30]),block(1,'right content',box,page)]
        assert run(items,'left content right content')==(items,[])


def test_table_image_and_marker_boundaries_are_not_joined():
    items=[block(0,'first',[10,20,35,30]),block(1,'second',[40,20,90,30])]
    assert run(items,'first second',images=[[36,10,39,40]])==(items,[])
    table={'id':'table','type':'table','source_refs':[{'bbox':[36,10,39,40]}]}
    assert run([table,*items],'first second')==([table,*items],[])
    marked=[block(0,'1.2',[10,20,35,30]),block(1,'Do this',[40,20,90,30])]
    assert run(marked,'1.2 Do this')==(marked,[])


def test_diagonal_chain_cannot_drift_into_another_line():
    items=[block(i,t,[10+30*i,20+3*i,35+30*i,30+3*i]) for i,t in enumerate(('one','two','three','four','five'))]
    rows,groups=run(items,'one two three four five')
    assert len(rows)>1
    assert 'one two three four five' not in [r['text'] for r in rows]


def _source_pdf(tmp_path):
    from io import BytesIO
    from hashlib import sha256
    from reportlab.pdfgen import canvas
    buffer=BytesIO();pdf=canvas.Canvas(buffer,pagesize=(595,842));pdf.setFont('Helvetica',11)
    x=72
    for value,offset in [('Facilities must',0),('not',.15),('discharge untreated water.',0)]:
        pdf.drawString(x,600+offset,value)
        x+=pdf.stringWidth(value,'Helvetica',11)+9
    pdf.showPage();pdf.drawString(72,600,'Retain this second page.');pdf.save()
    raw=buffer.getvalue();originals=tmp_path/'originals';originals.mkdir();(originals/'source.pdf').write_bytes(raw)
    source=dict(source_id='TS001',snapshot_id='TS001-001',relative_path='source.pdf',content_hash=sha256(raw).hexdigest(),file_format='pdf',operator_selection_decision='INCLUDE',selection_status='INCLUDE',snapshot_status='STORED',source_status='CURRENT',download_status='SUCCESS',registry_sha256='0'*64)
    return source,originals,raw


def test_real_pdf_candidate_restores_negation_row_with_reversible_source_evidence(tmp_path):
    import json
    from pdf_extraction.orchestration.material_parser import parse_material
    source,originals,raw=_source_pdf(tmp_path);out=tmp_path/'candidate'
    candidate=parse_material(source,originals,out)
    assert (originals/'source.pdf').read_bytes()==raw
    assert candidate['status']=='candidate_available' and candidate['requirement_status']=='not_connected'
    assert any(b['text']=='Facilities must not discharge untreated water.' for b in candidate['blocks'])
    evidence=json.loads((out/'pdf-source-row-groups.json').read_text())
    assert evidence['source_sha256']==source['content_hash']
    page=evidence['pages'][0];group,=page['groups']
    assert len(group['fragments'])==3
    native=json.loads((out/'pdf-native-0001.json').read_text())['pages'][0]['text_lines']
    for fragment,line in zip(group['fragments'],native):
        assert fragment['text']==line['text'].strip()
        assert fragment['source_refs'][0]['native_id']==line['id']
        assert fragment['source_refs'][0]['bbox']==line['bbox_points']
    start,end=group['normalized_native_interval']
    assert ' '.join(page['native_text'].split())[start:end]==group['source_text']
    assert any('Retain this second page.' in b['text'] for b in candidate['blocks'])


def test_original_order_read_failure_retains_positioned_text_and_visible_issue(tmp_path,monkeypatch):
    import json
    import pypdfium2 as pdfium
    from pdf_extraction.orchestration.material_parser import parse_material
    source,originals,raw=_source_pdf(tmp_path)
    real=pdfium.PdfTextPage.get_text_range
    def fail_complete(self,*args,**kwargs):
        if not args and not kwargs: raise RuntimeError('injected complete-order read failure')
        return real(self,*args,**kwargs)
    monkeypatch.setattr(pdfium.PdfTextPage,'get_text_range',fail_complete)
    out=tmp_path/'candidate';candidate=parse_material(source,originals,out)
    assert candidate['status']=='partial' and candidate['usable_scope']==['page:1','page:2']
    issues=[u for u in candidate['unresolved'] if u['code']=='source_row_evidence_unavailable']
    assert len(issues)==2 and all(u['message'] in candidate['warnings'] for u in issues)
    assert any(b['text']=='not' for b in candidate['blocks'])
    assert any('Retain this second page.' in b['text'] for b in candidate['blocks'])
    assert (originals/'source.pdf').read_bytes()==raw
    evidence=json.loads((out/issues[0]['evidence_ref']).read_text())
    assert all(p['native_text'] is None and p['groups']==[] and p['error_type']=='RuntimeError' for p in evidence['pages'])
