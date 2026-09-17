"""Read-only source fidelity check for the exact PA004 saved snapshot."""
from pathlib import Path
import json,sys,sqlite3,re,hashlib
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'system2/src'))
from bs4 import BeautifulSoup
from pdf_extraction.orchestration.material_parser import parse_material
with sqlite3.connect((OUT/'before.sqlite').as_uri()+'?mode=ro',uri=True) as db:
    material=json.loads(db.execute('SELECT data FROM material_documents WHERE id=?',('3a095821f303f88e7933410e71434264',)).fetchone()[0])
source=ROOT/'system1/Data'/material['source']['relative_path'];raw=source.read_bytes()
assert hashlib.sha256(raw).hexdigest()==material['source']['content_hash']
result=parse_material(material['source'],ROOT/'system1/Data',OUT/'parser-artifacts'/'final')
(OUT/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
soup=BeautifulSoup(raw,'lxml');body=soup.select_one('#documentBody')
for node in body.select('[role="button"],button,script,style'):node.decompose()
norm=lambda value:re.sub(r'\s+','',value)
expected=norm(body.get_text())
actual=norm(''.join(b.get('text','')+''.join(str(c) for row in b.get('table',{}).get('rows',[]) for c in row) for b in result['blocks']))
headings=[b for b in result['blocks'] if b['type']=='heading']
source_headings=body.select('h1,h2,h3,h4,h5,h6')
assert [norm(n.get_text()) for n in source_headings]==[norm(b['text']) for b in headings]
assert expected==actual
lists=[b for b in result['blocks'] if b.get('source_layout')=='numbered_list_table']
source_lists=body.select('table.listeItem')
assert [norm(n.get_text()) for n in source_lists]==[norm(b['text']) for b in lists]
assert [max(0,int(n.get('data-level','1'))-1) for n in source_lists]==[b['list_depth'] for b in lists]
summary=dict(source_id='PA004',source_hash=material['source']['content_hash'],parser_version=result['parser_version'],status=result['status'],retained=len(result['blocks']),excluded=result['body_filter']['excluded_count'],body_chars_without_whitespace=len(expected),body_text_order_matches_source=True,headings=len(headings),all_headings_match_source=True,list_items=len(lists),all_list_markers_text_and_depth_match_source=True,table_count=sum(b['type']=='table' for b in result['blocks']),start=[b['text'] for b in result['blocks'][:4]],human_review_confirmed=False)
(OUT/'source-comparison.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
print(json.dumps(summary,ensure_ascii=False,indent=2))
