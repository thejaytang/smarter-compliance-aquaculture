from pathlib import Path
from hashlib import sha256
import json
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'system2/src'))
from pdf_extraction.orchestration.material_parser import parse_material
OUT=Path(__file__).resolve().parent
src=OUT/'fixture/Data/A_Public_Authority/PA001-001_material.html'
raw=src.read_bytes()
source=dict(source_id='PA001',snapshot_id='PA001-001',relative_path=src.name,content_hash=sha256(raw).hexdigest(),file_format='html',operator_selection_decision='INCLUDE',selection_status='INCLUDE',snapshot_status='STORED',source_status='CURRENT',download_status='SUCCESS',registry_sha256='0'*64)
result=parse_material(source,src.parent,OUT/'real-html-extraction-final')
summary=dict(parser_version=result['parser_version'],status=result['status'],kept=len(result['blocks']),excluded=result['body_filter']['excluded_count'],headings=[b['text'] for b in result['blocks'] if b['type']=='heading'],start=[b['text'][:160] for b in result['blocks'][:10]],reasons=sorted(set(x['reason'] for x in result['body_filter']['excluded'])))
(OUT/'real-html-evidence.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
print(json.dumps(summary,ensure_ascii=False,indent=2))
