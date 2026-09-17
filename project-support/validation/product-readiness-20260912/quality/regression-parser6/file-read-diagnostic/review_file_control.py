from pathlib import Path
import hashlib,json,importlib.util
from fastapi.testclient import TestClient
from reportlab.pdfgen import canvas
from pdf_extraction.api.app import create_app
root=Path('/Users/tang/Desktop/smarter-compliance-aquaculture/05_Working area of requirements side');s=root/'system2';out=root/'project-support/product-readiness-20260912/quality/regression-parser6/file-read-diagnostic'
expected=json.loads((out.parent/'run-start.json').read_text())['source_and_tests']
assert hashlib.sha256((s/'src/pdf_extraction/api/app.py').read_bytes()).hexdigest()==expected['src/pdf_extraction/api/app.py']
control=out/'readable-control';control.mkdir(exist_ok=False);ui=control/'ui';ui.mkdir();text='<!doctype html><title>Isolated read control</title><p>Local read control</p>';(ui/'review.html').write_text(text)
pdf=control/'synthetic.pdf';c=canvas.Canvas(str(pdf));c.drawString(30,700,'Local read control');c.save();config=control/'config.yaml';config.write_text('{}')
client=TestClient(create_app(control/'jobs.sqlite3',ui));response=client.post('/documents',json={'input_path':str(pdf),'output_dir':str(control/'output'),'config_path':str(config)});assert response.status_code==202
job=response.json()['id'];review=client.get('/review/'+job);assert review.status_code==200 and review.text==text
result={'status':'PASS_DIAGNOSTIC_CONTROL_ONLY','create_status':response.status_code,'review_status':review.status_code,'body_exact':review.text==text,'api_module_sha256':expected['src/pdf_extraction/api/app.py'],'input':'New readable local HTML control. Does not retest or replace unavailable original review.html; full regression remains FAIL.','actual_anyio_origin':importlib.util.find_spec('anyio').origin}
(out/'readable-control.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
