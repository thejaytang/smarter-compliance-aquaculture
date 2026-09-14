"""Source-based regression cases for truthful scope and HTML text boundaries."""
from hashlib import sha256
from io import BytesIO

from reportlab.pdfgen import canvas
import pytest

from pdf_extraction.contracts.source import Snapshot
from pdf_extraction.orchestration.material_parser import parse_material


def parse(tmp_path, name, raw):
    originals=tmp_path/'originals';originals.mkdir()
    (originals/name).write_bytes(raw)
    source=Snapshot(source_id='TS001',snapshot_id='TS001-001',relative_path=name,
        content_hash=sha256(raw).hexdigest(),file_format=name.rsplit('.',1)[1],
        operator_selection_decision='INCLUDE',selection_status='INCLUDE',snapshot_status='STORED',
        source_status='CURRENT',download_status='SUCCESS',registry_sha256='0'*64)
    result=parse_material(source,originals,tmp_path/'candidate')
    assert (originals/name).read_bytes()==raw
    return result


def test_html_breaks_preserve_boundaries_without_separating_inline_words(tmp_path):
    result=parse(tmp_path,'source.html',b'<html><body><p>It must<br>not exceed <b>5</b> mg. H<sub>2</sub>O.</p><p><span>A<br>B</span>C</p><table><tr><td>One<br>Two</td><td><p>First</p><p>Second</p></td></tr></table></body></html>')
    assert [b['text'] for b in result['blocks'] if b['type']=='text']==['It must\nnot exceed 5 mg. H2O.','A\nBC']
    assert next(b['table']['rows'] for b in result['blocks'] if b['type']=='table')==[['One\nTwo','First\nSecond']]


def test_nested_html_lists_do_not_join_or_duplicate_parent_child_text(tmp_path):
    result=parse(tmp_path,'source.html',b'<html><body><h1>Rules</h1><ul><li>Parent<br>condition<ul><li>Child <b>must</b> comply</li></ul>Parent tail</li></ul></body></html>')
    assert [b['text'] for b in result['blocks']]==['Rules','Parent\ncondition','Child must comply','Parent tail']
    assert all(b['source_refs'] for b in result['blocks'])


@pytest.mark.parametrize(('heading','expected'), [
    ('§ 13.Oppryddingsplikt','§ 13'),
    ('§ 13 a.Fellesansvar','§ 13 a'),
    ('§ 13a. Fellesansvar','§ 13a'),
    ('§\u00a013\u00a0a. Fellesansvar','§\u00a013\u00a0a'),
    ('§ 13 a','§ 13 a'),
    ('§ 13 avfall','§ 13'),
    ('§ 130. Next section','§ 130'),
    ('§ 13-1. Different numbering scheme',''),
    ('1.2.3 Scope','1.2.3'),
    ('Unnumbered title',''),
])
def test_html_section_numbering_preserves_suffix_and_source_text(tmp_path,heading,expected):
    result=parse(tmp_path,'source.html',f'<html><head><meta charset="utf-8"></head><body><h3>{heading}</h3><p>Do not exceed 5 mg unless exempt.</p></body></html>'.encode())
    block=next(b for b in result['blocks'] if b['type']=='heading')
    assert block['numbering']==expected
    assert block['text']==heading
    body=next(b for b in result['blocks'] if b['type']=='text')
    assert body['text']=='Do not exceed 5 mg unless exempt.'
    assert body['parent_id']==block['id'] and body['dependencies']==[block['id']]
    assert block['source_refs'] and body['source_refs']


def test_image_only_pdf_is_empty_with_original_and_unresolved_scope(tmp_path):
    from PIL import Image
    from reportlab.lib.utils import ImageReader
    buffer=BytesIO();c=canvas.Canvas(buffer)
    c.drawImage(ImageReader(Image.new('RGB',(100,100),'gray')),30,500,width=100,height=100);c.save()
    r=parse(tmp_path,'image.pdf',buffer.getvalue())
    assert r['status']=='empty'
    assert r['processed_scope']==['page:1'] and r['usable_scope']==[]
    assert r['unresolved'][0]['scope_id']=='page:1'
    assert r['unresolved'][0]['code']=='native_text_unavailable'
    assert any(b['type']=='image' and b['source_refs'][0]['page_index']==0 for b in r['blocks'])
    assert (tmp_path/'candidate'/'pdf-page-0001.png').is_file()


def test_mixed_native_blank_pdf_is_partial_with_processed_and_usable_scope(tmp_path):
    buffer=BytesIO();c=canvas.Canvas(buffer);c.drawString(30,700,'Must retain this text');c.showPage();c.showPage();c.save()
    r=parse(tmp_path,'mixed.pdf',buffer.getvalue())
    assert r['status']=='partial'
    assert r['processed_scope']==['page:1','page:2'] and r['usable_scope']==['page:1']
    assert r['unresolved'][0]['scope_id']=='page:2'
    assert any('Must retain' in b['text'] for b in r['blocks'])


def test_ruled_table_only_pdf_has_usable_content(tmp_path):
    buffer=BytesIO();c=canvas.Canvas(buffer)
    for x in (40,180,360):c.line(x,500,x,650)
    for y in (500,550,600,650):c.line(40,y,360,y)
    for x,y,text in [(50,620,'Item'),(190,620,'Limit'),(50,570,'A'),(190,570,'5 mg'),(50,520,'B'),(190,520,'7 mg')]:c.drawString(x,y,text)
    c.save();r=parse(tmp_path,'table.pdf',buffer.getvalue())
    assert r['status']=='candidate_available' and r['usable_scope']==['page:1']
    assert r['unresolved']==[]
    assert any('5 mg' in v for b in r['blocks'] for row in b.get('table',{}).get('rows',[]) for v in row)


def test_material_pdf_route_does_not_import_docling(tmp_path,monkeypatch):
    from pdf_extraction.ingest.native_extractor import NativeExtractor
    calls=[]
    def unexpected(self,path):calls.append(path);raise RuntimeError('heavy backend must not start')
    monkeypatch.setattr(NativeExtractor,'_extract_docling',unexpected)
    buffer=BytesIO();c=canvas.Canvas(buffer);c.drawString(30,700,'Native text');c.save()
    r=parse(tmp_path,'native.pdf',buffer.getvalue())
    assert r['status']=='candidate_available'
    assert calls==[]


def order_block(identity, text, box, kind='text'):
    return {'id':identity,'type':kind,'text':text,'source_refs':[{'page_index':0,'scope_id':'page:1','bbox':box}]}


def test_marker_order_keeps_exact_payload_and_nonmarker_order():
    from copy import deepcopy
    from pdf_extraction.orchestration.material_parser import _stabilize_marker_order
    body=order_block('body','The site shall retain 5 mg.',[118,100,300,110])
    marker=order_block('marker','1.4.1',[54,102,82,112])
    tail=order_block('tail','Following paragraph.',[54,140,300,150])
    original=[body,marker,tail];before=deepcopy(original)
    ordered,ops=_stabilize_marker_order(original,600)
    assert [b['id'] for b in ordered]==['marker','body','tail']
    assert original==before and {b['id']:b for b in ordered}=={b['id']:b for b in before}
    assert len(ops)==1 and ops[0]['marker_source_refs']==marker['source_refs']
    assert _stabilize_marker_order(ordered,600)==(ordered,[])


def test_marker_pairing_keeps_two_column_body_order():
    from pdf_extraction.orchestration.material_parser import _stabilize_marker_order
    left=order_block('left','Left column body',[90,100,240,110])
    right=order_block('right','Right column body',[370,100,540,110])
    a=order_block('a','a.',[70,102,78,112]);b=order_block('b','b.',[350,102,358,112])
    ordered,ops=_stabilize_marker_order([left,right,a,b],600)
    assert [x['id'] for x in ordered]==['a','left','b','right']
    assert [(op['marker_block_id'],op['body_block_id']) for op in ops]==[('a','left'),('b','right')]


@pytest.mark.parametrize('case', ['distant_column','different_row','ambiguous_body','table_boundary','bare_number'])
def test_marker_pairing_abstains_at_unsupported_boundaries(case):
    from pdf_extraction.orchestration.material_parser import _stabilize_marker_order
    body=order_block('body','Must preserve this content',[118,100,300,110])
    marker=order_block('marker','1.4.1',[54,102,82,112])
    blocks=[body,marker]
    if case=='distant_column':body['source_refs'][0]['bbox']=[370,100,540,110]
    elif case=='different_row':marker['source_refs'][0]['bbox']=[54,120,82,130]
    elif case=='ambiguous_body':blocks.insert(1,order_block('duplicate','Another text layer',[118,100,300,110]))
    elif case=='table_boundary':blocks.insert(1,order_block('table','',[100,100,310,110],'table'))
    elif case=='bare_number':marker['text']='5'
    assert _stabilize_marker_order(blocks,600)==(blocks,[])


def test_paragraph_grouping_retains_numbering_critical_text_and_every_original_fragment():
    from copy import deepcopy
    from pdf_extraction.orchestration.material_parser import _group_pdf_paragraphs
    blocks=[order_block('marker','1.2.3',[50,122,80,132]),
            order_block('body','The concentration must not exceed 5 mg unless non-',[100,120,540,132]),
            order_block('tail','conforming feed is present.',[100,136,320,148]),
            order_block('next-marker','1.2.4',[50,172,80,182]),
            order_block('next','A separate obligation.',[100,170,340,182])]
    before=deepcopy(blocks)
    groups,ops=_group_pdf_paragraphs(blocks,600,800)
    assert len(groups)==2 and groups[0]['numbering']=='1.2.3'
    assert groups[0]['text']=='1.2.3\nThe concentration must not exceed 5 mg unless non-\nconforming feed is present.'
    assert groups[0]['source_refs']==[r for b in blocks[:3] for r in b['source_refs']]
    assert [b for op in ops for b in op['fragments']]==before and blocks==before
    assert _group_pdf_paragraphs(blocks,600,800)==(groups,ops)


@pytest.mark.parametrize('boundary',['sentence','gap','column','page','table','image','heading','margin','header_role','inline_marker','separate_marker','image_geometry','short_labels'])
def test_paragraph_grouping_does_not_cross_independent_boundaries(boundary):
    from pdf_extraction.orchestration.material_parser import _group_pdf_paragraphs
    left=order_block('left','An incomplete paragraph with sufficient words',[80,120,300,132])
    right=order_block('right','continued content',[80,136,300,148])
    blocks=[left,right];images=[]
    if boundary=='sentence':left['text']='A separately completed paragraph ends here.'
    elif boundary=='short_labels':left['text']='Combined category';right['text']='Item'
    elif boundary=='gap':right['source_refs'][0]['bbox']=[80,180,300,192]
    elif boundary=='column':right['source_refs'][0]['bbox']=[360,136,540,148]
    elif boundary=='page':right['source_refs'][0]['page_index']=1
    elif boundary in {'table','image','heading'}:blocks.insert(1,order_block('barrier','Boundary',[80,133,300,135],boundary))
    elif boundary=='margin':
        left['source_refs'][0]['bbox']=[80,720,300,732];right['source_refs'][0]['bbox']=[80,736,300,748]
    elif boundary=='header_role':left['role']='header'
    elif boundary=='inline_marker':right['text']='a. Separate numbered paragraph'
    elif boundary=='separate_marker':right['text']='a.'
    elif boundary=='image_geometry':images=[[90,133,180,135]]
    assert _group_pdf_paragraphs(blocks,600,800,images)==(blocks,[])


def test_pdf_group_artifact_round_trips_fragments_and_candidate_validates(tmp_path):
    import json
    from pdf_extraction.review.materials import validate_blocks
    buffer=BytesIO();c=canvas.Canvas(buffer,pagesize=(600,800))
    c.drawString(50,680,'1.2.3');c.drawString(100,680,'The site must not exceed 5 mg unless')
    c.drawString(100,664,'an approved exception applies.');c.save()
    result=parse(tmp_path,'grouped.pdf',buffer.getvalue())
    candidate=next(b for b in result['blocks'] if b['numbering']=='1.2.3')
    evidence=json.loads((tmp_path/'candidate'/'pdf-paragraph-groups.json').read_text())
    operation=next(g for g in evidence['groups'] if g['group_block_id']==candidate['id'])
    assert 'not exceed 5 mg unless\nan approved exception applies.' in candidate['text']
    assert candidate['source_refs']==[r for f in operation['fragments'] for r in f['source_refs']]
    validate_blocks(result['blocks'],result['scope'])
