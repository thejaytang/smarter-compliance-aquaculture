"""Exposed PA001 diagnostic: source DOM labels, never a business Gold score."""
from pathlib import Path
from hashlib import sha256
import json
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'system2/src'))
from bs4 import BeautifulSoup
from pdf_extraction.contracts.source import Snapshot
from pdf_extraction.formats.html import dom_path
from pdf_extraction.orchestration.material_parser import parse_material

out = Path(__file__).resolve().parent
stage = sys.argv[1]
assert stage in ('before', 'after')
freeze = json.loads((out / 'freeze.json').read_text())
source_path = ROOT / freeze['source']
raw = source_path.read_bytes()
assert sha256(raw).hexdigest() == freeze['source_sha256']
source = Snapshot(source_id='PA001', snapshot_id='PA001-001',
    relative_path=source_path.name, content_hash=freeze['source_sha256'],
    file_format='html', operator_selection_decision='INCLUDE', selection_status='INCLUDE',
    snapshot_status='STORED', source_status='CURRENT', download_status='SUCCESS', registry_sha256='0'*64)
candidate = parse_material(source, source_path.parent, out / stage)
soup = BeautifulSoup(raw, 'lxml')
by_locator = {b['source_refs'][0]['locator']: b for b in candidate['blocks'] if b['type']=='heading'}
labels = []
for span in soup.select('span.paragrafValue'):
    heading = span.find_parent(['h1','h2','h3','h4','h5','h6'])
    if heading is None:
        continue
    label = span.get_text().strip().removesuffix('.')
    block = by_locator.get(dom_path(heading), {})
    labels.append({'locator':dom_path(heading),'original_label':label,
        'original_heading':heading.get_text(),'actual_numbering':block.get('numbering'),
        'correct':block.get('numbering')==label,'original_text_retained':block.get('text')==heading.get_text()})
result = {'stage':stage,'source_sha256':freeze['source_sha256'],
    'parser_version':candidate['parser_version'],'denominator_source':'all paragrafValue spans within original heading elements',
    'correct':sum(x['correct'] for x in labels),'total':len(labels),'labels':labels,
    'all_original_heading_text_retained':all(x['original_text_retained'] for x in labels),
    'scope':'exposed development diagnostic only; not general HTML coverage, independent quality, or Requirement recognition'}
(out / (stage+'-measurement.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2))
assert source_path.read_bytes()==raw
print(json.dumps({k:v for k,v in result.items() if k!='labels'},indent=2))
