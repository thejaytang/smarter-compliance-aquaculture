from hashlib import sha256
import json
from pathlib import Path
import pytest
from bs4 import BeautifulSoup
from openpyxl import Workbook
from pdf_extraction.contracts.source import Snapshot, HtmlStructure
from pdf_extraction.intake.registry import build_manifest, read_registry, read_snapshot, IntakeError
from pdf_extraction.formats.html import parse_html, HtmlError
from pdf_extraction.formats.router import route_format, FormatError
from pdf_extraction.orchestration.source_batch import run_item

CONFIG = {'template':'lovdata-document-v1','encoding':'utf-8-sig','metadata':'#documentMeta','body':'#documentBody'}
HTML = b'''<html><body><div id="documentMeta"><h1>Example</h1><table class="meta"><tr><th>Dato</th><td>2026</td></tr></table></div><div id="documentBody"><div class="kapittel" id="k1"><h2>Chapter</h2><div class="paragraf" id="p1"><span class="paragrafValue">1</span><p>Fish must be inspected <a class="reference" data-id="lov/1">daily</a>.</p></div></div><div class="paragraf" id="p2"><p>Standalone.</p></div></div></body></html>'''

def source(raw=HTML, suffix='html'):
    return Snapshot(source_id='PA001', snapshot_id='PA001-001', relative_path=f'A/PA001-001_example.{suffix}',
                    content_hash=sha256(raw).hexdigest(), file_format=suffix, operator_selection_decision='INCLUDE',
                    selection_status='INCLUDE', snapshot_status='STORED', source_status='CURRENT',
                    download_status='SUCCESS', registry_sha256='a'*64)

def row(s):
    r=s.model_dump(); r.pop('registry_sha256'); r.pop('relative_path')
    return dict(r, folder_code='A',stored_filename=Path(s.relative_path).name)

def store(tmp, s, raw=HTML):
    p=tmp/s.relative_path; p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(raw)


def test_structure_deterministic_no_global_state_and_ancestry():
    a=parse_html(HTML,source(),CONFIG); b=parse_html(HTML,source(),CONFIG)
    assert a==b
    paragraphs=[n for n in a.nodes if n.kind=='paragraph']
    assert paragraphs[0].parent_id is not None and paragraphs[1].parent_id is None
    assert paragraphs[0].data['references'][0]['reference_id']=='lov/1'
    soup=BeautifulSoup(HTML,'lxml')
    assert all(len(soup.select(n.locator))==1 for n in a.nodes)
    assert all(n.confidence is None and n.review_policy=='review_required' for n in a.nodes)
    assert HtmlStructure.model_validate_json(a.model_dump_json())==a

@pytest.mark.parametrize('raw,reason',[(b'<html><body>Different</body></html>','template_mismatch'),
    (HTML.replace(b'Fish must',b'\xff must'),'decode_failed'),
    (HTML.replace(b'class="paragraf"',b'class="other"'),'empty_result'),
    (HTML.replace(b'class="kapittel"',b'class="kapittel" data-level="bad"'),'invalid_structure_level')])
def test_html_fails_explicitly(raw,reason):
    with pytest.raises(HtmlError,match=reason): parse_html(raw,source(raw),CONFIG)

@pytest.mark.parametrize('field,value', [('operator_selection_decision','EXCLUDE'),('selection_status',None),
 ('snapshot_status','MISSING'),('source_status','SUPERSEDED'),('download_status','FAILED')])
def test_ineligible_rows_never_read_snapshot(tmp_path,field,value):
    r=row(source()); r[field]=value
    result=build_manifest([r],'a'*64,tmp_path,{'PA001'})
    assert not result['items'] and result['rejected'][0]['fields']==[field]


def test_manifest_hash_and_selected_only(tmp_path):
    s=source(); store(tmp_path,s)
    r=row(s)
    result=build_manifest([r,dict(r,source_id='PA002')],'a'*64,tmp_path,{'PA001'})
    assert len(result['items'])==1
    (tmp_path/s.relative_path).write_bytes(b'changed')
    with pytest.raises(IntakeError,match='hash_mismatch'): read_snapshot(s,tmp_path)
    assert not build_manifest([r],'a'*64,tmp_path,{'PA001'})['items']

@pytest.mark.parametrize('folder,filename',[('../outside','x.html'),('/tmp','x.html'),('A','../../x.html')])
def test_unsafe_path_rejected(tmp_path,folder,filename):
    r=dict(row(source()),folder_code=folder,stored_filename=filename)
    assert not build_manifest([r],'a'*64,tmp_path,{'PA001'})['items']


def test_symlink_escape_rejected(tmp_path):
    root=tmp_path/'root'; root.mkdir(); (root/'A').symlink_to(tmp_path)
    with pytest.raises(IntakeError,match='outside'): read_snapshot(source(),root)

@pytest.mark.parametrize('path,declared,raw',[('x.pdf','pdf',HTML),('x.html','html',b'%PDF-1.7'),
    ('x.html','pdf',HTML),('x.xlsx','xlsx',b'PKxx'),('x.xls','xls',b'bad')])
def test_format_mismatches(path,declared,raw):
    with pytest.raises(FormatError): route_format(path,declared,raw)


def test_readonly_workbook_and_batch(tmp_path):
    s=source(); root=tmp_path/'sources'; store(root,s)
    r=row(s); path=tmp_path/'registry.xlsx'
    w=Workbook(); ws=w.active; ws.title='Source Register'; ws.append(['Display']); ws.append(list(r)); ws.append(list(r.values())); w.save(path)
    before=path.read_bytes(); records,digest=read_registry(path)
    manifest=build_manifest(records,digest,root,{'PA001'})
    item=Snapshot(**manifest['items'][0]); output=tmp_path/'run'
    result=run_item(item,root,output,CONFIG)
    assert result.status=='review_required' and path.read_bytes()==before
    canonical=json.loads((output/'canonical.json').read_text())
    assert canonical['source']['registry_sha256']==sha256(before).hexdigest()
    assert result.canonical_sha256==sha256((output/'canonical.json').read_bytes()).hexdigest()
    with pytest.raises(FileExistsError): run_item(item,root,output,CONFIG)
    with pytest.raises(ValueError,match='outside'): run_item(item,root,root/'run',CONFIG)


def test_excel_and_pdf_explicit_boundaries(tmp_path):
    raw=bytes.fromhex('d0cf11e0a1b11ae1')+b'dummy'; s=source(raw,'xls'); store(tmp_path/'s',s,raw)
    assert run_item(s,tmp_path/'s',tmp_path/'excel',CONFIG).status=='not_implemented'
    raw=b'%PDF-1.7'; s=source(raw,'pdf'); store(tmp_path/'s',s,raw)
    assert run_item(s,tmp_path/'s',tmp_path/'pdf',CONFIG).status=='blocked'


@pytest.mark.parametrize('quality,outcome,expected', [
    ('accepted','pass','review_required'), ('review_required','review','review_required'),
    ('failed','fail','failed'), ('accepted','fail','failed'), ('accepted',None,'failed'),
])
def test_pdf_adapter_preserves_pipeline_call_and_artifact(tmp_path,monkeypatch,quality,outcome,expected):
    import pdf_extraction
    from pdf_extraction.config import AppConfig
    from pdf_extraction.formats.pdf import parse_pdf
    raw=b'%PDF-1.7'; s=source(raw,'pdf'); store(tmp_path/'s',s,raw)
    cfg=AppConfig.from_yaml('config/pdf-intake-local.yaml')
    calls=[]
    def fake(path,output,config,*,page_indices):
        from tests.integration.test_scheme3 import _document
        from pdf_extraction.models import DocumentStatus
        calls.append((path.read_bytes(),page_indices))
        output.mkdir()
        document = _document(tmp_path)
        document.source.file_hash = s.content_hash
        document.quality.status = DocumentStatus(quality)
        (output/'canonical.json').write_text(document.model_dump_json())
        if outcome:
            (output/'verification-report.json').write_text(json.dumps({
                'document_id':document.document_id, 'depth':'source', 'outcome':outcome,
                'automatic_coverage':0, 'human_review_count':1,
            }))
    monkeypatch.setattr(pdf_extraction,'extract_pdf',fake)
    out=tmp_path/'out'; out.mkdir()
    result=parse_pdf(s,tmp_path/'s',out,cfg,{1})
    assert calls==[(raw,{1})] and result.canonical_path=='native/canonical.json'
    assert result.status == expected
    assert result.canonical_schema_version == '1.5'
    if outcome:
        assert result.verification_sha256 == sha256((out/result.verification_path).read_bytes()).hexdigest()
    for pages in (set(),{0,1,2,3,4},{-1}):
        with pytest.raises(ValueError,match='window'): parse_pdf(s,tmp_path/'s',out,cfg,pages)
    cfg.security.external_models_enabled=True
    with pytest.raises(ValueError,match='local_native'): parse_pdf(s,tmp_path/'s',out,cfg,{0})


def test_missing_and_duplicate_sources_are_rejected(tmp_path):
    r=row(source())
    result=build_manifest([r,r],'a'*64,tmp_path,{'PA001','PA099'})
    assert not result['items'] and len(result['rejected'])==2


def test_one_failed_file_does_not_hide_next_result(tmp_path):
    invalid=b'<html><body>Unsupported</body></html>'; s=source(invalid)
    store(tmp_path/'s',s,invalid)
    result=run_item(s,tmp_path/'s',tmp_path/'bad',CONFIG)
    assert result.status=='failed' and result.canonical_path is None
    assert (tmp_path/'bad'/'result.json').exists()
    store(tmp_path/'s',source())
    assert run_item(source(),tmp_path/'s',tmp_path/'good',CONFIG).status=='review_required'


def test_published_schemas_match_models():
    from pdf_extraction.contracts.source import ParseResult
    for name, model in [('source-snapshot',Snapshot),('html-structure',HtmlStructure),('source-parse-result',ParseResult)]:
        assert json.loads(Path(f'config/schemas/{name}.schema.json').read_text())==model.model_json_schema()
