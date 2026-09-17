from hashlib import sha256
from pathlib import Path
import json
import pytest
from pdf_extraction.contracts.html import HtmlDocument
from pdf_extraction.formats.html import parse_html
from pdf_extraction.verification.html import verify_html
from pdf_extraction.orchestration.source_batch import run_item
from tests.contracts.test_source_intake import source,store

RAW=b'''<html><head><title>Example</title></head><body><nav>Website menu</nav><div id="documentMeta"><h1>Law</h1></div><div id="documentBody"><div class="kapittel"><h2>Section</h2><p>Introduction outside clauses.</p><div class="paragraf" id="p1"><h3>Clause</h3><p>Must <b>not</b> omit 1.5 mg/L. <a href="#note">[1]</a></p><ul><li>Parent<ul><li>Child</li></ul></li></ul><table><tr><th rowspan="2">Header</th><th colspan="2">Values</th></tr><tr><td>A</td><td>B</td></tr></table><table><tr><td class="fotnote" id="note">Footnote <a href="#p1">return</a></td></tr></table><!-- --><script>alert('do not execute')</script></div></div></div></body></html>'''


def doc(raw=RAW):return parse_html(raw,source(raw),{'template':'auto'})


def test_v2_preserves_source_text_structure_and_independent_verification():
    d=doc();v=verify_html(RAW,d)
    assert v['status']=='passed',v
    assert d.schema_version=='html-document/2'
    assert any('Introduction outside' in a.text for a in d.atoms)
    assert not any('Website menu' in a.text or 'alert' in a.text for a in d.atoms)
    assert len(d.tables)==2 and len(d.lists)==2
    assert [(c.row,c.column,c.rowspan,c.colspan) for c in d.tables[0].cells]==[(0,0,2,1),(0,1,1,2),(1,1,1,1),(1,2,1,1)]
    assert all(l.status=='resolved' for l in d.links)
    assert any(n.kind=='footnote' for n in d.nodes)

@pytest.mark.parametrize('mutation',['drop_text','change_text','repeat_text','drop_table','change_cell','drop_link','shrink_root','wrong_parent','drop_node','drop_list','hide_comment','wrong_link_target','wrong_type','wrong_heading_context','wrong_role'])
def test_verifier_detects_mutated_artifacts(mutation):
    payload=doc().model_dump()
    if mutation=='drop_text':payload['atoms'].pop()
    elif mutation=='change_text':payload['atoms'][0]['text']='invented'
    elif mutation=='repeat_text':payload['atoms'].append(payload['atoms'][0])
    elif mutation=='drop_table':payload['tables'].pop()
    elif mutation=='change_cell':payload['tables'][0]['cells'][0]['column']=3
    elif mutation=='drop_link':payload['links'].pop()
    elif mutation=='shrink_root':payload['root_node_ids'].pop()
    elif mutation=='wrong_parent':payload['nodes'][-1]['parent_id']=payload['nodes'][0]['id']
    elif mutation=='drop_node':payload['nodes'].pop()
    elif mutation=='drop_list':payload['lists'].pop()
    elif mutation=='hide_comment':payload['omitted'].pop()
    elif mutation=='wrong_link_target':payload['links'][0]['target_node_ids']=[payload['nodes'][0]['id']]
    elif mutation=='wrong_type':next(n for n in payload['nodes'] if n['kind']=='paragraph')['kind']='container'
    elif mutation=='wrong_heading_context':payload['nodes'][-1]['section_id']=payload['nodes'][0]['id']
    elif mutation=='wrong_role':next(n for n in payload['nodes'] if n['kind']=='paragraph')['role']='navigation'
    assert verify_html(RAW,HtmlDocument(**payload))['status']=='failed'


def test_empty_body_and_unknown_template_fail_closed():
    for raw in (b'<html><div id="documentMeta">Law</div><div id="documentBody"></div></html>',b'<html><main>Unknown site</main></html>'):
        with pytest.raises(ValueError):doc(raw)


def test_asc_controls_hidden_footnotes_and_attributes_preserved():
    raw=b'''<html><main><aside class="sidebar--filters"><select><option>Marine</option></select></aside><h1>Standard</h1><div hidden data-system="cages"><p>Conditional provision <span class="footnote-link">1<span class="popup"><span class="popup-inner">Note body</span></span></span></p></div></main></html>'''
    d=doc(raw);assert verify_html(raw,d)['status']=='passed'
    assert any(n.attributes.get('data-system')=='cages' and 'hidden' in n.attributes for n in d.nodes)
    assert any(n.role=='control' for n in d.nodes)
    assert d.links[0].relation=='embedded_footnote' and d.links[0].status=='resolved'
    assert 'conditional_display_preserved_not_evaluated' in d.issues


def test_v2_batch_outputs_verified_canonical(tmp_path):
    s=source(RAW);store(tmp_path/'sources',s,RAW)
    r=run_item(s,tmp_path/'sources',tmp_path/'run',{'template':'auto'})
    assert r.status=='review_required' and r.canonical_schema_version=='html-document/2'
    p=tmp_path/'run'/r.verification_path
    assert sha256(p.read_bytes()).hexdigest()==r.verification_sha256
    assert json.loads(p.read_text())['status']=='passed'


def test_nested_table_cells_belong_only_to_their_table():
    raw=RAW.replace(b'<td>A</td>',b'<td>A<table><tr><td>Nested</td></tr></table></td>')
    d=doc(raw)
    assert len(d.tables)==3 and [len(t.cells) for t in d.tables]==[4,1,1]
    assert verify_html(raw,d)['status']=='passed'


def test_duplicate_targets_remain_ambiguous_and_active_links_blocked():
    raw=RAW.replace(b'<!-- -->',b'<p id="note">Duplicate</p><a href="javascript:alert(1)">action</a>')
    d=doc(raw)
    assert any(l.status=='ambiguous' for l in d.links)
    assert any(l.status=='blocked' for l in d.links)
    assert verify_html(raw,d)['status']=='passed'


def test_empty_comment_parser_difference_is_normalized_only_for_comments():
    raw=RAW.replace(b'<!-- -->',b'<!---->')
    assert verify_html(raw,doc(raw))['status']=='passed'


def test_bad_span_is_explicit_not_silently_coerced():
    raw=RAW.replace(b'rowspan="2"',b'rowspan="nonsense"')
    d=doc(raw);assert d.tables[0].issues and d.tables[0].column_count is None
    assert verify_html(raw,d)['status']=='passed'


def test_v2_published_schema_and_legacy_entry():
    from pdf_extraction.contracts.source import HtmlStructure
    assert json.loads(Path('config/schemas/html-document-v2.schema.json').read_text())==HtmlDocument.model_json_schema()
    legacy=parse_html(RAW,source(RAW),{'template':'lovdata-document-v1','encoding':'utf-8-sig','metadata':'#documentMeta','body':'#documentBody'})
    assert isinstance(legacy,HtmlStructure)


def test_whitespace_between_inline_nodes_is_not_silently_lost():
    raw=RAW.replace(b'Introduction outside clauses.',b'<b>Separate</b> <i>words</i> &amp; symbols.')
    d=doc(raw);v=verify_html(raw,d)
    assert v['status']=='passed' and v['raw_token_check']['status']=='passed'
    assert any(a.text==' ' for a in d.atoms)


def test_independent_raw_tokens_detect_shared_dom_loss():
    from pdf_extraction.verification.html_tokens import verify_raw_text
    d=doc();payload=d.model_dump();payload['atoms'].pop(0)
    assert verify_raw_text(RAW,HtmlDocument(**payload))['status']=='failed'


def test_source_indentation_is_preserved_for_raw_token_fidelity():
    raw=RAW.replace(b'</h2><p>',b'</h2>   \n    <p>')
    d=doc(raw);assert verify_html(raw,d)['status']=='passed'
    assert any(a.text=='   \n    ' for a in d.atoms)
