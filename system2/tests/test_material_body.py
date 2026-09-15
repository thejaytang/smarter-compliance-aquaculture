from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import pytest
from pdf_extraction.orchestration.material_body import select_body
from pdf_extraction.orchestration.material_parser import parse_material

def block(id,text,page=1,**extra):
    return dict(id=id,type='text',text=text,source_refs=[dict(scope_id=f'page:{page}',page=page)],**extra)

def parse(tmp_path,html):
    src=tmp_path/'input';src.mkdir();raw=html.encode();(src/'doc.html').write_bytes(raw)
    source=dict(source_id='TS005',snapshot_id='TS005-001',content_hash=sha256(raw).hexdigest(),relative_path='doc.html',file_format='html',operator_selection_decision='INCLUDE',selection_status='INCLUDE',snapshot_status='STORED',source_status='CURRENT',download_status='SUCCESS',registry_sha256='0'*64)
    return parse_material(source,src,tmp_path/'out')

def test_html_main_keeps_body_titles_tables_lists_and_notes(tmp_path):
    result=parse(tmp_path,'<html><body><header><h1>Website title</h1></header><nav><p>Search</p></nav><div id="documentMeta"><p>Published 2026</p></div><main><nav role="doc-toc"><h2>Contents</h2><p>Chapter 1</p></nav><h1>Chapter 1</h1><p>The fish shall swim.</p><a role="button" href="#share"><span>Share paragraph</span></a><ul><li>Check the net</li></ul><table><tr><th>A</th><th>B</th></tr><tr><td>1</td><td>2</td></tr></table><p>Read <a href="#footnote1">note 1</a>.</p></main><aside id="footnote1">Necessary note.</aside><footer>Website help</footer></body></html>')
    texts=[b['text'] for b in result['blocks']]
    assert 'Chapter 1' in texts and 'The fish shall swim.' in texts and 'Necessary note.' in texts
    assert 'Share paragraph' not in texts
    assert 'Contents' not in texts and 'Website help' not in texts and 'Website title' not in texts and 'Published 2026' not in texts
    assert any(b['type']=='table' for b in result['blocks'])
    assert result['body_filter']['excluded_count']>=5
    assert (tmp_path/'out/body-selection.json').exists()
    assert b'Website title' in (tmp_path/'out/source.html').read_bytes()
    ids={b['id'] for b in result['blocks']}
    assert all(b.get('parent_id') is None or b['parent_id'] in ids for b in result['blocks'])
    assert all(set(b.get('dependencies',[]))<=ids for b in result['blocks'])

def test_unknown_frontmatter_and_real_contents_prose_are_retained(tmp_path):
    result=parse(tmp_path,'<body><h1>Rules</h1><p>The contents shall be inspected.</p><p>Introduction and context.</p><h2>Contents</h2><p>This section describes required container contents.</p></body>')
    assert result['body_filter']['excluded_count']==0
    assert any(b['text']=='Contents' for b in result['blocks'])

def test_pdf_toc_and_cover_excluded_without_dropping_body_headings():
    items=[block('cover','Aquaculture Standard'),block('publisher','September 2026'),block('toc','Contents',2),block('a','Chapter 1 .... 3',2),block('b','Chapter 2 .... 4',2),block('h','Chapter 1 General',3),block('p','The operator shall inspect the net.',3)]
    original=deepcopy(items);kept,evidence=select_body(items,'pdf')
    assert [b['id'] for b in kept]==['h','p'] and kept[0]['type']=='heading'
    assert evidence['excluded_count']==5 and items==original

def test_pdf_joined_toc_and_table_toc_are_recognized():
    items=[block('joined','Table of contents\nChapter 1 .... 3\nChapter 2 .... 4',1)]
    items[0]['text']='Table of contents\nChapter 1 .... 3\nChapter 2 .... 4'
    assert select_body(items,'pdf')[0]==[]
    table=dict(id='t',type='table',text='',table={'rows':[['Section','Page'],['Chapter 1','3'],['Chapter 2','4']]},source_refs=[{'scope_id':'page:1','page':1}])
    kept,_=select_body([block('toc','目录'),table,block('h','Chapter 1 General',3)],'pdf')
    assert [b['id'] for b in kept]==['h']

def test_early_normative_text_and_unlabelled_tables_are_not_cover_or_toc():
    items=[block('p','The operator shall record every transfer.',1),block('toc','Contents',2),block('a','Chapter 1 .... 3',2),block('b','Chapter 2 .... 4',2)]
    assert [b['id'] for b in select_body(items,'pdf')[0]]==['p']
    table=dict(id='t',type='table',text='',table={'rows':[['Size','Count'],['Small','3'],['Large','4']]},source_refs=[])
    assert select_body([table],'pdf')[0][0]['id']=='t'

def test_repeated_margins_only_filter_with_page_geometry():
    items=[]
    for page in (1,2,3):
        h=block('h'+str(page),'Standard header',page);h['source_refs'][0].update(bbox=[10,5,200,15],page_size=[600,800]);items.extend([h,block('p'+str(page),'Keep this paragraph.',page)])
    kept,evidence=select_body(items,'pdf');assert len(kept)==3 and evidence['excluded_count']==3


def test_machine_markdown_keeps_basic_format_and_list_markers(tmp_path):
    result=parse(tmp_path,'<html><body><main><h1>Chapter <em>1</em></h1><p>The <strong>fish</strong> shall swim.</p><ol start="3"><li>Inspect the net.</li><li>Record it.</li></ol></main></body></html>')
    assert [b.get('markdown_source') for b in result['blocks']]==['# Chapter *1*','The **fish** shall swim.','3. Inspect the net.','4. Record it.']
    assert result['blocks'][1]['text']=='The fish shall swim.'


def test_foreword_before_toc_is_not_a_cover():
    items=[block('h','Foreword',1),block('p','Published in 2026 to describe the common framework.',1),block('toc','Contents',2),block('a','Chapter 1 .... 3',2),block('b','Chapter 2 .... 4',2)]
    assert [b['id'] for b in select_body(items,'pdf')[0]]==['h','p']


def test_explicit_layout_tables_become_lists_while_data_tables_remain_tables(tmp_path):
    result=parse(tmp_path,'''<html><body><main><h2>Chapter 1</h2>
<table class="listeItem" data-level="1"><tr><td class="listeitemNummer">a.</td><td><em>Definition:</em> keep all words.</td></tr></table>
<table class="listeItem" data-level="2"><tr><td class="listeitemNummer">2.</td><td>Nested item.</td></tr></table>
<table><tr><td>a.</td><td>This is an ordinary data table.</td></tr></table>
</main></body></html>''')
    a,b,c=result['blocks'][1:]
    assert a['type']=='text' and a['numbering']=='a.'
    assert a['markdown_source']=='a. *Definition:* keep all words.'
    assert b['type']=='text' and b['list_depth']==1 and b['numbering']=='2.'
    assert c['type']=='table' and c['table']['rows'][0][1]=='This is an ordinary data table.'
